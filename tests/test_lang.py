"""Every text shown is translated in French and Spanish, with the same
placeholders."""
import os
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from print3d import lang  # noqa: E402

PKG = Path(__file__).resolve().parents[1] / "print3d"
_LIT = re.compile(r'''\b(?:t|N_)\(\s*(["'])((?:(?!\1)[^\\]|\\.)*)\1''')


def _used():
    out = set()
    for f in PKG.glob("*.py"):
        if f.name == "lang.py":
            continue
        out |= {m[1] for m in _LIT.findall(f.read_text(encoding="utf-8"))}
    return out


def _fields(s):
    return sorted(f for _l, f, _s, _c in string.Formatter().parse(s) if f)


def test_same_keys_in_every_language():
    assert set(lang.FR) == set(lang.ES)


def test_every_shown_text_is_translated():
    used = _used()
    assert len(used) > 60
    missing = used - set(lang.FR)
    assert not missing, missing
    unused = set(lang.FR) - used
    assert not unused, unused


def test_placeholders_match():
    for key in lang.FR:
        assert _fields(lang.FR[key]) == _fields(key), key
        assert _fields(lang.ES[key]) == _fields(key), key


def test_decimal_mark_and_fallback():
    lang._forced = "es"
    try:
        assert lang.num(10.55, 1) in ("10,6", "10,5")
        assert lang.t("Apply") == "Aplicar"
        lang._forced = "de"
        assert lang.t("Apply") == "Apply" and lang.num(1.5) == "1.5"
    finally:
        lang._forced = None
