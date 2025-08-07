import asyncio
import websockets
import json
import logging
from datetime import datetime

logger = logging.getLogger("pumpfun_api")

PUMP_WS_URL = "wss://pumpportal.fun/api/data"

# Возвращает, сколько минут назад был создан токен
def minutes_since(timestamp):
    if not timestamp:
        return 999
    dt = datetime.fromtimestamp(timestamp)
    diff = datetime.now() - dt
    return diff.total_seconds() / 60

# Асинхронная подписка на WebSocket Pump.fun
def listen_pumpfun_tokens(callback):
    async def listen():
        async for ws in websockets.connect(PUMP_WS_URL):
            try:
                logger.info("[PUMPFUN] Connected to WebSocket")
                async for message in ws:
                    try:
                        data = json.loads(message)
                        if isinstance(data, list):
                            logger.debug(f"[PUMPFUN] Received batch with {len(data)} tokens")
                            await callback(data)
                    except Exception as e:
                        logger.error(f"[PUMPFUN] Error parsing message: {e}")
            except websockets.exceptions.ConnectionClosed:
                logger.warning("[PUMPFUN] WebSocket closed, reconnecting...")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"[PUMPFUN] Connection error: {e}")
                await asyncio.sleep(5)

    return listen
