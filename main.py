#!/usr/bin/env python3
"""
IKEA Skadis T-Clip Mounting Tool
Adds T-clip mounting slots to 3D-printed tool holders
"""

import sys
from pathlib import Path
import numpy as np

# Import core modules
from core.mesh_loader import load_mesh, print_mesh_info
from core.grid_system import SkadisGrid
from core.boolean_ops import process_multiple_slots
from core.section_analysis import get_section_by_axis
from config import T_CLIP_DEFAULT_DEPTH

# Try PyVista first, fall back to matplotlib
try:
    from visualization.viewer import MeshViewer
    VIEWER_ENGINE = "pyvista"
except (ImportError, OSError):
    from visualization.viewer_mpl import MeshViewer
    VIEWER_ENGINE = "matplotlib"
    print(f"Note: Using matplotlib for visualization (PyVista unavailable)")



def print_header():
    """Print application header."""
    print("\n" + "=" * 60)
    print("  IKEA Skadis T-Clip Mounting Tool")
    print("  Add T-clip slots to your 3D-printed tool holders")
    print("=" * 60 + "\n")


def get_user_input(prompt, input_type=str, default=None):
    """Get user input with type conversion and default value."""
    if default is not None:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    while True:
        try:
            user_input = input(prompt).strip()
            
            if not user_input and default is not None:
                return default
            
            if input_type == bool:
                return user_input.lower() in ['y', 'yes', 'true', '1']
            
            # Strip quotes from string inputs (file paths)
            if input_type == str:
                user_input = user_input.strip('"').strip("'")
            
            return input_type(user_input)
        
        except ValueError:
            print(f"Invalid input. Please enter a valid {input_type.__name__}.")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            sys.exit(0)


def get_slot_selection(grid):
    """Get slot selection from user."""
    print("\n--- Slot Selection ---")
    print("Enter slot numbers separated by commas (e.g., 5,12,18)")
    print("Or enter a range (e.g., 5-8)")
    print(f"Available slots: 1-{len(grid.slots)}")
    
    while True:
        try:
            selection = input("Slot number(s): ").strip()
            
            # Parse selection
            indices = []
            
            # Handle comma-separated values
            if ',' in selection:
                parts = selection.split(',')
                for part in parts:
                    part = part.strip()
                    if '-' in part:
                        # Range
                        start, end = map(int, part.split('-'))
                        indices.extend(range(start, end + 1))
                    else:
                        indices.append(int(part))
            elif '-' in selection:
                # Range
                start, end = map(int, selection.split('-'))
                indices = list(range(start, end + 1))
            else:
                # Single value
                indices = [int(selection)]
            
            # Validate indices
            valid_indices = [i for i in indices if 1 <= i <= len(grid.slots)]
            
            if not valid_indices:
                print(f"No valid slots selected. Please select from 1-{len(grid.slots)}")
                continue
            
            if len(valid_indices) != len(indices):
                invalid = set(indices) - set(valid_indices)
                print(f"Warning: Invalid slot numbers ignored: {invalid}")
            
            return valid_indices
        
        except ValueError:
            print("Invalid format. Use numbers separated by commas or ranges (e.g., 5,12,18 or 5-8)")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            sys.exit(0)


def get_depths(num_slots):
    """Get cutting depths for slots."""
    print("\n--- Cutting Depth ---")
    print(f"Default depth: {T_CLIP_DEFAULT_DEPTH}mm")
    
    use_same = get_user_input(
        "Use same depth for all slots? (y/n)",
        bool,
        default=True
    )
    
    if use_same:
        depth = get_user_input(
            "Enter depth in mm",
            float,
            default=T_CLIP_DEFAULT_DEPTH
        )
        return [depth] * num_slots
    else:
        depths = []
        for i in range(num_slots):
            depth = get_user_input(
                f"Depth for slot {i+1} in mm",
                float,
                default=T_CLIP_DEFAULT_DEPTH
            )
            depths.append(depth)
        return depths


