import asyncio
from typing import Coroutine, Any, Set

# Hold strong references to in-flight tasks. asyncio only keeps a weak reference
# to tasks, so a fire-and-forget task can be garbage-collected mid-run without
# this set. Tasks remove themselves on completion.
_background_tasks: Set[asyncio.Task] = set()


def safe_create_task(coro: Coroutine[Any, Any, None]) -> None:
    """
    Safely create an async task for cache invalidation.
    Works both in async context (with event loop) and sync context (tests).
    """
    try:
        # Try to get the running event loop
        loop = asyncio.get_running_loop()
        # If we have a loop, create task and keep a strong reference to it.
        task = loop.create_task(coro)
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        # No event loop running (probably in tests)
        # Run the coroutine in a new event loop
        try:
            asyncio.run(coro)
        except RuntimeError:
            # If asyncio.run() also fails (nested event loop), just ignore
            # This is fire-and-forget for cache invalidation anyway
            pass
