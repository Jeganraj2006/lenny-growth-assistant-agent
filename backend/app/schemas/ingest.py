from typing import List, Optional
from pydantic import BaseModel, Field

class IngestRequest(BaseModel):
    data_dir: Optional[str] = Field(default=None, description="Custom data directory path for transcript files")
    chunk_size: Optional[int] = Field(default=None, description="Custom chunk size in words")
    chunk_overlap: Optional[int] = Field(default=None, description="Custom chunk overlap in words")

class IngestResponse(BaseModel):
    status: str = Field(description="Ingestion process status (completed / failed)")
    files_discovered: int = Field(description="Total transcript files discovered")
    files_ingested: int = Field(description="Total files successfully parsed & stored")
    chunks_created: int = Field(description="Total new vector chunks created")
    chunks_skipped: int = Field(description="Chunks skipped due to content hash idempotency")
    failures: int = Field(description="Count of files that failed processing")
    diagnostics: List[str] = Field(default_factory=list, description="Diagnostic logs & error messages")
