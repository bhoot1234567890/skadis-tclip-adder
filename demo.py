#!/usr/bin/env python3
"""
Quick demo of the T-clip adder tool with automated slot selection.
This script demonstrates the workflow without user interaction.
"""

from pathlib import Path
from core.mesh_loader import load_mesh, print_mesh_info
from core.grid_system import SkadisGrid
from core.boolean_ops import process_multiple_slots
from visualization.viewer_mpl import MeshViewer

def demo():
    """Run a quick demonstration."""
    print("\n" + "=" * 60)
    print("  IKEA Skadis T-Clip Mounting Tool - DEMO")
    print("=" * 60 + "\n")
    
    # Step 1: Load mesh
    print("Step 1: Loading Clip Seat.step...")
    mesh_path = "Clip Seat.step"
    
    if not Path(mesh_path).exists():
        print(f"Error: {mesh_path} not found")
        return
    
    mesh = load_mesh(mesh_path)
    print_mesh_info(mesh)
    
    # Step 2: Create grid
    print("Step 2: Creating Skadis grid...")
    grid = SkadisGrid(mesh, offset=(0, 0, 0), use_mesh_center=True)
    grid.print_grid_info()
    
    # Step 3: Show visualization
    print("Step 3: Opening visualization...")
    print("Close the matplotlib window to continue...\n")
    
    viewer = MeshViewer(mesh, grid)
    viewer.show_multiview(show_grid=True)
    
    # Step 4: Select slots (automated for demo)
    print("\nStep 4: Selecting slots automatically...")
    
    # Select middle slots as an example
    num_slots = len(grid.slots)
    middle_slot = num_slots // 2
    selected_indices = [middle_slot - 1, middle_slot, middle_slot + 1]
    
    print(f"Selected slots: {selected_indices}")
    
    selected_slots = grid.get_slots_in_range(selected_indices)
    for slot in selected_slots:
        pos = slot['position']
        print(f"  {slot['label']}: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) mm")
    
    # Step 5: Process mesh (cut holes)
    print("\nStep 5: Cutting mounting holes...")
    
    slot_positions = [slot['position'] for slot in selected_slots]
    depths = [10.0] * len(selected_slots)  # 10mm depth for all
    
    try:
        result_mesh = process_multiple_slots(
            mesh,
            slot_positions,
            depths,
            tclip_mesh=None  # No T-clip insertion for demo
        )
        
        print(f"\n✓ Processing complete!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return
    
    # Step 6: Preview result
    print("\nStep 6: Previewing result...")
    print("Close the window to continue...")
    
    result_viewer = MeshViewer(result_mesh, grid)
    result_viewer.show_multiview(show_grid=True)
    
    # Step 7: Export
    print("\nStep 7: Exporting STL...")
    
    output_path = "Clip_Seat_with_tclip_demo.stl"
    result_mesh.export(output_path)
    
    print(f"\n✓ Exported: {output_path}")
    print(f"  Size: {Path(output_path).stat().st_size / 1024:.1f} KB")
    
    print("\n" + "=" * 60)
    print("  Demo Complete!")
    print("=" * 60 + "\n")
    
    print("To run the interactive tool, use: python main.py")

if __name__ == "__main__":
    try:
        demo()
    except KeyboardInterrupt:
        print("\n\nDemo cancelled.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
