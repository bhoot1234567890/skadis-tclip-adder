"""Visualization using matplotlib for compatibility."""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from config import MESH_COLOR, GRID_COLOR, BBOX_COLORS


class MeshViewer:
    """Multi-view mesh viewer using matplotlib."""
    
    def __init__(self, mesh, grid=None, figsize=(16, 12), show_bbox=False):
        """
        Initialize viewer with mesh and optional grid.
        
        Args:
            mesh: trimesh.Trimesh object
            grid: SkadisGrid object (optional)
            figsize: Figure size in inches
            show_bbox: Show colored bounding box for face selection
        """
        self.mesh = mesh
        self.grid = grid
        self.figsize = figsize
        self.show_bbox = show_bbox
        
    def _plot_mesh(self, ax, mesh, show_edges=True, alpha=0.7):
        """Plot mesh on given axes."""
        # Create mesh collection
        mesh_alpha = 0.3 if self.show_bbox else alpha
        mesh_data = Poly3DCollection(
            mesh.vertices[mesh.faces],
            alpha=mesh_alpha,
            facecolors='lightblue',
            edgecolors='gray' if show_edges else None,
            linewidths=0.1 if show_edges else 0
        )
        ax.add_collection3d(mesh_data)
        
        # Set axis limits
        bounds = mesh.bounds
        ax.set_xlim([bounds[0][0], bounds[1][0]])
        ax.set_ylim([bounds[0][1], bounds[1][1]])
        ax.set_zlim([bounds[0][2], bounds[1][2]])
        
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        
        # Add bounding box with colored faces if requested
        if self.show_bbox:
            self._add_colored_bbox(ax, bounds)
    
    def _add_colored_bbox(self, ax, bounds):
        """Add a colored bounding box to help identify faces."""
        min_b, max_b = bounds[0], bounds[1]
        
        # Define 6 faces of the bounding box with their colors
        # Each face is defined by 4 corners in counter-clockwise order
        faces_data = [
            # Front face (+Y) - RED
            {
                'vertices': [
                    [min_b[0], max_b[1], min_b[2]],
                    [max_b[0], max_b[1], min_b[2]],
                    [max_b[0], max_b[1], max_b[2]],
                    [min_b[0], max_b[1], max_b[2]]
                ],
                'color': BBOX_COLORS['front'],
                'label': 'Front (+Y)'
            },
            # Back face (-Y) - BLUE
            {
                'vertices': [
                    [min_b[0], min_b[1], min_b[2]],
                    [min_b[0], min_b[1], max_b[2]],
                    [max_b[0], min_b[1], max_b[2]],
                    [max_b[0], min_b[1], min_b[2]]
                ],
                'color': BBOX_COLORS['back'],
                'label': 'Back (-Y)'
            },
            # Left face (-X) - GREEN
            {
                'vertices': [
                    [min_b[0], min_b[1], min_b[2]],
                    [min_b[0], max_b[1], min_b[2]],
                    [min_b[0], max_b[1], max_b[2]],
                    [min_b[0], min_b[1], max_b[2]]
                ],
                'color': BBOX_COLORS['left'],
                'label': 'Left (-X)'
            },
            # Right face (+X) - YELLOW
            {
                'vertices': [
                    [max_b[0], min_b[1], min_b[2]],
                    [max_b[0], min_b[1], max_b[2]],
                    [max_b[0], max_b[1], max_b[2]],
                    [max_b[0], max_b[1], min_b[2]]
                ],
                'color': BBOX_COLORS['right'],
                'label': 'Right (+X)'
            },
            # Top face (+Z) - CYAN
            {
                'vertices': [
                    [min_b[0], min_b[1], max_b[2]],
                    [min_b[0], max_b[1], max_b[2]],
                    [max_b[0], max_b[1], max_b[2]],
                    [max_b[0], min_b[1], max_b[2]]
                ],
                'color': BBOX_COLORS['top'],
                'label': 'Top (+Z)'
            },
            # Bottom face (-Z) - MAGENTA
            {
                'vertices': [
                    [min_b[0], min_b[1], min_b[2]],
                    [max_b[0], min_b[1], min_b[2]],
                    [max_b[0], max_b[1], min_b[2]],
                    [min_b[0], max_b[1], min_b[2]]
                ],
                'color': BBOX_COLORS['bottom'],
                'label': 'Bottom (-Z)'
            }
        ]
        
        # Create all faces as a single collection
        all_faces = [face_data['vertices'] for face_data in faces_data]
        all_colors = [face_data['color'] for face_data in faces_data]
        
        bbox_collection = Poly3DCollection(
            all_faces,
            alpha=0.25,
            facecolors=all_colors,
            edgecolors='black',
            linewidths=1.5
        )
        ax.add_collection3d(bbox_collection)
        
        # Add labels at face centers
        for face_data in faces_data:
            vertices = np.array(face_data['vertices'])
            center = vertices.mean(axis=0)
            ax.text(center[0], center[1], center[2], 
                   face_data['label'],
                   fontsize=9, 
                   fontweight='bold',
                   ha='center',
                   bbox=dict(boxstyle='round', facecolor=face_data['color'], alpha=0.8))
    
    def _add_grid_overlay(self, ax, show_labels=False):
        """Add Skadis grid points and labels to the plot."""
        if not self.grid or not self.grid.slots:
            return
        
        # Extract slot positions
        positions = np.array([slot['position'] for slot in self.grid.slots])
        
        # Plot grid points
        ax.scatter(
            positions[:, 0],
            positions[:, 1],
            positions[:, 2],
            c=GRID_COLOR,
            marker='o',
            s=30,
            alpha=0.8,
            label='Slots'
        )
        
        # Add labels if requested
        if show_labels:
            for slot in self.grid.slots:
                pos = slot['position']
                ax.text(
                    pos[0], pos[1], pos[2],
                    slot['label'],
                    fontsize=6,
                    color='darkred'
                )
    
    def show_multiview(self, show_grid=True, show_section=False, section_axis='z'):
        """
        Display mesh in 3 views: isometric, front, and top.
        
        Args:
            show_grid: Display Skadis grid overlay
            show_section: Display cross-section
            section_axis: Axis for cross-section ('x', 'y', or 'z')
        """
        fig = plt.figure(figsize=self.figsize)
        
        title_suffix = " (Face Selection)" if self.show_bbox else ""
        
        # View 1: Isometric (2.5D)
        ax1 = fig.add_subplot(2, 2, 1, projection='3d')
        ax1.set_title(f'Isometric View (2.5D){title_suffix}', fontsize=14, fontweight='bold')
        self._plot_mesh(ax1, self.mesh)
        
        if show_grid and self.grid:
            self._add_grid_overlay(ax1)
        
        ax1.view_init(elev=30, azim=45)
        
        # View 2: Front View (XZ plane, looking along Y)
        ax2 = fig.add_subplot(2, 2, 2, projection='3d')
        ax2.set_title(f'Front View{title_suffix}', fontsize=14, fontweight='bold')
        self._plot_mesh(ax2, self.mesh)
        
        if show_grid and self.grid:
            self._add_grid_overlay(ax2)
        
        ax2.view_init(elev=0, azim=0)
        
        # View 3: Top View (XY plane, looking down Z)
        ax3 = fig.add_subplot(2, 2, 3, projection='3d')
        ax3.set_title(f'Top View{title_suffix}', fontsize=14, fontweight='bold')
        self._plot_mesh(ax3, self.mesh)
        
        if show_grid and self.grid:
            self._add_grid_overlay(ax3)
        
        ax3.view_init(elev=90, azim=0)
        
        # View 4: Interactive/Detail view with labels
        ax4 = fig.add_subplot(2, 2, 4, projection='3d')
        ax4.set_title(f'Detail View (with slot numbers){title_suffix}', fontsize=14, fontweight='bold')
        self._plot_mesh(ax4, self.mesh, alpha=0.5)
        
        if show_grid and self.grid:
            self._add_grid_overlay(ax4, show_labels=True)
            ax4.legend()
        
        ax4.view_init(elev=30, azim=135)
        
        plt.tight_layout()
        plt.show()
    
    def show_single_view(self, view_type='isometric', show_grid=True):
        """
        Show single view of the mesh.
        
        Args:
            view_type: 'isometric', 'front', 'top', 'side'
            show_grid: Display grid overlay
        """
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        self._plot_mesh(ax, self.mesh)
        
        if show_grid and self.grid:
            self._add_grid_overlay(ax, show_labels=True)
            ax.legend()
        
        # Set camera position
        if view_type == 'isometric':
            ax.view_init(elev=30, azim=45)
            ax.set_title('Isometric View', fontsize=14, fontweight='bold')
        elif view_type == 'front':
            ax.view_init(elev=0, azim=0)
            ax.set_title('Front View', fontsize=14, fontweight='bold')
        elif view_type == 'top':
            ax.view_init(elev=90, azim=0)
            ax.set_title('Top View', fontsize=14, fontweight='bold')
        elif view_type == 'side':
            ax.view_init(elev=0, azim=90)
            ax.set_title('Side View', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.show()
    
    def export_screenshot(self, filename, view_type='isometric', dpi=300):
        """Export a screenshot of the mesh."""
        fig = plt.figure(figsize=(12, 12))
        ax = fig.add_subplot(111, projection='3d')
        
        self._plot_mesh(ax, self.mesh)
        
        if self.grid:
            self._add_grid_overlay(ax, show_labels=True)
        
        if view_type == 'isometric':
            ax.view_init(elev=30, azim=45)
        elif view_type == 'front':
            ax.view_init(elev=0, azim=0)
        elif view_type == 'top':
            ax.view_init(elev=90, azim=0)
        
        plt.savefig(filename, dpi=dpi, bbox_inches='tight')
        plt.close()
        print(f"Screenshot saved: {filename}")


def quick_view(mesh, grid=None):
    """Quick single-view visualization."""
    viewer = MeshViewer(mesh, grid)
    viewer.show_single_view(view_type='isometric', show_grid=(grid is not None))
