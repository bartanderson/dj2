// static/js/terrain-generator.js

// Import the seeded random number generator
// This is assumed to be available globally or imported elsewhere
// import 'https://cdn.jsdelivr.net/npm/seedrandom@3.0.5/seedrandom.min.js';

class PerlinNoise {
    constructor(seed) {
        this.p = new Array(512);
        const perm = this.generatePermutation(seed);
        for (let i = 0; i < 512; i++) {
            this.p[i] = perm[i % 256];
        }
    }
    generatePermutation(seed) {
        const rng = new Math.seedrandom(seed.toString());
        const p = new Array(256);
        for (let i = 0; i < 256; i++) {
            p[i] = i;
        }
        for (let i = 255; i >= 0; i--) {
            const j = Math.floor(rng() * (i + 1));
            const temp = p[i];
            p[i] = p[j];
            p[j] = temp;
        }
        return p;
    }
    noise(x, y, z) {
        const X = Math.floor(x) & 255;
        const Y = Math.floor(y) & 255;
        const Z = Math.floor(z) & 255;
        x -= Math.floor(x);
        y -= Math.floor(y);
        z -= Math.floor(z);
        const u = this.fade(x);
        const v = this.fade(y);
        const w = this.fade(z);
        // Corrected index lookups with bitwise AND operator
        const A = (this.p[X] + Y) & 255;
        const AA = (this.p[A] + Z) & 255;
        const AB = (this.p[A + 1] + Z) & 255;
        const B = (this.p[X + 1] + Y) & 255;
        const BA = (this.p[B] + Z) & 255;
        const BB = (this.p[B + 1] + Z) & 255;

        return this.lerp(w, this.lerp(v, this.lerp(u, this.grad(this.p[AA], x, y, z), this.grad(this.p[BA], x - 1, y, z)), this.lerp(u, this.grad(this.p[AB], x, y - 1, z), this.grad(this.p[BB], x - 1, y - 1, z))), this.lerp(v, this.lerp(u, this.grad(this.p[AA + 1], x, y, z - 1), this.grad(this.p[BA + 1], x - 1, y, z - 1)), this.lerp(u, this.grad(this.p[AB + 1], x, y - 1, z - 1), this.grad(this.p[BB + 1], x - 1, y - 1, z - 1))));
    }
    fade(t) { return t * t * t * (t * (t * 6 - 15) + 10); }
    lerp(t, a, b) { return a + t * (b - a); }
    grad(hash, x, y, z) {
            const h = hash & 15;
            const u = h < 8 ? x : y;
            const v = h < 4 ? y : (h === 12 || h === 14 ? x : z);
            return ((h & 1) === 0 ? u : -u) + ((h & 2) === 0 ? v : -v);
        }
}

class TerrainGenerator {
    constructor(seed, width, height) {
        this.seed = seed;
        this.width = width;
        this.height = height;
        console.log("this.seed")
        console.log(this.seed)
        this.rng = new Math.seedrandom(this.seed.toString());
        this.perlinNoise = new PerlinNoise(this.seed);
        this.terrainTypes = {
            "ocean": {"color": "#4d6fb8", "height_range": [-1, 0.45]},
            "coast": {"color": "#a2c4c9", "height_range": [0.45, 0.5]},
            "plains": {"color": "#689f38", "height_range": [0.5, 0.58]},
            "hills": {"color": "#8d9946", "height_range": [0.58, 0.65]},
            "mountains": {"color": "#8d99ae", "height_range": [0.65, 0.73]},
            "snowcaps": {"color": "#ffffff", "height_range": [0.73, 1]}
        };
    }
    
