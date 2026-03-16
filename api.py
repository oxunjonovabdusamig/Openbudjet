import logging
import traceback
import json
import aiohttp
import asyncio
from config import API_URL, APP_ID

logger = logging.getLogger(__name__)

async def send_code(phone: str) -> dict:
    url = API_URL + "/vote/send-code/"
    payload = {"phone": phone, "application": APP_ID}
    logger.info("send_code request: %s", payload)
    try:
        async with aiohttp.ClientSession() as sess:
            resp = await sess.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            )
            text = await resp.text()
            logger.info("send_code response: status=%s body=%s", resp.status, text)
            try:
                return json.loads(text)
            except Exception:
                return {"raw": text}
    except aiohttp.ClientConnectorError as ex:
        logger.error("send_code connection error: %s", str(ex))
        return {"error": "Serverga ulanib bolmadi", "detail": str(ex)}
    except asyncio.TimeoutError:
        logger.error("send_code timeout!")
        return {"error": "Timeout - server javob bermadi"}
    except Exception as ex:
        logger.error("send_code unexpected: %s\n%s", str(ex), traceback.format_exc())
        return {"error": str(ex)}

async def confirm_vote(token: str, code: str) -> dict:
    url = API_URL + "/vote/confirm/"
    payload = {"token": token, "code": code}
    logger.info("confirm_vote request: %s", payload)
    try:
        async with aiohttp.ClientSession() as sess:
            resp = await sess.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            )
            text = await resp.text()
            logger.info("confirm_vote response: status=%s body=%s", resp.status, text)
            try:
                return json.loads(text)
            except Exception:
                return {"raw": text}
    except aiohttp.ClientConnectorError as ex:
        logger.error("confirm_vote connection error: %s", str(ex))
        return {"error": "Serverga ulanib bolmadi", "detail": str(ex)}
    except asyncio.TimeoutError:
        logger.error("confirm_vote timeout!")
        return {"error": "Timeout - server javob bermadi"}
    except Exception as ex:
        logger.error("confirm_vote unexpected: %s\n%s", str(ex), traceback.format_exc())
        return {"error": str(ex)}
