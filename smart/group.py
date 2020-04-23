"""Device Group abstractions"""

from typing import Sequence, Mapping, Any
import attr

from .attrib import AttribList
from .error import ParseError


@attr.s(auto_attribs=True, kw_only=True)
class Group(AttribList):
    """Represents a device group"""
    apikey: str
    protocol: Sequence[str]

    def key(self) -> str:
        """Return unique key"""
        return self.apikey

    @classmethod
    def fromdict(cls, data: Mapping[str, Any]):
        """Creates a Group object from a dict"""
        try:
            atlist = AttribList.fromdict(data)
            return cls(apikey=data['apikey'],
                       entity_type=atlist.entity_type,
                       protocol=data['protocol'],
                       static_attributes=atlist.static_attributes,
                       attributes=atlist.attributes)
        except (KeyError, TypeError) as err:
            raise ParseError(err=err, obj=data)
