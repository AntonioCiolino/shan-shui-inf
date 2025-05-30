import math
import random
from lib.rng import Prng

class PerlinNoise:
    PERLIN_YWRAPB = 4
    PERLIN_YWRAP = 1 << PERLIN_YWRAPB
    PERLIN_ZWRAPB = 8
    PERLIN_ZWRAP = 1 << PERLIN_ZWRAPB
    PERLIN_SIZE = 4095

    def __init__(self, seed=None): # Modified constructor
        self.perlin_octaves = 4
        self.perlin_amp_falloff = 0.5

        self.prng = Prng()
        self.prng.seed(seed) # Seed the internal Prng instance

        # Initialize self.perlin array directly in constructor
        self.perlin = [0.0] * (self.PERLIN_SIZE + 1)
        for i in range(self.PERLIN_SIZE + 1):
            self.perlin[i] = self.prng.next()

    def scaled_cosine(self, i):
        return 0.5 * (1.0 - math.cos(i * math.pi))

    def noise(self, x, y=0, z=0):
        # self.perlin is now guaranteed to be initialized by the constructor
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

    # noise_seed method is removed. Seeding is handled at construction.

# Example Usage (Optional)
if __name__ == '__main__':
    # PerlinNoise is now seeded directly at construction
    noise_gen_seeded = PerlinNoise(seed=123)

    # Test noise generation
    print(noise_gen_seeded.noise(0.1, 0.2, 0.3))

    # Test noise detail
    noise_gen_seeded.noise_detail(8, 0.65)
    print(noise_gen_seeded.noise(0.1, 0.2, 0.3))

    # To re-seed, create a new instance
    noise_gen_reseeded = PerlinNoise(seed=456)
    print(noise_gen_reseeded.noise(0.1, 0.2, 0.3))
