import requests
import time

PUMPFUN_URL = "https://pump.fun/api/token/{}"

def fetch_latest_tokens():
    try:
        res = requests.get("https://pump.fun/api/tokens")
        if res.status_code != 200:
            return []
        return res.json()
    except Exception:
        return []

def fetch_token_info(address):
    try:
        res = requests.get(PUMPFUN_URL.format(address))
        if res.status_code != 200:
            return None
        return res.json()
    except Exception:
        return None

def minutes_since(timestamp):
    return (time.time() - timestamp) / 60
