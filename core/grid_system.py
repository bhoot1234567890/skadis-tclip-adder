"""IKEA Skadis grid generation and slot management."""

import numpy as np
from config import SKADIS_SLOT_SPACING_H, SKADIS_SLOT_SPACING_V, SKADIS_STAGGER_OFFSET


class SkadisGrid:
    """Manages Skadis pegboard grid positioning and slot numbering."""
    
    def __init__(self, mesh, offset=(0, 0, 0), use_mesh_center=True, grid_plane='xy', boundary_type='max_z'):
        """
        Initialize grid based on mesh bounds.
        
        Args:
            mesh: trimesh.Trimesh object
            offset: Manual offset (x, y, z) in mm
            use_mesh_center: If True, center grid on mesh centroid in plane dimensions
            grid_plane: Which plane to draw grid on ('xy', 'xz', 'yz')
            boundary_type: Which boundary to place grid on (e.g., 'max_z', 'min_x')
        """
        self.mesh = mesh
        self.offset = np.array(offset)
        self.use_mesh_center = use_mesh_center
        self.grid_plane = grid_plane.lower()
        self.boundary_type = boundary_type
        
        # Calculate grid origin - center in plane, but at boundary in depth axis
        bounds = mesh.bounds
        if grid_plane == 'xy':
            # Grid on XY plane
            x = mesh.centroid[0] if use_mesh_center else bounds[0][0]
            y = mesh.centroid[1] if use_mesh_center else bounds[0][1]
            z = bounds[1][2] if 'max' in boundary_type else bounds[0][2]
            self.origin = np.array([x, y, z]) + self.offset
        elif grid_plane == 'xz':
            # Grid on XZ plane
            x = mesh.centroid[0] if use_mesh_center else bounds[0][0]
            y = bounds[1][1] if 'max' in boundary_type else bounds[0][1]
            z = mesh.centroid[2] if use_mesh_center else bounds[0][2]
            self.origin = np.array([x, y, z]) + self.offset
        else:  # 'yz'
            # Grid on YZ plane
            x = bounds[1][0] if 'max' in boundary_type else bounds[0][0]
            y = mesh.centroid[1] if use_mesh_center else bounds[0][1]
            z = mesh.centroid[2] if use_mesh_center else bounds[0][2]
            self.origin = np.array([x, y, z]) + self.offset
        
        # Generate grid slots
        self.slots = self._generate_slots()
        
    def _generate_slots(self):
        """Generate staggered Skadis grid with proper spacing."""
        bounds = self.mesh.bounds
        min_bound, max_bound = bounds[0], bounds[1]
        
        # Use minimal padding - just 1 slot spacing
        padding = max(SKADIS_SLOT_SPACING_H, SKADIS_SLOT_SPACING_V)
        
        # Determine which axes to use based on grid plane
        if self.grid_plane == 'xy':
            # Grid on XY plane, facing Z
            h_idx, v_idx, d_idx = 0, 1, 2  # X=horizontal, Y=vertical, Z=depth
            h_min, h_max = min_bound[0] - padding, max_bound[0] + padding
            v_min, v_max = min_bound[1] - padding, max_bound[1] + padding
            depth_pos = self.origin[2]
        elif self.grid_plane == 'xz':
            # Grid on XZ plane, facing Y
            h_idx, v_idx, d_idx = 0, 2, 1  # X=horizontal, Z=vertical, Y=depth
            h_min, h_max = min_bound[0] - padding, max_bound[0] + padding
            v_min, v_max = min_bound[2] - padding, max_bound[2] + padding
            depth_pos = self.origin[1]
        else:  # 'yz'
            # Grid on YZ plane, facing X
            h_idx, v_idx, d_idx = 1, 2, 0  # Y=horizontal, Z=vertical, X=depth
            h_min, h_max = min_bound[1] - padding, max_bound[1] + padding
            v_min, v_max = min_bound[2] - padding, max_bound[2] + padding
            depth_pos = self.origin[0]
        
        slots = []
        slot_index = 1
        
        # Generate staggered grid
        # Start from origin and work outward
        h_origin = self.origin[h_idx]
        v_origin = self.origin[v_idx]
        
        # Calculate starting positions
        h_start = h_origin - (int((h_origin - h_min) / SKADIS_SLOT_SPACING_H) * SKADIS_SLOT_SPACING_H)
        v_start = v_origin - (int((v_origin - v_min) / SKADIS_SLOT_SPACING_V) * SKADIS_SLOT_SPACING_V)
        
        col = 0
        h = h_start
        while h <= h_max:
            row = 0
            v = v_start
            
            # Every other column is staggered down by half vertical spacing
            if col % 2 == 1:
                v += SKADIS_STAGGER_OFFSET
            
            while v <= v_max:
                # Create position array based on grid plane
                position = np.zeros(3)
                position[h_idx] = h
                position[v_idx] = v
                position[d_idx] = depth_pos
                
                slots.append({
                    'index': slot_index,
                    'position': position,
                    'label': f"S{slot_index}",
                    'row': row,
                    'col': col,
                    'staggered': (col % 2 == 1)
                })
                slot_index += 1
                v += SKADIS_SLOT_SPACING_V
                row += 1
            
            h += SKADIS_SLOT_SPACING_H
            col += 1
        
        print(f"Generated {len(slots)} staggered grid slots")
        
        # Debug: Print first 3 slot positions
        if slots:
            print(f"\nDEBUG - Grid generation:")
            print(f"  Grid plane: {self.grid_plane}")
            print(f"  Origin: {self.origin}")
            print(f"  Depth axis index: {d_idx}, Depth position: {depth_pos}")
            print(f"  First 3 slot positions:")
            for i, slot in enumerate(slots[:3]):
                print(f"    Slot {slot['index']}: {slot['position']}")
        
        return slots
    
    def get_slot(self, index):
        """Get slot by index number."""
        for slot in self.slots:
            if slot['index'] == index:
                return slot
        return None
    
    def get_slot_position(self, index):
        """Get 3D position of a slot by index."""
        slot = self.get_slot(index)
        return slot['position'] if slot else None
    
    def get_slots_in_range(self, indices):
        """Get multiple slots by index list."""
        return [self.get_slot(i) for i in indices if self.get_slot(i)]
    
    def print_grid_info(self):
        """Print grid information."""
        print(f"\n=== Skadis Grid ===")
        print(f"Grid plane: {self.grid_plane.upper()}")
        print(f"Origin: ({self.origin[0]:.2f}, {self.origin[1]:.2f}, {self.origin[2]:.2f})")
        print(f"Offset: ({self.offset[0]:.2f}, {self.offset[1]:.2f}, {self.offset[2]:.2f})")
        print(f"Total slots: {len(self.slots)}")
        print(f"Horizontal spacing: {SKADIS_SLOT_SPACING_H}mm")
        print(f"Vertical spacing: {SKADIS_SLOT_SPACING_V}mm")
        print(f"Stagger offset: {SKADIS_STAGGER_OFFSET}mm (every other column)")
        print("=" * 20 + "\n")
