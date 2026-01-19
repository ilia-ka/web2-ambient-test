from ambient_client.config import get_config
from ambient_client.web2_req import get_verified_proof


def main() -> None:
    config = get_config()
    if not config:
        return
    api_url, api_key = config
    get_verified_proof(api_url, api_key)


if __name__ == "__main__":
    main()
