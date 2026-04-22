import re
import time
from typing import List, Dict, Any, Optional
from PyInquirer import prompt, style_from_dict, Token
from simple_colors import cyan, green

from fosutil.config import (
    secrets,
    SITE_PRI,
    SITE_SEC,
    BRC_PRI,
    BRC_SEC,
    WWN_PATTERN,
    PERSONA_MAP,
)
from fosutil.devices import Brocade
from fosutil.devices.hpe3par import Hpe3Par
from fosutil.models import AliasObject, ZoneObject
from fosutil.utils import (
    WwnValidator,
    normalize_wwn,
    generate_checkbox,
)


FORM_STYLE = style_from_dict(
    {
        Token.QuestionMark: "#FFCC00 bold",
        Token.Selected: "#51F89D",
        Token.Pointer: "#FFCC00",
        Token.Answer: "#51F89D bold",
        Token.Separator: "#51F89D",
    }
)


BANNER = r'''
    __________  _____       __  _ __
   / ____/ __ \/ ___/__  __/ /_(_) /
  / /_  / / / /\__ \/ / / / __/ / /
 / __/ / /_/ /___/ / /_/ / /_/ / /
/_/    \____//____/\__,_/\__/_/_/

FOSutil - Brocade FOS automation tool
Supported arrays
- HPE 3PAR
'''


def banner() -> None:
    print(BANNER)


def get_target_brocade(result: Dict[str, str]) -> List[Brocade]:
    target_brc = []
    if result["site"] == SITE_PRI:
        if result["fabric"] == "fabA":
            target_brc = [
                Brocade(
                    BRC_PRI["fabA"],
                    result["site"],
                    secrets["san_switches"][BRC_PRI["fabA"]]["host"],
                )
            ]
        elif result["fabric"] == "fabB":
            target_brc = [
                Brocade(
                    BRC_PRI["fabB"],
                    result["site"],
                    secrets["san_switches"][BRC_PRI["fabB"]]["host"],
                )
            ]
        else:
            target_brc = [
                Brocade(
                    BRC_PRI["fabA"],
                    result["site"],
                    secrets["san_switches"][BRC_PRI["fabA"]]["host"],
                ),
                Brocade(
                    BRC_PRI["fabB"],
                    result["site"],
                    secrets["san_switches"][BRC_PRI["fabB"]]["host"],
                ),
            ]
    elif result["site"] == SITE_SEC:
        if result["fabric"] == "fabA":
            target_brc = [
                Brocade(
                    BRC_SEC["fabA"],
                    result["site"],
                    secrets["san_switches"][BRC_SEC["fabA"]]["host"],
                )
            ]
        elif result["fabric"] == "fabB":
            target_brc = [
                Brocade(
                    BRC_SEC["fabB"],
                    result["site"],
                    secrets["san_switches"][BRC_SEC["fabB"]]["host"],
                )
            ]
        else:
            target_brc = [
                Brocade(
                    BRC_SEC["fabA"],
                    result["site"],
                    secrets["san_switches"][BRC_SEC["fabA"]]["host"],
                ),
                Brocade(
                    BRC_SEC["fabB"],
                    result["site"],
                    secrets["san_switches"][BRC_SEC["fabB"]]["host"],
                ),
            ]
    return target_brc


def confirm_operation() -> bool:
    result = prompt(
        [
            {
                "type": "confirm",
                "message": "Do you confirm the above operations?",
                "name": "confirm",
                "default": False,
            }
        ],
        style=FORM_STYLE,
    )
    return result["confirm"]


def display_unified_zones(zone_list: List[ZoneObject]) -> None:
    unified = {}
    pattern = re.compile(r"([0-9a-zA-Z].*?)_.*")

    for z in zone_list:
        unified[z.alias_a] = []
    for z in zone_list:
        unified[z.alias_a].extend(pattern.findall(z.alias_b))
    for z in zone_list:
        unified[z.alias_a] = sorted(set(unified[z.alias_a]))

    if unified == {}:
        print("Zoning for specified host not found in fabric")
    else:
        for host in unified:
            host_only = f"{host} => "
            print(cyan(host_only))
            print(*unified[host], sep=", ")


