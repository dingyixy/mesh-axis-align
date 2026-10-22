import bpy
import importlib.util
import pathlib
import numpy as np
from mathutils import Euler, Matrix, Vector

root = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('mesh_axis_align_tested', root / 'mesh_axis_align.py')
addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addon)
addon.register()

def rectangle(name):
    mesh = bpy.data.meshes.new(name)
    # Interior triangle diagonal exceeds every outline edge.
    mesh.from_pydata([(-3,-1,0),(3,-1,0),(3,1,0),(-3,1,0)], [], [(0,1,2),(0,2,3)])
    mesh.uv_layers.new(name='UVMap')
    for i, loop in enumerate(mesh.uv_layers.active.data):
        loop.uv = (i / 6, i % 2)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.rotation_euler = Euler((.73,-.44,.91))
    obj.location = (4,-8,3)
    obj.scale = (1.5,.7,2)
    bpy.context.view_layer.update()
    return obj

obj = rectangle('rotated_scaled')
shared = bpy.data.objects.new('unselected_shared', obj.data)
bpy.context.scene.collection.objects.link(shared)
shared_before = addon.world_points(shared)
before = addon.world_points(obj)
uv_before = [tuple(p.uv) for p in obj.data.uv_layers.active.data]
faces_before = [tuple(p.vertices) for p in obj.data.polygons]
expected = (obj.matrix_world.to_3x3() @ (obj.data.vertices[1].co-obj.data.vertices[0].co)).normalized()
mat = bpy.data.materials.new('preserved_material')
obj.data.materials.append(mat)
info = addon.align_object(obj)
assert np.allclose(before, addon.world_points(obj), atol=2e-6)
assert np.array_equal(shared_before, addon.world_points(shared))
assert obj.data != shared.data
assert obj.data.materials[0] == mat
assert uv_before == [tuple(p.uv) for p in obj.data.uv_layers.active.data]
assert faces_before == [tuple(p.vertices) for p in obj.data.polygons]
assert abs(obj.matrix_world.to_3x3().col[0].dot(expected)) > .99999
assert abs(obj.matrix_world.to_3x3().determinant()-1) < 1e-5
matrix_once = np.array(obj.matrix_world)
addon.align_object(obj)
assert np.allclose(matrix_once, np.array(obj.matrix_world), atol=2e-6)
print('PASS: outline axis, world shape, origin, shared mesh, UVs, materials, topology, repeatability')

for kind in ('parent', 'modifier', 'shape_key', 'animation', 'mirror'):
    target = rectangle('skip_' + kind)
    if kind == 'parent': target.parent = shared
    elif kind == 'modifier': target.modifiers.new('Armature', 'ARMATURE')
    elif kind == 'shape_key': target.shape_key_add(name='Basis')
    elif kind == 'animation': target.keyframe_insert(data_path='location', frame=1)
    else: target.scale.x = -1
    bpy.context.view_layer.update()
    original_data = target.data
    try:
        addon.align_object(target)
        raise AssertionError('unsafe object was not skipped: ' + kind)
    except addon.AlignmentError:
        pass
    assert target.data == original_data
print('PASS: parent, modifier, shape key, animation and mirror exclusions')

for points in (np.array([(0,0,0),(1,0,0),(2,0,0)]),
               np.array([(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)])):
    try:
        addon.find_basis(points, mode='PLANAR')
        raise AssertionError('ambiguous plane was not skipped')
    except addon.AlignmentError:
        pass
print('PASS: line and volumetric rejection')

bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
target.select_set(True)
bpy.context.view_layer.objects.active = obj
result = bpy.ops.object.mesh_axis_align()
assert result == {'FINISHED'}
assert bpy.context.scene.transform_orientation_slots[0].type == 'LOCAL'
assert '定轴 1 个，跳过 1 个' in bpy.context.window_manager.mesh_axis_align_report
addon.unregister()
print('PASS: batch operator, partial success report, registration cleanup')
rotation = np.array(Euler((.41,.73,-.38)).to_matrix())
corners = np.array([(x,y,z) for x in (-3,3) for y in (-1.5,1.5) for z in (-1,1)])
solid = corners @ rotation.T + (12,-4,8)
frame, info = addon.find_basis(solid)
assert info['mode'] == 'SOLID'
assert np.allclose(info['dimensions_xyz'], (6,3,2), atol=1e-5), info
assert abs(frame.col[0].dot(Vector(rotation[:,0]))) > .99999
assert abs(frame.determinant()-1) < 1e-5
# Internal vertices and repeated points must not change the outer-shape axes.
dense = np.concatenate([solid, np.repeat(solid[:1], 200, axis=0)])
frame2, info2 = addon.find_basis(dense, mode='SOLID')
assert np.allclose(np.abs(np.array(frame)), np.abs(np.array(frame2)), atol=2e-5)
cube = np.array([(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)])
fc, ic = addon.find_basis(cube)
assert np.allclose(ic['dimensions_xyz'], (2,2,2), atol=1e-5)
assert abs(fc.determinant()-1) < 1e-5
print('PASS: solid box length ordering, rotation, density independence, symmetric cube')
print('ALL TESTS PASSED')

