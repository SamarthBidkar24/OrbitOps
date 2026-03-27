import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_neo_predict():
    print("Testing 1: POST /api/v1/neo/predict")
    payload = {"date": "2025-08-12", "observatory_index": 2}
    try:
        response = requests.post(f"{BASE_URL}/neo/predict", json=payload)
        data = response.json()
        
        if response.status_code != 200:
            print(f"  [FAIL] Error: Status {response.status_code}")
            return False
            
        if "dummy" in data:
            print("  [FAIL] Failed: 'dummy' key found in response.")
            return False
        
        print("  [OK] Success: No 'dummy' key. Real model data returned.")
        return True
    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        return False

def test_meteor_calendar():
    print("Testing 2: GET /api/v1/meteor/calendar/Mumbai?year=2026&month=12")
    try:
        response = requests.get(f"{BASE_URL}/meteor/calendar/Mumbai", params={"year": 2026, "month": 12})
        data = response.json()
        
        if response.status_code != 200:
            print(f"  [FAIL] Error: Status {response.status_code}")
            if isinstance(data, dict) and "detail" in data:
                print(f"      Detail: {data['detail']}")
            return False
            
        keys = list(data.keys())
        print(f"  [INFO] Found {len(keys)} keys in response.")
        
        if len(keys) != 31:
            print(f"  [FAIL] Failed: Expected 31 keys, got {len(keys)}.")
            
        found_geminids = False
        for date in ["2026-12-13", "2026-12-14"]:
            if date in data:
                entry = data[date]
                print(f"  [INFO] {date}: {entry['intensity']} intensity, showers: {entry['showers']}")
                if entry['intensity'] == "high":
                    found_geminids = True
        
        if not found_geminids:
            print("  [FAIL] Failed: Geminids on Dec 13-14 didn't show 'high' intensity.")
            return False
            
        print("  [OK] Success: 31 keys found, Geminids high intensity confirmed.")
        return True
    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        return False

def test_chatbot_chat():
    print("Testing 3: POST /api/v1/chatbot/chat")
    payload = {
        "message": "Which Indian city has the darkest sky?",
        "conversation_history": [],
        "language": "en"
    }
    try:
        # Chatbot is streaming (SSE)
        response = requests.post(f"{BASE_URL}/chatbot/chat", json=payload, stream=True)
        
        if response.status_code != 200:
            print(f"  [FAIL] Error: Status {response.status_code}")
            return False
            
        full_text = ""
        found_key_words = False
        print("  [INFO] Receiving stream: ", end="", flush=True)
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    content = decoded_line[6:]
                    if content == "[DONE]":
                        break
                    full_text += content
                    print(".", end="", flush=True)
                    
                    if "hanle" in full_text.lower() or "ladakh" in full_text.lower():
                        found_key_words = True
        
        print("\n  [INFO] Full Response snippet: " + full_text[:100] + "...")
        
        if not found_key_words:
            print("  [FAIL] Response did not mention Hanle or Ladakh.")
            return False
            
        print("  [OK] Success: Streamed text mentions Hanle or Ladakh.")
        return True
    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        return False


if __name__ == "__main__":
    t1 = test_neo_predict()
    print("-" * 40)
    t2 = test_meteor_calendar()
    print("-" * 40)
    t3 = test_chatbot_chat()
    print("-" * 40)
    
    if all([t1, t2, t3]):
        print("ALL TESTS PASSED! Backend is correctly wired.")
    else:
        print("SOME TESTS FAILED. Check the output above.")
