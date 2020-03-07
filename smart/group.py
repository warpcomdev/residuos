"""Device Group abstractions"""

import itertools
from typing import Optional, Sequence, Mapping, Any
import yaml
import attr

from .error import ParseError
from .attrib import Attrib

# Json Attr List
AttrDict = Mapping[str, Any]


@attr.s(auto_attribs=True, kw_only=True)
class Group:
    """Represents a device group"""
    entity_type: str
    apikey: str
    protocol: Sequence[str]
    static_attributes: Optional[Sequence[Attrib]] = None
    attributes: Optional[Sequence[Attrib]] = None

    def asdict(self) -> Mapping[str, Any]:
        """Return only non-null attributes in dict"""
        return attr.asdict(self,
                           recurse=True,
                           filter=(lambda attr, v: v is not None))

    @staticmethod
    def _override(attributes: Sequence[AttrDict],
                  override: Sequence[AttrDict]) -> Sequence[AttrDict]:
        """Overrides attributes with the same name"""
        match = frozenset(item['name'] for item in override)
        return tuple(
            itertools.chain(
                (item for item in attributes if item['name'] not in match),
                override))

    @classmethod
    def fromdict(cls, data: Mapping[str, Any]):
        """Creates a Group object from a dict"""
        clone, attributes = dict(data), data['attributes']
        if '_override' in clone:
            # Overriden attribs replace regular attribs
            attributes = Group._override(attributes, clone['_override'])
            del clone['_override']
        clone['static_attributes'] = tuple(
            Attrib.fromdict(attr) for attr in attributes if 'value' in attr)
        clone['attributes'] = tuple(
            Attrib.fromdict(attr) for attr in attributes
            if not 'value' in attr)
        try:
            return cls(**clone)
        except TypeError as err:
            raise ParseError(err=err, obj=data)

    @classmethod
    def fromfile(cls, path: str):
        """Read a set of group objects from a file"""
        with open(path, "r", encoding="utf-8") as infile:
            data = yaml.safe_load(infile)
            return {
                k: Group.fromdict(v)
                for k, v in data.get('groups', dict()).items()
                if not k.startswith('_')
            }
