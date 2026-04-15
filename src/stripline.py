"""
Stripline Transmission Line Crosstalk Layout Generator for KLayout
==================================================================
HOW TO RUN:
  1. Open KLayout -> File -> New Layout (accept defaults)
  2. Macros -> Macro Editor (F5)
  3. Paste this script, press Run

STRUCTURE:
  Two parallel buried signal traces (aggressor + victim) sandwiched
  between two solid ground planes (m1 bottom, m2 top).
  Vary TRACE_SEPARATION between simulation runs to sweep crosstalk vs distance.

LAYER MAPPING (must match your Edit -> Layers panel):
  m1  (1/0) = bottom ground plane
  m2  (2/0) = top ground plane
  sig (3/0) = buried signal traces — add this layer in Edit -> Layers
              maps to Int1 or Int2 in your stackup
"""

import pya
import math

# ===========================================================================
# PARAMETERS — edit these
# ===========================================================================

LAYER_M1  = (1, 0)   # bottom ground plane
LAYER_M2  = (2, 0)   # top ground plane
LAYER_SIG = (3, 0)   # buried signal traces (Int1 or Int2)

# Signal traces
TRACE_WIDTH      = 1.0    # mm  width of each trace (run stripline calculator for 50 ohm)
TRACE_LENGTH     = 60.0   # mm  length of each trace
TRACE_SEPARATION = 2.0    # mm  edge-to-edge gap between aggressor and victim
                          #     VARY THIS for crosstalk sweep

# Ground plane margin outside the outermost trace edges
GND_MARGIN = 5.0          # mm

# Port pads at each end of each trace (makes simulation port attachment easier)
ADD_PADS   = True
PAD_WIDTH  = 2.0          # mm  pad wider than trace for port attach
PAD_LENGTH = 2.0          # mm  pad length at each end

# ===========================================================================
# DERIVED
# ===========================================================================
# Total span of both traces + gap
PAIR_SPAN  = 2 * TRACE_WIDTH + TRACE_SEPARATION

# Ground plane spans both traces plus margin on each outer edge
GND_WIDTH  = PAIR_SPAN + 2 * GND_MARGIN
TOTAL_LENGTH = TRACE_LENGTH

# Y positions — center the pair on y=0
# Aggressor (bottom trace)
AGG_Y_CENTER = -(TRACE_SEPARATION / 2.0 + TRACE_WIDTH / 2.0)
AGG_Y_BOT    = AGG_Y_CENTER - TRACE_WIDTH / 2.0
AGG_Y_TOP    = AGG_Y_CENTER + TRACE_WIDTH / 2.0

# Victim (top trace)
VIC_Y_CENTER = +(TRACE_SEPARATION / 2.0 + TRACE_WIDTH / 2.0)
VIC_Y_BOT    = VIC_Y_CENTER - TRACE_WIDTH / 2.0
VIC_Y_TOP    = VIC_Y_CENTER + TRACE_WIDTH / 2.0

# Ground plane Y extents
GND_Y_BOT = -GND_WIDTH / 2.0
GND_Y_TOP = +GND_WIDTH / 2.0

# ===========================================================================
# HELPERS
# ===========================================================================
def to_dbu(mm, u):
    return int(round(mm / u))

def box(x1, y1, x2, y2, u):
    return pya.Box(to_dbu(x1,u), to_dbu(y1,u),
                   to_dbu(x2,u), to_dbu(y2,u))

