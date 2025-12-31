"""Configuration constants for IKEA Skadis T-Clip system."""

# IKEA Skadis specifications (CORRECTED)
SKADIS_SLOT_SPACING_H = 20.0  # mm, horizontal center-to-center
SKADIS_SLOT_SPACING_V = 40.0  # mm, vertical center-to-center
SKADIS_SLOT_WIDTH = 5.0       # mm, narrow dimension (horizontal)
SKADIS_SLOT_HEIGHT = 15.0     # mm, tall dimension (vertical capsule)
SKADIS_SLOT_ARC_RADIUS = 2.5  # mm, radius of capsule ends
SKADIS_STAGGER_OFFSET = 20.0  # mm, every other column shifts down by this
SKADIS_BOARD_THICKNESS = 5.0  # mm

# T-Clip mounting specifications
T_CLIP_CIRCLE_DIAMETER = 28.284  # mm, sqrt(2) * 20 (for rotation)
T_CLIP_DEFAULT_DEPTH = 10.0      # mm, default cutting depth

# Visualization settings
MESH_COLOR = 'lightblue'
GRID_COLOR = 'red'
SLOT_MARKER_SIZE = 8
FONT_SIZE = 10

# Bounding box face colors
BBOX_COLORS = {
    'front': 'red',      # +Y face
    'back': 'blue',      # -Y face
    'left': 'green',     # -X face
    'right': 'yellow',   # +X face
    'top': 'cyan',       # +Z face
    'bottom': 'magenta'  # -Z face
}
