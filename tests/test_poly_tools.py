# tests/test_poly_tools.py
import unittest
try:
    from lib import poly_tools
    from lib import utils # PolyTools.bezzmh might depend on utils for mid_pt if not using its own
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from lib import poly_tools
    from lib import utils # PolyTools.bezzmh might depend on utils for mid_pt

class TestPolyTools(unittest.TestCase):

    def setUp(self):
        self.pt = poly_tools.PolyTools()
        # If PolyTools depends on other modules like utils, they might need to be instantiated
        # or their state managed here if PolyTools modifies them or relies on their state.
        # Based on current PolyTools, it seems mostly self-contained or uses passed-in instances for some methods.
        # The version of bezzmh in Man._draw_cloth_segment passes utils_instance.
        # The version in lib/utils.py uses a global poly_tools_instance.
        # For PolyTools class's own methods, ensure they are self-reliant or use passed instances.
        self.utils_instance = utils # Pass the module if PolyTools methods expect a utils_instance


    def test_mid_pt(self):
        self.assertEqual(self.pt.mid_pt([[0,0], [2,2]]), [1.0,1.0])
        self.assertEqual(self.pt.mid_pt([[0,0], [2,2], [1,1]]), [1.0,1.0]) # Average
        self.assertEqual(self.pt.mid_pt([[0,0]]), [0.0,0.0])
        self.assertEqual(self.pt.mid_pt([]), [0,0]) # Current behavior for empty list
        print("Tested mid_pt")

    def test_triangulate_simple_square(self):
        square = [[0,0], [10,0], [10,10], [0,10]]
        # Triangulation args default to {'area': 100, 'convex': False, 'optimize': True}
        # For a simple square, default area might be too large to force triangulation.
        triangles = self.pt.triangulate(square, {'area': 1})
        self.assertIsNotNone(triangles)
        if triangles: # Only proceed if triangles are returned
            self.assertEqual(len(triangles), 2) # A square should be two triangles
            # Could also check total area or specific vertex properties
        print("Tested triangulate_simple_square")

    def test_triangulate_triangle(self):
        triangle_in = [[0,0], [10,0], [5,10]]
        triangles = self.pt.triangulate(triangle_in, {'area': 1})
        self.assertIsNotNone(triangles)
        if triangles:
            self.assertEqual(len(triangles), 1)
            # Check if the returned triangle is similar to the input (considering vertex order might change)
            # For simplicity, check if all points are close.
            returned_pts = sorted([tuple(p) for p in triangles[0]])
            expected_pts = sorted([tuple(p) for p in triangle_in])
            self.assertEqual(returned_pts, expected_pts)
        print("Tested triangulate_triangle (already a triangle)")

    def test_triangulate_convex_polygon(self):
        # Pentagon
        pentagon = [[0,0], [10,0], [12,8], [5,12], [-2,8]]
        triangles = self.pt.triangulate(pentagon, {'area': 1})
        self.assertIsNotNone(triangles)
        if triangles:
            self.assertEqual(len(triangles), 3) # N-2 triangles for a convex polygon (5-2=3)
        print("Tested triangulate_convex_polygon (pentagon)")

    def test_bezzmh(self):
        # bezzmh(ptlist, resolution, utils_instance_if_needed)
        # The PolyTools.bezzmh method was added to Man class,
        # the original bezzmh is in lib.utils and uses a global poly_tools_instance for mid_pt.
        # If testing PolyTools.bezzmh (if it exists), it would be self.pt.bezzmh(...)
        # If testing utils.bezmh, it's utils.bezmh(...)

        # Test case for utils.bezmh (which uses utils.poly_tools_instance.mid_pt)
        points1 = [[0,0], [10,10], [20,0]]
        smoothed1 = utils.bezmh(points1, w=2) # w is resolution in original JS, here it's weight
                                              # The function signature in utils.py is bezzmh(P, w=1)
                                              # where w is the weight, not resolution. Resolution is hardcoded (pl=20)
        self.assertTrue(len(smoothed1) > 0)
        if smoothed1:
            self.assertAlmostEqual(smoothed1[0][0], 0) # Starts near first point
            self.assertAlmostEqual(smoothed1[0][1], 0)
            self.assertAlmostEqual(smoothed1[-1][0], 20) # Ends near last point
            self.assertAlmostEqual(smoothed1[-1][1], 0)

        points2 = [[0,0], [10,10]] # Two points
        smoothed2 = utils.bezmh(points2, w=2)
        # For 2 points, it inserts a mid_pt and then processes effectively 3 points.
        self.assertTrue(len(smoothed2) > 0)
        if smoothed2:
            self.assertAlmostEqual(smoothed2[0][0], 0)
            self.assertAlmostEqual(smoothed2[0][1], 0)
            self.assertAlmostEqual(smoothed2[-1][0], 10)
            self.assertAlmostEqual(smoothed2[-1][1], 10)

        print("Tested utils.bezmh (basic checks)")

    # Add more tests for triangulation:
    # - Concave polygon (behavior depends on algorithm's capabilities)
    # - Polygons with collinear points
    # - Polygons with very few points (e.g., < 3) - should be handled gracefully

if __name__ == '__main__':
    unittest.main()
