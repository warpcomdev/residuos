"""Defines errors used by this package"""

from typing import Optional, Mapping, Any
import attr
import aiohttp


@attr.s(auto_attribs=True, auto_exc=True)
class ParseError(Exception):
    """Exception raised when config cannot be imported"""
    err: Exception
    obj: Mapping[str, Any]


@attr.s(auto_attribs=True, auto_exc=True)
class FetchError(Exception):
    """Error raised when Fetch fails"""
    url: str
    resp: aiohttp.ClientResponse
    headers: Optional[Mapping[str, str]] = None
    body: Optional[Mapping[str, Any]] = None
    params: Optional[Mapping[str, Any]] = None
