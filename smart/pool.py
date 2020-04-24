"""API aggregator"""

import asyncio
from typing import Callable, Awaitable, Iterable, Sequence, TypeVar
import aiohttp

from .api import gather

# Default pool and chunk size
CHUNK_SIZE = 8
POOL_SIZE = 8
# pylint: disable=invalid-name
T = TypeVar('T')


class Pool:
    """Pool is a naive asyncio / aiohttp task pool"""
    def __init__(self,
                 session: aiohttp.ClientSession,
                 pool_size=POOL_SIZE,
                 chunk_size=CHUNK_SIZE):
        self._session = session
        self._chunk_size = chunk_size
        self._pool_size = pool_size

    async def _consume(self, queue: asyncio.Queue, task):
        """Consume a coroutine from the queue"""
        while True:
            item = await queue.get()
            if item is None:
                # pass on the word that we're done, and exit
                await queue.put(None)
                return None
            try:
                await task(self._session, item)
            # pylint: disable=broad-except
            except Exception as err:
                # abort
                await queue.put(None)
                return err

    async def amap(self, task: Callable[[aiohttp.ClientSession, T],
                                        Awaitable[None]], items: Iterable[T]):
        """Asynchronously map the coroutine once per item"""
        queue: asyncio.Queue = asyncio.Queue()
        tasks = [
            asyncio.ensure_future(self._consume(queue, task))
            for _ in range(self._pool_size)
        ]
        for item in items:
            if item is not None:
                await queue.put(item)
        await queue.put(None)
        await gather(*tasks)

    async def batch(self, task: Callable[[aiohttp.ClientSession, Sequence[T]],
                                         Awaitable[None]], items: Iterable[T]):
        """Map the coroutine on batches of Call the coroutine once per chunk"""
        csize = self._chunk_size
        fixed = tuple(items)
        chunk = (fixed[n:n + csize] for n in range(0, len(fixed), csize))
        await self.amap(task, chunk)
