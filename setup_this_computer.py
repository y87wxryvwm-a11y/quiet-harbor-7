"""
One-time setup: lets every script in this repo find kit.py.

Run this file once (F5 or the Run button) with the Python environment you use
for this work, e.g. myenv. Run it again only if you create a new environment
or move the research folder.

Creates one file, inside the Python environment (not in this repo):
  research_repo.pth   a one-line text file holding this folder's location.
                      Python reads it at startup and adds this folder to the
                      places it looks for code, so `from kit import ...` works
                      from any project, in VS Code, Spyder, or a terminal.
To undo, delete that file; the script prints where it is.
"""

import site
import subprocess
import sys
import sysconfig
from pathlib import Path

repo = Path(__file__).resolve().parent
line = str(repo) + "\n"

targets = [Path(sysconfig.get_paths()["purelib"]), Path(site.getusersitepackages())]
for folder in targets:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        pth = folder / "research_repo.pth"
        pth.write_text(line, encoding="utf-8")
        break
    except PermissionError:
        continue
else:
    raise SystemExit(f"Could not write to any of: {', '.join(map(str, targets))}")

check = subprocess.run(
    [sys.executable, "-c", "import kit; print(kit.__file__)"],
    capture_output=True, text=True,
)
if check.returncode == 0:
    print(f"Done. Wrote {pth}")
    print(f"Scripts will now find kit.py at {check.stdout.strip()}")
else:
    print(f"Wrote {pth}, but kit.py still can't be found:")
    print(check.stderr.strip().splitlines()[-1])
