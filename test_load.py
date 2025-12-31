#!/usr/bin/env python3
"""Quick test to verify STEP file loading."""

import sys
from pathlib import Path

# Test imports
try:
    import trimesh
    print("✓ trimesh imported")
except ImportError as e:
    print(f"✗ trimesh import failed: {e}")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('TkAgg')  # Use non-blocking backend
    import matplotlib.pyplot as plt
    print("✓ matplotlib imported")
except ImportError as e:
    print(f"✗ matplotlib import failed: {e}")
    sys.exit(1)

# Test STEP file loading
step_file = "Clip Seat.step"

if not Path(step_file).exists():
    print(f"✗ File not found: {step_file}")
    sys.exit(1)

print(f"\n✓ File exists: {step_file}")
print(f"  Size: {Path(step_file).stat().st_size / 1024:.1f} KB")

print("\nAttempting to load STEP file with trimesh...")

try:
    mesh = trimesh.load(step_file)
    print(f"✓ Loaded successfully!")
    print(f"  Type: {type(mesh)}")
    
    if isinstance(mesh, trimesh.Scene):
        print(f"  - Scene with {len(mesh.geometry)} geometries")
        mesh = mesh.dump(concatenate=True)
        print(f"  - Combined into single mesh")
    
    print(f"  - Vertices: {len(mesh.vertices):,}")
    print(f"  - Faces: {len(mesh.faces):,}")
    print(f"  - Bounds: {mesh.bounds}")
    print(f"  - Watertight: {mesh.is_watertight}")
    
    # Export as STL for testing
    stl_output = "test_output.stl"
    mesh.export(stl_output)
    print(f"\n✓ Exported test STL: {stl_output}")
    print(f"  Size: {Path(stl_output).stat().st_size / 1024:.1f} KB")
    
except Exception as e:
    print(f"✗ Failed to load: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ All tests passed!")
