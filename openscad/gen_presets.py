#!/usr/bin/env python3
"""Regenerate the preset block in src/rim.scad from ../presets/brand_presets.json.

Run after editing the JSON:  python3 openscad/gen_presets.py
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAD = HERE / "src" / "rim.scad"
PRESETS = HERE.parent / "presets" / "brand_presets.json"

def scad_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def render(presets):
    names = list(presets) + ["Custom"]
    enum = ", ".join(names)
    diam = "\n".join(f'    (spool_type == {scad_str(n)}) ? {p["diameter"]} :' for n, p in presets.items())
    label = "\n".join(f'    (spool_type == {scad_str(n)}) ? {scad_str(p["label"])} :' for n, p in presets.items())
    return f"""// BEGIN GENERATED PRESETS (edit presets/brand_presets.json, then run openscad/gen_presets.py)
/* [Preset Selection] */
// Select your spool brand. Choose "Custom" to use manual settings below.
spool_type = "{names[0]}"; // [{enum}]
// END GENERATED PRESETS""", f"""// BEGIN GENERATED LOOKUP
spool_diameter =
{diam}
    manual_spool_diameter;

label_text =
{label}
    manual_label_text;
// END GENERATED LOOKUP"""

def main(check=False):
    presets = json.loads(PRESETS.read_text())
    src = SCAD.read_text()
    enum_block, lookup_block = render(presets)
    out = re.sub(r"// BEGIN GENERATED PRESETS.*?// END GENERATED PRESETS", lambda _: enum_block, src, flags=re.S)
    out = re.sub(r"// BEGIN GENERATED LOOKUP.*?// END GENERATED LOOKUP", lambda _: lookup_block, out, flags=re.S)
    if out == src:
        return 0
    if check:
        print("rim.scad is stale; run openscad/gen_presets.py", file=sys.stderr)
        return 1
    SCAD.write_text(out)
    print("rim.scad updated")
    return 0

if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv))
