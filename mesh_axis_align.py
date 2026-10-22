bl_info = {
    "name": "网格边定轴 / Mesh Axis Align",
    "author": "Codex",
    "version": (1, 3, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > 网格工具",
    "description": "独立或同时执行所选网格定轴、重合网格去重，保持世界空间形状",
    "category": "Object",
}

import bpy
import numpy as np
from mathutils import Matrix, Vector
from bpy.props import BoolProperty, FloatProperty, EnumProperty


class AlignmentError(Exception):
    pass


def is_safe_smoothing(modifier):
    if modifier.type != 'NODES' or not modifier.node_group:
        return False
    # Inspect behavior, not a user-editable modifier name.
    allowed = {'NodeGroupInput', 'NodeGroupOutput', 'NodeReroute', 'NodeFrame',
               'GeometryNodeSetShadeSmooth', 'GeometryNodeInputMeshEdgeAngle',
               'GeometryNodeInputEdgeSmooth', 'GeometryNodeInputShadeSmooth',
               'FunctionNodeBooleanMath', 'FunctionNodeCompare', 'ShaderNodeMath'}
    nodes = modifier.node_group.nodes
    return (any(n.bl_idname == 'GeometryNodeSetShadeSmooth' for n in nodes)
            and all(n.bl_idname in allowed for n in nodes)
            and not modifier.node_group.animation_data)


def check_object(obj):
    if obj.type != 'MESH':
        raise AlignmentError("不是网格")
    if obj.mode != 'OBJECT':
        raise AlignmentError("请切换到物体模式")
    if obj.library or obj.override_library or obj.data.library:
        raise AlignmentError("链接或库覆盖对象")
    if obj.parent or obj.children:
        raise AlignmentError("存在父子关系；请在副本上处理")
    if obj.constraints:
        raise AlignmentError('存在约束')
    unsupported = [m.name for m in obj.modifiers if not is_safe_smoothing(m)]
    if unsupported:
        raise AlignmentError('不支持的修改器：' + '、'.join(unsupported))
    if obj.animation_data or obj.data.animation_data:
        raise AlignmentError("存在动画或驱动")
    if obj.data.shape_keys:
        raise AlignmentError("存在形态键")
    if obj.data.has_custom_normals:
        raise AlignmentError("存在自定义法向")
    if obj.matrix_world.determinant() <= 1e-12:
        raise AlignmentError("镜像或零缩放，请先在副本上处理")
    if len(obj.data.vertices) < 3 or not obj.data.polygons:
        raise AlignmentError("没有足够的面")


def world_points(obj):
    coords = np.empty(len(obj.data.vertices) * 3, dtype=np.float64)
    obj.data.vertices.foreach_get('co', coords)
    coords = coords.reshape((-1, 3))
    matrix = np.array(obj.matrix_world, dtype=np.float64)
    return coords @ matrix[:3, :3].T + matrix[:3, 3]


def evaluated_state(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh(preserve_all_data_layers=True,
                             depsgraph=bpy.context.evaluated_depsgraph_get())
    try:
        matrix = np.array(obj.matrix_world)
        points = np.array([v.co[:] for v in mesh.vertices]) @ matrix[:3,:3].T + matrix[:3,3]
        normal_matrix = np.linalg.inv(matrix[:3,:3]).T
        normals = np.array([n.vector[:] for n in mesh.corner_normals]) @ normal_matrix.T
        normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-30)
        return points, normals
    finally:
        evaluated.to_mesh_clear()


def normal_error_degrees(before, after):
    """Angular comparison of normalized directions, stable near zero angle."""
    if before.shape != after.shape or not np.isfinite(after).all():
        return float('inf')
    if len(before) == 0:
        return 0.0
    chord = np.linalg.norm(before - after, axis=1)
    return float(np.degrees(2 * np.arcsin(np.clip(chord / 2, 0, 1))).max())


def duplicate_key(obj, tolerance, match_appearance=False):
    """Conservative equality: geometry, winding, UVs, materials and smoothing.

    Quantization may miss points straddling a cell boundary; never use only bounds.
    """
    from collections import Counter
    check_object(obj)
    mesh = obj.data
    pts = world_points(obj)
    if not np.isfinite(pts).all():
        raise AlignmentError('无效顶点坐标')
    coords = [tuple(int(round(float(c)/tolerance)) for c in p) for p in pts]
    def cycle(values):
        values = tuple(values)
        return min(values[i:]+values[:i] for i in range(len(values)))
    faces = []
    for p in mesh.polygons:
        corners = []
        for li in p.loop_indices:
            uv = tuple(tuple(round(float(c), 6) for c in layer.data[li].uv) for layer in mesh.uv_layers) if match_appearance else ()
            corners.append((coords[mesh.loops[li].vertex_index], uv))
        material = obj.material_slots[p.material_index].material if p.material_index < len(obj.material_slots) else None
        faces.append((cycle(corners), material.as_pointer() if material and match_appearance else 0, p.use_smooth))
    # Other data layers may have independent meaning; require exact indexed equality.
    attributes = []
    for attr in mesh.attributes:
        if not match_appearance:
            break
        if attr.name.startswith('.') or attr.name in {'position', 'sharp_face', 'sharp_edge'} or attr.name in mesh.uv_layers:
            continue
        attributes.append((attr.name, attr.domain, attr.data_type,
                           tuple(repr(getattr(d, 'value', getattr(d, 'vector', getattr(d, 'color', None)))) for d in attr.data)))
    mods = tuple((m.node_group.as_pointer(), m.show_viewport, m.show_render,
                  tuple(sorted((k,repr(v)) for k,v in m.items()))) for m in obj.modifiers)
    edges = [(tuple(sorted((coords[e.vertices[0]],coords[e.vertices[1]]))), e.use_edge_sharp) for e in mesh.edges]
    visibility = (obj.hide_render, obj.hide_viewport, obj.hide_get(), obj.display_type)
    return (tuple(sorted(Counter(coords).items())), tuple(sorted(Counter(edges).items())),
            tuple(sorted(Counter(faces).items())), tuple(attributes), mods, visibility)


def duplicate_plan(objects, active, tolerance, match_appearance=False, skipped=None):
    keepers, duplicates = {}, []
    # Keep the active object; otherwise choose by name deterministically.
    for obj in sorted(objects, key=lambda o: (o != active, o.name)):
        if obj.type != 'MESH':
            continue
        try:
            key = duplicate_key(obj, tolerance, match_appearance)
        except Exception as exc:
            if skipped is not None:
                skipped.append('%s：%s' % (obj.name, exc))
            continue
        if key in keepers:
            duplicates.append((obj, keepers[key]))
        else:
            keepers[key] = obj
    return duplicates


def hull_2d(points):
    # Convex outline excludes internal triangulation diagonals. No mesh edit.
    points = sorted(set(map(tuple, points)))
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    lower, upper = [], []
    for point in points:
        while len(lower) > 1 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(points):
        while len(upper) > 1 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return np.array(lower[:-1] + upper[:-1])


def solid_basis(points):
    """Approximate minimum-volume oriented box of the convex outer shape.

    Hull face/edge frames avoid density bias and internal triangulation diagonals.
    Candidate count is bounded for batch work; not an exact global OBB solver.
    """
    import bmesh
    center = points.mean(axis=0)
    size = float(np.linalg.norm(np.ptp(points, axis=0)))
    if size < 1e-12:
        raise AlignmentError('网格尺寸过小')
    normalized = (points - center) / size
    bm = bmesh.new()
    try:
        for p in np.unique(normalized, axis=0):
            bm.verts.new(p)
        bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
        bm.normal_update()
        faces = sorted(bm.faces, key=lambda f: f.calc_area(), reverse=True)[:128]
        surface = {v for f in bm.faces for v in f.verts}
        hull = np.array([tuple(v.co) for v in surface])
        if len(hull) < 4:
            raise AlignmentError('无法建立立体外轮廓')
        _, pca = np.linalg.eigh(np.cov(hull.T))
        candidates = [np.eye(3), pca]
        seen = set()
        for face in faces:
            z = face.normal.normalized()
            for edge in face.edges:
                x = (edge.verts[1].co - edge.verts[0].co).normalized()
                y = z.cross(x).normalized()
                if y.length < .9:
                    continue
                frame = np.array(Matrix((x, y, x.cross(y))).transposed())
                key = tuple(np.round(np.abs(frame), 5).flat)
                if key not in seen:
                    candidates.append(frame)
                    seen.add(key)
        best = None
        for frame in candidates:
            spans = np.ptp(hull @ frame, axis=0)
            volume = float(np.prod(spans))
            order = sorted(range(3), key=lambda i: (-round(float(spans[i]), 6),
                                                    tuple(-abs(v) for v in frame[:, i])))
            x = Vector(frame[:, order[0]]).normalized()
            z = Vector(frame[:, order[2]]).normalized()
            for value in x:
                if abs(value) > 1e-5:
                    if value < 0: x.negate()
                    break
            for i in (2, 1, 0):
                if abs(z[i]) > 1e-5:
                    if z[i] < 0: z.negate()
                    break
            y = z.cross(x).normalized()
            x = y.cross(z).normalized()
            canonical = Matrix((x, y, z)).transposed()
            tie = tuple(round(v, 5) for row in canonical for v in row)
            if best is None or volume < best[0] * (1-1e-5) or (
                    abs(volume-best[0]) <= best[0]*1e-5 and tie > best[1]):
                best = (volume, tie, canonical)
        frame = best[2]
        dimensions = np.ptp((points-center) @ np.array(frame), axis=0)
        return frame, dimensions.tolist()
    finally:
        bm.free()


def find_basis(points, max_thickness_ratio=0.15, flip_x=False, flip_z=False, mode='AUTO'):
    if not np.isfinite(points).all():
        raise AlignmentError("顶点坐标包含无效数值")
    center = points.mean(axis=0)
    centered = points - center
    eigenvalues, vectors = np.linalg.eigh(centered.T @ centered / len(points))
    if eigenvalues[1] <= max(eigenvalues[2] * 1e-10, 1e-20):
        raise AlignmentError("网格近似一条线，无法确定 XY 平面")
    ratio = float(np.sqrt(max(0.0, eigenvalues[0]) / eigenvalues[1]))
    if mode not in {'AUTO', 'PLANAR', 'SOLID'}:
        raise AlignmentError('未知定轴模式')
    if mode == 'SOLID' or (mode == 'AUTO' and ratio > max_thickness_ratio):
        frame, dimensions = solid_basis(points)
        x, y, z = [frame.col[i].copy() for i in range(3)]
        if flip_x: x.negate()
        if flip_z: z.negate()
        y = z.cross(x).normalized()
        return Matrix((x, y, z)).transposed(), {
            'mode': 'SOLID', 'thickness_ratio': ratio, 'dimensions_xyz': dimensions}
    if ratio > max_thickness_ratio:
        raise AlignmentError("没有明确主平面（厚度比 %.3f）" % ratio)
    plane = vectors[:, 1:]
    hull = hull_2d(centered @ plane)
    if len(hull) < 3:
        raise AlignmentError("外轮廓无法构成平面")
    edges = np.roll(hull, -1, axis=0) - hull
    lengths = np.linalg.norm(edges, axis=1)
    # Equal opposite edges should select the same direction on repeated runs.
    maximum = lengths.max()
    candidates = np.flatnonzero(lengths >= maximum * (1.0 - 1e-6))
    directions = []
    for index in candidates:
        direction = Vector(plane @ (edges[index] / lengths[index]))
        for component in direction:
            if abs(component) > 1e-5:
                if component < 0:
                    direction.negate()
                break
        directions.append(direction)
    x = max(directions, key=lambda d: tuple(round(v, 6) for v in d)).normalized()
    z = Vector(vectors[:, 0]).normalized()
    for index in (2, 1, 0):
        if abs(z[index]) > 1e-5:
            if z[index] < 0:
                z.negate()
            break
    if flip_x:
        x.negate()
    if flip_z:
        z.negate()
    y = z.cross(x).normalized()
    z = x.cross(y).normalized()
    basis = Matrix((x, y, z)).transposed()
    return basis, {"mode": "PLANAR", "thickness_ratio": ratio, "outline_edge_length": float(maximum)}


def align_object(obj, max_thickness_ratio=0.15, flip_x=False, flip_z=False, mode='AUTO'):
    check_object(obj)
    before = world_points(obj)
    basis, info = find_basis(before, max_thickness_ratio, flip_x, flip_z, mode)
    old_matrix = obj.matrix_world.copy()
    old_rotation_mode = obj.rotation_mode
    new_matrix = basis.to_4x4()
    new_matrix.translation = old_matrix.translation
    transform = new_matrix.inverted() @ old_matrix
    old_mesh = obj.data
    evaluated_before = evaluated_state(obj) if obj.modifiers else None
    # Always work on a private copy: shared meshes outside this batch stay intact.
    new_mesh = old_mesh.copy()
    try:
        new_mesh.transform(transform)
        new_mesh.update()
        obj.data = new_mesh
        obj.matrix_world = new_matrix
        bpy.context.view_layer.update()
        error = float(np.linalg.norm(world_points(obj) - before, axis=1).max())
        # Blender coordinates are float32, with absolute precision dependent on location.
        extent = float(np.linalg.norm(np.ptp(before, axis=0)))
        tolerance = max(1e-6, extent * 2e-6, float(np.abs(before).max()) * 5e-7)
        if error > tolerance and obj.rotation_mode != 'QUATERNION':
            # Matrix-to-Euler conversion can lose precision near gimbal lock.
            obj.rotation_mode = 'QUATERNION'
            obj.matrix_world = new_matrix
            bpy.context.view_layer.update()
            error = float(np.linalg.norm(world_points(obj) - before, axis=1).max())
        if not np.isfinite(error) or error > tolerance:
            raise AlignmentError("世界坐标校验未通过，已回退")
        if evaluated_before is not None:
            after = evaluated_state(obj)
            if (any(a.shape != b.shape for a,b in zip(evaluated_before, after))
                    or not np.allclose(evaluated_before[0], after[0], atol=tolerance, rtol=0)):
                raise AlignmentError('修改器求值后的几何位置或数量改变，已回退')
            angle = normal_error_degrees(evaluated_before[1], after[1])
            info['normal_error_degrees'] = angle
            # float32 vertices on small/slender triangles may accumulate hundredths
            # of a degree of roundoff, even with unit object scale.
            if angle > 0.1:
                raise AlignmentError('平滑法向最大偏差 %.4f°，超过 0.1°，已回退' % angle)
    except Exception:
        obj.data = old_mesh
        obj.rotation_mode = old_rotation_mode
        obj.matrix_world = old_matrix
        if new_mesh.users == 0:
            bpy.data.meshes.remove(new_mesh)
        raise
    if old_mesh.users == 0 and not old_mesh.use_fake_user:
        old_name = old_mesh.name
        bpy.data.meshes.remove(old_mesh)
        new_mesh.name = old_name
    info['max_world_error'] = error
    return info


def alignment_properties():
    return dict(
    mode=EnumProperty(name='定轴模式', default='AUTO', items=[
        ('AUTO', '自动：薄板 / 立体', '根据厚度自动选择算法'),
        ('PLANAR', '薄板：最长轮廓边', '沿用 1.0 的主平面算法'),
        ('SOLID', '立体：整体长中短轴', '用凸包近似最小体积定向包围盒，X 最长、Y 次长、Z 最短')]),
    max_thickness_ratio=FloatProperty(
        name='最大厚度比', default=0.15, min=0.001, max=0.5,
        description='厚度与宽度标准差之比；自动模式超出后改用立体算法，薄板模式则跳过'),
    flip_x=BoolProperty(name='反转 X（同时反转 Y）', default=False),
    flip_z=BoolProperty(name='反转 Z（同时反转 Y）', default=False),
    show_axes=BoolProperty(name='显示物体 XYZ 标注', default=False))


def deduplicate_properties():
    return dict(
    match_appearance=BoolProperty(name='要求材质和 UV 也一致', default=False),
    duplicate_tolerance=FloatProperty(name='重合容差', default=0.00001, min=0.0000001,
        max=0.01, precision=6, description='世界坐标容差，单位为 Blender 单位'))


class MeshAxisBatchOperation:
    """Shared execution; each registered operator exposes only its own options."""
    do_alignment = False
    do_deduplication = False

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        success, skipped = [], []
        selected = list(context.selected_objects)
        mesh_count = sum(o.type == 'MESH' for o in selected)
        pairs = duplicate_plan(
            selected, context.view_layer.objects.active, self.duplicate_tolerance,
            self.match_appearance, skipped=skipped if not self.do_alignment else None
        ) if self.do_deduplication else []
        pending = {o.name for o,k in pairs}
        completed = set()
        for obj in sorted(selected, key=lambda o: o.name) if self.do_alignment else []:
            if obj.name in pending:
                continue
            if obj.type != 'MESH':
                continue
            try:
                info = align_object(obj, self.max_thickness_ratio, self.flip_x, self.flip_z, self.mode)
                obj.show_axis = self.show_axes
                success.append(obj.name + ('（立体）' if info['mode'] == 'SOLID' else '（薄板）'))
                completed.add(obj.name)
            except Exception as exc:
                skipped.append('%s：%s' % (obj.name, exc))
        deleted = []
        for obj, keeper in pairs:
            if self.do_alignment and keeper.name not in completed:
                skipped.append(obj.name + '：保留项定轴失败，未删除')
                continue
            deleted.append(obj.name + ' → 保留 ' + keeper.name)
            bpy.data.objects.remove(obj, do_unlink=True)
        if success:
            context.scene.transform_orientation_slots[0].type = 'LOCAL'
        if self.do_alignment and self.do_deduplication:
            summary = '定轴 %d 个，删除重复 %d 个，跳过 %d 个' % (len(success), len(deleted), len(skipped))
        elif self.do_alignment:
            summary = '定轴 %d 个，跳过 %d 个' % (len(success), len(skipped))
        else:
            checked = mesh_count - len(skipped)
            summary = '检查 %d 个，删除重复 %d 个，跳过 %d 个' % (checked, len(deleted), len(skipped))
        context.window_manager.mesh_axis_align_report = summary + '\n' + '\n'.join(success + deleted + skipped)
        self.report({'WARNING'} if skipped else {'INFO'}, summary + ('；' + skipped[0] if skipped else ''))
        if skipped:
            print('[Mesh Axis Align]\n' + '\n'.join(skipped))
        # Deletion alone is a successful, undoable change too.
        return {'FINISHED'} if success or deleted else {'CANCELLED'}


class OBJECT_OT_mesh_axis_align(MeshAxisBatchOperation, bpy.types.Operator):
    bl_idname = 'object.mesh_axis_align'
    bl_label = '仅修改轴向'
    bl_description = '只重设所选网格的局部轴，保持世界空间形状；不删除重合网格'
    bl_options = {'REGISTER', 'UNDO'}
    do_alignment = True
    __annotations__ = alignment_properties()


class OBJECT_OT_mesh_axis_deduplicate(MeshAxisBatchOperation, bpy.types.Operator):
    bl_idname = 'object.mesh_axis_deduplicate'
    bl_label = '仅去重'
    bl_description = '只删除所选重合网格，优先保留活动对象；不改变保留对象的轴向或网格'
    bl_options = {'REGISTER', 'UNDO'}
    do_deduplication = True
    __annotations__ = deduplicate_properties()


class OBJECT_OT_mesh_axis_align_and_deduplicate(MeshAxisBatchOperation, bpy.types.Operator):
    bl_idname = 'object.mesh_axis_align_and_deduplicate'
    bl_label = '修改轴向 + 去重（全部执行）'
    bl_description = '同时执行两项功能；保留对象定轴成功后才删除对应的重复网格'
    bl_options = {'REGISTER', 'UNDO'}
    do_alignment = True
    do_deduplication = True
    __annotations__ = {**alignment_properties(), **deduplicate_properties()}


class VIEW3D_PT_mesh_axis_align(bpy.types.Panel):
    bl_label = '网格边定轴'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '网格工具'

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        layout.label(text='选择网格 → 单独执行或全部执行')
        axes = layout.box()
        axes.label(text='修改轴向')
        axes.prop(wm, 'mesh_axis_align_mode', text='模式')
        op = axes.operator('object.mesh_axis_align', icon='ORIENTATION_LOCAL')
        op.mode = wm.mesh_axis_align_mode
        axes.label(text='薄板：最长轮廓边 + 主平面')
        axes.label(text='立体：X 最长，Y 次长，Z 最短')

        dedup = layout.box()
        dedup.label(text='去重（仅所选网格）')
        dedup.prop(wm, 'mesh_axis_match_appearance')
        dedup.prop(wm, 'mesh_axis_duplicate_tolerance')
        op = dedup.operator('object.mesh_axis_deduplicate', icon='DUPLICATE')
        op.match_appearance = wm.mesh_axis_match_appearance
        op.duplicate_tolerance = wm.mesh_axis_duplicate_tolerance

        layout.separator()
        op = layout.operator('object.mesh_axis_align_and_deduplicate', icon='CHECKMARK')
        op.mode = wm.mesh_axis_align_mode
        op.match_appearance = wm.mesh_axis_match_appearance
        op.duplicate_tolerance = wm.mesh_axis_duplicate_tolerance
        layout.label(text='三种操作均支持 Ctrl+Z 撤销')
        report = context.window_manager.mesh_axis_align_report
        if report:
            box = layout.box()
            for line in report.splitlines():
                box.label(text=line)


CLASSES = (OBJECT_OT_mesh_axis_align, OBJECT_OT_mesh_axis_deduplicate,
           OBJECT_OT_mesh_axis_align_and_deduplicate, VIEW3D_PT_mesh_axis_align)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.mesh_axis_align_report = bpy.props.StringProperty(
        name='操作结果', options={'SKIP_SAVE'})
    bpy.types.WindowManager.mesh_axis_align_mode = EnumProperty(name='模式', default='AUTO', items=[
        ('AUTO', '自动：薄板 / 立体', ''), ('PLANAR', '薄板', ''), ('SOLID', '立体', '')])
    bpy.types.WindowManager.mesh_axis_match_appearance = BoolProperty(name='要求材质和 UV 也一致', default=False)
    bpy.types.WindowManager.mesh_axis_duplicate_tolerance = deduplicate_properties()['duplicate_tolerance']


def unregister():
    if hasattr(bpy.types.WindowManager, 'mesh_axis_match_appearance'):
        del bpy.types.WindowManager.mesh_axis_match_appearance
    if hasattr(bpy.types.WindowManager, 'mesh_axis_duplicate_tolerance'):
        del bpy.types.WindowManager.mesh_axis_duplicate_tolerance
    if hasattr(bpy.types.WindowManager, 'mesh_axis_align_mode'):
        del bpy.types.WindowManager.mesh_axis_align_mode
    if hasattr(bpy.types.WindowManager, 'mesh_axis_align_report'):
        del bpy.types.WindowManager.mesh_axis_align_report
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
