import re
from typing import List, Optional, Dict, Any
from netmiko import ConnectHandler

from fosutil.config import (
    secrets,
    ALIAS_PATTERN,
    ALIAS_PAIR_PATTERN,
    ZONE_PATTERN,
    WWN_OBJECT_PATTERN,
    PORT_PATTERN,
    PID_PATTERN,
    SWITCH_NAME_PATTERN,
)
from fosutil.models import AliasObject, ZoneObject


class Brocade:
    def __init__(self, name: str, site: str, ip_addr: str):
        self.name = name
        self.site = site
        self.fabric = name[-4:]
        self.ip_addr = ip_addr
        self.cmd_register: List[str] = []
        self.connection: Optional[ConnectHandler] = None

    def connect(self) -> ConnectHandler:
        dev_config = {
            "device_type": "brocade_fos",
            "host": self.ip_addr,
            "username": secrets["san_switches"][self.name]["username"],
            "password": secrets["san_switches"][self.name]["password"],
            "timeout": 90,
            "conn_timeout": 90,
            "read_timeout_override": 90.0,
            "keepalive": 10,
        }
        self.connection = ConnectHandler(**dev_config)
        print(f"Connection established with {self.name} ({self.ip_addr})")
        return self.connection

    def disconnect(self) -> None:
        if self.connection:
            self.connection.disconnect()
            print(f"Connection with {self.name} ({self.ip_addr}) terminated")

    def apply_config(self) -> None:
        cfgsave = self.connection.send_command(
            command_string="cfgsave",
            expect_string=r"(yes, y, no, n)",
            strip_prompt=False,
            strip_command=False,
            read_timeout=60.0,
        )
        cfgsave += self.connection.send_command(
            command_string="y",
            expect_string=r"Updating flash",
            strip_prompt=False,
            strip_command=False,
            read_timeout=60.0,
        )
        cfgenable = self.connection.send_command(
            command_string="cfgenable prod",
            expect_string=r"(yes, y, no, n)",
            strip_prompt=False,
            strip_command=False,
            read_timeout=60.0,
        )
        cfgenable += self.connection.send_command(
            command_string="y",
            expect_string=r"Updating flash",
            strip_prompt=False,
            strip_command=False,
            read_timeout=60.0,
        )
        print(f"New config save and applied in {self.fabric}")

    def get_available_aliases(self, alias: str) -> List[str]:
        alishow = self.connection.send_command(f"alishow *{alias}*")
        return sorted(set(ALIAS_PATTERN.findall(alishow)))

    def get_wwwns(self, alias: str) -> List[Dict[str, Any]]:
        alias_list = []
        ret = []
        t = []

        parse_zoneshow = self.connection.send_command(f"zoneshow *{alias}*")
        for i in ALIAS_PAIR_PATTERN.findall(parse_zoneshow):
            alias_list.append(i)
        alias_list = [x for x in [y for ys in alias_list for y in ys] if alias in x]

        parse_alishow = self.connection.send_command(f"alishow *{alias}*")
        for i in ALIAS_PATTERN.findall(parse_alishow):
            t.append(i)
        t = [x for x in t if alias in x]

        alias_list = alias_list + t

        for x in sorted(set(alias_list)):
            alishow_output = self.connection.send_command(f"alishow *{x}*")
            alishow_alias = ALIAS_PATTERN.findall(alishow_output)
            alishow_wwn = WWN_OBJECT_PATTERN.findall(alishow_output)
            ret.append({"alias": alishow_alias[0], "wwn": alishow_wwn})
        return ret

    def create_alias(self, name: str, wwn: List[str]) -> Dict[str, Any]:
        ret = {}
        check = self.connection.send_command(f"alishow {name}")
        if re.match(r".*does not exist.", check[1:]):
            ret["result"] = True
            print(f"Alias to create in {self.fabric} - {name}")
            for w in wwn:
                self.cmd_register.append(f'alicreate "{name}", "{w}"')
        else:
            ret["result"] = False
            print(f"Defined alias is already present in {self.fabric} - {name}")
            match_alias = self.get_wwwns(name)
            self.get_alias_details({name: match_alias[name]})[0].display()
        return ret

    def remove_alias(self, alias: AliasObject) -> None:
        check = self.connection.send_command(f"alishow *{alias.name}*")
        if re.match(r".*does not exist.", check[1:]):
            print(f"Defined alias does not exist in {self.fabric}")
        else:
            alias.display()
            self.cmd_register.append(f'alidelete "{alias.name}"')

    def add_portname(self, name: str, wwn: str) -> None:
        nodefind = self.connection.send_command(f"nodefind {wwn}")
        if re.match(r".*No device found", nodefind):
            print(f"Defined alias is not present in {self.fabric}, script will not assign portname")
        else:
            port = PORT_PATTERN.findall(nodefind)
            self.cmd_register.append(f"portname {port[0]} -n {name}")

    def remove_portname(self, alias: AliasObject) -> None:
        if alias.port != "???":
            self.cmd_register.append(f"portname {alias.port} -n port{alias.port}")
        else:
            print(f"Defined alias is not present in {self.fabric}, script will not remove portname")

    def get_alias_details(self, parse_data) -> List[AliasObject]:
        ret = []
        fabshow_cmd = self.connection.send_command("fabricshow")

        if isinstance(parse_data, list):
            buf = []
            for a in parse_data:
                for w in a["wwn"]:
                    nodefind_cmd = self.connection.send_command(f"nodefind {w}")
                    if not PORT_PATTERN.findall(nodefind_cmd):
                        buf.append(AliasObject(a["alias"], None))
                    else:
                        port = PORT_PATTERN.findall(nodefind_cmd)[0]
                        fab_info = dict(
                            zip(
                                SWITCH_NAME_PATTERN.findall(fabshow_cmd),
                                PID_PATTERN.findall(fabshow_cmd),
                            )
                        )
                        for idx, (k, v) in enumerate(fab_info.items()):
                            if (
                                PID_PATTERN.findall(nodefind_cmd)[0][0:2]
                                == fab_info[k][-2:]
                            ):
                                match_switch = list(fab_info.keys())[idx]
                                match_port = port
                                buf.append(
                                    {
                                        "name": a["alias"],
                                        "switch": match_switch,
                                        "port": match_port,
                                        "wwn": w,
                                    }
                                )

            for it in buf:
                if isinstance(it, AliasObject):
                    ret.append(it)
                else:
                    alias_name = it["name"]
                    del it["name"]
                    x = AliasObject(alias_name, it)
                    ret.append(x)
        else:
            details = []
            nodefind_cmd = self.connection.send_command(f"nodefind {parse_data}")
            alias = re.findall(r"(?<=Aliases: )[0-9a-zA-Z_ ]*", nodefind_cmd)

            if not PORT_PATTERN.findall(nodefind_cmd):
                return ret

            port = PORT_PATTERN.findall(nodefind_cmd)[0]
            fab_info = dict(
                zip(
                    SWITCH_NAME_PATTERN.findall(fabshow_cmd),
                    PID_PATTERN.findall(fabshow_cmd),
                )
            )
            for idx, (k, v) in enumerate(fab_info.items()):
                if (
                    PID_PATTERN.findall(nodefind_cmd)[0][0:2]
                    == fab_info[k][-2:]
                ):
                    match_switch = list(fab_info.keys())[idx]
                    match_port = port
                    details.append(
                        {"switch": match_switch, "port": match_port, "wwn": parse_data}
                    )
            ret.append(AliasObject(alias[0], details[0]))
        return ret

    def get_zone_info(self, alias: str) -> List[ZoneObject]:
        ret = []
        zone_list = self.connection.send_command(f"zoneshow *{alias}*")
        for zone in ZONE_PATTERN.findall(zone_list):
            ret.append(ZoneObject(zone))
        return ret