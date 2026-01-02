# SDL + Vulkan Port Guide: IKEA Skadis T-Clip Mounting Tool

## Table of Contents
1. [Application Overview](#application-overview)
2. [Core Functionality Breakdown](#core-functionality-breakdown)
3. [Technical Requirements](#technical-requirements)
4. [Architecture Analysis](#architecture-analysis)
5. [SDL + Vulkan Component Mapping](#sdl--vulkan-component-mapping)
6. [Required Libraries and Dependencies](#required-libraries-and-dependencies)
7. [Implementation Roadmap](#implementation-roadmap)
8. [Code Examples](#code-examples)

---

## Application Overview

### Purpose
This is a **3D CAD tool** for adding T-clip mounting slots to 3D-printed tool holders designed for IKEA Skadis pegboards. The tool generates a staggered grid overlay matching the Skadis pegboard pattern (20mm × 40mm spacing), allows users to select mounting points, cuts holes, and optionally inserts T-clip geometry for parametric mounting.

### Target Users
- 3D printing enthusiasts
- Makers who use IKEA Skadis pegboards
- Users designing custom tool holders that need mounting slots

### Input Files
- **Mesh files**: STL, STEP, STP, OBJ formats (3D models of tool holders)
- **T-clip geometry**: Optional STEP/STL file for T-clip insertion

### Output Files
- Modified mesh with T-clip mounting slots (STL or STEP format)

---

## Core Functionality Breakdown

### 1. Mesh Loading and Processing

**What it does:**
- Loads 3D mesh files from disk (STL/STEP/OBJ)
- Converts file formats to internal mesh representation
- Automatically repairs non-watertight meshes
- Computes bounding boxes, centroids, and geometric properties
- Handles mesh scenes (multiple objects) by merging into single mesh

**Python Implementation Location:** [`core/mesh_loader.py`](core/mesh_loader.py)

**Key Operations:**
```python
# Current implementation uses:
- trimesh.load() for file I/O
- Trimesh objects for internal representation
- Mesh repair pipeline:
  * fill_holes() - closes gaps in mesh
  * remove_duplicate_faces() - eliminates redundant geometry
  * merge_vertices() - combines coincident vertices
  * fix_normals() - ensures consistent face orientation
```

**Critical Requirements for Port:**
- Need C++ mesh library with:
  - STL/STEP/OBJ file parsing
  - Half-edge or similar data structure
  - Mesh repair algorithms
  - Boolean operations (union, difference, intersection)
  - Watertightness checking and repair

---

### 2. Grid System Generation

**What it does:**
- Generates a **staggered grid** matching IKEA Skadis pegboard pattern
- Grid spacings: 20mm horizontal, 40mm vertical
- Every other column is offset by 20mm (staggered pattern)
- Grid is centered on selected mesh face
- Supports 3 different grid orientations (XY, XZ, YZ planes)
- Grid points represent potential T-clip mounting locations

**Python Implementation Location:** [`core/grid_system.py`](core/grid_system.py)

**Mathematical Specification:**
```
Horizontal spacing: 20mm
Vertical spacing: 40mm
Stagger offset: 20mm (applied to every even column)

Grid origin:
- In plane dimensions (u, v): centered on mesh face
- In depth dimension (w): at mesh boundary (face surface)

Grid plane orientations:
- XY plane: for top/bottom faces (Z = ± boundary)
- XZ plane: for front/back faces (Y = ± boundary)
- YZ plane: for left/right faces (X = ± boundary)
```

**Key Data Structure:**
```python
# Each grid slot contains:
slot = {
    'index': int,                    # Unique slot identifier
    'position': np.array([x,y,z]),   # 3D coordinates in mm
    'label': str,                    # Display label (e.g., "A1", "B2")
    'grid_coords': (col, row)        # Grid indices
}
```

**Critical Requirements for Port:**
- 3D grid generation algorithm
- Coordinate system transformation for different planes
- Mesh boundary detection (min/max X, Y, Z)
- 2D-to-3D coordinate mapping

---

### 3. 3D Visualization and Rendering

**What it does:**
- Renders 3D mesh with transparency
- Displays colored bounding box faces for selection
- Overlays grid points as interactive markers
- Supports camera rotation, pan, and zoom
- Multi-view presets: isometric, front, top, side
- Real-time updates when parameters change
- Interactive 3D clicking (ray casting/screen projection)

**Python Implementation Locations:**
- [`gui_app.py`](gui_app.py#L176-191) - Matplotlib integration
- [`visualization/viewer_mpl.py`](visualization/viewer_mpl.py) - Matplotlib viewer
- [`visualization/viewer.py`](visualization/viewer.py) - PyVista viewer

**Rendering Pipeline:**
```
1. Clear canvas/framebuffer
2. Set up 3D projection (perspective or orthographic)
3. Apply camera transforms (view matrix)
4. Draw mesh:
   - For each face in mesh:
     * Transform vertices to screen space
     * Apply lighting (optional)
     * Render with transparency (alpha blending)
5. Draw grid overlay:
   - For each grid point:
     * Render sphere/circle marker
     * Render text label
     * Highlight if selected
6. Draw bounding box faces (optional, for selection mode)
7. Swap buffers
```

**Visual Elements:**
- **Main mesh**: Light blue, 30% alpha, gray edges
- **Grid markers**: Green (unselected), Red (selected), with black outlines
- **Text labels**: Slot identifiers (A1, B2, etc.)
- **Bounding box**: Color-coded faces (red=front, blue=back, etc.)

**Critical Requirements for Port:**
- 3D rendering pipeline (Vulkan graphics)
- Vertex/index buffer management
- Shader programs for mesh rendering
- Camera system (orbit controls)
- Lighting calculations (Phong or simplified)
- Text rendering for labels
- Transparency/alpha blending
- Mouse input → 3D ray casting for picking

---

### 4. Face Selection System

**What it does:**
- Presents 6 faces of mesh bounding box (front, back, left, right, top, bottom)
- Each face is color-coded for visual identification
- User clicks on a face to select mounting surface
- Keyboard shortcuts (F, B, L, R, T, M) for quick selection
- Determines grid plane orientation and cutting direction

**Python Implementation Location:** [`gui_app.py`](gui_app.py#L262-326)

**Face Mapping:**
```python
Face      | Color   | Plane | Boundary | Cut Normal  | Shortcut
----------|---------|-------|----------|-------------|---------
Front     | Red     | XZ    | max_y    | [0, -1, 0]  | F
Back      | Blue    | XZ    | min_y    | [0, 1, 0]   | B
Left      | Green   | YZ    | min_x    | [1, 0, 0]   | L
Right     | Yellow  | YZ    | max_x    | [-1, 0, 0]  | R
Top       | Cyan    | XY    | max_z    | [0, 0, -1]  | T
Bottom    | Magenta | XY    | min_z    | [0, 0, 1]   | M
```

**Critical Concept:**
- `cut_normal` vector points **INTO** the mesh (opposite face normal)
- This determines direction of hole cutting and T-clip orientation
- Grid plane (XY/XZ/YZ) determines 2D coordinate system for grid generation

**Critical Requirements for Port:**
- 3D picking/ray casting (mouse click → 3D face)
- Bounding box calculation
- Visual representation of planes
- Keyboard event handling
- State management for selected face

---

### 5. Interactive Slot Selection

**What it does:**
- Displays grid points as interactive 3D markers
- User clicks on grid points to toggle selection
- Projects 3D points to 2D screen space for click detection
- Adaptive threshold based on zoom level
- Visual feedback: selected points turn red, unselected are green
- Shows count of selected slots
- Clear selection button

**Python Implementation Location:** [`gui_app.py`](gui_app.py#L439-492)

**Algorithm:**
```
1. User clicks at screen coordinates (mouse_x, mouse_y)
2. For each grid slot:
   a. Project 3D position to 2D screen space
   b. Calculate distance from click to projected point
   c. Track nearest slot
3. If nearest distance < adaptive_threshold:
   - Toggle slot selection state
   - Update visual rendering
4. Update UI counters and enable/disable process button
```

**Projection Math:**
```python
# 3D world → 2D screen
x2d, y2d, _ = proj3d.proj_transform(x, y, z, view_projection_matrix)

# Distance in screen space
distance = sqrt((x2d - click_x)^2 + (y2d - click_y)^2)

# Adaptive threshold
scale = max(xlim_range, ylim_range)
threshold = scale * 0.05  # 5% of visible range
```

**Critical Requirements for Port:**
- 3D-to-2D projection (world → screen space)
- View-projection matrix multiplication
- Euclidean distance calculation
- Adaptive threshold based on camera zoom
- Click event handling with coordinates
- Set data structure for selected slots (O(1) lookup)

---

### 6. Boolean Operations (Hole Cutting)

**What it does:**
- Cuts cylindrical holes in mesh at selected grid positions
- Cylinder diameter: 28.284mm (√2 × 20mm, allows 45° T-clip rotation)
- Cylinder depth: User-configurable (default 10mm)
- Cutting direction: Along `cut_normal` vector (points INTO mesh)
- Uses multiple boolean engines with fallback chain
- Processes all holes FIRST before T-clip insertion (stability)

**Python Implementation Location:** [`core/boolean_ops.py`](core/boolean_ops.py)

**Boolean Operation Pipeline:**
```
1. Create cutting cylinder geometry
2. Align cylinder Z-axis with cut_normal vector
3. Position cylinder base at grid point
4. Perform boolean difference: mesh - cylinder
5. Repeat for all selected slots
6. Try multiple engines until one succeeds:
   a. manifold3d (fastest, most reliable)
   b. OpenSCAD (scad backend)
   c. Blender (blender backend)
   d. Concatenation (simple merge, fallback only)
```

**Cutting Cylinder Specification:**
```
Geometry: Right circular cylinder
Diameter: 28.284 mm
Height: User-specified depth (default 10mm)
Orientation: Z-axis aligned with cut_normal
Position: Base centered at grid point, extends INTO mesh
```

**Critical Requirements for Port:**
- CSG (Constructive Solid Geometry) library
- Boolean operations: difference, union, intersection
- Mesh-mesh intersection algorithms
- Robust handling of non-manifold geometry
- Multiple engine fallback architecture

**C++ Libraries for Boolean Ops:**
- **manifold3d** (recommended) - Modern, fast, robust
- **CGAL** - Comprehensive computational geometry
- **Carve** - CSG library
- **libigl** - Geometry processing with boolean support
- **OpenVDB** - Volume-based boolean operations

---

### 7. T-Clip Insertion

**What it does:**
- Loads T-clip geometry from file (STEP/STL)
- Orients T-clip to align with grid face
- Inserts T-clip into cut holes
- T-clip base sits flush with mesh surface
- T-clip thin dimension (Y-axis) points perpendicular to face
- Optional auto-scaling if model is in wrong units

**Python Implementation Location:** [`core/boolean_ops.py`](core/boolean_ops.py) (`insert_tclip()` function)

**T-Clip Orientation Algorithm:**
```python
1. Load T-clip mesh (assumes centered at origin)
2. Detect if too small (< 1mm) → scale by 1000× (meters to mm)
3. Re-center to origin after scaling
4. Repair mesh if not watertight:
   - fill_holes()
   - remove_duplicate_faces()
   - merge_vertices()
   - fix_normals()
5. Align T-clip Y-axis (thin dimension) with NEGATIVE cut_normal
   - This makes base point OUT of mesh
6. Position T-clip:
   - MIN bound exactly at face position (flush mount)
7. Perform boolean union: mesh + tclip
```

**Critical Concept:**
- T-clip is modeled at origin with specific axis orientation
- Y-axis = thin dimension (must be perpendicular to grid plane)
- After transformation: T-clip base sits at mesh surface, points outward

**Critical Requirements for Port:**
- Mesh transformation pipeline:
  - Translation
  - Rotation (quaternion or axis-angle)
  - Scaling
- Axis alignment (mesh rotation to match direction vectors)
- Mesh union operations
- Watertight mesh repair

---

### 8. Parameter Adjustment System

**What it does:**
- Provides sliders for X, Y, Z offset adjustment
- Offsets range: -50mm to +50mm
- Real-time grid regeneration when sliders move
- Reset button to zero all offsets
- Depth spinner for cutting depth (1-50mm)
- All parameters update visualization immediately

**Python Implementation Location:** [`gui_app.py`](gui_app.py#L101-126)

**Offset Parameters:**
```python
x_offset: Horizontal shift in plane's X dimension
y_offset: Vertical shift in plane's Y dimension
z_offset: Depth shift (perpendicular to face)
depth:   Cutting depth for T-clip holes (1-50mm)
```

**Critical Requirements for Port:**
- Slider widgets (or custom implementation)
- Real-time event handling (slider drag → immediate update)
- Floating-point parameter storage
- Grid regeneration on parameter change
- State management for current offset values

---

### 9. File I/O Operations

**What it does:**
- File browser dialog for mesh selection
- File browser dialog for T-clip selection
- File save dialog for result export
- Format selection (STL vs STEP)
- Error handling for invalid files
- Progress feedback during loading/saving

**Python Implementation Location:** [`gui_app.py`](gui_app.py#L193-223, 582-618)

**Supported Formats:**
```
Input:
- STL (Stereolithography) - Binary or ASCII
- STEP/STP (ISO 10303) - NURBS-based CAD format
- OBJ (Wavefront) - Simple mesh format

Output:
- STL - Standard mesh format
- STEP - Better for non-watertight geometry
```

**Critical Requirements for Port:**
- Native file dialogs:
  - Windows: COM/IFileDialog (WinAPI)
  - macOS: Cocoa (NSSavePanel/NSOpenPanel)
  - Linux: GTK (GtkFileChooser)
- File format parsers/writers:
  - STL parsing (binary and ASCII)
  - STEP parsing (complex NURBS format)
  - OBJ parsing (simple text format)
- Error handling for malformed files
- Async loading with progress callbacks (large files)

---

### 10. GUI Framework and Layout

**What it does:**
- Two-panel layout: controls (left) + 3D view (right)
- Scrollable control panel (for many controls)
- Collapsible sections with labeled frames
- Status bar at bottom
- View control buttons (isometric, front, top, side)
- Process and export buttons with state management

**Python Implementation Location:** [`gui_app.py`](gui_app.py#L40-77)

**Layout Hierarchy:**
```
Main Window (1400×900)
├── Left Panel (400px, scrollable)
│   ├── Step 1: Load Mesh
│   ├── Step 2: Select Face
│   ├── Step 3: Grid Offset
│   │   ├── X Offset Slider
│   │   ├── Y Offset Slider
│   │   ├── Z Offset Slider
│   │   └── Reset Button
│   ├── Step 4: Select Slots
│   ├── View Controls
│   ├── Step 5: Cutting Depth
│   ├── Step 6: Process
│   └── Status Bar
└── Right Panel (flexible)
    └── 3D Canvas (matplotlib)
```

**UI Components:**
- Labels (static text)
- Buttons (clickable actions)
- Sliders (continuous value adjustment)
- Spinboxes (numeric input)
- Scrollable canvas (overflow handling)
- Progress/status indicators
- Color-coded feedback

**Critical Requirements for Port:**
- UI layout system (immediate or retained mode)
- Scrollable container widget
- Event handling (click, drag, scroll)
- Widget state management (enabled/disabled)
- Keyboard shortcuts
- Window management (resize, minimize, maximize)

---

## Technical Requirements

### Programming Language
- **Current**: Python 3.7+
- **Recommended for Port**: C++17 or C++20
  - Better performance for mesh operations
  - Direct Vulkan API access
  - Lower-level memory management
  - Wider ecosystem of graphics libraries

### Build System
- **CMake** (cross-platform)
- **vcpkg** or **Conan** for dependency management
- Platform-specific scripts for final packaging

---

## Architecture Analysis

### Current Python Architecture
```
┌─────────────────────────────────────┐
│   GUI Layer (Tkinter + Matplotlib)  │
│   - Window management               │
│   - Event handling                  │
│   - UI controls                     │
│   - 3D rendering (matplotlib)       │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Application Logic (gui_app.py)    │
│   - State management                │
│   - Workflow coordination           │
│   - User interaction                │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Core Modules                      │
│   ├── grid_system.py                │
│   ├── boolean_ops.py                │
│   └── mesh_loader.py                │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   External Libraries                │
│   ├── trimesh (mesh I/O, booleans)  │
│   ├── numpy (numerical ops)         │
│   ├── scipy (mesh repair)           │
│   └── manifold3d (fast booleans)    │
└─────────────────────────────────────┘
```

### Proposed C++ / Vulkan Architecture
```
┌─────────────────────────────────────┐
│   Vulkan Rendering Layer            │
│   ├── Swapchain management          │
│   ├── Command buffers               │
│   ├── Pipeline state objects        │
│   ├── Descriptor sets               │
│   └── Shader modules                │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   SDL2 Layer                        │
│   - Window creation                 │
│   - Event loop                      │
│   - Input handling                  │
│   - Platform abstraction            │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   UI System (Dear ImGui or custom)  │
│   - Widget rendering                │
│   - Layout management               │
│   - Event routing                   │
│   - File dialogs (native API)       │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Application Logic                 │
│   ├── MeshManager                   │
│   ├── GridSystem                    │
│   ├── BooleanOperations             │
│   └── SceneManager                  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Core Libraries                    │
│   ├── manifold3d (boolean ops)      │
│   ├── cgal or igl (geometry)        │
│   ├── assimp (mesh I/O)             │
│   ├── glm (math library)            │
│   └── spdlog (logging)              │
└─────────────────────────────────────┘
```

---

## SDL + Vulkan Component Mapping

### What SDL2 Provides

**Window Management:**
- Cross-platform window creation
- Window resizing, positioning
- OpenGL/Vulkan/DirectX surface creation
- Multi-monitor support

**Input Handling:**
- Keyboard events (keydown, keyup, text input)
- Mouse events (motion, buttons, wheel)
- Joystick/gamepad support (not needed here)
- Touch events (for future tablet support)

**Platform Abstraction:**
- Unified API across Windows/macOS/Linux
- Thread management
- Timer functions
- File system abstraction (basic)

**Audio (not needed for this app):**
- Sound playback
- Audio capture

**What SDL2 Does NOT Provide:**
- Complex UI widgets (no sliders, buttons beyond basic)
- 3D rendering (use Vulkan directly)
- File dialogs (use native APIs or ImGui)
- Advanced text rendering

### What Vulkan Provides

**Graphics Pipeline:**
- Vertex/fragment shaders
- Geometry/tessellation shaders (optional)
- Compute shaders (for mesh processing)
- Graphics pipeline configuration

**Resource Management:**
- Buffers (vertex, index, uniform)
- Images (textures, depth stencil)
- Memory allocation and management
- Descriptor sets for shader bindings

**Rendering Control:**
- Command buffers (recording rendering commands)
- Render passes (begin/end rendering)
- Framebuffer management
- Synchronization (fences, semaphores)

**Platform-Specific Integration:**
- Windows integration (Win32 surface)
- macOS integration (MoltenVK - Vulkan → Metal translation)
- Linux integration (XCB, Xlib, Wayland)

**What Vulkan Does NOT Provide:**
- Window creation (use SDL)
- Input handling (use SDL)
- File I/O (use C++ std or SDL)
- UI widgets (use ImGui or custom)

### What You Must Build Yourself

**1. UI System (or use Dear ImGui):**
- Slider widgets (X, Y, Z offsets)
- Button widgets (load, process, export, clear)
- Scrollable panel
- Text labels and status indicators
- File picker dialogs (native API integration)
- Layout manager (vertical/horizontal boxes)

**2. 3D Interaction:**
- Camera system (orbit, pan, zoom)
- Ray casting for 3D picking
- Grid point selection
- Face selection via ray-plane intersection

**3. Application State:**
- Workflow management (step-by-step progression)
- Mesh data caching
- Undo/redo system (optional but recommended)
- Settings persistence

**4. Shader Programs:**
- Mesh rendering shader (vertex + fragment)
- Grid point shader (for markers)
- Text rendering shader (or use SDF fonts)
- Lighting calculations

---

## Required Libraries and Dependencies

### Essential Libraries

#### 1. **Vulkan SDK**
**Purpose:** Core graphics API
**Website:** https://vulkan.lunarg.com/
**Components:**
- vulkan.h - API headers
- Validation layers (debugging)
- Shader compilers (glslang, SPIRV-V)
- Tools (Vulkan Inspector, etc.)

**Installation:**
```bash
# Linux
sudo apt install vulkan-sdk

# macOS (via Homebrew)
brew install vulkan-headers molten-vk

# Windows
# Download installer from LunarG website
```

**Key Headers:**
```cpp
#include <vulkan/vulkan.h>
#include <vulkan/vulkan_core.h>
```

---

#### 2. **SDL2**
**Purpose:** Window and input management
**Website:** https://www.libsdl.org/
**Version:** 2.30.0 or later

**Installation:**
```bash
# Linux
sudo apt install libsdl2-dev

# macOS
brew install sdl2

# Windows (vcpkg)
vcpkg install sdl2
```

**Key Functions:**
```cpp
SDL_Init(SDL_INIT_VIDEO);
SDL_Window* window = SDL_CreateWindow(...);
SDL_Vulkan_CreateSurface(window, instance, &surface);
SDL_PollEvent(&event); // Event loop
```

---

#### 3. **Dear ImGui (Recommended)**
**Purpose:** Immediate mode GUI system
**Website:** https://github.com/ocornut/imgui
**Why:** Drastically reduces UI development time

**Installation:**
```bash
# Clone repository
git clone https://github.com/ocornut/imgui.git

# Or use package manager
vcpkg install imgui
```

**Key Features:**
- Sliders, buttons, text inputs out of the box
- Docking branch supports complex layouts
- Built-in demo for learning
- Vulkan backends included
- Performance profiler, style editor

**Usage Example:**
```cpp
ImGui::Begin("Grid Offset");
ImGui::SliderFloat("X Offset", &x_offset, -50.0f, 50.0f);
ImGui::SliderFloat("Y Offset", &y_offset, -50.0f, 50.0f);
ImGui::SliderFloat("Z Offset", &z_offset, -50.0f, 50.0f);
if (ImGui::Button("Reset")) { /* reset */ }
ImGui::End();
```

**Alternative: Custom UI**
If you don't use ImGui, you'll need to build:
- Widget base class
- Layout engine
- Event routing
- Rendering for each widget type
- Estimated: 2000-5000 lines of code

---

#### 4. **Manifold3d (CRITICAL)**
**Purpose:** High-performance boolean operations
**Website:** https://github.com/elalish/manifold
**Why:** Fastest, most robust CSG library available

**Installation:**
```bash
# vcpkg (recommended)
vcpkg install manifold

# Or build from source
git clone https://github.com/elalish/manifold.git
cd manifold
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j8
sudo make install
```

**Key Features:**
- Boolean operations: difference, union, intersection
- Mesh repair and simplification
- Fast (GPU-accelerated via CUDA, optional)
- Robust (handles edge cases well)

**Usage Example:**
```cpp
#include <manifold/manifold.h>

// Load mesh
manifold::Manifold mesh = manifold::ImportMesh("model.stl");

// Create cutting cylinder
manifold::Manifold cylinder = manifold::Cylinder(radius, height);

// Transform cylinder
cylinder = cylinder.Translate(position);
cylinder = cylinder.Rotate(rotation);

// Cut hole
manifold::Manifold result = mesh - cylinder; // Boolean difference
```

**Alternatives:**
- **CGAL** (https://www.cgal.org/) - Comprehensive but heavy
- **Carve** (https://github.com/folded/csg) - Older, less maintained
- **libigl** (https://libigl.github.io/) - Has boolean ops but slower

---

#### 5. **Assimp**
**Purpose:** 3D model file I/O
**Website:** https://github.com/assimp/assimp
**Why:** Supports 50+ file formats (STL, STEP, OBJ, etc.)

**Installation:**
```bash
# Linux
sudo apt install libassimp-dev

# macOS
brew install assimp

# Windows (vcpkg)
vcpkg install assimp
```

**Usage Example:**
```cpp
#include <assimp/Importer.hpp>
#include <assimp/scene.h>
#include <assimp/postprocess.h>

Assimp::Importer importer;
const aiScene* scene = importer.ReadFile(
    "model.stl",
    aiProcess_Triangulate |
    aiProcess_JoinIdenticalVertices |
    aiProcess_FixInfacingNormals
);

// Extract vertices and faces
for (unsigned int m = 0; m < scene->mNumMeshes; m++) {
    aiMesh* mesh = scene->mMeshes[m];
    // Process mesh...
}
```

**Note on STEP:**
Assimp has limited STEP support. Consider:
- **OpenCASCADE** (https://www.opencascade.com/) for robust STEP I/O
- **STEPcode** (https://github.com/stepcode/stepcode)
- Commercial SDKs (expensive)

---

#### 6. **GLM (OpenGL Mathematics)**
**Purpose:** 3D math library (vectors, matrices, transformations)
**Website:** https://github.com/g-truc/glm
**Why:** Header-only, matches GLSL syntax

**Installation:**
```bash
# Linux
sudo apt install libglm-dev

# macOS
brew install glm

# Windows (vcpkg)
vcpkg install glm
```

**Usage Example:**
```cpp
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/quaternion.hpp>

// 3D vector
glm::vec3 position(10.0f, 20.0f, 30.0f);

// Model-view-projection matrix
glm::mat4 model = glm::mat4(1.0f);
glm::mat4 view = glm::lookAt(cameraPos, target, up);
glm::mat4 projection = glm::perspective(fov, aspect, near, far);
glm::mat4 mvp = projection * view * model;

// Quaternion rotation
glm::quat rotation = glm::angleAxis(glm::radians(45.0f), glm::vec3(0, 1, 0));
glm::mat4 rotMatrix = glm::mat4_cast(rotation);
```

**Alternative: Eigen**
- More general-purpose (linear algebra, optimization)
- Heavier dependency
- Website: https://eigen.tuxfamily.org/

---

#### 7. **Vulkan-Hpp (Optional but Recommended)**
**Purpose:** Modern C++ bindings for Vulkan
**Website:** Part of Vulkan SDK
**Why:** Reduces boilerplate, provides RAII wrappers

**Usage Comparison:**
```cpp
// C-style Vulkan (verbose)
VkInstance instance;
VkInstanceCreateInfo createInfo{};
createInfo.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
vkCreateInstance(&createInfo, nullptr, &instance);

// C++ style with vulkan-hpp (cleaner)
vk::InstanceCreateInfo createInfo;
vk::Instance instance = vk::createInstance(createInfo);
```

---

### Secondary Libraries (Recommended)

#### 8. **spdlog**
**Purpose:** Fast logging library
**Website:** https://github.com/gabime/spdlog
**Why:** Better than std::cout, supports file logging

**Installation:**
```bash
vcpkg install spdlog
```

---

#### 9. **stb_image / stb_image_write**
**Purpose:** Image loading/saving (for textures, screenshots)
**Website:** https://github.com/nothings/stb
**Why:** Header-only, easy to integrate

**Note:** Optional if you don't use textures

---

#### 10. **tinyfiledialogs**
**Purpose:** Native file dialogs
**Website:** https://sourceforge.net/projects/tinyfiledialogs/
**Why:** Cross-platform, easier than calling native APIs directly

**Installation:**
```bash
vcpkg install tinyfiledialogs
```

**Usage:**
```cpp
#include "tinyfiledialogs.h"

const char* filename = tinyfd_openFileDialog(
    "Select Mesh File",
    "",
    0,
    NULL,
    NULL,
    0
);
```

**Alternative:** Use ImGui::FileBrowser (https://github.com/AirGuanZ/imgui-filebrowser)

---

### Optional but Useful Libraries

#### 11. **entt**
**Purpose:** Entity Component System (ECS)
**Website:** https://github.com/skypjack/entt
**Why:** Good for managing complex scene graphs (if you expand functionality)

---

#### 12. **jwt-cpp** (if you add cloud features)
**Purpose:** JWT authentication
**Website:** https://github.com/Thalhammer/jwt-cpp

---

#### 13. **nlohmann/json**
**Purpose:** JSON parsing
**Website:** https://github.com/nlohmann/json
**Why:** Save/load project files, settings

**Usage:**
```cpp
#include <nlohmann/json.hpp>

nlohmann::json config;
config["grid_offset"]["x"] = 10.5;
config["selected_slots"] = {1, 5, 7};

std::ofstream file("project.json");
file << config.dump(4);
```

---

### Vulkan-Specific Tools

#### 14. **Vulkan Memory Allocator (VMA)**
**Purpose:** Manage GPU memory allocations
**Website:** https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator
**Why:** Prevents memory leaks, improves performance

**Installation:**
```bash
git clone https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator.git
```

---

#### 15. **VKDispatch**
**Purpose:** Dynamic Vulkan function loading
**Website:** https://github.com/Raikiri/VulkanDispatch
**Why:** Easier than manually loading function pointers

---

## Implementation Roadmap

### Phase 1: Project Setup (Week 1)
1. Set up CMake build system
2. Integrate vcpkg for dependencies
3. Create Hello World SDL + Vulkan app
4. Set up logging (spdlog)
5. Configure validation layers

**Deliverable:** Clear screen with Vulkan triangle

---

### Phase 2: Window and Input (Week 2)
1. Implement main window with SDL2
2. Set up event loop
3. Handle keyboard/mouse input
4. Implement camera class (orbit controls)
5. Add Dear ImGui integration

**Deliverable:** Interactive window with ImGui demo

---

### Phase 3: Mesh Loading (Week 3)
1. Integrate Assimp
2. Create Mesh class (vertex/index buffers)
3. Load STL files
4. Load OBJ files
5. Implement basic mesh rendering (solid color)
6. Add mesh repair pipeline (from trimesh)

**Deliverable:** Display loaded 3D mesh

---

### Phase 4: Grid System (Week 4)
1. Port grid_system.py logic to C++
2. Implement grid generation algorithm
3. Create grid point visualization (spheres/markers)
4. Add offset parameters
5. Implement grid regeneration

**Deliverable:** Grid overlay on mesh

---

### Phase 5: Boolean Operations (Week 5-6)
1. Integrate manifold3d
2. Create cylinder geometry for cutting
3. Implement boolean difference
4. Add multi-slot processing
5. Implement T-clip loading
6. Add boolean union for T-clip insertion

**Deliverable:** Functional hole cutting and T-clip insertion

---

### Phase 6: UI Implementation (Week 7-8)
1. Create left panel with ImGui
2. Add file browser dialogs
3. Implement sliders for offsets
4. Add slot selection UI
5. Create view control buttons
6. Add process and export buttons

**Deliverable:** Complete GUI matching current app

---

### Phase 7: Interaction (Week 9)
1. Implement 3D picking (ray casting)
2. Add face selection via click
3. Add grid point selection
4. Implement keyboard shortcuts
5. Add undo/redo system

**Deliverable:** Fully interactive application

---

### Phase 8: Polish and Optimization (Week 10)
1. Add text rendering for labels
2. Implement transparency (alpha blending)
3. Add loading progress indicators
4. Optimize mesh rendering (LOD, culling)
5. Error handling and validation
6. Create installer packages

**Deliverable:** Production-ready application

---

## Code Examples

### Example 1: Basic SDL + Vulkan Setup

```cpp
#include <SDL2/SDL.h>
#include <SDL2/SDL_vulkan.h>
#include <vulkan/vulkan.hpp>
#include <iostream>
#include <vector>

class VulkanApp {
public:
    void run() {
        initWindow();
        initVulkan();
        mainLoop();
        cleanup();
    }

private:
    SDL_Window* window;
    vk::Instance instance;
    vk::PhysicalDevice physicalDevice;
    vk::Device device;
    vk::Queue graphicsQueue;
    vk::SurfaceKHR surface;
    vk::SwapchainKHR swapChain;
    std::vector<vk::Image> swapChainImages;
    vk::Format swapChainImageFormat;
    vk::Extent2D swapChainExtent;

    void initWindow() {
        SDL_Init(SDL_INIT_VIDEO);

        window = SDL_CreateWindow(
            "Skadis T-Clip Tool",
            SDL_WINDOWPOS_CENTERED,
            SDL_WINDOWPOS_CENTERED,
            1400, 900,
            SDL_WINDOW_VULKAN | SDL_WINDOW_RESIZABLE
        );
    }

    void initVulkan() {
        createInstance();
        pickPhysicalDevice();
        createLogicalDevice();
        createSurface();
        createSwapChain();
    }

    void createInstance() {
        vk::ApplicationInfo appInfo{};
        appInfo.setPApplicationName("Skadis T-Clip Tool");
        appInfo.setApplicationVersion(VK_MAKE_VERSION(1, 0, 0));
        appInfo.setPEngineName("No Engine");
        appInfo.setEngineVersion(VK_MAKE_VERSION(1, 0, 0));
        appInfo.setApiVersion(VK_API_VERSION_1_2);

        uint32_t extensionCount = 0;
        SDL_Vulkan_GetInstanceExtensions(window, &extensionCount, nullptr);
        std::vector<const char*> extensions(extensionCount);
        SDL_Vulkan_GetInstanceExtensions(window, &extensionCount, extensions.data());

        vk::InstanceCreateInfo createInfo{};
        createInfo.setPApplicationInfo(&appInfo);
        createInfo.setEnabledExtensionCount(extensionCount);
        createInfo.setPpEnabledExtensionNames(extensions.data());

        // Enable validation layers in debug builds
        #ifndef NDEBUG
        const char* validationLayers[] = {"VK_LAYER_KHRONOS_validation"};
        createInfo.setEnabledLayerCount(1);
        createInfo.setPpEnabledLayerNames(validationLayers);
        #endif

        instance = vk::createInstance(createInfo);
    }

    void pickPhysicalDevice() {
        std::vector<vk::PhysicalDevice> devices = instance.enumeratePhysicalDevices();

        for (const auto& device : devices) {
            vk::PhysicalDeviceProperties properties = device.getProperties();
            std::cout << "Found device: " << properties.deviceName << "\n";

            // Pick first discrete GPU
            if (properties.deviceType == vk::PhysicalDeviceType::eDiscreteGpu) {
                physicalDevice = device;
                break;
            }
        }

        if (!physicalDevice) {
            throw std::runtime_error("Failed to find suitable GPU");
        }
    }

    void createLogicalDevice() {
        // Get queue family index
        uint32_t queueFamilyIndex = 0; // Simplified

        vk::DeviceQueueCreateInfo queueCreateInfo{};
        queueCreateInfo.setQueueFamilyIndex(queueFamilyIndex);
        queueCreateInfo.setQueueCount(1);
        float queuePriority = 1.0f;
        queueCreateInfo.setPQueuePriorities(&queuePriority);

        vk::DeviceCreateInfo createInfo{};
        createInfo.setQueueCreateInfoCount(1);
        createInfo.setPQueueCreateInfos(&queueCreateInfo);

        device = physicalDevice.createDevice(createInfo);
        graphicsQueue = device.getQueue(queueFamilyIndex, 0);
    }

    void createSurface() {
        VkSurfaceKHR _surface;
        if (SDL_Vulkan_CreateSurface(window, instance, &_surface) == 0) {
            throw std::runtime_error("Failed to create window surface");
        }
        surface = _surface;
    }

    void createSwapChain() {
        // Simplified - real implementation needs more setup
        vk::SurfaceCapabilitiesKHR capabilities = physicalDevice.getSurfaceCapabilitiesKHR(surface);

        swapChainExtent = capabilities.currentExtent;
        if (swapChainExtent.width == 0xFFFFFFFF) {
            swapChainExtent.width = 1400;
            swapChainExtent.height = 900;
        }

        swapChainFormat = vk::Format::eB8G8R8A8Srgb;

        vk::SwapchainCreateInfoKHR createInfo{};
        createInfo.setSurface(surface);
        createInfo.setMinImageCount(capabilities.minImageCount + 1);
        createInfo.setImageFormat(swapChainFormat);
        createInfo.setImageColorSpace(vk::ColorSpaceKHR::eSrgbNonlinear);
        createInfo.setImageExtent(swapChainExtent);
        createInfo.setImageArrayLayers(1);
        createInfo.setImageUsage(vk::ImageUsageFlagBits::eColorAttachment);
        createInfo.setImageSharingMode(vk::SharingMode::eExclusive);
        createInfo.setPreTransform(capabilities.currentTransform);
        createInfo.setCompositeAlpha(vk::CompositeAlphaFlagBitsKHR::eOpaque);
        createInfo.setPresentMode(vk::PresentModeKHR::eFifo);
        createInfo.setClipped(true);

        swapChain = device.createSwapchainKHR(createInfo);
        swapChainImages = device.getSwapchainImagesKHR(swapChain);
    }

    void mainLoop() {
        bool running = true;
        while (running) {
            SDL_Event event;
            while (SDL_PollEvent(&event)) {
                if (event.type == SDL_QUIT) {
                    running = false;
                }
            }

            // Render frame here
            drawFrame();
        }
    }

    void drawFrame() {
        // Implement rendering
    }

    void cleanup() {
        device.destroy();
        instance.destroySurfaceKHR(surface);
        instance.destroy();
        SDL_DestroyWindow(window);
        SDL_Quit();
    }
};

int main() {
    VulkanApp app;
    try {
        app.run();
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return 1;
    }
    return 0;
}
```

---

### Example 2: Mesh Loading with Assimp

```cpp
#include <assimp/Importer.hpp>
#include <assimp/scene.h>
#include <assimp/postprocess.h>
#include <vector>
#include <glm/glm.hpp>

struct Vertex {
    glm::vec3 position;
    glm::vec3 normal;
};

class Mesh {
public:
    std::vector<Vertex> vertices;
    std::vector<uint32_t> indices;

    bool loadFromFile(const std::string& filename) {
        Assimp::Importer importer;

        const aiScene* scene = importer.ReadFile(
            filename,
            aiProcess_Triangulate |
            aiProcess_JoinIdenticalVertices |
            aiProcess_FixInfacingNormals |
            aiProcess_GenNormals |
            aiProcess_PreTransformVertices
        );

        if (!scene || scene->mFlags & AI_SCENE_FLAGS_INCOMPLETE || !scene->mRootNode) {
            std::cerr << "Assimp error: " << importer.GetErrorString() << std::endl;
            return false;
        }

        // Process all meshes (merge if multiple)
        for (unsigned int m = 0; m < scene->mNumMeshes; m++) {
            processMesh(scene->mMeshes[m]);
        }

        return true;
    }

private:
    void processMesh(aiMesh* mesh) {
        uint32_t vertexOffset = vertices.size();

        // Extract vertices
        for (unsigned int i = 0; i < mesh->mNumVertices; i++) {
            Vertex vertex{};
            vertex.position = glm::vec3(
                mesh->mVertices[i].x,
                mesh->mVertices[i].y,
                mesh->mVertices[i].z
            );

            if (mesh->mNormals) {
                vertex.normal = glm::vec3(
                    mesh->mNormals[i].x,
                    mesh->mNormals[i].y,
                    mesh->mNormals[i].z
                );
            }

            vertices.push_back(vertex);
        }

        // Extract indices
        for (unsigned int i = 0; i < mesh->mNumFaces; i++) {
            aiFace face = mesh->mFaces[i];
            for (unsigned int j = 0; j < face.mNumIndices; j++) {
                indices.push_back(vertexOffset + face.mIndices[j]);
            }
        }
    }
};
```

---

### Example 3: Grid Generation (Port of grid_system.py)

```cpp
#include <vector>
#include <glm/glm.hpp>
#include <cmath>

struct GridSlot {
    int index;
    glm::vec3 position;
    std::string label;
    int col;
    int row;
};

class SkadisGrid {
public:
    static constexpr float H_SPACING = 20.0f;  // mm
    static constexpr float V_SPACING = 40.0f;  // mm
    static constexpr float STAGGER_OFFSET = 20.0f; // mm

    std::vector<GridSlot> slots;

    void generate(
        const glm::vec3& meshMin,
        const glm::vec3& meshMax,
        const glm::vec3& offset,
        const std::string& plane,
        const std::string& boundaryType
    ) {
        slots.clear();

        // Determine grid bounds based on plane
        float uMin, uMax, vMin, vMax;
        float boundaryValue;

        if (plane == "xy") {
            uMin = meshMin.x; uMax = meshMax.x; // U = X
            vMin = meshMin.y; vMax = meshMax.y; // V = Y
            boundaryValue = (boundaryType == "max_z") ? meshMax.z : meshMin.z;
        }
        else if (plane == "xz") {
            uMin = meshMin.x; uMax = meshMax.x; // U = X
            vMin = meshMin.z; vMax = meshMax.z; // V = Z
            boundaryValue = (boundaryType == "max_y") ? meshMax.y : meshMin.y;
        }
        else if (plane == "yz") {
            uMin = meshMin.y; uMax = meshMax.y; // U = Y
            vMin = meshMin.z; vMax = meshMax.z; // V = Z
            boundaryValue = (boundaryType == "max_x") ? meshMax.x : meshMin.x;
        }
        else {
            return; // Invalid plane
        }

        // Calculate grid center
        float uCenter = (uMin + uMax) / 2.0f + offset.x;
        float vCenter = (vMin + vMax) / 2.0f + offset.y;

        // Calculate grid dimensions
        float uSize = uMax - uMin;
        float vSize = vMax - vMin;

        // Number of grid points (with padding)
        int numCols = static_cast<int>(std::ceil(uSize / H_SPACING)) + 2;
        int numRows = static_cast<int>(std::ceil(vSize / V_SPACING)) + 2;

        // Starting positions (centered grid)
        float uStart = uCenter - (numCols * H_SPACING) / 2.0f;
        float vStart = vCenter - (numRows * V_SPACING) / 2.0f;

        int index = 0;
        for (int col = 0; col < numCols; col++) {
            for (int row = 0; row < numRows; row++) {
                // Apply stagger offset to every other column
                float stagger = (col % 2 == 1) ? STAGGER_OFFSET : 0.0f;

                float u = uStart + col * H_SPACING;
                float v = vStart + row * V_SPACING + stagger;

                glm::vec3 position;
                if (plane == "xy") {
                    position = glm::vec3(u, v, boundaryValue + offset.z);
                }
                else if (plane == "xz") {
                    position = glm::vec3(u, boundaryValue + offset.z, v);
                }
                else if (plane == "yz") {
                    position = glm::vec3(boundaryValue + offset.z, u, v);
                }

                // Generate label (A1, B2, etc.)
                char colChar = 'A' + (col % 26);
                std::string label = std::string(1, colChar) + std::to_string(row + 1);

                slots.push_back({
                    index++,
                    position,
                    label,
                    col,
                    row
                });
            }
        }
    }
};
```

---

### Example 4: Boolean Operations with manifold3d

```cpp
#include <manifold/manifold.h>
#include <glm/glm.hpp>
#include <glm/gtc/quaternion.hpp>

class BooleanOperations {
public:
    static manifold::Manifold cutHole(
        const manifold::Manifold& mesh,
        const glm::vec3& position,
        float depth,
        const glm::vec3& cutNormal
    ) {
        // Create cutting cylinder
        constexpr float radius = 14.142f; // 28.284 / 2

        manifold::Manifold cylinder = manifold::Cylinder(radius, depth, 0);

        // Align cylinder Z-axis with cut normal
        glm::vec3 zAxis(0.0f, 0.0f, 1.0f);
        glm::quat rotation = glm::rotation(zAxis, glm::normalize(cutNormal));

        // Rotate and translate cylinder
        manifold::Manifold alignedCyl = cylinder.Rotate({rotation.x, rotation.y, rotation.z, rotation.w});
        manifold::Manifold positionedCyl = alignedCyl.Translate({position.x, position.y, position.z});

        // Perform boolean difference
        manifold::Manifold result = mesh - positionedCyl;

        return result;
    }

    static manifold::Manifold insertTClip(
        const manifold::Manifold& mesh,
        const manifold::Manifold& tclipGeometry,
        const glm::vec3& position,
        const glm::vec3& cutNormal
    ) {
        // Get T-clip bounds
        glm::vec3 tclipMin, tclipMax;
        // ... calculate bounds ...

        // Align T-clip Y-axis (thin dimension) with NEGATIVE cut normal
        glm::vec3 yAxis(0.0f, 1.0f, 0.0f);
        glm::vec3 targetDir = -glm::normalize(cutNormal);
        glm::quat rotation = glm::rotation(yAxis, targetDir);

        // Rotate T-clip
        manifold::Manifold rotatedTClip = tclipGeometry.Rotate(
            {rotation.x, rotation.y, rotation.z, rotation.w}
        );

        // Position T-clip so base is flush with face
        glm::vec3 tclipPos = position + targetDir * glm::abs(tclipMin.y);
        manifold::Manifold positionedTClip = rotatedTClip.Translate(
            {tclipPos.x, tclipPos.y, tclipPos.z}
        );

        // Perform boolean union
        manifold::Manifold result = mesh + positionedTClip;

        return result;
    }

    static manifold::Manifold processMultipleSlots(
        const manifold::Manifold& mesh,
        const std::vector<glm::vec3>& positions,
        float depth,
        const manifold::Manifold& tclipGeometry,
        const glm::vec3& cutNormal,
        bool skipHoles = false
    ) {
        manifold::Manifold result = mesh;

        // Cut all holes FIRST
        if (!skipHoles) {
            for (const auto& pos : positions) {
                result = cutHole(result, pos, depth, cutNormal);
            }
        }

        // Then insert all T-clips
        if (tclipGeometry.IsValid()) {
            for (const auto& pos : positions) {
                result = insertTClip(result, tclipGeometry, pos, cutNormal);
            }
        }

        return result;
    }
};
```

---

### Example 5: Dear ImGui Integration

```cpp
#include <imgui.h>
#include <imgui_impl_sdl2.h>
#include <imgui_impl_vulkan.h>
#include <SDL2/SDL.h>

class SkadisGUI {
public:
    float xOffset = 0.0f;
    float yOffset = 0.0f;
    float zOffset = 0.0f;
    float depth = 10.0f;
    std::set<int> selectedSlots;

    void render() {
        // Main window
        ImGui::SetNextWindowPos(ImVec2(10, 10));
        ImGui::SetNextWindowSize(ImVec2(400, 800));
        ImGui::Begin("Skadis T-Clip Tool", nullptr, ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize);

        // Step 1: Load Mesh
        if (ImGui::CollapsingHeader("Step 1: Load Mesh", ImGuiTreeNodeFlags_DefaultOpen)) {
            if (ImGui::Button("Browse Mesh File...")) {
                browseMesh();
            }
            ImGui::Text("Loaded: %s", meshFilename.c_str());
        }

        // Step 2: Select Face
        if (ImGui::CollapsingHeader("Step 2: Select Face")) {
            ImGui::Text("Click on a colored face or use shortcuts:");
            ImGui::Text("F=Front, B=Back, L=Left, R=Right, T=Top, M=Bottom");
            ImGui::TextColored(ImVec4(0, 1, 0, 1), "Selected: %s", selectedFace.c_str());
        }

        // Step 3: Grid Offset
        if (ImGui::CollapsingHeader("Step 3: Grid Offset")) {
            ImGui::SliderFloat("X Offset (mm)", &xOffset, -50.0f, 50.0f);
            ImGui::SliderFloat("Y Offset (mm)", &yOffset, -50.0f, 50.0f);
            ImGui::SliderFloat("Z Offset (mm)", &zOffset, -50.0f, 50.0f);
            if (ImGui::Button("Reset Offsets")) {
                xOffset = yOffset = zOffset = 0.0f;
            }
        }

        // Step 4: Select Slots
        if (ImGui::CollapsingHeader("Step 4: Select Slots")) {
            ImGui::Text("Click on grid points to select");
            ImGui::TextColored(ImVec4(0, 0, 1, 1), "%zu slots selected", selectedSlots.size());
            if (ImGui::Button("Clear Selection")) {
                selectedSlots.clear();
            }
        }

        // View Controls
        if (ImGui::CollapsingHeader("View Controls")) {
            if (ImGui::Button("Isometric")) setViewIsometric();
            ImGui::SameLine();
            if (ImGui::Button("Front")) setViewFront();
            ImGui::SameLine();
            if (ImGui::Button("Top")) setViewTop();
            ImGui::SameLine();
            if (ImGui::Button("Side")) setViewSide();
        }

        // Step 5: Cutting Depth
        if (ImGui::CollapsingHeader("Step 5: Cutting Depth")) {
            ImGui::SliderFloat("Depth (mm)", &depth, 1.0f, 50.0f);
        }

        // Step 6: Process
        if (ImGui::CollapsingHeader("Step 6: Process")) {
            if (ImGui::Button("Cut Holes & Insert T-Clips", !selectedSlots.empty())) {
                processMesh();
            }
            if (ImGui::Button("Export (STL/STEP)", resultMeshValid)) {
                exportMesh();
            }
        }

        // Status
        ImGui::Separator();
        ImGui::TextColored(ImVec4(0.5f, 0.5f, 0.5f, 1), "Status: %s", statusText.c_str());

        ImGui::End();
    }

private:
    std::string meshFilename;
    std::string selectedFace;
    std::string statusText = "Ready";
    bool resultMeshValid = false;

    void browseMesh() {
        // Use tinyfiledialogs or ImGui::FileBrowser
        const char* filename = tinyfd_openFileDialog(
            "Select Mesh File",
            "",
            0,
            "STL files (*.stl)",
            "*.stl",
            0
        );

        if (filename) {
            meshFilename = filename;
            statusText = "Loaded: " + meshFilename;
        }
    }

    void setViewIsometric() { /* ... */ }
    void setViewFront() { /* ... */ }
    void setViewTop() { /* ... */ }
    void setViewSide() { /* ... */ }
    void processMesh() { /* ... */ }
    void exportMesh() { /* ... */ }
};
```

---

### Example 6: 3D Picking (Ray Casting)

```cpp
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

class RayCaster {
public:
    struct Ray {
        glm::vec3 origin;
        glm::vec3 direction;
    };

    static Ray screenToWorldRay(
        float mouseScreenX,
        float mouseScreenY,
        int windowWidth,
        int windowHeight,
        const glm::mat4& viewMatrix,
        const glm::mat4& projectionMatrix
    ) {
        // Normalize mouse coordinates to [-1, 1]
        float x = (2.0f * mouseScreenX) / windowWidth - 1.0f;
        float y = 1.0f - (2.0f * mouseScreenY) / windowHeight;

        // Create inverse matrices
        glm::mat4 invProjection = glm::inverse(projectionMatrix);
        glm::mat4 invView = glm::inverse(viewMatrix);

        // Clip space to view space
        glm::vec4 clipCoords(x, y, -1.0f, 1.0f);
        glm::vec4 eyeCoords = invProjection * clipCoords;
        eyeCoords = glm::vec4(eyeCoords.x, eyeCoords.y, -1.0f, 0.0f);

        // View space to world space
        glm::vec4 worldCoords = invView * eyeCoords;
        glm::vec3 rayDirection = glm::normalize(glm::vec3(worldCoords));

        // Ray origin is camera position
        glm::vec3 rayOrigin = glm::vec3(glm::inverse(viewMatrix)[3]);

        return {rayOrigin, rayDirection};
    }

    static bool intersectPlane(
        const Ray& ray,
        const glm::vec3& planePoint,
        const glm::vec3& planeNormal,
        glm::vec3& intersection
    ) {
        float denom = glm::dot(ray.direction, planeNormal);
        if (std::abs(denom) < 1e-6f) {
            return false; // Ray is parallel to plane
        }

        float t = glm::dot(planePoint - ray.origin, planeNormal) / denom;
        if (t < 0.0f) {
            return false; // Plane is behind ray
        }

        intersection = ray.origin + t * ray.direction;
        return true;
    }

    static int findNearestSlot(
        float mouseScreenX,
        float mouseScreenY,
        int windowWidth,
        int windowHeight,
        const glm::mat4& viewMatrix,
        const glm::mat4& projectionMatrix,
        const std::vector<GridSlot>& slots
    ) {
        Ray ray = screenToWorldRay(
            mouseScreenX, mouseScreenY,
            windowWidth, windowHeight,
            viewMatrix, projectionMatrix
        );

        float minDistance = std::numeric_limits<float>::max();
        int nearestSlot = -1;

        for (const auto& slot : slots) {
            // Distance from ray to point
            glm::vec3 rayToPoint = slot.position - ray.origin;
            float projection = glm::dot(rayToPoint, ray.direction);
            glm::vec3 closestPoint = ray.origin + projection * ray.direction;
            float distance = glm::length(slot.position - closestPoint);

            if (distance < minDistance) {
                minDistance = distance;
                nearestSlot = slot.index;
            }
        }

        // Adaptive threshold
        float threshold = 50.0f; // Adjust based on zoom level
        if (minDistance < threshold) {
            return nearestSlot;
        }
        return -1;
    }
};
```

---

### Example 7: Vulkan Shader for Mesh Rendering

**Vertex Shader (mesh.vert):**
```glsl
#version 450

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec3 inNormal;

layout(binding = 0) uniform UniformBufferObject {
    mat4 model;
    mat4 view;
    mat4 proj;
} ubo;

layout(location = 0) out vec3 fragNormal;
layout(location = 1) out vec3 fragPosition;

void main() {
    gl_Position = ubo.proj * ubo.view * ubo.model * vec4(inPosition, 1.0);
    fragNormal = mat3(transpose(inverse(ubo.model))) * inNormal;
    fragPosition = vec3(ubo.model * vec4(inPosition, 1.0));
}
```

**Fragment Shader (mesh.frag):**
```glsl
#version 450

layout(location = 0) in vec3 fragNormal;
layout(location = 1) in vec3 fragPosition;

layout(location = 0) out vec4 outColor;

// Simple directional light
const vec3 lightDirection = normalize(vec3(1.0, 1.0, 1.0));
const vec3 lightColor = vec3(1.0, 1.0, 1.0);
const vec3 objectColor = vec3(0.6f, 0.7f, 0.9f); // Light blue
const float ambientStrength = 0.3f;

void main() {
    // Ambient
    vec3 ambient = ambientStrength * lightColor;

    // Diffuse
    vec3 norm = normalize(fragNormal);
    float diff = max(dot(norm, lightDirection), 0.0);
    vec3 diffuse = diff * lightColor;

    // Combine
    vec3 result = (ambient + diffuse) * objectColor;

    // Transparency (alpha blending)
    outColor = vec4(result, 0.7f);
}
```

---

### Example 8: CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.20)
project(SkadisTClipTool)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find packages
find_package(Vulkan REQUIRED)
find_package(SDL2 REQUIRED)
find_package(glm REQUIRED)
find_package(spdlog REQUIRED)

# Manual libraries (vcpkg)
find_package(manifold CONFIG REQUIRED)
find_package(assimp REQUIRED)

# ImGui
set(IMGUI_DIR ${CMAKE_SOURCE_DIR}/third_party/imgui)
add_library(imgui STATIC
    ${IMGUI_DIR}/imgui.cpp
    ${IMGUI_DIR}/imgui_draw.cpp
    ${IMGUI_DIR}/imgui_widgets.cpp
    ${IMGUI_DIR}/imgui_tables.cpp
    ${IMGUI_DIR}/imgui_impl_sdl2.cpp
    ${IMGUI_DIR}/imgui_impl_vulkan.cpp
)
target_include_directories(imgui PUBLIC ${IMGUI_DIR})
target_link_libraries(imgui PUBLIC Vulkan::Vulkan SDL2::SDL2)

# Main executable
add_executable(skadis_tool
    src/main.cpp
    src/vulkan_app.cpp
    src/mesh_loader.cpp
    src/grid_system.cpp
    src/boolean_ops.cpp
    src/gui.cpp
)

target_include_directories(skadis_tool PRIVATE
    ${CMAKE_SOURCE_DIR}/include
    ${Vulkan_INCLUDE_DIRS}
)

target_link_libraries(skadis_tool PRIVATE
    Vulkan::Vulkan
    SDL2::SDL2
    glm::glm
    spdlog::spdlog
    manifold::manifold
    assimp
    imgui
)

# Platform-specific settings
if(APPLE)
    target_link_libraries(skadis_tool PRIVATE "-framework Metal -framework Quartz")
endif()

# Copy Vulkan shaders
file(COPY ${CMAKE_SOURCE_DIR}/shaders DESTINATION ${CMAKE_BINARY_DIR})
```

---

## Summary

### Key Takeaways

1. **This is a complex 3D CAD application**, not a simple game or visualization
2. **SDL + Vulkan is achievable** but requires significant development time (3-6 months minimum)
3. **Critical dependencies**: manifold3d, Assimp, SDL2, Vulkan SDK, Dear ImGui
4. **Most challenging aspects**:
   - Boolean operations (use manifold3d, don't implement yourself)
   - 3D picking/ray casting for interaction
   - UI system (use ImGui, don't build from scratch)
   - Mesh repair and watertightness checking
   - File I/O for multiple formats (especially STEP)

5. **Recommended approach**:
   - Start with working SDL + Vulkan + ImGui skeleton
   - Implement mesh loading and rendering first
   - Add grid system
   - Integrate boolean operations
   - Build UI last
   - Test on all three platforms early and often

### Estimated Development Effort

| Component | Time (Full-time) | Difficulty |
|-----------|------------------|------------|
| SDL + Vulkan setup | 1-2 weeks | Medium |
| Mesh loading | 1 week | Low-Medium |
| Grid system | 1 week | Low |
| Boolean operations | 2-3 weeks | High |
| 3D rendering (meshes) | 1-2 weeks | Medium |
| UI implementation | 2-3 weeks | Medium |
| Interaction (picking, etc.) | 2 weeks | High |
| File I/O (STEP format) | 1-2 weeks | Medium |
| Testing/debugging | 2-3 weeks | - |
| **Total** | **13-20 weeks** | - |

### Alternative: Qt + OpenGL (3-6 months)

If you want faster development with similar results, consider Qt + OpenGL instead of Vulkan.

---

## Additional Resources

### Vulkan Learning
- **Vulkan Tutorial**: https://vulkan-tutorial.com/
- **AMD GPUOpen**: https://gpuopen.com/learn/vulkan/
- **Khronos Vulkan Guide**: https://github.com/KhronosGroup/Vulkan-Guide

### SDL2 Documentation
- **Wiki**: https://wiki.libsdl.org/
- **SDL2 + Vulkan Guide**: https://gist.github.com/jmadsen/11450911

### Boolean Operations
- **Manifold3d**: https://github.com/elalish/manifold
- **CGAL Boolean Operations**: https://doc.cgal.org/latest/Nef_3/index.html

### CSG Libraries
- **Carve CSG**: https://github.com/folded/csg
- **Fuzzy CSG**: https://github.com/kaosat-dev/Blender_CSG_Skip

### Dear ImGui
- **GitHub**: https://github.com/ocornut/imgui
- **Wiki**: https://github.com/ocornut/imgui/wiki

### Mesh Processing
- **libigl**: https://libigl.github.io/
- **OpenMesh**: https://www.openmesh.org/
- **Trimesh** (original Python library): https://trimsh.org/

---

**End of Document**
