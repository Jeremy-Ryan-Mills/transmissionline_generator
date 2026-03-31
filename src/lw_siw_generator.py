"""
SIW Leaky Wave Antenna / Waveguide Layout Generator for KLayout
===============================================================
HOW TO RUN:
  1. Open KLayout -> File -> New Layout (accept defaults)
  2. Macros -> Macro Editor (F5)
  3. Paste this script, press Run

STRUCTURE (left to right):
  [microstrip feed] -> [taper] -> [SIW body with slots] -> [taper] -> [microstrip feed]

LAYER STRUCTURE:
  m1   = solid ground plane (full rectangle, bottom copper)
  m2   = top conductor, drawn as regions of copper:
           - two via wall strips (top and bottom edges of SIW)
           - solid fill between slots in the SIW body
           - taper polygons at each end
           - narrow microstrip feed at each end
  via1 = two rows of circles forming the SIW sidewalls

LEAKY WAVE MECHANISM:
  Rectangular slots are cut into the top conductor (m2) periodically.
  The copper BETWEEN the slots is drawn as separate rectangles on m2.
  Each slot acts as a radiating element — energy leaks out as a wave
  propagates down the guide.
"""

import pya
import math

# ===========================================================================
# PARAMETERS — edit these
# ===========================================================================

LAYER_M1   = (1, 0)   # m1  bottom ground plane
LAYER_M2   = (2, 0)   # m2  top conductor
LAYER_VIA1 = (1, 1)   # via1 sidewall vias

# --- Via geometry ---
VIA_DIAMETER    = 0.3    # mm  drill diameter
VIA_PITCH       = 0.6    # mm  center-to-center spacing along row
VIA_SEGMENTS    = 64     # polygon sides approximating circle
VIA_STRIP_WIDTH = 1.0    # mm  width of m2 copper strip along each via row

# --- SIW body ---
SIW_WIDTH  = 28.0        # mm  center-to-center between the two via rows
SIW_LENGTH = 60.0        # mm  length of the SIW section (excluding tapers and feeds)

# --- Leaky wave slots (cut into top conductor m2) ---
SLOT_WIDTH   = 2.0       # mm  slot dimension along the waveguide (x direction)
SLOT_HEIGHT  = 14.0      # mm  slot dimension across the waveguide (y direction)
                         #     typically ~SIW_WIDTH/2, centered
SLOT_PERIOD  = 6.0       # mm  center-to-center period between slots
SLOT_OFFSET  = 3.0       # mm  x offset of first slot from start of SIW body

# --- Taper transition ---
TAPER_LENGTH = 10.0      # mm  length of the taper section

# --- Microstrip feed ---
FEED_WIDTH  = 1.5        # mm  narrow feed line width (~50 ohm)
FEED_LENGTH = 10.0       # mm  length of feed stub

# --- Ground plane margin ---
GND_MARGIN  = 3.0        # mm  extra m1 copper outside the outermost via rows

# ===========================================================================
# DERIVED
# ===========================================================================
VIA_RADIUS = VIA_DIAMETER / 2.0

# Y positions (centered on y=0 for the SIW)
Y_CENTER   = 0.0
Y_TOP_ROW  = Y_CENTER + SIW_WIDTH / 2.0   # top via row
Y_BOT_ROW  = Y_CENTER - SIW_WIDTH / 2.0   # bottom via row

# X layout (left to right):
#  0                          = left edge of m1
#  FEED_LENGTH                = end of left feed / start of left taper
#  FEED_LENGTH + TAPER_LENGTH = end of left taper / start of SIW body
#  ... + SIW_LENGTH           = end of SIW body / start of right taper
#  ... + TAPER_LENGTH         = end of right taper / start of right feed
#  ... + FEED_LENGTH          = right edge of m1

X0          = 0.0
X_FEED_END  = FEED_LENGTH
X_TAPER_END = FEED_LENGTH + TAPER_LENGTH
X_SIW_END   = FEED_LENGTH + TAPER_LENGTH + SIW_LENGTH
X_RTAPER_END= FEED_LENGTH + TAPER_LENGTH + SIW_LENGTH + TAPER_LENGTH
X_TOTAL     = FEED_LENGTH + TAPER_LENGTH + SIW_LENGTH + TAPER_LENGTH + FEED_LENGTH

# Via rows run only along the SIW body
X_VIA_START = X_TAPER_END
X_VIA_END   = X_SIW_END

# m1 height spans SIW width + margins on each side
M1_Y_BOT = Y_BOT_ROW - GND_MARGIN
M1_Y_TOP = Y_TOP_ROW + GND_MARGIN

# ===========================================================================
# HELPERS
# ===========================================================================
def to_dbu(mm, u):
    return int(round(mm / u))

def box(x1, y1, x2, y2, u):
    return pya.Box(to_dbu(x1,u), to_dbu(y1,u),
                   to_dbu(x2,u), to_dbu(y2,u))

