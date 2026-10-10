import sys
import asyncio
from app.db.session import AsyncSessionLocal, init_db
from app.services.ingest import ingest_transcripts

async def main():
    print("Initializing database extension and tables...")
    await init_db()
    
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"Starting transcript ingestion from data directory: {data_dir or 'default'}...")
    
    async with AsyncSessionLocal() as session:
        stats = await ingest_transcripts(db_session=session, data_dir=data_dir)
        print("\n--- INGESTION RESULTS ---")
        print(f"Status:            Completed")
        print(f"Files Discovered:  {stats['files_discovered']}")
        print(f"Files Ingested:    {stats['files_ingested']}")
        print(f"Chunks Created:    {stats['chunks_created']}")
        print(f"Chunks Skipped:    {stats['chunks_skipped']}")
        print(f"Failures:          {stats['failures']}")
        if stats["diagnostics"]:
            print("\nDiagnostics:")
            for diag in stats["diagnostics"]:
                print(f" - {diag}")

if __name__ == "__main__":
    asyncio.run(main())
