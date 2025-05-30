import math
import random
from lib.rng import Prng

class PerlinNoise:
    PERLIN_YWRAPB = 4
    PERLIN_YWRAP = 1 << PERLIN_YWRAPB
    PERLIN_ZWRAPB = 8
    PERLIN_ZWRAP = 1 << PERLIN_ZWRAPB
    PERLIN_SIZE = 4095

    def __init__(self, prng_instance=None):
        self.perlin_octaves = 4
        self.perlin_amp_falloff = 0.5
        self.perlin = None
        # Use the provided Prng instance or create a new one
        self.prng = prng_instance if prng_instance else Prng()
        # Seed the Prng instance if it's newly created
        if not prng_instance:
            self.prng.seed()


    def scaled_cosine(self, i):
        return 0.5 * (1.0 - math.cos(i * math.pi))

    def noise(self, x, y=0, z=0):
        if self.perlin is None:
            self.perlin = [0.0] * (self.PERLIN_SIZE + 1) # Initialize with floats
            for i in range(self.PERLIN_SIZE + 1):
                self.perlin[i] = self.prng.next() # Use Prng instance's next()

        if x < 0:
            x = -x
        if y < 0:
            y = -y
        if z < 0:
            z = -z

        xi = math.floor(x)
        yi = math.floor(y)
        zi = math.floor(z)
        xf = x - xi
        yf = y - yi
        zf = z - zi

        r = 0
        ampl = 0.5

        for o in range(self.perlin_octaves):
            of = xi + (yi << self.PERLIN_YWRAPB) + (zi << self.PERLIN_ZWRAPB)
            rxf = self.scaled_cosine(xf)
            ryf = self.scaled_cosine(yf)

            n1 = self.perlin[of & self.PERLIN_SIZE]
            n1 += rxf * (self.perlin[(of + 1) & self.PERLIN_SIZE] - n1)
            n2 = self.perlin[(of + self.PERLIN_YWRAP) & self.PERLIN_SIZE]
            n2 += rxf * (self.perlin[(of + self.PERLIN_YWRAP + 1) & self.PERLIN_SIZE] - n2)
            n1 += ryf * (n2 - n1)

            of += self.PERLIN_ZWRAP
            n2 = self.perlin[of & self.PERLIN_SIZE]
            n2 += rxf * (self.perlin[(of + 1) & self.PERLIN_SIZE] - n2)
            n3 = self.perlin[(of + self.PERLIN_YWRAP) & self.PERLIN_SIZE]
            n3 += rxf * (self.perlin[(of + self.PERLIN_YWRAP + 1) & self.PERLIN_SIZE] - n3)
            n2 += ryf * (n3 - n2)

            n1 += self.scaled_cosine(zf) * (n2 - n1)
            r += n1 * ampl
            ampl *= self.perlin_amp_falloff
            xi <<= 1
            xf *= 2
            yi <<= 1
            yf *= 2
            zi <<= 1
            zf *= 2

            if xf >= 1.0:
                xi += 1
                xf -= 1
            if yf >= 1.0:
                yi += 1
                yf -= 1
            if zf >= 1.0:
                zi += 1
                zf -= 1
        return r

    def noise_detail(self, lod, falloff):
        if lod > 0:
            self.perlin_octaves = lod
        if falloff > 0:
            self.perlin_amp_falloff = falloff

    def noise_seed(self, seed_val):
        # LCG class definition (as nested or helper class if preferred)
        class LCG:
            def __init__(self):
                self.m = 4294967296
                self.a = 1664525
                self.c = 1013904223
                self.seed_val = None
                self.z = None

            def set_seed(self, val):
                # Use Prng's next() for default seed if val is None
                self.z = self.seed_val = (val if val is not None else self.prng.next() * self.m) % self.m


            def get_seed(self):
                return self.seed_val

            def rand(self):
                self.z = (self.a * self.z + self.c) % self.m
                return self.z / self.m

        lcg = LCG()
        lcg.prng = self.prng # Pass prng to LCG instance
        lcg.set_seed(seed_val)
        self.perlin = [0.0] * (self.PERLIN_SIZE + 1) # Initialize with floats
        for i in range(self.PERLIN_SIZE + 1):
            self.perlin[i] = lcg.rand()

# Example Usage (Optional)
if __name__ == '__main__':
    # Create a Prng instance
    prng_for_perlin = Prng()
    prng_for_perlin.seed(123)  # Seed it with a specific value

    # Pass the Prng instance to PerlinNoise
    noise_gen = PerlinNoise(prng_instance=prng_for_perlin)

    # Test noise generation
    print(noise_gen.noise(0.1, 0.2, 0.3))

    # Test noise detail
    noise_gen.noise_detail(8, 0.65)
    print(noise_gen.noise(0.1, 0.2, 0.3))

    # Test noise seed
    noise_gen.noise_seed(456)
    print(noise_gen.noise(0.1, 0.2, 0.3))
