"""FLAT OUT — an original, wordless Blender short, animated entirely with bpy.

Blender 4.5 LTS:
  blender -b -t 2 --python create_scene.py -- --out /path/to/output
  blender -b /path/to/output/flat-out.blend -t 2 -a

The shadow is a single animated ellipse, projected onto the floor and unfolded
up the wall. The orange character is squash-and-stretch geometry, not a sim.
"""
import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

FPS = 24
FRAMES = 384
WALL_X = 3.85
RADIUS = 0.62


def rgba(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb) + (1,)


def material(name, color, roughness=.6):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba(color)
    bsdf.inputs['Roughness'].default_value = roughness
    return mat


def sphere(name, scale, mat, parent=None, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = location
    obj.scale = scale
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.visible_shadow = False
    return obj


def block(name, location, scale, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Soft edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 4
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def shadow_material(name, color, wall=False):
    """One ellipse in unfolded floor/wall coordinates; no independent blob."""
    mat = material(name, color, .85)
    tree = mat.node_tree
    nodes, links = tree.nodes, tree.links

    def math_node(op, a, b=0):
        node = nodes.new('ShaderNodeMath')
        node.operation = op
        for index, value in enumerate((a, b)):
            if isinstance(value, (int, float)):
                node.inputs[index].default_value = value
            else:
                links.new(value, node.inputs[index])
        return node.outputs[0]

    xyz = nodes.new('ShaderNodeSeparateXYZ')
    geo = nodes.new('ShaderNodeNewGeometry')
    links.new(geo.outputs['Position'], xyz.inputs[0])
    values = {}
    for label, default in [('Travel', -4.4), ('Width', .64), ('Depth', .40)]:
        node = nodes.new('ShaderNodeValue')
        node.label = label
        node.name = label
        node.outputs[0].default_value = default
        values[label] = node.outputs[0]
    u = math_node('ADD', xyz.outputs['Z'], WALL_X) if wall else xyz.outputs['X']
    dx = math_node('DIVIDE', math_node('SUBTRACT', u, values['Travel']), values['Width'])
    dy = math_node('DIVIDE', math_node('SUBTRACT', xyz.outputs['Y'], .13), values['Depth'])
    distance = math_node('ADD', math_node('MULTIPLY', dx, dx), math_node('MULTIPLY', dy, dy))
    edge = nodes.new('ShaderNodeMapRange')
    edge.clamp = True
    edge.inputs['From Min'].default_value = .86
    edge.inputs['From Max'].default_value = 1.08
    edge.inputs['To Min'].default_value = 1
    edge.inputs['To Max'].default_value = 0
    links.new(distance, edge.inputs['Value'])
    mask = edge.outputs[0]
    if wall:
        normal = nodes.new('ShaderNodeSeparateXYZ')
        links.new(geo.outputs['Normal'], normal.inputs[0])
        mask = math_node('MULTIPLY', mask, math_node('LESS_THAN', normal.outputs['X'], -.8))
    else:
        mask = math_node('MULTIPLY', mask, math_node('LESS_THAN', xyz.outputs['X'], WALL_X))
    mix = nodes.new('ShaderNodeMixRGB')
    mix.inputs[1].default_value = rgba(color)
    mix.inputs[2].default_value = rgba('202631')
    links.new(mask, mix.inputs[0])
    links.new(mix.outputs[0], nodes.get('Principled BSDF').inputs['Base Color'])
    return mat, values


def ease(a, b, t):
    t = min(1, max(0, t))
    t = t * t * (3 - 2 * t)
    return a + (b - a) * t


def motion(t):
    """Seconds -> character position, squash, gaze, and the shadow's path."""
    x, z = -4.45, RADIUS
    sx = sy = sz = 1.0
    facing, pupil, blink = .15, .0, 1.0
    shadow, width, depth = -4.26, .62, .36

    # Establish a normal attached shadow through a leisurely little hop.
    if .5 < t < .78:
        q = math.sin(math.pi * (t - .5) / .28)
        sx, sy, sz = 1 + .15*q, 1 + .09*q, 1 - .19*q
        z = RADIUS * sz
    elif .78 <= t < 1.62:
        q = math.sin(math.pi * (t - .78) / .84)
        z += .76 * q
        sz, sx = 1 + .10*q, 1 - .04*q
        width, depth = .62 - .19*q, .36 - .11*q
    elif 1.62 <= t < 1.95:
        q = math.sin(math.pi * (t - 1.62) / .33)
        sx, sy, sz = 1 + .19*q, 1 + .10*q, 1 - .23*q
        z = RADIUS * sz

    # Launch. The shadow misses the departure.
    if 2.15 <= t < 2.5:
        q = (t - 2.15) / .35
        sx, sy, sz = 1 + .2*q, 1 + .10*q, 1 - .3*q
        x -= .15 * q
        z = RADIUS * sz
    elif 2.5 <= t < 3.28:
        q = (t - 2.5) / .78
        x = ease(-4.60, -.45, q)
        sx, sy, sz = 1 + .48*math.sin(math.pi*q), .86, .84
        z = .68 + .24*math.sin(math.pi*q)
        facing, pupil = .48, .025
    elif 3.28 <= t < 3.65:
        q = (t - 3.28) / .37
        x = -.45 + .28*math.sin(math.pi*q)
        sx, sy, sz = 1 - .20*math.sin(math.pi*q), 1, 1 + .14*math.sin(math.pi*q)
        z = RADIUS * sz
    elif t >= 3.65:
        x = -.45

    # Look down, then back. This pause makes the absence readable.
    if 3.75 <= t < 5.65:
        facing = ease(.2, -.75, (t - 4.15) / .45)
        pupil = -.028
        blink = .10 if 4.05 < t < 4.18 else 1
        if 5.0 < t < 5.4:
            q = math.sin(math.pi*(t-5.0)/.4)
            x -= .09*q
            z += .045*q

    # The shadow catches up, passes, and invites the chase.
    if 5.7 <= t < 7.0:
        q = (t - 5.7) / 1.3
        shadow = ease(-4.26, .40, q)
        width = .62 + .65*math.sin(math.pi*q)
        depth = .36 - .13*math.sin(math.pi*q)
        facing = ease(-.75, .55, (t - 6.15) / .45)
        pupil = .026
    elif 7 <= t < 12.45:
        q = (t - 7) / 5.45
        contact = WALL_X - RADIUS*1.13 - .012
        x = -.45 + (contact + .45)*q*q
        sx, sz = 1.05 + .08*q, .98 - .08*q
        z = RADIUS*sz + .12*abs(math.sin(math.pi*(.4*(t-7) + .12*(t-7)**2)))
        shadow = x + .85
        facing, pupil = .65, .03
        if t >= 11.8:
            q_wall = (t - 11.8) / .65
            approach = -.45 + (contact + .45)*(4.8/5.45)**2 + .85
            shadow = approach + (5.25 - approach)*q_wall
            width, depth = .58, .37
    elif t >= 12.45:
        # Impact: a three-dimensional orange becomes a two-dimensional orange.
        q = min(1, (t - 12.45) / .16)
        sx = ease(1.13, .065, q)
        sy = ease(1.0, 1.30, q)
        sz = ease(.90, 1.25, q)
        x = WALL_X - RADIUS*sx - .012
        z = ease(.69, .88, q)
        facing = ease(.70, -math.pi/2, q)
        pupil = 0
        shadow = ease(5.25, 5.70, (t - 12.45) / 1.15)
        width, depth = .59, .38
        if t > 13:
            z -= .095 * min(1, (t - 13) / 2)
            pupil = -.017
            blink = .09 if 14.0 < t < 14.13 else 1

    return (x, z), (sx, sy, sz), facing, pupil, blink, (shadow, width, depth)


def build(out):
    # One small contract check catches geometry crossing the wall before impact.
    for frame in range(1, FRAMES + 1):
        t = (frame - 1) / FPS
        (x, z), (sx, sy, sz), *_, (travel, width, depth) = motion(t)
        assert all(math.isfinite(v) for v in (x, z, sx, sy, sz, travel, width, depth))
        assert min(sx, sy, sz, width, depth) > 0
        assert z - RADIUS*sz >= -.001
        if 7 <= t < 12.45:
            assert x + RADIUS*sx < WALL_X
        if t >= 13.6:
            assert travel + width < WALL_X + 2.64
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.name = 'FLAT OUT | original procedural animation'
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(out / 'frames' / '') + '/'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = rgba('EEF2F6')
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .65

    floor_mat, floor_shadow = shadow_material('Warm paper with living shadow', 'F4EDD9')
    wall_mat, wall_shadow = shadow_material('Blue wall with continuous shadow', 'A0BBD4', wall=True)
    bpy.ops.mesh.primitive_plane_add(size=200)
    bpy.context.object.name = 'Paper stage'
    bpy.context.object.data.materials.append(floor_mat)
    block('The wall', (WALL_X + .19, .10, 1.32), (.38, 3.2, 2.64), wall_mat, .04)

    bpy.ops.object.empty_add(type='PLAIN_AXES')
    character = bpy.context.object
    character.name = 'Orange — squash and stretch'
    sphere('Orange body', (RADIUS,)*3, material('Tangerine rubber', 'F65E37', .48), character)
    bpy.ops.object.empty_add(type='PLAIN_AXES')
    face = bpy.context.object
    face.name = 'Face direction'
    face.parent = character
    whites, pupils = [], []
    white = material('Warm eye white', 'FFF9EB', .62)
    ink = material('Eye ink', '16202B', .60)
    for side in (-1, 1):
        whites.append(sphere('Eye white', (.106, .062, .148), white, face, (side*.18, -.558, .13)))
        pupils.append(sphere('Pupil', (.049, .024, .082), ink, face, (side*.18, -.615, .13)))

    bpy.ops.object.camera_add(location=(-5.2, -14.2, 8.4))
    camera = bpy.context.object
    camera.name = 'One continuous orthographic shot'
    camera.rotation_euler = (Vector((-.05, 0, .55)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 12.7
    scene.camera = camera
    bpy.ops.object.light_add(type='AREA', location=(-3.5, -4.5, 9))
    light = bpy.context.object
    light.name = 'Large softbox'
    light.data.energy = 1600
    light.data.shape = 'DISK'
    light.data.size = 6

    # The title is the final visual pun, not an explanation before the joke.
    bpy.ops.object.text_add()
    title = bpy.context.object
    title.name = 'FLAT OUT. — end title'
    title.data.body = 'FLAT OUT.'
    title.data.size = .72
    title.data.space_character = 1.08
    font = Path('/usr/share/fonts/liberation/LiberationSans-Bold.ttf')
    if font.exists():
        title.data.font = bpy.data.fonts.load(str(font))
    title.parent = camera
    title.location = (-3.92, 1.75, -10)
    title.rotation_euler = (0, 0, 0)
    title_mat = material('Title ink', '25313B')
    emission = title_mat.node_tree.nodes.new('ShaderNodeEmission')
    emission.inputs[0].default_value = rgba('25313B')
    title_mat.node_tree.links.new(emission.outputs[0], title_mat.node_tree.nodes.get('Material Output').inputs['Surface'])
    title.data.materials.append(title_mat)
    title.visible_shadow = False
    title.hide_render = True
    title.keyframe_insert('hide_render', frame=1)
    title.hide_render = False
    title.keyframe_insert('hide_render', frame=334)

    for frame in range(1, FRAMES + 1):
        t = (frame - 1) / FPS
        (x, z), scale, facing, pupil, blink, shadow = motion(t)
        character.location = (x, 0, z)
        character.scale = scale
        character.keyframe_insert('location', frame=frame)
        character.keyframe_insert('scale', frame=frame)
        face.rotation_euler.z = facing
        face.keyframe_insert('rotation_euler', frame=frame)
        for eye in whites:
            eye.scale.z = .148 * blink
            eye.keyframe_insert('scale', frame=frame)
        for side, eye in zip((-1, 1), pupils):
            eye.location.x = side*.18 + pupil
            eye.scale.z = .082 * blink
            eye.keyframe_insert('location', frame=frame)
            eye.keyframe_insert('scale', frame=frame)
        for values in (floor_shadow, wall_shadow):
            for name, value in zip(('Travel', 'Width', 'Depth'), shadow):
                values[name].default_value = value
                values[name].keyframe_insert('default_value', frame=frame)
        # A restrained push-in follows the last acceleration and holds the gag.
        push = ease(0, 1, (t - 11.65) / 2)
        camera.location = (-5.2 + 1.5*push, -14.2, 8.4 + .25*push)
        camera.data.ortho_scale = 12.7 - 3.2*push
        camera.keyframe_insert('location', frame=frame)
        camera.data.keyframe_insert('ortho_scale', frame=frame)

    for label, sec in [('Normal hop', .78), ('Outruns shadow', 2.5), ('Missing shadow', 4.1),
                       ('Shadow overtakes', 6.4), ('Chase', 8.8), ('Flat out', 12.5), ('Title', 13.9)]:
        scene.timeline_markers.new(label, frame=round(sec*FPS) + 1)
    scene['Authorship'] = 'Original concept, code and animation by Codex, an AI agent, for Blucca.'
    scene['Technique'] = 'bpy keyframes, analytic floor/wall shadow, squash and stretch; no stock models.'
    scene['Story'] = 'An orange outruns its shadow, then chases it into a dimension it cannot enter.'
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'flat-out.blend'))
    return scene


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--frames', default='', help='Optional comma-separated preview frames')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'frames').mkdir(exist_ok=True)
    scene = build(args.out.resolve())
    for frame in [int(v) for v in args.frames.split(',') if v]:
        scene.frame_set(frame)
        scene.render.filepath = str(args.out.resolve() / f'preview-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
