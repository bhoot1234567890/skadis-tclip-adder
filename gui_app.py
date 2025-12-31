"""GUI Application for IKEA Skadis T-Clip Mounting Tool."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import proj3d
import numpy as np
from pathlib import Path

from core.mesh_loader import load_mesh
from core.grid_system import SkadisGrid
from core.boolean_ops import process_multiple_slots
from config import BBOX_COLORS, T_CLIP_DEFAULT_DEPTH


class SkadisToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IKEA Skadis T-Clip Mounting Tool")
        self.root.geometry("1400x900")
        
        # State variables
        self.mesh = None
        self.grid = None
        self.tclip_mesh = None
        self.selected_face = None
        self.grid_plane = None
        self.boundary_type = None
        self.selected_slots = set()
        self.result_mesh = None
        
        # Setup UI
        self.setup_ui()
        
    def setup_ui(self):
        """Create the main UI layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls with scrollbar
        left_container = ttk.Frame(main_frame, width=400)
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_container.pack_propagate(False)
        
        # Create canvas and scrollbar for left panel
        canvas = tk.Canvas(left_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right panel - 3D View
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_left_panel(scrollable_frame)
        self.setup_right_panel(right_panel)
        
    def setup_left_panel(self, parent):
        """Setup control panel on the left."""
        # Title
        title = ttk.Label(parent, text="Skadis T-Clip Tool", font=("Arial", 16, "bold"))
        title.pack(pady=(0, 20))
        
        # Step 1: Load Mesh
        step1_frame = ttk.LabelFrame(parent, text="Step 1: Load Mesh", padding=10)
        step1_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(step1_frame, text="Browse Mesh File...", command=self.browse_mesh).pack(fill=tk.X)
        self.mesh_label = ttk.Label(step1_frame, text="No mesh loaded", foreground="gray")
        self.mesh_label.pack(pady=5)
        
        # Step 2: Select Face
        step2_frame = ttk.LabelFrame(parent, text="Step 2: Select Face", padding=10)
        step2_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(step2_frame, text="Click on a colored face:").pack()
        self.face_label = ttk.Label(step2_frame, text="No face selected", foreground="gray")
        self.face_label.pack(pady=5)
        
        # Step 3: Configure Grid
        step3_frame = ttk.LabelFrame(parent, text="Step 3: Grid Offset", padding=10)
        step3_frame.pack(fill=tk.X, pady=5)
        
        # X Offset
        ttk.Label(step3_frame, text="X Offset (mm):").pack(anchor=tk.W)
        self.x_offset = tk.DoubleVar(value=0)
        x_slider = ttk.Scale(step3_frame, from_=-50, to=50, variable=self.x_offset, 
                           command=self.update_grid, orient=tk.HORIZONTAL)
        x_slider.pack(fill=tk.X)
        
        # Y Offset
        ttk.Label(step3_frame, text="Y Offset (mm):").pack(anchor=tk.W)
        self.y_offset = tk.DoubleVar(value=0)
        y_slider = ttk.Scale(step3_frame, from_=-50, to=50, variable=self.y_offset,
                           command=self.update_grid, orient=tk.HORIZONTAL)
        y_slider.pack(fill=tk.X)
        
        # Z Offset
        ttk.Label(step3_frame, text="Z Offset (mm):").pack(anchor=tk.W)
        self.z_offset = tk.DoubleVar(value=0)
        z_slider = ttk.Scale(step3_frame, from_=-50, to=50, variable=self.z_offset,
                           command=self.update_grid, orient=tk.HORIZONTAL)
        z_slider.pack(fill=tk.X)
        
        ttk.Button(step3_frame, text="Reset Offsets", command=self.reset_offsets).pack(pady=5)
        
        # Step 4: Select Slots
        step4_frame = ttk.LabelFrame(parent, text="Step 4: Select Slots", padding=10)
        step4_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(step4_frame, text="Click on grid points to select").pack()
        self.selected_label = ttk.Label(step4_frame, text="0 slots selected", foreground="blue")
        self.selected_label.pack(pady=5)
        ttk.Button(step4_frame, text="Clear Selection", command=self.clear_selection).pack(fill=tk.X)
        
        # View Controls
        view_frame = ttk.LabelFrame(parent, text="View Controls", padding=10)
        view_frame.pack(fill=tk.X, pady=5)
        
        view_buttons = [
            ("Isometric", self.view_isometric),
            ("Front", self.view_front),
            ("Top", self.view_top),
            ("Side", self.view_side),
        ]
        
        for text, command in view_buttons:
            ttk.Button(view_frame, text=text, command=command).pack(fill=tk.X, pady=2)
        
        # Step 5: Cutting Depth
        step5_frame = ttk.LabelFrame(parent, text="Step 5: Cutting Depth", padding=10)
        step5_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(step5_frame, text="Depth (mm):").pack(anchor=tk.W)
        self.depth_var = tk.DoubleVar(value=T_CLIP_DEFAULT_DEPTH)
        depth_spinner = ttk.Spinbox(step5_frame, from_=1, to=50, textvariable=self.depth_var, width=10)
        depth_spinner.pack()
        
        # Step 6: Process
        step6_frame = ttk.LabelFrame(parent, text="Step 6: Process", padding=10)
        step6_frame.pack(fill=tk.X, pady=5)
        
        self.process_btn = ttk.Button(step6_frame, text="Cut Holes & Insert T-Clips", 
                                     command=self.process_mesh, state=tk.DISABLED)
        self.process_btn.pack(fill=tk.X, pady=5)
        
        self.export_btn = ttk.Button(step6_frame, text="Export (STL/STEP)", 
                                    command=self.export_stl, state=tk.DISABLED)
        self.export_btn.pack(fill=tk.X)
        
        # Status
        self.status_label = ttk.Label(parent, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
    def setup_right_panel(self, parent):
        """Setup 3D visualization on the right."""
        # Create matplotlib figure
        self.fig = Figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        toolbar = NavigationToolbar2Tk(self.canvas, parent)
        toolbar.update()
        
        # Connect click event
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        
    def browse_mesh(self):
        """Open file browser to select mesh."""
        filename = filedialog.askopenfilename(
            title="Select Mesh File",
            filetypes=[
                ("3D Files", "*.stl *.step *.stp *.obj"),
                ("STL Files", "*.stl"),
                ("STEP Files", "*.step *.stp"),
                ("OBJ Files", "*.obj"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            try:
                self.status_label.config(text="Loading mesh...")
                self.root.update()
                
                self.mesh = load_mesh(filename)
                self.mesh_label.config(text=Path(filename).name, foreground="green")
                self.status_label.config(text=f"Loaded: {len(self.mesh.vertices)} vertices")
                
                # Load T-clip if exists
                self.load_tclip()
                
                # Show mesh with colored bbox
                self.show_face_selection()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load mesh:\n{e}")
                self.status_label.config(text="Error loading mesh")
    
    def load_tclip(self):
        """Load T-clip geometry."""
        tclip_paths = [Path("Clip Seat.step"), Path("models/t_clip_slot.stl")]
        for path in tclip_paths:
            if path.exists():
                try:
                    self.tclip_mesh = load_mesh(str(path))
                    # Scale and center
                    dims = self.tclip_mesh.bounds[1] - self.tclip_mesh.bounds[0]
                    if max(dims) < 1.0:
                        self.tclip_mesh.apply_scale(1000.0)
                        self.tclip_mesh.apply_translation(-self.tclip_mesh.centroid)
                    
                    # Try harder to fix the mesh
                    if not self.tclip_mesh.is_watertight:
                        print(f"T-clip is not watertight, attempting repairs...")
                        # Fill holes
                        self.tclip_mesh.fill_holes()
                        # Remove duplicate/degenerate faces
                        self.tclip_mesh.remove_duplicate_faces()
                        self.tclip_mesh.remove_degenerate_faces()
                        # Merge vertices
                        self.tclip_mesh.merge_vertices()
                        # Try to fix normals
                        self.tclip_mesh.fix_normals()
                        
                        if self.tclip_mesh.is_watertight:
                            print(f"✓ T-clip repaired successfully")
                        else:
                            print(f"⚠ T-clip still not watertight, boolean operations may fail")
                    
                    self.status_label.config(text=f"T-clip loaded from {path.name}")
                    return
                except Exception as e:
                    print(f"Failed to load T-clip from {path}: {e}")
                    pass
    
    def show_face_selection(self):
        """Display mesh with colored bounding box faces."""
        self.ax.clear()
        
        if self.mesh is None:
            return
        
        # Plot mesh (transparent)
        mesh_collection = Poly3DCollection(
            self.mesh.vertices[self.mesh.faces],
            alpha=0.1,
            facecolors='lightblue',
            edgecolors='gray',
            linewidths=0.1
        )
        self.ax.add_collection3d(mesh_collection)
        
        # Add colored bounding box
        bounds = self.mesh.bounds
        min_b, max_b = bounds[0], bounds[1]
        
        # Store face data for click detection
        self.face_data = {
            'front': {'vertices': np.array([[min_b[0], max_b[1], min_b[2]], [max_b[0], max_b[1], min_b[2]], 
                           [max_b[0], max_b[1], max_b[2]], [min_b[0], max_b[1], max_b[2]]]),
                 'color': BBOX_COLORS['front'], 'label': 'Front (+Y)', 'plane': 'xz', 'boundary': 'max_y', 'cut_normal': np.array([0, -1, 0])},
            'back': {'vertices': np.array([[min_b[0], min_b[1], min_b[2]], [min_b[0], min_b[1], max_b[2]],
                          [max_b[0], min_b[1], max_b[2]], [max_b[0], min_b[1], min_b[2]]]),
                'color': BBOX_COLORS['back'], 'label': 'Back (-Y)', 'plane': 'xz', 'boundary': 'min_y', 'cut_normal': np.array([0, 1, 0])},
            'left': {'vertices': np.array([[min_b[0], min_b[1], min_b[2]], [min_b[0], max_b[1], min_b[2]],
                          [min_b[0], max_b[1], max_b[2]], [min_b[0], min_b[1], max_b[2]]]),
                'color': BBOX_COLORS['left'], 'label': 'Left (-X)', 'plane': 'yz', 'boundary': 'min_x', 'cut_normal': np.array([1, 0, 0])},
            'right': {'vertices': np.array([[max_b[0], min_b[1], min_b[2]], [max_b[0], min_b[1], max_b[2]],
                           [max_b[0], max_b[1], max_b[2]], [max_b[0], max_b[1], min_b[2]]]),
                 'color': BBOX_COLORS['right'], 'label': 'Right (+X)', 'plane': 'yz', 'boundary': 'max_x', 'cut_normal': np.array([-1, 0, 0])},
            'top': {'vertices': np.array([[min_b[0], min_b[1], max_b[2]], [min_b[0], max_b[1], max_b[2]],
                         [max_b[0], max_b[1], max_b[2]], [max_b[0], min_b[1], max_b[2]]]),
               'color': BBOX_COLORS['top'], 'label': 'Top (+Z)', 'plane': 'xy', 'boundary': 'max_z', 'cut_normal': np.array([0, 0, -1])},
            'bottom': {'vertices': np.array([[min_b[0], min_b[1], min_b[2]], [max_b[0], min_b[1], min_b[2]],
                            [max_b[0], max_b[1], min_b[2]], [min_b[0], max_b[1], min_b[2]]]),
                  'color': BBOX_COLORS['bottom'], 'label': 'Bottom (-Z)', 'plane': 'xy', 'boundary': 'min_z', 'cut_normal': np.array([0, 0, 1])}
        }
        
        # Draw faces
        for face_name, face_info in self.face_data.items():
            face_poly = Poly3DCollection([face_info['vertices']], alpha=0.3, 
                                        facecolors=face_info['color'], edgecolors='black', linewidths=2)
            self.ax.add_collection3d(face_poly)
            
            # Add label
            center = face_info['vertices'].mean(axis=0)
            self.ax.text(center[0], center[1], center[2], face_info['label'],
                        fontsize=10, fontweight='bold', ha='center',
                        bbox=dict(boxstyle='round', facecolor=face_info['color'], alpha=0.7))
        
        # Set limits
        self.ax.set_xlim([min_b[0], max_b[0]])
        self.ax.set_ylim([min_b[1], max_b[1]])
        self.ax.set_zlim([min_b[2], max_b[2]])
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_zlabel('Z (mm)')
        self.ax.set_title('Click on a colored face to select mounting surface')
        
        self.canvas.draw()
    
    def on_canvas_click(self, event):
        """Handle click events on the 3D canvas."""
        if event.inaxes != self.ax:
            return
        
        # Face selection mode
        if self.mesh and not self.grid:
            # User is selecting a face - we'll use a simple proximity check
            # This is a simplified version; a real implementation would do proper ray-face intersection
            messagebox.showinfo("Face Selection", 
                              "Please use the toolbar to rotate the view, then click near the face center.\n\n" +
                              "Or use keyboard shortcuts:\n" +
                              "F - Front (+Y)\n" +
                              "B - Back (-Y)\n" +
                              "L - Left (-X)\n" +
                              "R - Right (+X)\n" +
                              "T - Top (+Z)\n" +
                              "M - Bottom (-Z)")
        
        # Slot selection mode
        elif self.grid and self.grid.slots:
            self.select_nearby_slot(event)
    
    def select_face(self, face_name):
        """Select a face for grid placement."""
        if face_name in self.face_data:
            face_info = self.face_data[face_name]
            self.selected_face = face_name
            self.grid_plane = face_info['plane']
            self.boundary_type = face_info['boundary']
            self.cut_normal = face_info.get('cut_normal', None)
            self.face_label.config(text=face_info['label'], foreground="green")
            # Generate grid
            self.generate_grid()
    
    def generate_grid(self):
        """Generate Skadis grid on selected face."""
        if not self.mesh or not self.grid_plane:
            return
        
        offset = [self.x_offset.get(), self.y_offset.get(), self.z_offset.get()]
        self.grid = SkadisGrid(self.mesh, offset=offset, use_mesh_center=True, 
                              grid_plane=self.grid_plane, boundary_type=self.boundary_type)
        
        self.selected_slots.clear()
        self.show_grid()
        self.process_btn.config(state=tk.DISABLED)
    
    def update_grid(self, *args):
        """Update grid when offset sliders change."""
        if self.grid:
            self.generate_grid()
    
    def reset_offsets(self):
        """Reset all offset sliders to zero."""
        self.x_offset.set(0)
        self.y_offset.set(0)
        self.z_offset.set(0)
    
    def show_grid(self):
        """Display mesh with grid overlay."""
        if not self.mesh or not self.grid:
            return
        
        self.ax.clear()
        
        # Plot mesh
        mesh_collection = Poly3DCollection(
            self.mesh.vertices[self.mesh.faces],
            alpha=0.3,
            facecolors='lightblue',
            edgecolors='gray',
            linewidths=0.1
        )
        self.ax.add_collection3d(mesh_collection)
        
        # Plot grid slots
        positions = np.array([slot['position'] for slot in self.grid.slots])
        
        # Plot all slots with better visibility
        for i, slot in enumerate(self.grid.slots):
            pos = slot['position']
            is_selected = slot['index'] in self.selected_slots
            
            # Main marker
            color = 'red' if is_selected else 'lime'
            size = 200 if is_selected else 100
            
            self.ax.scatter([pos[0]], [pos[1]], [pos[2]], 
                          c=color, marker='o', s=size, alpha=0.9, 
                          edgecolors='black', linewidths=2)
            
            # Label
            label_color = 'darkred' if is_selected else 'darkgreen'
            self.ax.text(pos[0], pos[1], pos[2], slot['label'], 
                        fontsize=8, color=label_color, fontweight='bold',
                        ha='center', va='bottom')
        
        # Set limits
        bounds = self.mesh.bounds
        self.ax.set_xlim([bounds[0][0], bounds[1][0]])
        self.ax.set_ylim([bounds[0][1], bounds[1][1]])
        self.ax.set_zlim([bounds[0][2], bounds[1][2]])
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_zlabel('Z (mm)')
        self.ax.set_title(f'Click on grid points to select ({len(self.selected_slots)} selected)')
        
        self.canvas.draw()
        self.selected_label.config(text=f"{len(self.selected_slots)} slots selected")
    
    def select_nearby_slot(self, event):
        """Select slot near click position using proper 3D projection."""
        if not self.grid or event.xdata is None or event.ydata is None:
            return
        
        # Get click position in data coordinates
        click_x, click_y = event.xdata, event.ydata
        
        # Find nearest slot by projecting 3D points to 2D screen space
        min_dist = float('inf')
        nearest_slot = None
        
        for slot in self.grid.slots:
            pos = slot['position']
            
            # Project 3D point to 2D display coordinates
            try:
                x2d, y2d, _ = proj3d.proj_transform(pos[0], pos[1], pos[2], self.ax.get_proj())
                
                # Calculate distance in 2D projected space
                dist = np.sqrt((x2d - click_x)**2 + (y2d - click_y)**2)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_slot = slot
                    
            except Exception as e:
                print(f"Projection error for slot {slot['index']}: {e}")
                continue
        
        # Get axis scale for adaptive threshold
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        scale = max(xlim[1] - xlim[0], ylim[1] - ylim[0])
        threshold = scale * 0.05  # 5% of axis range
        
        # Toggle selection if close enough
        if nearest_slot and min_dist < threshold:
            slot_idx = nearest_slot['index']
            print(f"Clicked on slot {slot_idx} (distance: {min_dist:.2f})")
            
            if slot_idx in self.selected_slots:
                self.selected_slots.remove(slot_idx)
            else:
                self.selected_slots.add(slot_idx)
            
            self.show_grid()
            
            if self.selected_slots:
                self.process_btn.config(state=tk.NORMAL)
            else:
                self.process_btn.config(state=tk.DISABLED)
        else:
            print(f"Click too far from any slot (min distance: {min_dist:.2f}, threshold: {threshold:.2f})")
    
    def clear_selection(self):
        """Clear all selected slots."""
        self.selected_slots.clear()
        if self.grid:
            self.show_grid()
        self.process_btn.config(state=tk.DISABLED)
    
    def view_isometric(self):
        """Set isometric view."""
        self.ax.view_init(elev=30, azim=45)
        self.canvas.draw()
    
    def view_front(self):
        """Set front view."""
        self.ax.view_init(elev=0, azim=0)
        self.canvas.draw()
    
    def view_top(self):
        """Set top view."""
        self.ax.view_init(elev=90, azim=0)
        self.canvas.draw()
    
    def view_side(self):
        """Set side view."""
        self.ax.view_init(elev=0, azim=90)
        self.canvas.draw()
    
    def process_mesh(self):
        """Process mesh: cut holes and insert T-clips."""
        if not self.mesh or not self.selected_slots:
            return
        try:
            self.status_label.config(text="Processing...")
            self.root.update()
            # Get selected slot positions
            selected_slot_objs = [s for s in self.grid.slots if s['index'] in self.selected_slots]
            slot_positions = [slot['position'] for slot in selected_slot_objs]
            depth = self.depth_var.get()
            cut_normal = getattr(self, 'cut_normal', None)
            print(f"[DEBUG] Slot positions: {slot_positions}")
            print(f"[DEBUG] Depth: {depth}")
            print(f"[DEBUG] Grid plane: {self.grid_plane}")
            print(f"[DEBUG] Cut normal: {cut_normal}")
            # Process
            self.result_mesh = process_multiple_slots(
                self.mesh,
                slot_positions,
                depth,
                self.tclip_mesh,
                self.grid_plane,
                skip_holes=False,
                cut_normal=cut_normal
            )
            # Show result
            self.show_result()
            self.export_btn.config(state=tk.NORMAL)
            self.status_label.config(text=f"Processed {len(self.selected_slots)} slots")
        except Exception as e:
            messagebox.showerror("Error", f"Processing failed:\n{e}")
            self.status_label.config(text="Error during processing")
    
    def show_result(self):
        """Display the result mesh."""
        if not self.result_mesh:
            return
        
        self.ax.clear()
        
        mesh_collection = Poly3DCollection(
            self.result_mesh.vertices[self.result_mesh.faces],
            alpha=0.7,
            facecolors='lightgreen',
            edgecolors='gray',
            linewidths=0.1
        )
        self.ax.add_collection3d(mesh_collection)
        
        bounds = self.result_mesh.bounds
        self.ax.set_xlim([bounds[0][0], bounds[1][0]])
        self.ax.set_ylim([bounds[0][1], bounds[1][1]])
        self.ax.set_zlim([bounds[0][2], bounds[1][2]])
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_zlabel('Z (mm)')
        self.ax.set_title('Result Preview')
        
        self.canvas.draw()
    
    def export_stl(self):
        """Export result to STL or STEP file."""
        if not self.result_mesh:
            return
        
        # Ask user for format
        format_choice = messagebox.askyesnocancel(
            "Export Format",
            "Export as STL?\n\nYes = STL (standard)\nNo = STEP (better for non-watertight)\nCancel = abort"
        )
        
        if format_choice is None:  # Cancel
            return
        
        # Choose file extension based on choice
        if format_choice:  # Yes = STL
            file_types = [("STL Files", "*.stl"), ("All Files", "*.*")]
            default_ext = ".stl"
            initial_file = "output_with_tclip.stl"
        else:  # No = STEP
            file_types = [("STEP Files", "*.step *.stp"), ("All Files", "*.*")]
            default_ext = ".step"
            initial_file = "output_with_tclip.step"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=file_types,
            initialfile=initial_file
        )
        
        if filename:
            try:
                self.result_mesh.export(filename)
                messagebox.showinfo("Success", f"Exported to:\n{filename}")
                self.status_label.config(text=f"Exported: {Path(filename).name}")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed:\n{e}")


def main():
    """Run the GUI application."""
    root = tk.Tk()
    app = SkadisToolGUI(root)
    
    # Keyboard shortcuts for face selection
    root.bind('f', lambda e: app.select_face('front'))
    root.bind('b', lambda e: app.select_face('back'))
    root.bind('l', lambda e: app.select_face('left'))
    root.bind('r', lambda e: app.select_face('right'))
    root.bind('t', lambda e: app.select_face('top'))
    root.bind('m', lambda e: app.select_face('bottom'))
    
    root.mainloop()


if __name__ == "__main__":
    main()