def main():
    """Main application workflow."""
    print_header()
    
    # Step 1: Load mesh
    print("Step 1: Load Tool Holder Mesh")
    print("-" * 40)
    
    # Auto-detect mesh files in current directory (exclude T-clip geometry)
    current_dir = Path.cwd()
    mesh_files = []
    
    # Look for STL, STEP, and OBJ files
    for ext in ['*.stl', '*.step', '*.stp', '*.obj']:
        mesh_files.extend(current_dir.glob(ext))
    
    # Filter out T-clip geometry files (exclude "Clip Seat" which is the T-clip)
    mesh_files = [f for f in mesh_files if 'clip seat' not in f.name.lower()]
    
    if mesh_files:
        # Default to first found mesh file
        default_path = str(mesh_files[0])
        print(f"Found: {mesh_files[0].name}")
        if len(mesh_files) > 1:
            print(f"  (and {len(mesh_files)-1} other mesh file(s))")
        
        use_default = get_user_input("Use this file? (y/n)", bool, default=True)
        if use_default:
            mesh_path = default_path
        else:
            mesh_path = get_user_input("Enter path to mesh file (STL/STEP/OBJ)")
    else:
        mesh_path = get_user_input("Enter path to mesh file (STL/STEP/OBJ)")
    
    try:
        mesh = load_mesh(mesh_path)
        print_mesh_info(mesh)
    except Exception as e:
        print(f"Error loading mesh: {e}")
        sys.exit(1)
    
    # Step 2: Select grid plane
    print("\nStep 2: Select Grid Plane")
    print("-" * 40)
    print("First, view the mesh with colored bounding box faces...")
    print("Close the window to continue.")
    
    # Show mesh with colored bounding box for face selection
    bbox_viewer = MeshViewer(mesh, grid=None, show_bbox=True)
    bbox_viewer.show_multiview(show_grid=False)
    
    print("\nFace color reference:")
    print("  RED    = Front (+Y)")
    print("  BLUE   = Back (-Y)")
    print("  GREEN  = Left (-X)")
    print("  YELLOW = Right (+X)")
    print("  CYAN   = Top (+Z)")
    print("  MAGENTA = Bottom (-Z)")
    
    print("\nWhich face should the Skadis grid be drawn on?")
    # Map face selection to (plane, boundary_type)
    # boundary_type: 'max' means use max bound coordinate, 'min' means use min bound coordinate
    face_options = {
        'red': ('xz', 'max_y', 'Front (+Y)'), 'front': ('xz', 'max_y', 'Front (+Y)'),
        'blue': ('xz', 'min_y', 'Back (-Y)'), 'back': ('xz', 'min_y', 'Back (-Y)'),
        'green': ('yz', 'min_x', 'Left (-X)'), 'left': ('yz', 'min_x', 'Left (-X)'),
        'yellow': ('yz', 'max_x', 'Right (+X)'), 'right': ('yz', 'max_x', 'Right (+X)'),
        'cyan': ('xy', 'max_z', 'Top (+Z)'), 'top': ('xy', 'max_z', 'Top (+Z)'),
        'magenta': ('xy', 'min_z', 'Bottom (-Z)'), 'bottom': ('xy', 'min_z', 'Bottom (-Z)')
    }
    
    while True:
        face_choice = get_user_input(
            "Enter face color or name (e.g., 'red', 'front', 'cyan', 'top')",
            str
        ).lower()
        
        if face_choice in face_options:
            grid_plane, boundary_type, face_name = face_options[face_choice]
            break
        else:
            print(f"Invalid choice. Please enter one of: {', '.join(set(face_options.keys()))}")
    
    print(f"Selected face: {face_name}")
    print(f"Grid plane: {grid_plane.upper()}")
    
    # Step 3: Configure grid
    print("\nStep 3: Configure Skadis Grid")
    print("-" * 40)
    
    use_center = get_user_input(
        "Center grid on mesh? (y/n)",
        bool,
        default=True
    )
    
    offset = [0, 0, 0]
    if get_user_input("Apply manual offset? (y/n)", bool, default=False):
        offset[0] = get_user_input("X offset (mm)", float, default=0)
        offset[1] = get_user_input("Y offset (mm)", float, default=0)
        offset[2] = get_user_input("Z offset (mm)", float, default=0)
    
    grid = SkadisGrid(mesh, offset=offset, use_mesh_center=use_center, grid_plane=grid_plane, boundary_type=boundary_type)
    
    # Debug: Show mesh bounds for reference
    print(f"\nDEBUG - Mesh bounds:")
    print(f"  Min: {mesh.bounds[0]}")
    print(f"  Max: {mesh.bounds[1]}")
    print(f"  Centroid: {mesh.centroid}")
    
    grid.print_grid_info()
    
    # Step 4: Visualize mesh with grid
    print("\nStep 4: Visualize Mesh with Grid")
    print("-" * 40)
    print("Opening 3D viewer with staggered grid overlay...")
    print("Close the window to continue.")
    
    viewer = MeshViewer(mesh, grid)
    viewer.show_multiview(show_grid=True)
    
    # Step 5: Section analysis (optional)
    print("\nStep 5: Section Analysis (Optional)")
    print("-" * 40)
    
    if get_user_input("View cross-section? (y/n)", bool, default=False):
        axis = get_user_input("Section axis (x/y/z)", str, default='z')
        section = get_section_by_axis(mesh, axis)
        if section:
            print(f"Section created along {axis.upper()}-axis")
            # Could visualize section here if needed
        else:
            print("No intersection found at that plane")
    
    # Step 6: Select slots
    print("\nStep 6: Select Mounting Slots")
    print("-" * 40)
    
    selected_indices = get_slot_selection(grid)
    selected_slots = grid.get_slots_in_range(selected_indices)
    
    print(f"\nSelected {len(selected_slots)} slot(s):")
    for slot in selected_slots:
        pos = slot['position']
        print(f"  {slot['label']}: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})")
    
    # Step 7: Get cutting depths
    depths = get_depths(len(selected_slots))
    
    # Step 8: Process mesh (cut holes)
    print("\nStep 8: Processing Mesh")
    print("-" * 40)
    print("Cutting mounting holes...")
    
    slot_positions = [slot['position'] for slot in selected_slots]
    
    # Look for T-clip geometry
    tclip_mesh = None
    possible_tclip_paths = [
        Path("Clip Seat.step"),
        Path("models/t_clip_slot.stl"),
        Path("t_clip_slot.stl")
    ]
    
    # Find first existing T-clip file
    tclip_path = None
    for path in possible_tclip_paths:
        if path.exists():
            tclip_path = path
            break
    
    if tclip_path:
        print(f"Found T-clip geometry: {tclip_path}")
        if get_user_input("Insert T-clip geometry into holes? (y/n)", bool, default=True):
            try:
                tclip_mesh = load_mesh(str(tclip_path))
                print(f"✓ T-clip mesh loaded: {tclip_mesh.vertices.shape[0]} vertices")
                
                # Show T-clip dimensions
                tclip_dims = tclip_mesh.bounds[1] - tclip_mesh.bounds[0]
                print(f"  T-clip dimensions: {tclip_dims[0]:.4f} × {tclip_dims[1]:.4f} × {tclip_dims[2]:.4f} mm")
                
                # Check if T-clip needs scaling (if it's tiny, likely in meters instead of mm)
                max_dim = max(tclip_dims)
                if max_dim < 1.0:
                    suggested_scale = 1000.0  # Convert from meters to mm
                    print(f"  ⚠ T-clip appears very small (max dimension: {max_dim:.4f}mm)")
                    print(f"  Suggested scale factor: {suggested_scale}x (to convert to mm)")
                    
                    scale_factor = get_user_input(
                        f"Scale T-clip by factor [1000.0]",
                        float,
                        default=suggested_scale
                    )
                    
                    if scale_factor != 1.0:
                        tclip_mesh.apply_scale(scale_factor)
                        tclip_dims_scaled = tclip_mesh.bounds[1] - tclip_mesh.bounds[0]
                        print(f"  ✓ Scaled T-clip to: {tclip_dims_scaled[0]:.2f} × {tclip_dims_scaled[1]:.2f} × {tclip_dims_scaled[2]:.2f} mm")
                        
                        # Re-center the T-clip after scaling (scaling moves the centroid)
                        centroid = tclip_mesh.centroid
                        tclip_mesh.apply_translation(-centroid)
                        print(f"  ✓ Re-centered T-clip to origin (was offset by {centroid})")
                
                # Ask if user wants to cut holes or just insert T-clips
                cut_holes = get_user_input("Cut mounting holes before inserting T-clips? (y/n)", bool, default=True)
                if not cut_holes:
                    print("Skipping hole cutting, will only insert T-clip geometry")
                    depths = None  # Signal to skip hole cutting
            except Exception as e:
                print(f"Warning: Could not load T-clip mesh: {e}")
                print("Will only cut holes")
    else:
        print("No T-clip geometry found, will only cut holes")
    
    try:
        result_mesh = process_multiple_slots(
            mesh,
            slot_positions,
            depths,
            tclip_mesh,
            grid_plane,  # Pass grid plane for correct cutting orientation
            skip_holes=(depths is None)  # Skip holes if depths is None
        )
        
        print(f"\n✓ Processing complete!")
        print(f"  - {len(selected_slots)} slot(s) processed")
        
    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        sys.exit(1)
    
    # Step 9: Preview result
    print("\nStep 9: Preview Result")
    print("-" * 40)
    
    if get_user_input("Preview modified mesh? (y/n)", bool, default=True):
        print("Opening preview... Close window to continue.")
        result_viewer = MeshViewer(result_mesh, grid)
        result_viewer.show_multiview(show_grid=True)
    
    # Step 10: Export
    print("\nStep 10: Export STL")
    print("-" * 40)
    
    # Generate default output filename
    input_name = Path(mesh_path).stem
    default_output = f"{input_name}_with_tclip.stl"
    
    output_path = get_user_input(
        "Output filename",
        str,
        default=default_output
    )
    
    # Add .stl extension if not present
    if not output_path.endswith('.stl'):
        output_path += '.stl'
    
    try:
        result_mesh.export(output_path)
        print(f"\n✓ Successfully exported: {output_path}")
        print(f"  File size: {Path(output_path).stat().st_size / 1024:.1f} KB")
        
    except Exception as e:
        print(f"\n✗ Error exporting file: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("  Processing Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
