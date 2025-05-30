import displayio
import math
import random
from lib.perlin_noise import PerlinNoise
from lib.utils import loop_noise

# Global PerlinNoise instance
perlin_noise_instance = PerlinNoise()

# Coordinate System Note: Assumes (x,y) map directly to pixels.

def draw_line(bitmap, x0, y0, x1, y1, color_index):
    """Draws a line using Bresenham's algorithm."""
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < bitmap.width and 0 <= y0 < bitmap.height:
            bitmap[x0, y0] = color_index
        if x0 == x1 and y0 == y1: break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

def draw_polygon(bitmap, points, color_index):
    """Draws the outline of a polygon."""
    if not points or len(points) < 2: return
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        if not (isinstance(p1, (list, tuple)) and len(p1) == 2 and
                isinstance(p2, (list, tuple)) and len(p2) == 2):
            # print(f"Warning: Invalid point format in draw_polygon: {p1}, {p2}") # Reduce noise
            continue
        # OLD OUTLINE LOGIC: draw_line(bitmap, p1[0], p1[1], p2[0], p2[1], color_index)
        pass # Outline drawing is removed, filling is done below via triangulation

    # Triangulation and filling logic
    # This assumes PolyTools is imported and an instance is available.
    # If poly_tools_instance is not globally available or passed, this needs adjustment.
    # For now, let's assume it's available as in the Tree class structure.
    # This might mean draw_polygon needs access to self.poly_tools if it becomes a class method,
    # or poly_tools_instance needs to be passed or created here.

    # Create a PolyTools instance here if not passed or globally available.
    # This is less efficient if draw_polygon is called many times.
    # Consider making poly_tools_instance an argument or part of a class.
    if not hasattr(draw_polygon, "poly_tools_instance"): # Create instance once
        # This creates a circular dependency if PolyTools itself uses draw_polygon
        # For now, assuming PolyTools is independent or this is resolved by structure.
        try:
            # Assuming PolyTools is in lib.poly_tools
            from lib.poly_tools import PolyTools
            draw_polygon.poly_tools_instance = PolyTools()
        except ImportError:
            print("Error: lib.poly_tools.PolyTools could not be imported for draw_polygon.")
            # Fallback to outline if triangulation is not possible
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]
                if not (isinstance(p1, (list, tuple)) and len(p1) == 2 and
                        isinstance(p2, (list, tuple)) and len(p2) == 2):
                    continue
                draw_line(bitmap, p1[0], p1[1], p2[0], p2[1], color_index)
            return


    if hasattr(draw_polygon, "poly_tools_instance"):
        # Triangulation args: 'area' is a threshold. Smaller means more triangles.
        # 'convex' and 'optimize' are PolyTools specific.
        # The points list might need to be cleaned of None values or invalid points
        # before passing to triangulate, depending on its robustness.
        valid_points = [p for p in points if p and isinstance(p, (tuple, list)) and len(p) == 2]
        if len(valid_points) < 3: # Not enough points for a polygon to triangulate
             # Draw lines for 2 points, or nothing for < 2.
            if len(valid_points) == 2:
                draw_line(bitmap, valid_points[0][0], valid_points[0][1], valid_points[1][0], valid_points[1][1], color_index)
            return

        try:
            triangles = draw_polygon.poly_tools_instance.triangulate(valid_points, {'area': 1}) # Small area for more detail
        except Exception as e:
            # print(f"Error during triangulation in draw_polygon: {e}")
            # Fallback to drawing outline if triangulation fails
            for i in range(len(valid_points)):
                p1 = valid_points[i]
                p2 = valid_points[(i + 1) % len(valid_points)]
                draw_line(bitmap, p1[0], p1[1], p2[0], p2[1], color_index)
            return

        if triangles:
            for triangle in triangles:
                if triangle and len(triangle) == 3:
                    _fill_triangle(bitmap, triangle[0], triangle[1], triangle[2], color_index)
                # else:
                    # print(f"Warning: Invalid triangle from triangulation: {triangle}")
        # else:
            # print(f"Warning: Triangulation returned no triangles for points: {valid_points}")
            # Fallback to outline if triangulation returns nothing
            # for i in range(len(valid_points)):
            #     p1 = valid_points[i]
            #     p2 = valid_points[(i + 1) % len(valid_points)]
            #     draw_line(bitmap, p1[0], p1[1], p2[0], p2[1], color_index)


# Helper function to fill a triangle (scanline algorithm)
def _fill_triangle(bitmap, p0, p1, p2, color_index):
    """Fills a triangle using a scanline algorithm."""
    # Sort vertices by y-coordinate (p0.y <= p1.y <= p2.y)
    points = sorted([p0, p1, p2], key=lambda pt: pt[1])
    v0, v1, v2 = points[0], points[1], points[2]

    # Ensure points are integer coordinates for scanline iteration
    v0 = (int(round(v0[0])), int(round(v0[1])))
    v1 = (int(round(v1[0])), int(round(v1[1])))
    v2 = (int(round(v2[0])), int(round(v2[1])))

    # Case 1: Triangle with a flat bottom (v1.y == v2.y)
    if v1[1] == v2[1]:
        _fill_flat_bottom_triangle(bitmap, v0, v1, v2, color_index)
    # Case 2: Triangle with a flat top (v0.y == v1.y)
    elif v0[1] == v1[1]:
        _fill_flat_top_triangle(bitmap, v0, v1, v2, color_index)
    # Case 3: General triangle, split into two triangles (one flat top, one flat bottom)
    else:
        # Find the x-coordinate of the point on the edge v0-v2 at the y-level of v1
        # Using float for precision in division
        if (v2[1] - v0[1]) == 0: # Avoid division by zero if v0 and v2 have same y
            vx = v0[0]
        else:
            vx = v0[0] + (float(v1[1] - v0[1]) / float(v2[1] - v0[1])) * (v2[0] - v0[0])
        v_split = (int(round(vx)), v1[1])

        _fill_flat_bottom_triangle(bitmap, v0, v1, v_split, color_index)
        _fill_flat_top_triangle(bitmap, v1, v_split, v2, color_index)

def _fill_flat_bottom_triangle(bitmap, v0, v1, v2, color_index):
    """Helper for filling a flat-bottom triangle (v1.y == v2.y)."""
    # v0 is the top vertex
    # Ensure v1 is to the left of v2 if they share y
    if v1[0] > v2[0]:
        v1, v2 = v2, v1 # Swap

    # Slopes of the two non-horizontal edges
    # Inverse slopes (dx/dy) are used for scanline algorithm
    inv_slope1 = (float(v1[0] - v0[0]) / float(v1[1] - v0[1])) if (v1[1] - v0[1]) != 0 else 0
    inv_slope2 = (float(v2[0] - v0[0]) / float(v2[1] - v0[1])) if (v2[1] - v0[1]) != 0 else 0

    x_start = float(v0[0])
    x_end = float(v0[0])

    # Iterate from top vertex y down to the flat bottom y
    for y in range(v0[1], v1[1] + 1):
        # Fill pixels between x_start and x_end on the current scanline
        # Ensure x_start is to the left of x_end
        x_draw_start = int(round(min(x_start, x_end)))
        x_draw_end = int(round(max(x_start, x_end)))

        for x in range(x_draw_start, x_draw_end + 1):
            if 0 <= x < bitmap.width and 0 <= y < bitmap.height:
                bitmap[x, y] = color_index

        x_start += inv_slope1
        x_end += inv_slope2

def _fill_flat_top_triangle(bitmap, v0, v1, v2, color_index):
    """Helper for filling a flat-top triangle (v0.y == v1.y)."""
    # v2 is the bottom vertex
    # Ensure v0 is to the left of v1 if they share y
    if v0[0] > v1[0]:
        v0, v1 = v1, v0 # Swap

    inv_slope1 = (float(v2[0] - v0[0]) / float(v2[1] - v0[1])) if (v2[1] - v0[1]) != 0 else 0
    inv_slope2 = (float(v2[0] - v1[0]) / float(v2[1] - v1[1])) if (v2[1] - v1[1]) != 0 else 0

    x_start = float(v2[0])
    x_end = float(v2[0])

    # Iterate from bottom vertex y up to the flat top y
    for y in range(v2[1], v0[1] - 1, -1): # Iterate downwards
        x_draw_start = int(round(min(x_start, x_end)))
        x_draw_end = int(round(max(x_start, x_end)))

        for x in range(x_draw_start, x_draw_end + 1):
            if 0 <= x < bitmap.width and 0 <= y < bitmap.height:
                bitmap[x,y] = color_index

        x_start -= inv_slope1 # Subtract because we are going upwards
        x_end -= inv_slope2   # Subtract because we are going upwards


def draw_stroke(bitmap, points, args):
    """Draws a stroke with variable width and noise."""
    if not points or len(points) < 2: return
    wid = args.get('wid', 2)
    col = args.get('col', 1)
    noi = args.get('noi', 0.5)
    default_fun = lambda x: math.sin(x * math.pi)
    fun = args.get('fun', default_fun)
    vtxlist0, vtxlist1 = [], []
    n0 = random.random() * 10

    if len(points) <=2:
        if len(points) == 2: draw_line(bitmap, points[0][0], points[0][1], points[1][0], points[1][1], col)
        return

    for i in range(1, len(points) - 1):
        w = wid * fun(i / len(points))
        noise_val = perlin_noise_instance.noise(i * 0.5, n0)
        w = w * (1 - noi) + w * noi * noise_val
        p_curr, p_prev, p_next = points[i], points[i-1], points[i+1]
        a1 = math.atan2(p_curr[1] - p_prev[1], p_curr[0] - p_prev[0])
        a2 = math.atan2(p_curr[1] - p_next[1], p_curr[0] - p_next[0])
        a = (a1 + a2) / 2
        if a < a2: a += math.pi
        vtxlist0.append((p_curr[0] + w * math.cos(a), p_curr[1] + w * math.sin(a)))
        vtxlist1.append((p_curr[0] - w * math.cos(a), p_curr[1] - w * math.sin(a)))

    if not vtxlist0 or not vtxlist1:
        if len(points) >= 2: draw_line(bitmap, points[0][0], points[0][1], points[-1][0], points[-1][1], col)
        return
    final_vtxlist = [points[0]] + vtxlist0 + [points[-1]] + vtxlist1[::-1] + [points[0]]
    draw_polygon(bitmap, final_vtxlist, col)

def get_blob_points(x_center, y_center, args, noise_instance_ref):
    """Calculates and returns the vertices of a blob shape."""
    blob_len = args.get('len', 20)
    blob_wid = args.get('wid', 5)
    angle = args.get('ang', 0)
    noise_factor = args.get('noi', 0.5)
    default_fun = lambda p_val: math.pow(math.sin(p_val * math.pi), 0.5) if p_val <= 1 \
        else -math.pow(math.sin((p_val + 1) * math.pi), 0.5)
    shape_fun = args.get('fun', default_fun)
    reso = 20.0
    lalist = []
    for i in range(int(reso) + 1):
        p_val = (i / reso) * 2
        xo = blob_len / 2 - abs(p_val - 1) * blob_len
        yo = (shape_fun(p_val) * blob_wid) / 2
        la_angle = math.atan2(yo, xo)
        la_length = math.sqrt(xo**2 + yo**2)
        lalist.append([la_length, la_angle])
    nslist = []
    n0 = random.random() * 10
    for i in range(int(reso) + 1):
        nslist.append(noise_instance_ref.noise(i * 0.05, n0)) # Use passed instance
    loop_noise(nslist)
    plist = []
    for i in range(len(lalist)):
        noise_scale = nslist[i] * noise_factor + (1 - noise_factor)
        current_l = lalist[i][0] * noise_scale
        current_a = lalist[i][1] + angle
        nx = x_center + math.cos(current_a) * current_l
        ny = y_center + math.sin(current_a) * current_l
        plist.append((nx, ny))
    return plist

def draw_blob(bitmap, x_center, y_center, args):
    """Draws a blob shape by generating points and then drawing the polygon."""
    points = get_blob_points(x_center, y_center, args, perlin_noise_instance)
    color_index = args.get('col', 1)
    if points:
        draw_polygon(bitmap, points, color_index)

# Color Handling Note (repeated for context):
# JS RGBA strings vs CircuitPython palette indices. 'col' args should be indices.
# Alpha/variations imply using different pre-defined palette indices.

# Placeholder color indices
WHITE_COLOR_INDEX = 0
FOOT_STROKE_COLOR_INDEX = 1
MOUNTAIN_OUTLINE_COLOR_INDEX = 1
FLAT_TOP_STROKE_COLOR_INDEX = 1
ROCK_OUTLINE_COLOR_INDEX = 1
BOX_STROKE_COLOR_INDEX = 1
RAIL_STROKE_COLOR_INDEX = 1
MAN_COLOR_INDEX = 1 # Assuming 1 is a visible color
ROOF_STROKE_COLOR_INDEX = 1
PAGODA_ROOF_STROKE_COLOR_INDEX = 1
BOAT_STROKE_COLOR_INDEX = 1
TOWER_STROKE_COLOR_INDEX = 1


from lib.poly_tools import PolyTools
import lib.utils

