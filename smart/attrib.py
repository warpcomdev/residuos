"""Device / Group Attribute"""

from typing import Optional, Mapping, Any
import attr

from .error import ParseError


@attr.s(auto_attribs=True, kw_only=True)
class Attrib:
    """
    Represents an attribute in a device group.

    Attributes have the following properties:
    - name: Name of the attribute.
    - type: string, date, integer, float, array, geo:point ...
    - value: For static attributes, value.
    - expression: For auto-calculated attributes, expression.
    - object_id: alias for the attribute, as received via HTTP or MQTT.
    - entity_name, entity_type: in case you need to split
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
