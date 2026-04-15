"""
SIW Leaky Wave Waveguide Crosstalk Layout Generator for KLayout
===============================================================
HOW TO RUN:
  1. Open KLayout -> File -> New Layout (accept defaults)
  2. Macros -> Macro Editor (F5)
  3. Paste this script, press Run

STRUCTURE:
  Two parallel SIW leaky wave waveguides (aggressor + victim).
  Each has: [feed] -> [taper] -> [SIW body with slots] -> [taper] -> [feed]
  Shared m1 ground plane covers both.
  Vary WAVEGUIDE_SEPARATION to sweep crosstalk vs distance.

LAYER STRUCTURE:
  m1   = single solid ground plane (covers both waveguides)
  m2   = top conductor for both waveguides (via walls, slots, tapers, feeds)
  via1 = sidewall via circles for both waveguides
"""

import pya
import math

# ===========================================================================
# PARAMETERS
# ===========================================================================

LAYER_M1   = (1, 0)
LAYER_M2   = (2, 0)
LAYER_VIA1 = (1, 1)

# Via geometry
VIA_DIAMETER    = 0.3    # mm
VIA_PITCH       = 0.6    # mm
VIA_SEGMENTS    = 64
VIA_STRIP_WIDTH = 1.0    # mm  m2 copper band along each via row

# SIW body
SIW_WIDTH  = 28.0        # mm  center-to-center between via rows
SIW_LENGTH = 60.0        # mm  SIW section length (excludes tapers and feeds)

# Leaky wave slots
SLOT_WIDTH  = 2.0        # mm  slot length along waveguide (x)
SLOT_HEIGHT = 14.0       # mm  slot height across waveguide (y), centered
SLOT_PERIOD = 6.0        # mm  center-to-center period
SLOT_OFFSET = 3.0        # mm  x offset of first slot from SIW body start

# Taper
TAPER_LENGTH = 10.0      # mm

# Feed
FEED_WIDTH  = 1.5        # mm  ~50 ohm microstrip
FEED_LENGTH = 10.0       # mm

# Ground plane margin outside outermost via rows
GND_MARGIN = 3.0         # mm

# Crosstalk sweep parameter
WAVEGUIDE_SEPARATION = 5.0  # mm  edge-to-edge gap between the two SIW waveguides
                             #     VARY THIS for crosstalk sweep

# ===========================================================================
# DERIVED
# ===========================================================================
VIA_RADIUS = VIA_DIAMETER / 2.0

X_FEED_END   = FEED_LENGTH
X_TAPER_END  = FEED_LENGTH + TAPER_LENGTH
X_SIW_END    = FEED_LENGTH + TAPER_LENGTH + SIW_LENGTH
X_RTAPER_END = FEED_LENGTH + TAPER_LENGTH + SIW_LENGTH + TAPER_LENGTH
X_TOTAL      = FEED_LENGTH + TAPER_LENGTH + SIW_LENGTH + TAPER_LENGTH + FEED_LENGTH

X_VIA_START = X_TAPER_END
X_VIA_END   = X_SIW_END

# Y layout — two waveguides stacked vertically, centered on y=0
# Each waveguide occupies SIW_WIDTH in Y centered on its own center
# Aggressor (bottom), Victim (top)
AGG_Y_CENTER = -(WAVEGUIDE_SEPARATION / 2.0 + SIW_WIDTH / 2.0)
VIC_Y_CENTER = +(WAVEGUIDE_SEPARATION / 2.0 + SIW_WIDTH / 2.0)

# m1 spans from bottom of aggressor to top of victim plus margins
M1_Y_BOT = AGG_Y_CENTER - SIW_WIDTH / 2.0 - GND_MARGIN
M1_Y_TOP = VIC_Y_CENTER + SIW_WIDTH / 2.0 + GND_MARGIN

# ===========================================================================
# HELPERS
# ===========================================================================
def to_dbu(mm, u):
    return int(round(mm / u))

