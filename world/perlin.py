import math
import random

class PerlinNoise:
    def __init__(self, seed=0):
        self.p = [0] * 512
        perm = [i for i in range(256)]
        rng = random.Random(seed)
        for i in range(255, -1, -1):
            j = rng.randint(0, i)
            perm[i], perm[j] = perm[j], perm[i]
        for i in range(512):
            self.p[i] = perm[i % 256]

    def fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def lerp(self, t, a, b):
        return a + t * (b - a)

    def grad(self, hash, x, y, z):
        h = hash & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h in (12, 14) else z)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise(self, x, y, z=0):
        xi = math.floor(x) & 255
        yi = math.floor(y) & 255
        zi = math.floor(z) & 255
        x -= math.floor(x)
        y -= math.floor(y)
        z -= math.floor(z)
        u = self.fade(x)
        v = self.fade(y)
        w = self.fade(z)

        aaa = self.p[self.p[self.p[xi] + yi] + zi]
        aba = self.p[self.p[self.p[xi] + yi + 1] + zi]
        aab = self.p[self.p[self.p[xi] + yi] + zi + 1]
        abb = self.p[self.p[self.p[xi] + yi + 1] + zi + 1]
        baa = self.p[self.p[self.p[xi + 1] + yi] + zi]
        bba = self.p[self.p[self.p[xi + 1] + yi + 1] + zi]
        bab = self.p[self.p[self.p[xi + 1] + yi] + zi + 1]
        bbb = self.p[self.p[self.p[xi + 1] + yi + 1] + zi + 1]

        x1 = self.lerp(u, self.grad(aaa, x, y, z), self.grad(baa, x - 1, y, z))
        x2 = self.lerp(u, self.grad(aba, x, y - 1, z), self.grad(bba, x - 1, y - 1, z))
        y1 = self.lerp(v, x1, x2)

        x3 = self.lerp(u, self.grad(aab, x, y, z - 1), self.grad(bab, x - 1, y, z - 1))
        x4 = self.lerp(u, self.grad(abb, x, y - 1, z - 1), self.grad(bbb, x - 1, y - 1, z - 1))
        y2 = self.lerp(v, x3, x4)

        return self.lerp(w, y1, y2)