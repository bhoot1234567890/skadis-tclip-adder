"""Mesh loading and validation utilities."""

import trimesh
import numpy as np
from pathlib import Path


def load_mesh(file_path):
    """
    Load a mesh from STL, STEP, OBJ, or other supported formats.
    
    Args:
        file_path: Path to the mesh file
        
    Returns:
        trimesh.Trimesh: Loaded mesh object
        
    Raises:
        ValueError: If file format is not supported or file doesn't exist
    """
    path = Path(file_path)
    
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")
    
    print(f"Loading mesh from: {path.name}")
    
    # Trimesh can handle many formats including STEP via gmsh
    try:
        mesh = trimesh.load(str(path))
        
        # If it's a scene (multiple meshes), combine them
        if isinstance(mesh, trimesh.Scene):
            print("  - Scene detected, combining meshes...")
            # Use to_geometry() instead of deprecated dump()
            if hasattr(mesh, 'to_geometry'):
                mesh = mesh.to_geometry()
            else:
                mesh = mesh.dump(concatenate=True)
        
        print(f"  - Loaded: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        print(f"  - Bounds: {mesh.bounds}")
        print(f"  - Watertight: {mesh.is_watertight}")
        
        # Attempt to fix common issues
        if not mesh.is_watertight:
            print("  - Attempting to fix mesh...")
            mesh.fill_holes()
            mesh.remove_duplicate_faces()
            mesh.remove_degenerate_faces()
            print(f"  - After fixes, watertight: {mesh.is_watertight}")
        
        return mesh
        
    except Exception as e:
        raise ValueError(f"Failed to load mesh: {e}")


def get_mesh_info(mesh):
    """Get comprehensive information about a mesh."""
    bounds = mesh.bounds
    center = mesh.centroid
    
    return {
        'vertices': len(mesh.vertices),
        'faces': len(mesh.faces),
        'bounds_min': bounds[0],
        'bounds_max': bounds[1],
        'dimensions': bounds[1] - bounds[0],
        'centroid': center,
        'volume': mesh.volume if mesh.is_volume else 0,
        'area': mesh.area,
        'watertight': mesh.is_watertight,
    }


def print_mesh_info(mesh):
    """Print detailed mesh information."""
    info = get_mesh_info(mesh)
    
    print("\n=== Mesh Information ===")
    print(f"Vertices: {info['vertices']:,}")
    print(f"Faces: {info['faces']:,}")
    print(f"Dimensions (X×Y×Z): {info['dimensions'][0]:.2f} × {info['dimensions'][1]:.2f} × {info['dimensions'][2]:.2f} mm")
    print(f"Centroid: ({info['centroid'][0]:.2f}, {info['centroid'][1]:.2f}, {info['centroid'][2]:.2f})")
    print(f"Surface Area: {info['area']:.2f} mm²")
    if info['watertight']:
        print(f"Volume: {info['volume']:.2f} mm³")
    print(f"Watertight: {info['watertight']}")
    print("=" * 25 + "\n")
