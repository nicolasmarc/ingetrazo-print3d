# SPDX-License-Identifier: GPL-3.0-or-later
"""Build ``dist/print3d-<version>.zip`` byte for byte the same on
every machine (fixed dates and order) and print its SHA-256."""
from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "print3d"
ID = "print3d"


def version() -> str:
    text = (PKG / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)


def build() -> Path:
    out = ROOT / "dist" / f"{ID}-{version()}.zip"
    out.parent.mkdir(exist_ok=True)
    files = sorted(p for p in PKG.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts
                   and p.suffix != ".pyc")
    files += [ROOT / "LICENSE", ROOT / "README.md"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            arc = (p.relative_to(ROOT) if p.parent != ROOT
                   else Path("print3d") / p.name)
            info = zipfile.ZipInfo(arc.as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes())
    return out


if __name__ == "__main__":
    path = build()
    print(path.relative_to(ROOT))
    print(hashlib.sha256(path.read_bytes()).hexdigest())
