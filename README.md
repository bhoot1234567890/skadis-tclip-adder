# IKEA Skadis T-Clip Mounting Tool

A Python tool to add T-clip mounting slots to 3D-printed tool holders for IKEA Skadis pegboards.

## Features

- **Graphical User Interface (GUI)** with scrollable controls
- Load STL, STEP, or OBJ mesh files
- Generate numbered Skadis grid overlay (20mm x 40mm, staggered)
- Multi-view visualization (isometric, front, top, side)
- Interactive slot selection by clicking on grid
- Boolean operations to cut mounting holes (28.284mm diameter)
- Optional T-clip geometry insertion (auto-repair for non-watertight meshes)
- Export as STL or STEP (STEP recommended for non-manifold geometry)
- Section analysis for cross-sectional views
- CLI mode also available (main.py)

## Installation

```bash
pip install -r requirements.txt
```

### Dependencies

- `trimesh[easy]` - 3D mesh processing
- `matplotlib` - Visualization (TkAgg backend)
- `manifold3d` - Boolean operations
- `numpy`, `scipy` - Numerical operations
- `pyvista` (optional) - Advanced visualization
- `tkinter` - GUI framework (standard with Python)

## Usage

### GUI Workflow (Recommended)

```bash
python gui_app.py
```

1. **Load Mesh** - Browse and select your tool holder file
2. **Select Face** - Click or use keyboard shortcuts (F/B/L/R/T/M)
3. **Configure Grid** - Adjust grid offset with sliders
4. **Select Slots** - Click on grid points to select slots (color feedback)
5. **Set Depth** - Choose cutting depth (default: 10mm)
6. **Process** - Cut holes and insert T-clips
7. **Export** - Save as STL or STEP

### CLI Workflow

```bash
python main.py
```

Follow the interactive prompts for mesh loading, grid setup, slot selection, and export.

## Configuration

Edit `config.py` to adjust:
- Skadis slot spacing (default: 20mm x 40mm, staggered)
- T-clip circle diameter (default: 28.284mm)
- Default cutting depth
- Visualization colors

## Skadis T-Clip System

The T-Clip uses a rotating mechanism:
- **Circle diameter**: 28.284mm (√2 × 20mm)
- Allows 45° rotation for insertion and locking
- No hardware required
- Parametric and fully 3D-printable

## Project Structure

```
t clip adder/
├── gui_app.py                 # GUI application (recommended)
├── main.py                    # CLI interface
├── config.py                  # Configuration constants
├── requirements.txt           # Python dependencies
├── core/
│   ├── mesh_loader.py        # STL/STEP loading
│   ├── grid_system.py        # Skadis grid generation
│   ├── boolean_ops.py        # Cutting and combining
│   └── section_analysis.py   # Cross-sections
├── visualization/
│   └── viewer.py             # PyVista multi-view
└── models/
    └── t_clip_slot.stl       # T-clip geometry (optional)
```

## Notes

- Meshes are auto-repaired for boolean operations, but watertight geometry is best
- Grid is centered on mesh face by default; use sliders for manual offset
- Multiple slots can be selected by clicking or with comma/range input (CLI)
- T-clip insertion is optional; holes can be cut without geometry insertion
- Export as STEP if STL merge fails (for non-manifold geometry)
- The left control panel is scrollable for accessibility

## License

MIT