class Mount:
    def __init__(self, noise_instance, utils_module, poly_tools_instance, tree_instance, arch_instance=None): # Added arch_instance
        self.noise_instance = noise_instance
        self.utils = utils_module
        self.poly_tools = poly_tools_instance
        self.tree_instance = tree_instance
        self.arch_instance = arch_instance # Store arch_instance
        # Mountain methods might create their own specifically seeded noise instances.

    def _draw_mountain_foot(self, bitmap, ptlist_local, x_offset, y_offset, args):
        if not ptlist_local or not isinstance(ptlist_local, list) or not ptlist_local[0]:
            return

        ftlist_polygons_local = []
        span = 10
        ni = 0

        for i in range(len(ptlist_local) - 2):
            if i == ni:
                ni = min(ni + random.choice([1,2]), len(ptlist_local) -1)
                if i >= len(ptlist_local) or ni >= len(ptlist_local): break

                current_layer = ptlist_local[i]
                next_layer = ptlist_local[ni]

                if not current_layer or not next_layer or len(current_layer) == 0 or len(next_layer) == 0:
                    continue

                poly1_local, poly2_local = [], []
                min_len_detail = min(math.floor(len(current_layer) / 8) if len(current_layer) > 0 else 0, 10)

                for j in range(min_len_detail):
                    if j < len(current_layer):
                        poly1_local.append((
                            current_layer[j][0] + self.noise_instance.noise(j * 0.1, i * 0.11) * 10, # Varied noise slightly
                            current_layer[j][1]
                        ))
                    if len(current_layer) -1 -j >= 0 :
                         poly2_local.append((
                            current_layer[len(current_layer) - 1 - j][0] - self.noise_instance.noise(j * 0.1, i * 0.12) * 10, # Varied noise slightly
                            current_layer[len(current_layer) - 1 - j][1]
                        ))

                poly1_local.reverse()
                poly2_local.reverse()

                for j_interp in range(span + 1):
                    p_factor = j_interp / span
                    if not current_layer or not next_layer or not current_layer[0] or not next_layer[0] or not current_layer[-1] or not next_layer[-1]: continue

                    x1_interp = current_layer[0][0] * (1 - p_factor) + next_layer[0][0] * p_factor
                    y1_interp = current_layer[0][1] * (1 - p_factor) + next_layer[0][1] * p_factor
                    x2_interp = current_layer[-1][0] * (1 - p_factor) + next_layer[-1][0] * p_factor
                    y2_interp = current_layer[-1][1] * (1 - p_factor) + next_layer[-1][1] * p_factor
                    vib = -1.7 * (p_factor - 1) * math.pow(p_factor, 1/5) if p_factor > 0 else 0

                    y1_interp += vib * 5 + self.noise_instance.noise(i * 0.51, j_interp * 0.21) * 5
                    y2_interp += vib * 5 + self.noise_instance.noise(i * 0.52, j_interp * 0.22) * 5

                    poly1_local.append((x1_interp, y1_interp))
                    poly2_local.append((x2_interp, y2_interp))

                if poly1_local: ftlist_polygons_local.append(poly1_local)
                if poly2_local: ftlist_polygons_local.append(poly2_local)

        for poly_local_pts in ftlist_polygons_local:
            if not poly_local_pts or len(poly_local_pts) < 2: continue
            poly_global_pts = [(pt[0] + x_offset, pt[1] + y_offset) for pt in poly_local_pts]
            draw_polygon(bitmap, poly_global_pts, WHITE_COLOR_INDEX)
            stroke_args_foot = {
                'col': FOOT_STROKE_COLOR_INDEX, 'wid': 1,
                'noi': 0.1, 'fun': lambda x_prog: 1
            }
            draw_stroke(bitmap, poly_global_pts, stroke_args_foot)

    def _draw_flat_decs(self, bitmap, x_mountain_base, y_mountain_base, grbd_local):
        """Draws decorations on the flat top of a mountain."""
        if not grbd_local or not self.tree_instance: # Ensure tree_instance is available
            return

        # TODO: Implement or import self.utils.bound_box if truly needed.
        # For now, grbd_local is assumed to be {'xmin':..., 'xmax':..., 'ymin':..., 'ymax':...}
        # relative to the mountain's local (0,0).

        # Draw rocks
        for _ in range(int(random.random() * 5)):
            rock_args = {
                'wid': 10 + random.random() * 20,
                'hei': 10 + random.random() * 20,
                'sha': 2,
                'tex': 20 # Fewer textures for smaller rocks
            }
            # Position rocks within the flat area, then transform to global
            rock_x_local = self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax'])
            # Y for rocks on flat top: use average of ymin/ymax + some offset, then global transform
            rock_y_local = (grbd_local['ymin'] + grbd_local['ymax']) / 2 + self.utils.norm_rand(-10, 10) + 10

            self.draw_rock(bitmap,
                           x_mountain_base + rock_x_local,
                           y_mountain_base + rock_y_local,
                           random.random() * 100, rock_args)

        # Draw clusters of trees (e.g., tree08)
        for _ in range(random.choice([0,0,1,2])): # Number of tree clusters
            cluster_center_x_local = self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax'])
            cluster_center_y_local = (grbd_local['ymin'] + grbd_local['ymax']) / 2 + self.utils.norm_rand(-5,5) + 20

            for _ in range(int(2 + random.random() * 3)): # Number of trees per cluster
                tree_x_local = cluster_center_x_local + self.utils.norm_rand(-30,30)
                # Ensure tree is within the flat area's x-bounds
                tree_x_local = max(grbd_local['xmin'], min(grbd_local['xmax'], tree_x_local))

                tree_args_08 = {
                    'hei': 60 + random.random() * 40,
                    'col': MOUNTAIN_OUTLINE_COLOR_INDEX # Example color
                }
                self.tree_instance.tree08(bitmap,
                                           x_mountain_base + tree_x_local,
                                           y_mountain_base + cluster_center_y_local,
                                           tree_args_08)

        # Logic for different types of larger features based on 'tt' from JS
        tt = random.choice([0,0,1,2,3,4])

        if tt == 0: # More rocks
            for _ in range(int(random.random() * 3)):
                rock_args_large = {
                    'wid': 50 + random.random() * 20, 'hei': 40 + random.random() * 20, 'sha': 5, 'tex': 30
                }
                rock_x_l = self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax'])
                rock_y_l = (grbd_local['ymin'] + grbd_local['ymax']) / 2 + self.utils.norm_rand(-5,5) + 20
                self.draw_rock(bitmap, x_mountain_base + rock_x_l, y_mountain_base + rock_y_l, random.random()*100, rock_args_large)

        elif tt == 1: # Grove of tree05
            pmin_factor = random.random() * 0.5
            pmax_factor = random.random() * 0.5 + 0.5
            xmin_grove = grbd_local['xmin'] * (1-pmin_factor) + grbd_local['xmax'] * pmin_factor
            xmax_grove = grbd_local['xmin'] * (1-pmax_factor) + grbd_local['xmax'] * pmax_factor

            for x_tree_local in range(int(xmin_grove), int(xmax_grove), 30):
                tree05_args = {'hei': 100 + random.random() * 200, 'col': MOUNTAIN_OUTLINE_COLOR_INDEX}
                self.tree_instance.tree05(bitmap,
                                           x_mountain_base + x_tree_local + self.utils.norm_rand(-20,20),
                                           y_mountain_base + (grbd_local['ymin'] + grbd_local['ymax']) / 2 + 20,
                                           tree05_args)
            # Add some rocks around the grove
            for _ in range(int(random.random()*4)):
                rock_args_grove = {'wid': 50 + random.random()*20, 'hei': 40 + random.random()*20, 'sha':5, 'tex':30}
                rock_x_g = self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax'])
                rock_y_g = (grbd_local['ymin'] + grbd_local['ymax']) / 2 + self.utils.norm_rand(-5,5) + 20
                self.draw_rock(bitmap, x_mountain_base + rock_x_g, y_mountain_base + rock_y_g, random.random()*100, rock_args_grove)


        elif tt == 2: # tree04 with rocks
            for _ in range(random.choice([1,1,1,1,2,2,3])):
                xr_local = self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax'])
                yr_local = (grbd_local['ymin'] + grbd_local['ymax']) / 2
                tree04_args = {'col': MOUNTAIN_OUTLINE_COLOR_INDEX, 'hei': 150 + random.random()*50} # Example hei
                self.tree_instance.tree04(bitmap, x_mountain_base + xr_local, y_mountain_base + yr_local + 20, tree04_args)
                for _ in range(int(random.random()*2)):
                    rock_args_t04 = {'wid':50+random.random()*20, 'hei':40+random.random()*20, 'sha':5, 'tex':30}
                    rock_x_t04 = max(grbd_local['xmin'], min(grbd_local['xmax'], xr_local + self.utils.norm_rand(-50,50)))
                    self.draw_rock(bitmap, x_mountain_base+rock_x_t04, y_mountain_base+yr_local+self.utils.norm_rand(-5,5)+20, random.random()*100, rock_args_t04)

        elif tt == 3: # tree06
            for _ in range(random.choice([1,1,1,1,2,2,3])):
                tree06_args = {'hei': 60 + random.random()*60, 'col': MOUNTAIN_OUTLINE_COLOR_INDEX}
                self.tree_instance.tree06(bitmap,
                                           x_mountain_base + self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax']),
                                           y_mountain_base + (grbd_local['ymin'] + grbd_local['ymax']) / 2,
                                           tree06_args)
        elif tt == 4: # tree07 grove
            pmin_factor = random.random() * 0.5
            pmax_factor = random.random() * 0.5 + 0.5
            xmin_grove_t07 = grbd_local['xmin'] * (1-pmin_factor) + grbd_local['xmax'] * pmin_factor
            xmax_grove_t07 = grbd_local['xmin'] * (1-pmax_factor) + grbd_local['xmax'] * pmax_factor
            for x_tree_local_t07 in range(int(xmin_grove_t07), int(xmax_grove_t07), 20):
                tree07_args = {'hei': self.utils.norm_rand(40,80), 'col': MOUNTAIN_OUTLINE_COLOR_INDEX}
                self.tree_instance.tree07(bitmap,
                                           x_mountain_base + x_tree_local_t07 + self.utils.norm_rand(-20,20),
                                           y_mountain_base + (grbd_local['ymin'] + grbd_local['ymax'])/2 + self.utils.norm_rand(-1,1),
                                           tree07_args)

        # General small shrubs (tree02)
        for _ in range(int(50 * random.random())):
            tree02_args = {'col': MOUNTAIN_OUTLINE_COLOR_INDEX} # Default size for tree02
            self.tree_instance.tree02(bitmap,
                                       x_mountain_base + self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax']),
                                       y_mountain_base + self.utils.norm_rand(grbd_local['ymin'], grbd_local['ymax']),
                                       tree02_args)

        # Call Arch.arch01 if instance is available
        if hasattr(self, 'arch_instance') and self.arch_instance:
            ts = random.choice([0,0,0,0,1])
            if ts == 1 and tt != 4: # Condition from JS
                arch_x_local = self.utils.norm_rand(grbd_local['xmin'], grbd_local['xmax'])
                arch_y_local = (grbd_local['ymin'] + grbd_local['ymax']) / 2 + 20

                arch01_args = {
                    'wid': self.utils.norm_rand(160, 200),
                    'hei': self.utils.norm_rand(80, 100),
                    'per': random.random(), # Perspective factor
                    'rot': random.random()*0.4+0.3, # Rotation factor for internal box
                    'col': BOX_STROKE_COLOR_INDEX # Base color for the structure
                }
                # Arch methods would also need palette info if they draw directly.
                # Assuming for now that Arch methods are structured like Mount/Tree methods
                # and will eventually take current_palette, palette_type.
                # For this subtask, the call is made; further refactoring of Arch methods for palette is separate.
                self.arch_instance.draw_arch01(bitmap,
                                               x_mountain_base + arch_x_local,
                                               y_mountain_base + arch_y_local,
                                               random.random(), arch01_args)
                                               # current_palette, palette_type) # Palette args to be added later if needed by arch01


    def draw_rock(self, bitmap, x_offset, y_offset, seed, args_rock):
        """Draws a rock formation."""
        hei = args_rock.get('hei', 80)
        wid = args_rock.get('wid', 100)
        tex_density = args_rock.get('tex', 40)
        shade_amount = args_rock.get('sha', 10) # 'sha' in JS, for shading in texture

        # Seeded noise for this rock
        rock_prng = lib.utils.Prng()
        rock_prng.seed(seed)
        noise_gen = PerlinNoise(prng_instance=rock_prng)

        reso_y = 10 # Layers for rock ptlist
        reso_x = 50 # Points per layer for rock ptlist
        ptlist_layers_local = []

        for i_layer in range(reso_y):
            layer_points = []
            nslist_layer = [] # Noise for this specific layer's circumference
            for j_point_idx in range(reso_x):
                # Use noise_gen which is seeded specifically for this rock
                nslist_layer.append(noise_gen.noise(i_layer, j_point_idx * 0.2))

            # loop_noise needs to be available, ensure it's imported or part of self.utils
            self.utils.loop_noise(nslist_layer) # Modifies nslist_layer in-place

            for j_point_idx in range(reso_x):
                angle_rad = (j_point_idx / reso_x) * math.pi * 2 - math.pi / 2 # From -PI/2 to 3PI/2

                # Elliptical base shape
                # l = (wid * hei) / Math.sqrt(Math.pow(hei * Math.cos(a),2) + Math.pow(wid * Math.sin(a),2));
                # This is the polar equation for an ellipse.
                # Avoid division by zero if hei or wid is zero.
                if hei == 0 or wid == 0:
                    ellipse_radius = 0
                else:
                    ellipse_radius_num = wid * hei
                    ellipse_radius_den_sq = (hei * math.cos(angle_rad))**2 + (wid * math.sin(angle_rad))**2
                    ellipse_radius = ellipse_radius_num / math.sqrt(ellipse_radius_den_sq) if ellipse_radius_den_sq > 0 else 0

                ellipse_radius *= (0.7 + 0.3 * nslist_layer[j_point_idx]) # Modulate radius with looped noise

                p_factor = 1 - i_layer / reso_y # Tapering factor for height

                local_x = math.cos(angle_rad) * ellipse_radius * p_factor
                local_y = -math.sin(angle_rad) * ellipse_radius * p_factor # Y inverted

                # JS: if (Math.PI < a || a < 0) { ny *= 0.2; } (where a is angle_rad)
                # This flattens the bottom of the rock. angle_rad is from -PI/2 to 3PI/2.
                # Condition Math.PI < angle_rad means angle_rad is in range (PI, 3PI/2] (bottom-left quadrant)
                # Condition angle_rad < 0 means angle_rad is in range [-PI/2, 0) (bottom-right quadrant)
                if (math.pi < angle_rad <= 3 * math.pi / 2) or (-math.pi / 2 <= angle_rad < 0):
                    local_y *= 0.2

                # JS: ny += hei * (i / reso[0]) * 0.2; (Shift upper layers down slightly - relative to rock top)
                # This seems to make upper layers "sink" a bit.
                local_y += hei * (i_layer / reso_y) * 0.2

                layer_points.append((local_x, local_y))
            ptlist_layers_local.append(layer_points)

        if not ptlist_layers_local or not ptlist_layers_local[0]: return

        ptlist_layers_global = [[(p[0] + x_offset, p[1] + y_offset) for p in layer] for layer in ptlist_layers_local]

        # Draw white background for the rock
        if ptlist_layers_global[0] and len(ptlist_layers_global[0])>=3:
             # Closing the polygon for fill - might need a flatter bottom line
            outer_rock_shape = ptlist_layers_global[0]
            # A simple way to close: connect last point to first point.
            # If a filled effect is desired, this should be a filled polygon.
            # draw_polygon(bitmap, outer_rock_shape + [outer_rock_shape[0]], WHITE_COLOR_INDEX) # Close it
            draw_polygon(bitmap, outer_rock_shape, WHITE_COLOR_INDEX)


        # Stroke outline
        if ptlist_layers_global[0] and len(ptlist_layers_global[0]) >=2:
            stroke_args_rock_outline = {
                'col': ROCK_OUTLINE_COLOR_INDEX, 'noi': 1, 'wid': 3,
                'fun': lambda x_prog: math.sin(x_prog * math.pi)
            }
            draw_stroke(bitmap, ptlist_layers_global[0], stroke_args_rock_outline)

        # Texture for the rock
        texture_args_rock = {
            'xof': x_offset, 'yof': y_offset,
            'tex': tex_density, 'wid': 3, 'sha': shade_amount,
            'col': lambda p_ratio: int(180 + p_ratio * 0), # Fixed dark grey (assuming 180 is a valid index or maps to one)
                                                          # JS: "rgba(180,180,180,"+(0.3+Math.random()*0.3).toFixed(3)+")"
                                                          # This needs palette mapping. For now, using a placeholder logic.
                                                          # Let's assume FOOT_STROKE_COLOR_INDEX can be used.
                                                          # col_func = lambda p: FOOT_STROKE_COLOR_INDEX,
            'dis': lambda: (0.15 + 0.15 * random.random()) if random.random() > 0.5 else (0.85 - 0.15 * random.random())
        }
        # Ensure the color function returns a valid index for the bitmap palette
        def rock_texture_color_func(p_ratio):
            # Example: map to a few shades of grey if available, or just use one dark color
            # This is highly dependent on the actual palette.
            # If palette is [white, black, grey1, grey2], this might return 1, 2, or 3.
            # For now, returning a fixed index.
            return FOOT_STROKE_COLOR_INDEX # Placeholder
        texture_args_rock['col'] = rock_texture_color_func

        draw_texture(bitmap, ptlist_layers_local, texture_args_rock)

    def draw_dist_mountain(self, bitmap, x_offset, y_offset, seed, args_dist_mount):
        """Draws distant, simpler mountains."""
        hei = args_dist_mount.get('hei', 300)
        length = args_dist_mount.get('len', 2000) # 'len' from JS
        segments = args_dist_mount.get('seg', 5) # 'seg' from JS

        # Seeded noise for this distant mountain
        dist_mount_prng = lib.utils.Prng()
        dist_mount_prng.seed(seed)
        noise_gen = PerlinNoise(prng_instance=dist_mount_prng)

        span = 10 # From JS

        # list_of_polygons_local will store lists of points, each list is a polygon
        list_of_polygons_local = []

        num_main_segments = math.floor(length / span / segments) if segments > 0 and span > 0 else 0

        for i_main_seg in range(num_main_segments):
            current_poly_local = []
            # Generate top edge of the polygon segment
            for j_sub_seg in range(segments + 1):
                k = i_main_seg * segments + j_sub_seg
                # Equivalent of JS tran(k) for top edge
                # yoff is y_offset (global y for the start of this mountain)
                # hei is height of this mountain
                # noise_gen.noise(k * 0.05, seed) - seed in noise call was original JS,
                # but if noise_gen is already seeded, the extra seed arg might be redundant or behave differently.
                # Assuming noise_gen.noise(x,y) is sufficient.
                y_val = y_offset - hei * noise_gen.noise(k * 0.05, 0) * \
                        math.pow(math.sin((math.pi * k) / (length / span if span > 0 else 1)), 0.5) \
                        if (length/span) > 0 else y_offset # Avoid division by zero

                # Store points relative to (x_offset, y_offset) as local for now
                current_poly_local.append( (k * span, y_val - y_offset) )

            # Generate bottom edge of the polygon segment (reversed)
            for j_sub_seg in range(math.floor(segments / 2) + 1):
                k = i_main_seg * segments + (math.floor(segments/2) - j_sub_seg) * 2 # Iterate backwards for x
                 # Equivalent of JS tran(k) for bottom edge
                y_val = y_offset + 24 * noise_gen.noise(k * 0.05, 2) * \
                        math.pow(math.sin((math.pi * k) / (length / span if span > 0 else 1)), 1) \
                        if (length/span) > 0 else y_offset
                current_poly_local.append( (k*span, y_val - y_offset) )

            if current_poly_local:
                list_of_polygons_local.append(current_poly_local)

        # Draw each polygon segment
        for poly_local in list_of_polygons_local:
            if not poly_local or len(poly_local) < 3: continue

            poly_global = [(pt[0] + x_offset, pt[1] + y_offset) for pt in poly_local]

            # Color based on midpoint, similar to JS
            # For poly_tools.mid_pt, we need points relative to some origin, local is fine.
            mid_pt_local = self.poly_tools.mid_pt(poly_local)
            # JS: getCol(m[0],m[1]) where getCol = function(x,y){ var c = (Noise.noise(x*0.02,y*0.02,yoff)*55+200)|0; return "rgb("+c+","+c+","+c+")"}
            # This implies yoff (the mountain's global y_offset) is part of the noise seed here.
            # We need to map the resulting grayscale (200-255) to our palette.
            noise_val_col = noise_gen.noise(mid_pt_local[0] * 0.02, mid_pt_local[1] * 0.02, y_offset)
            # Example mapping: if palette has several grays, map noise_val_col (0-1) to them.
            # For now, using a placeholder:
            # Assuming a simple palette: 0=white, 1=dark1, 2=dark2, 3=dark3
            # Higher noise_val_col (closer to 1.0 from noise) means brighter (closer to 255 in JS).
            # Lower noise_val_col (closer to 0.0) means darker (closer to 200 in JS).
            # Let's say we have 3 dark shades (1,2,3) and white (0).
            # If palette is [WHITE, DARK1, DARK2, DARK3]
            # noise_val_col (0-1) * 55 + 200 = range 200-255.
            # Let's map this to indices. If 200-218 -> index 3 (darkest), 218-236 -> index 2, 237-255 -> index 1
            c_val_from_noise = noise_val_col * 55 + 200
            current_poly_color_idx = MOUNTAIN_OUTLINE_COLOR_INDEX # Default
            if c_val_from_noise < 218: current_poly_color_idx = 3 # Darkest if palette supports
            elif c_val_from_noise < 237: current_poly_color_idx = 2 # Mid if palette supports
            else: current_poly_color_idx = 1 # Lightest dark if palette supports
            # This is a placeholder: actual color mapping depends heavily on the defined palette.
            # For B&W, it might just be one dark color.

            draw_polygon(bitmap, poly_global, current_poly_color_idx)

            # Triangulation and drawing triangles
            if hasattr(self, 'poly_tools') and self.poly_tools:
                triangles_local = self.poly_tools.triangulate(poly_local, {'area': 100, 'convex': True, 'optimize': False})
                for tri_local in triangles_local:
                    if not tri_local or len(tri_local) <3: continue
                    tri_global = [(pt[0] + x_offset, pt[1] + y_offset) for pt in tri_local]
                    mid_pt_tri_local = self.poly_tools.mid_pt(tri_local)
                    noise_val_tri_col = noise_gen.noise(mid_pt_tri_local[0] * 0.02, mid_pt_tri_local[1] * 0.02, y_offset)

                    c_val_tri_from_noise = noise_val_tri_col * 55 + 200
                    tri_color_idx = MOUNTAIN_OUTLINE_COLOR_INDEX # Default
                    if c_val_tri_from_noise < 218: tri_color_idx = 3
                    elif c_val_tri_from_noise < 237: tri_color_idx = 2
                    else: tri_color_idx = 1
                    # Again, placeholder color logic.
                    draw_polygon(bitmap, tri_global, tri_color_idx)


    def draw_mountain(self, bitmap, x_offset, y_offset, seed, args_mountain):
        """
        Draws a standard mountain.
        """
        hei = args_mountain.get('hei', 100 + random.random() * 400)
        wid = args_mountain.get('wid', 400 + random.random() * 200)
        tex_density = args_mountain.get('tex', 200)
        # veg_flag = args_mountain.get('veg', True) # Placeholder for vegetation logic

        # Default texture color function - can be overridden by args_mountain['col']
        default_texture_col_func = lambda p_ratio: FOOT_STROKE_COLOR_INDEX
        texture_col_func = args_mountain.get('col', default_texture_col_func)

        # Noise generator specific to this mountain instance
        mountain_prng = lib.utils.Prng()
        mountain_prng.seed(seed) # Seed for this mountain's unique shape
        noise_gen = PerlinNoise(prng_instance=mountain_prng)

        ptlist_layers_local = []
        reso_y = 10
        reso_x = 50

        # hoff_accumulator = 0 # Original JS had a y-offset accumulation that might need careful porting if desired.
                             # For now, keeping layers aligned at their base.

        for j_layer in range(reso_y):
            layer_points = []
            # hoff_accumulator += (random.random() * y_offset_global_for_mountain) / 100 # This was problematic in JS interpretation
            for i_point in range(reso_x):
                x_norm = (i_point / reso_x - 0.5) * math.pi
                y_base = math.cos(x_norm)
                y_noisy = y_base * noise_gen.noise(x_norm + 10, j_layer * 0.15, seed) # Pass seed to noise if its perlin uses it that way

                p_factor = 1 - j_layer / reso_y

                local_x = (x_norm / math.pi) * wid * p_factor
                local_y = -y_noisy * hei * p_factor
                layer_points.append((local_x, local_y))
            ptlist_layers_local.append(layer_points)

        if not ptlist_layers_local or not ptlist_layers_local[0]: return

        ptlist_layers_global = [[(p[0] + x_offset, p[1] + y_offset) for p in layer] for layer in ptlist_layers_local]

        # TODO: Call vegetate (rim)

        if ptlist_layers_global and ptlist_layers_global[0]:
            outer_layer_global = ptlist_layers_global[0]
            # Create a closing polygon for the background fill
            min_x_bg = outer_layer_global[0][0]
            max_x_bg = outer_layer_global[-1][0]
            bottom_y_bg = y_offset + hei * 0.2 # Example bottom extent, adjust as needed

            bg_poly_pts = outer_layer_global + [(max_x_bg, bottom_y_bg), (min_x_bg, bottom_y_bg)]
            if len(bg_poly_pts) >=3:
                draw_polygon(bitmap, bg_poly_pts, WHITE_COLOR_INDEX)

        if ptlist_layers_global and ptlist_layers_global[0] and len(ptlist_layers_global[0]) >=2:
            stroke_args_outline = {
                'col': MOUNTAIN_OUTLINE_COLOR_INDEX, 'noi': 1.0, 'wid': 3,
                'fun': lambda x_prog: math.sin(x_prog * math.pi)
            }
            draw_stroke(bitmap, ptlist_layers_global[0], stroke_args_outline)

        self._draw_mountain_foot(bitmap, ptlist_layers_local, x_offset, y_offset, {})

        texture_args = {
            'xof': x_offset, 'yof': y_offset,
            'tex': tex_density,
            'wid': 1.5,
            'len': 0.2,
            'sha': random.choice([0,0,0,0,5]),
            'col': texture_col_func,
        }
        draw_texture(bitmap, ptlist_layers_local, texture_args)

        # TODO: Call vegetate (top, middle, bottom)
        # TODO: Call Arch functions (bott arch, top arch, transm)
        # TODO: Call Mount.rock (bott rock) - this would be self.draw_rock(...)