def check_zone() -> None:
    menu = [
        {"type": "list", "name": "site", "message": "Choose site", "choices": [SITE_PRI, SITE_SEC]},
        {
            "type": "list",
            "name": "fabric",
            "message": "Choose fabric",
            "choices": ["fabA+fabB", "fabA", "fabB"],
        },
        {"type": "input", "name": "alias", "message": "Define host/alias name"},
    ]
    result = prompt(menu, style=FORM_STYLE)
    target_brc = get_target_brocade(result)

    for dev in target_brc:
        dev.connect()
        zones = dev.get_zone_info(result["alias"])
        print(green(f"-- Zoning in {dev.fabric} --", "bright"))
        display_unified_zones(zones)
        dev.disconnect()


def check_alias() -> None:
    form_part1 = [
        {"type": "list", "name": "site", "message": "Choose site", "choices": [SITE_PRI, SITE_SEC]},
        {
            "type": "list",
            "name": "variant",
            "message": "Choose search type (ex. by alias or by WWN)",
            "choices": ["alias", "WWN"],
        },
    ]
    variant_alias = [
        {"type": "input", "name": "data", "message": "Define host/hosts alias (full or partial)"}
    ]
    variant_wwn = [
        {
            "type": "input",
            "name": "data",
            "message": "Define valid WWN",
            "validate": WwnValidator,
        }
    ]

    part1 = prompt(form_part1, style=FORM_STYLE)
    result = {}
    if part1["variant"] == "alias":
        result = prompt(variant_alias, style=FORM_STYLE)
    elif part1["variant"] == "WWN":
        result = prompt(variant_wwn, style=FORM_STYLE)

    result["site"] = part1["site"]
    result["fabric"] = "fabA"

    is_wwn = WWN_PATTERN.search(result["data"])
    target_brc = get_target_brocade(result)

    for dev in target_brc:
        dev.connect()
        if is_wwn:
            aliases = dev.get_alias_details(normalize_wwn(result["data"]))
        else:
            wwns = dev.get_wwwns(result["data"])
            aliases = dev.get_alias_details(wwns)

        print(green(f"-- Information from {dev.fabric} --", "bright"))
        if aliases == []:
            print(f"Host WWN not found in {dev.fabric}")
        else:
            for obj in aliases:
                obj.display()
        dev.disconnect()


def create_alias() -> None:
    menu_s1 = [
        {"type": "list", "name": "site", "message": "Choose site", "choices": [SITE_PRI, SITE_SEC]},
        {
            "type": "list",
            "name": "fabric",
            "message": "Choose fabric",
            "choices": ["fabA+fabB", "fabA", "fabB"],
        },
    ]
    result = prompt(menu_s1, style=FORM_STYLE)
    target_brc = get_target_brocade(result)

    for dev in target_brc:
        end = False
        alias_to_check = []
        while end != True:
            get_alias_to_create = [
                {
                    "type": "input",
                    "name": "alias",
                    "message": f"Define new host alias in {dev.fabric}",
                },
                {
                    "type": "input",
                    "name": "wwn",
                    "message": f"Define new host WWN in {dev.fabric}",
                    "validate": WwnValidator,
                },
            ]
            alias_info = prompt(get_alias_to_create, style=FORM_STYLE)
            alias_to_check.append(
                {"alias": alias_info["alias"], "wwn": normalize_wwn(alias_info["wwn"])}
            )

            next_result = prompt(
                [
                    {
                        "type": "confirm",
                        "message": f"Do you want to define another host in {dev.fabric}?",
                        "name": "confirm",
                        "default": False,
                    }
                ],
                style=FORM_STYLE,
            )

            if next_result["confirm"] == True:
                end = False
            else:
                end = True

        print(f"Checking given aliases in {dev.fabric}...")
        dev.connect()
        for a in alias_to_check:
            dev.create_alias(a["alias"], [a["wwn"]])
            dev.add_portname(a["alias"], a["wwn"])

        print(green("--- Summary ---", "bright"))
        for a in dev.cmd_register:
            print(a)

    commit = prompt(
        [
            {
                "type": "confirm",
                "message": "Do you want to create the above aliases?",
                "name": "confirm",
                "default": False,
            }
        ],
        style=FORM_STYLE,
    )

    if commit["confirm"] == True:
        for dev in target_brc:
            dev.connection.send_multiline(dev.cmd_register)
            dev.apply_config()
            print(f"Aliases created in {dev.fabric}")
            dev.cmd_register = []
            dev.disconnect()
    else:
        for dev in target_brc:
            dev.cmd_register = []
            dev.disconnect()
        print("Operation rejected, aliases will not be created")
    time.sleep(3)


