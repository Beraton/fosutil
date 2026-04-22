import os
import re
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

SITE_PRI = "S01"
SITE_SEC = "S02"

BRC_PRI = {"fabA": "S01-brocade-lab-fabA", "fabB": "S01-brocade-lab-fabB"}
BRC_SEC = {"fabA": "S02-brocade-lab-fabA", "fabB": "S02-brocade-lab-fabB"}

WWN_PATTERN = re.compile(r"^(\w[0-9a-fA-F]{15}|\w[0-9a-fA-F:]{22})")
HOST_PATTERN = re.compile(r"([0-9a-zA-Z]*)")
ALIAS_PATTERN = re.compile(r"(?<=alias:\s)([0-9a-zA-Z_]*)")
ZONE_PATTERN = re.compile(r"(?<=zone:\s)([0-9a-zA-Z_]*)")
ALIAS_PAIR_PATTERN = re.compile(r"([0-9a-zA-Z_].*?.*); ([0-9a-zA-Z_].*?.*)")
WWN_OBJECT_PATTERN = re.compile(r"(\w[0-9a-fA-F:]{22})")
PORT_PATTERN = re.compile(r"(?<=Port Index: )[0-9]*")
PID_PATTERN = re.compile(r"\s([0-9a-fA-F]{6})")
SWITCH_NAME_PATTERN = re.compile(r'"([a-zA-Z0-9_-]*)"')
FULL_ALIAS_PATTERN = re.compile(r"([0-9a-zA-Z].*_p[0-9]{1})_([0-9a-zA-Z].*)")
NODEFIND_ALIAS_PATTERN = re.compile(r"(?<=Aliases: )[0-9a-zA-Z_ ]*")
NODEFIND_WWN_PATTERN = re.compile(r"(?<=WWPN\s)([0-9a-zA-Z:]{23})")

PERSONA_MAP = {
    "Generic-ALUA": {"persona": 2},
    "VMWare": {"persona": 8},
    "WindowsServer": {"persona": 11},
}


def load_secrets():
    with open(ENV_FILE_PATH, "r") as f:
        return yaml.safe_load(f)


secrets = load_secrets()