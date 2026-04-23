# -*- coding: utf-8 -*-
# Complete SIW Transmission Line Builder for HFSS Terminal Network
# Builds geometry, stackup, vias, port rectangles, and solution setup
# NOTE: Port excitations must be assigned manually in GUI (to set integration line)
# Run via Tools -> Run Script in a blank HFSSDesign (Terminal Network)

# ===========================================================================
# STACKUP (mm, bottom to top)
# ===========================================================================
M1_Z     = 0.0;    M1_THK   = 0.035
PRE1_Z   = 0.035;  PRE1_THK = 0.2104
INT1_Z   = 0.2454; INT1_THK = 0.0152
CORE_Z   = 0.2606; CORE_THK = 1.065
INT2_Z   = 1.3256; INT2_THK = 0.0152
PRE2_Z   = 1.3408; PRE2_THK = 0.2104
M2_Z     = 1.5512; M2_THK   = 0.035
TOP_Z    = 1.5862

# ===========================================================================
# LAYOUT DIMENSIONS (mm)
# ===========================================================================
TOTAL_LENGTH    = 76.0
TOTAL_HEIGHT    = 73.0
AIR_PADDING     = 5.0

SIW_WIDTH       = 28.0
GND_MARGIN      = 3.0
CHANNEL_HEIGHT  = SIW_WIDTH + 2 * GND_MARGIN   # 34.0
CHANNEL_GAP     = 5.0
FEED_WIDTH      = 5.0
VIA_STRIP_WIDTH = 5.0
FEED_LENGTH     = 5.0
VIA_DIAMETER    = 0.3
VIA_PITCH       = 0.6
VIA_RADIUS      = VIA_DIAMETER / 2.0

X_VIA_START = FEED_LENGTH + GND_MARGIN         # 8.0
X_VIA_END   = X_VIA_START + 60.0              # 68.0

CH0_CENTER  = CHANNEL_HEIGHT / 2.0             # 17.0
CH1_CENTER  = CHANNEL_HEIGHT + CHANNEL_GAP + CHANNEL_HEIGHT / 2.0  # 56.0
CH0_BOT_ROW = CH0_CENTER - SIW_WIDTH / 2.0    # 3.0
CH0_TOP_ROW = CH0_CENTER + SIW_WIDTH / 2.0    # 31.0
CH1_BOT_ROW = CH1_CENTER - SIW_WIDTH / 2.0    # 42.0
CH1_TOP_ROW = CH1_CENTER + SIW_WIDTH / 2.0    # 70.0

PORT_Z_BOT  = 0.0
PORT_Z_TOP  = TOP_Z
X_LEFT      = 0.0
X_RIGHT     = TOTAL_LENGTH

# ===========================================================================
# INITIALIZE
# ===========================================================================
oDesktop.AddMessage("", "", 0, "=== SIW Build Script Starting ===")

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")
oBoundarySetup     = oDesign.GetModule("BoundarySetup")
oAnalysisSetup     = oDesign.GetModule("AnalysisSetup")
oDefinitionManager = oProject.GetDefinitionManager()

# ===========================================================================
# 1. CLEAN UP
# ===========================================================================
for pattern in ["red_*", "m1", "m2_strip*", "prepreg*", "Int*", "core",
                "airbox", "port_rect_*", "via_*"]:
    try:
        objs = list(oEditor.GetMatchedObjectName(pattern))
        if objs:
            oEditor.Delete(["NAME:Selections", "Selections:=", ",".join(objs)])
    except:
        pass

for bnd in ["Port1","Port2","Port3","Port4","Rad1"]:
    try: oBoundarySetup.DeleteBoundaries([bnd])
    except: pass

for setup in ["Setup1"]:
    try: oAnalysisSetup.DeleteSetups([setup])
    except: pass

oDesktop.AddMessage("", "", 0, "Cleanup done")

# ===========================================================================
# 2. MATERIALS
# ===========================================================================
for mat_name, er, tand in [("PP017", "4.4", "0.02"), ("Core039", "4.6", "0.02")]:
    try:
        oDefinitionManager.AddMaterial(
            ["NAME:" + mat_name,
             "CoordinateSystemType:=", "Cartesian",
             ["NAME:AttachedData"],
             "permittivity:=", er,
             "dielectric_loss_tangent:=", tand,
            ]
        )
    except:
        pass