# ===========================================================================
# MAIN
# ===========================================================================
def run():
    app = pya.Application.instance()
    mw  = app.main_window()

    cv = mw.current_view().active_cellview()
    if cv is None or not cv.is_valid():
        raise RuntimeError("No layout open — go to File -> New Layout first.")

    layout = cv.layout()
    u = layout.dbu
    print(f"DBU = {u} mm")

    if layout.cells() > 0:
        cell = layout.cell(layout.top_cells()[0].cell_index())
        cell.clear()
        print(f"Cleared cell: {cell.name}")
    else:
        cell = layout.create_cell("STRIPLINE_CROSSTALK")
        cv.cell_name = cell.name
        print(f"Created cell: {cell.name}")

    lm1  = layout.layer(LAYER_M1[0],  LAYER_M1[1])
    lm2  = layout.layer(LAYER_M2[0],  LAYER_M2[1])
    lsig = layout.layer(LAYER_SIG[0], LAYER_SIG[1])
    print(f"Layers — m1:{lm1}  m2:{lm2}  sig:{lsig}")

    n = 0

    # -----------------------------------------------------------------------
    # 1. M1 — bottom ground plane (one solid rectangle, spans both traces)
    # -----------------------------------------------------------------------
    cell.shapes(lm1).insert(box(0, GND_Y_BOT, TOTAL_LENGTH, GND_Y_TOP, u))
    n += 1
    print(f"[m1] Bottom GND: {TOTAL_LENGTH:.2f} x {GND_WIDTH:.2f} mm")

    # -----------------------------------------------------------------------
    # 2. M2 — top ground plane (same footprint)
    # -----------------------------------------------------------------------
    cell.shapes(lm2).insert(box(0, GND_Y_BOT, TOTAL_LENGTH, GND_Y_TOP, u))
    n += 1
    print(f"[m2] Top GND: {TOTAL_LENGTH:.2f} x {GND_WIDTH:.2f} mm")

    # -----------------------------------------------------------------------
    # 3. SIG — aggressor trace (bottom)
    # -----------------------------------------------------------------------
    cell.shapes(lsig).insert(box(0, AGG_Y_BOT, TOTAL_LENGTH, AGG_Y_TOP, u))
    n += 1
    print(f"[sig] Aggressor: y={AGG_Y_BOT:.3f} to {AGG_Y_TOP:.3f}  center={AGG_Y_CENTER:.3f}")

    # -----------------------------------------------------------------------
    # 4. SIG — victim trace (top)
    # -----------------------------------------------------------------------
    cell.shapes(lsig).insert(box(0, VIC_Y_BOT, TOTAL_LENGTH, VIC_Y_TOP, u))
    n += 1
    print(f"[sig] Victim:    y={VIC_Y_BOT:.3f} to {VIC_Y_TOP:.3f}  center={VIC_Y_CENTER:.3f}")

    print(f"      Edge-to-edge separation: {TRACE_SEPARATION:.3f} mm")

    # -----------------------------------------------------------------------
    # 5. Port pads on each trace end
    # -----------------------------------------------------------------------
    if ADD_PADS:
        for y_center in [AGG_Y_CENTER, VIC_Y_CENTER]:
            py1 = y_center - PAD_WIDTH / 2.0
            py2 = y_center + PAD_WIDTH / 2.0
            # Left pad
            cell.shapes(lsig).insert(box(0, py1, PAD_LENGTH, py2, u))
            # Right pad
            cell.shapes(lsig).insert(box(TOTAL_LENGTH - PAD_LENGTH, py1, TOTAL_LENGTH, py2, u))
            n += 2
        print(f"[sig] Port pads: {PAD_LENGTH:.2f} x {PAD_WIDTH:.2f} mm at each end of each trace")

    mw.current_view().zoom_fit()

    print("\n" + "=" * 55)
    print("  SUCCESS — Stripline Crosstalk Layout")
    print("=" * 55)
    print(f"  Trace width      : {TRACE_WIDTH:.2f} mm")
    print(f"  Trace length     : {TRACE_LENGTH:.2f} mm")
    print(f"  Trace separation : {TRACE_SEPARATION:.2f} mm  <- vary for sweep")
    print(f"  GND width        : {GND_WIDTH:.2f} mm")
    print(f"  GND margin       : {GND_MARGIN:.2f} mm each side")
    print(f"  Total shapes     : {n}")
    print("=" * 55)
    print("  LAYER SUMMARY:")
    print(f"  m1  ({LAYER_M1[0]}/{LAYER_M1[1]}) = bottom ground plane")
    print(f"  m2  ({LAYER_M2[0]}/{LAYER_M2[1]}) = top ground plane")
    print(f"  sig ({LAYER_SIG[0]}/{LAYER_SIG[1]}) = aggressor + victim traces")
    print("=" * 55)
    print("  CROSSTALK SWEEP: change TRACE_SEPARATION and rerun")
    print("  Suggested values: 1x, 2x, 3x, 5x trace width")
    print("=" * 55)

run()