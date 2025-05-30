import math
import random
from lib.poly_tools import PolyTools # Added import
from lib.rng import Prng # Added import

# Initialize Prng and PolyTools instances
# These will be used by functions that were originally using Math.random or PolyTools.midPt in JS
prng_instance = Prng()
prng_instance.seed() # Seed the random number generator

poly_tools_instance = PolyTools()


def un_nan(plist):
    if not isinstance(plist, list) or plist is None:
        return plist or 0
    else:
        return [un_nan(item) for item in plist]

def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)

def mapval(value, istart, istop, ostart, ostop):
    return ostart + (ostop - ostart) * ((value - istart) / (istop - istart))

def loop_noise(nslist):
    if not nslist: # Added check for empty list
        return
    dif = nslist[-1] - nslist[0]
    bds = [100, -100]
    for i in range(len(nslist)):
        nslist[i] += (dif * (len(nslist) - 1 - i)) / (len(nslist) - 1)
        if nslist[i] < bds[0]:
            bds[0] = nslist[i]
        if nslist[i] > bds[1]:
            bds[1] = nslist[i]

    # Added check to prevent division by zero if bds[0] == bds[1]
    if bds[0] == bds[1]:
        for i in range(len(nslist)):
            nslist[i] = 0 # Or some other default value like 0.5, or handle as an error
        return # Exit if range is zero

    for i in range(len(nslist)):
        nslist[i] = mapval(nslist[i], bds[0], bds[1], 0, 1)

def rand_choice(arr):
    return arr[math.floor(len(arr) * prng_instance.next())] # Uses prng_instance

def norm_rand(m, M):
    return mapval(prng_instance.next(), 0, 1, m, M) # Uses prng_instance

def wtrand(func):
    x = prng_instance.next() # Uses prng_instance
    y = prng_instance.next() # Uses prng_instance
    if y < func(x):
        return x
    else:
        return wtrand(func)

def rand_gaussian():
    return (wtrand(lambda x: math.exp(-24 * (x - 0.5)**2)) * 2 - 1)

def bezmh(P, w=1):
    if len(P) == 2:
        # Uses poly_tools_instance for midPt
        P = [P[0], poly_tools_instance.mid_pt(P[0], P[1]), P[1]]
    plist = []
    for j in range(len(P) - 2):
        p0 = P[j] if j == 0 else poly_tools_instance.mid_pt(P[j], P[j + 1]) # Uses poly_tools_instance
        p1 = P[j + 1]
        p2 = P[j + 2] if j == len(P) - 3 else poly_tools_instance.mid_pt(P[j + 1], P[j + 2]) # Uses poly_tools_instance

        pl = 20
        for i in range(pl + (1 if j == len(P) - 3 else 0)): # Adjusted loop range
            t = i / pl
            u_calc = (1 - t)**2 + 2 * t * (1 - t) * w + t**2 # Renamed 'u' to 'u_calc'
            if u_calc == 0: continue # Avoid division by zero

            x_coord = ((1 - t)**2 * p0[0] + 2 * t * (1 - t) * p1[0] * w + t**2 * p2[0]) / u_calc
            y_coord = ((1 - t)**2 * p0[1] + 2 * t * (1 - t) * p1[1] * w + t**2 * p2[1]) / u_calc
            plist.append([x_coord, y_coord])
    return plist

def poly(plist, args=None):
    args = args if args is not None else {}
    xof = args.get('xof', 0)
    yof = args.get('yof', 0)
    fil = args.get('fil', "rgba(0,0,0,0)")
    st_r = args.get('str', fil) # Renamed 'str' to 'st_r' to avoid conflict with Python's str
    wid = args.get('wid', 0)

    # Simplified SVG polyline string construction
    points_str = " ".join([f"{(p[0] + xof):.1f},{(p[1] + yof):.1f}" for p in plist])
    return f"<polyline points='{points_str}' style='fill:{fil};stroke:{st_r};stroke-width:{wid}'/>"

# Example Usage (Optional)
if __name__ == '__main__':
    print(f"Random Choice from [1,2,3]: {rand_choice([1,2,3])}")
    print(f"Normalized Random (10-20): {norm_rand(10,20)}")
    print(f"Gaussian Random: {rand_gaussian()}")

    points_for_bezmh = [[0,0], [10,10], [20,5], [30,15]]
    # print(f"Bezmh: {bezmh(points_for_bezmh)}") #Temporarily commented out due to Polytools dependency

    svg_poly = poly([[10,10], [20,20], [30,10]], {'fil': 'blue', 'str': 'red', 'wid': 1})
    print(f"SVG Polyline: {svg_poly}")
