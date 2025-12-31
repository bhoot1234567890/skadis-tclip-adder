"""Visualization using PyVista for multi-view rendering."""

import pyvista as pv
import numpy as np
from config import MESH_COLOR, GRID_COLOR, SLOT_MARKER_SIZE, BBOX_COLORS


def trimesh_to_pyvista(mesh):
    """Convert trimesh mesh to PyVista PolyData."""
    faces = np.column_stack((
        np.full(len(mesh.faces), 3),
        mesh.faces
    )).flatten()
    
    return pv.PolyData(mesh.vertices, faces)


class MeshViewer:
    """Multi-view mesh viewer with grid overlay."""
    
    def __init__(self, mesh, grid=None, window_size=(1600, 1200), show_bbox=False):
        """
        Initialize viewer with mesh and optional grid.
        
        Args:
            mesh: trimesh.Trimesh object
            grid: SkadisGrid object (optional)
            window_size: (width, height) in pixels
            show_bbox: Show colored bounding box for face selection
        """
        self.mesh = mesh
        self.grid = grid
        self.pv_mesh = trimesh_to_pyvista(mesh)
        self.window_size = window_size
        self.show_bbox = show_bbox
        
    def show_multiview(self, show_grid=True, show_section=False, section_axis='z'):
        """
        Display mesh in 3 views: isometric, front, and top.
        
        Args:
            show_grid: Display Skadis grid overlay
            show_section: Display cross-section
            section_axis: Axis for cross-section ('x', 'y', or 'z')
        """
        plotter = pv.Plotter(shape=(2, 2), window_size=self.window_size)
        
        # Adjust mesh opacity if showing bounding box
        mesh_opacity = 0.3 if self.show_bbox else 1.0
        title_suffix = " (Face Selection)" if self.show_bbox else ""
        
        # View 1: Isometric (2.5D)
        plotter.subplot(0, 0)
        plotter.add_text(f"Isometric View (2.5D){title_suffix}", font_size=12, color='black')
        plotter.add_mesh(self.pv_mesh, color=MESH_COLOR, opacity=mesh_opacity, show_edges=True, edge_color='gray')
        
        if self.show_bbox:
            self._add_colored_bbox(plotter)
        
        if show_grid and self.grid:
            self._add_grid_overlay(plotter)
        
        plotter.view_isometric()
        plotter.camera.zoom(1.2)
        
        # View 2: Front View (XZ plane)
        plotter.subplot(0, 1)
        plotter.add_text(f"Front View{title_suffix}", font_size=12, color='black')
        plotter.add_mesh(self.pv_mesh, color=MESH_COLOR, opacity=mesh_opacity, show_edges=True, edge_color='gray')
        
        if self.show_bbox:
            self._add_colored_bbox(plotter)
        
        if show_grid and self.grid:
            self._add_grid_overlay(plotter)
        
        plotter.view_xz()
        plotter.camera.zoom(1.2)
        
        # View 3: Top View (XY plane)
        plotter.subplot(1, 0)
        plotter.add_text(f"Top View{title_suffix}", font_size=12, color='black')
        plotter.add_mesh(self.pv_mesh, color=MESH_COLOR, opacity=mesh_opacity, show_edges=True, edge_color='gray')
        
        if self.show_bbox:
            self._add_colored_bbox(plotter)
        
        if show_grid and self.grid:
            self._add_grid_overlay(plotter)
        
        plotter.view_xy()
        plotter.camera.zoom(1.2)
        
        # View 4: Interactive/Detail view
        plotter.subplot(1, 1)
        plotter.add_text(f"Detail View (Interactive){title_suffix}", font_size=12, color='black')
        plotter.add_mesh(self.pv_mesh, color=MESH_COLOR, opacity=mesh_opacity, show_edges=True, edge_color='gray')
        
        if self.show_bbox:
            self._add_colored_bbox(plotter)
        
        if show_grid and self.grid:
            self._add_grid_overlay(plotter, show_labels=True)
        
        plotter.view_isometric()
        plotter.add_axes()
        
        plotter.show()
    
    def _add_grid_overlay(self, plotter, show_labels=False):
        """Add Skadis grid points and labels to the plot."""
        if not self.grid or not self.grid.slots:
            return
        
        # Extract slot positions
        positions = np.array([slot['position'] for slot in self.grid.slots])
        
        # Add slot markers as spheres
        for slot in self.grid.slots:
            pos = slot['position']
            sphere = pv.Sphere(radius=2, center=pos)
            plotter.add_mesh(sphere, color=GRID_COLOR, opacity=0.7)
            
            # Add labels if requested
            if show_labels:
                plotter.add_point_labels(
                    [pos],
                    [slot['label']],
                    font_size=8,
                    point_size=0,
                    text_color='darkred',
                    bold=False
                )
    
    def _add_colored_bbox(self, plotter):
        """Add a colored bounding box to help identify faces."""
        bounds = self.mesh.bounds
        min_b, max_b = bounds[0], bounds[1]
        
        # Create boxes for each face with PyVista
        # Front face (+Y) - RED
        front = pv.Box(bounds=(min_b[0], max_b[0], max_b[1]-0.1, max_b[1], min_b[2], max_b[2]))
        plotter.add_mesh(front, color=BBOX_COLORS['front'], opacity=0.3, show_edges=True, line_width=2)
        center = np.array([(min_b[0]+max_b[0])/2, max_b[1], (min_b[2]+max_b[2])/2])
        plotter.add_point_labels([center], ['Front (+Y)'], font_size=10, bold=True, 
                                 shape_opacity=0.7, shape_color=BBOX_COLORS['front'])
        
        # Back face (-Y) - BLUE
        back = pv.Box(bounds=(min_b[0], max_b[0], min_b[1], min_b[1]+0.1, min_b[2], max_b[2]))
        plotter.add_mesh(back, color=BBOX_COLORS['back'], opacity=0.3, show_edges=True, line_width=2)
        center = np.array([(min_b[0]+max_b[0])/2, min_b[1], (min_b[2]+max_b[2])/2])
        plotter.add_point_labels([center], ['Back (-Y)'], font_size=10, bold=True,
                                 shape_opacity=0.7, shape_color=BBOX_COLORS['back'])
        
        # Left face (-X) - GREEN
        left = pv.Box(bounds=(min_b[0], min_b[0]+0.1, min_b[1], max_b[1], min_b[2], max_b[2]))
        plotter.add_mesh(left, color=BBOX_COLORS['left'], opacity=0.3, show_edges=True, line_width=2)
        center = np.array([min_b[0], (min_b[1]+max_b[1])/2, (min_b[2]+max_b[2])/2])
        plotter.add_point_labels([center], ['Left (-X)'], font_size=10, bold=True,
                                 shape_opacity=0.7, shape_color=BBOX_COLORS['left'])
        
        # Right face (+X) - YELLOW
        right = pv.Box(bounds=(max_b[0]-0.1, max_b[0], min_b[1], max_b[1], min_b[2], max_b[2]))
        plotter.add_mesh(right, color=BBOX_COLORS['right'], opacity=0.3, show_edges=True, line_width=2)
        center = np.array([max_b[0], (min_b[1]+max_b[1])/2, (min_b[2]+max_b[2])/2])
        plotter.add_point_labels([center], ['Right (+X)'], font_size=10, bold=True,
                                 shape_opacity=0.7, shape_color=BBOX_COLORS['right'])
        
        # Top face (+Z) - CYAN
        top = pv.Box(bounds=(min_b[0], max_b[0], min_b[1], max_b[1], max_b[2]-0.1, max_b[2]))
        plotter.add_mesh(top, color=BBOX_COLORS['top'], opacity=0.3, show_edges=True, line_width=2)
        center = np.array([(min_b[0]+max_b[0])/2, (min_b[1]+max_b[1])/2, max_b[2]])
        plotter.add_point_labels([center], ['Top (+Z)'], font_size=10, bold=True,
                                 shape_opacity=0.7, shape_color=BBOX_COLORS['top'])
        
        # Bottom face (-Z) - MAGENTA
        bottom = pv.Box(bounds=(min_b[0], max_b[0], min_b[1], max_b[1], min_b[2], min_b[2]+0.1))
        plotter.add_mesh(bottom, color=BBOX_COLORS['bottom'], opacity=0.3, show_edges=True, line_width=2)
        center = np.array([(min_b[0]+max_b[0])/2, (min_b[1]+max_b[1])/2, min_b[2]])
        plotter.add_point_labels([center], ['Bottom (-Z)'], font_size=10, bold=True,
                                 shape_opacity=0.7, shape_color=BBOX_COLORS['bottom'])
    
    def show_single_view(self, view_type='isometric', show_grid=True):
        """
        Show single view of the mesh.
        
        Args:
            view_type: 'isometric', 'front', 'top', 'side'
            show_grid: Display grid overlay
        """
        plotter = pv.Plotter(window_size=(800, 800))
        
        plotter.add_mesh(self.pv_mesh, color=MESH_COLOR, show_edges=True, edge_color='gray')
        
        if show_grid and self.grid:
            self._add_grid_overlay(plotter, show_labels=True)
        
        # Set camera position
        if view_type == 'isometric':
            plotter.view_isometric()
        elif view_type == 'front':
            plotter.view_xz()
        elif view_type == 'top':
            plotter.view_xy()
        elif view_type == 'side':
            plotter.view_yz()
        
        plotter.add_axes()
        plotter.show()
    
    def export_screenshot(self, filename, view_type='isometric'):
        """Export a screenshot of the mesh."""
        plotter = pv.Plotter(off_screen=True, window_size=(1920, 1080))
        
        plotter.add_mesh(self.pv_mesh, color=MESH_COLOR, show_edges=True)
        
        if self.grid:
            self._add_grid_overlay(plotter, show_labels=True)
        
        if view_type == 'isometric':
            plotter.view_isometric()
        elif view_type == 'front':
            plotter.view_xz()
        elif view_type == 'top':
            plotter.view_xy()
        
        plotter.screenshot(filename)
        print(f"Screenshot saved: {filename}")


def quick_view(mesh, grid=None):
    """Quick single-view visualization."""
    viewer = MeshViewer(mesh, grid)
    viewer.show_single_view(view_type='isometric', show_grid=(grid is not None))
