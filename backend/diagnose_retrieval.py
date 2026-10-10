import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.services.retrieval import search_transcript_chunks
from app.services.ingest import generate_embedding

async def diagnose():
    async with AsyncSessionLocal() as session:
        # Check chunks in DB
        res = await session.execute(text('SELECT count(*), array_agg(DISTINCT transcript_id) FROM transcript_chunks;'))
        row = res.fetchone()
        print('Total chunks in DB:', row[0])
        print('Transcript IDs:', row[1])

        res2 = await session.execute(text('SELECT id, transcript_id, episode_title, speaker, vector_dims(embedding), length(content) FROM transcript_chunks;'))
        for r in res2.fetchall():
            print(f'Chunk: {r[1]} | {r[2][:35]} | {r[3]} | Dims: {r[4]} | ContentLen: {r[5]}')

    # Test queries
    test_queries = [
        "Patrick Campbell's SaaS pricing advice",
        "How should SaaS companies price their products according to Patrick Campbell?",
        "What makes a great growth strategy and growth loops?",
        "Elena Verna B2B product-led growth",
        "How to bake sourdough bread at home with chocolate"
    ]

    for q in test_queries:
        chunks = await search_transcript_chunks(query=q, top_k=5, similarity_threshold=0.0)
        print(f"\n--- Query: '{q}' ---")
        for c in chunks:
            print(f"  score: {c['similarity_score']:.4f} | dist: {c['distance']:.4f} | ep: {c['episode_title']} | speaker: {c['speaker']}")

if __name__ == '__main__':
    asyncio.run(diagnose())
