# tests/test_utils.py
import unittest # Or use simple asserts if unittest is not desired for CircuitPython target
import math
# Assuming lib.utils is accessible, adjust path if necessary when running tests
# For local testing, PYTHONPATH might need to be set, or run as a module.
try:
    from lib import utils
    from lib import poly_tools # For utils.bezmh dependency
    from lib import rng # For utils.prng_instance dependency
except ImportError:
    # This path adjustment is often needed for local testing outside a proper package structure
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from lib import utils
    from lib import poly_tools # For utils.bezmh dependency
    from lib import rng # For utils.prng_instance dependency

class TestUtils(unittest.TestCase):

    def setUp(self):
        # It's good practice to ensure that any global state in utils is reset or managed if necessary
        # For lib.utils, prng_instance and poly_tools_instance are created at module level.
        # For repeatable tests, we might want to seed the prng_instance or replace it.
        utils.prng_instance.seed(12345) # Seed for predictable tests

    def test_mapval(self):
        self.assertEqual(utils.mapval(0.5, 0, 1, 0, 100), 50.0)
        self.assertEqual(utils.mapval(0, 0, 1, 0, 100), 0.0)
        self.assertEqual(utils.mapval(1, 0, 1, 0, 100), 100.0)
        self.assertEqual(utils.mapval(5, 0, 10, 0, 100), 50.0)
        self.assertEqual(utils.mapval(0.25, 0, 1, 100, 200), 125.0)
        # Test case with ostart > ostop
        self.assertEqual(utils.mapval(0.5, 0, 1, 100, 0), 50.0)
        # Test case with negative numbers
        self.assertEqual(utils.mapval(-5, -10, 0, 0, 100), 50.0)
        # Test case where value is outside istart/istop (extrapolation)
        self.assertEqual(utils.mapval(2, 0, 1, 0, 100), 200.0)
        self.assertEqual(utils.mapval(-1, 0, 1, 0, 100), -100.0)
        # Test with istart == istop (should ideally handle gracefully, e.g. return ostart or error)
        with self.assertRaises(ZeroDivisionError): # Or check for specific behavior if it's handled differently
             utils.mapval(1, 0, 0, 0, 100) # This will cause ZeroDivisionError
        print("Tested mapval")


    def test_distance(self):
        self.assertEqual(utils.distance((0,0), (3,4)), 5.0)
        self.assertEqual(utils.distance((0,0), (0,0)), 0.0)
        self.assertEqual(utils.distance((-1,-1), (1,1)), math.sqrt(8)) # sqrt(2^2 + 2^2) = sqrt(4+4)
        print("Tested distance")

    def test_loop_noise(self):
        # Test that loop_noise correctly normalizes and adjusts a list of noise values.
        noise_list_1 = [0.1, 0.2, 0.8, 0.9]
        expected_output_1 = [0.1, 0.2, 0.8, 0.9] # Example, actual output depends on its logic
        # The function modifies the list in place, so make a copy for comparison if needed
        # or derive the expected output based on the algorithm

        # Test case 1: Simple list
        nl1_copy = list(noise_list_1)
        utils.loop_noise(nl1_copy)
        # The exact values depend on the loop_noise algorithm's specifics (subtracting diff, re-mapping)
        # For now, just check if it runs and values are between 0 and 1
        for val in nl1_copy:
            self.assertTrue(0 <= val <= 1)

        # Test case 2: Already looped (should ideally not change much or stay valid)
        nl2 = [0.5, 0.6, 0.4, 0.5] # Ends match start
        nl2_copy = list(nl2)
        utils.loop_noise(nl2_copy)
        for val in nl2_copy:
            self.assertTrue(0 <= val <= 1)
        # self.assertAlmostEqual(nl2_copy[0], nl2_copy[-1]) # Check if it remains looped

        # Test case 3: Flat list
        nl3 = [0.5, 0.5, 0.5, 0.5]
        nl3_copy = list(nl3)
        utils.loop_noise(nl3_copy) # Should handle this, likely all values become 0 or stay 0.5
        # If bds[0] == bds[1], mapval would result in division by zero if not handled.
        # The updated loop_noise handles this by setting all to 0.
        self.assertEqual(nl3_copy, [0.0, 0.0, 0.0, 0.0])

        # Test case 4: Empty list
        nl4 = []
        utils.loop_noise(nl4) # Should not error
        self.assertEqual(nl4, [])

        print("Tested loop_noise (basic checks for 0-1 range and handling of flat/empty lists)")


    def test_norm_rand(self):
        # Test that norm_rand returns values within the specified range [m, M]
        m, M = 10, 20
        for _ in range(100):
            val = utils.norm_rand(m, M)
            self.assertTrue(m <= val <= M)

        m, M = -5, 5
        for _ in range(100):
            val = utils.norm_rand(m, M)
            self.assertTrue(m <= val <= M)
        print("Tested norm_rand (value range)")

    def test_rand_gaussian(self):
        # Test that rand_gaussian returns values, distribution is harder to test simply
        # We expect values roughly between -1 and 1, centered around 0
        vals = [utils.rand_gaussian() for _ in range(1000)]
        for val in vals:
            self.assertTrue(-1.5 < val < 1.5) # Generous range, true Gaussian is unbounded

        mean = sum(vals) / len(vals)
        # For a large sample, mean should be close to 0
        self.assertTrue(-0.2 < mean < 0.2) # Check if mean is reasonably close to 0
        print("Tested rand_gaussian (value range and approximate mean)")


    # Note: Testing utils.bezmh and utils.div would require PolyTools instance setup
    # or making them independent of PolyTools if they are purely geometric.
    # utils.bezmh currently uses poly_tools_instance from utils module.
    # utils.div is not present in the provided utils.py, so can't test.

if __name__ == '__main__':
    unittest.main()