def create_zone() -> None:
    menu = [
        {"type": "list", "name": "site", "message": "Choose site", "choices": [SITE_PRI, SITE_SEC]},
        {
            "type": "list",
            "name": "fabric",
            "message": "Choose fabric",
            "choices": ["fabA+fabB", "fabA", "fabB"],
        },
        {"type": "input", "name": "alias1", "message": "Define first host alias"},
        {"type": "input", "name": "alias2", "message": "Define second host alias"},
    ]
    result = prompt(menu, style=FORM_STYLE)

    target_brc = get_target_brocade(result)
    available_aliases = {"alias1": {"fabA": [], "fabB": []}, "alias2": {"fabA": [], "fabB": []}}

    for dev in target_brc:
        dev.connect()
        available_aliases["alias1"][dev.fabric] = dev.get_available_aliases(result["alias1"])
        available_aliases["alias2"][dev.fabric] = dev.get_available_aliases(result["alias2"])

    chosen_aliases = prompt(
        [
            {
                "type": "checkbox",
                "name": "alias1",
                "message": "Available aliases",
                "choices": [{"name": x} for x in generate_checkbox(available_aliases["alias1"])],
            },
            {
                "type": "checkbox",
                "name": "alias2",
                "message": "Availables aliases",
                "choices": [{"name": x} for x in generate_checkbox(available_aliases["alias2"])],
            },
        ],
        style=FORM_STYLE,
    )

    for dev in target_brc:
        print(green(f"--- Zoning to commit in {dev.fabric} ---", "bold"))
        cmds = []
        for k_a in available_aliases["alias1"][dev.fabric]:
            for k_b in available_aliases["alias2"][dev.fabric]:
                if k_a in chosen_aliases["alias1"] and k_b in chosen_aliases["alias2"]:
                    cmds.append(f'zonecreate "{k_a}_{k_b}", "{k_a}; {k_b}"')
                    cmds.append(f"cfgadd prod, {k_a}_{k_b}")
        dev.cmd_register = cmds
        for cmd in dev.cmd_register[::2]:
            print(cmd)
        for cmd in dev.cmd_register[1::2]:
            print(cmd)

    confirmation = confirm_operation()

    if confirmation:
        for dev in target_brc:
            dev.connection.send_multiline(dev.cmd_register)
            dev.apply_config()
            dev.cmd_register = []
            dev.disconnect()
            print(f"Changed commited in {dev.fabric}")
    else:
        for dev in target_brc:
            dev.cmd_register = []
            dev.disconnect()
        print("Operation rejected, config has not been modified")

    define_hosts = prompt(
        [
            {
                "type": "confirm",
                "message": "Do you want to create new hosts on arrays?",
                "name": "confirm",
                "default": False,
            }
        ],
        style=FORM_STYLE,
    )

    if define_hosts["confirm"] == True:
        host_pattern = re.compile(r"([0-9a-zA-Z]*)")
        chosen_aliases["alias1"] = sorted(
            set([host_pattern.match(x).group(0) for x in chosen_aliases["alias1"] if host_pattern.match(x)])
        )
        print(green("--- Suggested host names to create ---", "bold"))

        host_form = prompt(
            [
                {
                    "type": "checkbox",
                    "name": "hostsToCreate",
                    "message": "List of suggested host names to create",
                    "choices": [{"name": x} for x in chosen_aliases["alias1"]],
                },
                {
                    "type": "list",
                    "name": "persona",
                    "message": "Choose host persona",
                    "choices": ["Generic-ALUA", "VMWare", "WindowsServer"],
                },
                {
                    "type": "checkbox",
                    "name": "targetArrays",
                    "message": "On which arrays do you cant to create hosts?",
                    "choices": [
                        {"name": x["name"]}
                        for x in secrets["arrays"]
                        if x["site"] == result["site"]
                    ],
                },
            ],
            style=FORM_STYLE,
        )

        buf = []
        for dev in target_brc:
            dev.connect()
            for h in host_form["hostsToCreate"]:
                i = dev.get_wwwns(h)
                buf.append(dev.get_wwwns(h)[0])
            dev.disconnect()

        for ar in host_form["targetArrays"]:
            cl = Hpe3Par(ar).connect()

            for h in host_form["hostsToCreate"]:
                try:
                    host_wwns = [x["wwn"][0] for x in buf if h in x["alias"]]
                    cl.create_host(
                        h,
                        PERSONA_MAP.get(host_form["persona"]),
                        host_wwns,
                    )
                    print(f"[{ar}] Host defined {h} {host_wwns}")
                except Exception as ex:
                    print(f"ERROR: Defining host failed ({type(ex).__name__}). Reason: {ex}")

        add_to_hostset = prompt(
            [
                {
                    "type": "confirm",
                    "message": "Do you want to add defined hosts to hostset?",
                    "name": "confirm",
                    "default": False,
                }
            ],
            style=FORM_STYLE,
        )

        if add_to_hostset["confirm"] == True:
            for ar in host_form["targetArrays"]:
                cl = Hpe3Par(ar).connect()
                cl.get_defined_hosts()

                hostset_form = prompt(
                    [
                        {
                            "type": "list",
                            "name": "hostsetToAdd",
                            "message": "Choose hostset",
                            "choices": [
                                {"name": hs["name"]} for hs in cl.get_defined_hosts()["members"]
                            ],
                        },
                    ],
                    style=FORM_STYLE,
                )

                cl.modifyHostSet(hostset_form["hostsetToAdd"], 1, None, None, host_form["hostsToCreate"])
                print(
                    "Host/hosts", *host_form["hostsToCreate"], "added to hostset", hostset_form["hostsetToAdd"]
                )
            time.sleep(3)
        else:
            print("Host/hosts", *host_form["hostsToCreate"], "created")
            time.sleep(3)

    for dev in target_brc:
        dev.disconnect()