# ===========================================================================
# 3. HELPERS
# ===========================================================================
def make_box(name, x, y, z, xs, ys, zs, mat, solve_inside):
    try:
        oEditor.CreateBox(
            ["NAME:BoxParameters",
             "XPosition:=", str(x)  + "mm",
             "YPosition:=", str(y)  + "mm",
             "ZPosition:=", str(z)  + "mm",
             "XSize:=",     str(xs) + "mm",
             "YSize:=",     str(ys) + "mm",
             "ZSize:=",     str(zs) + "mm",
            ],
            ["NAME:Attributes",
             "Name:=",          name,
             "MaterialValue:=", "\"" + mat + "\"",
             "SolveInside:=",   solve_inside,
            ]
        )
        oDesktop.AddMessage("", "", 0, "Box: " + name)
    except Exception as e:
        oDesktop.AddMessage("", "", 0, "Box error " + name + ": " + str(e))

def make_cylinder(name, x, y, z, radius, height, mat):
    try:
        oEditor.CreateCylinder(
            ["NAME:CylinderParameters",
             "XCenter:=",  str(x)      + "mm",
             "YCenter:=",  str(y)      + "mm",
             "ZCenter:=",  str(z)      + "mm",
             "Radius:=",   str(radius) + "mm",
             "Height:=",   str(height) + "mm",
             "WhichAxis:=", "Z",
             "NumSides:=",  0,
            ],
            ["NAME:Attributes",
             "Name:=",          name,
             "MaterialValue:=", "\"" + mat + "\"",
             "SolveInside:=",   False,
            ]
        )
    except Exception as e:
        oDesktop.AddMessage("", "", 0, "Cyl error " + name + ": " + str(e))

W = TOTAL_LENGTH
H = TOTAL_HEIGHT

# ===========================================================================
# 4. M1 - bottom ground plane
# ===========================================================================
make_box("m1", 0, 0, M1_Z, W, H, M1_THK, "copper", False)

# ===========================================================================
# 5. DIELECTRIC STACKUP
# ===========================================================================
make_box("prepreg1", 0, 0, PRE1_Z, W, H, PRE1_THK, "PP017",   True)
make_box("Int1_GND", 0, 0, INT1_Z, W, H, INT1_THK, "copper",  False)
make_box("core",     0, 0, CORE_Z, W, H, CORE_THK, "Core039", True)
make_box("Int2",     0, 0, INT2_Z, W, H, INT2_THK, "copper",  False)
make_box("prepreg2", 0, 0, PRE2_Z, W, H, PRE2_THK, "PP017",   True)

# ===========================================================================
# 6. M2 - top conductor strips
# ===========================================================================
make_box("m2_strip1", 0, CH0_BOT_ROW - VIA_STRIP_WIDTH/2, M2_Z,
         W, VIA_STRIP_WIDTH, M2_THK, "copper", False)
make_box("m2_strip2", 0, CH0_CENTER - FEED_WIDTH/2, M2_Z,
         W, FEED_WIDTH, M2_THK, "copper", False)
mid_y1 = CH0_TOP_ROW - VIA_STRIP_WIDTH/2
mid_y2 = CH1_BOT_ROW + VIA_STRIP_WIDTH/2
make_box("m2_strip3", 0, mid_y1, M2_Z, W, mid_y2 - mid_y1, M2_THK, "copper", False)
make_box("m2_strip4", 0, CH1_CENTER - FEED_WIDTH/2, M2_Z,
         W, FEED_WIDTH, M2_THK, "copper", False)
make_box("m2_strip5", 0, CH1_TOP_ROW - VIA_STRIP_WIDTH/2, M2_Z,
         W, VIA_STRIP_WIDTH, M2_THK, "copper", False)

oDesktop.AddMessage("", "", 0, "M2 strips at Z=" + str(M2_Z))

# ===========================================================================
# 7. VIAS
# ===========================================================================
via_count = 0
via_height = TOP_Z - M1_Z
for row_y in [CH0_BOT_ROW, CH0_TOP_ROW, CH1_BOT_ROW, CH1_TOP_ROW]:
    x = X_VIA_START
    while x <= X_VIA_END + 1e-6:
        make_cylinder("via_" + str(via_count), x, row_y, M1_Z,
                      VIA_RADIUS, via_height, "copper")
        via_count += 1
        x += VIA_PITCH

oDesktop.AddMessage("", "", 0, "Vias: " + str(via_count))

# ===========================================================================
# 8. AIRBOX
# ===========================================================================
P = AIR_PADDING
make_box("airbox", -P, -P, M1_Z - P,
         W + 2*P, H + 2*P, TOP_Z - M1_Z + 2*P, "vacuum", True)

