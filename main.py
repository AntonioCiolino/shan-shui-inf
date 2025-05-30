import board
import displayio
import time
import random # Added for INITIAL_SEED if time.monotonic() is not available or for other randomness
import gc # Added for garbage collection

from lib import display_setup
from lib import color_utils
from lib import utils # Module import
from lib import perlin_noise # Module import, class is PerlinNoise
from lib import poly_tools # Module import, class is PolyTools
from lib.drawing import Tree, Mount, Arch, Man
from lib import landscape_manager # Module import, class is LandscapeManager

# --- Configuration ---
DISPLAY_TYPE = 'bw_7_5'  # Options: 'bw_7_5', 'color_5_65' (match display_setup)

# SCROLL_INTERVAL_SECONDS = 60 # For production (e.g., e-paper)
SCROLL_INTERVAL_SECONDS = 2  # For testing (e.g., LCD or faster e-paper)
# SCROLL_INTERVAL_SECONDS = 0.1 # For very fast testing on non-e-paper

SCROLL_STEP_PIXELS = 20    # Pixels to scroll each interval
CHUNK_WIDTH = 256          # Width of each landscape chunk (adjust based on memory/performance)
                           # Smaller chunks = more frequent generation, but smaller data per chunk.
                           # Larger chunks = less frequent generation, but more data per chunk.
                           # View width for Waveshare 7.5" BW is 800. Chunk width of 256 or 512 is reasonable.

# Use time.monotonic() for a changing seed, or a fixed integer for reproducible landscapes.
try:
    INITIAL_SEED = int(time.monotonic() * 1000)
except AttributeError: # time.monotonic might not be present on all CircuitPython builds
    INITIAL_SEED = int(time.time() * 1000) if hasattr(time, 'time') else random.randint(0, 1000000)


