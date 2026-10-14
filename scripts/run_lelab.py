"""Use this checkout's settings with the separately locked LeLab runtime."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from so101_setup.lelab_app import main

if __name__ == "__main__":
    main()
