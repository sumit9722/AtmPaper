"""Offline revision runner; never rebuilds or modifies Restart 6."""
import importlib.metadata
import platform
import subprocess
import sys
from common import *


def main():
    save(QA / "status.json", {"status": "RUNNING", "scientific_review": "PENDING", "models_fitted": False})
    save(QA / "validation.json", {"status": "NOT_YET_VALIDATED"})
    test = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
                          capture_output=True, text=True)
    (QA / "regression_tests.log").write_text(test.stdout + test.stderr)
    if test.returncode:
        raise RuntimeError(test.stdout + test.stderr)
    save(QA / "environment.json", {"python": platform.python_version(),
         "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pyproj")}})
    for name in ("build.py", "validate.py", "report.py", "verify_release.py"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / name)], check=True)


if __name__ == "__main__":
    main()
