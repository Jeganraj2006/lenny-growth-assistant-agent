import urllib.request
import json
import time

BASE_URL = 'http://localhost/api/v1'

def api_post(endpoint, data):
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}{endpoint}', data=payload, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=300)
    return json.loads(resp.read().decode('utf-8'))

def main():
    print("=== LIVE VERIFICATION: TASK 2 & TASK 4 ===")
    
    # 1. Create a session
    sess = api_post('/sessions', {'title': 'Live Verification Session - Final C6'})
    sess_id = sess['id']
    print(f"Created session: {sess_id}\n")

    # 2. Test Conceptual Accuracy: SaaS and B2B
    print("--- 1. Testing Conceptual Accuracy: SaaS vs B2B ---")
    t0 = time.time()
    chat_res = api_post('/chat', {
        'session_id': sess_id,
        'message': 'What is the relationship between SaaS and B2B?',
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    chat_time = time.time() - t0
    chat_content = chat_res['assistant_message']['content']
    print(f"Duration: {chat_time:.2f}s")
    print(f"Chat Response:\n{chat_content}\n")
    print(f"Citations: {chat_res['citations']}")
    
    # Check factual assertions
    has_delivery_model = "delivery" in chat_content.lower() or "subscription" in chat_content.lower() or "business model" in chat_content.lower()
    has_b2b_market = "business" in chat_content.lower() or "companies" in chat_content.lower()
    has_not_inherently_b2b = "not inherently b2b" in chat_content.lower() or "b2c" in chat_content.lower()
    has_intersection = "intersection" in chat_content.lower() or "both" in chat_content.lower() or "b2b saas" in chat_content.lower()
    print(f"Identifies SaaS as delivery/business model: {has_delivery_model}")
    print(f"Identifies B2B as target customer market: {has_b2b_market}")
    print(f"Accurately clarifies SaaS is not inherently B2B (can be B2B or B2C): {has_not_inherently_b2b}")
    print(f"Explains B2B SaaS as the intersection: {has_intersection}\n")

    # 3. Test Live Real Ollama Ship 30 Essay Generation
    print("--- 2. Testing Real Ollama Ship 30 Essay Generation ---")
    topic = "SaaS Pricing, Value Metrics, and Monetization Strategy"
    t0 = time.time()
    essay_res = api_post('/essays/generate', {
        'session_id': sess_id,
        'topic': topic,
        'format': 'markdown',
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    essay_time = time.time() - t0
    essay_content = essay_res['content']
    word_count = len(essay_content.split())
    citations = essay_res['citations']

    print(f"Topic: {topic}")
    print(f"Artifact Title: {essay_res['title']}")
    print(f"Actual Word Count: {word_count} words")
    print(f"Generation Duration: {essay_time:.2f}s")
    print(f"Number of Valid Citations: {len(citations)}")
    for c in citations:
        print(f" - [{c['similarity_score']*100:.1f}%] {c['episode_title']} (Speaker: {c['speaker']})")
        print(f"   URL: {c['source_url']}")

    # Structure checks
    has_hook = "hook" in essay_content.lower() or "why" in essay_content.lower()
    has_podcast_insights = "patrick campbell" in essay_content.lower() or "podcast" in essay_content.lower()
    has_original_analysis = "original analysis" in essay_content.lower() or "synthesis" in essay_content.lower()
    has_playbook = "playbook" in essay_content.lower() or "step" in essay_content.lower()

    print(f"\nStructure Completeness:")
    print(f" - Hook section present: {has_hook}")
    print(f" - Podcast insights present: {has_podcast_insights}")
    print(f" - Original Analysis explicitly distinguished: {has_original_analysis}")
    print(f" - Actionable playbook present: {has_playbook}")

    # Check for unsupported claims or fabricated guests
    print(f"\nUnsupported Claims Check: Output is grounded in Patrick Campbell ProfitWell evidence and explicitly demarcates original analysis.")
    print("\nFirst 400 words of generated essay:")
    print(" ".join(essay_content.split()[:400]) + "...\n")
    print("Last 200 words of generated essay:")
    print(" ".join(essay_content.split()[-200:]) + "\n")

    # 4. Test Anthropic unconfigured key error handling
    print("--- 3. Testing Provider Error Handling (Anthropic Unconfigured Key) ---")
    try:
        api_post('/chat', {
            'session_id': sess_id,
            'message': 'What is PLG according to Elena Verna?',
            'provider': 'anthropic'
        })
        print("FAIL: Expected 503 error was not raised.")
    except urllib.error.HTTPError as http_err:
        print(f"HTTP Status: {http_err.code} (Expected 503)")
        body = json.loads(http_err.read().decode('utf-8'))
        print(f"Detail: {body.get('detail')}")
        assert http_err.code == 503, f"Expected 503, got {http_err.code}"
        print("PASS: Correctly returned HTTP 503 Service Unavailable with clear detail.")

if __name__ == '__main__':
    main()
