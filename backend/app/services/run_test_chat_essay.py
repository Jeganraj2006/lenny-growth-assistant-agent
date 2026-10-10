import sys
import asyncio
import uuid
from app.db.session import AsyncSessionLocal
from app.db.models import SessionModel
from app.services.chat import process_chat_completion
from app.services.essay import generate_ship30_essay

async def main():
    print("=================================================================")
    print("   LENNY GROWTH ASSISTANT — OLLAMA CHAT & ESSAY END-TO-END TEST  ")
    print("=================================================================\n", flush=True)

    # 0. Create a test session
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Phase C5 Real Corpus Test Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        session_id = sess.id
        print(f"Created Test Session: {session_id}", flush=True)

    # 1. Test Grounded Chat Response
    print("\n--- 1. Testing Grounded Chat Completion ---", flush=True)
    chat_prompt = "What is Elena Verna's core framework for product-led growth and freemium conversion?"
    print(f"User Prompt: '{chat_prompt}'", flush=True)
    
    async with AsyncSessionLocal() as session:
        user_msg, assistant_msg, citations, provider_used, model_used = await process_chat_completion(
            db_session=session,
            session_id=session_id,
            user_prompt=chat_prompt,
            provider="ollama",
            model="qwen3:4b"
        )
        print("\n[Chat Assistant Response]:", flush=True)
        print(assistant_msg.content[:300] + "...\n", flush=True)
        print(f"Citations Returned: {len(citations)}", flush=True)
        for c in citations:
            print(f" - Episode: {c.episode_title} | Speaker: {c.speaker} | Score: {c.similarity_score:.4f}", flush=True)

    # 2. Test Ship 30 for 30 Essay Generation
    print("\n--- 2. Testing Ship 30 for 30 Essay Generation ---", flush=True)
    topic = "B2B SaaS Pricing Strategies and Value Metric Optimization"
    print(f"Essay Topic: '{topic}'", flush=True)

    async with AsyncSessionLocal() as session:
        artifact, essay_citations, essay_provider, essay_model = await generate_ship30_essay(
            db_session=session,
            session_id=session_id,
            topic=topic,
            output_format="markdown",
            provider="ollama",
            model="qwen3:4b"
        )

        word_count = len(artifact.content.split())
        byte_size = len(artifact.content.encode("utf-8"))

        print("\n[Generated Essay Artifact Summary]:", flush=True)
        print(f"Artifact ID:        {artifact.id}", flush=True)
        print(f"Artifact Title:     {artifact.title}", flush=True)
        print(f"Format:             {artifact.format}", flush=True)
        print(f"Provider Used:      {essay_provider}", flush=True)
        print(f"Model Used:         {essay_model}", flush=True)
        print(f"Actual Word Count:  {word_count} words", flush=True)
        print(f"Content Size:       {byte_size} bytes ({byte_size / 1024:.2f} KB)", flush=True)
        print(f"Citations Count:    {len(essay_citations)}", flush=True)

        print("\n[Essay Content Preview]:", flush=True)
        print(artifact.content[:400] + "...\n", flush=True)

    # 3. Cleanup test session
    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, session_id)
        if s_obj:
            await session.delete(s_obj)
            await session.commit()
            print("Cleaned up test session.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