def box(x1, y1, x2, y2, u):
    return pya.Box(to_dbu(x1,u), to_dbu(y1,u),
                   to_dbu(x2,u), to_dbu(y2,u))

def poly(pts_mm, u):
    return pya.Polygon([pya.Point(to_dbu(x,u), to_dbu(y,u)) for x,y in pts_mm])

def circle(cx, cy, r, n, u):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(pya.Point(to_dbu(cx + r*math.cos(a), u),
                             to_dbu(cy + r*math.sin(a), u)))
    return pya.Polygon(pts)

def draw_siw(cell, lm2, lvia, y_center, u, label):
    """Draw one complete SIW leaky wave waveguide centered on y_center."""
    n = 0

    y_top = y_center + SIW_WIDTH / 2.0
    y_bot = y_center - SIW_WIDTH / 2.0

    # --- Left feed ---
    cell.shapes(lm2).insert(box(0, y_center - FEED_WIDTH/2,
                                   X_FEED_END, y_center + FEED_WIDTH/2, u))
    n += 1

    # --- Left taper ---
    cell.shapes(lm2).insert(poly([
        (X_FEED_END,  y_center - FEED_WIDTH/2),
        (X_FEED_END,  y_center + FEED_WIDTH/2),
        (X_TAPER_END, y_top),
        (X_TAPER_END, y_bot),
    ], u))
    n += 1

    # --- Via wall strips (full SIW length) ---
    cell.shapes(lm2).insert(box(X_VIA_START, y_top - VIA_STRIP_WIDTH,
                                   X_VIA_END,   y_top + VIA_STRIP_WIDTH, u))
    cell.shapes(lm2).insert(box(X_VIA_START, y_bot - VIA_STRIP_WIDTH,
                                   X_VIA_END,   y_bot + VIA_STRIP_WIDTH, u))
    n += 2

    # --- Inner copper between slots ---
    inner_y_bot = y_bot + VIA_STRIP_WIDTH
    inner_y_top = y_top - VIA_STRIP_WIDTH
    slot_y_bot  = y_center - SLOT_HEIGHT / 2.0
    slot_y_top  = y_center + SLOT_HEIGHT / 2.0

    slot_starts = []
    x_slot = X_VIA_START + SLOT_OFFSET
    while x_slot + SLOT_WIDTH <= X_VIA_END:
        slot_starts.append(x_slot)
        x_slot += SLOT_PERIOD

    if slot_starts:
        # Left end cap
        if slot_starts[0] > X_VIA_START:
            cell.shapes(lm2).insert(box(X_VIA_START, inner_y_bot, slot_starts[0], inner_y_top, u))
            n += 1
        # Copper between slots
        for i in range(len(slot_starts) - 1):
            x_gap_start = slot_starts[i] + SLOT_WIDTH
            x_gap_end   = slot_starts[i+1]
            if x_gap_end > x_gap_start:
                cell.shapes(lm2).insert(box(x_gap_start, inner_y_bot, x_gap_end, inner_y_top, u))
                n += 1
        # Right end cap
        x_after = slot_starts[-1] + SLOT_WIDTH
        if x_after < X_VIA_END:
            cell.shapes(lm2).insert(box(x_after, inner_y_bot, X_VIA_END, inner_y_top, u))
            n += 1
        # Y-side copper beside each slot
        for xs in slot_starts:
            xe = xs + SLOT_WIDTH
            if slot_y_bot > inner_y_bot:
                cell.shapes(lm2).insert(box(xs, inner_y_bot, xe, slot_y_bot, u))
                n += 1
            if slot_y_top < inner_y_top:
                cell.shapes(lm2).insert(box(xs, slot_y_top, xe, inner_y_top, u))
                n += 1
    else:
        cell.shapes(lm2).insert(box(X_VIA_START, inner_y_bot, X_VIA_END, inner_y_top, u))
        n += 1

    # --- Right taper ---
    cell.shapes(lm2).insert(poly([
        (X_SIW_END,    y_bot),
        (X_SIW_END,    y_top),
        (X_RTAPER_END, y_center + FEED_WIDTH/2),
        (X_RTAPER_END, y_center - FEED_WIDTH/2),
    ], u))
    n += 1

    # --- Right feed ---
    cell.shapes(lm2).insert(box(X_RTAPER_END, y_center - FEED_WIDTH/2,
                                   X_TOTAL, y_center + FEED_WIDTH/2, u))
    n += 1

    # --- Via circles ---
    via_count = 0
    x = X_VIA_START
    while x <= X_VIA_END + 1e-6:
        cell.shapes(lvia).insert(circle(x, y_top, VIA_RADIUS, VIA_SEGMENTS, u))
        cell.shapes(lvia).insert(circle(x, y_bot, VIA_RADIUS, VIA_SEGMENTS, u))
        x += VIA_PITCH
        via_count += 2
    n += via_count

    print(f"[{label}] y_center={y_center:.2f}  slots={len(slot_starts)}  vias={via_count}  shapes={n}")
    return n

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
        cell = layout.create_cell("SIW_LEAKY_CROSSTALK")
        cv.cell_name = cell.name
        print(f"Created cell: {cell.name}")

    lm1  = layout.layer(LAYER_M1[0],   LAYER_M1[1])
    lm2  = layout.layer(LAYER_M2[0],   LAYER_M2[1])
    lvia = layout.layer(LAYER_VIA1[0], LAYER_VIA1[1])
    print(f"Layers — m1:{lm1}  m2:{lm2}  via1:{lvia}")

    n = 0

    # -----------------------------------------------------------------------
    # 1. M1 — single shared ground plane covering both waveguides
    # -----------------------------------------------------------------------
    cell.shapes(lm1).insert(box(0, M1_Y_BOT, X_TOTAL, M1_Y_TOP, u))
    n += 1
    print(f"[m1] Ground plane: {X_TOTAL:.2f} x {M1_Y_TOP - M1_Y_BOT:.2f} mm")
    print(f"     y={M1_Y_BOT:.2f} to {M1_Y_TOP:.2f}")

    # -----------------------------------------------------------------------
    # 2. Draw aggressor waveguide (bottom)
    # -----------------------------------------------------------------------
    print(f"\nAggressor (bottom) waveguide:")
    n += draw_siw(cell, lm2, lvia, AGG_Y_CENTER, u, "aggressor")

    # -----------------------------------------------------------------------
    # 3. Draw victim waveguide (top)
    # -----------------------------------------------------------------------
    print(f"\nVictim (top) waveguide:")
    n += draw_siw(cell, lm2, lvia, VIC_Y_CENTER, u, "victim")

    mw.current_view().zoom_fit()

    print("\n" + "=" * 60)
    print("  SUCCESS — SIW Leaky Wave Crosstalk Layout")
    print("=" * 60)
    print(f"  Total length       : {X_TOTAL:.1f} mm")
    print(f"  SIW width          : {SIW_WIDTH:.1f} mm")
    print(f"  Feed width         : {FEED_WIDTH:.1f} mm")
    print(f"  Taper length       : {TAPER_LENGTH:.1f} mm")
    print(f"  Slot size          : {SLOT_WIDTH:.1f} x {SLOT_HEIGHT:.1f} mm")
    print(f"  Slot period        : {SLOT_PERIOD:.1f} mm")
    print(f"  Waveguide sep.     : {WAVEGUIDE_SEPARATION:.1f} mm  <- vary for sweep")
    print(f"  Aggressor y_center : {AGG_Y_CENTER:.2f} mm")
    print(f"  Victim y_center    : {VIC_Y_CENTER:.2f} mm")
    print(f"  Total shapes       : {n}")
    print("=" * 60)
    print("  CROSSTALK SWEEP: change WAVEGUIDE_SEPARATION and rerun")
    print("=" * 60)

run()