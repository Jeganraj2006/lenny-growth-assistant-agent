import os
import glob
import json
import hashlib
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import TranscriptChunkModel

def compute_content_hash(content: str, transcript_id: str, chunk_index: int) -> str:
    """Computes a deterministic SHA-256 hash for a transcript chunk."""
    raw = f"{transcript_id}:{chunk_index}:{content.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Deterministically splits text into overlapping chunks by words.
    Ensures context continuity across boundaries.
    """
    words = text.split()
    if not words:
        return []
    
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break
    return chunks

def parse_transcript_file(file_path: str) -> Dict[str, Any]:
    """
    Parses a transcript file (.json, .md, .txt) and extracts metadata + body text.
    """
    ext = os.path.splitext(file_path)[1].lower()
    basename = os.path.basename(file_path)
    transcript_id = os.path.splitext(basename)[0]

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "transcript_id": data.get("id") or transcript_id,
            "episode_title": data.get("title") or data.get("episode_title") or transcript_id.replace("-", " ").title(),
            "speaker": data.get("guest") or data.get("speaker") or "Lenny's Guest",
            "source_url": data.get("url") or data.get("source_url") or "",
            "content": data.get("content") or data.get("transcript") or data.get("text") or ""
        }
    elif ext in [".md", ".txt"]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        episode_title = transcript_id.replace("-", " ").replace("_", " ").title()
        speaker = "Lenny's Guest"
        source_url = ""
        content_lines = []

        # Header frontmatter parsing if available
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("Title:") or line_str.startswith("# "):
                episode_title = line_str.replace("Title:", "").replace("# ", "").strip()
            elif line_str.startswith("Guest:") or line_str.startswith("Speaker:"):
                speaker = line_str.replace("Guest:", "").replace("Speaker:", "").strip()
            elif line_str.startswith("URL:") or line_str.startswith("Source:"):
                source_url = line_str.replace("URL:", "").replace("Source:", "").strip()
            else:
                content_lines.append(line)

        return {
            "transcript_id": transcript_id,
            "episode_title": episode_title,
            "speaker": speaker,
            "source_url": source_url,
            "content": "".join(content_lines).strip()
        }
    else:
        raise ValueError(f"Unsupported file format: {ext}")

async def generate_embedding(text_chunk: str, host_url: Optional[str] = None, model: Optional[str] = None) -> List[float]:
    """
    Generates dense vector embedding using Ollama nomic-embed-text:latest (768 dimensions).
    """
    host = host_url or settings.OLLAMA_HOST
    embed_model = model or settings.OLLAMA_EMBED_MODEL

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try Ollama /api/embeddings first
        try:
            resp = await client.post(
                f"{host}/api/embeddings",
                json={"model": embed_model, "prompt": text_chunk}
            )
            if resp.status_code == 200:
                data = resp.json()
                embedding = data.get("embedding", [])
                if embedding:
                    return embedding
        except Exception:
            pass

        # Fallback to Ollama /v1/embeddings
        resp = await client.post(
            f"{host}/v1/embeddings",
            json={"model": embed_model, "input": text_chunk}
        )
        if resp.status_code == 200:
            data = resp.json()
            embedding = data.get("data", [{}])[0].get("embedding", [])
            if embedding:
                return embedding

        raise RuntimeError(f"Embedding generation failed for model {embed_model} at {host}")

async def ingest_transcripts(
    db_session: AsyncSession,
    data_dir: Optional[str] = None,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None
) -> Dict[str, Any]:
    """
    Scans data directory, parses transcript files, generates embeddings,
    prunes obsolete stale chunks on re-ingestion, and idempotently inserts chunk records into PostgreSQL.
    """
    target_dir = data_dir or settings.DATA_DIR
    c_size = chunk_size or settings.CHUNK_SIZE
    c_overlap = overlap or settings.CHUNK_OVERLAP

    stats = {
        "files_discovered": 0,
        "files_ingested": 0,
        "chunks_created": 0,
        "chunks_skipped": 0,
        "chunks_pruned": 0,
        "failures": 0,
        "diagnostics": []
    }

    if not os.path.exists(target_dir):
        stats["diagnostics"].append(f"Data directory '{target_dir}' does not exist. Please create directory and place podcast transcripts (.json, .md, .txt) inside.")
        return stats

    file_patterns = [os.path.join(target_dir, "**", f"*{ext}") for ext in [".json", ".md", ".txt"]]
    discovered_files = []
    for pattern in file_patterns:
        discovered_files.extend(glob.glob(pattern, recursive=True))

    stats["files_discovered"] = len(discovered_files)

    if not discovered_files:
        stats["diagnostics"].append(f"No transcript files (.json, .md, .txt) found in '{target_dir}'. Place files in directory to ingest.")
        return stats

    for file_path in discovered_files:
        try:
            parsed = parse_transcript_file(file_path)
            raw_content = parsed.get("content", "").strip()
            if not raw_content:
                stats["failures"] += 1
                stats["diagnostics"].append(f"Skipped empty file: {os.path.basename(file_path)}")
                continue

            chunks = chunk_text(raw_content, chunk_size=c_size, overlap=c_overlap)
            current_hashes = [compute_content_hash(text_block, parsed["transcript_id"], idx) for idx, text_block in enumerate(chunks)]
            
            # Prune stale/obsolete chunks for this transcript_id whose content_hash is no longer in current_hashes
            del_stmt = (
                delete(TranscriptChunkModel)
                .where(
                    TranscriptChunkModel.transcript_id == parsed["transcript_id"],
                    TranscriptChunkModel.content_hash.not_in(current_hashes)
                )
            )
            del_res = await db_session.execute(del_stmt)
            if del_res.rowcount and del_res.rowcount > 0:
                stats["chunks_pruned"] += del_res.rowcount

            file_chunks_created = 0

            for idx, text_block in enumerate(chunks):
                chash = current_hashes[idx]

                # Idempotency check: check if chunk hash already exists
                stmt = select(TranscriptChunkModel.id).where(TranscriptChunkModel.content_hash == chash)
                existing = await db_session.execute(stmt)
                if existing.scalar_one_or_none():
                    stats["chunks_skipped"] += 1
                    continue

                # Generate vector embedding via Ollama
                embedding = await generate_embedding(text_block)

                # Instantiate new chunk record
                chunk_record = TranscriptChunkModel(
                    transcript_id=parsed["transcript_id"],
                    episode_title=parsed["episode_title"],
                    speaker=parsed["speaker"],
                    source_url=parsed["source_url"],
                    chunk_index=idx,
                    content=text_block,
                    content_hash=chash,
                    embedding=embedding
                )
                db_session.add(chunk_record)
                file_chunks_created += 1

            await db_session.commit()
            stats["files_ingested"] += 1
            stats["chunks_created"] += file_chunks_created

        except Exception as exc:
            await db_session.rollback()
            stats["failures"] += 1
            stats["diagnostics"].append(f"Error processing {os.path.basename(file_path)}: {str(exc)}")

    return stats
