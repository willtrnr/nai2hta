#! /usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

from . import main

if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
