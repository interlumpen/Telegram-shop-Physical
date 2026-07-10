import asyncio
import logging

from bot.database.methods.inventory import cleanup_expired_reservations

logger = logging.getLogger(__name__)

# Strong reference to the long-lived cleaner task so it is not garbage-collected
# (asyncio only holds a weak reference to tasks).
_cleaner_task: "asyncio.Task | None" = None


async def run_reservation_cleaner():
    """
    Background task that runs continuously to cleanup expired reservations.
    Checks every 60 seconds for expired reservations and releases them.
    """
    logger.info("Reservation cleaner task started")

    while True:
        try:
            # Run cleanup
            count, order_codes = await cleanup_expired_reservations()

            if count > 0:
                logger.info(
                    f"Released {count} expired reservation(s): {', '.join(order_codes)}"
                )

            # Wait 60 seconds before next check
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Error in reservation cleaner task: {e}", exc_info=True)
            # Wait a bit longer on error to avoid spam
            await asyncio.sleep(120)


def start_reservation_cleaner():
    """
    Start the reservation cleaner task in the background.
    Call this function when the bot starts.
    """
    global _cleaner_task
    _cleaner_task = asyncio.create_task(run_reservation_cleaner())
    logger.info("Reservation cleaner task scheduled")
    return _cleaner_task