    generateHeightmap() {
        const generateStats = 0;
        const heightmap = new Array(this.height).fill(null).map(() => new Array(this.width).fill(0));
        const scale = 0.005;
        const octaves = 4;
        const persistence = 0.5;
        const lacunarity = 2;
        
        let maxNoise = 0;
        let amplitude = 1;
        for (let i = 0; i < octaves; i++) {
            maxNoise += amplitude;
            amplitude *= persistence;
        }

        if (generateStats) {
            // Add this section to calculate and log stats
            let rawNoiseValues = [];
            let totalNoise = 0;
            let minRawNoise = Infinity;
            let maxRawNoise = -Infinity;
        }

        
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                let noise = 0;
                amplitude = 1;
                let frequency = 1;
                for (let i = 0; i < octaves; i++) {
                    noise += this.perlinNoise.noise(x * scale * frequency, y * scale * frequency, this.seed) * amplitude;
                    amplitude *= persistence;
                    frequency *= lacunarity;
                }
                heightmap[y][x] = noise;
                if (generateStats) {
                    // Track min, max, and total
                    rawNoiseValues.push(noise);
                    totalNoise += noise;
                    if (noise < minRawNoise) minRawNoise = noise;
                    if (noise > maxRawNoise) maxRawNoise = noise;
                }
            }
        }

        if (generateStats) {
            // this along with the associated usages above generate data to allow determining the range of noise values to determine distribution within that range should something need to be changed
            console.log("--- Raw Noise Stats (Before Normalization) ---");
            console.log("Min Raw Noise:", minRawNoise);
            console.log("Max Raw Noise:", maxRawNoise);
            console.log("Average Raw Noise:", totalNoise / (this.width * this.height));
            console.log("--------------------------------------------");
        }
        
        // Normalize heightmap
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                heightmap[y][x] = (heightmap[y][x] + maxNoise) / (2 * maxNoise);
            }
        }
        return heightmap;
    }
    
    generateTerrain(heightmap) {
        const terrain = new Array(this.height).fill(null).map(() => new Array(this.width).fill(0));
        for (let y = 0; y < this.height; y++) {
            for (let x = 0; x < this.width; x++) {
                const height = heightmap[y][x];
                let terrainType = "ocean";
                if (height >= this.terrainTypes["snowcaps"].height_range[0]) {
                    terrainType = "snowcaps";
                } else if (height >= this.terrainTypes["mountains"].height_range[0]) {
                    terrainType = "mountains";
                } else if (height >= this.terrainTypes["hills"].height_range[0]) {
                    terrainType = "hills";
                } else if (height >= this.terrainTypes["plains"].height_range[0]) {
                    terrainType = "plains";
                } else if (height >= this.terrainTypes["coast"].height_range[0]) {
                    terrainType = "coast";
                }
                terrain[y][x] = this.terrainTypes[terrainType].color;
            }
        }
        return terrain;
    }

    renderTerrain(terrain, canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas with ID ${canvasId} not found.`);
            return;
        }

        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width;
        canvas.height = rect.height;
        
        const ctx = canvas.getContext('2d');
        const imageData = ctx.createImageData(canvas.width, canvas.height);
        const data = imageData.data;

        const scaleX = this.width / canvas.width;
        const scaleY = this.height / canvas.height;

        for (let y = 0; y < canvas.height; y++) {
            for (let x = 0; x < canvas.width; x++) {
                const originalX = Math.floor(x * scaleX);
                const originalY = Math.floor(y * scaleY);

                const hexColor = terrain[originalY][originalX];
                
                const r = parseInt(hexColor.substring(1, 3), 16);
                const g = parseInt(hexColor.substring(3, 5), 16);
                const b = parseInt(hexColor.substring(5, 7), 16);
                
                const index = (y * canvas.width + x) * 4;
                
                data[index] = r;
                data[index + 1] = g;
                data[index + 2] = b;
                data[index + 3] = 255;
            }
        }
        ctx.putImageData(imageData, 0, 0);
    }
}

class HexGridRenderer {
    constructor(width, height, hexSize = 20) {
        this.width = width;
        this.height = height;
        this.hexSize = hexSize;
    }

    renderGrid(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        
        const rect = canvas.getBoundingClientRect();
        const canvasWidth = rect.width;
        const canvasHeight = rect.height;

        const hexWidth = this.hexSize * 2;
        const hexHeight = Math.sqrt(3) / 2 * hexWidth;
        
        ctx.strokeStyle = "rgba(0, 0, 0, 0.3)";
        ctx.lineWidth = 1;
        
        const scaleX = canvasWidth / this.width;
        const scaleY = canvasHeight / this.height;

        for (let x = 0; x < this.width / (hexWidth * 0.75); x++) {
            for (let y = 0; y < this.height / hexHeight; y++) {
                const center_x = (x * hexWidth * 0.75 + this.hexSize) * scaleX;
                const center_y = (y * hexHeight + (x % 2) * hexHeight / 2 + hexHeight / 2) * scaleY;
                
                ctx.beginPath();
                for (let i = 0; i < 6; i++) {
                    const angle_deg = 60 * i;
                    const angle_rad = Math.PI / 180 * angle_deg;
                    const point_x = center_x + this.hexSize * scaleX * Math.cos(angle_rad);
                    const point_y = center_y + this.hexSize * scaleY * Math.sin(angle_rad);
                    if (i === 0) {
                        ctx.moveTo(point_x, point_y);
                    } else {
                        ctx.lineTo(point_x, point_y);
                    }
                }
                ctx.closePath();
                ctx.stroke();
            }
        }
    }
}