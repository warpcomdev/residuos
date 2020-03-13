"""Device / Group Attribute"""

from itertools import filterfalse
from typing import Optional, Mapping, Sequence, Generator, Any
import attr

from .attrib import Attrib


@attr.s(auto_attribs=True)
class AttribList:
    """Atribute List"""
    entity_type: str
    static_attributes: Optional[Sequence[Attrib]] = None
    attributes: Optional[Sequence[Attrib]] = None

    def attribs(self) -> Generator[Attrib, None, None]:
        """Chains static and dynamic attribs"""
        return Attrib.chain(self.static_attributes, self.attributes)

    def asdict(self):
        """To be overriden by derived classes"""
        raise NotImplementedError("AttribList.asdict()")

    @classmethod
    def fromattr(cls, entity_type: str, attribs: Sequence[Attrib]):
        """Build AttrList from entity_type and list of attribs"""
        val_none = lambda attrib: attrib.value is None
        statics = tuple(filterfalse(val_none, attribs))
        attribs = tuple(filter(val_none, attribs))
        return cls(entity_type=entity_type,
                   static_attributes=statics or None,
                   attributes=attribs or None)


@attr.s(auto_attribs=True)
class Factory:
    """AttribListFactory supports creating AttribList with inheritance"""
    references: Mapping[str, AttribList]

    @attr.s(auto_attribs=True)
    class Inherit:
        """
        Represents an 'inheritance' relationship between an entity/group
        and another entities/groups.
        """
        device_id: Optional[str] = None
        apikey: Optional[str] = None
        values: Optional[Mapping[str, Any]] = None

        @classmethod
        def fromdict(cls, data: Mapping[str, Any]):
            """Load an inheritance block from dict"""
            result = cls(**data)
            if result.device_id is None and result.apikey is None:
                raise ValueError(
                    f'Either entity_id or apikey must be specified for {data}')
            return result

        def key(self):
            """Return either entity_id or api_key"""
            return self.device_id if self.device_id is not None else self.apikey

        def __call__(self, attrib):
            """Apply inheritance to the provided attribute"""
            if self.values is None:
                return attrib
            value = self.values.get(attrib.name, None)
            if value is None:
                return attrib
            attrib = Attrib.clone(attrib)
            attrib.value = value
            return attrib

    def _inherit(self, inherit: Inherit) -> Generator[Attrib, None, None]:
        """
        Apply inheritance using the references in this factory.
        This means, clone the attributes from the inherited entity / group,
        and override values according to the inherit specification.
        """
        ref = self.references[inherit.key()]
        if inherit.values is None:
            return ref.attribs()
        return (inherit(attrib) for attrib in ref.attribs())

    def _entity_type(self, data: Mapping[str, Any],
                     inherit: Sequence[Inherit]) -> str:
        """Merges the entity_type from the inheritance list"""
        entity_type = data.get('entity_type', None)
        if entity_type is not None:
            return entity_type
        if len(inherit) <= 0:
            raise KeyError('entity_type')
        key = inherit[-1].key()
        return self.references[key].entity_type

    def _attributes(self, data: Mapping[str, Any],
                    inherit: Sequence[Inherit]) -> str:
        """Merges the attributes from the inheritance list"""
        inherited = (self._inherit(entry) for entry in inherit)
        proper = (Attrib.fromdict(item)
                  for item in data.get('attributes', tuple()))
        return tuple(Attrib.chain(*inherited, proper))

    def __call__(self, key: str, data: Mapping[str, Any]) -> AttribList:
        """
        Reads the '_inherit' and 'attributes' fields in data, builds
        an AttribList with them, and saves unker 'key' for future _inherit.
        """
        # Support both dict and list for _inherit
        raw_inherit = data.get('_inherit', tuple())
        if hasattr(raw_inherit, 'items'):
            raw_inherit = tuple(raw_inherit)
        inherit = tuple(
            Factory.Inherit.fromdict(entry) for entry in raw_inherit)
        # Build the AttribList
        attrib_list = AttribList.fromattr(self._entity_type(data, inherit),
                                          self._attributes(data, inherit))
        # Save the AttribList for future reference
        self.references[key] = attrib_list
        return attrib_list