class Arch:
    def __init__(self, noise_instance, utils_module, poly_tools_instance, tree_instance=None, mount_instance=None):
        self.noise_instance = noise_instance
        self.utils = utils_module
        self.poly_tools = poly_tools_instance
        self.tree_instance = tree_instance
        self.mount_instance = mount_instance
        self.man_instance = man_instance # Added man_instance

    def _generate_decoration_lines_local(self, style, args_deco):
        """
        Generates a list of polylines for box decorations, based on JS 'deco'.
        Points are relative to the decoration area defined by pul, pur, pdl, pdr.
        Each returned polyline is a list of points.
        """
        pul = args_deco.get('pul', (0,0))
        pur = args_deco.get('pur', (0,10)) # Adjusted default for visibility if used alone
        pdl = args_deco.get('pdl', (10,0))
        pdr = args_deco.get('pdr', (10,10))

        hsp_params = args_deco.get('hsp', [1,3])
        vsp_params = args_deco.get('vsp', [1,2])

        polylines_local = []

        # Ensure div can handle cases where segment count might be zero or one.
        # self.utils.div should ideally return the start point or [start, end] if segments is < 1.
        dl = self.utils.div([pul, pdl], vsp_params[1])
        dr = self.utils.div([pur, pdr], vsp_params[1])
        du = self.utils.div([pul, pur], hsp_params[1])
        dd = self.utils.div([pdl, pdr], hsp_params[1])

        if not all([dl, dr, du, dd]): return [] # Need all edge divisions

        if style == 1: # -| |- style
            if not (hsp_params[0] < len(du) and hsp_params[0] < len(dd) and \
                    len(du) - 1 - hsp_params[0] >= 0 and len(dd) - 1 - hsp_params[0] >=0 ):
                return []

            mlu, mru = du[hsp_params[0]], du[len(du) - 1 - hsp_params[0]]
            mld, mrd = dd[hsp_params[0]], dd[len(dd) - 1 - hsp_params[0]]

            polylines_local.append(self.utils.div([mlu, mld], 5))
            polylines_local.append(self.utils.div([mru, mrd], 5))

            inner_left_pts = self.utils.div([mlu,mld],vsp_params[1])
            inner_right_pts = self.utils.div([mru,mrd],vsp_params[1])

            for i in range(vsp_params[0], len(dl) - vsp_params[0], vsp_params[0]):
                if i < len(inner_left_pts) and i < len(dl):
                     polylines_local.append(self.utils.div([inner_left_pts[i], dl[i]], 2)) # Simple line
                if i < len(inner_right_pts) and i < len(dr):
                     polylines_local.append(self.utils.div([inner_right_pts[i], dr[i]], 2))


        elif style == 2: # |||| style (vertical lines)
            for i in range(hsp_params[0], len(du) - hsp_params[0], hsp_params[0]):
                if i < len(du) and i < len(dd):
                    polylines_local.append(self.utils.div([du[i], dd[i]], 2))

        elif style == 3: # |##| style (grid-like, simplified from previous attempt)
            if not (hsp_params[0] < len(du) and hsp_params[0] < len(dd) and \
                    len(du) - 1 - hsp_params[0] >= 0 and len(dd) - 1 - hsp_params[0] >=0 ):
                return []
            mlu, mru = du[hsp_params[0]], du[len(du) - 1 - hsp_params[0]]
            mld, mrd = dd[hsp_params[0]], dd[len(dd) - 1 - hsp_params[0]]

            polylines_local.append(self.utils.div([mlu, mld], 5)) # Left inner vertical
            polylines_local.append(self.utils.div([mru, mrd], 5)) # Right inner vertical

            num_horizontal_bars = vsp_params[0]
            for i_bar in range(1, num_horizontal_bars + 1):
                p_factor = i_bar / (num_horizontal_bars + 1.0)
                pt_on_left_v = (mlu[0]*(1-p_factor) + mld[0]*p_factor, mlu[1]*(1-p_factor) + mld[1]*p_factor)
                pt_on_right_v = (mru[0]*(1-p_factor) + mrd[0]*p_factor, mru[1]*(1-p_factor) + mrd[1]*p_factor)
                polylines_local.append(self.utils.div([pt_on_left_v, pt_on_right_v], 2))

        return polylines_local

    def draw_arch01(self, bitmap, x_offset, y_offset, seed, args_arch01):
        """Draws architecture type 01."""
        hei = args_arch01.get('hei', 70)
        wid = args_arch01.get('wid', 180)
        # rot = args_arch01.get('rot', 0.7) # rot is per box/roof, not whole arch here
        # per = args_arch01.get('per', 5)   # per is per box/roof
        base_col_idx = args_arch01.get('col', BOX_STROKE_COLOR_INDEX) # Default to box color

        # Proportions from JS
        p_split = 0.4 + random.random() * 0.2 # Proportion for hut part
        h0_hut = hei * p_split
        h1_box = hei * (1 - p_split)

        # Hut part (top)
        args_hut = {
            'hei': h0_hut, 'wid': wid, 'tex': 200, # tex from JS arch01->hut call
            'col': base_col_idx
        }
        self.draw_hut(bitmap, x_offset, y_offset - h1_box, args_hut) # Hut is on top of the box

        # Box part (bottom)
        args_box = {
            'hei': h1_box, 'wid': wid * 2/3,
            'per': args_arch01.get('per', 5), # Use per from main args
            'rot': args_arch01.get('rot', random.random()*0.4+0.3), # Random rot if not specified
            'bot': False, # Bottom not drawn for this box part in JS arch01
            'tra': True, # Transparent for arch01 box
            'wei': 2, # Default stroke weight
            'col': base_col_idx,
            # No dec_style specified for the box in arch01 JS
        }
        self.draw_box(bitmap, x_offset, y_offset, args_box)

        # Railings
        # Railing perspective and width should match the box they sit on or relate to.
        # The JS rail calls use wid of the hut, per of the main arch.
        rail_per = args_arch01.get('per', 5) * 2
        rail_wid = wid

        args_rail_front = {
            'hei': 10, 'wid': rail_wid, 'per': rail_per,
            'seg': int(3 + random.random() * 3), 'tra': False, 'fro': True,
            'rot': args_box['rot'], # Match box rotation for consistency
            'col': base_col_idx
        }
        self.draw_rail(bitmap, x_offset, y_offset, seed, args_rail_front)

        args_rail_back = {
            'hei': 10, 'wid': rail_wid, 'per': rail_per,
            'seg': int(3 + random.random() * 3), 'tra': True, 'fro': False,
            'rot': args_box['rot'],
            'col': base_col_idx
        }
        # Seed for second rail call could be varied if desired
        self.draw_rail(bitmap, x_offset, y_offset, seed + 1 if seed is not None else random.random()*1000, args_rail_back)


        # Men
        mcnt = random.choice([0, 1, 1, 2])
        if hasattr(self, 'man_instance') and self.man_instance:
            if mcnt == 1:
                man_args = {'fli': random.choice([True, False]), 'sca': 0.42, 'col': MAN_COLOR_INDEX}
                self.man_instance.draw_man(bitmap, x_offset + self.utils.norm_rand(-wid/3, wid/3), y_offset, man_args)
            elif mcnt == 2:
                man_args1 = {'fli': False, 'sca': 0.42, 'col': MAN_COLOR_INDEX}
                self.man_instance.draw_man(bitmap, x_offset + self.utils.norm_rand(-wid/4, -wid/5), y_offset, man_args1)
                man_args2 = {'fli': True, 'sca': 0.42, 'col': MAN_COLOR_INDEX}
                self.man_instance.draw_man(bitmap, x_offset + self.utils.norm_rand(wid/5, wid/4), y_offset, man_args2)
        # else:
            # print("Man instance not available in Arch for draw_arch01")

    def draw_arch02(self, bitmap, x_offset, y_offset, seed, args_arch02):
        """Draws architecture type 02 (multi-story with roof)."""
        hei_story = args_arch02.get('hei', 10) # Height per story
        wid_base = args_arch02.get('wid', 50)
        rot = args_arch02.get('rot', 0.3)
        per = args_arch02.get('per', 5)
        stories = args_arch02.get('sto', 3)
        deco_style = args_arch02.get('sty', 1) # Decoration style for boxes
        has_rail = args_arch02.get('rai', False)
        base_col_idx = args_arch02.get('col', BOX_STROKE_COLOR_INDEX)

        hoff = 0 # Current height offset from y_offset for each story

        for i_story in range(stories):
            current_wid = wid_base * math.pow(0.85, i_story)
            current_hei = hei_story # Assuming story height is constant, JS hei is per story

            # Box for the current story
            box_args = {
                'hei': current_hei, 'wid': current_wid, 'rot': rot, 'per': per,
                'tra': False, # Stories are not transparent
                'wei': 1.5, 'col': base_col_idx,
                'dec_style': deco_style,
                'dec_custom_args': { # Default deco spacings, can be overridden
                    'hsp': [[],[1,5],[1,5],[1,4]][deco_style] if deco_style <=3 else [1,3], # JS: sty index for hsp/vsp
                    'vsp': [[],[1,2],[1,2],[1,3]][deco_style] if deco_style <=3 else [1,2]
                }
            }
            self.draw_box(bitmap, x_offset, y_offset - hoff, box_args)

            if has_rail:
                rail_args = {
                    'wid': current_wid * 1.1, 'hei': current_hei / 2, 'per': per,
                    'rot': rot, 'wei': 0.5, 'tra': False, 'fro': True,
                    'seg': max(1, int(current_wid / 15)), # Scale segments with width
                    'col': base_col_idx
                }
                # Vary seed for each rail slightly
                self.draw_rail(bitmap, x_offset, y_offset - hoff, seed + i_story if seed is not None else random.random()*1000, rail_args)

            # Roof for the current story
            plaque_text_for_story = ""
            if stories == 1 and random.random() < 1/3 : # Plaque only on single story arch02
                plaque_text_for_story = "Pizza Hut" # Example from JS

            roof_args = {
                'hei': current_hei, 'wid': current_wid * 0.9, # Roof slightly narrower
                'rot': rot, 'per': per, 'wei': 1.5, 'col': base_col_idx,
                'pla': [1 if plaque_text_for_story else 0, plaque_text_for_story]
            }
            self.draw_roof(bitmap, x_offset, y_offset - hoff - current_hei, roof_args)

            hoff += current_hei * 1.5 # Move up for the next story

    def draw_arch03(self, bitmap, x_offset, y_offset, seed, args_arch03):
        """Draws architecture type 03 (multi-story pagoda-style)."""
        hei_story = args_arch03.get('hei', 10)
        wid_base = args_arch03.get('wid', 50)
        rot = args_arch03.get('rot', 0.7)
        per = args_arch03.get('per', 5)
        stories = args_arch03.get('sto', 7)
        base_col_idx = args_arch03.get('col', BOX_STROKE_COLOR_INDEX)

        hoff = 0

        for i_story in range(stories):
            current_wid = wid_base * math.pow(0.85, i_story)
            current_hei = hei_story

            box_args = {
                'hei': current_hei, 'wid': current_wid, 'rot': rot, 'per': per / 2,
                'tra': False, 'wei': 1.5, 'col': base_col_idx,
                'dec_style': 1, # Style 1 deco for arch03 boxes
                'dec_custom_args': {'hsp': [1,4], 'vsp': [1,2]} # Specific deco params
            }
            self.draw_box(bitmap, x_offset, y_offset - hoff, box_args)

            rail_args = {
                'wid': current_wid * 1.1, 'hei': current_hei / 2, 'per': per / 2,
                'rot': rot, 'wei': 0.5, 'tra': False, 'fro': True, 'seg': 5,
                'col': base_col_idx
            }
            self.draw_rail(bitmap, x_offset, y_offset - hoff, seed + i_story if seed is not None else random.random()*1000, rail_args)

            pagoda_roof_args = {
                'hei': current_hei * 1.5, 'wid': current_wid * 0.9,
                'rot': rot, 'per': per, 'wei': 1.5, 'col': base_col_idx,
                'sid': 4 # Default sides for pagoda roof
            }
            self.draw_pagoda_roof(bitmap, x_offset, y_offset - hoff - current_hei, pagoda_roof_args)

            hoff += current_hei * 1.5

    def draw_arch04(self, bitmap, x_offset, y_offset, seed, args_arch04):
        """Draws architecture type 04 (similar to arch03 but transparent boxes)."""
        hei_story = args_arch04.get('hei', 15)
        wid_base = args_arch04.get('wid', 30)
        rot = args_arch04.get('rot', 0.7)
        per = args_arch04.get('per', 5)
        stories = args_arch04.get('sto', 2)
        base_col_idx = args_arch04.get('col', BOX_STROKE_COLOR_INDEX)

        hoff = 0

        for i_story in range(stories):
            current_wid = wid_base * math.pow(0.85, i_story)
            current_hei = hei_story

            box_args = {
                'hei': current_hei, 'wid': current_wid, 'rot': rot, 'per': per / 2,
                'tra': True, # Key difference from arch03: transparent boxes
                'wei': 1.5, 'col': base_col_idx,
                'dec_style': 0, # No decoration for arch04 boxes
            }
            self.draw_box(bitmap, x_offset, y_offset - hoff, box_args)

            rail_args = {
                'wid': current_wid * 1.2, 'hei': current_hei / 3, 'per': per / 2,
                'rot': rot, 'wei': 0.5, 'tra': True, 'fro': True, 'seg': 3,
                'col': base_col_idx
            }
            self.draw_rail(bitmap, x_offset, y_offset - hoff, seed + i_story if seed is not None else random.random()*1000, rail_args)

            pagoda_roof_args = {
                'hei': current_hei * 1.0, 'wid': current_wid * 0.9, # Roof height relative to story
                'rot': rot, 'per': per, 'wei': 1.5, 'col': base_col_idx,
                'sid': 4
            }
            self.draw_pagoda_roof(bitmap, x_offset, y_offset - hoff - current_hei, pagoda_roof_args)

            hoff += current_hei * 1.2 # Slightly less vertical spacing than arch03

    def draw_boat01(self, bitmap, x_offset, y_offset, seed, args_boat):
        """Draws a simple boat with a man."""
        boat_len = args_boat.get('len', 120)
        sca = args_boat.get('sca', 1.0)
        is_flipped = args_boat.get('fli', False)
        base_col_idx = args_boat.get('col', BOAT_STROKE_COLOR_INDEX)

        direction = -1 if is_flipped else 1

        # Draw the man on the boat
        if hasattr(self, 'man_instance') and self.man_instance:
            # Man args from JS: ite: Man.stick01, hat: Man.hat02, sca: 0.5*sca, fli: !fli
            # The 'ite' and 'hat' are specific functions/styles for the man.
            # Our placeholder Man.draw_man doesn't support these directly yet.
            # We pass scale and flip. Color is MAN_COLOR_INDEX.
            man_args = {
                'sca': 0.5 * sca,
                'fli': not is_flipped, # Man faces opposite to boat's flip state
                'col': MAN_COLOR_INDEX
                # TODO: Add 'ite' and 'hat' to args_man if Man class gets updated
            }
            # Man is positioned relative to the boat's x_offset
            self.man_instance.draw_man(bitmap,
                                       x_offset + 20 * sca * direction,
                                       y_offset, # Man stands at the boat's y_offset level
                                       man_args)

        plist1_local, plist2_local = [], []

        # Hull shape functions from JS
        fun1 = lambda x_norm: math.pow(math.sin(x_norm * math.pi), 0.5) * 7 * sca
        fun2 = lambda x_norm: math.pow(math.sin(x_norm * math.pi), 0.5) * 10 * sca

        # Generate points for the hull (local coordinates)
        # x ranges from 0 up to boat_len * sca
        num_segments_hull = int(boat_len * sca / (5 * sca)) # Match density of JS loop
        if num_segments_hull == 0: num_segments_hull = 1 # ensure at least one segment for very small scales

        for i in range(num_segments_hull + 1): # +1 to include endpoint
            x_local = i * (5 * sca) * direction
            # Normalize x for sin function (0 to 1 over the boat length)
            x_norm_for_sin = (i * 5 * sca) / (boat_len * sca) if boat_len * sca > 0 else 0

            plist1_local.append((x_local, fun1(x_norm_for_sin)))
            plist2_local.append((x_local, fun2(x_norm_for_sin)))

        if not plist1_local or not plist2_local: return # Not enough points

        plist_combined_local = plist1_local + plist2_local[::-1]

        # Transform to global coordinates for drawing
        plist_combined_global = [(p[0] + x_offset, p[1] + y_offset) for p in plist_combined_local]

        if len(plist_combined_global) >=3:
            draw_polygon(bitmap, plist_combined_global, WHITE_COLOR_INDEX) # White fill for hull

            stroke_args_boat = {
                'col': base_col_idx,
                'wid': 1, # Fixed width from JS
                'noi': 0.1, # Assuming little noise for boat outline
                'fun': lambda x_prog: math.sin(x_prog * math.pi * 2) # JS fun for boat stroke
            }
            draw_stroke(bitmap, plist_combined_global, stroke_args_boat)

    def draw_transmission_tower01(self, bitmap, x_offset, y_offset, seed, args_tower):
        """Draws a transmission tower."""
        hei = args_tower.get('hei', 100)
        wid = args_tower.get('wid', 20)
        base_col_idx = args_tower.get('col', TOWER_STROKE_COLOR_INDEX)

        # Helper for drawing strokes, applying offset
        def quickstroke_local(local_polyline_pts):
            if not local_polyline_pts or len(local_polyline_pts) < 2: return
            # Ensure all points in polyline are tuples/lists of 2 numbers
            valid_pts = True
            for pt in local_polyline_pts:
                if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                    valid_pts = False; break
            if not valid_pts:
                # print(f"Warning: Invalid points in quickstroke_local: {local_polyline_pts}")
                return

            global_polyline_pts = [(p[0] + x_offset, p[1] + y_offset) for p in local_polyline_pts]
            stroke_args = {
                'wid': 1, 'fun': lambda x_prog: 0.5, # Constant, half-unit width
                'col': base_col_idx, 'noi': 0.05 # Minimal noise
            }
            draw_stroke(bitmap, global_polyline_pts, stroke_args)

        # Define local points for the tower structure (relative to tower's own (0,0) at base center)
        # These are y-negative because graphics y typically goes down.
        p00 = (-wid * 0.05, -hei)
        p01 = (wid * 0.05, -hei)
        p10 = (-wid * 0.1, -hei * 0.9)
        p11 = (wid * 0.1, -hei * 0.9)
        p20 = (-wid * 0.2, -hei * 0.5)
        p21 = (wid * 0.2, -hei * 0.5)
        p30 = (-wid * 0.5, 0) # Base left
        p31 = (wid * 0.5, 0)  # Base right

        # Arms (bch - branch cross-members)
        bch = [[0.7, -0.85], [1.0, -0.675], [0.7, -0.5]] # Relative width factor, relative height factor
        for item in bch:
            w_factor, h_factor = item
            arm_y = h_factor * hei
            arm_tip_x = w_factor * wid

            # Horizontal arm cross-member
            quickstroke_local([(-arm_tip_x, arm_y), (arm_tip_x, arm_y)])
            # Supports from arm tips to a point slightly below arm center
            quickstroke_local([(-arm_tip_x, arm_y), (0, arm_y - 0.05*hei)])
            quickstroke_local([(arm_tip_x, arm_y), (0, arm_y - 0.05*hei)])
            # Short vertical supports from arm tips
            quickstroke_local([(-arm_tip_x, arm_y), (-arm_tip_x, arm_y + 0.1*hei)])
            quickstroke_local([(arm_tip_x, arm_y), (arm_tip_x, arm_y + 0.1*hei)])

        # Main tower body lattice
        # Using self.utils.div to create smoother interpolated lines for legs
        # The JS uses div([p00,p10,p20,p30],5) which means 5 segments for the whole leg.
        # Our div takes point list and number of segments.
        # If div is for a single segment, we need to div each pair.
        # Assuming div here is to make a polyline from a list of points, with 5 segments for the whole.

        leg_left_pts = self.utils.div([p00,p10,p20,p30], 5 * 3) # 5 segments between each pair
        leg_right_pts = self.utils.div([p01,p11,p21,p31], 5 * 3)

        if leg_left_pts and leg_right_pts and len(leg_left_pts) > 1 and len(leg_right_pts) > 1:
            min_len = min(len(leg_left_pts), len(leg_right_pts))
            for i in range(min_len -1):
                quickstroke_local([leg_left_pts[i], leg_right_pts[i+1]])
                quickstroke_local([leg_right_pts[i], leg_left_pts[i+1]])

        # Horizontal braces
        quickstroke_local([p00, p01])
        quickstroke_local([p10, p11])
        quickstroke_local([p20, p21])
        # Base line (p30, p31) is implicitly part of the legs if drawn fully.
        # If legs are drawn segment by segment, then p30-p31 might not be drawn explicitly by leg drawing.
        # The JS code draws the legs first, then the cross members.
        # Let's ensure the main vertical legs are drawn:
        quickstroke_local(leg_left_pts)
        quickstroke_local(leg_right_pts)


    def draw_hut(self, bitmap, x_offset, y_offset, args_hut):
        """Draws a hut structure."""
        hei = args_hut.get('hei', 40)
        wid = args_hut.get('wid', 180)
        tex_density = args_hut.get('tex', 300)
        # Color for strokes, outline, and texture (can be overridden by texture_col_func)
        base_col_idx = args_hut.get('col', MOUNTAIN_OUTLINE_COLOR_INDEX)

        reso_y = 10 # Number of layers for hut structure
        reso_x = 10 # Number of points per layer

        ptlist_layers_local = [] # List of polylines, points relative to hut's local (0,0)

        for i_layer in range(reso_y):
            layer_points = []
            # Height variation for each vertical strut of the hut
            current_strut_height = hei + hei * 0.2 * random.random()
            for j_point in range(reso_x):
                # nx is x-coordinate along the width of the hut
                # ny is y-coordinate along the height of the strut, with perspective
                nx = wid * (i_layer / (reso_y -1) - 0.5) * math.pow(j_point / (reso_x -1), 0.7) if reso_y > 1 and reso_x > 1 else 0
                ny = current_strut_height * (j_point / (reso_x-1)) if reso_x > 1 else 0
                layer_points.append((nx,ny))
            ptlist_layers_local.append(layer_points)

        if not ptlist_layers_local: return

        # Transform points for drawing
        ptlist_layers_global = []
        for layer_local in ptlist_layers_local:
            ptlist_layers_global.append([(pt[0] + x_offset, pt[1] + y_offset) for pt in layer_local])

        # Draw background polygon (white fill)
        if len(ptlist_layers_global) >= 2 and ptlist_layers_global[0] and ptlist_layers_global[-1]:
            # Combine the first and last layer (reversed) to form a closed polygon for the background
            # Exclude last point of each list to avoid doubling when joining for closed poly
            bg_poly_pts_global = ptlist_layers_global[0][:-1] + ptlist_layers_global[-1][:-1][::-1]
            if len(bg_poly_pts_global) >=3:
                draw_polygon(bitmap, bg_poly_pts_global, WHITE_COLOR_INDEX)

        # Stroke first and last layers (outlines of the hut)
        if ptlist_layers_global[0] and len(ptlist_layers_global[0]) >=2:
            draw_stroke(bitmap, ptlist_layers_global[0], {'col': base_col_idx, 'wid': 2, 'noi':0.1}) # Minimal noise for structure
        if ptlist_layers_global[-1] and len(ptlist_layers_global[-1]) >=2:
            draw_stroke(bitmap, ptlist_layers_global[-1], {'col': base_col_idx, 'wid': 2, 'noi':0.1})

        # Draw texture on the hut (using local points for texture generation)
        # Define texture color function for hut - JS: "rgba(120,120,120,"+(0.3+Math.random()*0.3).toFixed(3)+")"
        # This implies a somewhat dark grey with random alpha.
        # We need to map this to our palette. Assuming a dark color index.
        def hut_texture_col_func(p_ratio):
            # Could be more complex, e.g., varying index if palette supports multiple grays
            return base_col_idx # Or a specific grey index from palette

        texture_args_hut = {
            'xof': x_offset, 'yof': y_offset,
            'tex': tex_density,
            'wid': 1, 'len': 0.25, 'sha': 0, # No shading for hut texture per JS
            'col': hut_texture_col_func,
            'dis': lambda: self.utils.wtrand(lambda a: a*a), # Weighted random distribution
            'noi': lambda lyr_p1: 5 # Noise function for texture
        }
        draw_texture(bitmap, ptlist_layers_local, texture_args_hut)

    def draw_box(self, bitmap, x_offset, y_offset, args_box):
        """Draws a box structure, potentially with decorations."""
        hei = args_box.get('hei', 20)
        wid = args_box.get('wid', 120)
        rot = args_box.get('rot', 0.7) # Rotation/perspective factor
        per = args_box.get('per', 4)   # Perspective y-offset
        tra = args_box.get('tra', True) # Transparent flag (if False, draw white bg for front face)
        bot = args_box.get('bot', True) # Bottom face visible flag
        stroke_wei = args_box.get('wei', 3)
        deco_style = args_box.get('dec_style', 0) # Decoration style, 0 for none
        deco_args_custom = args_box.get('dec_custom_args', {}) # For custom hsp/vsp

        # Calculate key points for box perspective
        # mid is the vanishing point x-offset for the "front" face (closer to viewer if per > 0)
        # bmid is for the "back" face (further if per > 0)
        mid = -wid * 0.5 + wid * rot
        bmid = -wid * 0.5 + wid * (1 - rot) # Symmetric to mid for the other side if box is centered around rot=0.5

        list_of_lines_local = [] # Each element is a polyline (list of points)

        # Define main structural lines of the box (local coordinates, relative to box center (0,0))
        # Vertical edges
        list_of_lines_local.append([(-wid * 0.5, -hei), (-wid * 0.5, 0)]) # Left front
        list_of_lines_local.append([(wid * 0.5, -hei), (wid * 0.5, 0)])   # Right front
        list_of_lines_local.append([(mid, -hei + per if bot else -hei), (mid, per if bot else 0)]) # Middle front (if perspective)
                                                                    # Adjusted for per based on 'bot' for top point too

        if tra: # If transparent, also draw back vertical edges
            list_of_lines_local.append([(bmid, -hei - per if bot else -hei), (bmid, -per if bot else 0)]) # Middle back

        # Horizontal edges (top and bottom connections)
        if bot: # If bottom is visible, connect to perspective points
            list_of_lines_local.append([(-wid * 0.5, 0), (mid, per)])       # Bottom-left to mid-front
            list_of_lines_local.append([(wid * 0.5, 0), (mid, per)])        # Bottom-right to mid-front
            if tra: # Back bottom edges if transparent
                list_of_lines_local.append([(-wid * 0.5, 0), (bmid, -per)]) # Bottom-left to mid-back
                list_of_lines_local.append([(wid * 0.5, 0), (bmid, -per)])  # Bottom-right to mid-back

        # Top edges
        # Top-left to mid-front (or mid-back if transparent top edge)
        list_of_lines_local.append([(-wid * 0.5, -hei), (mid, -hei + per if bot else -hei)])
        list_of_lines_local.append([(wid * 0.5, -hei), (mid, -hei + per if bot else -hei)])
        if tra:
            list_of_lines_local.append([(-wid * 0.5, -hei), (bmid, -hei - per if bot else -hei)])
            list_of_lines_local.append([(wid * 0.5, -hei), (bmid, -hei - per if bot else -hei)])


        # Generate decorations if a style is specified
        if deco_style > 0:
            # Define corners for the front face decoration area (local to box)
            # Surface for decoration is chosen based on rotation/perspective (rot < 0.5 means left face is more prominent)
            surf_sign = 1 if rot < 0.5 else -1 # Determines which face (left/right of mid) is decorated

            # These points define the quad on which decorations are drawn.
            # They should be relative to the box's local (0,0) for _generate_decoration_lines_local.
            deco_pul = (surf_sign * wid * 0.5, -hei)
            deco_pur = (mid, -hei + per if bot else -hei)
            deco_pdl = (surf_sign * wid * 0.5, 0)
            deco_pdr = (mid, per if bot else 0)

            # Ensure points are correctly ordered for _generate_decoration_lines_local if it expects certain winding
            # E.g., pul=top-left, pur=top-right, pdl=bottom-left, pdr=bottom-right of the face.
            # If surf_sign is -1 (right face prominent), pul/pdl will be on the right.
            # The _generate_decoration_lines_local must handle this coordinate system.
            # Let's assume for now it expects pul, pur, pdl, pdr as corners of a quad.
            # If surf_sign is -1, then (mid,...) becomes the "left" side of the decoration panel.
            if surf_sign == -1: # Right face is prominent, swap left and right for deco
                deco_pul_actual = (mid, -hei + per if bot else -hei)
                deco_pur_actual = (-surf_sign * wid * 0.5, -hei) # This is wid*0.5
                deco_pdl_actual = (mid, per if bot else 0)
                deco_pdr_actual = (-surf_sign * wid * 0.5, 0)
            else: # Left face is prominent
                deco_pul_actual = deco_pul
                deco_pur_actual = deco_pur
                deco_pdl_actual = deco_pdl
                deco_pdr_actual = deco_pdr

            deco_gen_args = {
                'pul': deco_pul_actual, 'pur': deco_pur_actual,
                'pdl': deco_pdl_actual, 'pdr': deco_pdr_actual,
                'hsp': deco_args_custom.get('hsp', [1,5]), # Default hsp from JS deco example
                'vsp': deco_args_custom.get('vsp', [1,2])  # Default vsp
            }
            decoration_polylines_local = self._generate_decoration_lines_local(deco_style, deco_gen_args)
            list_of_lines_local.extend(decoration_polylines_local)

        # Draw background for the front face if not transparent
        if not tra:
            # Define polygon for the front face (local coordinates)
            # Order: top-left, top-right, bottom-right (perspective), bottom-left (perspective)
            polist_bg_local = [
                (-wid * 0.5, -hei), (wid * 0.5, -hei),
                (wid * 0.5, 0),    (mid, per if bot else 0),
                (-wid * 0.5, 0)
            ]
            # If mid is to the left of -wid*0.5 (rot is small), order might need to change for correct winding.
            # For simplicity, assuming standard perspective.
            # The JS version of poly() doesn't care about winding for fill. Ours might if using advanced fill.
            polist_bg_global = [(p[0] + x_offset, p[1] + y_offset) for p in polist_bg_local]
            if len(polist_bg_global) >=3:
                 draw_polygon(bitmap, polist_bg_global, WHITE_COLOR_INDEX) # Assuming white fill

        # Draw all lines (structure and decorations)
        for line_pts_local in list_of_lines_local:
            if not line_pts_local or len(line_pts_local) < 2: continue
            line_pts_global = [(p[0] + x_offset, p[1] + y_offset) for p in line_pts_local]
            stroke_args = {
                'col': BOX_STROKE_COLOR_INDEX,
                'wid': stroke_wei,
                'noi': 0.1, # Minimal noise for architectural lines
                'fun': lambda x_prog: 1 # Constant width
            }
            draw_stroke(bitmap, line_pts_global, stroke_args)

    def draw_rail(self, bitmap, x_offset, y_offset, seed, args_rail):
        """Draws a rail structure."""
        hei = args_rail.get('hei', 20)
        wid = args_rail.get('wid', 180)
        rot = args_rail.get('rot', 0.7)
        per = args_rail.get('per', 4)
        seg_count = args_rail.get('seg', 4) # Number of segments for div
        stroke_w = args_rail.get('wei', 1)
        tra = args_rail.get('tra', True) # Transparent (draw back rails)
        fro = args_rail.get('fro', True) # Draw front rails

        # Seeded noise for this rail instance
        rail_prng = lib.utils.Prng()
        rail_prng.seed(seed) # Different seed for each rail call
        noise_gen_rail = PerlinNoise(prng_instance=rail_prng)


        mid = -wid * 0.5 + wid * rot
        bmid = -wid * 0.5 + wid * (1 - rot)

        ptlist_horizontal_rails_local = []

        # Define horizontal rails (local coordinates)
        # Front rails
        if fro:
            ptlist_horizontal_rails_local.append(self.utils.div([(-wid * 0.5, 0), (mid, per)], seg_count))
            ptlist_horizontal_rails_local.append(self.utils.div([(mid, per), (wid * 0.5, 0)], seg_count))
            ptlist_horizontal_rails_local.append(self.utils.div([(-wid * 0.5, -hei), (mid, -hei + per)], seg_count))
            ptlist_horizontal_rails_local.append(self.utils.div([(mid, -hei + per), (wid * 0.5, -hei)], seg_count))
        # Back rails (if transparent)
        if tra:
            ptlist_horizontal_rails_local.append(self.utils.div([(-wid * 0.5, 0), (bmid, -per)], seg_count))
            ptlist_horizontal_rails_local.append(self.utils.div([(bmid, -per), (wid * 0.5, 0)], seg_count))
            ptlist_horizontal_rails_local.append(self.utils.div([(-wid * 0.5, -hei), (bmid, -hei - per)], seg_count))
            ptlist_horizontal_rails_local.append(self.utils.div([(bmid, -hei - per), (wid * 0.5, -hei)], seg_count))

        # Randomly open one segment in the back rails if transparent
        if tra and ptlist_horizontal_rails_local:
            # This part of JS logic is a bit complex: ptlist[open] = ptlist[open].slice(0,-1)
            # It means one segment of a rail is not drawn.
            # For simplicity here, we might skip drawing one of the back horizontal rails randomly.
            # Or, more closely, shorten one of the lists of points.
            # Let's try to shorten one of the back rail segments if tra is True
            # The back rails start from index 4 if fro is also true, or 0 if fro is false.
            back_rail_start_index = 4 if fro else 0
            if len(ptlist_horizontal_rails_local) > back_rail_start_index:
                 open_segment_index = random.randrange(back_rail_start_index, len(ptlist_horizontal_rails_local))
                 if ptlist_horizontal_rails_local[open_segment_index] and len(ptlist_horizontal_rails_local[open_segment_index]) > 1:
                     ptlist_horizontal_rails_local[open_segment_index] = ptlist_horizontal_rails_local[open_segment_index][:-1]


        all_polylines_to_draw_global = []

        # Add horizontal rails (transformed)
        for rail_local in ptlist_horizontal_rails_local:
            if rail_local and len(rail_local) >=2: # Check if rail_local is not None and has enough points
                 all_polylines_to_draw_global.append([(p[0] + x_offset, p[1] + y_offset) for p in rail_local])

        # Vertical connections
        # JS logic: for (var i=0; i<ptlist.length/2; i++){ for (var j=0; j<ptlist[i].length; j++){ ...}}}
        # This implies connecting points between corresponding top/bottom or front/back rails.
        # If fro=true, tra=true, ptlist_horizontal_rails_local has 8 rails:
        # 0: front-bottom-left, 1: front-bottom-right, 2: front-top-left, 3: front-top-right
        # 4: back-bottom-left,  5: back-bottom-right,  6: back-top-left,  7: back-top-right

        num_front_rails = 4 if fro else 0
        num_back_rails = 4 if tra else 0

        # Connect front bottom to front top
        if fro:
            for rail_idx_offset in [0,1]: # Left and Right sides
                bottom_rail = ptlist_horizontal_rails_local[rail_idx_offset]
                top_rail = ptlist_horizontal_rails_local[rail_idx_offset+2]
                if bottom_rail and top_rail:
                    for j in range(min(len(bottom_rail), len(top_rail))):
                        p_bottom_local = list(bottom_rail[j]) # Make mutable
                        p_top_local = list(top_rail[j])     # Make mutable

                        p_bottom_local[1] += (noise_gen_rail.noise(rail_idx_offset, j * 0.5) - 0.5) * hei
                        p_top_local[1] += (noise_gen_rail.noise(rail_idx_offset + 0.5, j * 0.5) - 0.5) * hei

                        # JS: ln[0][0] += (Math.random()-0.5)*hei*0.5; (applied to one end of vertical connection)
                        # This makes vertical posts not perfectly vertical. Let's apply to x of bottom point.
                        p_bottom_local[0] += (random.random()-0.5)*hei*0.5

                        vertical_line_local = [tuple(p_bottom_local), tuple(p_top_local)]
                        all_polylines_to_draw_global.append([(p[0] + x_offset, p[1] + y_offset) for p in vertical_line_local])
        # Connect back bottom to back top
        if tra:
            for rail_idx_offset in [0,1]: # Left and Right sides
                bottom_rail_idx = back_rail_start_index + rail_idx_offset
                top_rail_idx = back_rail_start_index + rail_idx_offset + 2
                if top_rail_idx < len(ptlist_horizontal_rails_local): # Ensure indices are valid
                    bottom_rail = ptlist_horizontal_rails_local[bottom_rail_idx]
                    top_rail = ptlist_horizontal_rails_local[top_rail_idx]
                    if bottom_rail and top_rail:
                        for j in range(min(len(bottom_rail), len(top_rail))):
                            p_bottom_local = list(bottom_rail[j])
                            p_top_local = list(top_rail[j])
                            p_bottom_local[1] += (noise_gen_rail.noise(rail_idx_offset+num_front_rails, j*0.5)-0.5)*hei
                            p_top_local[1] += (noise_gen_rail.noise(rail_idx_offset+num_front_rails+0.5, j*0.5)-0.5)*hei
                            p_bottom_local[0] += (random.random()-0.5)*hei*0.5
                            vertical_line_local = [tuple(p_bottom_local), tuple(p_top_local)]
                            all_polylines_to_draw_global.append([(p[0] + x_offset, p[1] + y_offset) for p in vertical_line_local])

        # Draw all lines
        for polyline_global in all_polylines_to_draw_global:
            if len(polyline_global) >= 2:
                stroke_args = {
                    'col': RAIL_STROKE_COLOR_INDEX,
                    'wid': stroke_w,
                    'noi': 0.5, # Default noise for rails
                    'fun': lambda x_prog: 1 # Constant width for rail segments
                }
                draw_stroke(bitmap, polyline_global, stroke_args)

    def draw_roof(self, bitmap, x_offset, y_offset, args_roof):
        """Draws a standard roof structure."""
        hei = args_roof.get('hei', 20)
        wid = args_roof.get('wid', 120)
        rot = args_roof.get('rot', 0.7) # Rotation/perspective factor
        per = args_roof.get('per', 4)   # Perspective y-offset for the roof ridge
        cor = args_roof.get('cor', 5)   # Corner flare/overhang
        stroke_wei = args_roof.get('wei', 3)
        plaque_params = args_roof.get('pla', [0, ""]) # [enable_plaque, plaque_text]

        # Flip logic based on rotation (perspective)
        # If rot < 0.5, the left side is more prominent, so we might flip coordinates
        # for a consistent definition of "front" facing elements.
        # The JS opf function flips around axis 0.

        # Effective rotation for calculations (ensuring it's on the "closer" side)
        rrot = rot if rot >= 0.5 else 1 - rot

        # Function to flip x-coordinates if original rot < 0.5
        # This means all local x-coords will be defined as if rot >= 0.5, then flipped if needed.
        def opf(pt_list_local):
            if rot < 0.5:
                return [(-p[0], p[1]) for p in pt_list_local]
            return pt_list_local

        mid = -wid * 0.5 + wid * rrot   # Vanishing point x for the closer ridge
        # bmid = -wid * 0.5 + wid * (1 - rrot) # Vanishing point x for the further ridge (not explicitly used in JS roof's line list)
        quat = (mid + wid * 0.5) * 0.5 - mid # A quarter distance along the closer top edge, for curve points

        ptlist_roof_lines_local_unflipped = []
        # Define roof lines based on the JS structure (local coordinates, before opf flip)
        # These points define Bezier-like curves or straight lines for div.
        # Each is a list of 2 or 3 points for self.utils.div or a Bezier function.
        # For simplicity, assuming self.utils.div can handle 2 points (line) or 3 (quadratic Bezier control points).
        # If div only does linear, then these 3-point lists imply two line segments or need a Bezier helper.
        # The JS `div` is not shown, but `bezmh` takes 3 points for quadratic.
        # Let's assume these are polylines to be stroked.

        # Curved edges of the roof
        ptlist_roof_lines_local_unflipped.append( # Top-left slanted edge
            self.utils.div(opf([[-wid*0.5+quat, -hei-per/2], [-wid*0.5+quat*0.5, -hei/2-per/4], [-wid*0.5-cor, 0]]), 5)
        )
        ptlist_roof_lines_local_unflipped.append( # Top-right slanted edge
             self.utils.div(opf([[mid+quat, -hei], [(mid+quat+wid*0.5)/2, -hei/2], [wid*0.5+cor, 0]]), 5)
        )
        ptlist_roof_lines_local_unflipped.append( # Ridge-to-corner slanted edge (front)
             self.utils.div(opf([[mid+quat, -hei], [mid+quat/2, -hei/2+per/2], [mid+cor, per]]), 5)
        )

        # Straight edges of the roof
        ptlist_roof_lines_local_unflipped.append(opf([[-wid*0.5-cor, 0], [mid+cor, per]])) # Bottom front edge
        ptlist_roof_lines_local_unflipped.append(opf([[wid*0.5+cor, 0], [mid+cor, per]])) # Bottom right edge (connects to front mid)
        ptlist_roof_lines_local_unflipped.append(opf([[-wid*0.5+quat, -hei-per/2], [mid+quat, -hei]])) # Top ridge

        # Define polygon for the main roof face (local coordinates, before opf flip)
        # This is for the white fill background.
        polist_bg_local_unflipped = opf([
            (-wid*0.5, 0), (-wid*0.5+quat, -hei-per/2),
            (mid+quat, -hei), (wid*0.5, 0), (mid, per)
        ])

        # Transform points and draw
        polist_bg_global = [(p[0] + x_offset, p[1] + y_offset) for p in polist_bg_local_unflipped]
        if len(polist_bg_global) >=3:
            draw_polygon(bitmap, polist_bg_global, WHITE_COLOR_INDEX)

        for line_local_unflipped in ptlist_roof_lines_local_unflipped:
            if not line_local_unflipped or len(line_local_unflipped) < 2: continue
            line_global = [(p[0] + x_offset, p[1] + y_offset) for p in line_local_unflipped]
            stroke_args_roof = {
                'col': ROOF_STROKE_COLOR_INDEX, 'wid': stroke_wei,
                'noi': 0.1, 'fun': lambda x_prog: 1
            }
            draw_stroke(bitmap, line_global, stroke_args_roof)

        # TODO: Handle plaque text (plaque_params[0] is enable, plaque_params[1] is text)
        # This would involve creating a displayio.Label.
        # The position and rotation need to be calculated based on roof geometry.
        # JS: transform='translate("+(mp[0]+xoff)+","+(mp[1]+yoff)+") rotate("+adeg+")'"
        # mp is midpoint of a specific roof segment.
        if plaque_params[0] and plaque_params[1] != "":
            # Placeholder for plaque text logic
            # print(f"Plaque: {plaque_params[1]} at roof on {x_offset},{y_offset}")
            pass

    def draw_pagoda_roof(self, bitmap, x_offset, y_offset, args_pagoda_roof):
        """Draws a pagoda-style roof."""
        hei = args_pagoda_roof.get('hei', 20)
        wid = args_pagoda_roof.get('wid', 120)
        # rot = args_pagoda_roof.get('rot', 0.7) # Not used in JS pagodaRoof
        per = args_pagoda_roof.get('per', 4)   # Perspective y-offset for the roof ridge points
        cor = args_pagoda_roof.get('cor', 10)  # Corner flare/overhang
        sides = args_pagoda_roof.get('sid', 4) # Number of sides/tiers for the roof appearance
        stroke_wei = args_pagoda_roof.get('wei', 3)

        ptlist_roof_lines_local = []
        # Points for the background polygon, relative to (0, -hei) as the peak
        # The first point is the peak of the pagoda.
        polist_bg_local = [(0, -hei)]

        for i in range(sides):
            # Calculate points for each "side" or tier of the pagoda roof
            # fx, fy define the control point for the curve of the roof segment
            fx = wid * (i / (sides - 1) - 0.5) if sides > 1 else 0 # Avoid division by zero if sides = 1
            fy = per * (1 - abs(i / (sides - 1) - 0.5) * 2) if sides > 1 else per

            # fxx is the x-coordinate of the outer edge of this roof segment/tier
            fxx = (wid + cor) * (i / (sides - 1) - 0.5) if sides > 1 else 0

            # Each roof segment is a curve from the peak (0, -hei) through a control point to the outer edge (fxx, fy)
            # We can represent this as a polyline (list of points) using self.utils.div for interpolation.
            # The JS code uses three points for `div` to make a quadratic Bezier like curve.
            # Peak: (0, -hei)
            # Control point: (fx * 0.5, (-hei + fy) * 0.5) - midpoint towards the calculated fx,fy
            # End point: (fxx, fy)

            # If i > 0, it also draws a line from the previous fxx,fy to current fxx,fy (the bottom edge of the tier)
            if i > 0 and ptlist_roof_lines_local:
                # Get the last point of the previously added line segment (which is the previous fxx, fy)
                # This assumes ptlist_roof_lines_local stores polylines, and the last point of the last polyline is the previous (fxx, fy)
                prev_fxx_fy = ptlist_roof_lines_local[-1][-1]
                ptlist_roof_lines_local.append(self.utils.div([prev_fxx_fy, (fxx, fy)], 2)) # Straight line for bottom edge of tier

            # Define the curved segment of the roof tier
            # Points are local to the roof's own coordinate system (peak at 0, -hei)
            curve_points = [
                (0, -hei),
                (fx * 0.5, (-hei + fy) * 0.5),
                (fxx, fy)
            ]
            ptlist_roof_lines_local.append(self.utils.div(curve_points, 5)) # 5 segments for the curve

            polist_bg_local.append((fxx, fy)) # Add outer point to background polygon

        # Transform points and draw
        polist_bg_global = [(p[0] + x_offset, p[1] + y_offset) for p in polist_bg_local]
        if len(polist_bg_global) >= 3:
            draw_polygon(bitmap, polist_bg_global, WHITE_COLOR_INDEX)

        for line_local in ptlist_roof_lines_local:
            if not line_local or len(line_local) < 2: continue
            line_global = [(p[0] + x_offset, p[1] + y_offset) for p in line_local]
            stroke_args_pagoda = {
                'col': PAGODA_ROOF_STROKE_COLOR_INDEX, 'wid': stroke_wei,
                'noi': 0.1, 'fun': lambda x_prog: 1
            }
            draw_stroke(bitmap, line_global, stroke_args_pagoda)

