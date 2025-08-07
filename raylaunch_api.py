import logging
import os
import requests

BITQUERY_URL = "https://graphql.bitquery.io/"
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY", "")

def get_new_raylaunch_tokens():
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
            args = inst.get("Instruction", {}).get("Arguments", [])
            for arg in args:
                val = arg.get("Value", {})
                address = val.get("address")
                if address:
                    tokens.append(address)
        logging.info(f"[RAYLAUNCH_API] Raydium Launchpad pool tokens fetched: {tokens}")
        return tokens
    except Exception as e:
        logging.error(f"[RAYLAUNCH_API] Error: {e}")
        return []
