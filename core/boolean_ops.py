"""Boolean operations for mesh manipulation."""

import trimesh
import numpy as np
from config import T_CLIP_CIRCLE_DIAMETER


def create_cutting_cylinder(position, depth, diameter=T_CLIP_CIRCLE_DIAMETER, grid_plane='xy', cut_normal=None):
    """
    Create a cylinder for cutting mounting holes.
    
    Args:
        position: (x, y, z) position for cylinder center
        depth: Depth of the cylinder in mm
        diameter: Diameter in mm (default: 28.284mm)
        grid_plane: Plane orientation ('xy', 'xz', 'yz')
        cut_normal: np.array, direction to cut into the mesh (optional)
        
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
    if cut_normal is not None:
        n = np.array(cut_normal, dtype=float)
        n /= np.linalg.norm(n)
        axis = np.array([0, 0, 1], dtype=float)
        if not np.allclose(n, axis):
            rot_axis = np.cross(axis, n)
            rot_angle = np.arccos(np.clip(np.dot(axis, n), -1.0, 1.0))
            if np.linalg.norm(rot_axis) > 1e-6:
                rot_axis /= np.linalg.norm(rot_axis)
                rot_matrix = trimesh.transformations.rotation_matrix(rot_angle, rot_axis)
                cylinder.apply_transform(rot_matrix)
        # Place base of cylinder at position, extend into mesh along n
        cylinder.apply_translation(position + n * (depth / 2.0))
    else:
        # Old behavior: orient and offset by grid_plane
        if grid_plane == 'xz':
            rotation = trimesh.transformations.rotation_matrix(
                np.radians(90), [1, 0, 0], [0, 0, 0]
            )
            cylinder.apply_transform(rotation)
        elif grid_plane == 'yz':
            rotation = trimesh.transformations.rotation_matrix(
                np.radians(90), [0, 1, 0], [0, 0, 0]
            )
            cylinder.apply_transform(rotation)
        if grid_plane == 'xy':
            cylinder.apply_translation([0, 0, -depth/2])
        elif grid_plane == 'xz':
            cylinder.apply_translation([0, -depth/2, 0])
        else:  # 'yz'
            cylinder.apply_translation([-depth/2, 0, 0])
        cylinder.apply_translation(position)
    return cylinder


def cut_hole(mesh, position, depth, diameter=T_CLIP_CIRCLE_DIAMETER, grid_plane='xy', cut_normal=None):
    """
    Cut a circular hole in the mesh at specified position.
    
    Args:
        mesh: Original mesh
        position: (x, y, z) position for hole center
        depth: Depth of cut in mm
        diameter: Hole diameter in mm
        grid_plane: Plane orientation for proper cutting direction
        cut_normal: np.array, direction to cut into the mesh (optional)
        
    Returns:
        trimesh.Trimesh: Mesh with hole cut out
    """
    print(f"  - Cutting {diameter:.2f}mm diameter hole at position ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})")
    print(f"    Depth: {depth:.2f}mm, Grid plane: {grid_plane.upper()}")
    
    # Create cutting cylinder oriented correctly for the grid plane and normal
    cutter = create_cutting_cylinder(position, depth, diameter, grid_plane, cut_normal)
    
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


def insert_tclip(mesh, tclip_mesh, position, rotation_angle=0, grid_plane='xy', cut_normal=None):
    """
    Insert T-clip mounting slot at specified position.
    
    Args:
        mesh: Original mesh (with hole cut)
        tclip_mesh: T-clip mounting geometry
        position: (x, y, z) position for T-clip
        rotation_angle: Rotation around insertion axis in degrees
        grid_plane: Plane orientation for proper T-clip orientation
        cut_normal: np.array, direction pointing into the mesh (optional)
        
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
    
    # Orient T-clip based on cut_normal if provided, otherwise use grid_plane
    if cut_normal is not None:
        # Normalize the normal
        n = np.array(cut_normal, dtype=float)
        n /= np.linalg.norm(n)
        
        # Original T-clip: Y-axis is thin dimension, goes from negative to positive
        # The mounting face (base) is at MAX Y (Y=0 after centering)
        # We want the mounting face to point in the OPPOSITE direction of cut_normal
        # (cut_normal points INTO mesh, base should be flush at face)
        
        # Target: align Y-axis with NEGATIVE cut_normal
        target_axis = -n
        from_axis = np.array([0, 1, 0], dtype=float)
        
        if not np.allclose(target_axis, from_axis):
            # Check if it's pointing in opposite direction (180 degree rotation needed)
            if np.allclose(target_axis, -from_axis):
                # Need 180 degree rotation - use X-axis as rotation axis
                rot_matrix = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
                tclip_copy.apply_transform(rot_matrix)
                print(f"    Applied 180° rotation to reverse Y-axis direction")
            else:
                rot_axis = np.cross(from_axis, target_axis)
                rot_angle = np.arccos(np.clip(np.dot(from_axis, target_axis), -1.0, 1.0))
                if np.linalg.norm(rot_axis) > 1e-6:
                    rot_axis /= np.linalg.norm(rot_axis)
                    rot_matrix = trimesh.transformations.rotation_matrix(rot_angle, rot_axis)
                    tclip_copy.apply_transform(rot_matrix)
                    print(f"    Oriented T-clip: Y-axis now points opposite to cut_normal: {-n}")
        else:
            print(f"    T-clip Y-axis already points opposite to cut_normal")
    else:
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

    # IMPORTANT: The T-clip is now centered so the mounting face (MIN of thin dimension) is at origin
    # This means we can directly place it at the grid position - no offset needed!
    # The T-clip extends INTO the mesh from the mounting face

    # Verify mounting face is at origin (before rotation, it's at MIN Y = 0)
    # After rotation, we need to find which axis now represents the "thin" dimension (mounting face)
    flush_offset = np.array([0.0, 0.0, 0.0])

    if cut_normal is not None:
        # After orienting with cut_normal, the thin dimension should align with the normal axis
        # Find which axis has the smallest dimension (the thin one)
        thin_axis_idx = np.argmin(rot_dims)

        # The mounting face is at the MIN bound of this axis (should be 0 or very close)
        min_val = rot_bounds[0][thin_axis_idx]

        if abs(min_val) > 0.1:  # If not at origin (within 0.1mm tolerance)
            print(f"    Warning: Mounting face at {min_val:.2f} on axis {thin_axis_idx}, expected near 0")
            flush_offset[thin_axis_idx] = -min_val

        print(f"    Mounting face is at MIN of axis {thin_axis_idx} (value={rot_bounds[0][thin_axis_idx]:.4f})")
        print(f"    T-clip will be flush at face, extending {rot_dims[thin_axis_idx]:.2f}mm INTO mesh")
    else:
        # Legacy fallback for grid_plane without cut_normal
        if grid_plane == 'xy':
            # Z is the thin dimension after rotation
            flush_offset[2] = -rot_bounds[0][2]
        elif grid_plane == 'xz':
            # Y is the thin dimension (should already be at 0)
            flush_offset[1] = -rot_bounds[0][1]
        elif grid_plane == 'yz':
            # X is the thin dimension after rotation
            flush_offset[0] = -rot_bounds[0][0]

    # Position T-clip at grid position (mounting face flush with surface)
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


def process_multiple_slots(mesh, slot_positions, depths, tclip_mesh=None, grid_plane='xy', skip_holes=False, cut_normal=None):
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
            result = cut_hole(result, position, depth, grid_plane=grid_plane, cut_normal=cut_normal)
    
    # SECOND: Insert all T-clips (if provided)
    if tclip_mesh is not None:
        print("\n--- Inserting T-clips ---")
        for i, position in enumerate(slot_positions):
            print(f"\nT-clip {i+1}/{len(slot_positions)}:")
            result = insert_tclip(result, tclip_mesh, position, grid_plane=grid_plane, cut_normal=cut_normal)
    
    return result
