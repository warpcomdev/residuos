"""API aggregator"""

import logging
import asyncio
from typing import (Mapping, Dict, Sequence, Optional, Iterable, Awaitable,
                    Any)

import aiohttp
import attr

from .request import Request
from .attrib import AttribList
from .group import Group
from .entity import Entity


async def gather(*awaitables: Awaitable):
    """
    Gather awaitables that return None.
    If any of the awaitables raises an exception, logs it.
    Raises the last exception to arrive.
    """
    last_err = None
    for err in await asyncio.gather(*awaitables, return_exceptions=True):
        if err is not None:
            last_err = err
            logging.error(err)
    if last_err is not None:
        raise last_err


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

    def _headers(self):
        """Return headers"""
        headers = {
            'Fiware-Service': self.service,
            'Fiware-ServicePath': self.subservice,
        }
        if self.token is not None:
            headers['X-Auth-Token'] = self.token
        return headers

    async def auth(self, session: aiohttp.ClientSession):
        """Get an authentication token"""
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

        resp = await Request(
            session=session,
            title="Get authentication token",
            url=f'{self.url_keystone}/v3/auth/tokens',
            headers=self._headers(),
            body=request).post(lambda status: 200 <= status <= 204)
        self.token = resp.headers['X-Subject-Token']

    async def _create_iota(self, session: aiohttp.ClientSession, kind: str,
                           sequence: Sequence[AttribList]):
        """Create a sequence of entities using the IoTA API"""
        data = {kind: tuple(item.asdict() for item in sequence)}
        keys = ", ".join(item.key() for item in sequence)
        await Request(session=session,
                      title="Create IOTA %s with keys %s",
                      args=(kind, keys),
                      url=f'{self.url_iotagent}/iot/{kind}',
                      headers=self._headers(),
                      body=data).post(lambda status: status == 201)

    async def _create_devices(self, session: aiohttp.ClientSession,
                              sequence: Sequence[Entity]):
        return await self._create_iota(session, 'devices', sequence)

    async def _create_entities(self, session: aiohttp.ClientSession,
                               sequence: Sequence[Entity]):
        """Create a sequence of entities using the CB API"""
        def cb_entity(attrib: Entity) -> Optional[Mapping[str, Any]]:
            """Turns an Entity into a dict suitable for the CB"""
            if not attrib.static_attributes:
                return None
            data: Dict[str, Any] = {
                'id': attrib.device_id,
                'type': attrib.entity_type,
            }
            for current in attrib.static_attributes:
                data[current.name] = {
                    'type': current.type,
                    'value': current.value,
                }
            return data

        ents = tuple(cb_entity(item) for item in sequence)
        ents = tuple(ent for ent in ents if ent is not None)
        if len(ents) <= 0:
            logging.debug("No entities to create")
            return

        data = {'actionType': 'APPEND', 'entities': ents}
        keys = ", ".join(item['id'] if item is not None else ''
                         for item in ents)

        await Request(session=session,
                      title="Create CB entities with keys %s",
                      args=(keys, ),
                      url=f'{self.url_cb}/v2/op/update',
                      headers=self._headers(),
                      body=data).post(lambda status: status == 204)

    async def create_entities(self, session: aiohttp.ClientSession,
                              entities: Sequence[Entity]):
        """Create IOTA / CB Entities"""
        # Only send to IOTA those entities that have at least one attribute
        iota_data = tuple(entity for entity in entities if entity.attributes)
        ctxb_data = tuple(entity for entity in entities
                          if not entity.attributes)
        await gather(self._create_devices(session, iota_data),
                     self._create_entities(session, ctxb_data))

    async def create_groups(self, session: aiohttp.ClientSession,
                            sequence: Sequence[Group]):
        """Create IOTA groups"""
        return await self._create_iota(session, 'services', sequence)

    async def _delete(self, session: aiohttp.ClientSession, url: str,
                      params: Optional[Mapping[str, Any]]):
        """Delete the group using the API"""
        await Request(
            session=session,
            title="Delete object at %s with params %s",
            args=(url, params),
            url=url,
            headers=self._headers(),
            params=params).delete(lambda status:
                                  (200 <= status <= 204) or status == 404)

    async def delete_entity(self, session: aiohttp.ClientSession,
                            entity: Entity):
        """Delete the entity using the API"""
        tasks = list()
        # Delete from IOTA
        if entity.attributes:
            tasks.append(
                self._delete(
                    session,
                    f'{self.url_iotagent}/iot/devices/{entity.device_id}',
                    {'protocol': entity.protocol}))
        # And also from context broker
        tasks.append(
            self._delete(session,
                         f'{self.url_cb}/v2/entities/{entity.entity_name}',
                         None))
        await gather(*tasks)

    async def delete_group(self, session: aiohttp.ClientSession, group: Group):
        """Delete the group using the API"""
        url = f'{self.url_iotagent}/iot/services'
        await gather(*(self._delete(session, url, {
            'apikey': group.apikey,
            'protocol': protocol
        }) for protocol in group.protocol))
