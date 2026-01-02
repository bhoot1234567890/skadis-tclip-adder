# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool for adding T-clip mounting slots to 3D-printed tool holders designed for IKEA Skadis pegboards. The tool generates a staggered grid overlay matching the Skadis pegboard pattern (20mm × 40mm spacing), allows users to select mounting points, cuts holes, and optionally inserts T-clip geometry for parametric mounting.

## Common Commands

### Running the Application

```bash
# GUI (recommended)
python gui_app.py

# CLI interface
python main.py
```

### Installation

```bash
pip install -r requirements.txt
```

### Testing Mesh Loading

```bash
python test_load.py
```

## Architecture

### Entry Points

- **gui_app.py** - Tkinter-based GUI with matplotlib 3D visualization. Main workflow: load mesh → select face (color-coded bbox) → adjust grid offset → click grid points to select slots → cut holes → insert T-clips → export STL/STEP
- **main.py** - Interactive CLI with same workflow but text-based prompts

### Core Modules

**core/grid_system.py (SkadisGrid)**
- Generates staggered grid matching IKEA Skadis pattern (20mm H × 40mm V, every other column offset by 20mm)
- Grid origin is centered on mesh face in plane dimensions, at boundary in depth dimension
- Supports 3 grid planes: 'xy' (top/bottom faces), 'xz' (front/back), 'yz' (left/right)
- Key concept: `boundary_type` ('max_z', 'min_x', etc.) determines which mesh face the grid attaches to

**core/boolean_ops.py**
- `create_cutting_cylinder()` - Creates cylinder for cutting holes, oriented by `cut_normal` vector or `grid_plane`
- `cut_hole()` - Boolean difference operation using multiple engines (manifold3d → scad → blender, with fallback)
- `insert_tclip()` - Orients and places T-clip geometry. Critical: T-clip is centered at origin, thin dimension (Y-axis) must point perpendicular to grid plane, base sits flush at face
- `process_multiple_slots()` - Cuts all holes FIRST, then inserts all T-clips (important for boolean stability)
- Key insight: `cut_normal` parameter (np.array) overrides `grid_plane` for orientation. When provided, cylinders and T-clips align to this vector pointing INTO the mesh

**core/mesh_loader.py**
- Loads STL/STEP/OBJ via trimesh
- Auto-converts scenes to single mesh
- Attempts repair for non-watertight meshes (fill_holes, remove_duplicate_faces, merge_vertices)

**visualization/viewer.py (PyVista)** and **visualization/viewer_mpl.py (matplotlib)**
- Multi-view rendering: isometric, front, top, side
- PyVista preferred, matplotlib fallback
- GUI uses matplotlib viewer embedded in Tkinter

### Configuration (config.py)

Key constants:
- `SKADIS_SLOT_SPACING_H = 20.0` mm (horizontal)
- `SKADIS_SLOT_SPACING_V = 40.0` mm (vertical)
- `SKADIS_STAGGER_OFFSET = 20.0` mm (every other column shifted down)
- `T_CLIP_CIRCLE_DIAMETER = 28.284` mm (√2 × 20, allows 45° rotation for insertion)
- `T_CLIP_DEFAULT_DEPTH = 10.0` mm
- `BBOX_COLORS` - Color-coded face selection for GUI (red=front, blue=back, etc.)

## Critical Implementation Details

### Grid Orientation and Cutting Direction

The system determines cutting direction in two ways:
1. **cut_normal parameter** (preferred): Explicit 3D vector pointing INTO the mesh. Used in GUI for precise face-based orientation
2. **grid_plane fallback**: Infers direction from plane orientation (xy→cut along -Z, xz→cut along -Y, yz→cut along -X)

When `cut_normal` is provided to `create_cutting_cylinder()`:
- Cylinder Z-axis is rotated to align with cut_normal
- Cylinder base is placed at position, extends INTO mesh along cut_normal

When `cut_normal` is provided to `insert_tclip()`:
- T-clip Y-axis (thin dimension) is rotated to align with NEGATIVE cut_normal
- This makes the T-clip base (mounting face) point OUT of the mesh (opposite to cut direction)
- T-clip is positioned with its MIN bound (base edge) exactly at the face position (flush mount)

### T-Clip Geometry Handling

T-clip files searched in order: `Clip Seat.step`, `models/t_clip_slot.stl`, `t_clip_slot.stl`

Auto-scaling: If max dimension < 1.0mm, assumes model is in meters and scales by 1000×, then re-centers to origin.

Repair pipeline (applied if not watertight):
1. `fill_holes()`
2. `remove_duplicate_faces()`
3. `remove_degenerate_faces()`
4. `merge_vertices()`
5. `fix_normals()`

### Boolean Operation Fallback Chain

For both hole cutting and T-clip insertion, engines tried in order:
1. **manifold** (if manifold3d installed) - most reliable
2. **scad** - OpenSCAD backend
3. **blender** - Blender backend
4. **concatenation** (union only) - simple mesh merge, no boolean

If all engines fail, returns original mesh (for holes) or concatenated meshes (for T-clips).

### GUI Face Selection Workflow

1. Load mesh → show with colored bounding box faces
2. User clicks face OR uses keyboard shortcut (F/B/L/R/T/M)
3. GUI stores `grid_plane` and `cut_normal` from selected face
4. Grid generated centered on that face
5. User adjusts offset sliders to fine-tune position

Face mapping (from gui_app.py):
- Front (+Y, red): plane='xz', boundary='max_y', cut_normal=[0,-1,0]
- Back (-Y, blue): plane='xz', boundary='min_y', cut_normal=[0,1,0]
- Left (-X, green): plane='yz', boundary='min_x', cut_normal=[1,0,0]
- Right (+X, yellow): plane='yz', boundary='max_x', cut_normal=[-1,0,0]
- Top (+Z, cyan): plane='xy', boundary='max_z', cut_normal=[0,0,-1]
- Bottom (-Z, magenta): plane='xy', boundary='min_z', cut_normal=[0,0,1]

Note that `cut_normal` points INTO the mesh (opposite to face normal direction).

## File Structure Conventions

- `models/` - Optional directory for T-clip geometry
- Input files: Any STL/STEP/OBJ in working directory (auto-detected by CLI)
- T-clip geometry: Excluded from auto-detection (filtered by 'clip seat' in filename)
- Output: Default suffix `_with_tclip.stl` (or `.step`)

## Dependencies

Core:
- `trimesh[easy]` - Mesh I/O and boolean operations
- `numpy` - Numerical operations
- `matplotlib` - Visualization (TkAgg backend required for GUI)

Optional but recommended:
- `manifold3d` - High-performance boolean engine
- `pyvista` - Advanced 3D visualization

## Workflow Notes

- CLI auto-detects mesh files in current directory, excluding T-clip geometry
- CLI supports range input for slot selection (e.g., "5-8" for slots 5,6,7,8)
- GUI allows clicking grid points in 3D view using projection to 2D screen space with adaptive threshold
- Export format choice: STL (standard) vs STEP (better for non-manifold geometry)
- Grid is generated with minimal padding (1 slot spacing beyond mesh bounds)
