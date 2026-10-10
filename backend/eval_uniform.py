import asyncio
from app.services.run_eval import EVAL_QUESTIONS
from app.services.retrieval import search_transcript_chunks

async def eval_scores():
    print("ID | ShouldFind | Top Score | Top Speaker        | Query")
    print("-" * 80)
    for item in EVAL_QUESTIONS:
        chunks = await search_transcript_chunks(query=item['query'], top_k=1, similarity_threshold=0.0)
        top = chunks[0] if chunks else None
        score = top['similarity_score'] if top else 0.0
        speaker = top['speaker'] if top else 'None'
        should = "YES" if item['should_find_evidence'] else "NO "
        print(f"{item['id']:2d} | {should}        | {score:.4f}    | {speaker:18} | {item['query'][:40]}")

if __name__ == '__main__':
    asyncio.run(eval_scores())
