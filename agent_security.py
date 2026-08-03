"""Backward-compatible import shim.

New code should import from the ``security`` package.
"""

from security import *  # noqa: F401,F403
