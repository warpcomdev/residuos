"""API aggregator"""

import json
import logging
from typing import Sequence, Iterable, Mapping, Tuple, Optional, Any
import attr
import aiohttp
from aiostream import stream, pipe, async_

from .error import FetchError
from .attrib import Attrib
from .factory import AttribList
from .group import Group
from .entity import Entity

# Number of entities / groups created per request
CHUNK_SIZE = 8


async def gather(*awaitables):
    """Portable version of asyncio.gather based on aiostream"""
    #pylint: disable=no-member
    await (stream.iterate(awaitables) | pipe.map(async_(lambda task: task)))


@attr.s(auto_attribs=True)
class Api:
    """Api manager for connecting to the IOTAgents"""
    url_keystone: str
    url_cb: str
    url_iotagent: str
    service: str
    subservice: str
    username: str
    password: str
    token: Optional[str] = None

    def __attrs_post_init__(self):
        """Logs API creation"""
        logging.debug(
            "Api object created: %s",
            attr.asdict(self, filter=(lambda a, v: a.name != "password")))

    async def auth(self, session: aiohttp.ClientSession):
        """Get an authentication token"""
        logging.debug("Getting authentication token")
        request = {
            "auth": {
                "scope": {
                    "project": {
                        "domain": {
                            "name": self.service
                        },
                        "name": self.subservice
                    }
                },
                "identity": {
                    "password": {
                        "user": {
                            "domain": {
                                "name": self.service
                            },
                            "password": self.password,
                            "name": self.username
                        }
                    },
                    "methods": ["password"]
                }
            }
        }
        url = f'{self.url_keystone}/v3/auth/tokens'
        resp = await session.post(url, json=request)
        if resp.status < 200 or resp.status > 204:
            raise FetchError(url, resp, json=request)
        logging.debug("Authentication ok")
        self.token = resp.headers['X-Subject-Token']

    async def _create_iota(self, session: aiohttp.ClientSession, kind: str,
                           sequence: Iterable[AttribList]):
        """Create a sequence of entities using the IoTA API"""
        assert self.token is not None
        url = f'{self.url_iotagent}/iot/{kind}'
        headers = {
            'Fiware-Service': self.service,
            'Fiware-ServicePath': self.subservice,
            'X-Auth-Token': self.token,
            'Content-Type': 'application/json',
        }

        data = {kind: tuple(item.asdict() for item in sequence)}
        keys = ", ".join(item.key() for item in sequence)
        logging.debug("Creating IOTA %s keys %s", kind, keys)
        resp = await session.post(url, headers=headers, json=data)
        if resp.status != 201:
            raise FetchError(url, resp, headers=headers, json=data)
        logging.debug("IOTA %s keys %s created with code %d", kind, keys,
                      resp.status)

    async def _create_cb(self, session: aiohttp.ClientSession,
                         sequence: Iterable[AttribList]):
        """Create a sequence of entities using the CB API"""
        assert self.token is not None
        url = f'{self.url_cb}/v2/op/update'
        headers = {
            'Fiware-Service': self.service,
            'Fiware-ServicePath': self.subservice,
            'X-Auth-Token': self.token,
            'Content-Type': 'application/json',
        }

        def cb_entity(attrib: Attrib) -> Mapping[str, Any]:
            """Turns an attrib into an entity suitable for the CB"""
            data = {
                'id': attrib.device_id,
                'type': attrib.entity_type,
            }
            for current in attrib.static_attributes:
                data[current.name] = {
                    'type': current.type,
                    'value': current.value,
                }
            return data

        data = {
            'actionType': 'APPEND',
            'entities': list(cb_entity(item) for item in sequence)
        }
        keys = ", ".join(item.key() for item in sequence)
        logging.debug("Creating CB entities keys %s", keys)
        resp = await session.post(url, headers=headers, json=data)
        if resp.status != 204:
            raise FetchError(url, resp, headers=headers, json=data)
        logging.debug("CB entities keys %s created with code %d", keys, resp.status)

    async def create_groups(self,
                            session: aiohttp.ClientSession,
                            groups: Sequence[Group],
                            chunk_size=CHUNK_SIZE):
        """Create the groups using the API"""
        async def iota(groups: Sequence[Group]):
            await self._create_iota(session, 'services', groups)

        # pylint: disable=no-member
        await (stream.iterate(groups) | pipe.chunks(chunk_size)
               | pipe.map(iota))

    async def create_entities(self,
                              session: aiohttp.ClientSession,
                              entities: Sequence[Entity],
                              chunk_size=CHUNK_SIZE):
        """Create the groups using the API"""

        # Only send to IOTA those entities that have at least one attribute
        async def iota(entities: Sequence[Entity]):
            await self._create_iota(session, 'devices', entities)

        async def ctxb(entities: Sequence[Entity]):
            await self._create_cb(session, entities)

        # pylint: disable=no-member
        await gather(
            stream.iterate(entity for entity in entities if entity.attributes)
            | pipe.chunks(chunk_size) | pipe.map(iota),
            stream.iterate(entity
                           for entity in entities if not entity.attributes)
            | pipe.chunks(chunk_size) | pipe.map(ctxb))

    async def _delete(self, session: aiohttp.ClientSession,
                      items: Iterable[Tuple[str, Mapping[str, Any]]]):
        """Delete the groups using the API"""
        assert self.token is not None
        headers = {
            'Fiware-Service': self.service,
            'Fiware-ServicePath': self.subservice,
            'X-Auth-Token': self.token,
        }

        async def delete(url: str, params: Mapping[str, Any]):
            """Delete a group given its apikey"""
            logging.debug("Deleting entity with URL %s and Params %s", url,
                          json.dumps(params))
            resp = await session.delete(url, headers=headers, params=params)
            if (resp.status < 200 or resp.status > 204) and resp.status != 404:
                raise FetchError(url, resp, headers=headers, json=params)
            logging.debug("Entity %s deleted with code %d", url, resp.status)

        # pylint: disable=no-member
        await (stream.iterate(items) | pipe.starmap(delete))

    async def delete_groups(self, session: aiohttp.ClientSession,
                            groups: Sequence[Group]):
        """Delete the groups using the API"""
        url = f'{self.url_iotagent}/iot/services'
        pairs = ((url, {
            'apikey': group.apikey,
            'protocol': protocol
        }) for group in groups for protocol in group.protocol)
        await self._delete(session, pairs)

    async def delete_entities(self, session: aiohttp.ClientSession,
                              entities: Sequence[Entity]):
        """Delete the groups using the API"""
        # Delete from IOTA
        iota = ((f'{self.url_iotagent}/iot/devices/{entity.device_id}', {
            'protocol': entity.protocol
        }) for entity in entities if entity.attributes)
        # And also from context broker
        ctxb = ((f'{self.url_cb}/v2/entities/{entity.device_id}', None)
                for entity in entities)
        await gather(self._delete(session, iota), self._delete(session, ctxb))
