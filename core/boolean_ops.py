"""Boolean operations for mesh manipulation."""

import trimesh
import numpy as np
from config import T_CLIP_CIRCLE_DIAMETER


def create_cutting_cylinder(position, depth, diameter=T_CLIP_CIRCLE_DIAMETER, grid_plane='xy'):
    """
    Create a cylinder for cutting mounting holes.
    
    Args:
        position: (x, y, z) position for cylinder center
        depth: Depth of the cylinder in mm
        diameter: Diameter in mm (default: 28.284mm)
        grid_plane: Plane orientation ('xy', 'xz', 'yz')
        
    Returns:
        trimesh.Trimesh: Cylinder mesh
    """
    radius = diameter / 2.0
    
    # Create cylinder aligned with Z-axis by default
    cylinder = trimesh.creation.cylinder(
        radius=radius,
        height=depth,
        sections=32  # Smooth circle
    )
    
    # Rotate cylinder based on grid plane to cut perpendicular to that plane
    if grid_plane == 'xz':
        # Grid on XZ plane, cut along Y-axis (rotate 90° around X)
        rotation = trimesh.transformations.rotation_matrix(
            np.radians(90), [1, 0, 0], [0, 0, 0]
        )
        cylinder.apply_transform(rotation)
    elif grid_plane == 'yz':
        # Grid on YZ plane, cut along X-axis (rotate 90° around Y)
        rotation = trimesh.transformations.rotation_matrix(
            np.radians(90), [0, 1, 0], [0, 0, 0]
        )
        cylinder.apply_transform(rotation)
    # else: grid_plane == 'xy', cylinder already aligned with Z-axis (perpendicular to XY)
    
    # Offset cylinder by half depth so it cuts inward from the surface
    if grid_plane == 'xy':
        # Move down by half depth
        cylinder.apply_translation([0, 0, -depth/2])
    elif grid_plane == 'xz':
        # Move along -Y by half depth
        cylinder.apply_translation([0, -depth/2, 0])
    else:  # 'yz'
        # Move along -X by half depth
        cylinder.apply_translation([-depth/2, 0, 0])
    
    # Position at the specified location
    cylinder.apply_translation(position)
    
    return cylinder


def cut_hole(mesh, position, depth, diameter=T_CLIP_CIRCLE_DIAMETER, grid_plane='xy'):
    """
    Cut a circular hole in the mesh at specified position.
    
    Args:
        mesh: Original mesh
        position: (x, y, z) position for hole center
        depth: Depth of cut in mm
        diameter: Hole diameter in mm
        grid_plane: Plane orientation for proper cutting direction
        
    Returns:
        trimesh.Trimesh: Mesh with hole cut out
    """
    print(f"  - Cutting {diameter:.2f}mm diameter hole at position ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})")
    print(f"    Depth: {depth:.2f}mm, Grid plane: {grid_plane.upper()}")
    
    # Create cutting cylinder oriented correctly for the grid plane
    cutter = create_cutting_cylinder(position, depth, diameter, grid_plane)
    
    # Perform boolean difference - try different engines
    engines_to_try = []
    
    # Check if manifold3d is available
    try:
        import manifold3d
        engines_to_try.append('manifold')
    except ImportError:
        pass
    
    # Always try scad and blender as fallback
    engines_to_try.extend(['scad', 'blender'])
    
    for engine in engines_to_try:
        try:
            result = mesh.difference(cutter, engine=engine)
            print(f"    ✓ Hole cut successfully (using {engine})")
            return result
        except Exception as e:
            print(f"    ✗ {engine} engine failed: {e}")
            continue
    
    print(f"    ✗ All boolean engines failed, returning original mesh")
    return mesh


