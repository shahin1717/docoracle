
import requests
import json

def test_citations():
    url = "http://localhost:11434/api/chat"
    model = "mistral:7b-instruct-q8_0"
    
    messages = [
        {"role": "system", "content": "You are a strict citation bot. Use [1] for every sentence. CONTEXT: [1] Time complexity is O(n)."},
        {"role": "user", "content": "What is time complexity?"}
    ]
    
    print(f"Testing model: {model}")
    response = requests.post(url, json={
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1}
    })
    
    result = response.json()
    print("\nAI RESPONSE:")
    print(result["message"]["content"])
    print("\n---")
    if "[" in result["message"]["content"]:
        print("✅ CITATIONS DETECTED!")
    else:
        print("❌ NO CITATIONS FOUND.")

if __name__ == "__main__":
    test_citations()
