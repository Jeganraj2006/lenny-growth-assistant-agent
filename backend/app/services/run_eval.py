import sys
import asyncio
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.retrieval import search_transcript_chunks
from app.services.chat import call_ollama_chat

EVAL_QUESTIONS = [
    {
        "id": 1,
        "query": "What is Elena Verna's view on freemium vs free trial for B2B SaaS?",
        "expected_speaker": "Elena Verna",
        "should_find_evidence": True
    },
    {
        "id": 2,
        "query": "How does Patrick Campbell advise structuring SaaS value metric pricing?",
        "expected_speaker": "Patrick Campbell",
        "should_find_evidence": True
    },
    {
        "id": 3,
        "query": "What is the LNO framework for PM time management by Shreyas Doshi?",
        "expected_speaker": "Shreyas Doshi",
        "should_find_evidence": True
    },
    {
        "id": 4,
        "query": "What is the difference between growth funnels and growth loops according to Brian Balfour?",
        "expected_speaker": "Brian Balfour",
        "should_find_evidence": True
    },
    {
        "id": 5,
        "query": "How does Geoff Charles maintain product shipping velocity at Ramp?",
        "expected_speaker": "Geoff Charles",
        "should_find_evidence": True
    },
    {
        "id": 6,
        "query": "How does Casey Winters explain identifying the hard side of a two-sided marketplace?",
        "expected_speaker": "Casey Winters",
        "should_find_evidence": True
    },
    {
        "id": 7,
        "query": "What is Shreyas Doshi's approach to conducting a product pre-mortem?",
        "expected_speaker": "Shreyas Doshi",
        "should_find_evidence": True
    },
    {
        "id": 8,
        "query": "How does Patrick Campbell suggest tackling involuntary customer churn?",
        "expected_speaker": "Patrick Campbell",
        "should_find_evidence": True
    },
    {
        "id": 9,
        "query": "What are the quantum computing algorithms for sub-atomic simulation in drug discovery?",
        "expected_speaker": None,
        "should_find_evidence": False
    },
    {
        "id": 10,
        "query": "How do you configure Kubernetes ingress controllers for multi-region failover?",
        "expected_speaker": None,
        "should_find_evidence": False
    }
]

async def main():
    print("=================================================================")
    print("      LENNY GROWTH ASSISTANT — RAG RETRIEVAL EVALUATION RUN      ")
    print("=================================================================\n")

    results = []

    for item in EVAL_QUESTIONS:
        qid = item["id"]
        query = item["query"]
        expected_speaker = item["expected_speaker"]
        should_find = item["should_find_evidence"]

        print(f"[{qid}/10] Query: '{query}'", flush=True)

        # Execute vector search
        chunks = await search_transcript_chunks(
            db_session=None,
            query=query,
            top_k=3,
            similarity_threshold=settings.RETRIEVAL_THRESHOLD
        )

        found_count = len(chunks)
        top_title = chunks[0]["episode_title"] if chunks else "N/A (No Evidence Found)"
        top_speaker = chunks[0]["speaker"] if chunks else "N/A"
        top_score = chunks[0]["similarity_score"] if chunks else 0.0

        is_valid_citation = False
        if should_find:
            is_valid_citation = (found_count > 0) and (expected_speaker.lower() in top_speaker.lower() if expected_speaker else True)
        else:
            is_valid_citation = (found_count == 0)

        status = "PASSED" if is_valid_citation else "WARNING"

        print(f"      Retrieved Chunks: {found_count}", flush=True)
        print(f"      Top Episode:      {top_title}", flush=True)
        print(f"      Top Speaker:      {top_speaker}", flush=True)
        print(f"      Similarity Score: {top_score:.4f}", flush=True)
        print(f"      Eval Status:      {status}\n", flush=True)

        results.append({
            "id": qid,
            "query": query,
            "found_count": found_count,
                "top_title": top_title,
                "top_speaker": top_speaker,
                "top_score": top_score,
                "status": status,
                "should_find": should_find
            })

    # Summary Statistics
    total_evals = len(results)
    passed_count = sum(1 for r in results if r["status"] == "PASSED")
    print("-----------------------------------------------------------------")
    print(f"EVALUATION SUMMARY: {passed_count}/{total_evals} Passed ({passed_count/total_evals*100:.1f}%)")
    print("-----------------------------------------------------------------")

if __name__ == "__main__":
    asyncio.run(main())
