#!/usr/bin/env python3
"""
tech_to_aedt.py  –  Convert a KLayout/AEDT .tech file into an HFSS setup script.

The tech file format (units: nm) is:
    // comment lines are ignored
    Label   Color   Elevation_nm   Thickness_nm

Layer classification by colour (override with --sheet-color / --diel-color etc.):
    red    → GDS sheet layer  (imported 2-D sheets; moved + thickened in HFSS)
    orange → copper box       (internal plane, solve_inside=False)
    green  → dielectric box   (prepreg  – default material PP017)
    blue   → dielectric box   (core     – default material Core039)
    yellow → via layer        (skipped by default; use --include-via to add as copper box)

Usage:
    python tech_to_aedt.py <tech_file> [options]

Options:
    --length  <mm>    Board X-extent in mm          (default 76.0)
    --height  <mm>    Board Y-extent in mm          (default 73.0)
    --air     <mm>    Air-box padding in mm         (default  5.0)
    --sheet-color <c> Comma-separated colour(s) that mark GDS sheet layers
                      (default: red)
    --include-via     Also create a via copper box  (default: skip)
    --out <file>      Output script path            (default: <stem>_setup.py)

Material defaults (edit the COLOR_MAP dict to change):
    green  → PP017   (er=4.4, tand=0.02)
    blue   → Core039 (er=4.6, tand=0.02)
    orange → copper
    yellow → copper  (only if --include-via)
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# colour → (layer_type, material, solve_inside)
#   layer_type: "sheet" | "conductor" | "dielectric" | "via" | "ignore"
# ---------------------------------------------------------------------------
COLOR_MAP: dict[str, tuple[str, str, bool]] = {
    "red":    ("sheet",      "copper",  False),
    "orange": ("conductor",  "copper",  False),
    "green":  ("dielectric", "PP017",   True),
    "blue":   ("dielectric", "Core039", True),
    "yellow": ("via",        "copper",  False),
}

# Dielectric material properties  {name: (er, tand)}
DIEL_PROPS: dict[str, tuple[str, str]] = {
    "PP017":   ("4.4", "0.02"),
    "Core039": ("4.6", "0.02"),
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_tech(path: Path) -> list[dict]:
    """Return list of layer dicts: {label, color, elv_nm, thk_nm}."""
    layers: list[dict] = []
    with path.open() as fh:
        for raw in fh:
            line = raw.split("//")[0].strip()       # strip inline comments
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            if parts[0].lower() == "label":         # skip header row
                continue
            label, color, elv_s, thk_s = parts[0], parts[1].lower(), parts[2], parts[3]
            try:
                layers.append(dict(
                    label=label,
                    color=color,
                    elv_nm=int(elv_s),
                    thk_nm=int(thk_s),
                ))
            except ValueError:
                print(f"  [skip] cannot parse line: {raw.rstrip()}", file=sys.stderr)
    return layers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def nm_to_mm(nm: int) -> float:
    return nm / 1_000_000


def fmt(v: float) -> str:
    """Format float without trailing zeros, up to 7 significant figures."""
    s = f"{v:.7f}".rstrip("0").rstrip(".")
    return s if s else "0"


def safe_var(label: str) -> str:
    """Return a valid Python identifier for a layer label.

    Labels that start with a digit are prefixed with 'L_' so the generated
    script does not contain invalid tokens like  1_Z  or  2_THK.
    """
    upper = label.upper()
    if upper[0].isdigit():
        return "L" + upper          # e.g. "1" → "L1",  "2" → "L2"
    return upper


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

def generate(layers: list[dict],
             length_mm: float,
             height_mm: float,
             air_mm: float,
             sheet_colors: set[str],
             include_via: bool,
             out_path: Path) -> None:

    # ------------------------------------------------------------------
    # Classify layers
    # ------------------------------------------------------------------
    sheet_layers: list[dict] = []
    box_layers:   list[dict] = []       # each entry gets 'material', 'solve_inside'

    for ly in layers:
        raw_type, mat, si = COLOR_MAP.get(ly["color"], ("ignore", "vacuum", True))

        # Allow user to override which colours are "sheet"
        if ly["color"] in sheet_colors:
            raw_type = "sheet"

        if raw_type == "sheet":
            sheet_layers.append(ly)
        elif raw_type == "via":
            if include_via:
                box_layers.append({**ly, "material": mat, "solve_inside": si})
            # else silently skip
        elif raw_type in ("conductor", "dielectric"):
            box_layers.append({**ly, "material": mat, "solve_inside": si})
        # "ignore" → drop

    if not sheet_layers:
        print("WARNING: no sheet layers found – check colour names / --sheet-color",
              file=sys.stderr)

    # Primary sheet layer (lowest elevation) drives Move/ThickenSheet
    sheet_layers_sorted = sorted(sheet_layers, key=lambda l: l["elv_nm"])
    primary = sheet_layers_sorted[0] if sheet_layers_sorted else layers[0]

    M1_Z   = nm_to_mm(primary["elv_nm"])
    M1_THK = nm_to_mm(primary["thk_nm"])

    # Top of stackup
    top_z = max(nm_to_mm(l["elv_nm"] + l["thk_nm"]) for l in layers)

    # Collect unique dielectric materials that need AddMaterial calls
    diel_mats: dict[str, tuple[str, str]] = {}
    for bl in box_layers:
        mat = bl["material"]
        if mat not in ("copper", "vacuum") and mat not in diel_mats:
            diel_mats[mat] = DIEL_PROPS.get(mat, ("3.5", "0.01"))

    # ------------------------------------------------------------------
    # Build output lines
    # ------------------------------------------------------------------
    L: list[str] = []
    a = L.append

    a('# -*- coding: utf-8 -*-')
    a('# Auto-generated by tech_to_aedt.py')
    a(f'# Source tech file: {out_path.stem.replace("_setup", "")}')
    a('# Run via  Tools -> Run Script  in HFSS')
    a('')

    # ── Stackup constants ─────────────────────────────────────────────
    a('# Stackup (mm, bottom to top) ──────────────────────────────────')
    col = 16   # column width for alignment
    for ly in layers:
        sv    = safe_var(ly["label"])
        z_mm  = nm_to_mm(ly["elv_nm"])
        th_mm = nm_to_mm(ly["thk_nm"])
        lhs_z  = f"{sv}_Z"
        lhs_th = f"{sv}_THK"
        a(f'{lhs_z:<{col}}= {fmt(z_mm)};  {lhs_th:<{col}}= {fmt(th_mm)}')

    a(f'{"TOP_Z":<{col}}= {fmt(top_z)}')
    a('')
    a('# Layout extents (mm)')
    a(f'TOTAL_LENGTH = {length_mm}')
    a(f'TOTAL_HEIGHT = {height_mm}')
    a(f'AIR_PADDING  = {air_mm}')
    a('')

    # ── HFSS object handles ───────────────────────────────────────────
    a('oDesktop.AddMessage("", "", 0, "Starting thicken and stackup")')
    a('')
    a('oProject           = oDesktop.GetActiveProject()')
    a('oDesign            = oProject.GetActiveDesign()')
    a('oEditor            = oDesign.SetActiveEditor("3D Modeler")')
    a('oBoundarySetup     = oDesign.GetModule("BoundarySetup")')
    a('oDefinitionManager = oProject.GetDefinitionManager()')
    a('')

    # ── AddMaterial ───────────────────────────────────────────────────
    if diel_mats:
        a('# Custom dielectric materials ───────────────────────────────────')
        a('for mat_name, er, tand in [')
        for mname, (er, tand) in diel_mats.items():
            a(f'        ("{mname}", "{er}", "{tand}"),')
        a(']:')
        a('    try:')
        a('        oDefinitionManager.AddMaterial(')
        a('            ["NAME:" + mat_name,')
        a('             "CoordinateSystemType:=", "Cartesian",')
        a('             ["NAME:AttachedData"],')
        a('             "permittivity:=",          er,')
        a('             "dielectric_loss_tangent:=", tand,')
        a('            ]')
        a('        )')
        a('        oDesktop.AddMessage("", "", 0, "Added " + mat_name)')
        a('    except:')
        a('        oDesktop.AddMessage("", "", 0, mat_name + " already exists")')
        a('')

    # ── Move + ThickenSheet ───────────────────────────────────────────
    a('# Thicken imported GDS sheets ───────────────────────────────────')
    a('sheets = list(oEditor.GetObjectsInGroup("Sheets"))')
    a('oDesktop.AddMessage("", "", 0, "Imported sheets: " + str(len(sheets)))')
    a('')
    a('if sheets:')
    primary_label = safe_var(primary["label"])
    a(f'    # Move to Z = {fmt(M1_Z)} mm  ({primary["label"]} elevation)')
    a('    oEditor.Move(')
    a('        ["NAME:Selections", "Selections:=", ",".join(sheets)],')
    a('        ["NAME:TranslateParameters",')
    a('         "CoordinateSystemID:=", -1,')
    a('         "TranslateVectorX:=", "0mm",')
    a('         "TranslateVectorY:=", "0mm",')
    a(f'         "TranslateVectorZ:=", str({primary_label}_Z) + "mm",')
    a('        ]')
    a('    )')
    a(f'    # Thicken by {fmt(M1_THK)} mm  ({primary["label"]} thickness)')
    a('    oEditor.ThickenSheet(')
    a('        ["NAME:Selections", "Selections:=", ",".join(sheets)],')
    a('        ["NAME:ThickenSheetParameters",')
    a(f'         "Thickness:=", str({primary_label}_THK) + "mm",')
    a('         "BothSides:=", False,')
    a('        ]')
    a('    )')
    a(f'    oDesktop.AddMessage("", "", 0,')
    a(f'        "Sheets thickened by " + str({primary_label}_THK) + "mm at Z=" + str({primary_label}_Z))')
    a('')

    # ── make_box helper ───────────────────────────────────────────────
    a('# Box helper ────────────────────────────────────────────────────')
    a('def make_box(name, x, y, z, xs, ys, zs, mat, solve_inside):')
    a('    try:')
    a('        oEditor.CreateBox(')
    a('            ["NAME:BoxParameters",')
    a('             "XPosition:=", str(x)  + "mm",')
    a('             "YPosition:=", str(y)  + "mm",')
    a('             "ZPosition:=", str(z)  + "mm",')
    a('             "XSize:=",     str(xs) + "mm",')
    a('             "YSize:=",     str(ys) + "mm",')
    a('             "ZSize:=",     str(zs) + "mm",')
    a('            ],')
    a('            ["NAME:Attributes",')
    a('             "Name:=",          name,')
    a('             "MaterialValue:=", \'"\' + mat + \'"\',')
    a('             "SolveInside:=",   solve_inside,')
    a('            ]')
    a('        )')
    a('        oDesktop.AddMessage("", "", 0, "Created box: " + name)')
    a('    except Exception as e:')
    a('        oDesktop.AddMessage("", "", 0, "Box error " + name + ": " + str(e))')
    a('')
    a('W = TOTAL_LENGTH')
    a('H = TOTAL_HEIGHT')
    a('')

    # ── Dielectric / conductor boxes ──────────────────────────────────
    a('# Dielectric and conductor boxes ────────────────────────────────')
    for bl in box_layers:
        label     = bl["label"]
        safe      = safe_var(label)
        mat       = bl["material"]
        si        = bl["solve_inside"]
        si_s      = "True" if si else "False"
        a(f'make_box("{label}", 0, 0, {safe}_Z, W, H, {safe}_THK, "{mat}", {si_s})')
    a('')

    # ── Airbox ────────────────────────────────────────────────────────
    a('# Airbox ────────────────────────────────────────────────────────')
    a('P = AIR_PADDING')
    a(f'make_box("airbox",')
    a(f'         -P, -P, {primary_label}_Z - P,')
    a(f'         W + 2*P, H + 2*P, TOP_Z + 2*P,')
    a( '         "vacuum", True)')
    a('')

    # ── Radiation boundary ────────────────────────────────────────────
    a('# Radiation boundary on airbox ──────────────────────────────────')
    a('try:')
    a('    oBoundarySetup.AssignRadiation(')
    a('        ["NAME:Rad1",')
    a('         "Objects:=", ["airbox"],')
    a('         "IsFssReference:=", False,')
    a('         "IsForPML:=",       False,')
    a('        ]')
    a('    )')
    a('    oDesktop.AddMessage("", "", 0, "Radiation boundary on airbox")')
    a('except Exception as e:')
    a('    oDesktop.AddMessage("", "", 0, "Radiation error: " + str(e))')
    a('')
    a('oProject.Save()')
    a('oDesktop.AddMessage("", "", 0, "DONE – add wave ports at feed line ends then analyze")')

    out_path.write_text("\n".join(L) + "\n")
    print(f"Written: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("tech_file",
                    help="Path to the .tech / .txt file")
    ap.add_argument("--length", type=float, default=76.0, metavar="mm",
                    help="Board X-extent in mm (default 76.0)")
    ap.add_argument("--height", type=float, default=73.0, metavar="mm",
                    help="Board Y-extent in mm (default 73.0)")
    ap.add_argument("--air",    type=float, default=5.0,  metavar="mm",
                    help="Airbox padding in mm (default 5.0)")
    ap.add_argument("--sheet-color", default="red", metavar="COLORS",
                    help="Comma-separated colour(s) for GDS sheet layers (default: red)")
    ap.add_argument("--include-via", action="store_true",
                    help="Create a via copper box instead of skipping it")
    ap.add_argument("--out", default=None, metavar="FILE",
                    help="Output path (default: <tech_stem>_setup.py)")
    args = ap.parse_args()

    tech_path = Path(args.tech_file)
    if not tech_path.exists():
        sys.exit(f"ERROR: file not found: {tech_path}")

    out_path = (Path(args.out) if args.out
                else tech_path.parent / (tech_path.stem + "_setup.py"))

    sheet_colors = {c.strip().lower() for c in args.sheet_color.split(",")}

    layers = parse_tech(tech_path)
    if not layers:
        sys.exit("ERROR: no layers parsed – check tech file format")

    print(f"Parsed {len(layers)} layers:")
    for ly in layers:
        ltype = COLOR_MAP.get(ly["color"], ("?",))[0]
        print(f"  {ly['label']:15s}  {ly['color']:8s}  [{ltype:11s}]"
              f"  elv={ly['elv_nm']:>9,} nm  thk={ly['thk_nm']:>9,} nm")

    generate(layers, args.length, args.height, args.air,
             sheet_colors, args.include_via, out_path)


if __name__ == "__main__":
    main()
