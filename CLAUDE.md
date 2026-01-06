# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool for adding T-clip mounting slots to 3D-printed tool holders designed for IKEA Skadis pegboards. The tool generates a staggered grid overlay matching the Skadis pegboard pattern (20mm × 40mm spacing), allows users to select mounting points, cuts holes, and optionally inserts T-clip geometry for parametric mounting.

## Common Commands

### Running the Application

```bash
# GUI (recommended) - Tkinter with matplotlib 3D visualization
python gui_app.py

# CLI interface - Interactive text-based workflow
python main.py

# Quick demo - Automated processing with preset values
python demo.py
```

### Installation

```bash
# Core dependencies (trimesh, numpy, matplotlib, scipy)
pip install -r requirements.txt

# Optional but highly recommended for boolean operations
pip install manifold3d

# Optional for advanced visualization
pip install pyvista
```

### Testing

```bash
# Test mesh loading and basic operations
python test_load.py
```

## Architecture

### Entry Points

- **gui_app.py** - Tkinter-based GUI with matplotlib 3D visualization. Main workflow: load mesh → select face (color-coded bbox) → adjust grid offset → click grid points to select slots → cut holes → insert T-clips → export STL/STEP. Features scrollable left control panel for accessibility.
- **main.py** - Interactive CLI with same workflow but text-based prompts. Supports range input for slot selection (e.g., "5-8" for slots 5,6,7,8).
- **demo.py** - Automated demo that loads Clip Seat.step, selects 3 middle slots, processes, and exports.

### Core Modules

**core/grid_system.py (SkadisGrid class)**
- Generates staggered grid matching IKEA Skadis pattern (20mm H × 40mm V, every other column offset by 20mm)
- Grid origin placement: centered on mesh face in plane dimensions, at boundary in depth dimension
- Supports 3 grid planes: 'xy' (top/bottom faces), 'xz' (front/back), 'yz' (left/right)
- Key parameters:
  - `grid_plane`: Which plane the grid lies on ('xy', 'xz', 'yz')
  - `boundary_type`: Which mesh face the grid attaches to ('max_z', 'min_x', etc.)
  - `offset`: Manual (x, y, z) offset in mm
  - `use_mesh_center`: Whether to center grid on mesh centroid in plane dimensions
- Methods: `get_slot(index)`, `get_slot_position(index)`, `get_slots_in_range(indices)`

**core/boolean_ops.py**
- `create_cutting_cylinder(position, depth, diameter, grid_plane, cut_normal)` - Creates cutting cylinder. When `cut_normal` provided, cylinder Z-axis rotates to align with it, base placed at position extending INTO mesh.
- `cut_hole(mesh, position, depth, ...)` - Boolean difference using fallback chain: manifold3d → scad → blender → concatenation (no-op)
- `insert_tclip(mesh, tclip_mesh, position, ...)` - Orients and places T-clip. Critical: T-clip Y-axis (thin dimension) aligns opposite to `cut_normal`, making base point OUT of mesh. T-clip positioned with MIN bound (base edge) exactly at face position.
- `process_multiple_slots(mesh, slot_positions, depths, tclip_mesh, ...)` - TWO-PHASE PROCESS: cuts ALL holes FIRST, then inserts ALL T-clips. This order is critical for boolean operation stability.

**core/mesh_loader.py**
- `load_mesh(file_path)` - Loads STL/STEP/OBJ via trimesh. Auto-converts scenes to single mesh using `to_geometry()` or `dump(concatenate=True)`.
- Repair pipeline for non-watertight meshes: `fill_holes()`, `remove_duplicate_faces()`, `remove_degenerate_faces()`, `merge_vertices()`, `fix_normals()`
- `get_mesh_info(mesh)` and `print_mesh_info(mesh)` for debugging

**core/section_analysis.py**
- Cross-section generation: `create_section(mesh, plane_origin, plane_normal)` for arbitrary plane cuts
- Convenience functions: `create_xy_section()`, `create_xz_section()`, `create_yz_section()`
- Returns 2D planar projection via `section.to_planar()`

**visualization/viewer.py (PyVista)** and **visualization/viewer_mpl.py (matplotlib)**
- Multi-view rendering: isometric, front, top, side
- PyVista preferred for interactivity, matplotlib as fallback
- GUI uses matplotlib viewer embedded in Tkinter with clickable grid points using projection to 2D screen space

### Configuration (config.py)

Key constants:
- `SKADIS_SLOT_SPACING_H = 20.0` mm (horizontal center-to-center)
- `SKADIS_SLOT_SPACING_V = 40.0` mm (vertical center-to-center)
- `SKADIS_STAGGER_OFFSET = 20.0` mm (every other column shifted down)
- `T_CLIP_CIRCLE_DIAMETER = 28.284` mm (√2 × 20, allows 45° rotation for insertion)
- `T_CLIP_DEFAULT_DEPTH = 10.0` mm
- `BBOX_COLORS` - Color-coded face selection for GUI (red=front, blue=back, green=left, yellow=right, cyan=top, magenta=bottom)

## Critical Implementation Details

### Grid Orientation and Cutting Direction

The system determines cutting direction in two ways:
1. **cut_normal parameter** (preferred in GUI): Explicit 3D vector pointing INTO the mesh. Used for precise face-based orientation
2. **grid_plane fallback** (CLI/legacy): Infers direction from plane orientation (xy→cut along -Z, xz→cut along -Y, yz→cut along -X)

