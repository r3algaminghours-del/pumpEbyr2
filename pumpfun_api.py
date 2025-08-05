import logging
import requests

PUMPFUN_API_URL = "https://pump.fun/api/tokens"

def get_new_pumpfun_tokens():
    try:
        response = requests.get(PUMPFUN_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        logging.info(f"[PUMPFUN_API] Response: {type(data)} - {len(data)} items")

        new_tokens = []
        for token in data:
            # пример фильтрации — можно адаптировать
            if token.get("is_new", False):
                new_tokens.append(token.get("name", "UnnamedToken"))

        return new_tokens

    except Exception as e:
        logging.error(f"[PUMPFUN_API] Error: {e}")
        return []
