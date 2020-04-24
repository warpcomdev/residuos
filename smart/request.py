"""Provide helper wrappers for aiohttp"""

import logging
from typing import Optional, Sequence, Mapping, Dict, Callable, Any

import attr
import aiohttp

from .error import FetchError


@attr.s(auto_attribs=True)
class Request:
    """Encapsulates an aiohttp request"""
    title: str
    session: aiohttp.ClientSession
    url: str
    headers: Dict[str, str]
    args: Sequence[Any] = attr.Factory(tuple)
    params: Optional[Mapping[str, str]] = None
    body: Optional[Mapping[str, Any]] = None

    async def _do(self, action: Any,
                  success: Callable[[int], bool]) -> aiohttp.ClientResponse:
        """Perform a session request"""
        #pylint: disable=not-an-iterable
        logging.debug("Start " + self.title, *self.args)
        if self.body is not None:
            self.headers['Content-type'] = 'application/json'
        response = await action(self.url,
                                headers=self.headers,
                                json=self.body,
                                params=self.params)
        status = response.status
        if not success(status):
            raise FetchError(self.url,
                             response,
                             headers=self.headers,
                             body=self.body,
                             params=self.params)
        #pylint: disable=not-an-iterable
        logging.debug("Complete " + self.title + ". Status: %d", *self.args,
                      status)
        return response

    async def post(self, success: Callable[[int], bool]):
        """Post message"""
        return await self._do(action=self.session.post, success=success)

    async def delete(self, success: Callable[[int], bool]):
        """Delete message"""
        return await self._do(action=self.session.delete, success=success)