def main():
    print("Procedural Landscape Generator")
    print(f"Initial Seed: {INITIAL_SEED}")

    print("Initializing display...")
    # Initialize display based on selected type
    # This returns display, main_group for adding elements, and the active palette
    display, main_group, current_palette = display_setup.initialize_display(DISPLAY_TYPE)

    if DISPLAY_TYPE == 'bw_7_5':
        palette_type_enum = color_utils.PALETTE_TYPE_BW
    elif DISPLAY_TYPE == 'color_5_65':
        palette_type_enum = color_utils.PALETTE_TYPE_7COLOR
    else:
        print(f"Warning: Unknown DISPLAY_TYPE '{DISPLAY_TYPE}', defaulting to BW handling.")
        palette_type_enum = color_utils.PALETTE_TYPE_BW

    print(f"Display initialized: {display.width}x{display.height}")
    print(f"Palette type enum: {palette_type_enum}, num_colors in palette: {len(current_palette)}")

    # Create the main bitmap where the landscape will be drawn and scrolled
    # This bitmap is added to the display via a TileGrid.
    landscape_bitmap = displayio.Bitmap(display.width, display.height, len(current_palette))

    # Fill with a background color (e.g., white)
    # Use color_utils to get the correct palette index for "white"
    try:
        white_idx = color_utils.get_palette_color_index("white", palette_type_enum, current_palette)
        if white_idx is None:
            print("Warning: 'white' not found in palette, defaulting to index 0 or 1.")
            white_idx = 0 if palette_type_enum == color_utils.PALETTE_TYPE_BW else 1 # Common defaults
    except Exception as e:
        print(f"Error getting white index: {e}. Defaulting to 0 or 1.")
        white_idx = 0 if palette_type_enum == color_utils.PALETTE_TYPE_BW else 1

    landscape_bitmap.fill(white_idx)

    landscape_tilegrid = displayio.TileGrid(landscape_bitmap, pixel_shader=current_palette)
    main_group.append(landscape_tilegrid)

    # Show the main group. Some displays auto-refresh, others need display.refresh().
    # displayio handles this via display.root_group = main_group for many modern boards.
    if hasattr(display, 'root_group'):
        display.root_group = main_group
    elif hasattr(display, 'show'): # Older or specific display libraries
        display.show(main_group)
    else:
        print("Warning: Display object does not have 'root_group' or 'show'. Manual refresh might be needed.")

    print("Initializing helper modules and drawing class instances...")
    # lib.utils is a module of functions, not a class to instantiate in this structure.
    # Pass the module itself if an "instance" of utils is needed.
    utils_module_as_instance = utils

    # PerlinNoise is seeded directly.
    noise_inst = perlin_noise.PerlinNoise(seed=INITIAL_SEED)
    poly_tools_inst = poly_tools.PolyTools() # PolyTools has no specific init dependencies in current form

    # Instantiate drawing classes with their dependencies
    man_drawer = Man(poly_tools_instance=poly_tools_inst, utils_instance=utils_module_as_instance)

    tree_drawer = Tree(poly_tools_instance=poly_tools_inst,
                       noise_instance=noise_inst,
                       utils_instance=utils_module_as_instance,
                       man_instance=man_drawer)

    arch_drawer = Arch(poly_tools_instance=poly_tools_inst,
                       tree_instance=tree_drawer,
                       man_instance=man_drawer,
                       noise_instance=noise_inst, # Added missing
                       utils_instance=utils_module_as_instance) # Added missing

    mount_drawer = Mount(poly_tools_instance=poly_tools_inst,
                         tree_instance=tree_drawer,
                         arch_instance=arch_drawer,
                         man_instance=man_drawer,
                         noise_instance=noise_inst,
                         utils_instance=utils_module_as_instance)

    print("Initializing Landscape Manager...")
    landscape_mgr = landscape_manager.LandscapeManager(
        display_bitmap=landscape_bitmap,
        view_width=display.width,
        chunk_width=CHUNK_WIDTH,
        tree_instance=tree_drawer,
        mount_instance=mount_drawer,
        arch_instance=arch_drawer,
        man_instance=man_drawer,
        poly_tools_instance=poly_tools_inst,
        noise_instance=noise_inst,
        utils_instance=utils_module_as_instance, # Pass the module
        current_palette=current_palette,
        palette_type=palette_type_enum
    )

    current_scroll_x = 0
    print("Initialization complete. Starting main loop...")

    loop_count = 0
    while True:
        loop_start_time = time.monotonic() if hasattr(time, 'monotonic') else time.time()
        print(f"\nLoop {loop_count}: current_scroll_x = {current_scroll_x}")

        print(" LandscapeManager: Ensuring chunks are loaded...")
        landscape_mgr.ensure_chunks_loaded(current_scroll_x)

        print(" LandscapeManager: Rendering visible chunks...")
        landscape_mgr.render_visible_chunks(current_scroll_x)

        print(" Display: Refreshing...")
        refresh_start_time = time.monotonic() if hasattr(time, 'monotonic') else time.time()

        # Display refresh logic can vary.
        # For e-paper, display.refresh() blocks until done.
        # For others, it might be non-blocking or require checking display.busy.
        if hasattr(display, 'busy'):
            while display.busy:
                time.sleep(0.01) # Short sleep while busy

        display.refresh()

        # If display.busy was not used, and refresh is non-blocking,
        # we might need a fixed sleep if SCROLL_INTERVAL_SECONDS is very short
        # or rely on the main loop sleep. For e-paper, refresh() is usually blocking.

        print(f" Display refreshed in {( (time.monotonic() if hasattr(time, 'monotonic') else time.time()) - refresh_start_time):.3f}s")

        # Scroll for the next frame
        current_scroll_x += SCROLL_STEP_PIXELS
        loop_count += 1

        # Calculate loop duration and sleep if necessary
        loop_end_time = time.monotonic() if hasattr(time, 'monotonic') else time.time()
        loop_duration = loop_end_time - loop_start_time

        # Garbage Collection and Memory Info
        print(f"Memory Info: Free={gc.mem_free() if hasattr(gc, 'mem_free') else 'N/A'}, Alloc={gc.mem_alloc() if hasattr(gc, 'mem_alloc') else 'N/A'}")
        print("Collecting garbage...")
        gc.collect()
        print(f"Memory Info after GC: Free={gc.mem_free() if hasattr(gc, 'mem_free') else 'N/A'}, Alloc={gc.mem_alloc() if hasattr(gc, 'mem_alloc') else 'N/A'}")

        sleep_time = SCROLL_INTERVAL_SECONDS - loop_duration
        if sleep_time > 0:
            print(f" Loop duration: {loop_duration:.3f}s. Sleeping for {sleep_time:.3f}s.")
            time.sleep(sleep_time)
        else:
            print(f" Loop duration: {loop_duration:.3f}s. (Frame took longer than interval!)")

if __name__ == "__main__":
    main()
