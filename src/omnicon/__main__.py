# Copyright (c) 2026 Chenglin Qiu (SHC - Super Han Chinese). All rights reserved.
# Licensed under the OmniCon Proprietary License. See LICENSE for details.
"""Entry point for `python -m omnicon`."""

import sys


def main() -> None:
    """Launch the OmniCon application."""
    # Defer heavy imports until main() is called
    from omnicon.app import create_app

    app = create_app(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
