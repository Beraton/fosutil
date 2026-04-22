import re
from typing import List, Dict, Any
from prompt_toolkit.validation import Validator, ValidationError


class WwnValidator(Validator):
    def validate(self, document):
        text = document.text
        ok = re.match(r"^(\w[0-9a-fA-F]{15}|\w[0-9a-fA-F:]{22})", text)
        if not ok:
            raise ValidationError(message="Wrong WWN format", cursor_position=len(text))


def normalize_wwn(wwn: str) -> str:
    if len(wwn) == 16:
        return re.sub(r"(\w{2})", r"\1:", wwn, count=7)
    return wwn


def parse_zoneshow(raw: str, fullzone: bool = False) -> List[str]:
    zone_pattern = re.compile(r"(?<=zone:\s)([0-9a-zA-Z_]*)")
    alias_pattern = re.compile(r"([0-9a-zA-Z].*?)_.*; ([0-9a-zA-Z].*?)_.*")
    ret = []
    if not fullzone:
        for x in alias_pattern.findall(raw):
            for i in x:
                ret.append(i)
        return list(set(ret))
    else:
        for x in zone_pattern.findall(raw):
            ret.append(x)
        return ret


def parse_alishow(raw: str) -> Dict[str, str]:
    aliases = re.findall(r"(?<=alias:\s)([0-9a-zA-Z_]*)", raw)
    wwns = re.findall(r"(\w[0-9a-fA-F:]{22})", raw)
    return dict(zip(aliases, wwns))


def parse_nodefind(raw: str) -> Dict[str, str]:
    alias = re.findall(r"(?<=Aliases: )[0-9a-zA-Z_ ]*", raw)
    wwn = re.findall(r"(?<=WWPN\s)([0-9a-zA-Z:]{23})", raw)
    return dict(zip(alias, wwn))


def generate_checkbox(alias_list: Dict[str, List[str]]) -> List[str]:
    ret = []
    for k, v in alias_list.items():
        for x in v:
            ret.append(x)
    return ret


def create_zones_checkbox(raw: Dict[str, List[str]]) -> List[str]:
    ret = []
    for zones in raw.values():
        for z in zones:
            ret.append(z)
    return ret