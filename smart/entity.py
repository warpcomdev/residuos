"""Device Group abstractions"""

from typing import Mapping, Any
import attr

from .error import ParseError
from .attrib import AttribList


@attr.s(auto_attribs=True, kw_only=True)
class Entity(AttribList):
    """Represents a device"""
    device_id: str
    entity_name: str
    protocol: str

    def key(self) -> str:
        """Return unique key"""
        return self.device_id

    @classmethod
    def fromdict(cls, data: Mapping[str, Any]):
        """Creates an Entity object from a dict"""
        try:
            atlist = AttribList.fromdict(data)
            return cls(device_id=data['device_id'],
                       entity_type=atlist.entity_type,
                       entity_name=data['entity_name'],
                       protocol=data['protocol'],
                       static_attributes=atlist.static_attributes,
                       attributes=atlist.attributes)
        except (KeyError, TypeError) as err:
            raise ParseError(err=err, obj=data)
