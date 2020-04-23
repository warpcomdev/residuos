"""API aggregator"""

import asyncio
import logging
from typing import Callable, Awaitable, Iterable, TypeVar
import aiohttp

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

    async def _consume(self, queue: asyncio.Queue, exc: asyncio.Queue, task):
        """Consume a coroutine from the queue"""
        while True:
            item = await queue.get()
            if item is None:
                # pass on the word that we're done, and exit
                await queue.put(None)
                break
            try:
                await task(self._session, item)
            # pylint: disable=broad-except
            except Exception as err:
                # abort
                await queue.put(None)
                await exc.put(err)

    async def serial(self, task: Callable[[aiohttp.ClientSession, T],
                                          Awaitable[None]],
                     items: Iterable[T]):
        """Call the coroutine once per item"""
        queue: asyncio.Queue = asyncio.Queue()
        exc: asyncio.Queue = asyncio.Queue()
        tasks = [
            asyncio.ensure_future(self._consume(queue, exc, task))
            for _ in range(self._pool_size)
        ]
        for item in items:
            if item is not None:
                await queue.put(item)
        await queue.put(None)
        await asyncio.gather(*tasks)
        if not exc.empty():
            raise await exc.get()

    async def chunked(self,
                      task: Callable[[aiohttp.ClientSession, Iterable[T]],
                                     Awaitable[None]], items: Iterable[T]):
        """Call the coroutine once per chunk"""
        csize = self._chunk_size
        fixed = tuple(items)
        chunk = (fixed[n:n + csize] for n in range(0, len(fixed), csize))
        await self.serial(task, chunk)