def remove_zone() -> None:
    menu = [
        {"type": "list", "name": "site", "message": "Choose site", "choices": [SITE_PRI, SITE_SEC]},
        {
            "type": "list",
            "name": "fabric",
            "message": "Choose fabric",
            "choices": ["fabA+fabB", "fabA", "fabB"],
        },
        {"type": "input", "name": "alias1", "message": "Define first host alias"},
        {"type": "input", "name": "alias2", "message": "Define second host alias"},
    ]
    result = prompt(menu, style=FORM_STYLE)

    target_brc = get_target_brocade(result)
    available_zones = {"fabA": [], "fabB": []}

    for dev in target_brc:
        dev.connect()
        available_zones[dev.fabric] = [
            a
            for a in dev.get_zone_info(result["alias1"])
            if result["alias1"] in a.name and result["alias2"] in a.name
        ]

    if available_zones["fabA"] == [] and available_zones["fabB"] == []:
        print("Zoning not found for given host aliases")
        for dev in target_brc:
            dev.disconnect()

    chosen_zones = prompt(
        [
            {
                "type": "checkbox",
                "name": "zones_to_del",
                "message": "Available zones",
                "choices": [
                    {"name": x.name} for x in available_zones["fabA"] + available_zones["fabB"]
                ],
            },
        ],
        style=FORM_STYLE,
    )

    for dev in target_brc:
        print(green(f"--- Zoning to remove in {dev.fabric} ---", "bold"))
        for z in available_zones[dev.fabric]:
            if z.name in chosen_zones["zones_to_del"]:
                dev.cmd_register.append(f"zonedelete {z.name}")
                dev.cmd_register.append(f"cfgremove prod, {z.name}")
        for cmd in dev.cmd_register[::2]:
            print(cmd)
        for cmd in dev.cmd_register[1::2]:
            print(cmd)

    confirmation = confirm_operation()

    if confirmation:
        for dev in target_brc:
            dev.connection.send_multiline(dev.cmd_register)
            dev.apply_config()
            dev.cmd_register = []
            dev.disconnect()
            print(f"Changed commited in {dev.fabric}")
    else:
        for dev in target_brc:
            dev.cmd_register = []
            dev.disconnect()
            print("Operation rejected, config has not been modified")

    define_hosts = prompt(
        [
            {
                "type": "confirm",
                "message": "Do you want to remove host definition from array?",
                "name": "confirm",
                "default": False,
            }
        ],
        style=FORM_STYLE,
    )

    if define_hosts["confirm"] == True:
        host_pattern = re.compile(r"([0-9a-zA-Z]*)")
        print(green("--- Suggested hosts to remove ---", "bold"))

        host_form = prompt(
            [
                {
                    "type": "checkbox",
                    "name": "hostsToRemove",
                    "message": "List of suggested hosts to remove",
                    "choices": [
                        {"name": x}
                        for x in sorted(
                            set(
                                [
                                    host_pattern.findall(x)[0]
                                    for x in chosen_zones["zones_to_del"]
                                ]
                            )
                        )
                    ],
                },
                {
                    "type": "checkbox",
                    "name": "targetArrays",
                    "message": "On which arrays do you want to remove host from",
                    "choices": [
                        {"name": x["name"]}
                        for x in secrets["arrays"]
                        if x["site"] == result["site"]
                    ],
                },
            ],
            style=FORM_STYLE,
        )

        print(green("--- Hosts to remove from ---".format(*host_form["targetArrays"], sep=" "), "bold"))
        print(*host_form["hostsToRemove"], sep=" ")

        confirmation_2 = confirm_operation()

        if confirmation_2:
            for ar in host_form["targetArrays"]:
                cl = Hpe3Par(ar).connect()

                for h in host_form["hostsToRemove"]:
                    cl.remove_host_from_its_hostset(h)
                    try:
                        cl.delete_host(h)
                        print(f"[{ar}] Host removed {h}")
                    except Exception as ex:
                        print(f"ERROR: Host removal failed ({type(ex).__name__}). Reason: {ex}")
        else:
            print("Operation rejected, hosts have not been removed from array")

        time.sleep(3)

    for dev in target_brc:
        dev.cmd_register = []
        dev.disconnect()


