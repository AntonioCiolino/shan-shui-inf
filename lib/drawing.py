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
        draw_line(bitmap, p1[0], p1[1], p2[0], p2[1], color_index)

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
    # Pass the global perlin_noise_instance to get_blob_points
    points = get_blob_points(x_center, y_center, args, perlin_noise_instance)
    color_index = args.get('col', 1)
    if points: # Ensure points were generated
        draw_polygon(bitmap, points, color_index)

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
