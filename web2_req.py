import requests

API_URL = "https://api.ambient.xyz/v1/chat/completions"
API_KEY = "api"

def get_verified_proof():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "large",
        "messages": [
            {"role": "user", "content": "What is Ambient Network on Solana?"}
        ],
        "emit_verified": True,
        "wait_for_verification": True
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        data = response.json()
        merkle = data.get('merkle_root')
        print(f"Response received. Merkle Root: {merkle}")
    except Exception as e:
        print(f"Error: {e}")
if __name__ == "__main__":
    get_verified_proof()
