# Mesh Axis Align

[English](README.md) | [简体中文](README.zh-CN.md)

**Batch local-axis alignment and overlapping mesh deduplication for Blender.**

Mesh Axis Align helps prepare imported game meshes for editing, including models imported into Blender after a Ninja Ripper capture. It derives useful local axes from each mesh's overall shape and removes matching overlapping mesh objects within a selection. Alignment preserves the mesh's world-space shape and position, so you can work with more useful local transform directions without repositioning the model.

This is a post-import Blender tool. It does not capture games, import Ninja Ripper files, or recover original authoring axes, rigs, UVs, or materials. It is an independent project, not an official Ninja Ripper product.

## Features

- **Align only:** rebuild local axes without deleting objects.
- **Deduplicate only:** remove matching selected objects without changing the retained objects' axes or mesh data.
- **Align + deduplicate:** run both operations together. Duplicates are deleted only after the retained object aligns successfully.
- **Planar mode:** use the longest edge of the projected convex outline for X, an orthogonal in-plane direction for Y, and the plane normal for Z.
- **Solid mode:** use an approximate minimum-volume oriented bounding box of the convex hull; assign its longest, middle and shortest directions to X, Y and Z.
- **Auto mode:** choose between planar and solid methods using a thickness threshold.
- Preserve world-space geometry, origin position, topology, UVs and material assignments during alignment; use private mesh copies to protect unselected objects sharing mesh data.
- Prioritize the active object when choosing which duplicate to keep. Otherwise use object-name order.
- Optional material and UV matching, configurable coordinate tolerance, per-object reports and Ctrl+Z undo.
- Hide object XYZ labels by default after alignment; standard transform gizmos remain available.

## Compatibility

| Item | Status |
| --- | --- |
| Version | 1.3.0 |
| Tested environment | Blender 4.5.3 LTS on Windows |
| Declared minimum Blender version | 4.2; other versions have not been verified |
| Interface | Primarily Chinese; button translations are provided below |
| Packaging | Legacy Python add-on; not a Blender Extensions package |
| Dependencies | Blender's bundled Python and NumPy; no separate pip installation |

## Installation

1. Download **`mesh_axis_align_v1.3.0.zip`** from this repository's **Releases → Assets**.
2. In Blender, open **Edit → Preferences → Add-ons**.
3. Open the menu and choose **Install from Disk**, then select the ZIP without extracting it.
4. Enable **网格边定轴 / Mesh Axis Align**.
5. In the 3D Viewport, press **N** and open **网格工具 → 网格边定轴**.

Use the named add-on ZIP, not GitHub's automatically generated **Source code (zip)** archive. If upgrading leaves the old panel visible, restart Blender after installation.

## Quick start

Import your meshes using your normal importer first. Work in **Object Mode**, select the meshes to process, and choose an operation:

| UI label | Meaning |
| --- | --- |
| 仅修改轴向 | Align axes only |
| 仅去重 | Deduplicate only |
| 修改轴向 + 去重（全部执行） | Align axes and deduplicate |
| 要求材质和 UV 也一致 | Require matching materials and UVs |
| 重合容差 | Duplicate coordinate tolerance |

Start with **Auto**. Successful alignment changes the transform orientation to **Local**, making the new axes useful for scaling and rotation. Use **F9** to adjust the last operation's options or **Ctrl+Z** to undo. Each combined operation is undone in one step.

If a specific overlapping object has the appearance you want to keep, make it the active object before deduplicating. For imported models with layered surfaces, consider enabling material/UV matching first.

## How duplicate matching works

Only selected objects participate. Matching checks quantized world-space vertex positions, edge and face structure, face winding, smoothing flags, supported modifier settings and visibility. Equal bounding boxes alone are not sufficient.

- Default coordinate tolerance: **0.00001 Blender units**. Quantization can miss near-matches on cell boundaries; this is not a nearest-point distance matcher.
- Material/UV matching is **off by default**. Objects with matching geometry but different materials or UVs can therefore be deleted.
- Strict matching compares assigned material datablock identity, UV values and additional mesh attributes. It does not prove that two separately created materials render identically.
- It does not weld vertices, merge different objects into one mesh, or collapse differently triangulated but visually similar surfaces.
- Object deletion does not purge orphaned mesh datablocks.

## Limits and skipped objects

The add-on deliberately skips objects with parent/child relationships, constraints, animation or drivers, shape keys, custom split normals, linked/library-override data, non-positive or near-zero transform determinants, insufficient geometry, or unsupported modifiers. The same eligibility checks currently apply to deduplication-only operations.

Only a restricted set of automatic smoothing Geometry Nodes graphs is accepted. A modifier named “Auto Smooth” is not automatically supported. Alignment validates world-space vertex positions and, for accepted modifiers, evaluated geometry and corner normals. If validation fails, that object's alignment is rolled back; supported modifier normals use a maximum deviation threshold of 0.1°.

Other practical limits:

- Rigged character meshes are generally skipped; this is not a rig-preserving reorientation tool.
- The oriented-box search is approximate, not a guaranteed global optimum. Symmetric shapes have no unique longest axis.
- The inferred axes describe shape, not the original game's intended axes or pivot placement. Alignment preserves the origin position and normalizes object scale rather than recovering original transforms.
- Local/Object/Generated-coordinate procedural materials may change appearance even though UVs and material nodes are preserved.
- Very dense meshes can take time to process. The add-on does not automatically save or back up `.blend` files.

## Python commands

With the add-on enabled:

```python
import bpy

bpy.ops.object.mesh_axis_align(mode='AUTO')
bpy.ops.object.mesh_axis_deduplicate(match_appearance=True)
bpy.ops.object.mesh_axis_align_and_deduplicate(
    mode='AUTO', match_appearance=True, duplicate_tolerance=0.00001)
```

These are three alternative operations; run the one you need. In 1.3.0, `mesh_axis_align()` only aligns. The old `remove_duplicates` argument has been removed.

## Tests and bug reports

Regression scripts are in `tests/`. Run each in its own factory-startup background Blender process, not in your working scene:

```text
blender --background --factory-startup --python-exit-code 1 --python tests/test_mesh_axis_align.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_mesh_axis_align_v12.py
blender --background --factory-startup --python-exit-code 1 --python tests/test_mesh_axis_align_v13.py
```

For an issue, include the Blender/add-on versions, operation and settings, full skip/error report, and a minimal reproducible mesh when possible. Synthetic examples are useful; the repository does not need captured game assets to reproduce most geometry problems.
