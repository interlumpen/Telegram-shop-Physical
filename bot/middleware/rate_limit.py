import time
from typing import Dict, Any, Callable, Awaitable
from collections import defaultdict
from dataclasses import dataclass, field

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.exceptions import TelegramBadRequest

from bot.i18n import localize


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    # Global limits
    global_limit: int = 30  # requests
    global_window: int = 60  # seconds

    # Limits for specific actions
    action_limits: dict = field(default_factory=lambda: {
        'broadcast': (1, 3600),  # 1 time per hour
        'shop_view': (60, 60),  # 60 times per minute
        'admin_action': (30, 60),  # 30 times a minute
        'buy_item': (5, 60),  # 5 buys a minute
    })

    # Temporary ban after exceeding
    ban_duration: int = 300  # 5 minutes

    # Exceptions for admins
    admin_bypass: bool = True


class RateLimiter:
    """A repository for tracking rate limits"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.user_requests: Dict[int, list] = defaultdict(list)
        self.user_actions: Dict[str, Dict[int, list]] = defaultdict(lambda: defaultdict(list))
        self.banned_users: Dict[int, float] = {}
        self._last_prune = time.time()
        # How often to sweep idle users out of the tracking dicts (seconds).
        self._prune_interval = 300

    def _clean_old_requests(self, requests: list, window: int) -> list:
        """Clears old requests outside the window"""
        current_time = time.time()
        return [req_time for req_time in requests if current_time - req_time < window]

    def prune(self) -> None:
        """Drop idle users from the tracking dicts to bound memory usage.

        Without this, every user that ever touched the bot keeps an entry in
        user_requests / user_actions forever (unbounded growth / memory leak).
        """
        now = time.time()
        if now - self._last_prune < self._prune_interval:
            return
        self._last_prune = now

        # Global request windows
        for user_id in list(self.user_requests.keys()):
            fresh = self._clean_old_requests(self.user_requests[user_id], self.config.global_window)
            if fresh:
                self.user_requests[user_id] = fresh
            else:
                del self.user_requests[user_id]

        # Per-action windows
        for action in list(self.user_actions.keys()):
            _, window = self.config.action_limits.get(action, (0, self.config.global_window))
            per_user = self.user_actions[action]
            for user_id in list(per_user.keys()):
                fresh = self._clean_old_requests(per_user[user_id], window)
                if fresh:
                    per_user[user_id] = fresh
                else:
                    del per_user[user_id]
            if not per_user:
                del self.user_actions[action]

        # Expired bans
        for user_id in list(self.banned_users.keys()):
            if now - self.banned_users[user_id] > self.config.ban_duration:
                del self.banned_users[user_id]

    def is_banned(self, user_id: int) -> bool:
        """Checks if the user is banned"""
        if user_id not in self.banned_users:
            return False

        ban_time = self.banned_users[user_id]
        if time.time() - ban_time > self.config.ban_duration:
            del self.banned_users[user_id]
            return False

        return True

    def ban_user(self, user_id: int):
        """Bans the user for a period of time"""
        self.banned_users[user_id] = time.time()

    def check_global_limit(self, user_id: int) -> bool:
        """Checks the global request limit"""
        current_time = time.time()

        # Clearing old requests
        self.user_requests[user_id] = self._clean_old_requests(
            self.user_requests[user_id],
            self.config.global_window
        )

        # Checking the limit
        if len(self.user_requests[user_id]) >= self.config.global_limit:
            return False

        # Add the current query
        self.user_requests[user_id].append(current_time)
        return True

    def check_action_limit(self, user_id: int, action: str) -> bool:
        """Checks the limit for a specific action"""
        if action not in self.config.action_limits:
            return True

        limit, window = self.config.action_limits[action]
        current_time = time.time()

        # Clear old requests for this action
        self.user_actions[action][user_id] = self._clean_old_requests(
            self.user_actions[action][user_id],
            window
        )

        # Checking the limit
        if len(self.user_actions[action][user_id]) >= limit:
            return False

        # Add the current query
        self.user_actions[action][user_id].append(current_time)
        return True

    def get_wait_time(self, user_id: int, action: str = None) -> int:
        """Returns the wait time until the next available request"""
        if self.is_banned(user_id):
            ban_time = self.banned_users[user_id]
            return int(self.config.ban_duration - (time.time() - ban_time))

        if action and action in self.config.action_limits:
            limit, window = self.config.action_limits[action]
            # Read-only access: don't materialize empty defaultdict entries here.
            requests = self.user_actions.get(action, {}).get(user_id, [])
            if len(requests) >= limit:
                oldest_request = min(requests)
                return int(window - (time.time() - oldest_request))

        # Global limit
        global_requests = self.user_requests.get(user_id, [])
        if len(global_requests) >= self.config.global_limit:
            oldest_request = min(global_requests)
            return int(self.config.global_window - (time.time() - oldest_request))

        return 0


class RateLimitMiddleware(BaseMiddleware):
    """Middleware to limit the frequency of requests"""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.limiter = RateLimiter(self.config)
        self.action_mapping = {
            # Callback data prefix -> action name.
            # Order placement in this physical shop happens at checkout_cart /
            # payment_method_* (not the digital shop's "buy_"), so those are what
            # the purchase limit must throttle.
            'broadcast': 'broadcast',
            'send_message': 'broadcast',
            'checkout_cart': 'buy_item',
            'payment_method_': 'buy_item',
            'shop': 'shop_view',
            'category_': 'shop_view',
            'item_': 'shop_view',
            'add_to_cart_': 'shop_view',
            'view_cart': 'shop_view',
            'console': 'admin_action',
            'admin': 'admin_action',
        }

    def _get_action_from_event(self, event: TelegramObject) -> str:
        """Determines the action from the event"""
        if isinstance(event, CallbackQuery):
            data = event.data or ""
            for prefix, action in self.action_mapping.items():
                if data.startswith(prefix):
                    return action

        elif isinstance(event, Message):
            text = event.text or ""
            if text.startswith('/start'):
                return 'shop_view'
            elif text.startswith('/'):
                return 'admin_action'

        return 'default'

    async def _check_admin_bypass(self, user_id: int) -> bool:
        """Checks if the user has any administrative permission (non-blocking)."""
        if not self.config.admin_bypass:
            return False

        try:
            from bot.database.methods import check_role, run_db
            from bot.database.models.main import Permission
            # Offload the sync DB read so we never block the event loop here.
            perms = await run_db(check_role, user_id)
            admin_mask = (
                Permission.BROADCAST | Permission.SETTINGS_MANAGE | Permission.USERS_MANAGE
                | Permission.SHOP_MANAGE | Permission.ADMINS_MANAGE | Permission.OWN
            )
            return bool(perms & admin_mask)
        except Exception:
            return False

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        """Basic middleware logic"""

        # Define the user
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user:
            return await handler(event, data)

        user_id = user.id

        # Periodically sweep idle users out of the tracking dicts (bounded memory).
        self.limiter.prune()

        # Checking the ban
        if self.limiter.is_banned(user_id):
            wait_time = self.limiter.get_wait_time(user_id)

            if isinstance(event, CallbackQuery):
                await event.answer(
                    localize("middleware.ban", time=wait_time),
                    show_alert=True
                )
                return None
            elif isinstance(event, Message):
                await event.answer(
                    localize("middleware.ban", time=wait_time)
                )
                return None

        # Check bypass for admins
        if await self._check_admin_bypass(user_id):
            return await handler(event, data)

        # Define action
        action = self._get_action_from_event(event)

        # Checking the limits
        if not self.limiter.check_global_limit(user_id):
            self.limiter.ban_user(user_id)

            if isinstance(event, CallbackQuery):
                await event.answer(
                    localize("middleware.above_limits"),
                    show_alert=True
                )
            elif isinstance(event, Message):
                await event.answer(localize("middleware.above_limits"))
            return None

        if not self.limiter.check_action_limit(user_id, action):
            wait_time = self.limiter.get_wait_time(user_id, action)

            if isinstance(event, CallbackQuery):
                await event.answer(
                    localize("middleware.waiting", time=wait_time),
                    show_alert=True
                )
            elif isinstance(event, Message):
                try:
                    await event.answer(localize("middleware.waiting", time=wait_time))
                except TelegramBadRequest as e:
                    # Ignore message sending errors (deleted chat, etc.)
                    pass
            return None

        # skip ahead
        return await handler(event, data)


# Function for quick setup
def setup_rate_limiting(dp, config: RateLimitConfig = None):
    """Connects rate limiting to the dispatcher"""
    middleware = RateLimitMiddleware(config)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)
    return middleware