# Placeholder Man Class
class Man:
    def __init__(self):
        pass

    def draw_man(self, bitmap, x_offset, y_offset, args_man):
        # Placeholder: Draw a simple shape or log a message
        # print(f"Placeholder: Man.draw_man called at ({x_offset}, {y_offset})")
        # Example: draw a small rectangle (10px high, 4px wide)
        # Ensure color index is valid for the bitmap's palette
        man_color = args_man.get('col', MAN_COLOR_INDEX)

        # Simple stick figure: body and head
        # Body
        body_start = (x_offset, y_offset)
        body_end = (x_offset, y_offset - 8) # 8px tall body
        draw_line(bitmap, body_start[0], body_start[1], body_end[0], body_end[1], man_color)
        # Head (simple circle - draw_polygon can approximate with enough points, or use a small square)
        head_center_x = x_offset
        head_center_y = y_offset - 10 # 2px radius head on top of body
        head_radius = 2
        # Approximate circle with a small square for simplicity with draw_polygon
        head_pts = [
            (head_center_x - head_radius, head_center_y - head_radius),
            (head_center_x + head_radius, head_center_y - head_radius),
            (head_center_x + head_radius, head_center_y + head_radius),
            (head_center_x - head_radius, head_center_y + head_radius),
        ]
        draw_polygon(bitmap, head_pts, man_color)
        # Legs (simple lines)
        # draw_line(bitmap, x_offset, y_offset, x_offset - 2, y_offset + 4, man_color)
        # draw_line(bitmap, x_offset, y_offset, x_offset + 2, y_offset + 4, man_color)
        # Arms (simple lines)
        # draw_line(bitmap, x_offset, y_offset - 6, x_offset - 3, y_offset - 4, man_color)
        # draw_line(bitmap, x_offset, y_offset - 6, x_offset + 3, y_offset - 4, man_color)
        pass


