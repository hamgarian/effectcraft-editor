"""Helpers for photoreal 3D sets rendered headless in Blender (tested on Blender 5.0) and placed in EffectCraft as
a PNG sequence. Import from a set script run with `blender -b -P set.py -- ...` after adding this folder to sys.path.
Every helper here came from a render that read as "CG" or broke; see references/rules.md -> Photoreal 3D.
"""
import math
import os

import bpy
from mathutils import Vector


def args(argv, defaults):
    """parse `--key value` pairs after `--` into a dict, starting from `defaults` (values keep their default's type)"""
    out = dict(defaults)
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    for i in range(0, len(rest) - 1, 2):
        k = rest[i].lstrip("-").replace("-", "_")
        if k in out and out[k] is not None and not isinstance(out[k], str):
            out[k] = type(out[k])(rest[i + 1])
        else:
            out[k] = rest[i + 1]
    return out


def scene(res=(1440, 1080), fps=20, frames=(0, 0), out="", samples=96, exposure=0.0):
    """empty scene, Cycles on the GPU when available (OptiX, then CUDA), denoised, AgX, motion blur on"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = frames
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 8
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = dev; prefs.get_devices()
            except TypeError:
                continue
            if any(d.type == dev for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == dev
                sc.cycles.device = "GPU"
                break
    except KeyError:
        pass   # no cycles prefs: CPU render, slower but the same image
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.8
    sc.view_settings.view_transform = "AgX"   # photographic roll-off; "Standard" clips like CG
    sc.view_settings.exposure = exposure      # brighten here, not with a gamma lift in the compositor (that greys blacks)
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(out, "frame_") if out else ""
    return sc


def principled(name, rgb=(0.5, 0.5, 0.5), rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    return m, b


def node(m, kind, **inputs):
    n = m.node_tree.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def texture(m, b, path, alpha=False, bump=0.0):
    """image -> base colour; optional alpha cut-out and a bump from the image's own detail"""
    tx = m.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(path)
    m.node_tree.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    if alpha:
        m.node_tree.links.new(tx.outputs["Alpha"], b.inputs["Alpha"])
        try:
            m.surface_render_method = "DITHERED"
        except AttributeError:
            m.blend_method = "HASHED"
    if bump:
        bn = node(m, "ShaderNodeBump", Strength=bump, Distance=0.002)
        m.node_tree.links.new(tx.outputs["Color"], bn.inputs["Height"]); m.node_tree.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return tx


def grime(m, b, socket, lo, hi, scale=60.0):
    """noise-driven variation into a Principled input (smudges, wear): real surfaces are never uniform"""
    nz = node(m, "ShaderNodeTexNoise", Scale=scale, Detail=6.0)
    mr = node(m, "ShaderNodeMapRange", **{"From Min": 0.35, "From Max": 0.75, "To Min": lo, "To Max": hi})
    m.node_tree.links.new(nz.outputs["Fac"], mr.inputs["Value"]); m.node_tree.links.new(mr.outputs["Result"], b.inputs[socket])


def screen_material(name, first_image, emission=1.2, diffuse=0.08):
    """a display: emissive image under a smudged clear coat, with a diffuse base so sunlight washes it out and
    shadows show on it (a pure-black emissive panel ignores light, so shadows skip the device)"""
    m, b = principled(name, (diffuse, diffuse, diffuse * 1.06), 0.5)
    tx = m.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = bpy.data.images.load(first_image)
    m.node_tree.links.new(tx.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = emission
    b.inputs["Coat Weight"].default_value = 1.0; grime(m, b, "Coat Roughness", 0.06, 0.28, 90.0)
    return m, tx


def image_sequence(tex_node, paths):
    """show paths[frame] on an image node: load every frame and swap it before each frame renders
    (an animated UI rendered from EffectCraft, projected onto a 3D screen)"""
    imgs = [bpy.data.images.load(p) for p in paths]

    def swap(scene, *_):
        tex_node.image = imgs[max(0, min(len(imgs) - 1, scene.frame_current))]
    bpy.app.handlers.frame_change_pre.append(swap)
    return imgs


def hdri_world(strength=0.15, rotation_deg=130.0, name="interior.exr"):
    """bounce light + reflections from an HDRI that ships with Blender (datafiles/studiolights/world).
    Rotate it when its window shows up as a hotspot on glass. Keep it low so sun/shade contrast survives."""
    w = bpy.data.worlds.new("world"); bpy.context.scene.world = w; w.use_nodes = True; nt = w.node_tree
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(bpy.utils.system_resource("DATAFILES"), "studiolights", "world", name))
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, math.radians(rotation_deg))
    nt.links.new(nt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"]); nt.nodes["Background"].inputs["Strength"].default_value = strength
    return w


def sun(elev_deg=40.0, azim_deg=-30.0, energy=9.0, angle_deg=2.5, colour=(1.0, 0.94, 0.86)):
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(elev_deg), math.radians(azim_deg), 0)); s = bpy.context.object
    s.data.energy = energy; s.data.angle = math.radians(angle_deg); s.data.color = colour
    bpy.context.view_layer.update()
    return s


def shadow_caster(sun_obj, name, size, ground_point, height, zrot_deg=0.0):
    """a box that only casts shadow (invisible to camera and reflections), placed so its centre projects along the
    sun onto `ground_point`. Use a wide box for a wall edge, a thin one for a window bar or branch."""
    d = sun_obj.matrix_world.to_3x3() @ Vector((0, 0, -1))   # direction the light travels
    c = Vector(ground_point) - d * (height / -d.z)
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=(0, 0, math.radians(zrot_deg))); o = bpy.context.object
    o.scale = size; o.name = name; o.visible_camera = False; o.visible_glossy = False
    return o


def fcurves(idblock):
    """an object's/data's F-curves; Blender 5 keeps them in action layers -> strips -> channelbags"""
    a = idblock.animation_data.action
    if hasattr(a, "fcurves") and len(a.fcurves):
        return list(a.fcurves)
    return [fc for l in a.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def camera_beats(keys, lens=35.0):
    """camera that tracks a focus empty. keys: [(frame, cam_xyz, target_xyz, fstop, interp_to_next), ...];
    interp "CONSTANT" holds a beat, "LINEAR"/"QUAD" moves (in-between frames get motion blur = the ref's smear frames)"""
    bpy.ops.object.camera_add(); cam = bpy.context.object; bpy.context.scene.camera = cam
    cam.data.lens = lens; cam.data.dof.use_dof = True
    cam.data.clip_start = 0.002   # the default 10 cm erases everything in a macro shot
    tgt = bpy.data.objects.new("focus", None); bpy.context.scene.collection.objects.link(tgt); cam.data.dof.focus_object = tgt
    tr = cam.constraints.new("TRACK_TO"); tr.target = tgt; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"
    for fr, c, t, fs, _ in keys:
        cam.location = c; cam.keyframe_insert("location", frame=fr)
        tgt.location = t; tgt.keyframe_insert("location", frame=fr)
        cam.data.dof.aperture_fstop = fs; cam.data.dof.keyframe_insert("aperture_fstop", frame=fr)
    interp = {k[0]: k[4] for k in keys}
    for idb in (cam, tgt, cam.data):
        for fc in fcurves(idb):
            for kp in fc.keyframe_points:
                kp.interpolation = interp.get(int(round(kp.co[0])), "LINEAR")
    return cam, tgt
