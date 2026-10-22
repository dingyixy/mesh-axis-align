import bpy, importlib.util, pathlib, numpy as np
spec = importlib.util.spec_from_file_location('axis12', pathlib.Path(__file__).resolve().parent.parent / 'mesh_axis_align.py')
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a); a.register()
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def cube(name):
    bpy.ops.mesh.primitive_cube_add()
    o=bpy.context.object; o.name=name; o.scale=(3,1,.5)
    o.rotation_euler=(.4,.7,.9); bpy.context.view_layer.update()
    return o

first=cube('keep'); second=first.copy(); second.data=first.data.copy()
bpy.context.scene.collection.objects.link(second); second.name='duplicate'
second.data.uv_layers.active.data[0].uv.x += .2
bpy.context.view_layer.update()
assert a.duplicate_plan([first,second],first,1e-5)==[(second,first)]
assert a.duplicate_plan([first,second],first,1e-5,True)==[]
third=first.copy(); third.data=first.data.copy(); third.name='different_surface'
bpy.context.scene.collection.objects.link(third)
third.data.polygons[0].flip()
assert not a.duplicate_plan([first,third],first,1e-5)
fourth=first.copy();fourth.data=first.data.copy();fourth.location.x+=.1
bpy.context.scene.collection.objects.link(fourth);bpy.context.view_layer.update()
assert not a.duplicate_plan([first,fourth],first,1e-5)
print('PASS duplicate position, winding, UV strict/default rules')

group=bpy.data.node_groups.new('Auto Smooth verified','GeometryNodeTree')
group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
inp=group.nodes.new('NodeGroupInput');out=group.nodes.new('NodeGroupOutput')
smooth=group.nodes.new('GeometryNodeSetShadeSmooth')
group.links.new(inp.outputs['Geometry'],smooth.inputs['Geometry']);group.links.new(smooth.outputs['Geometry'],out.inputs['Geometry'])
mod=first.modifiers.new('Auto Smooth','NODES');mod.node_group=group
try:
    a.align_object(first)
    raise AssertionError('nonuniform smoothing change should roll back')
except a.AlignmentError:
    pass
bpy.ops.object.select_all(action='DESELECT');first.select_set(True)
bpy.context.view_layer.objects.active=first
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
before=a.evaluated_state(first);a.align_object(first);after=a.evaluated_state(first)
assert np.allclose(before[0],after[0],atol=1e-5)
assert np.allclose(before[1],after[1],atol=2e-4)
assert first.modifiers[0].node_group==group
unsafe=cube('unsafe');bad=unsafe.modifiers.new('Auto Smooth','NODES')
bad.node_group=group.copy();bad.node_group.nodes.new('GeometryNodeSetPosition')
assert not a.is_safe_smoothing(bad)
print('PASS smoothing preserved; misleading Auto Smooth name rejected')

# Fresh identical pair for the actual batch operator and undo.
one=cube('UndoKeep');two=one.copy();two.data=one.data.copy();two.name='UndoDelete'
bpy.context.scene.collection.objects.link(two)
bpy.ops.object.select_all(action='DESELECT');one.select_set(True);two.select_set(True)
bpy.context.view_layer.objects.active=one;bpy.context.view_layer.update()
bpy.context.preferences.edit.use_global_undo=True
bpy.ops.ed.undo_push(message='Before test batch')
assert bpy.ops.object.mesh_axis_align_and_deduplicate()=={'FINISHED'}
assert bpy.data.objects.get('UndoDelete') is None
assert bpy.data.objects.get('UndoKeep') is not None
assert not one.show_axis
bpy.ops.ed.undo_push(message='After test batch')
bpy.ops.ed.undo()
assert bpy.data.objects.get('UndoDelete') is not None
assert bpy.data.objects.get('UndoKeep') is not None
print('PASS operator deletes duplicate only; undo restores both')
print('ALL V1.2 TESTS PASSED')

base=np.array([[1.,0,0]])
for degrees in (.02,.075,.1,.2,30):
    rad=np.radians(degrees)
    result=a.normal_error_degrees(base,np.array([[np.cos(rad),np.sin(rad),0.]]))
    assert abs(result-degrees)<1e-8
assert a.normal_error_degrees(base,np.array([[float('nan'),0,0]]))==float('inf')
print('PASS: angular roundoff and significant normal changes distinguished')
