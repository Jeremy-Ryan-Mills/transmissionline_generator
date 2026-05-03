"""
Tapered CPW Transmission Line Layout Generator for KLayout
With solid via plane (replaces circular via wall) for HFSS simulation

Dimensions from PCB image annotations:
  Wide  section : signal = 0.293 mm, gap = 0.204 mm
  Narrow section : signal = 0.206 mm, gap = 0.140 mm
  End gaps (x3)  : ~0.103 mm each
"""

import pya
import math

# ===========================================================================
# PARAMETERS
# ===========================================================================

LAYER_M1    = (1, 0)
LAYER_M2    = (2, 0)
LAYER_VIA1  = (1, 1)
LAYER_LABEL = (10, 0)

# Signal trace widths (from image annotations)
W_WIDE      = 0.293    # mm — wide-section signal width
W_NARROW    = 0.206    # mm — narrow-section signal width

# CPW gaps — signal edge to inner ground edge (from image annotations)
G_WIDE      = 0.204    # mm — gap in wide section
G_NARROW    = 0.140    # mm — gap in narrow section

# Straight section lengths
L_WIDE      = 3.0      # mm — wide straight section
L_TAPER     = 2.0      # mm — linear taper transition
L_NARROW    = 3.0      # mm — narrow straight section

# Ground copper width beyond the gap (GND_MARGIN from original)
GND_MARGIN  = 1.0      # mm

# Via plane — solid filled strip (replaces individual via circles)
VIA_PLANE_WIDTH = 0.3  # mm — thickness of via plane, inset from outer ground edge

# ===========================================================================
# DERIVED
# ===========================================================================
TOTAL_LENGTH   = L_WIDE + L_TAPER + L_NARROW                          # 8.0 mm
TOTAL_HEIGHT   = W_WIDE + 2 * G_WIDE + 2 * GND_MARGIN                 # 2.905 mm
X_TAPER_START  = L_WIDE
X_TAPER_END    = L_WIDE + L_TAPER

# ===========================================================================
# HELPERS
# ===========================================================================
def to_dbu(mm, u):
    return int(round(mm / u))

def box(x1, y1, x2, y2, u):
    return pya.Box(to_dbu(x1, u), to_dbu(y1, u),
                   to_dbu(x2, u), to_dbu(y2, u))

def trapezoid(x1, y_bot1, y_top1, x2, y_bot2, y_top2, u):
    """Four-point polygon for a linearly tapered section."""
    pts = [
        pya.Point(to_dbu(x1, u), to_dbu(y_bot1, u)),
        pya.Point(to_dbu(x2, u), to_dbu(y_bot2, u)),
        pya.Point(to_dbu(x2, u), to_dbu(y_top2, u)),
        pya.Point(to_dbu(x1, u), to_dbu(y_top1, u)),
    ]
    return pya.Polygon(pts)

def label(text, x, y, u, shapes, layer):
    """Place a text label for port definition."""
    t = pya.Text(text, to_dbu(x, u), to_dbu(y, u))
    shapes(layer).insert(t)

