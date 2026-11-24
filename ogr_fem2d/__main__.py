# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""``python -m ogr_fem2d [model]``: the interface (spec 006)."""
import sys

from ogr_fem2d.gui.app import main

if __name__ == "__main__":
    sys.exit(main())
