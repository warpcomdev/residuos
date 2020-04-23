"""Device / Group Attribute"""

from itertools import chain, filterfalse
from typing import Optional, Mapping, Sequence, Iterator, Any
import attr

from .error import ParseError


@attr.s(auto_attribs=True, kw_only=True)
class Attrib:
    """
    Represents an attribute in a device group.

    Attributes have the following properties:
    - name: Name of the attribute.
    - type: string, date, integer, float, array, geo:point ...
    - value: A fixed value for static attributes.
    - expression: An expression for auto-calculated attributes.
    - object_id: Alias for the attribute, as received via HTTP or MQTT.
    - entity_name, entity_type: In case you need to split
      a measure in several entities.
    """
    name: str
    type: str
    expression: Optional[str] = None
    object_id: Optional[str] = None
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    value: Any = None

    @classmethod
    def fromdict(cls, data: Mapping[str, Any]):
        """Read a GroupAttr object from a dict"""
        try:
            return cls(**data)
        except TypeError as err:
            raise ParseError(err=err, obj=data)

    @classmethod
    def clone(cls, item):
        """Clone item"""
        return cls.fromdict(attr.asdict(item))


@attr.s(auto_attribs=True)
class AttribList:
    """List of attributes with attached entity type"""
    entity_type: str
    static_attributes: Optional[Sequence[Attrib]] = None
    attributes: Optional[Sequence[Attrib]] = None

    def attribs(self) -> Iterator[Attrib]:
        """Chains static and dynamic attribs"""
        return chain(*(seq for seq in (self.static_attributes, self.attributes)
                       if seq is not None))

    def asdict(self) -> Mapping[str, Any]:
        """Return only non-null attributes in dict"""
        return attr.asdict(self,
                           recurse=True,
                           filter=(lambda attr, v: v is not None))

    def key(self) -> str:
        """Key of this object. Implemented by subclasses."""
        raise NotImplementedError("key not implemented in AttribList")

    @classmethod
    def fromdict(cls, data: Mapping[str, Any]):
        """Build AttrList from entity_type and list of attribs"""
        attribs = tuple(
            Attrib.fromdict(item) for item in data.get('attributes', tuple()))
        val_none = lambda attrib: attrib.value is None
        regular = tuple(filter(val_none, attribs))
        statics = tuple(filterfalse(val_none, attribs))
        return cls(entity_type=data['entity_type'],
                   static_attributes=statics or None,
                   attributes=regular or None)
