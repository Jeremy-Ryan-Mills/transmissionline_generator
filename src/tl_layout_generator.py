"""
SIW Leaky Wave Waveguide Layout Generator for KLayout
======================================================
HOW TO RUN:
  1. Open KLayout -> File -> New Layout (accept defaults)
  2. Macros -> Macro Editor (F5)
  3. Paste this script, press Run
  4. Check console for confirmation

LAYER STRUCTURE:
  m1  = one solid rectangle (full ground plane, bottom copper)
  m2  = 5 separate strips only, NO solid rectangle:
          strip 1 (bottom outer via wall)  — ch0 bot_row
          strip 2 (ch0 signal/TL)          — ch0 center
          strip 3 (shared middle via wall)  — ch0 top_row TO ch1 bot_row (one wide piece)
          strip 4 (ch1 signal/TL)          — ch1 center
          strip 5 (top outer via wall)     — ch1 top_row
  via1 = circles at ch0 top_row, ch0 bot_row, ch1 top_row, ch1 bot_row

Y COORDINATE EXAMPLE (default params):
  ch0: bot_row=3  center=17  top_row=31
  ch1: bot_row=42 center=56  top_row=70
  strip1 @ y~3, strip2 @ y~17, strip3 y=31..42, strip4 @ y~56, strip5 @ y~70
"""

import pya
import math

# ===========================================================================
# PARAMETERS
# ===========================================================================

LAYER_M1   = (1, 0)
LAYER_M2   = (2, 0)
LAYER_VIA1 = (1, 1)

VIA_DIAMETER    = 0.3    # mm
VIA_PITCH       = 0.6    # mm
VIA_SEGMENTS    = 64
VIA_STRIP_WIDTH = 5.0    # mm  height of the thin outer via wall strips

SIW_WIDTH  = 28.0        # mm  center-to-center between via rows per channel
SIW_LENGTH = 60.0        # mm

GND_MARGIN = 3.0         # mm  margin outside the outermost via rows

NUM_CHANNELS = 2
CHANNEL_GAP  = 5.0       # mm  clear gap between channels on m2

FEED_WIDTH  = 5.0        # mm  TL strip width
FEED_LENGTH = 5.0        # mm  feed stub past via region each side

# ===========================================================================
# DERIVED
# ===========================================================================
VIA_RADIUS     = VIA_DIAMETER / 2.0
TOTAL_LENGTH   = FEED_LENGTH + GND_MARGIN + SIW_LENGTH + GND_MARGIN + FEED_LENGTH
X_VIA_START    = FEED_LENGTH + GND_MARGIN
X_VIA_END      = X_VIA_START + SIW_LENGTH
CHANNEL_HEIGHT = SIW_WIDTH + 2 * GND_MARGIN
TOTAL_HEIGHT   = NUM_CHANNELS * CHANNEL_HEIGHT + (NUM_CHANNELS - 1) * CHANNEL_GAP

# ===========================================================================
# HELPERS
# ===========================================================================
def to_dbu(mm, u):
    return int(round(mm / u))

def box(x1, y1, x2, y2, u):
    return pya.Box(to_dbu(x1,u), to_dbu(y1,u),
                   to_dbu(x2,u), to_dbu(y2,u))

def circle(cx, cy, r, n, u):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(pya.Point(to_dbu(cx + r*math.cos(a), u),
                             to_dbu(cy + r*math.sin(a), u)))
    return pya.Polygon(pts)

