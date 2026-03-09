"""Background scheduler for re-engagement jobs.

Runs as a separate process (see docker-compose.yml).
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import AsyncSessionLocal
from app.services.reengagement_service import process_reengagement
from app.telegram.bot import send_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reengagement_job():
    logger.info("Running re-engagement job...")
    async with AsyncSessionLocal() as db:
        await process_reengagement(db, send_message)
    logger.info("Re-engagement job complete.")


async def main():
    scheduler = AsyncIOScheduler()
    # Run re-engagement check every 30 minutes
    scheduler.add_job(reengagement_job, "interval", minutes=30, id="reengagement")
    scheduler.start()

    logger.info("Scheduler started. Running re-engagement every 30 minutes.")

    try:
        # Keep running indefinitely
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