def remove_alias() -> None:
    menu = [
        {"type": "list", "name": "site", "message": "Choose site", "choices": [SITE_PRI, SITE_SEC]},
        {
            "type": "list",
            "name": "fabric",
            "message": "Choose fabric",
            "choices": ["fabA+fabB", "fabA", "fabB"],
        },
        {"type": "input", "name": "alias", "message": "Define alises to remove"},
    ]
    result = prompt(menu, style=FORM_STYLE)

    target_brc = get_target_brocade(result)
    available_aliases = {"fabA": [], "fabB": []}

    for dev in target_brc:
        dev.connect()
        t = []
        for a in dev.get_available_aliases(result["alias"]):
            alias_obj = dev.get_alias_details(dev.get_wwwns(a))
            available_aliases[dev.fabric].append(alias_obj)

    if available_aliases["fabA"] == [] and available_aliases["fabB"] == []:
        print("Defined alias/aliases not found in any fabric")
        time.sleep(3)

    for a in available_aliases["fabA"] + available_aliases["fabB"]:
        print(a.display())

    chosen_aliases = prompt(
        [
            {
                "type": "checkbox",
                "name": "alias_to_del",
                "message": "Choose available aliases to remove",
                "choices": [
                    {"name": f"{a.name}"}
                    for a in available_aliases["fabA"] + available_aliases["fabB"]
                ],
            },
        ],
        style=FORM_STYLE,
    )

    for dev in target_brc:
        print(green(f"--- Aliases to remove in {dev.fabric} ---", "bold"))
        for a in available_aliases[dev.fabric]:
            if a in chosen_aliases["alias_to_del"]:
                dev.remove_alias(a)
                dev.remove_portname(a)
        for cmd in dev.cmd_register[::2]:
            print(cmd)
        for cmd in dev.cmd_register[1::2]:
            print(cmd)

    confirmation = confirm_operation()

    if confirmation:
        for dev in target_brc:
            dev.connection.send_multiline(dev.cmd_register)
            dev.apply_config()
            dev.cmd_register = []
            dev.disconnect()
            print(f"Changes commited in {dev.fabric}")
    else:
        for dev in target_brc:
            dev.cmd_register = []
            dev.disconnect()
        print("Operation rejected, config has not been modified")


def main_menu() -> None:
    banner()
    try:
        menu = [
            {
                "type": "list",
                "name": "option",
                "message": "Choose operation",
                "choices": [
                    {"name": "Check active zoning configuration", "value": "chk_zone"},
                    {"name": "Detailed information about host", "value": "chk_alias"},
                    {"name": "Create alias", "value": "cr_alias"},
                    {"name": "Remove alias", "value": "rem_alias"},
                    {"name": "Create zoning", "value": "cr_zone"},
                    {"name": "Remove zoning", "value": "rem_zone"},
                    {"name": "Exit", "value": "exit"},
                ],
            },
        ]
        chosen_option = prompt(menu, style=FORM_STYLE)

        if chosen_option["option"] == "chk_zone":
            check_zone()
        elif chosen_option["option"] == "chk_alias":
            check_alias()
        elif chosen_option["option"] == "cr_alias":
            create_alias()
        elif chosen_option["option"] == "rem_alias":
            remove_alias()
        elif chosen_option["option"] == "cr_zone":
            create_zone()
        elif chosen_option["option"] == "rem_zone":
            remove_zone()
        elif chosen_option["option"] == "exit":
            exit()
        else:
            print("Unsupported yet")
            exit()
    except KeyError:
        print("Closing script")
        exit()


def run() -> None:
    main_menu()
