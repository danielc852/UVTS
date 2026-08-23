import asyncio
from collections.abc import AsyncIterator

from redis.asyncio import Redis


class RedisStateNotifications:
    """Redis is a wake-up signal; subscribers always refetch durable database state."""

    def __init__(self, redis: Redis, *, heartbeat_seconds: float = 15.0) -> None:
        self._redis = redis
        self._heartbeat_seconds = heartbeat_seconds

    @staticmethod
    def _channel(test_id: str) -> str:
        return f"uvts:test:{test_id}"

    async def publish(self, test_id: str) -> None:
        await self._redis.publish(self._channel(test_id), "changed")

    async def listen(self, test_id: str) -> AsyncIterator[None]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self._channel(test_id))
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=self._heartbeat_seconds,
                )
                if message is not None:
                    yield None
                else:
                    # Heartbeats are intentionally yielded as refetch opportunities.
                    yield None
                await asyncio.sleep(0)
        finally:
            await pubsub.unsubscribe(self._channel(test_id))
            await pubsub.aclose()  # type: ignore[no-untyped-call]
