#!/usr/bin/env python3
"""Bundle src/paraspool.py + assets into dist/paraspool.py (the file users install)."""
import base64, gzip, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
import paraspool  # noqa: E402

src = (HERE / "src" / "paraspool.py").read_text()
embedded = {k: base64.b64encode(gzip.compress(p.read_bytes(), 9)).decode() for k, p in paraspool._DEV_PATHS.items()}
marker = "_EMBEDDED: dict[str, str] = {}"
assert marker in src
lines = ["_EMBEDDED: dict[str, str] = {"] + [f"    {k!r}: {v!r}," for k, v in embedded.items()] + ["}"]
out = src.replace(marker, "\n".join(lines), 1)
# Inline python/rim.py (everything after its `from __future__` line) so the release needs no repo.
rim = (HERE.parent / "python" / "rim.py").read_text()
rim_body = rim.split("from __future__ import annotations\n", 1)[1].split('\nif __name__ == "__main__":', 1)[0]
assert "# RIM_PY_INLINE" in out
out = out.replace("# RIM_PY_INLINE", rim_body, 1)
dist = HERE / "dist"; dist.mkdir(exist_ok=True)
import re
version = re.search(r'^# version = "([^"]+)"', src, re.M).group(1)
for stale in dist.glob("paraspool*.py"):
    stale.unlink()
name = f"paraspool_v{version}_any.py"  # versioned so the upload target is unambiguous
(dist / name).write_text(out)
print(f"wrote dist/{name} ({len(out) // 1024} KB)")
