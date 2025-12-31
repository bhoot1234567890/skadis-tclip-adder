# Quick Start Guide

## Installation

```bash
cd "/Users/chaitanyamalhotra/Desktop/scratch projects/t clip adder"
pip install -r requirements.txt
```

## Running the Tool

### Option 1: Graphical User Interface (Recommended)

```bash
python gui_app.py
```

#### GUI Workflow
1. **Load Mesh**: Browse and select your STL/STEP/OBJ file
2. **Select Face**: Click or use keyboard shortcuts (F/B/L/R/T/M)
3. **Grid Offset**: Adjust X/Y/Z sliders for grid position
4. **Select Slots**: Click on grid points to select (color feedback)
5. **Cutting Depth**: Set depth (default: 10mm)
6. **Process**: Cut holes and insert T-clips
7. **Export**: Save as STL or STEP (choose format in dialog)

- The left control panel is scrollable for accessibility
- Meshes are auto-repaired for boolean operations, but watertight geometry is best
- If STL export fails, try STEP format for non-manifold geometry

### Option 2: CLI Mode

```bash
python main.py
```

Follow the interactive prompts:
1. Confirm to use `Clip Seat.step` (or provide another path)
2. Choose grid centering (default: yes)
3. View the mesh with numbered slot overlay
4. Select slots by number (e.g., `5,12,18` or `5-8`)
5. Enter cutting depth (default: 10mm)
6. Preview the result
7. Save the modified STL

### Option 3: Quick Demo

```bash
python demo.py
```

Runs an automated demo that:
- Loads the Clip Seat STEP file
- Creates a Skadis grid overlay
- Automatically selects 3 middle slots
- Cuts 10mm deep mounting holes
- Exports result as `Clip_Seat_with_tclip_demo.stl`

## Understanding the Visualization

When you run the tool, you'll see **4 views**:

```
┌─────────────────┬─────────────────┐
│ Isometric (2.5D)│   Front View    │
│                 │                 │
│                 │                 │
├─────────────────┼─────────────────┤
│   Top View      │  Detail + Labels│
│                 │                 │
│                 │  (with slot #s) │
└─────────────────┴─────────────────┘
```

- **Red dots** = Skadis slot positions
- **Numbers (S1, S2, etc.)** = Slot indices for selection
- **Spacing** = 40mm × 40mm (standard Skadis)

## Slot Selection Examples

```
Single slot:        12
Multiple slots:     5,12,18
Range:             5-8
Mixed:             5,12-15,20
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Circle diameter | 28.284mm | √2 × 20mm for T-clip rotation |
| Cutting depth | 10mm | User configurable per slot |
| Slot spacing | 40mm | IKEA Skadis standard |
| Grid center | Mesh centroid | Can add manual offset |

## File Formats Supported

- **Input**: STL, STEP, OBJ, PLY (via trimesh)
- **Output**: STL (binary)

## Tips

1. **Mesh not watertight?** The tool will attempt automatic fixes
2. **No boolean operations available?** Install OpenSCAD for best results:
   ```bash
   brew install openscad  # macOS
   ```
3. **Need T-clip geometry?** Place `t_clip_slot.stl` in `models/` directory
4. **Multiple depths?** Answer 'n' when asked "Use same depth for all slots?"

## Example Workflow

```bash
$ python main.py

# Step 1: Load mesh
Found: Clip Seat.step
Use this file? [y]: y

# Step 2: Grid setup
Center grid on mesh? [y]: y
Apply manual offset? [n]: n

# Step 3: Visualize (window opens - close it to continue)

# Step 4: Select slots
Slot number(s): 5,12
Selected 2 slots

# Step 5: Depth
Use same depth for all slots? [y]: y
Enter depth in mm [10.0]: 12

# Step 6: Processing...
✓ Processing complete!

# Step 7: Preview (window opens)

# Step 8: Export
Output filename [Clip_Seat_with_tclip.stl]: 
✓ Successfully exported
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "STEP file not loading" | Install `gmsh`: `pip install gmsh` |
| "Boolean operations failing" | Install OpenSCAD or try smaller depths |
| "Visualization not working" | Using matplotlib fallback (works but less interactive) |
| "Slots not aligned with part" | Use manual offset: X, Y, Z in mm |
| "STL export fails" | Try exporting as STEP instead |

## Advanced: Python API

```python
from core.mesh_loader import load_mesh
from core.grid_system import SkadisGrid
from core.boolean_ops import process_multiple_slots

# Load mesh
mesh = load_mesh("your_part.stl")

# Create grid
grid = SkadisGrid(mesh, offset=(0, 0, 0), use_mesh_center=True)

# Select slots
slot_positions = [grid.get_slot_position(i) for i in [5, 12, 18]]

# Process
result = process_multiple_slots(mesh, slot_positions, depths=10.0)

# Export
result.export("output.stl")
```

## Need Help?

Check [README.md](README.md) for full documentation.
