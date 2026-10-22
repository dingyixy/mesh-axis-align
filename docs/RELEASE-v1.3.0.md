# Mesh Axis Align v1.3.0

## English

A Blender add-on for organizing imported mesh axes and removing matching overlapping mesh objects, including post-import Ninja Ripper workflows.

This release separates the workflow into three actions:

- **Align only** — rebuild local axes while preserving world-space geometry.
- **Deduplicate only** — remove matching selected objects without changing the retained objects' axes.
- **Align + deduplicate** — run both in one undoable operation; delete duplicates only after their retained object aligns successfully.

Includes Auto/Planar/Solid axis modes, optional material/UV matching, active-object priority, per-object reports and Ctrl+Z undo.

**Download:** `mesh_axis_align_v1.3.0.zip` under Assets. Install using Blender → Edit → Preferences → Add-ons → Install from Disk, then enable the add-on. Do not use the automatically generated Source code archives as the installer.

**Tested:** Blender 4.5.3 LTS on Windows. Declared minimum: 4.2; other versions are unverified. The UI is primarily Chinese. Objects with custom normals, rigs, parenting or other unsupported data may be skipped. Material/UV matching is off by default, so geometry-identical objects with different appearances can be removed.

**API change:** `object.mesh_axis_align()` now only aligns. Use `object.mesh_axis_deduplicate()` for deduplication or `object.mesh_axis_align_and_deduplicate()` for both. The old `remove_duplicates` argument was removed.

## 简体中文

用于导入模型局部轴整理与重合网格去重的 Blender 插件，适合 Ninja Ripper 模型导入后的后处理流程。

本版将功能拆分为三个操作：

- **仅修改轴向**：保留世界空间外形，重新确定局部轴。
- **仅去重**：删除匹配的所选重合对象，不改变保留对象的轴向。
- **修改轴向 + 去重**：一次执行两项；保留项定轴成功后才删除重复项。

支持自动/薄板/立体模式、可选材质与 UV 匹配、活动对象优先保留、逐对象报告，以及 Ctrl+Z 撤销。

**下载与安装：**在 Assets 下载 `mesh_axis_align_v1.3.0.zip`，通过 Blender「编辑 → 偏好设置 → 插件 → 从磁盘安装」安装并启用。不要将自动生成的 Source code 压缩包用作安装包。

**已测试：**Windows / Blender 4.5.3 LTS；声明最低 Blender 4.2，其他版本未验证。当前主要为中文界面。自定义法向、骨骼绑定、父子关系等对象可能跳过。严格材质/UV 匹配默认关闭，几何一致但外观不同的对象也可能被删除。

**命令变化：**`object.mesh_axis_align()` 现在只定轴；单独去重使用 `object.mesh_axis_deduplicate()`；组合操作使用 `object.mesh_axis_align_and_deduplicate()`。旧参数 `remove_duplicates` 已移除。
