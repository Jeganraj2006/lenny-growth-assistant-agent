import urllib.request
import json
import time
import sys

BASE_URL = 'http://localhost/api/v1'

def api_post(endpoint, data):
    payload = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(f'{BASE_URL}{endpoint}', data=payload, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=180)
    return json.loads(resp.read().decode('utf-8'))

def api_get(endpoint):
    req = urllib.request.Request(f'{BASE_URL}{endpoint}')
    resp = urllib.request.urlopen(req, timeout=180)
    return json.loads(resp.read().decode('utf-8'))

def main():
    print("Starting Task 5 Quality Acceptance Tests...")
    
    # 1. Create a session
    sess = api_post('/sessions', {'title': 'Quality Acceptance Evaluation Session'})
    sess_id = sess['id']
    print(f"Session created: {sess_id}\n")

    # TEST 1: Greeting
    print("--------------------------------------------------")
    print("TEST 1: 'hi' (Conversational Greeting)")
    t0 = time.time()
    res1 = api_post('/chat', {
        'session_id': sess_id,
        'message': 'hi',
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    elapsed1 = time.time() - t0
    ans1 = res1['assistant_message']['content']
    cits1 = res1['citations']
    print(f"Latency: {elapsed1:.2f}s")
    print(f"Model Answer: {ans1}")
    print(f"Citations Count: {len(cits1)}")
    pass1 = ("hello" in ans1.lower() or "lenny" in ans1.lower()) and len(cits1) == 0
    print(f"Result: {'PASS' if pass1 else 'FAIL'}")

    # TEST 2: Patrick Campbell on SaaS pricing
    print("\n--------------------------------------------------")
    print("TEST 2: 'What is Patrick Campbell advice on SaaS pricing?'")
    t0 = time.time()
    res2 = api_post('/chat', {
        'session_id': sess_id,
        'message': "What is Patrick Campbell's advice on SaaS pricing?",
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    elapsed2 = time.time() - t0
    ans2 = res2['assistant_message']['content']
    cits2 = res2['citations']
    print(f"Latency: {elapsed2:.2f}s")
    print(f"Model Answer: {ans2}")
    print(f"Citations Count: {len(cits2)}")
    for c in cits2:
        print(f" - [{c['similarity_score']*100:.1f}%] {c['episode_title']} (Speaker: {c['speaker']})")
        print(f"   URL: {c['source_url']}")
        print(f"   Excerpt: {c['excerpt'][:120]}...")
    pass2 = ("value metric" in ans2.lower() or "seat" in ans2.lower() or "pricing" in ans2.lower()) and len(cits2) > 0 and "Patrick Campbell" in cits2[0]['speaker']
    print(f"Result: {'PASS' if pass2 else 'FAIL'}")

    # TEST 3: Shreyas Doshi LNO framework
    print("\n--------------------------------------------------")
    print("TEST 3: 'What is the LNO framework according to Shreyas Doshi?'")
    t0 = time.time()
    res3 = api_post('/chat', {
        'session_id': sess_id,
        'message': "What is the LNO framework according to Shreyas Doshi?",
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    elapsed3 = time.time() - t0
    ans3 = res3['assistant_message']['content']
    cits3 = res3['citations']
    print(f"Latency: {elapsed3:.2f}s")
    print(f"Model Answer: {ans3}")
    print(f"Citations Count: {len(cits3)}")
    for c in cits3:
        print(f" - [{c['similarity_score']*100:.1f}%] {c['episode_title']} (Speaker: {c['speaker']})")
    pass3 = ("leverage" in ans3.lower() and "neutral" in ans3.lower() and "overhead" in ans3.lower()) and len(cits3) > 0 and "Shreyas Doshi" in cits3[0]['speaker']
    print(f"Result: {'PASS' if pass3 else 'FAIL'}")

    # TEST 4: SaaS and B2B relationship
    print("\n--------------------------------------------------")
    print("TEST 4: 'What is the relationship between SaaS and B2B?'")
    t0 = time.time()
    res4 = api_post('/chat', {
        'session_id': sess_id,
        'message': "What is the relationship between SaaS and B2B?",
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    elapsed4 = time.time() - t0
    ans4 = res4['assistant_message']['content']
    cits4 = res4['citations']
    print(f"Latency: {elapsed4:.2f}s")
    print(f"Model Answer: {ans4}")
    print(f"Citations Count: {len(cits4)}")
    for c in cits4:
        print(f" - [{c['similarity_score']*100:.1f}%] {c['episode_title']} (Speaker: {c['speaker']})")
    pass4 = len(ans4) > 50 and ("b2b" in ans4.lower() or "saas" in ans4.lower())
    print(f"Result: {'PASS' if pass4 else 'FAIL'}")

    # TEST 5: Out of domain / Quantum computer
    print("\n--------------------------------------------------")
    print("TEST 5: 'How do I build a quantum computer?' (Irrelevant Fallback)")
    t0 = time.time()
    res5 = api_post('/chat', {
        'session_id': sess_id,
        'message': "How do I build a quantum computer?",
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    elapsed5 = time.time() - t0
    ans5 = res5['assistant_message']['content']
    cits5 = res5['citations']
    print(f"Latency: {elapsed5:.2f}s")
    print(f"Model Answer: {ans5}")
    print(f"Citations Count: {len(cits5)}")
    pass5 = any(marker in ans5.lower() for marker in ["insufficient evidence", "not contain sufficient", "not contain relevant", "no evidence"]) and len(cits5) == 0
    print(f"Result: {'PASS' if pass5 else 'FAIL'}")

    # TEST 6: Follow-up question in existing session (conversational continuity)
    print("\n--------------------------------------------------")
    print("TEST 6: Follow-up question in existing session")
    t0 = time.time()
    res6 = api_post('/chat', {
        'session_id': sess_id,
        'message': "What did Patrick Campbell say about involuntary churn and failed credit cards?",
        'provider': 'ollama',
        'model': 'llama3.2:3b'
    })
    elapsed6 = time.time() - t0
    ans6 = res6['assistant_message']['content']
    cits6 = res6['citations']
    print(f"Latency: {elapsed6:.2f}s")
    print(f"Model Answer: {ans6}")
    print(f"Citations Count: {len(cits6)}")
    pass6 = ("involuntary" in ans6.lower() or "churn" in ans6.lower() or "credit card" in ans6.lower()) and len(cits6) > 0
    print(f"Result: {'PASS' if pass6 else 'FAIL'}")

    # TEST 7: Message list duplication check upon session retrieval
    print("\n--------------------------------------------------")
    print("TEST 7: Session message retrieval and duplicate check")
    msg_res = api_get(f'/sessions/{sess_id}/messages')
    all_msgs = msg_res['messages']
    total_msgs = len(all_msgs)
    msg_ids = [m['id'] for m in all_msgs]
    unique_ids = set(msg_ids)
    print(f"Total messages returned: {total_msgs}")
    print(f"Unique message IDs: {len(unique_ids)}")
    pass7 = (total_msgs == 12) and (len(unique_ids) == 12)
    print(f"Result: {'PASS' if pass7 else 'FAIL'} (Expected 12 unique messages across 6 prompt-response turns)")

    print("\n==================================================")
    print("QUALITY ACCEPTANCE SUITE SUMMARY:")
    print(f"Test 1 (Greeting): {'PASS' if pass1 else 'FAIL'}")
    print(f"Test 2 (Patrick Campbell Pricing): {'PASS' if pass2 else 'FAIL'}")
    print(f"Test 3 (Shreyas Doshi LNO): {'PASS' if pass3 else 'FAIL'}")
    print(f"Test 4 (SaaS & B2B Concept): {'PASS' if pass4 else 'FAIL'}")
    print(f"Test 5 (Quantum Computer Fallback): {'PASS' if pass5 else 'FAIL'}")
    print(f"Test 6 (Follow-up Continuity): {'PASS' if pass6 else 'FAIL'}")
    print(f"Test 7 (Session Deduplication): {'PASS' if pass7 else 'FAIL'}")
    print("==================================================")

if __name__ == '__main__':
    main()
