"""Section analysis and cross-section generation."""

import numpy as np
import trimesh


def create_section(mesh, plane_origin, plane_normal, return_2d=True):
    """
    Create a cross-section of the mesh at a specified plane.
    
    Args:
        mesh: trimesh.Trimesh object
        plane_origin: Point on the plane (x, y, z)
        plane_normal: Normal vector of the plane (x, y, z)
        return_2d: If True, return 2D planar projection
        
    Returns:
        Section path or None if no intersection
    """
    section = mesh.section(
        plane_origin=plane_origin,
        plane_normal=plane_normal
    )
    
    if section is None:
        return None
    
    if return_2d:
        # Convert to 2D planar coordinates
        planar, to_3D = section.to_planar()
        return planar
    
    return section


def create_xy_section(mesh, z_position=None):
    """Create XY plane section (top view cross-section)."""
    if z_position is None:
        z_position = mesh.centroid[2]
    
    return create_section(
        mesh,
        plane_origin=[0, 0, z_position],
        plane_normal=[0, 0, 1]
    )


def create_xz_section(mesh, y_position=None):
    """Create XZ plane section (front view cross-section)."""
    if y_position is None:
        y_position = mesh.centroid[1]
    
    return create_section(
        mesh,
        plane_origin=[0, y_position, 0],
        plane_normal=[0, 1, 0]
    )


def create_yz_section(mesh, x_position=None):
    """Create YZ plane section (side view cross-section)."""
    if x_position is None:
        x_position = mesh.centroid[0]
    
    return create_section(
        mesh,
        plane_origin=[x_position, 0, 0],
        plane_normal=[1, 0, 0]
    )


def get_section_by_axis(mesh, axis='z', position=None):
    """
    Get section along specified axis.
    
    Args:
        mesh: trimesh.Trimesh object
        axis: 'x', 'y', or 'z'
        position: Position along axis (default: centroid)
        
    Returns:
        Section path
    """
    axis = axis.lower()
    
    if axis == 'x':
        return create_yz_section(mesh, position)
    elif axis == 'y':
        return create_xz_section(mesh, position)
    elif axis == 'z':
        return create_xy_section(mesh, position)
    else:
        raise ValueError(f"Invalid axis: {axis}. Use 'x', 'y', or 'z'")