def insert_tclip(mesh, tclip_mesh, position, rotation_angle=0, grid_plane='xy'):
    """
    Insert T-clip mounting slot at specified position.
    
    Args:
        mesh: Original mesh (with hole cut)
        tclip_mesh: T-clip mounting geometry
        position: (x, y, z) position for T-clip
        rotation_angle: Rotation around insertion axis in degrees
        grid_plane: Plane orientation for proper T-clip orientation
        
    Returns:
        trimesh.Trimesh: Combined mesh with T-clip
    """
    print(f"  - Inserting T-clip at position ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})")
    
    # Copy T-clip to avoid modifying original
    tclip_copy = tclip_mesh.copy()
    
    # Debug: Show original T-clip info
    orig_bounds = tclip_copy.bounds
    orig_dims = orig_bounds[1] - orig_bounds[0]
    orig_centroid = tclip_copy.centroid
    print(f"    Original T-clip: dims=({orig_dims[0]:.4f}, {orig_dims[1]:.4f}, {orig_dims[2]:.4f}), centroid=({orig_centroid[0]:.4f}, {orig_centroid[1]:.4f}, {orig_centroid[2]:.4f})")
    
    # Determine which axis is the thin dimension (the "depth" that should point perpendicular to grid)
    # Assume Y is the thin dimension in the original model
    thin_axis_idx = 1  # Y-axis
    
    # Orient T-clip based on grid plane
    # The thin dimension should point perpendicular to the grid plane
    if grid_plane == 'xy':
        # Grid on XY plane, thin dimension should point along Z-axis
        # Original thin is Y, need to rotate Y→Z: rotate -90° around X
        rotation = trimesh.transformations.rotation_matrix(
            np.radians(-90), [1, 0, 0], [0, 0, 0]
        )
        tclip_copy.apply_transform(rotation)
        print(f"    Applied -90° rotation around X-axis (Y→Z for XY plane)")
    elif grid_plane == 'xz':
        # Grid on XZ plane, thin dimension should point along Y-axis
        # Original thin is already Y, NO rotation needed
        print(f"    No rotation needed (Y-axis already perpendicular to XZ plane)")
    elif grid_plane == 'yz':
        # Grid on YZ plane, thin dimension should point along X-axis
        # Original thin is Y, need to rotate Y→X: rotate -90° around Z
        rotation = trimesh.transformations.rotation_matrix(
            np.radians(-90), [0, 0, 1], [0, 0, 0]
        )
        tclip_copy.apply_transform(rotation)
        print(f"    Applied -90° rotation around Z-axis (Y→X for YZ plane)")
    
    # Apply additional rotation if specified
    if rotation_angle != 0:
        if grid_plane == 'xy':
            axis = [0, 0, 1]  # Rotate around Z
        elif grid_plane == 'xz':
            axis = [0, 1, 0]  # Rotate around Y
        else:  # 'yz'
            axis = [1, 0, 0]  # Rotate around X
        
        rotation_matrix = trimesh.transformations.rotation_matrix(
            np.radians(rotation_angle),
            axis,
            point=[0, 0, 0]
        )
        tclip_copy.apply_transform(rotation_matrix)
    
    # Debug: Show T-clip after rotation
    rot_centroid = tclip_copy.centroid
    rot_bounds = tclip_copy.bounds
    rot_dims = rot_bounds[1] - rot_bounds[0]
    print(f"    After rotation: centroid=({rot_centroid[0]:.4f}, {rot_centroid[1]:.4f}, {rot_centroid[2]:.4f}), dims=({rot_dims[0]:.2f}, {rot_dims[1]:.2f}, {rot_dims[2]:.2f})")
    
    # Calculate offset to make T-clip exactly flush with face
    # We want the outer edge of the T-clip to be exactly at the grid position
    flush_offset = np.array([0.0, 0.0, 0.0])
    
    if grid_plane == 'xy':
        # Grid on XY plane at specific Z, T-clip thin dimension is now along Z
        # We want max Z of T-clip to be at position Z
        flush_offset[2] = -rot_bounds[1][2]  # Offset so max Z aligns with position
        print(f"    Flush offset: Z={flush_offset[2]:.2f}mm (max Z edge at grid plane)")
    elif grid_plane == 'xz':
        # Grid on XZ plane at specific Y, T-clip thin dimension is along Y
        # We want max Y of T-clip to be at position Y
        flush_offset[1] = -rot_bounds[1][1]  # Offset so max Y aligns with position
        print(f"    Flush offset: Y={flush_offset[1]:.2f}mm (max Y edge at grid plane)")
    elif grid_plane == 'yz':
        # Grid on YZ plane at specific X, T-clip thin dimension is along X
        # We want max X of T-clip to be at position X
        flush_offset[0] = -rot_bounds[1][0]  # Offset so max X aligns with position
        print(f"    Flush offset: X={flush_offset[0]:.2f}mm (max X edge at grid plane)")
    
    # Position T-clip with flush offset
    tclip_copy.apply_translation(position + flush_offset)
    
    # Debug: Show final position
    final_centroid = tclip_copy.centroid
    final_bounds = tclip_copy.bounds
    print(f"    Final T-clip: centroid=({final_centroid[0]:.2f}, {final_centroid[1]:.2f}, {final_centroid[2]:.2f})")
    print(f"    Final bounds: min=({final_bounds[0][0]:.2f}, {final_bounds[0][1]:.2f}, {final_bounds[0][2]:.2f}), max=({final_bounds[1][0]:.2f}, {final_bounds[1][1]:.2f}, {final_bounds[1][2]:.2f})")
    
    # Try different engines
    engines_to_try = []
    
    # Check if manifold3d is available
    try:
        import manifold3d
        engines_to_try.append('manifold')
    except ImportError:
        pass
    
    engines_to_try.extend(['scad', 'blender'])
    
    # Try to repair T-clip if not watertight
    if not tclip_copy.is_watertight:
        print(f"    T-clip not watertight, attempting repairs...")
        tclip_copy.fill_holes()
        tclip_copy.remove_duplicate_faces()
        tclip_copy.remove_degenerate_faces()
        tclip_copy.merge_vertices()
        tclip_copy.fix_normals()
        if tclip_copy.is_watertight:
            print(f"    ✓ T-clip repaired and watertight")
        else:
            print(f"    ⚠ T-clip still not watertight")
    
    # Try to repair main mesh if not watertight
    if not mesh.is_watertight:
        print(f"    Main mesh not watertight, attempting repairs...")
        mesh.fill_holes()
        mesh.remove_duplicate_faces()
        mesh.remove_degenerate_faces()
        mesh.merge_vertices()
        mesh.fix_normals()
        if mesh.is_watertight:
            print(f"    ✓ Main mesh repaired and watertight")
        else:
            print(f"    ⚠ Main mesh still not watertight")
    
    for engine in engines_to_try:
        try:
            result = mesh.union(tclip_copy, engine=engine)
            print(f"    ✓ T-clip inserted successfully (using {engine})")
            return result
        except Exception as e:
            print(f"    ✗ {engine} engine failed: {e}")
            continue
    
    # Fallback: just concatenate the meshes
    print(f"    ⚠ Using concatenation fallback (meshes not merged)")
    return trimesh.util.concatenate([mesh, tclip_copy])