from lib.poly_tools import PolyTools
import lib.utils

class Tree:
    def __init__(self, noise_instance, utils_module, poly_tools_instance):
        self.noise_instance = noise_instance
        self.utils = utils_module
        self.poly_tools = poly_tools_instance

    def _branch(self, args):
        """
        Helper function to generate branch geometry.
        Translates the JS 'branch' function.
        :param args: Dictionary with 'hei', 'wid', 'ang', 'det', 'ben'.
        :return: [[list_of_points_side1], [list_of_points_side2]]
        """
        hei = args.get('hei', 300)
        wid = args.get('wid', 6)
        ang_offset = args.get('ang', 0)
        detail_segments = args.get('det', 10)
        bend_factor = args.get('ben', math.pi * 0.2)

        tlist = []
        nx, ny = 0, 0
        tlist.append((nx, ny))

        current_bend_angle = 0
        g = 3

        for _ in range(g):
            current_bend_angle += (bend_factor / 2 + (random.random() * bend_factor) / 2) * random.choice([-1, 1])
            nx += math.cos(current_bend_angle) * hei / g
            ny -= math.sin(current_bend_angle) * hei / g
            tlist.append((nx, ny))

        if tlist:
            tip_x, tip_y = tlist[-1]
            transform_angle_adjustment = math.atan2(tip_y, tip_x) if not (tip_x == 0 and tip_y == 0) else 0

            for i in range(len(tlist)):
                pt_x, pt_y = tlist[i]
                current_point_angle = math.atan2(pt_y, pt_x) if not (pt_x == 0 and pt_y == 0) else 0
                dist_from_origin = math.sqrt(pt_x**2 + pt_y**2)

                final_angle = current_point_angle - transform_angle_adjustment + ang_offset
                tlist[i] = (dist_from_origin * math.cos(final_angle),
                              dist_from_origin * math.sin(final_angle))

        trlist1, trlist2 = [], []

        if not tlist or len(tlist) < 2 :
            return [[],[]]

        total_interpolated_segments = (len(tlist) - 1) * detail_segments

        if not tlist: # Should not happen if len(tlist) >= 2 check passed but as safeguard
             return [[],[]]
        last_drawn_x, last_drawn_y = tlist[0]


        if total_interpolated_segments == 0:
            if len(tlist) >=2:
                p_start, p_end = tlist[0], tlist[-1]
                seg_ang = math.atan2(p_end[1]-p_start[1], p_end[0]-p_start[0]) if not (p_end[0]==p_start[0] and p_end[1]==p_start[1]) else 0
                trlist1.append((p_start[0] + wid/2 * math.cos(seg_ang + math.pi/2), p_start[1] + wid/2 * math.sin(seg_ang + math.pi/2) ))
                trlist1.append((p_end[0] + wid/2 * math.cos(seg_ang + math.pi/2), p_end[1] + wid/2 * math.sin(seg_ang + math.pi/2) ))
                trlist2.append((p_start[0] - wid/2 * math.cos(seg_ang + math.pi/2), p_start[1] - wid/2 * math.sin(seg_ang + math.pi/2) ))
                trlist2.append((p_end[0] - wid/2 * math.cos(seg_ang + math.pi/2), p_end[1] - wid/2 * math.sin(seg_ang + math.pi/2) ))
            return [trlist1, trlist2]

        for i_interp_seg in range(total_interpolated_segments + 1):
            major_seg_idx = min(math.floor(i_interp_seg / detail_segments), len(tlist)-2)

            p_major_start = tlist[major_seg_idx]
            p_major_end = tlist[major_seg_idx + 1] if major_seg_idx + 1 < len(tlist) else tlist[-1]

            interp_factor = (i_interp_seg % detail_segments) / detail_segments if detail_segments > 0 else 0

            nx_center = p_major_start[0] * (1 - interp_factor) + p_major_end[0] * interp_factor
            ny_center = p_major_start[1] * (1 - interp_factor) + p_major_end[1] * interp_factor

            current_segment_angle = math.atan2(ny_center - last_drawn_y, nx_center - last_drawn_x) \
                if not (nx_center == last_drawn_x and ny_center == last_drawn_y) \
                else (last_drawn_x if isinstance(last_drawn_x, (float, int)) else 0.0)

            woff = (self.noise_instance.noise(i_interp_seg * 0.3) - 0.5) * wid * hei / 80

            bulge = random.random() * wid if interp_factor == 0 else 0

            current_width = wid * (((total_interpolated_segments - i_interp_seg) / total_interpolated_segments) * 0.5 + 0.5) \
                if total_interpolated_segments > 0 else wid

            angle_left = current_segment_angle + math.pi / 2
            angle_right = current_segment_angle - math.pi / 2

            trlist1.append((
                nx_center + math.cos(angle_left) * (current_width + woff + bulge),
                ny_center + math.sin(angle_left) * (current_width + woff + bulge)
            ))
            trlist2.append((
                nx_center + math.cos(angle_right) * (current_width - woff + bulge),
                ny_center + math.sin(angle_right) * (current_width - woff + bulge)
            ))
            last_drawn_x, last_drawn_y = nx_center, ny_center

        return [trlist1, trlist2]

    def tree01(self, bitmap, x_offset, y_offset, args):
        """Draws tree type 01."""
        hei = args.get('hei', 50)
        wid = args.get('wid', 3)
        base_col_idx = args.get('col', 1)

        reso = 10
        nslist = []
        for i in range(reso):
            nslist.append([self.noise_instance.noise(i * 0.5), self.noise_instance.noise(i * 0.5, 0.5)])

        line1, line2 = [], []
        leaf_blob_draw_calls = []

        for i in range(reso):
            nx_base = x_offset
            ny_base = y_offset - (i * hei) / reso

            if i >= reso / 4:
                for _ in range(int((reso - i) / 5)):
                    leaf_col_idx = base_col_idx
                    blob_len_val = random.random() * 20 * (reso - i) * 0.2 + 10
                    blob_wid_val = random.random() * 6 + 3
                    blob_ang_val = (random.random() - 0.5) * math.pi / 6
                    blob_x = nx_base + (random.random() - 0.5) * wid * 1.2 * (reso - i)
                    blob_y = ny_base + (random.random() - 0.5) * wid

                    blob_args = {
                        'len': blob_len_val, 'wid': blob_wid_val, 'ang': blob_ang_val,
                        'col': leaf_col_idx, 'noi': 0.5
                    }
                    leaf_blob_draw_calls.append({'x': blob_x, 'y': blob_y, 'args': blob_args})

            line1.append((nx_base + (nslist[i][0] - 0.5) * wid - wid / 2, ny_base))
            line2.append((nx_base + (nslist[i][1] - 0.5) * wid + wid / 2, ny_base))

        if len(line1) >= 2: draw_polygon(bitmap, line1, base_col_idx)
        if len(line2) >= 2: draw_polygon(bitmap, line2, base_col_idx)

        for call_data in leaf_blob_draw_calls:
            draw_blob(bitmap, call_data['x'], call_data['y'], call_data['args'])

    def tree03(self, bitmap, x_offset, y_offset, args):
        """Draws tree type 03."""
        hei = args.get('hei', 50)
        wid = args.get('wid', 5)
        ben_func = args.get('ben', lambda p_prog: 0)
        base_col_idx = args.get('col', 1)

        reso = 10
        nslist = []
        for i in range(reso):
            nslist.append([self.noise_instance.noise(i * 0.5), self.noise_instance.noise(i * 0.5, 0.5)])

        leaf_blob_draw_calls = []
        line1, line2 = [], []

        for i in range(reso):
            nx_base = x_offset + ben_func(i / reso) * 100
            ny_base = y_offset - (i * hei) / reso

            if i >= reso / 5:
                for _ in range(int((reso - i) * 2)):
                    shape_fn = lambda p_val: math.log(50 * p_val + 1) / 3.95 if (50 * p_val + 1) > 0 else 0
                    ox = random.random() * wid * 2 * shape_fn((reso - i) / reso)
                    blob_center_x = nx_base + ox * random.choice([-1,1])
                    blob_center_y = ny_base + (random.random() - 0.5) * wid * 2
                    leaf_col_idx = base_col_idx

                    current_blob_args = {
                        'len': ox * 2, 'wid': random.random() * 6 + 3,
                        'ang': (random.random() - 0.5) * math.pi / 6,
                        'col': leaf_col_idx, 'noi': 0.5
                    }
                    leaf_blob_draw_calls.append({'x': blob_center_x, 'y': blob_center_y, 'args': current_blob_args})

            line1.append((nx_base + (((nslist[i][0] - 0.5) * wid - wid / 2) * (reso - i)) / reso, ny_base))
            line2.append((nx_base + (((nslist[i][1] - 0.5) * wid + wid / 2) * (reso - i)) / reso, ny_base))

        lc = line1 + line2[::-1]
        if len(lc) >= 2:
            # Using base_col_idx for trunk outline, JS had a 'white' fill for trunk.
            # This might need adjustment based on desired visual effect and palette.
            draw_polygon(bitmap, lc, base_col_idx)

        for blob_data in leaf_blob_draw_calls:
            draw_blob(bitmap, blob_data['x'], blob_data['y'], blob_data['args'])

    def tree07(self, bitmap, x_offset, y_offset, args):
        """Draws tree type 07 (triangulated)."""
        hei = args.get('hei', 60)
        wid = args.get('wid', 4)
        ben_func = args.get('ben', lambda p_prog: math.sqrt(p_prog) * 0.2 if p_prog >= 0 else 0)
        base_col_idx = args.get('col', 1)

        reso = 10
        nslist = []
        for i in range(reso):
            nslist.append([self.noise_instance.noise(i * 0.5), self.noise_instance.noise(i * 0.5, 0.5)])

        T = []

        for i in range(reso):
            nx_base = x_offset + ben_func(i / reso) * 100
            ny_base = y_offset - (i * hei) / reso
            if i >= reso / 4:
                for _ in range(1):
                    def tree07_blob_shape_fun(p_val):
                        if p_val <= 1: return 2.75 * p_val * math.pow(1 - p_val, 1 / 1.8) if (1-p_val) >=0 else 0
                        else: return 2.75 * (p_val - 2) * math.pow(p_val - 1, 1 / 1.8) if (p_val-1)>=0 else 0

                    leaf_col_idx = base_col_idx
                    blob_gen_args = {
                        'len': random.random() * 50 + 20, 'wid': random.random() * 12 + 12,
                        'ang': (-random.random() * math.pi) / 6, 'col': leaf_col_idx,
                        'noi': 0.5, 'fun': tree07_blob_shape_fun,
                    }
                    blob_center_x = nx_base + (random.random() - 0.5) * wid * 1.2 * (reso - i) * 0.5
                    blob_center_y = ny_base + (random.random() - 0.5) * wid * 0.5

                    bpl = get_blob_points(blob_center_x, blob_center_y, blob_gen_args, self.noise_instance)

                    if bpl and len(bpl) >= 3:
                        # Ensure poly_tools is available
                        if hasattr(self, 'poly_tools') and self.poly_tools:
                            triangles = self.poly_tools.triangulate(bpl, {'area': 50, 'convex': True, 'optimize': False})
                            T.extend(triangles)
                        else:
                            print("Warning: poly_tools not available in Tree instance for tree07.")

        line1, line2 = [], []
        for i in range(reso):
            nx_base = x_offset + ben_func(i / reso) * 100
            ny_base = y_offset - (i * hei) / reso
            line1.append((nx_base + (nslist[i][0] - 0.5) * wid - wid / 2, ny_base))
            line2.append((nx_base + (nslist[i][1] - 0.5) * wid + wid / 2, ny_base))

        trunk_poly_pts = line1 + line2[::-1]
        if len(trunk_poly_pts) >= 3:
            if hasattr(self, 'poly_tools') and self.poly_tools:
                triangles_trunk = self.poly_tools.triangulate(trunk_poly_pts, {'area': 50, 'convex': True, 'optimize': True})
                T.extend(triangles_trunk)
            else:
                print("Warning: poly_tools not available in Tree instance for tree07 trunk.")

        for triangle_pts in T:
            if not triangle_pts or len(triangle_pts) < 3: continue

            if hasattr(self, 'poly_tools') and self.poly_tools:
                m = self.poly_tools.mid_pt(triangle_pts)
                noise_color_val = self.noise_instance.noise(m[0] * 0.02, m[1] * 0.02)
                mapped_color_index = base_col_idx if noise_color_val > 0.5 else 0
                draw_polygon(bitmap, triangle_pts, mapped_color_index)
            else:
                # Fallback if poly_tools not available: draw outline of the triangle points
                draw_polygon(bitmap, triangle_pts, base_col_idx)

    def _twig(self, bitmap, tx, ty, dep, args):
        """
        Helper function to draw a twig with potential sub-twigs and leaves.
        :param bitmap: The displayio.Bitmap to draw on.
        :param tx, ty: Starting coordinates of the twig (absolute, already offset).
        :param dep: Current recursion depth for sub-twigs.
        :param args: Dictionary with 'dir', 'sca', 'wid', 'ang', 'lea', 'col'.
        """
        direction = args.get('dir', 1)
        scale = args.get('sca', 1)
        stroke_w = args.get('wid', 1)
        angle = args.get('ang', 0)
        leaf_params = args.get('lea', [True, 12])
        base_col_idx = args.get('col', 1)

        twlist = []
        tl = 10
        hs = random.random() * 0.5 + 0.5

        def twig_shape_func(idx, total_segments):
            if total_segments == 0: return 1
            return -1 / math.pow(idx / total_segments + 1, 5) + 1

        a0 = ((random.random() * math.pi) / 6) * direction + angle

        next_twig_start_x, next_twig_start_y = tx, ty

        for i_seg in range(tl):
            mx_rel = direction * twig_shape_func(i_seg, tl) * 50 * scale * hs
            my_rel = -i_seg * 5 * scale

            segment_angle_unrotated = math.atan2(my_rel, mx_rel) if not (mx_rel == 0 and my_rel == 0) else 0
            segment_dist = math.sqrt(mx_rel**2 + my_rel**2)

            px = tx + segment_dist * math.cos(segment_angle_unrotated + a0)
            py = ty + segment_dist * math.sin(segment_angle_unrotated + a0)
            twlist.append((px, py))

            next_twig_start_x, next_twig_start_y = px, py

            if (i_seg == int(tl / 3) or i_seg == int(tl * 2 / 3)) and dep > 0:
                sub_twig_args = args.copy()
                sub_twig_args['dir'] = direction * random.choice([-1, 1])
                sub_twig_args['sca'] = scale * 0.8
                self._twig(bitmap, next_twig_start_x, next_twig_start_y, dep - 1, sub_twig_args)

            if i_seg == tl - 1 and leaf_params[0]:
                leaf_size_param = leaf_params[1]
                for j_leaf in range(5):
                    dj = (j_leaf - 2.5) * 5

                    def leaf_blob_fun(p_val):
                        if p_val <= 1:
                            return math.pow(math.sin(p_val * math.pi) * p_val, 0.5) if p_val >=0 else 0
                        else:
                            return -math.pow(math.sin((p_val - 2) * math.pi * (p_val - 2)), 0.5) if (p_val-2) >=0 and (p_val-1)>=0 else 0

                    leaf_col_idx = base_col_idx

                    blob_args_leaf = {
                        'len': (15 + 12 * random.random()) * stroke_w * scale,
                        'wid': (6 + 3 * random.random()) * stroke_w * scale,
                        'ang': angle / 2 + math.pi / 2 + math.pi * 0.2 * (random.random() - 0.5),
                        'col': leaf_col_idx,
                        'noi': 0.5,
                        'fun': leaf_blob_fun
                    }
                    draw_blob(bitmap,
                              next_twig_start_x + math.cos(angle) * dj * stroke_w * scale,
                              next_twig_start_y + (math.sin(angle) * dj - leaf_size_param / (dep + 1)) * stroke_w * scale,
                              blob_args_leaf)

        if len(twlist) >= 2:
            stroke_args_twig = {
                'wid': stroke_w * scale,
                'col': base_col_idx,
                'noi': 0.1,
                'fun': lambda x_prog: math.cos(x_prog * math.pi / 2)
            }
            draw_stroke(bitmap, twlist, stroke_args_twig)

    def tree05(self, bitmap, x_offset, y_offset, args):
        """
        Draws tree type 05.
        :param bitmap: The displayio.Bitmap to draw on.
        :param x_offset: Base x-coordinate for the tree.
        :param y_offset: Base y-coordinate for the tree.
        :param args: Dictionary with 'hei', 'wid', 'col'.
        """
        hei = args.get('hei', 300)
        wid = args.get('wid', 5)
        base_col_idx = args.get('col', 1)
        color_white_index = args.get('white_col_idx', 0)

        main_branch_args = {'hei': hei, 'wid': wid, 'ang': -math.pi / 2, 'ben': 0, 'det': max(2,int(hei / 20))}
        trlist_main1, trlist_main2 = self._branch(main_branch_args)

        # TODO: Call barkify here.
        # Example: self.barkify(bitmap, x_offset, y_offset, [main_trunk_rel1_abs, main_trunk_rel2_abs], {})

        trlist_combined = trlist_main1 + trlist_main2[::-1]
        trmlist = []

        for i in range(len(trlist_combined)):
            pt_on_trunk = trlist_combined[i]

            p_progress = 0
            if i < len(trlist_main1):
                p_progress = i / len(trlist_main1) if len(trlist_main1) > 0 else 0
            else:
                p_progress = (len(trlist_combined) - 1 - i) / len(trlist_main2) if len(trlist_main2) > 0 else 0
            p_progress = 1.0 - p_progress

            should_branch = False
            if len(trlist_combined) * 0.2 <= i <= len(trlist_combined) * 0.8:
                if i % 3 == 0 and random.random() > p_progress:
                    should_branch = True
            if i == math.floor(len(trlist_combined) / 2) - 1 :
                 should_branch = True

            if should_branch:
                bar = random.random() * 0.2
                is_second_half = i >= len(trlist_main1)
                ba = -bar * math.pi - (1 - bar * 2) * math.pi * is_second_half

                sub_branch_height = hei * (0.3 * p_progress - random.random() * 0.05)
                if sub_branch_height <=0: sub_branch_height = hei * 0.05

                sub_branch_args = {
                    'hei': sub_branch_height, 'wid': wid * 0.5, 'ang': ba,
                    'ben': 0.5, 'det': max(2, int(sub_branch_height / 10))
                }
                brlist_sub1, brlist_sub2 = self._branch(sub_branch_args)

                brlist_sub1_offset_from_trunk_pt = [(p[0] + pt_on_trunk[0], p[1] + pt_on_trunk[1]) for p in brlist_sub1]
                brlist_sub2_offset_from_trunk_pt = [(p[0] + pt_on_trunk[0], p[1] + pt_on_trunk[1]) for p in brlist_sub2]

                for j_twig in range(len(brlist_sub1_offset_from_trunk_pt)):
                    if j_twig % 20 == 0 or j_twig == len(brlist_sub1_offset_from_trunk_pt) - 1:
                        twig_args = {
                            'wid': hei / 300 if hei > 0 else 0.1,
                            'ang': ba if ba > -math.pi / 2 else ba + math.pi,
                            'sca': (0.2 * hei) / 300 if hei > 0 else 0.02,
                            'dir': 1 if (ba > -math.pi / 2) else -1,
                            'lea': [True, 5],
                            'col': base_col_idx
                        }
                        twig_start_x = brlist_sub1_offset_from_trunk_pt[j_twig][0] + x_offset
                        twig_start_y = brlist_sub1_offset_from_trunk_pt[j_twig][1] + y_offset
                        self._twig(bitmap, twig_start_x, twig_start_y, 0, twig_args)

                trmlist.extend(brlist_sub1_offset_from_trunk_pt)
                trmlist.extend(brlist_sub2_offset_from_trunk_pt[::-1])
            else:
                trmlist.append(pt_on_trunk)

        trmlist_transformed_abs = [(p[0] + x_offset, p[1] + y_offset) for p in trmlist]
        if len(trmlist_transformed_abs) >= 3:
            draw_polygon(bitmap, trmlist_transformed_abs, color_white_index)

        if len(trmlist_transformed_abs) > 2:
            trmlist_for_stroke = trmlist_transformed_abs[1:-1]
            if len(trmlist_for_stroke) >=2:
                stroke_args = {
                    'col': base_col_idx, 'wid': 2.5, 'noi': 0.9,
                    'fun': lambda x_prog: math.sin(1)
                }
                draw_stroke(bitmap, trmlist_for_stroke, stroke_args)

    def _generate_fractal_detail(self, bitmap, x_start, y_start, dep, args_detail):
        """
        Helper for drawing fine fractal details, like in tree08.
        Draws directly to the bitmap.
        """
        ang = args_detail.get('ang', -math.pi / 2)
        length = args_detail.get('len', 15)
        ben = args_detail.get('ben', 0)
        color_index = args_detail.get('col', 1)

        fun_width_modulator = (lambda x_prog: math.cos(0.5 * math.pi * x_prog)) if dep == 0 else (lambda x_prog: 1)

        spt_global = (x_start, y_start)
        ept_global = (x_start + math.cos(ang) * length,
                      y_start + math.sin(ang) * length)

        current_segment_pts_local = [(0,0), (length, 0)]

        bfun = random.choice([
            lambda x_prog: math.sin(x_prog * math.pi),
            lambda x_prog: -math.sin(x_prog * math.pi)
        ])

        subdivided_pts_local = self.utils.div(current_segment_pts_local, 10)

        trmlist_bent_local = []
        if not subdivided_pts_local:
            return

        for i in range(len(subdivided_pts_local)):
            pt_sub_local = subdivided_pts_local[i]
            bent_y_local = pt_sub_local[1] + bfun(i / len(subdivided_pts_local)) * 2
            trmlist_bent_local.append((pt_sub_local[0], bent_y_local))

        trmlist_global_for_stroke = []
        for pt_bent_local in trmlist_bent_local:
            dist_from_origin = math.sqrt(pt_bent_local[0]**2 + pt_bent_local[1]**2)
            angle_local = math.atan2(pt_bent_local[1], pt_bent_local[0]) if dist_from_origin > 0 else 0

            global_x = x_start + dist_from_origin * math.cos(angle_local + ang)
            global_y = y_start + dist_from_origin * math.sin(angle_local + ang)
            trmlist_global_for_stroke.append((global_x,global_y))

        if len(trmlist_global_for_stroke) >=2:
            stroke_args = {
                'fun': fun_width_modulator,
                'wid': 0.8,
                'col': color_index,
                'noi': 0
            }
            draw_stroke(bitmap, trmlist_global_for_stroke, stroke_args)

        if dep != 0:
            nben = ben + random.choice([-1, 1]) * math.pi * 0.001 * dep * dep

            num_recursive_calls = 1 if random.random() < 0.5 else 2
            angle_factor_ranges = [(-1, 0.5), (0.5, 1)]

            for i_call in range(num_recursive_calls):
                # Corrected logic for selecting angle factor range
                current_range_idx = i_call if num_recursive_calls == 2 else 0 # Use first range if only one call, or cycle for two
                current_range = angle_factor_ranges[current_range_idx % len(angle_factor_ranges)]
                if num_recursive_calls == 1: # If only one call, use wider range
                    current_range = (-1,1)

                angle_factor = self.utils.norm_rand(current_range[0], current_range[1])

                detail_args_recurse = {
                    'ang': ang + ben + math.pi * angle_factor * 0.2,
                    'len': length * self.utils.norm_rand(0.8, 0.9),
                    'ben': nben,
                    'col': color_index
                }
                self._generate_fractal_detail(bitmap, ept_global[0], ept_global[1], dep - 1, detail_args_recurse)

    def tree08(self, bitmap, x_offset, y_offset, args):
        """
        Draws tree type 08.
        """
        hei = args.get('hei', 80)
        wid = args.get('wid', 1)
        base_col_idx = args.get('col', 1)
        color_white_index = args.get('white_col_idx', 0)

        ang_trunk_offset = self.utils.norm_rand(-1, 1) * math.pi * 0.2
        detail_segments_trunk = max(2, int(hei / 20))

        main_trunk_args = {
            'hei': hei,
            'wid': wid,
            'ang': -math.pi / 2 + ang_trunk_offset,
            'ben': math.pi * 0.2,
            'det': detail_segments_trunk
        }
        main_trunk_rel1, main_trunk_rel2 = self._branch(main_trunk_args)

        main_trunk_abs_poly_pts = \
            [(p[0] + x_offset, p[1] + y_offset) for p in main_trunk_rel1] + \
            [(p[0] + x_offset, p[1] + y_offset) for p in main_trunk_rel2[::-1]]

        # TODO: Barkify for main_trunk
        # self.barkify(bitmap, main_trunk_abs_poly_pts, {})

        trunk_centerline_approx = main_trunk_rel1

        for i in range(len(trunk_centerline_approx)):
            pt_on_trunk_rel = trunk_centerline_approx[i]
            pt_on_trunk_abs_x = pt_on_trunk_rel[0] + x_offset
            pt_on_trunk_abs_y = pt_on_trunk_rel[1] + y_offset

            should_add_detail = False
            if random.random() < 0.2:
                should_add_detail = True
            elif i == math.floor(len(trunk_centerline_approx) / 2):
                should_add_detail = True

            if should_add_detail:
                recursion_depth = math.floor(4 * random.random()) if i != math.floor(len(trunk_centerline_approx) / 2) else 3
                detail_len = args.get('detail_len', 15)

                detail_args = {
                    'ang': -math.pi / 2 - ang_trunk_offset * random.random(),
                    'len': detail_len,
                    'ben': 0,
                    'col': base_col_idx
                }
                self._generate_fractal_detail(bitmap,
                                              pt_on_trunk_abs_x,
                                              pt_on_trunk_abs_y,
                                              recursion_depth,
                                              detail_args)

        if len(main_trunk_abs_poly_pts) >= 3:
            draw_polygon(bitmap, main_trunk_abs_poly_pts, color_white_index)

        if len(main_trunk_abs_poly_pts) > 1:
            stroke_args_trunk = {
                'col': base_col_idx,
                'wid': 2.5,
                'noi': 0.9,
                'fun': lambda x_prog: math.sin(1)
            }
            draw_stroke(bitmap, main_trunk_abs_poly_pts, stroke_args_trunk)

    def _frac_tree(self, bitmap, x_accum, y_accum, dep, args_frac):
        """
        Recursive helper for generating fractal tree geometry (like in tree06).
        Points returned are relative to the x_accum, y_accum of this call's *branch base*.
        Drawing of twigs/bark happens directly within this function or its children,
        using absolute coordinates derived from x_accum, y_accum and local point coordinates.
        """
        hei = args_frac.get('hei', 100)
        wid = args_frac.get('wid', 6)
        ang = args_frac.get('ang', 0)
        ben = args_frac.get('ben', 0)
        base_col_idx = args_frac.get('col', 1)

        detail_val = max(2, int(hei / 20))

        branch_args = {'hei': hei, 'wid': wid, 'ang': ang, 'ben': ben, 'det': detail_val}
        tr_segment_pts_list1, tr_segment_pts_list2 = self._branch(branch_args)

        current_branch_outline_local = tr_segment_pts_list1 + tr_segment_pts_list2[::-1]
        trmlist_recursive_for_outline = []

        if not current_branch_outline_local:
            return []

        for i in range(len(current_branch_outline_local)):
            pt_local = current_branch_outline_local[i]
            pt_abs_x, pt_abs_y = x_accum + pt_local[0], y_accum + pt_local[1]
            trmlist_recursive_for_outline.append(pt_local)

            is_mid_point_ish = (i == math.floor(len(current_branch_outline_local)/2) -1 or \
                                i == math.floor(len(current_branch_outline_local)/2) +1)
            is_in_branching_zone = (len(current_branch_outline_local)*0.2 <= i <= len(current_branch_outline_local)*0.8)

            should_recurse_and_branch = False
            if dep > 0:
                if is_mid_point_ish:
                    should_recurse_and_branch = True
                elif is_in_branching_zone and random.random() < 0.025:
                    should_recurse_and_branch = True

            if should_recurse_and_branch:
                bar = 0.02 + random.random() * 0.08
                is_second_half_of_branch = i >= len(tr_segment_pts_list1)
                ba_sub_branch = bar * math.pi - bar * 2 * math.pi * is_second_half_of_branch

                new_args_frac = {
                    'hei': hei * (0.7 + random.random() * 0.2),
                    'wid': wid * 0.6,
                    'ang': ang + ba_sub_branch,
                    'ben': args_frac.get('sub_ben', 0.55),
                    'col': base_col_idx
                }
                sub_branch_outline_pts = self._frac_tree(bitmap, pt_abs_x, pt_abs_y, dep - 1, new_args_frac)

                for sp_rel_to_sub_base in sub_branch_outline_pts:
                    trmlist_recursive_for_outline.append((sp_rel_to_sub_base[0] + pt_local[0], sp_rel_to_sub_base[1] + pt_local[1]))

                if random.random() < 0.03:
                    twig_args = {
                        'ang': ba_sub_branch * (random.random() * 0.5 + 0.75),
                        'sca': 0.3, 'dir': 1 if ba_sub_branch > 0 else -1,
                        'lea': [False, 0], 'wid': max(1, wid * 0.1), 'col': base_col_idx
                    }
                    self._twig(bitmap, pt_abs_x, pt_abs_y, 2, twig_args)

        return trmlist_recursive_for_outline

    def tree06(self, bitmap, x_offset, y_offset, args):
        """
        Draws tree type 06 (Fractal Tree).
        """
        hei = args.get('hei', 100)
        wid = args.get('wid', 6)
        base_col_idx = args.get('col', 1)
        color_white_index = args.get('white_col_idx', 0)

        initial_frac_args = {
            'hei': hei,
            'wid': wid,
            'ang': -math.pi / 2,
            'ben': 0,
            'col': base_col_idx,
            'sub_ben': 0.55
        }

        trmlist_total_relative_to_base = self._frac_tree(bitmap, x_offset, y_offset, 3, initial_frac_args)

        trmlist_total_transformed = [(p[0] + x_offset, p[1] + y_offset) for p in trmlist_total_relative_to_base]

        if len(trmlist_total_transformed) >= 3:
            draw_polygon(bitmap, trmlist_total_transformed, color_white_index)

        if len(trmlist_total_transformed) > 2:
            trmlist_for_stroke = trmlist_total_transformed[1:-1]
            if len(trmlist_for_stroke) >= 2:
                stroke_args = {
                    'col': base_col_idx, 'wid': 2.5, 'noi': 0.9,
                    'fun': lambda x_prog: math.sin(1)
                }
                draw_stroke(bitmap, trmlist_for_stroke, stroke_args)
