"""Create entities for dumps vertical"""

import sys
import stat
import os
import asyncio
import logging
from collections import defaultdict
from typing import Sequence, Mapping
import configargparse
import attr
import aiohttp
import yaml

from smart import AttribList, Group, Entity, Api, Factory


@attr.s(auto_attribs=True)
class Config:
    """Configuration parameters"""
    path: Sequence[str]
    url_keystone: str = "Full URL of the keystone API"
    url_cb: str = "Full URL of the context broker"
    url_iotagent: str = "Full URL of the IOTA API"
    service: str = "Service name"
    subservice: str = "/Subservice path"
    username: str = "API User name"
    password: str = "API User password"
    delete: bool = False
    markdown: bool = False

    @classmethod
    def must(cls, prefix: str):
        """Loads config from file, env or args"""
        parse = configargparse.ArgParser(default_config_files=['.env'])
        # pylint: disable=bad-continuation
        parse.add('-c',
                  '--config',
                  required=False,
                  is_config_file=True,
                  help='config file path')
        prefix = prefix.upper()
        for field in attr.fields(cls):
            if field.name == 'path':
                parse.add('path',
                          type=str,
                          nargs='+',
                          metavar='PATH',
                          help='Files or folders of YAML descriptors')
            elif field.name == 'delete':
                parse.add('-d',
                          '--delete',
                          action='store_true',
                          help='Delete entities (instead of create)')
            elif field.name == 'markdown':
                parse.add('-md',
                          '--markdown',
                          action='store_true',
                          help='print the entities in markdown')
            else:
                # pylint: disable=bad-continuation
                parse.add(f'--{field.name}',
                          help=field.default,
                          type=str,
                          required=True,
                          env_var=f'{prefix}_{field.name.upper()}')
        args = parse.parse_args()
        return cls(**{
            field.name: getattr(args, field.name)
            for field in attr.fields(cls)
        })

    def files(self):
        """Enumerates all yaml files in provided paths"""
        for path in self.path:
            mode = os.stat(path).st_mode
            if stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                yield path
            elif stat.S_ISDIR(mode):
                for fname in os.listdir(path):
                    lower = fname.lower()
                    if any(fname.endswith(ext) for ext in ('.yml', 'yaml')):
                        yield os.path.join(path, fname)
            else:
                raise ValueError(
                    f'File path {path} is not a file or directory')


async def create_entities(api: Api, groups: Sequence[Group],
                          entities: Sequence[Entity]):
    """Create entities using the Api"""
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            verify_ssl=False)) as session:
        await api.auth(session)
        logging.info("Creating objects")
        await asyncio.gather(api.create_groups(session, groups),
                             api.create_entities(session, entities))


async def delete_entities(api: Api, groups: Sequence[Group],
                          entities: Sequence[Entity]):
    """Delete entities using the Api"""
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            verify_ssl=False)) as session:
        await api.auth(session)
        logging.info("Deleting objects")
        await asyncio.gather(api.delete_groups(session, groups),
                             api.delete_entities(session, entities))


def print_entities(groups: Sequence[Group], entities: Sequence[Entity]):
    """Print entities in markdown format"""
    typemap: Mapping[str, AttribList] = defaultdict(list)
    for group in groups:
        typemap[group.entity_type].append(group)
    for entity in entities:
        typemap[entity.entity_type].append(entity)
    msg = list()
    for typename, items in typemap.items():
        msg.append(f"### {typename}\n")
        for item in items:
            mapping = item.asdict()
            if 'apikey' in mapping:
                msg.append(f"*Group: {mapping['apikey']}*\n")
            else:
                msg.append(f"*Entity: {mapping['device_id']}*\n")
            msg.append(yaml.dump(item.asdict()))
    print("\n".join(msg))


async def main():
    """Main function"""
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    config = Config.must("SMART")
    print(attr.asdict(config))
    api = Api(url_keystone=config.url_keystone,
              url_cb=config.url_cb,
              url_iotagent=config.url_iotagent,
              service=config.service,
              subservice=config.subservice,
              username=config.username,
              password=config.password)

    # Read all groups first
    factory = Factory(dict())
    groups = list()
    for fname in config.files():
        logging.info("Reading groups from file: %s", fname)
        groups.extend(Group.fromfile(factory, fname))
    logging.info("%d Groups loaded: %s", len(groups),
                 ", ".join(g.apikey for g in groups))

    # Now, real all entities
    entities = list()
    for fname in config.files():
        logging.info("Reading entities from file: %s", fname)
        entities.extend(Entity.fromfile(factory, fname))
    logging.info("%d Entities loaded: %s", len(entities),
                 ",".join(e.device_id for e in entities))

    if config.markdown:
        print_entities(groups, entities)
    elif config.delete:
        await delete_entities(api, groups, entities)
    else:
        await create_entities(api, groups, entities)


if __name__ == "__main__":
    LOOP = asyncio.get_event_loop()
    try:
        LOOP.run_until_complete(main())
    finally:
        LOOP.close()
