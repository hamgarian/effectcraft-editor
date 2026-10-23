"""Photoreal "phone lying on a desk" set: textured desk, a phone whose screen plays a UI image sequence (render your UI
comp from EffectCraft to ui_0000.png, ui_0001.png, ...), an optional disc prop, a cable, off-screen shadow casters,
HDRI bounce, Cycles. Edit CAMK for your shot.

  blender -b -P scripts/blender/phone_on_desk.py -- --desk desk.png --ui-dir ui --out renders
          [--disc disc.png] [--frames 0-31] [--res 1440x1080] [--samples 96] [--exposure 0.7] [--shadow-x -0.497]

Writes OUT/frame_####.png; place them in EffectCraft one layer per frame (jsx/helpers.jsx imageSequence()).
"""
import glob
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import kit  # noqa: E402

A = kit.args(sys.argv, {"desk": "", "ui_dir": "", "out": "", "disc": "", "frames": "0-31", "res": "1440x1080",
                        "samples": 96, "exposure": 0.7, "shadow_x": -0.497})
f0, f1 = map(int, A["frames"].split("-"))
rw, rh = map(int, A["res"].split("x"))
ui_frames = sorted(glob.glob(os.path.join(A["ui_dir"], "ui_*.png")))
assert A["desk"] and ui_frames and A["out"], "need --desk, --ui-dir (with ui_*.png) and --out"
kit.scene((rw, rh), 20, (f0, f1), A["out"], A["samples"], A["exposure"])

# desk: texture + bump from its own grain + roughness variation (metres: the phone is 7.4 x 15.5 cm)
dm, db = kit.principled("desk", rough=0.55); kit.texture(dm, db, A["desk"], bump=0.25); kit.grime(dm, db, "Roughness", 0.42, 0.7, 14.0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.1, 0)); desk = bpy.context.object; desk.scale = (1.0, 0.56, 1); desk.data.materials.append(dm)

# phone: bevelled anisotropic aluminium, side buttons, smudged glass, camera pill, the UI as a screen that takes light
PW, PH, PT, yaw = 0.074, 0.155, 0.008, math.radians(-14)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, PT / 2), rotation=(0, 0, yaw)); body = bpy.context.object
body.scale = (PW, PH, PT); bpy.ops.object.transform_apply(scale=True)
bv = body.modifiers.new("round", "BEVEL"); bv.width = 0.009; bv.segments = 10; bv.limit_method = "NONE"
am, ab = kit.principled("alu", (0.78, 0.78, 0.8), 0.28, 1.0)
try:
    ab.inputs["Anisotropic"].default_value = 0.6
except KeyError:
    pass
kit.grime(am, ab, "Roughness", 0.22, 0.38, 220.0); body.data.materials.append(am)


def child(size, local_loc, mat, bevel=0.0):
    """part placed in the phone's own space (parented with an identity inverse, so it rotates with the phone)"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=local_loc); o = bpy.context.object
    o.scale = size; bpy.ops.object.transform_apply(scale=True); o.data.materials.append(mat)
    if bevel:
        b = o.modifiers.new("round", "BEVEL"); b.width = bevel; b.segments = 6
    o.parent = body
    return o


for by, bl in [(0.035, 0.022), (0.006, 0.012), (-0.012, 0.012)]:
    child((0.0016, bl, 0.0024), (-PW / 2 - 0.0006, by, PT * 0.05), am)
glass, gb = kit.principled("glass", (0.004, 0.004, 0.005), 0.03); gb.inputs["Coat Weight"].default_value = 1.0
kit.grime(glass, gb, "Coat Roughness", 0.06, 0.28, 90.0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, PT + 0.0004), rotation=(0, 0, yaw)); g = bpy.context.object
g.scale = (PW - 0.003, PH - 0.003, 1); g.data.materials.append(glass)
sm, stex = kit.screen_material("screen", ui_frames[0])
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, PT + 0.0006), rotation=(0, 0, yaw)); ui = bpy.context.object
ui.scale = (PW - 0.006, PH - 0.006, 1); ui.data.materials.append(sm)
kit.image_sequence(stex, ui_frames)
child((0.02, 0.006, 0.0002), (0, PH / 2 - 0.009, PT / 2 + 0.0008), kit.principled("pill", (0, 0, 0), 0.2)[0], 0.0029)
rub, rb = kit.principled("rubber", (0.02, 0.02, 0.022), 0.45); kit.grime(rub, rb, "Roughness", 0.35, 0.6, 400.0)
child((0.008, 0.012, 0.004), (0, -PH / 2 - 0.006, -PT * 0.05), rub)
cable = bpy.data.curves.new("cable", "CURVE"); cable.dimensions = "3D"; cable.bevel_depth = 0.0022; cable.bevel_resolution = 6
sp = cable.splines.new("BEZIER"); pts = [(0.0, -0.088, 0.0035), (-0.02, -0.14, 0.0022), (-0.09, -0.17, 0.0022), (-0.25, -0.12, 0.0022)]
sp.bezier_points.add(len(pts) - 1)
for bp, p in zip(sp.bezier_points, pts):
    bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
co = bpy.data.objects.new("cable", cable); bpy.context.scene.collection.objects.link(co); co.rotation_euler = (0, 0, yaw); cable.materials.append(rub)

if A["disc"]:   # e.g. a CD: a circular RGBA print, 1.2 mm thick
    cm, cb = kit.principled("disc", rough=0.3); kit.texture(cm, cb, A["disc"], alpha=True); cb.inputs["Coat Weight"].default_value = 0.6
    bpy.ops.mesh.primitive_plane_add(size=0.12, location=(0.085, 0.035, 0.0013)); d = bpy.context.object; d.data.materials.append(cm)
    d.modifiers.new("thick", "SOLIDIFY").thickness = 0.0012

# light: low HDRI fill + sun, then off-screen casters so a clear soft-edged shadow crosses the set (and the phone)
kit.hdri_world(0.15)
s = kit.sun()
kit.shadow_caster(s, "wall edge", (1.0, 2.0, 0.02), (A["shadow_x"], 0.0, 0.0), 0.45, 22)   # right edge lands ~0.5 m right of its centre
kit.shadow_caster(s, "window bar", (0.022, 2.0, 0.02), (0.12, 0.0, 0.0), 0.45, 22)

# camera: wide top-down hold, blurred push, close on the lower half, macro on the newest message (edit for your shot)
CAMK = [(0, (0.12, -0.2, 0.36), (0.03, 0.0, 0), 4.0, "LINEAR"), (2, (0.06, -0.16, 0.33), (0.025, 0.0, 0), 4.0, "LINEAR"),
        (8, (0.05, -0.15, 0.31), (0.02, -0.005, 0), 4.0, "LINEAR"), (10, (0.01, -0.12, 0.15), (-0.006, -0.03, 0.008), 2.8, "LINEAR"),
        (15, (0.01, -0.125, 0.14), (-0.006, -0.035, 0.008), 2.8, "CONSTANT"), (16, (0.0, -0.105, 0.105), (-0.008, -0.04, 0.008), 2.2, "LINEAR"),
        (22, (0.0, -0.108, 0.1), (-0.008, -0.042, 0.008), 2.2, "LINEAR"), (24, (-0.03, -0.076, 0.037), (-0.029, -0.032, 0.009), 4.0, "LINEAR"),
        (31, (-0.031, -0.078, 0.035), (-0.029, -0.03, 0.009), 4.0, "LINEAR")]
kit.camera_beats(CAMK)
bpy.ops.render.render(animation=True)