# ===========================================================================
# MAIN
# ===========================================================================
def run():
    app = pya.Application.instance()
    mw  = app.main_window()

    cv = mw.current_view().active_cellview()
    if cv is None or not cv.is_valid():
        raise RuntimeError("No layout open.")

    layout = cv.layout()
    u = layout.dbu
    print(f"DBU          = {u} mm")
    print(f"TOTAL_LENGTH = {TOTAL_LENGTH} mm")
    print(f"TOTAL_HEIGHT = {TOTAL_HEIGHT:.4f} mm")

    if layout.cells() > 0:
        cell = layout.cell(layout.top_cells()[0].cell_index())
        cell.clear()
        print(f"Cleared cell: {cell.name}")
    else:
        cell = layout.create_cell("TAPERED_CPW")
        cv.cell_name = cell.name

    lm1  = layout.layer(LAYER_M1[0],    LAYER_M1[1])
    lm2  = layout.layer(LAYER_M2[0],    LAYER_M2[1])
    lvia = layout.layer(LAYER_VIA1[0],  LAYER_VIA1[1])
    llbl = layout.layer(LAYER_LABEL[0], LAYER_LABEL[1])

    # ── Section x-boundaries ────────────────────────────────────────
    x0 = 0.0                        # start of wide section
    x1 = L_WIDE                     # start of taper
    x2 = L_WIDE + L_TAPER           # start of narrow section
    x3 = TOTAL_LENGTH               # end of narrow section

    # ── Y coordinates — wide section (centred on TOTAL_HEIGHT/2) ───
    cy          = TOTAL_HEIGHT / 2.0
    sig_top_w   = cy + W_WIDE   / 2.0
    sig_bot_w   = cy - W_WIDE   / 2.0
    gnd_top_w   = sig_top_w + G_WIDE        # inner ground edge — top
    gnd_bot_w   = sig_bot_w - G_WIDE        # inner ground edge — bot
    out_top_w   = gnd_top_w + GND_MARGIN    # outer ground edge — top
    out_bot_w   = gnd_bot_w - GND_MARGIN    # outer ground edge — bot (= 0)

    # ── Y coordinates — narrow section ──────────────────────────────
    sig_top_n   = cy + W_NARROW / 2.0
    sig_bot_n   = cy - W_NARROW / 2.0
    gnd_top_n   = sig_top_n + G_NARROW
    gnd_bot_n   = sig_bot_n - G_NARROW
    out_top_n   = gnd_top_n + GND_MARGIN
    out_bot_n   = gnd_bot_n - GND_MARGIN

    # ── Via plane Y positions (anchored to wide outer edge) ─────────
    via_top_outer = out_top_w
    via_top_inner = out_top_w - VIA_PLANE_WIDTH
    via_bot_outer = out_bot_w
    via_bot_inner = out_bot_w + VIA_PLANE_WIDTH

    print(f"Center Y     = {cy:.4f} mm")
    print(f"Wide  : sig=[{sig_bot_w:.4f}, {sig_top_w:.4f}]  "
          f"gap=[{gnd_bot_w:.4f}, {gnd_top_w:.4f}]  "
          f"outer=[{out_bot_w:.4f}, {out_top_w:.4f}]")
    print(f"Narrow: sig=[{sig_bot_n:.4f}, {sig_top_n:.4f}]  "
          f"gap=[{gnd_bot_n:.4f}, {gnd_top_n:.4f}]  "
          f"outer=[{out_bot_n:.4f}, {out_top_n:.4f}]")

    n = 0

    # ── M1: Full ground plane (bottom metal) ─────────────────────────
    cell.shapes(lm1).insert(box(x0, out_bot_w, x3, out_top_w, u))
    n += 1

    # ── M2: Signal trace — wide section ─────────────────────────────
    cell.shapes(lm2).insert(box(x0, sig_bot_w, x1, sig_top_w, u))
    n += 1

    # M2: Signal trace — taper section
    cell.shapes(lm2).insert(trapezoid(x1, sig_bot_w, sig_top_w,
                                      x2, sig_bot_n, sig_top_n, u))
    n += 1

    # M2: Signal trace — narrow section
    cell.shapes(lm2).insert(box(x2, sig_bot_n, x3, sig_top_n, u))
    n += 1

    # ── M2: Top ground fill — wide section ──────────────────────────
    cell.shapes(lm2).insert(box(x0, gnd_top_w, x1, out_top_w, u))
    n += 1

    # M2: Top ground fill — taper section
    cell.shapes(lm2).insert(trapezoid(x1, gnd_top_w, out_top_w,
                                      x2, gnd_top_n, out_top_n, u))
    n += 1

    # M2: Top ground fill — narrow section
    cell.shapes(lm2).insert(box(x2, gnd_top_n, x3, out_top_n, u))
    n += 1

    # ── M2: Bottom ground fill — wide section ───────────────────────
    cell.shapes(lm2).insert(box(x0, out_bot_w, x1, gnd_bot_w, u))
    n += 1

    # M2: Bottom ground fill — taper section
    cell.shapes(lm2).insert(trapezoid(x1, out_bot_w, gnd_bot_w,
                                      x2, out_bot_n, gnd_bot_n, u))
    n += 1

    # M2: Bottom ground fill — narrow section
    cell.shapes(lm2).insert(box(x2, out_bot_n, x3, gnd_bot_n, u))
    n += 1

    # ── VIA1: Via PLANE — solid fill (replaces individual circles) ───
    # One solid rectangle per side running the full structure length.
    # Inset from the outer ground edge so it sits entirely within M2 copper.
    # Top via plane
    cell.shapes(lvia).insert(box(x0, via_top_inner, x3, via_top_outer, u))
    n += 1
    # Bottom via plane
    cell.shapes(lvia).insert(box(x0, via_bot_outer, x3, via_bot_inner, u))
    n += 1

    # ── Port labels (layer 10/0) for HFSS / EMX ─────────────────────
    label("p1", x0, cy, u, cell.shapes, llbl)   # wide-end port
    label("p2", x3, cy, u, cell.shapes, llbl)   # narrow-end port
    n += 2
    print(f"Port labels placed: p1 (wide end), p2 (narrow end)")

    mw.current_view().zoom_fit()

    print("\n" + "=" * 55)
    print("  SUCCESS")
    print(f"  Layout size   : {TOTAL_LENGTH:.3f} x {TOTAL_HEIGHT:.4f} mm")
    print(f"  Wide  section : W={W_WIDE} mm  G={G_WIDE} mm  ({L_WIDE} mm long)")
    print(f"  Taper section : {L_TAPER} mm long")
    print(f"  Narrow section: W={W_NARROW} mm  G={G_NARROW} mm  ({L_NARROW} mm long)")
    print(f"  Via plane     : solid fill, {VIA_PLANE_WIDTH} mm wide (layer {LAYER_VIA1})")
    print(f"  Total shapes  : {n}")
    print("=" * 55)
    print("  Port labels on layer 10/0:")
    print("  p1 = wide-end port  (x = 0)")
    print(f"  p2 = narrow-end port (x = {TOTAL_LENGTH:.1f} mm)")
    print("=" * 55)

run()