**When `cut_normal` is provided:**
- `create_cutting_cylinder()`: Cylinder Z-axis rotates to align with cut_normal, base placed at position extending INTO mesh
- `insert_tclip()`: T-clip Y-axis (thin dimension) rotates to align with NEGATIVE cut_normal. This makes the T-clip base (mounting face) point OUT of the mesh. T-clip positioned with its MIN bound (base edge) exactly at face position for flush mount.

### T-Clip Geometry

T-clip file search order: `Clip Seat.step`, `models/t_clip_slot.stl`, `t_clip_slot.stl`

Auto-scaling: If max dimension < 1.0mm, assumes model is in meters and scales by 1000×, then re-centers to origin.

Repair pipeline (applied if not watertight before boolean operations):
1. `fill_holes()`
2. `remove_duplicate_faces()`
3. `remove_degenerate_faces()`
4. `merge_vertices()`
5. `fix_normals()`

### Boolean Operation Fallback Chain

For both hole cutting and T-clip insertion, engines tried in order:
1. **manifold** (if manifold3d installed) - Most reliable, recommended
2. **scad** - OpenSCAD backend (requires OpenSCAD installed)
3. **blender** - Blender backend (requires Blender installed)
4. **concatenation** (union only) - Simple mesh merge, no actual boolean operation

If all engines fail:
- For holes: Returns original mesh unchanged
- For T-clips: Returns concatenated meshes (not actually merged)

### GUI Face Selection and Mapping

The GUI uses color-coded bounding box faces for selection:

| Face | Color | plane   | boundary | cut_normal      |
|------|-------|---------|----------|-----------------|
| Front (+Y) | Red    | xz      | max_y    | [0, -1, 0]      |
| Back (-Y)  | Blue   | xz      | min_y    | [0, 1, 0]       |
| Left (-X)  | Green  | yz      | min_x    | [1, 0, 0]       |
| Right (+X) | Yellow | yz      | max_x    | [-1, 0, 0]      |
| Top (+Z)   | Cyan   | xy      | max_z    | [0, 0, -1]      |
| Bottom (-Z)| Magenta| xy      | min_z    | [0, 0, 1]       |

**Important:** `cut_normal` points INTO the mesh (opposite to face normal direction). This is critical for proper T-clip orientation.

GUI workflow:
1. Load mesh → displays with colored bounding box faces
2. User clicks face OR uses keyboard shortcut (F/B/L/R/T/M)
3. GUI stores `grid_plane` and `cut_normal` from selected face
4. Grid generated centered on that face
5. User adjusts X/Y/Z offset sliders to fine-tune position
6. User clicks grid points in 3D view to select slots (with adaptive threshold for screen projection)

### Two-Phase Processing Order

The `process_multiple_slots()` function enforces a specific order for stability:
1. **Phase 1**: Cut ALL holes first (accumulative boolean differences)
2. **Phase 2**: Insert ALL T-clips (accumulative boolean unions)

This order prevents geometry conflicts that can occur when interleaving cuts and inserts.

## File Structure Conventions

```
t clip adder/
├── gui_app.py                 # GUI application (Tkinter + matplotlib)
├── main.py                    # CLI interface
├── demo.py                    # Automated demo
├── config.py                  # Configuration constants
├── requirements.txt           # Core dependencies
├── core/
│   ├── mesh_loader.py        # Mesh loading and repair
│   ├── grid_system.py        # SkadisGrid class
│   ├── boolean_ops.py        # Cutting and insertion
│   └── section_analysis.py   # Cross-section generation
├── visualization/
│   ├── viewer.py             # PyVista viewer
│   └── viewer_mpl.py         # Matplotlib viewer
└── models/                    # Optional T-clip geometry directory
```

- Input files: Any STL/STEP/OBJ in working directory (CLI auto-detects, excluding T-clip geometry)
- T-clip geometry: Excluded from auto-detection (filtered by 'clip seat' in filename)
- Output files: Default suffix `_with_tclip.stl` or `.step` (user choice)

## Dependencies

**Core requirements (requirements.txt):**
- `trimesh[easy]` - Mesh I/O and boolean operations
- `numpy` - Numerical operations
- `matplotlib` - Visualization (TkAgg backend required for GUI)
- `scipy` - Scientific computing

**Optional but recommended:**
- `manifold3d` - High-performance boolean engine (highly recommended for reliability)
- `pyvista` - Advanced 3D visualization

**External software (optional fallbacks):**
- OpenSCAD - For scad boolean engine
- Blender - For blender boolean engine

## Important Recent Fixes

Based on git history, several critical orientation bugs were fixed:
- `45ba849` - T-clip Y-axis now oriented opposite to cut_normal (prevents flipped clips)
- `513b9dc` - T shape now faces correct direction
- `1a4df88` - T-clip points INTO mesh instead of OUT
- `8e5665d` - T-clips sit exactly at mesh surface (flush mount)

When modifying T-clip orientation code, verify the `cut_normal` handling to prevent regressions.

## Development Notes

- CLI supports range input for slot selection (e.g., "5-8" for slots 5,6,7,8, or "5,12-15,20" for mixed)
- GUI uses matplotlib's TkAgg backend - do not change backend
- Grid generated with minimal padding (1 slot spacing beyond mesh bounds)
- Export as STEP if STL merge fails (for non-manifold geometry)
- The left control panel in GUI is scrollable for accessibility
- T-clip insertion is optional; holes can be cut without geometry insertion
