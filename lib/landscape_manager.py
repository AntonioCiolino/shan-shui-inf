import math
import random

# Assuming these modules will be in the lib directory or accessible
from lib.perlin_noise import PerlinNoise # Assuming PerlinNoise class is directly in perlin_noise.py
from lib.utils import Utils # Assuming Utils class is directly in utils.py
from lib.drawing import Tree, Mount, Arch, Man # Importing classes from drawing.py
# PolyTools might be needed if LandscapeManager itself uses it, or if passed instances use it and it's not part of their init.
# For now, assuming poly_tools_instance is passed and used by other instances.

class LandscapeManager:
    def __init__(self, display_bitmap, view_width, chunk_width,
                 tree_instance, mount_instance, arch_instance, man_instance,
                 poly_tools_instance, noise_instance, utils_instance,
                 current_palette, palette_type):

        self.display_bitmap = display_bitmap
        self.view_width = view_width
        self.chunk_width = chunk_width

        self.tree_instance = tree_instance
        self.mount_instance = mount_instance
        self.arch_instance = arch_instance
        self.man_instance = man_instance # Though Man is usually called via Arch/Boat etc.
        self.poly_tools_instance = poly_tools_instance
        self.noise_instance = noise_instance
        self.utils_instance = utils_instance # Storing the passed utils_instance

        self.current_palette = current_palette
        self.palette_type = palette_type

        self.chunks = {}  # dictionary to store chunk data, keyed by chunk_x_start
        self.loaded_chunk_x_coords = []  # sorted list of x_start of loaded chunks

        # Initialize min_loaded_x and max_loaded_x carefully
        # It's better to set them after the first chunk is loaded.
        self.min_loaded_x = None
        self.max_loaded_x = None

        self.planmtx = {}  # for density planning across conceptual "columns"
        self.scroll_speed = 10 # Default scroll speed for planning, can be adjusted

        # Base Y offsets for different entity types
        self.y_offsets = {
            'mountain': 700,
            'flatmount': 700,
            'distmount': 280,
            'boat': 500,
            # Add other entities like trees, rocks if they have a standard base y
        }
        # Approximate widths for planning to avoid overlap
        self.entity_widths_approx = {
            'mountain': 400,
            'flatmount': 600, # Flat mountains can be wider
            'distmount': 2000, # Distant mountains are very wide but sparse
            'boat': 150,
        }


    def _plan_entities_for_chunk(self, chunk_x_start, chunk_x_end):
        """
        Plans entities within a given chunk's x-range.
        Analogous to parts of the JS mountplanner function.
        """
        planned_entities = []

        # x_step determines how frequently we check for placing a major entity.
        # Should be related to scroll_speed or average entity width.
        x_step = self.scroll_speed * 10 # Or e.g., self.chunk_width / 10
        if x_step == 0: x_step = 50 # Avoid infinite loop if scroll_speed is 0

        # Iterate through the chunk to plan entities
        # current_x represents potential placement points for groups of entities or major entities.
        num_steps = math.ceil((chunk_x_end - chunk_x_start) / x_step)

        for i_step in range(num_steps):
            current_x_plan_node = chunk_x_start + i_step * x_step

            # --- Mountain Planning (example) ---
            # yr_val is like a general height modulator for the region from JS.
            # Using noise based on current_x_plan_node to vary conditions.
            yr_val = self.noise_instance.noise(current_x_plan_node * 0.001, math.pi) # Scaled x for broader changes

            # Bands for placing mountains (vertical layers)
            # Max height for mountain placement influenced by yr_val.
            # JS: for(var j=0;j<yr*480;j+=30) -> yr is ns(i*0.01,PI)
            # Let's map yr_val (0-1) to a number of bands or max y_band_offset.
            max_y_band_offset = yr_val * 200 # e.g. mountains can go up to 200px higher based on yr_val
            y_band_step = 30

            num_y_bands = math.floor(max_y_band_offset / y_band_step)

            for i_band in range(num_y_bands):
                current_y_band_offset = i_band * y_band_step

                # Noise to decide if a mountain should be here.
                # JS: ns(i*0.03,j*0.03) -> i is x_plan_node, j is y_band_offset
                noise_val_mount_decision = self.noise_instance.noise(current_x_plan_node * 0.003, current_y_band_offset * 0.003)

                # Adjust threshold based on JS: max(ns(...) - 0.55, 0) * 2; if this > 0.3
                # So, ns(...) - 0.55 > 0.15  => ns(...) > 0.7
                if noise_val_mount_decision > 0.7:
                    # Check planmtx to avoid overcrowding
                    # planmtx uses discretized "columns" based on x_step or entity_width.
                    # Let's use a column index based on mountain_width_approx.
                    plan_column_idx = math.floor(current_x_plan_node / self.entity_widths_approx['mountain'])

                    if self.planmtx.get(plan_column_idx, 0) < current_x_plan_node : # If slot is available
                        entity_x_actual = current_x_plan_node + self.utils_instance.norm_rand(-x_step/2, x_step/2) # Add jitter
                        entity_y_actual = self.y_offsets['mountain'] - current_y_band_offset # Higher bands -> lower y

                        # Define mountain args
                        # Height can be modulated by how strong the noise_val_mount_decision was.
                        mount_hei_modulator = (noise_val_mount_decision - 0.7) / 0.3 # Scale 0-1
                        mount_args = {
                            'hei': 100 + mount_hei_modulator * 300, # Height 100 to 400
                            'wid': self.entity_widths_approx['mountain'] * self.utils_instance.norm_rand(0.8, 1.2),
                            # Add other specific args for draw_mountain if needed
                        }
                        planned_entities.append({
                            'type': 'mountain',
                            'x': entity_x_actual, 'y': entity_y_actual,
                            'seed': self.utils_instance.rand_gaussian(500, 500), # More varied seed
                            'args': mount_args
                        })
                        # Mark this slot and nearby slots as occupied for mountains
                        self.planmtx[plan_column_idx] = entity_x_actual + self.entity_widths_approx['mountain']

            # --- Distant Mountain Planning ---
            # Place these less frequently, e.g., one per few chunk_widths or based on noise
            # JS places them if abs(i)%1000 < scr.val (scroll speed)
            # This means roughly every 1000 pixels of planned area if scroll speed allows.
            if abs(math.floor(current_x_plan_node)) % 1000 < x_step: # Check once per 1000px interval
                dist_mount_args = {
                    'hei': 200 + random.random() * 200,
                    'len': self.entity_widths_approx['distmount'], # Length is its width
                    'seg': 5 + random.randint(0,5) # Number of segments
                }
                planned_entities.append({
                    'type': 'distmount',
                    'x': current_x_plan_node, # Usually starts at edge of view or specific planned point
                    'y': self.y_offsets['distmount'],
                    'seed': random.random() * 1000,
                    'args': dist_mount_args
                })

            # --- Flat Mountain Planning ---
            # JS: if planmtx for this column is empty and random chance
            flat_mount_plan_col_idx = math.floor(current_x_plan_node / self.entity_widths_approx['flatmount'])
            if self.planmtx.get(flat_mount_plan_col_idx, 0) < current_x_plan_node and random.random() < 0.02: # Low probability
                flat_mount_args = {
                    'wid': self.entity_widths_approx['flatmount'] * self.utils_instance.norm_rand(0.9, 1.1),
                    'hei': 100 + random.random() * 100,
                    # flatmount specific args like 'dec': True/False for decorations
                }
                planned_entities.append({
                    'type': 'flatmount',
                    'x': current_x_plan_node,
                    'y': self.y_offsets['flatmount'],
                    'seed': random.random() * 1000,
                    'args': flat_mount_args
                })
                self.planmtx[flat_mount_plan_col_idx] = current_x_plan_node + self.entity_widths_approx['flatmount']

            # --- Boat Planning ---
            # Boats are simpler, placed randomly with some y variation.
            if random.random() < 0.005: # Very low probability for boats per planning node
                boat_args = {
                    'len': 80 + random.random() * 70,
                    # Scale and flip will be set in _generate_chunk_data based on y position
                }
                planned_entities.append({
                    'type': 'boat',
                    'x': current_x_plan_node + self.utils_instance.norm_rand(-x_step*2, x_step*2), # Wider placement jitter
                    'y': self.y_offsets['boat'] + self.utils_instance.norm_rand(-100, 100),
                    'seed': random.random() * 1000,
                    'args': boat_args
                })

        return planned_entities

    def _generate_chunk_data(self, chunk_x_start):
        """
        Generates drawing commands for a specific chunk.
        These commands are tuples: (draw_function, x, y, seed, args_dict).
        The actual drawing happens during the render phase, using these commands.
        """
        chunk_x_end = chunk_x_start + self.chunk_width

        # Get planned entities for this specific x-range.
        # Note: _plan_entities_for_chunk might generate entities slightly outside this exact range
        # if their 'x' is jittered. We might need to filter them here or ensure planning is precise.
        # For now, assume entities returned are meant for this chunk or will be culled at render time.
        entities_in_chunk_range = self._plan_entities_for_chunk(chunk_x_start, chunk_x_end)

        drawing_commands = []

        for entity in entities_in_chunk_range:
            entity_type = entity['type']
            draw_func = None
            args = entity.get('args', {}) # Ensure args is always a dict

            # Add palette info to args for each entity, so drawing functions can use it
            args['palette_type'] = self.palette_type
            args['current_palette'] = self.current_palette
            args['_type'] = entity_type # Store type for width lookup in render

            if entity_type == 'mountain':
                draw_func = self.mount_instance.draw_mountain
            elif entity_type == 'flatmount':
                draw_func = self.mount_instance.draw_flat_mountain
                # Example: flatmounts might have specific default decoration settings
                args.setdefault('dec', self.utils_instance.rand_choice([True, True, False]))
            elif entity_type == 'distmount':
                draw_func = self.mount_instance.draw_dist_mountain
            elif entity_type == 'boat':
                draw_func = self.arch_instance.draw_boat01
                # Boat specific argument adjustments from JS
                args['sca'] = entity['y'] / 800.0 # Scale based on y-position
                args['fli'] = random.choice([True, False])
                # Ensure common args like 'col' are set if not in entity['args']
                args.setdefault('col', BOAT_STROKE_COLOR_INDEX) # Placeholder from drawing.py
                args.setdefault('man_body_col', "dark_blue") # Example color for boatman

            # TODO: Add other entity types like 'tree', 'arch', 'rock'
            # elif entity_type == 'tree01': # Example for a specific tree type
            #     draw_func = self.tree_instance.tree01
            #     args.setdefault('col', TREE_COLOR_INDEX) # Placeholder

            if draw_func:
                # Command: (function, x_pos, y_pos, seed, arguments_dict)
                # Note: x,y,seed are top-level in entity dict, args contains drawing-specific params
                drawing_commands.append((
                    draw_func,
                    entity['x'],
                    entity['y'],
                    entity['seed'],
                    args
                ))

        self.chunks[chunk_x_start] = drawing_commands

        if chunk_x_start not in self.loaded_chunk_x_coords:
            self.loaded_chunk_x_coords.append(chunk_x_start)
            self.loaded_chunk_x_coords.sort()

        # Update overall loaded range
        if self.min_loaded_x is None or chunk_x_start < self.min_loaded_x:
            self.min_loaded_x = chunk_x_start
        if self.max_loaded_x is None or (chunk_x_start + self.chunk_width) > self.max_loaded_x:
            self.max_loaded_x = chunk_x_start + self.chunk_width

        # print(f"Generated data for chunk: {chunk_x_start}. Total loaded: {len(self.loaded_chunk_x_coords)}")

    def ensure_chunks_loaded(self, current_camera_x):
        """
        Checks if chunks around the current_camera_x are loaded,
        and triggers generation if not.
        Placeholder for now.
        """
        if self.chunk_width <= 0: # Safety check
            print("Error: chunk_width must be positive.")
            return

        # Initial load if no chunks are loaded
        if self.min_loaded_x is None or self.max_loaded_x is None:
            initial_chunk_x_start = math.floor(current_camera_x / self.chunk_width) * self.chunk_width
            self._generate_chunk_data(initial_chunk_x_start)
            # After _generate_chunk_data, min_loaded_x and max_loaded_x are set.
            if not self.loaded_chunk_x_coords: # Should not happen if _generate_chunk_data worked
                self.min_loaded_x = initial_chunk_x_start
                self.max_loaded_x = initial_chunk_x_start + self.chunk_width
                # Manually add to loaded_chunk_x_coords if _generate_chunk_data didn't (e.g. if it was empty)
                if initial_chunk_x_start not in self.loaded_chunk_x_coords:
                    self.loaded_chunk_x_coords.append(initial_chunk_x_start)
                    self.loaded_chunk_x_coords.sort()


        # Load chunks on the right (ahead of view)
        # Load up to one full view_width plus an extra chunk ahead
        while self.max_loaded_x < current_camera_x + self.view_width + self.chunk_width:
            self._generate_chunk_data(self.max_loaded_x) # max_loaded_x is end of current last chunk, so it's start of new one

        # Load chunks on the left (behind view)
        # Load up to one extra chunk behind the current view window start
        while self.min_loaded_x > current_camera_x - self.chunk_width:
            self._generate_chunk_data(self.min_loaded_x - self.chunk_width)

        # Unloading Logic
        # Keep a certain span of chunks loaded, e.g., 3 times view_width
        max_loaded_span = self.view_width * 3
        # Ensure we have more than a minimum number of chunks before unloading
        # e.g., enough to cover max_loaded_span or at least a few chunks.
        min_chunks_to_keep = math.ceil(max_loaded_span / self.chunk_width)
        if min_chunks_to_keep < 3: min_chunks_to_keep = 3 # Keep at least a few

        while (self.max_loaded_x - self.min_loaded_x) > max_loaded_span and \
              len(self.loaded_chunk_x_coords) > min_chunks_to_keep:

            dist_left_edge_to_view = current_camera_x - self.min_loaded_x
            dist_right_edge_to_view = self.max_loaded_x - (current_camera_x + self.view_width)

            if dist_left_edge_to_view > dist_right_edge_to_view: # Unload from left (left side is further from view)
                if not self.loaded_chunk_x_coords: break # Safety
                chunk_to_remove_x = self.loaded_chunk_x_coords.pop(0)
                if chunk_to_remove_x in self.chunks:
                    del self.chunks[chunk_to_remove_x]
                # print(f"Unloaded left chunk: {chunk_to_remove_x}")
                self.min_loaded_x = self.loaded_chunk_x_coords[0] if self.loaded_chunk_x_coords else self.max_loaded_x
            else: # Unload from right
                if not self.loaded_chunk_x_coords: break # Safety
                chunk_to_remove_x = self.loaded_chunk_x_coords.pop(-1)
                if chunk_to_remove_x in self.chunks:
                    del self.chunks[chunk_to_remove_x]
                # print(f"Unloaded right chunk: {chunk_to_remove_x}")
                self.max_loaded_x = self.loaded_chunk_x_coords[-1] + self.chunk_width if self.loaded_chunk_x_coords else self.min_loaded_x

            if not self.loaded_chunk_x_coords: # All chunks got unloaded
                self.min_loaded_x = None
                self.max_loaded_x = None
                # print("All chunks unloaded.")
                break
        # print(f"Ensure Chunks: Loaded {len(self.loaded_chunk_x_coords)} chunks from {self.min_loaded_x} to {self.max_loaded_x}")


    def render_visible_chunks(self, current_camera_x):
        """
        Renders the drawing commands from currently visible chunks to the display_bitmap.
        """
        try:
            from lib import color_utils # Import here to ensure it's found
        except ImportError:
            print("Error: lib.color_utils could not be imported for render_visible_chunks.")
            # Fallback: try to fill with a raw index like 0 if import fails
            self.display_bitmap.fill(0)
            return

        # Determine the white color index for clearing the bitmap
        # Assuming BW_WHITE is an abstract constant like 0xFFFFFF or similar
        # and get_palette_color_index can map it.
        # If palette is BW, BW_WHITE might map to 0 or 1 depending on palette order.
        # For safety, let's request a known abstract like "white".
        # This depends on how color_utils and specific palettes are defined.
        # A more robust way: pass an abstract "clear_color_request" to LandscapeManager init.
        try:
            white_idx = color_utils.get_palette_color_index("white", self.palette_type, self.current_palette)
        except Exception as e:
            # print(f"Error getting white_idx: {e}. Defaulting to 0.")
            white_idx = 0 # Default to palette index 0 if "white" is not resolvable

        self.display_bitmap.fill(white_idx)

        if not self.loaded_chunk_x_coords:
            return # No chunks to render

        for x_coord_chunk_start in self.loaded_chunk_x_coords:
            chunk_x_end = x_coord_chunk_start + self.chunk_width

            # Check if this chunk is visible at all
            if not (chunk_x_end > current_camera_x and x_coord_chunk_start < current_camera_x + self.view_width):
                continue # Chunk is not visible

            chunk_drawing_commands = self.chunks.get(x_coord_chunk_start, [])

            for cmd_idx, command_tuple in enumerate(chunk_drawing_commands):
                if len(command_tuple) == 5:
                    draw_func, entity_x, entity_y, entity_seed, entity_args_orig = command_tuple
                else:
                    # print(f"Warning: Malformed drawing command in chunk {x_coord_chunk_start}, cmd_idx {cmd_idx}")
                    continue

                screen_x = entity_x - current_camera_x

                # Visibility check for the entity itself
                # Get entity type from the arguments dictionary where it was stored
                entity_type_for_width = entity_args_orig.get('_type', 'mountain') # Default to 'mountain' if not found
                approx_entity_width = self.entity_widths_approx.get(entity_type_for_width, 200) # Default width

                if not (screen_x + approx_entity_width > 0 and screen_x < self.view_width):
                    continue # Entity is not visible on screen

                entity_args_copy = entity_args_orig.copy()

                # Palette type and current_palette should already be in entity_args_copy
                # from _generate_chunk_data. No need to pop and re-add from self.
                palette_type_to_use = entity_args_copy.get('palette_type')
                current_palette_to_use = entity_args_copy.get('current_palette')

                if palette_type_to_use is None or current_palette_to_use is None:
                    # print(f"Warning: Palette info missing in entity args for {entity_type_for_width}. Using manager's defaults.")
                    palette_type_to_use = self.palette_type
                    current_palette_to_use = self.current_palette

                # Ensure seed is in args if drawing function expects it.
                # Mount/Arch/Tree drawing functions take (bitmap, x, y, seed, args, palette_type, current_palette)
                # So seed is a separate param. The args dict passed to them is entity_args_copy.

                # Corrected call to drawing function:
                # The drawing functions from drawing.py (e.g., Mount.draw_mountain) expect:
                # (self, bitmap, x_offset, y_offset, seed, args_mountain, palette_type, current_palette)
                # So, entity_seed is passed as the 4th positional argument after x, y.
                # entity_args_copy is passed as the 'args_...' argument.
                try:
                    draw_func(self.display_bitmap, screen_x, entity_y, entity_seed, entity_args_copy, palette_type_to_use, current_palette_to_use)
                except Exception as e:
                    # print(f"Error drawing entity: type={entity_type_for_width}, x={screen_x}, y={entity_y}, seed={entity_seed}, args={entity_args_copy}")
                    # print(f"Exception: {e}")
                    pass # Continue rendering other entities

# Example color constants (if not imported or defined elsewhere)
# These would typically come from a central color definitions module or be part of palette handling
BOAT_STROKE_COLOR_INDEX = 1
TREE_COLOR_INDEX = 1
MOUNTAIN_COLOR_INDEX = 1
globals().update({"BOAT_STROKE_COLOR_INDEX":1, "TREE_COLOR_INDEX":1, "MOUNTAIN_COLOR_INDEX":1}) # Hack for tool
