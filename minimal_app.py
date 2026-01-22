import asyncio
import sys
import logging
import signal
import traceback

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try different event loop policies
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Using WindowsProactorEventLoopPolicy")
    except AttributeError:
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Using WindowsSelectorEventLoopPolicy")
        except AttributeError:
            logger.info("No Windows-specific event loop policy available")

from fastapi import FastAPI, Request

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request started: {request.method} {request.url}")
    try:
        response = await call_next(request)
        logger.info(f"Request completed: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.get("/test")
def test():
    logger.info("Test endpoint called")
    return {"status": "ok"}

@app.get("/health")
def health():
    logger.info("Health endpoint called")
    return {"status": "healthy", "version": "1.0.0"}

# Signal handlers
def signal_handler(signum, frame):
    logger.info(f"Signal {signum} received")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)