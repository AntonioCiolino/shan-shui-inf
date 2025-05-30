import time
import json
import base64
import math

class Prng:
    def __init__(self):
        self.s = 1234
        self.p = 999979  # 9887 #983
        self.q = 999983  # 9967 #991
        self.m = self.p * self.q

    def hash(self, x):
        y = base64.b64encode(json.dumps(x).encode('utf-8')).decode('utf-8')
        z = 0
        for i in range(len(y)):
            z += ord(y[i]) * (128 ** i)
        return z

    def seed(self, x=None):
        if x is None:
            x = int(time.time() * 1000)  # Current time in milliseconds

        y = 0
        z = 0

        def redo():
            nonlocal y, z # Add nonlocal declaration
            y = (self.hash(x) + z) % self.m
            z += 1

        redo() # Initial call to redo

        while y % self.p == 0 or y % self.q == 0 or y == 0 or y == 1:
            redo()

        self.s = y
        print(["int seed", self.s])
        for _ in range(10):
            self.next()

    def next(self):
        self.s = (self.s * self.s) % self.m
        return self.s / self.m

    def test(self, f=None):
        F = f or (lambda: self.next())
        t0 = int(time.time() * 1000)
        chart = [0] * 10
        for _ in range(10000000):
            chart[math.floor(F() * 10)] += 1
        print(chart)
        print("finished in " + str(int(time.time() * 1000) - t0))
        return chart

# Example usage (optional)
if __name__ == '__main__':
    prng_instance = Prng()
    prng_instance.seed()

    # Replace Math.random and Math.seed with PRNG instance
    # Math.random = lambda: prng_instance.next()
    # Math.seed = lambda x: prng_instance.seed(x)

    # parseArgs equivalent (simplified)
    # SEED = str(int(time.time() * 1000))
    # # Implement parseArgs if needed, or set SEED directly
    # prng_instance.seed(SEED)
    # print(prng_instance.seed)

    # Test the PRNG
    prng_instance.test()
