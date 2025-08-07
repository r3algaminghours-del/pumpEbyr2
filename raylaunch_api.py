import logging
import os
import requests
import time
from datetime import datetime

BITQUERY_URL = "https://graphql.bitquery.io/"
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY", "ory_at_z5nmCYRkee-7v2ZeBSd5NOoKrts0xnxxFAlp1gH6jBo.CfZTkZhqz5bvFNw5lS7wSiHhjYoTFEwrJZdNpv3LZ3o")

def minutes_since(timestamp):
    if not timestamp:
        return 999
    dt = datetime.fromtimestamp(timestamp)
    diff = datetime.now() - dt
    return diff.total_seconds() / 60

def fetch_raylaunch_tokens():
    if not BITQUERY_API_KEY:
        logging.warning("[RAYLAUNCH_API] Bitquery API Key not set, skipping")
        return []

    query = """
    {
      Solana(network: solana) {
        Instructions(
          where: {
            Instruction: {
              Program: { Address: { is: "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj" },
                         Method: { is: "PoolCreateEvent" } }
            }
          }
          limit: {count: 5}
          orderBy: { descending: Block_Time }
        ) {
          Block_Time
          Instruction {
            Arguments {
              Value {
                ... on Solana_ABI_Address_Value_Arg {
                  address
                }
              }
            }
          }
        }
      }
    }
    """

    try:
        response = requests.post(BITQUERY_URL, json={'query': query}, headers={
            "X-API-KEY": BITQUERY_API_KEY
        }, timeout=10)
        response.raise_for_status()
        result = response.json()
        items = result.get("data", {}).get("Solana", {}).get("Instructions", [])
        tokens = []
        for inst in items:
            block_time_str = inst.get("Block_Time")  # ISO8601 string like '2023-08-01T12:34:56'
            created_at_ts = None
            if block_time_str:
                try:
                    dt = datetime.fromisoformat(block_time_str.replace('Z', '+00:00'))
                    created_at_ts = dt.timestamp()
                except Exception:
                    created_at_ts = time.time()

            args = inst.get("Instruction", {}).get("Arguments", [])
            for arg in args:
                val = arg.get("Value", {})
                address = val.get("address")
                if address:
                    # Возвращаем словарь с данными, чтобы main.py мог работать
                    tokens.append({
                        "address": address,
                        "created_at": created_at_ts or time.time(),
                        "market_cap": 0,
                        "name": "Unknown",
                        "symbol": "???",
                        "holders": 0,
                        "dev_hold": 0,
                        "volume": 0,
                        "inflow": 0,
                        "url": f"https://raydium.io/launchpad/{address}"
                    })
        logging.info(f"[RAYLAUNCH_API] Raydium Launchpad tokens fetched: {len(tokens)}")
        return tokens
    except Exception as e:
        logging.error(f"[RAYLAUNCH_API] Error: {e}")
        return []


