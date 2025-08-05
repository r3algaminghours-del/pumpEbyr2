import logging
import requests

RAYLAUNCH_API_URL = "https://api.raylaunch.xyz/tokens"

def get_new_raylaunch_tokens():
    try:
        response = requests.get(RAYLAUNCH_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        logging.info(f"[RAYLAUNCH_API] Response: {type(data)} - {len(data)} items")

        new_tokens = []
        for token in data:
            # пример фильтрации — можно адаптировать
            if token.get("is_new", False):
                new_tokens.append(token.get("name", "UnnamedToken"))

        return new_tokens

    except Exception as e:
        logging.error(f"[RAYLAUNCH_API] Error: {e}")
        return []