def process_slot(mesh, slot_position, depth, tclip_mesh=None, grid_plane='xy', skip_hole=False):
    """
    Process a single slot: cut hole and optionally insert T-clip.
    
    Args:
        mesh: Original mesh
        slot_position: (x, y, z) position
        depth: Cutting depth in mm
        tclip_mesh: Optional T-clip mesh to insert
        grid_plane: Plane orientation for cutting direction
        skip_hole: If True, skip hole cutting and only insert T-clip
        
    Returns:
        trimesh.Trimesh: Processed mesh
    """
    result = mesh
    
    # Cut the hole with proper orientation (unless skipped)
    if not skip_hole:
        result = cut_hole(result, slot_position, depth, grid_plane=grid_plane)
    
    # Insert T-clip if provided
    if tclip_mesh is not None:
        result = insert_tclip(result, tclip_mesh, slot_position, grid_plane=grid_plane)
    
    return result


def process_multiple_slots(mesh, slot_positions, depths, tclip_mesh=None, grid_plane='xy', skip_holes=False):
    """
    Process multiple slots with individual depths.
    
    Args:
        mesh: Original mesh
        slot_positions: List of (x, y, z) positions
        depths: List of depths (same length as positions) or single depth for all, or None to skip
        tclip_mesh: Optional T-clip mesh to insert at each position
        grid_plane: Plane orientation for cutting direction
        skip_holes: If True, skip hole cutting and only insert T-clips
        
    Returns:
        trimesh.Trimesh: Processed mesh
    """
    result = mesh
    
    # Handle single depth value or None
    if depths is None or skip_holes:
        depths = [0] * len(slot_positions)
        skip_holes = True
    elif not isinstance(depths, (list, tuple)):
        depths = [depths] * len(slot_positions)
    
    # FIRST: Cut all holes (if not skipped)
    if not skip_holes:
        print("\n--- Cutting holes ---")
        for i, (position, depth) in enumerate(zip(slot_positions, depths)):
            print(f"\nHole {i+1}/{len(slot_positions)}:")
            result = cut_hole(result, position, depth, grid_plane=grid_plane)
    
    # SECOND: Insert all T-clips (if provided)
    if tclip_mesh is not None:
        print("\n--- Inserting T-clips ---")
        for i, position in enumerate(slot_positions):
            print(f"\nT-clip {i+1}/{len(slot_positions)}:")
            result = insert_tclip(result, tclip_mesh, position, grid_plane=grid_plane)
    
    return result
