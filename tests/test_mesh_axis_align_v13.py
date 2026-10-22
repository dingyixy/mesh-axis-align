"""Run in a factory-startup background Blender, never against the user's scene."""
import bpy
import importlib.util
import pathlib
import numpy as np

spec = importlib.util.spec_from_file_location('axis13', pathlib.Path(__file__).resolve().parent.parent / 'mesh_axis_align.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
a.register()


def setup():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_cube_add()
    keep = bpy.context.object
    keep.name = 'Z_active_keep'
    keep.scale = (3, 1, .5)
    keep.rotation_euler = (.4, .7, .9)
    dup = keep.copy()
    dup.data = keep.data.copy()
    dup.name = 'A_duplicate'
    bpy.context.scene.collection.objects.link(dup)
    untouched = keep.copy()
    untouched.data = keep.data.copy()
    untouched.name = 'unselected_duplicate'
    bpy.context.scene.collection.objects.link(untouched)
    dup.select_set(True)
    untouched.select_set(False)
    bpy.context.view_layer.objects.active = keep
    bpy.context.view_layer.update()
    bpy.context.scene.transform_orientation_slots[0].type = 'GLOBAL'
    return keep, dup, untouched


def expect_undo():
    bpy.ops.ed.undo_push(message='After action')
    bpy.ops.ed.undo()
    assert bpy.data.objects.get('Z_active_keep')
    assert bpy.data.objects.get('A_duplicate')


bpy.context.preferences.edit.use_global_undo = True
keep, dup, outside = setup()
before = {o.name: a.world_points(o) for o in (keep, dup, outside)}
old = keep.matrix_world.copy()
bpy.ops.ed.undo_push(message='Before alignment')
assert bpy.ops.object.mesh_axis_align() == {'FINISHED'}
assert len(bpy.data.objects) == 3
assert not np.allclose(old, keep.matrix_world)
for o in (keep, dup, outside):
    assert np.allclose(before[o.name], a.world_points(o), atol=1e-5)
assert not keep.show_axis and not dup.show_axis
expect_undo()
assert np.allclose(bpy.data.objects['Z_active_keep'].matrix_world, old)
print('PASS alignment-only keeps all duplicates, preserves world geometry, and undoes')

keep, dup, outside = setup()
old = keep.matrix_world.copy()
mesh = keep.data
keep.show_axis = True
bpy.ops.ed.undo_push(message='Before deduplication')
assert bpy.ops.object.mesh_axis_deduplicate() == {'FINISHED'}
assert not bpy.data.objects.get('A_duplicate')
assert bpy.data.objects.get('unselected_duplicate')
assert keep.data == mesh and np.array_equal(old, keep.matrix_world)
assert keep.show_axis
assert bpy.context.scene.transform_orientation_slots[0].type == 'GLOBAL'
expect_undo()
print('PASS dedup-only preserves active keeper mesh, axes, display and unselected objects; undo restores duplicate')

keep, dup, outside = setup()
dup.data.uv_layers.active.data[0].uv.x += .2
assert bpy.ops.object.mesh_axis_deduplicate(match_appearance=True) == {'CANCELLED'}
assert bpy.data.objects.get('A_duplicate')
assert bpy.ops.object.mesh_axis_deduplicate(match_appearance=False) == {'FINISHED'}
assert bpy.ops.object.mesh_axis_deduplicate() == {'CANCELLED'}
assert '删除重复 0 个' in bpy.context.window_manager.mesh_axis_align_report
print('PASS independent dedup respects strict UV setting and reports no-op')

keep, dup, outside = setup()
before = a.world_points(keep)
bpy.ops.ed.undo_push(message='Before combined')
assert bpy.ops.object.mesh_axis_align_and_deduplicate() == {'FINISHED'}
assert not bpy.data.objects.get('A_duplicate')
assert np.allclose(before, a.world_points(keep), atol=1e-5)
assert bpy.context.scene.transform_orientation_slots[0].type == 'LOCAL'
expect_undo()
print('PASS combined operation aligns and deduplicates in a single undo step')

keep, dup, outside = setup()
original_align = a.align_object
def fail(*args, **kwargs):
    raise a.AlignmentError('Simulated alignment failure')
a.align_object = fail
try:
    assert bpy.ops.object.mesh_axis_align_and_deduplicate() == {'CANCELLED'}
    assert bpy.data.objects.get('A_duplicate')
    assert '保留项定轴失败，未删除' in bpy.context.window_manager.mesh_axis_align_report
    assert bpy.ops.object.mesh_axis_deduplicate() == {'FINISHED'}
finally:
    a.align_object = original_align
print('PASS combined failure retains duplicate; dedup-only does not call alignment')

keep, dup, outside = setup()
keep.modifiers.new('Unsupported bevel', 'BEVEL')
assert bpy.ops.object.mesh_axis_deduplicate() == {'CANCELLED'}
assert bpy.data.objects.get('A_duplicate')
assert '不支持的修改器' in bpy.context.window_manager.mesh_axis_align_report
print('PASS unsupported objects are reported and left intact')

assert 'mode' in bpy.ops.object.mesh_axis_align.get_rna_type().properties
assert 'match_appearance' not in bpy.ops.object.mesh_axis_align.get_rna_type().properties
assert 'mode' not in bpy.ops.object.mesh_axis_deduplicate.get_rna_type().properties
assert 'match_appearance' in bpy.ops.object.mesh_axis_deduplicate.get_rna_type().properties
assert 'mode' in bpy.ops.object.mesh_axis_align_and_deduplicate.get_rna_type().properties
assert 'match_appearance' in bpy.ops.object.mesh_axis_align_and_deduplicate.get_rna_type().properties
a.unregister()
a.register()
a.unregister()
assert not hasattr(bpy.types.WindowManager, 'mesh_axis_duplicate_tolerance')
print('PASS operator options are independent; registration and clean unregistration succeed')
print('ALL V1.3 TESTS PASSED')
