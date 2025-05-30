import displayio

PALETTE_TYPE_BW = 'bw'
PALETTE_TYPE_7COLOR = '7color'

# Abstract color/value placeholders
BW_BLACK = 0  # Typically index 0 in a B&W palette
BW_WHITE = 1  # Typically index 1 in a B&W palette

# For 7-color palette (example mapping, actual indices depend on palette creation)
COLOR_BLACK = 0
COLOR_WHITE = 1
COLOR_GREEN = 2
COLOR_BLUE = 3
COLOR_RED = 4
COLOR_YELLOW = 5
COLOR_ORANGE = 6
# Add any other abstract color names if needed, e.g. COLOR_GREY

def get_palette_color_index(value, palette_type, palette_instance=None):
    """
    Maps an abstract color value or raw value to a palette index.

    :param value: Abstract color constant (e.g., BW_BLACK) or a raw number (e.g., grayscale, noise).
    :param palette_type: String identifying the type of palette (e.g., PALETTE_TYPE_BW).
    :param palette_instance: The displayio.Palette instance (optional, but can help with validation).
    :return: An integer palette index.
    """
    if palette_type == PALETTE_TYPE_BW:
        if value == BW_BLACK:
            return 0
        elif value == BW_WHITE:
            return 1
        elif isinstance(value, (int, float)): # Assuming grayscale 0-255 or float 0-1
            # Simple thresholding for B&W
            # If value is float 0-1 (e.g. noise), scale it or use a threshold like 0.5
            # If value is int 0-255, use threshold like 128
            if isinstance(value, float) and 0.0 <= value <= 1.0:
                return 0 if value < 0.5 else 1 # Black for <0.5, White for >=0.5
            elif isinstance(value, int) and 0 <= value <= 255:
                return 0 if value < 128 else 1 # Black for <128, White for >=128
            else: # Fallback for other numeric values, could be more sophisticated
                return 0 if value == 0 else 1
        else:
            return 0 # Default to black for unrecognized values

    elif palette_type == PALETTE_TYPE_7COLOR:
        # Direct mapping for defined color constants
        if isinstance(value, int) and 0 <= value <= 6: # Assuming direct use of COLOR_* constants
            if palette_instance and value >= len(palette_instance):
                return 0 # Fallback to black if index out of bounds
            return value

        elif isinstance(value, float) and 0.0 <= value <= 1.0: # Map noise value (0-1)
            # Simple linear mapping to the 7 colors.
            # Exclude black and white (indices 0 and 1) from random mapping if desired,
            # or include them. For now, map across all 7.
            # palette_len = len(palette_instance) if palette_instance else 7
            # For 7-color, indices are 0-6.
            # Let's assume we want to map noise primarily to the actual colors (2-6)
            # or map across all, including B&W.
            # Mapping across all 7:
            idx = int(value * 6.999) # value * (palette_size - 1) for 0 to N-1
            # Clamp to be safe, though value*6.999 should keep it in 0-6 for value in [0,1]
            if palette_instance:
                idx = max(0, min(idx, len(palette_instance) - 1))
            else: # Assume 7 colors if no palette instance
                idx = max(0, min(idx, 6))
            return idx
        else:
            # Default for unrecognized values in 7-color mode
            return COLOR_BLACK # Default to black

    # Fallback for unknown palette_type
    return 0 # Default to black