# ===========================================================================
# 9. RADIATION BOUNDARY
# ===========================================================================
try:
    oBoundarySetup.AssignRadiation(
        ["NAME:Rad1",
         "Objects:=",       ["airbox"],
         "IsFssReference:=", False,
         "IsForPML:=",      False,
        ]
    )
    oDesktop.AddMessage("", "", 0, "Radiation boundary assigned")
except Exception as e:
    oDesktop.AddMessage("", "", 0, "Radiation error: " + str(e))

# ===========================================================================
# 10. PORT RECTANGLES (no excitation assigned - do this manually in GUI)
# Each rectangle spans full board height Z=0 to Z=1.5862
# After running script:
#   Draw -> Port -> Create Terminal Ports
#   Click each rectangle, draw integration line from m2 (top) to m1 (bottom)
# Port1 = aggressor left  (x=0,  y=17)
# Port2 = aggressor right (x=76, y=17)
# Port3 = victim left     (x=0,  y=56)
# Port4 = victim right    (x=76, y=56)
# ===========================================================================
ports = [
    ("port_rect_Port1", X_LEFT,  CH0_CENTER),
    ("port_rect_Port2", X_RIGHT, CH0_CENTER),
    ("port_rect_Port3", X_LEFT,  CH1_CENTER),
    ("port_rect_Port4", X_RIGHT, CH1_CENTER),
]

for rect_name, x, y_center in ports:
    try:
        oEditor.CreateRectangle(
            ["NAME:RectangleParameters",
             "IsCovered:=", True,
             "XStart:=",    str(x) + "mm",
             "YStart:=",    str(y_center - FEED_WIDTH/2) + "mm",
             "ZStart:=",    str(PORT_Z_BOT) + "mm",
             "Width:=",     str(FEED_WIDTH) + "mm",
             "Height:=",    str(PORT_Z_TOP - PORT_Z_BOT) + "mm",
             "WhichAxis:=", "X",
            ],
            ["NAME:Attributes",
             "Name:=",          rect_name,
             "MaterialValue:=", "\"vacuum\"",
             "SolveInside:=",   True,
            ]
        )
        oDesktop.AddMessage("", "", 0, "Port rect: " + rect_name)
    except Exception as e:
        oDesktop.AddMessage("", "", 0, "Rect error " + rect_name + ": " + str(e))

# ===========================================================================
# 11. SOLUTION SETUP
# ===========================================================================
try:
    oAnalysisSetup.InsertSetup("HfssDriven",
        ["NAME:Setup1",
         "Frequency:=",              "5GHz",
         "MaxDeltaS:=",              0.02,
         "MaximumPasses:=",          10,
         "MinimumPasses:=",          2,
         "MinimumConvergedPasses:=", 1,
         "PercentRefinement:=",      30,
         "IsEnabled:=",              True,
         ["NAME:MeshLink", "ImportMesh:=", False],
         "BasisOrder:=",             1,
         "DoLambdaRefine:=",         True,
         "DoMaterialLambda:=",       True,
         "SaveRadFieldsOnly:=",      False,
         "SaveAnyFields:=",          True,
        ]
    )
    oAnalysisSetup.InsertFrequencySweep("Setup1",
        ["NAME:Sweep1",
         "IsEnabled:=",       True,
         "RangeType:=",       "LinearCount",
         "RangeStart:=",      "1GHz",
         "RangeEnd:=",        "10GHz",
         "RangeCount:=",      91,
         "Type:=",            "Interpolating",
         "SaveFields:=",      False,
         "SaveRadFields:=",   False,
         "InterpTolerance:=", 0.5,
         "InterpMaxSolns:=",  250,
         "ExtrapToDC:=",      False,
        ]
    )
    oDesktop.AddMessage("", "", 0, "Solution setup: 5GHz adaptive, 1-10GHz sweep")
except Exception as e:
    oDesktop.AddMessage("", "", 0, "Setup error: " + str(e))

# ===========================================================================
# 12. SAVE
# ===========================================================================
oProject.Save()
oDesktop.AddMessage("", "", 0, "=== BUILD COMPLETE ===")
oDesktop.AddMessage("", "", 0, "Next: assign port excitations manually in GUI")
oDesktop.AddMessage("", "", 0, "  Draw -> Port -> Create Terminal Ports")
oDesktop.AddMessage("", "", 0, "  Click each port_rect, draw integration line top->bottom")
oDesktop.AddMessage("", "", 0, "Then Validate and F10 to analyze")
oDesktop.AddMessage("", "", 0, "Crosstalk = dB(St(Port3,Port1))")
