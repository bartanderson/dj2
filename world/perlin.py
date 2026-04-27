import math
import random

# ============================================================================
# Perlin Noise – exact port of the JS version from your tuner
# ============================================================================
class PerlinNoise:
    def __init__(self, seed):
        self.p = [0] * 512
        perm = self._generate_permutation(seed)
        for i in range(512):
            self.p[i] = perm[i % 256]

    def _generate_permutation(self, seed):
        rng = random.Random(seed)
        p = list(range(256))
        for i in range(255, -1, -1):
            j = rng.randint(0, i)
            p[i], p[j] = p[j], p[i]
        return p

    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, t, a, b):
        return a + t * (b - a)

    def _grad(self, hash_val, x, y, z):
        h = hash_val & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h == 12 or h == 14 else z)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise(self, x, y, z=0):
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        Z = int(math.floor(z)) & 255
        x -= math.floor(x)
        y -= math.floor(y)
        z -= math.floor(z)
        u = self._fade(x)
        v = self._fade(y)
        w = self._fade(z)

        A = (self.p[X] + Y) & 255
        AA = (self.p[A] + Z) & 255
        AB = (self.p[A + 1] + Z) & 255
        B = (self.p[X + 1] + Y) & 255
        BA = (self.p[B] + Z) & 255
        BB = (self.p[B + 1] + Z) & 255

        return self._lerp(w,
            self._lerp(v, self._lerp(u, self._grad(self.p[AA], x, y, z), self._grad(self.p[BA], x - 1, y, z)),
                          self._lerp(u, self._grad(self.p[AB], x, y - 1, z), self._grad(self.p[BB], x - 1, y - 1, z))),
            self._lerp(v, self._lerp(u, self._grad(self.p[AA + 1], x, y, z - 1), self._grad(self.p[BA + 1], x - 1, y, z - 1)),
                          self._lerp(u, self._grad(self.p[AB + 1], x, y - 1, z - 1), self._grad(self.p[BB + 1], x - 1, y - 1, z - 1))))