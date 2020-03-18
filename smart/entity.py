"""Device Group abstractions"""

from typing import Mapping, Any
import yaml
import attr

from .error import ParseError
from .factory import AttribList, Factory


@attr.s(auto_attribs=True, kw_only=True)
class Entity(AttribList):
    """Represents a device"""
    device_id: str
    entity_name: str
    protocol: str

    def asdict(self) -> Mapping[str, Any]:
        """Return only non-null attributes in dict"""
        return attr.asdict(self,
                           recurse=True,
                           filter=(lambda attr, v: v is not None))

    def key(self) -> str:
        """Return entity id"""
        return self.device_id

    @classmethod
    def fromdict(cls, factory: Factory, data: Mapping[str, Any]):
        """Creates an Entity object from a dict"""
        try:
            device_id = data['device_id']
            atlist = factory(device_id, data)
            return cls(device_id=device_id,
                       entity_type=atlist.entity_type,
                       entity_name=data['entity_name'],
                       protocol=data['protocol'],
                       static_attributes=atlist.static_attributes,
                       attributes=atlist.attributes)
        except KeyError as err:
            raise ParseError(err=err, obj=data)
        except TypeError as err:
            raise ParseError(err=err, obj=data)

    @classmethod
    def fromfile(cls, factory: Factory, path: str):
        """
        Read a set of group objects from a file.
        Adds all new groups to the "inherit" mapping, and
        returns a list of groups.
        """
        with open(path, "r", encoding="utf-8") as infile:
            return tuple(
                Entity.fromdict(factory, data)
                for data in yaml.safe_load(infile).get('entities', list()))
