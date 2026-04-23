"""
SIW Leaky Wave Waveguide Layout Generator for KLayout
With port labels for EMX simulation
"""

import pya
import math

# ===========================================================================
# PARAMETERS
# ===========================================================================

LAYER_M1    = (1, 0)
LAYER_M2    = (2, 0)
LAYER_VIA1  = (1, 1)
LAYER_LABEL = (10, 0)  # text labels for EMX ports (new layer)

VIA_DIAMETER    = 0.3
VIA_PITCH       = 0.6
VIA_SEGMENTS    = 64
VIA_STRIP_WIDTH = 5.0

SIW_WIDTH  = 28.0
SIW_LENGTH = 60.0
GND_MARGIN = 3.0

NUM_CHANNELS = 2
CHANNEL_GAP  = 5.0

FEED_WIDTH  = 5.0
FEED_LENGTH = 5.0

# ===========================================================================
# DERIVED
# ===========================================================================
VIA_RADIUS     = VIA_DIAMETER / 2.0
TOTAL_LENGTH   = FEED_LENGTH + GND_MARGIN + SIW_LENGTH + GND_MARGIN + FEED_LENGTH  # 76.0
X_VIA_START    = FEED_LENGTH + GND_MARGIN
X_VIA_END      = X_VIA_START + SIW_LENGTH
CHANNEL_HEIGHT = SIW_WIDTH + 2 * GND_MARGIN   # 34.0
TOTAL_HEIGHT   = NUM_CHANNELS * CHANNEL_HEIGHT + (NUM_CHANNELS - 1) * CHANNEL_GAP  # 73.0

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

def label(text, x, y, u, shapes, layer):
    """Place a text label for EMX port definition."""
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
    print(f"DBU = {u} mm")
    print(f"TOTAL_LENGTH = {TOTAL_LENGTH} mm")
    print(f"TOTAL_HEIGHT = {TOTAL_HEIGHT} mm")
    print(f"CHANNEL_HEIGHT = {CHANNEL_HEIGHT} mm")

    if layout.cells() > 0:
        cell = layout.cell(layout.top_cells()[0].cell_index())
        cell.clear()
        print(f"Cleared cell: {cell.name}")
    else:
        cell = layout.create_cell("SIW_LEAKY_WAVE")
        cv.cell_name = cell.name

    lm1   = layout.layer(LAYER_M1[0],    LAYER_M1[1])
    lm2   = layout.layer(LAYER_M2[0],    LAYER_M2[1])
    lvia  = layout.layer(LAYER_VIA1[0],  LAYER_VIA1[1])
    llbl  = layout.layer(LAYER_LABEL[0], LAYER_LABEL[1])

    # Compute channel Y positions
    channels = []
    for ch in range(NUM_CHANNELS):
        ch_y_bot    = ch * (CHANNEL_HEIGHT + CHANNEL_GAP)
        ch_y_center = ch_y_bot + CHANNEL_HEIGHT / 2.0
        y_bot_row   = ch_y_center - SIW_WIDTH / 2.0
        y_top_row   = ch_y_center + SIW_WIDTH / 2.0
        channels.append({
            "center":  ch_y_center,
            "bot_row": y_bot_row,
            "top_row": y_top_row,
        })
        print(f"Channel {ch}: bot_row={y_bot_row:.2f} center={ch_y_center:.2f} top_row={y_top_row:.2f}")

    n = 0

    # M1 ground plane
    cell.shapes(lm1).insert(box(0, 0, TOTAL_LENGTH, TOTAL_HEIGHT, u))
    n += 1

    # M2 Strip 1 - bottom outer via wall
    y = channels[0]["bot_row"]
    cell.shapes(lm2).insert(box(0, y - VIA_STRIP_WIDTH/2, TOTAL_LENGTH, y + VIA_STRIP_WIDTH/2, u))
    n += 1

    # M2 Strip 2 - ch0 signal TL
    y = channels[0]["center"]
    cell.shapes(lm2).insert(box(0, y - FEED_WIDTH/2, TOTAL_LENGTH, y + FEED_WIDTH/2, u))
    n += 1

    # M2 Strip 3 - shared middle via wall
    y1 = channels[0]["top_row"] - VIA_STRIP_WIDTH/2
    y2 = channels[1]["bot_row"] + VIA_STRIP_WIDTH/2
    cell.shapes(lm2).insert(box(0, y1, TOTAL_LENGTH, y2, u))
    n += 1

    # M2 Strip 4 - ch1 signal TL
    y = channels[1]["center"]
    cell.shapes(lm2).insert(box(0, y - FEED_WIDTH/2, TOTAL_LENGTH, y + FEED_WIDTH/2, u))
    n += 1

    # M2 Strip 5 - top outer via wall
    y = channels[1]["top_row"]
    cell.shapes(lm2).insert(box(0, y - VIA_STRIP_WIDTH/2, TOTAL_LENGTH, y + VIA_STRIP_WIDTH/2, u))
    n += 1

    # Via rows
    for ch, ch_data in enumerate(channels):
        via_count = 0
        x = X_VIA_START
        while x <= X_VIA_END + 1e-6:
            cell.shapes(lvia).insert(circle(x, ch_data["top_row"], VIA_RADIUS, VIA_SEGMENTS, u))
            cell.shapes(lvia).insert(circle(x, ch_data["bot_row"], VIA_RADIUS, VIA_SEGMENTS, u))
            x += VIA_PITCH
            via_count += 2
        n += via_count

    # -----------------------------------------------------------------------
    # PORT LABELS for EMX (placed on m2 layer at feed line ends)
    # Left end = x=0, Right end = x=TOTAL_LENGTH
    # Port naming: p1/p2 = aggressor (ch0), p3/p4 = victim (ch1)
    # -----------------------------------------------------------------------
    # Aggressor ch0 ports
    label("p1", 0,            channels[0]["center"], u, cell.shapes, llbl)
    label("p2", TOTAL_LENGTH, channels[0]["center"], u, cell.shapes, llbl)
    # Victim ch1 ports
    label("p3", 0,            channels[1]["center"], u, cell.shapes, llbl)
    label("p4", TOTAL_LENGTH, channels[1]["center"], u, cell.shapes, llbl)
    n += 4
    print(f"Port labels placed: p1,p2 (aggressor ch0), p3,p4 (victim ch1)")

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
    print("  Port labels on layer 10/0:")
    print("  p1 = aggressor left,  p2 = aggressor right")
    print("  p3 = victim left,     p4 = victim right")
    print("=" * 55)

run()