def poly(pts_mm, u):
    """Make a polygon from a list of (x,y) tuples in mm."""
    return pya.Polygon([pya.Point(to_dbu(x,u), to_dbu(y,u)) for x,y in pts_mm])

def circle(cx, cy, r, n, u):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(pya.Point(to_dbu(cx + r*math.cos(a), u),
                             to_dbu(cy + r*math.sin(a), u)))
    return pya.Polygon(pts)

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
        cell = layout.create_cell("SIW_LEAKY_WAVE_ANT")
        cv.cell_name = cell.name
        print(f"Created cell: {cell.name}")

    lm1  = layout.layer(LAYER_M1[0],   LAYER_M1[1])
    lm2  = layout.layer(LAYER_M2[0],   LAYER_M2[1])
    lvia = layout.layer(LAYER_VIA1[0], LAYER_VIA1[1])
    print(f"Layers — m1:{lm1}  m2:{lm2}  via1:{lvia}")

    n = 0

    # -----------------------------------------------------------------------
    # 1. M1 — solid ground plane
    # -----------------------------------------------------------------------
    cell.shapes(lm1).insert(box(X0, M1_Y_BOT, X_TOTAL, M1_Y_TOP, u))
    n += 1
    print(f"[m1] Ground plane: {X_TOTAL:.2f} x {M1_Y_TOP - M1_Y_BOT:.2f} mm")

    # -----------------------------------------------------------------------
    # 2. M2 — left microstrip feed (narrow strip)
    # -----------------------------------------------------------------------
    cell.shapes(lm2).insert(box(X0, -FEED_WIDTH/2, X_FEED_END, FEED_WIDTH/2, u))
    n += 1
    print(f"[m2] Left feed: x=0 to {X_FEED_END:.2f}, width={FEED_WIDTH} mm")

    # -----------------------------------------------------------------------
    # 3. M2 — left taper (trapezoid: narrow at feed end, full SIW width at body)
    #    Drawn as a polygon with 4 corners
    # -----------------------------------------------------------------------
    left_taper_pts = [
        (X_FEED_END,  -FEED_WIDTH/2),   # bottom left (narrow)
        (X_FEED_END,   FEED_WIDTH/2),   # top left (narrow)
        (X_TAPER_END,  Y_TOP_ROW),      # top right (full SIW width)
        (X_TAPER_END,  Y_BOT_ROW),      # bottom right (full SIW width)
    ]
    cell.shapes(lm2).insert(poly(left_taper_pts, u))
    n += 1
    print(f"[m2] Left taper: x={X_FEED_END:.2f} to {X_TAPER_END:.2f}")

    # -----------------------------------------------------------------------
    # 4. M2 — SIW body top conductor
    #    Drawn as copper regions BETWEEN the slots, plus the via wall strips
    #
    #    Via wall strips run the full SIW length (top and bottom edges)
    #    The center region is filled EXCEPT where slots are cut
    # -----------------------------------------------------------------------

    # 4a. Top via wall strip (full SIW length)
    cell.shapes(lm2).insert(box(
        X_VIA_START, Y_TOP_ROW - VIA_STRIP_WIDTH,
        X_VIA_END,   Y_TOP_ROW + VIA_STRIP_WIDTH, u))
    n += 1

    # 4b. Bottom via wall strip (full SIW length)
    cell.shapes(lm2).insert(box(
        X_VIA_START, Y_BOT_ROW - VIA_STRIP_WIDTH,
        X_VIA_END,   Y_BOT_ROW + VIA_STRIP_WIDTH, u))
    n += 1

    print(f"[m2] Via wall strips: top y={Y_TOP_ROW:.2f}, bot y={Y_BOT_ROW:.2f}")

    # 4c. Center copper between slots
    #     The inner copper region spans from just inside the via walls
    #     to the slot edges in Y, and fills the gaps between slots in X
    inner_y_bot = Y_BOT_ROW + VIA_STRIP_WIDTH   # just above bottom via strip
    inner_y_top = Y_TOP_ROW - VIA_STRIP_WIDTH   # just below top via strip

    # Build list of slot X positions
    slot_starts = []
    x_slot = X_VIA_START + SLOT_OFFSET
    while x_slot + SLOT_WIDTH <= X_VIA_END:
        slot_starts.append(x_slot)
        x_slot += SLOT_PERIOD

    print(f"[m2] Slots: {len(slot_starts)} slots, period={SLOT_PERIOD} mm, size={SLOT_WIDTH}x{SLOT_HEIGHT} mm")

    # Draw copper regions between slots (filling gaps in the inner area)
    # First: copper from SIW start to first slot
    if slot_starts:
        # Left end cap (before first slot)
        if slot_starts[0] > X_VIA_START:
            cell.shapes(lm2).insert(box(X_VIA_START, inner_y_bot, slot_starts[0], inner_y_top, u))
            n += 1

        # Copper between consecutive slots
        for i in range(len(slot_starts) - 1):
            x_gap_start = slot_starts[i] + SLOT_WIDTH
            x_gap_end   = slot_starts[i+1]
            if x_gap_end > x_gap_start:
                cell.shapes(lm2).insert(box(x_gap_start, inner_y_bot, x_gap_end, inner_y_top, u))
                n += 1

        # Right end cap (after last slot)
        x_after_last = slot_starts[-1] + SLOT_WIDTH
        if x_after_last < X_VIA_END:
            cell.shapes(lm2).insert(box(x_after_last, inner_y_bot, X_VIA_END, inner_y_top, u))
            n += 1

        # Also draw the slot Y-side copper (above and below each slot,
        # between via wall strip and slot edge)
        slot_y_bot = Y_CENTER - SLOT_HEIGHT/2
        slot_y_top = Y_CENTER + SLOT_HEIGHT/2

        for xs in slot_starts:
            xe = xs + SLOT_WIDTH
            # Copper below slot (between bottom via wall strip and slot bottom)
            if slot_y_bot > inner_y_bot:
                cell.shapes(lm2).insert(box(xs, inner_y_bot, xe, slot_y_bot, u))
                n += 1
            # Copper above slot (between slot top and top via wall strip)
            if slot_y_top < inner_y_top:
                cell.shapes(lm2).insert(box(xs, slot_y_top, xe, inner_y_top, u))
                n += 1
    else:
        # No slots — just fill the whole inner region
        cell.shapes(lm2).insert(box(X_VIA_START, inner_y_bot, X_VIA_END, inner_y_top, u))
        n += 1
        print("[m2] Warning: no slots fit — check SLOT_OFFSET and SLOT_PERIOD vs SIW_LENGTH")

    # -----------------------------------------------------------------------
    # 5. M2 — right taper (mirror of left)
    # -----------------------------------------------------------------------
    right_taper_pts = [
        (X_SIW_END,    Y_BOT_ROW),       # bottom left (full SIW width)
        (X_SIW_END,    Y_TOP_ROW),       # top left (full SIW width)
        (X_RTAPER_END, FEED_WIDTH/2),    # top right (narrow)
        (X_RTAPER_END, -FEED_WIDTH/2),   # bottom right (narrow)
    ]
    cell.shapes(lm2).insert(poly(right_taper_pts, u))
    n += 1
    print(f"[m2] Right taper: x={X_SIW_END:.2f} to {X_RTAPER_END:.2f}")

    # -----------------------------------------------------------------------
    # 6. M2 — right microstrip feed
    # -----------------------------------------------------------------------
    cell.shapes(lm2).insert(box(X_RTAPER_END, -FEED_WIDTH/2, X_TOTAL, FEED_WIDTH/2, u))
    n += 1
    print(f"[m2] Right feed: x={X_RTAPER_END:.2f} to {X_TOTAL:.2f}")

    # -----------------------------------------------------------------------
    # 7. VIA1 — two rows of circles along the SIW body
    # -----------------------------------------------------------------------
    via_count = 0
    x = X_VIA_START
    while x <= X_VIA_END + 1e-6:
        cell.shapes(lvia).insert(circle(x, Y_TOP_ROW, VIA_RADIUS, VIA_SEGMENTS, u))
        cell.shapes(lvia).insert(circle(x, Y_BOT_ROW, VIA_RADIUS, VIA_SEGMENTS, u))
        x += VIA_PITCH
        via_count += 2
    n += via_count
    print(f"[via1] {via_count} circles ({via_count//2} per row)")

    # -----------------------------------------------------------------------
    # 8. Done
    # -----------------------------------------------------------------------
    mw.current_view().zoom_fit()

    print("\n" + "=" * 60)
    print("  SUCCESS — SIW Leaky Wave Antenna")
    print("=" * 60)
    print(f"  Total length    : {X_TOTAL:.1f} mm")
    print(f"  SIW width       : {SIW_WIDTH:.1f} mm")
    print(f"  Feed width      : {FEED_WIDTH:.1f} mm")
    print(f"  Taper length    : {TAPER_LENGTH:.1f} mm")
    print(f"  Slot size       : {SLOT_WIDTH:.1f} x {SLOT_HEIGHT:.1f} mm")
    print(f"  Slot period     : {SLOT_PERIOD:.1f} mm")
    print(f"  Number of slots : {len(slot_starts)}")
    print(f"  Via pitch/diam  : {VIA_PITCH}/{VIA_DIAMETER} mm")
    print(f"  Total shapes    : {n}")
    print("=" * 60)
    print("  TUNING GUIDE:")
    print("  - SLOT_PERIOD  controls beam angle (shorter = steeper)")
    print("  - SLOT_HEIGHT  controls how much energy leaks per slot")
    print("  - SLOT_WIDTH   controls slot resonance frequency")
    print("  - TAPER_LENGTH controls impedance match bandwidth")
    print("=" * 60)

run()
