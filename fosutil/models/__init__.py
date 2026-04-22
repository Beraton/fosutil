from dataclasses import dataclass
from typing import Optional, Dict, Any

from fosutil.config import HOST_PATTERN, FULL_ALIAS_PATTERN


@dataclass
class AliasObject:
    name: str
    switch: str = "???"
    wwn: str = "???"
    port: str = "???"

    def __post_init__(self, associations: Optional[Dict[str, Any]] = None):
        if associations is not None:
            self.switch = associations.get("switch", "???")
            self.wwn = associations.get("wwn", "???")
            self.port = associations.get("port", "???")

    def display(self) -> str:
        msg = f"  == Alias: {self.name}, SW: {self.switch}, WWN: {self.wwn}, Port: {self.port}"
        return msg

    def hostname(self):
        return HOST_PATTERN.match(self.name)


@dataclass
class ZoneObject:
    name: str
    alias_a: str = ""
    alias_b: str = ""

    def __post_init__(self):
        if not self.alias_a:
            matches = FULL_ALIAS_PATTERN.findall(self.name)
            if matches:
                self.alias_a = matches[-1][0]
                self.alias_b = matches[-1][1]

    def display(self) -> str:
        return f"Zone: {self.name}, Alias A: {self.alias_a}, Alias B: {self.alias_b}"