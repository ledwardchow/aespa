from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    # Restore only the trusted runtime directory removed by Python's isolated
    # mode. This exposes aespa_runtime without re-enabling cwd/user site paths.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    runpy.run_path(sys.argv[1], run_name="__main__")
