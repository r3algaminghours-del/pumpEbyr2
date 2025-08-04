import requests
import time

BASE_URL = "https://api.raylaunch.app/api/launchpad/recent"

def fetch_raylaunch_tokens():
    try:
        res = requests.get(BASE_URL)
        if res.status_code != 200:
            return []
        data = res.json()
        return data.get("tokens", [])
    except Exception:
        return []

def minutes_since(timestamp):
    return (time.time() - timestamp) / 60
