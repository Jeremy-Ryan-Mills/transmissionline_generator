# -*- coding: utf-8 -*-
# Thicken imported GDS sheets and add dielectric stackup
# Run via Tools -> Run Script in HFSS Terminal Network design

# Stackup (mm, bottom to top)
M1_Z     = 0.0;    M1_THK   = 0.035
PRE1_Z   = 0.035;  PRE1_THK = 0.2104
INT1_Z   = 0.2454; INT1_THK = 0.0152
CORE_Z   = 0.2606; CORE_THK = 1.065
INT2_Z   = 1.3256; INT2_THK = 0.0152
PRE2_Z   = 1.3408; PRE2_THK = 0.2104
M2_Z     = 1.5512; M2_THK   = 0.035
TOP_Z    = 1.5862

# Layout extents from KLayout script (mm)
TOTAL_LENGTH = 76.0   # 5+3+60+3+5
TOTAL_HEIGHT = 73.0   # 2*(28+6) + 5
AIR_PADDING  = 5.0

oDesktop.AddMessage("", "", 0, "Starting thicken and stackup")

oProject = oDesktop.GetActiveProject()
oDesign  = oProject.GetActiveDesign()
oEditor  = oDesign.SetActiveEditor("3D Modeler")
oBoundarySetup = oDesign.GetModule("BoundarySetup")
oDefinitionManager = oProject.GetDefinitionManager()

# Add materials
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
        oDesktop.AddMessage("", "", 0, "Added " + mat_name)
    except:
        oDesktop.AddMessage("", "", 0, mat_name + " already exists")

# Get all imported sheet objects
sheets = list(oEditor.GetObjectsInGroup("Sheets"))
oDesktop.AddMessage("", "", 0, "Imported sheets: " + str(len(sheets)))

# Move all sheets to M1 elevation and thicken
if sheets:
    oEditor.Move(
        ["NAME:Selections", "Selections:=", ",".join(sheets)],
        ["NAME:TranslateParameters",
         "CoordinateSystemID:=", -1,
         "TranslateVectorX:=", "0mm",
         "TranslateVectorY:=", "0mm",
         "TranslateVectorZ:=", str(M1_Z) + "mm",
        ]
    )
    oEditor.ThickenSheet(
        ["NAME:Selections", "Selections:=", ",".join(sheets)],
        ["NAME:ThickenSheetParameters",
         "Thickness:=", str(M1_THK) + "mm",
         "BothSides:=", False,
        ]
    )
    oDesktop.AddMessage("", "", 0, "Sheets thickened by " + str(M1_THK) + "mm at Z=" + str(M1_Z))

# Helper to create a box
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
        oDesktop.AddMessage("", "", 0, "Created box: " + name)
    except Exception as e:
        oDesktop.AddMessage("", "", 0, "Box error " + name + ": " + str(e))

W = TOTAL_LENGTH
H = TOTAL_HEIGHT

# Dielectric and conductor boxes
make_box("prepreg1", 0, 0, PRE1_Z, W, H, PRE1_THK, "PP017",   True)
make_box("Int1_GND", 0, 0, INT1_Z, W, H, INT1_THK, "copper",  False)
make_box("core",     0, 0, CORE_Z, W, H, CORE_THK, "Core039", True)
make_box("Int2",     0, 0, INT2_Z, W, H, INT2_THK, "copper",  False)
make_box("prepreg2", 0, 0, PRE2_Z, W, H, PRE2_THK, "PP017",   True)

# Airbox
P = AIR_PADDING
make_box("airbox",
         -P, -P, M1_Z - P,
         W + 2*P, H + 2*P, TOP_Z + 2*P,
         "vacuum", True)

# Radiation boundary on airbox
try:
    oBoundarySetup.AssignRadiation(
        ["NAME:Rad1",
         "Objects:=", ["airbox"],
         "IsFssReference:=", False,
         "IsForPML:=", False,
        ]
    )
    oDesktop.AddMessage("", "", 0, "Radiation boundary on airbox")
except Exception as e:
    oDesktop.AddMessage("", "", 0, "Radiation error: " + str(e))

oProject.Save()
oDesktop.AddMessage("", "", 0, "DONE - add wave ports at feed line ends then analyze")
