import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Exception in request: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.get("/test")
def test():
    logger.info("Test endpoint called")
    try:
        result = {"status": "ok", "message": "Test endpoint working"}
        logger.info(f"Returning: {result}")
        return result
    except Exception as e:
        logger.error(f"Exception in test endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise