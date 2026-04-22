#!/usr/bin/env python3

import warnings
import urllib3
from cryptography.utils import CryptographyDeprecationWarning

from fosutil.cli import run

urllib3.disable_warnings()
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)


if __name__ == "__main__":
    run()