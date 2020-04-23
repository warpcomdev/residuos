"""API aggregator"""

import logging
import json
import asyncio
from typing import Iterable, Mapping, Dict, Optional, Any

import aiohttp
import attr

from .error import FetchError
from .attrib import Attrib, AttribList
from .group import Group
from .entity import Entity


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

    async def _create_devices(self, session: aiohttp.ClientSession,
                              sequence: Iterable[Entity]):
        return await self._create_iota(session, 'devices', sequence)

    async def _create_entities(self, session: aiohttp.ClientSession,
                               sequence: Iterable[Entity]):
        """Create a sequence of entities using the CB API"""
        assert self.token is not None
        url = f'{self.url_cb}/v2/op/update'
        headers = {
            'Fiware-Service': self.service,
            'Fiware-ServicePath': self.subservice,
            'X-Auth-Token': self.token,
            'Content-Type': 'application/json',
        }

        def cb_entity(attrib: Entity) -> Optional[Mapping[str, Any]]:
            """Turns an attrib into an entity suitable for the CB"""
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
        keys = ", ".join(item['id'] if item is not None else '' for item in ents)
        logging.debug("Creating CB entities keys %s", keys)

        resp = await session.post(url, headers=headers, json=data)
        if resp.status != 204:
            raise FetchError(url, resp, headers=headers, json=data)
        logging.debug("CB entities keys %s created with code %d", keys,
                      resp.status)

    async def create_entities(self, session: aiohttp.ClientSession,
                              entities: Iterable[Entity]):
        """Create IOTA / CB Entities"""
        await asyncio.gather(
            # Only send to IOTA those entities that have at least one attribute
            self._create_devices(
                session, (entity for entity in entities if entity.attributes)),
            self._create_entities(
                session,
                (entity for entity in entities if not entity.attributes)))

    async def create_groups(self, session: aiohttp.ClientSession,
                            sequence: Iterable[Group]):
        """Create IOTA groups"""
        return await self._create_iota(session, 'services', sequence)

    async def _delete(self, session: aiohttp.ClientSession, url: str,
                      params: Optional[Mapping[str, Any]]):
        """Delete the group using the API"""
        assert self.token is not None
        headers = {
            'Fiware-Service': self.service,
            'Fiware-ServicePath': self.subservice,
            'X-Auth-Token': self.token,
        }
        logging.debug("Deleting entity with URL %s and Params %s", url,
                      json.dumps(params))
        resp = await session.delete(url, headers=headers, params=params)
        if (resp.status < 200 or resp.status > 204) and resp.status != 404:
            raise FetchError(url, resp, headers=headers, json=params)
        logging.debug("Entity %s deleted with code %d", url, resp.status)

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
        await asyncio.gather(*tasks)

    async def delete_group(self, session: aiohttp.ClientSession, group: Group):
        """Delete the group using the API"""
        url = f'{self.url_iotagent}/iot/services'
        await asyncio.gather(*(self._delete(session, url, {
            'apikey': group.apikey,
            'protocol': protocol
        }) for protocol in group.protocol))