def thin_strip(y_center, length, width, u, shapes, layer):
    """Draw a thin horizontal strip centered on y_center."""
    shapes(layer).insert(box(0, y_center - width/2, length, y_center + width/2, u))

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
        cell = layout.create_cell("SIW_LEAKY_WAVE")
        cv.cell_name = cell.name
        print(f"Created cell: {cell.name}")

    lm1  = layout.layer(LAYER_M1[0],   LAYER_M1[1])
    lm2  = layout.layer(LAYER_M2[0],   LAYER_M2[1])
    lvia = layout.layer(LAYER_VIA1[0], LAYER_VIA1[1])
    print(f"Layers — m1:{lm1}  m2:{lm2}  via1:{lvia}")

    # -----------------------------------------------------------------------
    # Compute Y positions for each channel
    # Channel 0 sits at the bottom (low Y), channel 1 above it (high Y)
    # -----------------------------------------------------------------------
    channels = []
    for ch in range(NUM_CHANNELS):
        ch_y_bot    = ch * (CHANNEL_HEIGHT + CHANNEL_GAP)
        ch_y_center = ch_y_bot + CHANNEL_HEIGHT / 2.0
        # bot_row = lower via row (lower Y value)
        # top_row = upper via row (higher Y value)
        y_bot_row = ch_y_center - SIW_WIDTH / 2.0
        y_top_row = ch_y_center + SIW_WIDTH / 2.0
        channels.append({
            "center":  ch_y_center,
            "bot_row": y_bot_row,   # lower Y
            "top_row": y_top_row,   # higher Y
        })
        print(f"Channel {ch}: bot_row={y_bot_row:.2f}  center={ch_y_center:.2f}  top_row={y_top_row:.2f}")

    print(f"\nTotal layout: {TOTAL_LENGTH:.2f} x {TOTAL_HEIGHT:.2f} mm")
    print(f"Via region: x={X_VIA_START:.2f} to {X_VIA_END:.2f}\n")

    n = 0

    # -----------------------------------------------------------------------
    # M1 — one solid ground plane rectangle (ONLY m1 gets this)
    # -----------------------------------------------------------------------
    cell.shapes(lm1).insert(box(0, 0, TOTAL_LENGTH, TOTAL_HEIGHT, u))
    n += 1
    print(f"[m1] Solid ground plane: 0,0 to {TOTAL_LENGTH:.2f},{TOTAL_HEIGHT:.2f}")

    # -----------------------------------------------------------------------
    # M2 STRIP 1 — bottom outer via wall
    # Centered on ch0's bottom via row (lowest Y via row in the whole layout)
    # -----------------------------------------------------------------------
    y = channels[0]["bot_row"]
    y1 = y - VIA_STRIP_WIDTH / 2
    y2 = y + VIA_STRIP_WIDTH / 2
    cell.shapes(lm2).insert(box(0, y1, TOTAL_LENGTH, y2, u))
    n += 1
    print(f"[m2] Strip 1 — bottom outer via wall: y={y1:.3f} to {y2:.3f}")

    # -----------------------------------------------------------------------
    # M2 STRIP 2 — ch0 signal / TL strip
    # Centered on ch0's center Y
    # -----------------------------------------------------------------------
    y = channels[0]["center"]
    y1 = y - FEED_WIDTH / 2
    y2 = y + FEED_WIDTH / 2
    cell.shapes(lm2).insert(box(0, y1, TOTAL_LENGTH, y2, u))
    n += 1
    print(f"[m2] Strip 2 — ch0 TL signal: y={y1:.3f} to {y2:.3f}")

    # -----------------------------------------------------------------------
    # M2 STRIP 3 — shared middle via wall (ONE wide piece)
    # Runs from ch0's TOP via row down to ch1's BOTTOM via row
    # This spans the full CHANNEL_GAP between them
    # -----------------------------------------------------------------------
    y1 = channels[0]["top_row"] - VIA_STRIP_WIDTH / 2   # just below ch0 top row
    y2 = channels[1]["bot_row"] + VIA_STRIP_WIDTH / 2   # just above ch1 bot row
    cell.shapes(lm2).insert(box(0, y1, TOTAL_LENGTH, y2, u))
    n += 1
    print(f"[m2] Strip 3 — shared middle via wall: y={y1:.3f} to {y2:.3f}  (height={(y2-y1):.3f} mm)")

    # -----------------------------------------------------------------------
    # M2 STRIP 4 — ch1 signal / TL strip
    # Centered on ch1's center Y
    # -----------------------------------------------------------------------
    y = channels[1]["center"]
    y1 = y - FEED_WIDTH / 2
    y2 = y + FEED_WIDTH / 2
    cell.shapes(lm2).insert(box(0, y1, TOTAL_LENGTH, y2, u))
    n += 1
    print(f"[m2] Strip 4 — ch1 TL signal: y={y1:.3f} to {y2:.3f}")

    # -----------------------------------------------------------------------
    # M2 STRIP 5 — top outer via wall
    # Centered on ch1's top via row (highest Y via row in the layout)
    # -----------------------------------------------------------------------
    y = channels[1]["top_row"]
    y1 = y - VIA_STRIP_WIDTH / 2
    y2 = y + VIA_STRIP_WIDTH / 2
    cell.shapes(lm2).insert(box(0, y1, TOTAL_LENGTH, y2, u))
    n += 1
    print(f"[m2] Strip 5 — top outer via wall: y={y1:.3f} to {y2:.3f}")

    # -----------------------------------------------------------------------
    # VIA1 — circles at all 4 via rows (2 per channel)
    # -----------------------------------------------------------------------
    for ch, ch_data in enumerate(channels):
        via_count = 0
        x = X_VIA_START
        while x <= X_VIA_END + 1e-6:
            cell.shapes(lvia).insert(circle(x, ch_data["top_row"], VIA_RADIUS, VIA_SEGMENTS, u))
            cell.shapes(lvia).insert(circle(x, ch_data["bot_row"], VIA_RADIUS, VIA_SEGMENTS, u))
            x += VIA_PITCH
            via_count += 2
        n += via_count
        print(f"[via1] Channel {ch}: {via_count} circles ({via_count//2} per row)")

    mw.current_view().zoom_fit()

    print("\n" + "=" * 55)
    print("  SUCCESS")
    print(f"  Layout size  : {TOTAL_LENGTH:.1f} x {TOTAL_HEIGHT:.1f} mm")
    print(f"  Channels     : {NUM_CHANNELS}")
    print(f"  SIW width    : {SIW_WIDTH} mm")
    print(f"  Channel gap  : {CHANNEL_GAP} mm")
    print(f"  Via pitch/d  : {VIA_PITCH}/{VIA_DIAMETER} mm")
    print(f"  Total shapes : {n}")
    print("=" * 55)
    print("  m1  = 1 solid rectangle")
    print("  m2  = 5 strips (bot wall | TL0 | mid wall | TL1 | top wall)")
    print("  via1= 4 rows of circles")
    print("=" * 55)

run()