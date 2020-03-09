"""Device Group abstractions"""

from itertools import filterfalse
from typing import Sequence, Mapping, Any
import yaml
import attr

from .error import ParseError
from .attrib import Attrib
from .group import Group


@attr.s(auto_attribs=True, kw_only=True)
class Entity:
    """Represents a device"""
    device_id: str
    entity_type: str
    entity_name: str
    protocol: str
    static_attributes: Sequence[Attrib]
    attributes: Sequence[Attrib]

    def asdict(self) -> Mapping[str, Any]:
        """Return only non-null attributes in dict"""
        return attr.asdict(self,
                           recurse=True,
                           filter=(lambda attr, v: v is not None))

    @staticmethod
    def _override(attributes: Mapping[str, Any],
                  override: Mapping[str, Any]) -> Mapping[str, Any]:
        """Overrides attributes with the same name"""
        result = dict(attributes)
        result.update(override)
        return result

    @staticmethod
    def _resolve(attributes: Mapping[str, Any],
                 group: Group) -> Sequence[Attrib]:
        """Resolve attributes against a group definition"""
        attmap = dict()
        if group.static_attributes is not None:
            attmap.update(
                {attrib.name: attrib
                 for attrib in group.static_attributes})
        if group.attributes is not None:
            attmap.update({attrib.name: attrib for attrib in group.attributes})
        for key, val in attributes.items():
            clone = Attrib.clone(attmap[key])
            clone.value = val
            attmap[key] = clone
        return tuple(attmap.values())

    @classmethod
    def fromdict(cls, groups: Mapping[str, Group], data: Mapping[str, Any]):
        """Creates an Entity object from a dict"""
        clone, attributes = dict(data), data['attributes']
        # Get group and entity_Type from referenced _group
        group = groups[clone['_group']]
        del clone['_group']
        clone['entity_type'] = group.entity_type
        # If there is an _override, merge it with attributes
        if '_override' in clone:
            # Overriden attribs replace regular attribs
            attributes = Entity._override(attributes, clone['_override'])
            del clone['_override']
        # Resolve all attributes to references in the group
        attributes = Entity._resolve(attributes, group)
        static = lambda attrib: attrib.value is not None
        clone['static_attributes'] = tuple(filter(static, attributes))
        clone['attributes'] = tuple(filterfalse(static, attributes))
        if ' ' in clone['entity_name']:
            raise ValueError(f"Entity Name '{clone['entity_name']}' invalid")
        try:
            return cls(**clone)
        except TypeError as err:
            raise ParseError(err=err, obj=data)

    @classmethod
    def fromfile(cls, groups: Mapping[str, Group], path: str):
        """Read a set of entity objects from a file"""
        with open(path, "r", encoding="utf-8") as infile:
            data = yaml.safe_load(infile)
            return {
                k: Entity.fromdict(groups, v)
                for k, v in data.get('entities', dict()).items()
                if not k.startswith('_')
            }
