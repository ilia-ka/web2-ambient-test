import requests


def get_verified_proof(api_url: str, api_key: str) -> None:
    headers = {
        "Authorization": f"Bearer {api_key}",
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
        response = requests.post(api_url, headers=headers, json=payload)
        data = response.json()
        merkle = data.get("merkle_root")
        print(f"Response received. Merkle Root: {merkle}")
    except Exception as e:
        print(f"Error: {e}")
