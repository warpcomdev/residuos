"""CSV module reads entities and groups from a CSV file"""

import logging
import csv
from typing import Optional, Mapping, Callable, Any, Sequence
import json
import attr


@attr.s(auto_attribs=True)
class AttribIndex:
    """
    Relates a column number in the CSV, with an attribute in the group or entity
    """
    column: int
    name: str
    type: str
    cast: Callable[[str], Any]
    object_id: Optional[str] = None

    @classmethod
    def fromheader(cls, column: int, header: str):
        """
        Parse CSV header and attach to a particular column number.

        The header is expected to have the following format:

        'object_id:name<type>'

        e.g.: 't:temperature<Number>"

        Type is optional, if ommitted if will be set to Text.
        object_id can also be ommitted.
        """
        name, entity_type, object_id = header.strip(), "Text", None
        # No-Op cast
        cast = lambda text: text
        if "<" in header:
            name, entity_type = header.split("<")
            name = name.strip()
            entity_type = entity_type.strip(">").strip()
            if entity_type == 'Number':
                cast = lambda number: float(number.replace(",", "."))
            elif 'json' in entity_type:
                cast = json.loads
        if ":" in name:
            object_id, name = name.split(":")
            object_id = object_id.strip()
            name = name.strip()
        # Skip the "TimeInstant" attribute, it's set by the IOTA.
        if name == "TimeInstant":
            return None
        return cls(column=column,
                   name=name,
                   type=entity_type,
                   object_id=object_id,
                   cast=cast)

    def __call__(self, value: Optional[str]) -> Optional[Mapping[str, Any]]:
        """Build a Dictionary from a CSV value"""
        if value is not None:
            value = value.strip() or None
        if value is None:
            # Even if value is None, if the attribute has an object_id,
            # we want to generate it.
            if self.object_id is None:
                return None
        data = {
            'name': self.name,
            'type': self.type,
        }
        if self.object_id is not None:
            data['object_id'] = self.object_id
        if value is None:
            pass
        elif "${" in value:
            data['expression'] = value
        else:
            data['value'] = self.cast(value)
        return data


@attr.s(auto_attribs=True)
class CSVIndex:
    """
    Relates column numbers with all the relevant fields to parse:
    entity_type, entity_id, device_idm apikey and attributes.
    """
    entity_type: int
    default_proto: str
    entity_id: Optional[int]
    device_id: Optional[int]
    apikey: Optional[int]
    protocol: Optional[int]
    attribs: Sequence[AttribIndex]

    @classmethod
    def fromheader(cls, default_proto: str, header: Sequence[str]):
        """Builds a CSV indexer from the header row

        The header row is expected to have the following columns:
        - 'entityType': mandatory, the type.
        - 'entityID': optional, for entities only (as opposed to groups)
        - 'deviceID': optional, entityID is used if deviceID is not specified.
        - 'apikey': optional, for groups only.
        - 'protocol': optional, 'IoTA-JSON' or 'IoTA-UL'. If not specified,
           use the default value given as a parameter
        - A variable number of atributes.
        """
        entity_id, entity_type, device_id, apikey, protocol = None, None, None, None, None
        attribs = list()
        for column, text in enumerate(header):
            if text == 'entityID':
                entity_id = column
            elif text == 'entityType':
                entity_type = column
            elif text == 'apiKey' or text == 'apikey':
                apikey = column
            elif text == 'deviceID':
                device_id = column
            elif text == 'protocol':
                protocol = column
            else:
                item = AttribIndex.fromheader(column, text)
                if item is not None:
                    attribs.append(item)
        if entity_id is None and apikey is None:
            raise ValueError(
                "At least one of entityID or apiKey columns must be defined")
        return cls(entity_type=entity_type,
                   default_proto=default_proto,
                   entity_id=entity_id,
                   device_id=device_id,
                   apikey=apikey,
                   protocol=protocol,
                   attribs=attribs)

    # pylint: disable=too-many-branches
    def readline(self, line: Sequence[str]):
        """
        Turn the CSV line into a dictionary object suitable
        for the Group or Entity .fromdict() function
        """
        entity_type = line[self.entity_type].strip() or None
        if entity_type is None:
            raise ValueError("entityType value must not be empty")
        entity_id, device_id, apikey = None, None, None
        # Get entity_id and device_id
        if self.entity_id is not None:
            entity_id = line[self.entity_id].strip() or None
            if self.device_id is None:
                device_id = entity_id
            else:
                device_id = line[self.device_id].strip() or entity_id
        # Get apikey
        if self.apikey is not None:
            apikey = line[self.apikey].strip() or None
        # Check at least one (and at most one) of entity_id or apikey
        # are provided
        if entity_id is None and apikey is None:
            raise ValueError(
                "At least one of entityID or apiKey values must be defined")
        if entity_id is not None and apikey is not None:
            raise ValueError(
                "Only one of entity_id or apikey must have a value")
        # Get the protocol
        protocol = None
        if self.protocol is None:
            protocol = self.default_proto
        else:
            protocol = line[self.protocol].strip() or self.default_proto
        # Build the dict
        data = {'entity_type': entity_type}
        if entity_id is not None:
            data['device_id'] = device_id
            data['entity_name'] = entity_id
            data['protocol'] = protocol
        else:
            data['apikey'] = apikey
            # For a group, protocol should be a list
            if "[" in protocol:
                data['protocol'] = json.loads(protocol)
            else:
                data['protocol'] = (protocol, )
        # Build the attributes
        attributes = list()
        for attrib in self.attribs:
            item = attrib(line[attrib.column])
            if item is not None:
                attributes.append(item)
        data['attributes'] = attributes
        return data

    @classmethod
    def readfile(cls, protocol: str, path: str):
        """Yields groups and entities in CSV file"""
        with open(path, "r", encoding='utf-8') as infile:
            csv_reader = csv.reader(infile, delimiter=',')
            csv_index = None
            for line, row in enumerate(csv_reader):
                try:
                    if csv_index is None:
                        csv_index = cls.fromheader(protocol, row)
                    elif any(cell.strip() != "" for cell in row):
                        yield csv_index.readline(row)
                except ValueError as err:
                    logging.error("File %s failed to load at row %d: %s", path,
                                  line + 1, ",".join(row))
                    raise
