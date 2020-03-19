"""Device Group abstractions"""

from typing import Sequence, Mapping, Any
import yaml
import attr

from .factory import AttribList, Factory
from .error import ParseError


@attr.s(auto_attribs=True, kw_only=True)
class Group(AttribList):
    """Represents a device group"""
    apikey: str
    protocol: Sequence[str]

    def asdict(self) -> Mapping[str, Any]:
        """Return only non-null attributes in dict"""
        return attr.asdict(self,
                           recurse=True,
                           filter=(lambda attr, v: v is not None))

    def key(self) -> str:
        """Return group API key"""
        return self.apikey

    @classmethod
    def fromdict(cls, factory: Factory, data: Mapping[str, Any]):
        """Creates a Group object from a dict"""
        try:
            apikey = data['apikey']
            atlist = factory(apikey, data)
            return cls(apikey=apikey,
                       entity_type=atlist.entity_type,
                       protocol=data['protocol'],
                       static_attributes=atlist.static_attributes,
                       attributes=atlist.attributes)
        except KeyError as err:
            raise ParseError(err=err, obj=data)
        except TypeError as err:
            raise ParseError(err=err, obj=data)

    @classmethod
    def fromyaml(cls, factory: Factory, path: str):
        """
        Read a set of group objects from a file.
        Adds all new groups to the "inherit" mapping, and
        returns a list of groups.
        """
        with open(path, "r", encoding="utf-8") as infile:
            return tuple(
                Group.fromdict(factory, data)
                for data in yaml.safe_load(infile).get('groups', list()))
