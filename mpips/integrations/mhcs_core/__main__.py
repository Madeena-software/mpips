"""Executable module entrypoint for MHCS Core Grabber workflow.

Allows invocation via::

    python -m mpips.integrations.mhcs_core ...
"""

from __future__ import annotations

import sys

from mpips.integrations.mhcs_core.cli import main

if __name__ == "__main__":
    sys.exit(main())
