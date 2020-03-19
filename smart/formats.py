"""CSV module reads entities and groups from a CSV file"""

from typing import Any, Mapping, Tuple, Sequence
import yaml

from .factory import Factory
from .group import Group
from .entity import Entity
from .csv import CSVIndex


def fromlist(cls, factory: Factory, seq: Sequence[Mapping[str, Any]]):
    """
    Read a set of Group or Entity objects from a list,
    using the Factory for inheritance.
    """
    return tuple(cls.fromdict(factory, data) for data in seq)


def readcsv(factory: Factory, path: str,
            protocol: str) -> Tuple[Sequence[Group], Sequence[Entity]]:
    """Read groups and entities from CSV file"""
    groups, entities = list(), list()
    for data in CSVIndex.readfile(protocol, path):
        if 'apikey' in data:
            groups.append(data)
        else:
            entities.append(data)
    return (fromlist(Group, factory,
                     groups), fromlist(Entity, factory, entities))


def readyaml(factory: Factory,
             path: str) -> Tuple[Sequence[Group], Sequence[Entity]]:
    """Read groups and entities from yaml file"""
    with open(path, "r", encoding="utf-8") as infile:
        body = yaml.safe_load(infile)
        return (fromlist(Group, factory, body.get('groups', list())),
                fromlist(Entity, factory, body.get('entities', list())))


def readfile(factory: Factory, path: str,
             protocol: str) -> Tuple[Sequence[Group], Sequence[Entity]]:
    """Read groups and entities from either yaml or CSV file"""
    lower = path.lower()
    if any(lower.endswith(ext) for ext in ('.yml', '.yaml')):
        return readyaml(factory, path)
    if any(lower.endswith(ext) for ext in ('.csv', )):
        return readcsv(factory, path, protocol)
    return tuple(), tuple()
