// static\js\world.js
// ===== CORE WORLD STATE =====
let worldState = {
    currentLocation: null,
    party: [],
    activeQuests: [],
    discoveredLocations: [],
    characters: {},
    parties: []
};
let terrainImage = null; // will hold the terrain as an Image or offscreen canvas
let fogOpacity = 1.0;
window.currentPartyId = null;  // Will be set when player joins/creates party
window.currentLocationId = null;  // Will be set from world state

// After worldState is loaded, set currentPartyId from player's party
if (worldState.parties && worldState.parties.length > 0) {
    // Find party that contains the active character
    const activeCharId = worldState.activeCharacterId;
    if (activeCharId) {
        const playerParty = worldState.parties.find(p => p.members.includes(activeCharId));
        if (playerParty) {
            window.currentPartyId = playerParty.id;
        }
    }
    // Fallback to first party
    if (!window.currentPartyId && worldState.parties[0]) {
        window.currentPartyId = worldState.parties[0].id;
    }
}

// ===== LOCATION PREVIEW =====
class LocationPreview {
    constructor() {
        this.element = null;
        this.isVisible = false;
        this.create();
    }
    
    create() {
        this.remove();
        this.element = document.createElement('div');
        this.element.id = 'location-preview';
        this.element.className = 'hidden';
        this.element.innerHTML = `
            <div class="preview-content">
                <h3 id="preview-name"></h3>
                <p id="preview-type"></p>
                <p id="preview-description"></p>
            </div>
        `;
        Object.assign(this.element.style, {
            position: 'fixed',
            background: 'rgba(0, 0, 0, 0.9)',
            color: 'white',
            padding: '15px',
            borderRadius: '8px',
            zIndex: '1000',
            maxWidth: '300px',
            boxShadow: '0 4px 8px rgba(0,0,0,0.5)',
            pointerEvents: 'none',
            display: 'none'
        });
        document.body.appendChild(this.element);
        return this;
    }
    
    show(location, x, y) {
        if (!this.element) this.create();
        const name = this.element.querySelector('#preview-name');
        const type = this.element.querySelector('#preview-type');
        const desc = this.element.querySelector('#preview-description');
        name.textContent = location.name;
        type.textContent = `Type: ${location.type}`;
        desc.textContent = location.description || 'No description available';
        const previewRect = this.element.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        let left = x + 20;
        let top = y - 20;
        if (left + previewRect.width > viewportWidth) {
            left = x - previewRect.width - 20;
        }
        if (top + previewRect.height > viewportHeight) {
            top = y - previewRect.height - 20;
        }
        this.element.style.left = `${left}px`;
        this.element.style.top = `${top}px`;
        this.element.style.display = 'block';
        this.isVisible = true;
    }
    
    hide() {
        if (this.element) {
            this.element.style.display = 'none';
            this.isVisible = false;
        }
    }
    
    remove() {
        const existing = document.getElementById('location-preview');
        if (existing) existing.remove();
        this.element = null;
        this.isVisible = false;
    }
}

const locationPreview = new LocationPreview();

async function loadActiveCharacter() {
    console.log("loadActiveCharacter: worldState.characters at start =", worldState.characters);
    try {
        const response = await fetch('/api/player/active-character');
        const data = await response.json();
        if (data.character_id) {
            worldState.activeCharacterId = data.character_id;
            // Now set currentPartyId from the character's party
            if (worldState.parties) {
                for (const party of worldState.parties) {
                    if (party.members.includes(data.character_id)) {
                        window.currentPartyId = party.id;
                        break;
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error loading active character:', error);
    }
}

function getCurrentPartyCharacters() {
    // Get the active party from world state
    const activeParty = worldState.parties.find(p => p.id === window.currentPartyId);
    if (!activeParty) return [];
    
    return activeParty.members.map(charId => {
        const char = worldState.characters[charId];
        if (!char) {
            console.log('charId not in worldState.characters')
            return null;
        }
        console.log("char id", char.id)
        console.log("char name", char.name)
        console.log("char race", char.race)
        console.log("char class", char.class)
        return {
            id: char.id,
            name: char.name,
            race: char.race,
            class: char.class,
            hp: char.hp,
            max_hp: char.max_hp,
            sp: char.sp,
            max_sp: char.max_sp,
            conditions: char.conditions || [],
            inventory: char.inventory || [],
            skills: char.skills || {},
            attributes: char.attributes || {}
        };
    }).filter(c => c !== null);
}

function addWorldChatMessage(text, sender = 'system') {
    const chatDiv = document.getElementById('world-chat-messages');
    if (!chatDiv) return;
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${sender}`;
    msgDiv.style.marginBottom = '5px';
    msgDiv.style.padding = '5px';
    msgDiv.style.borderRadius = '3px';
    msgDiv.style.backgroundColor = 
        sender === 'user' ? 'rgba(78, 204, 163, 0.2)' :
        sender === 'dm' ? 'rgba(15, 52, 96, 0.3)' :
        'rgba(0,0,0,0.3)';
    msgDiv.innerHTML = `<strong>${sender === 'user' ? 'You' : (sender === 'dm' ? 'DM' : 'System')}:</strong> ${text}`;
    chatDiv.appendChild(msgDiv);
    chatDiv.scrollTop = chatDiv.scrollHeight;
}

function addWorldMessage(text) {
    const chatDiv = document.getElementById('world-chat-messages');
    if (chatDiv) {
        const msgDiv = document.createElement('div');
        msgDiv.textContent = text;
        chatDiv.appendChild(msgDiv);
        chatDiv.scrollTop = chatDiv.scrollHeight;
    } else {
        console.log('World message:', text);
    }
}


// async function sendWorldCommand(command) {
//     try {
//         const response = await fetch('/api/command', {
//             method: 'POST',
//             headers: {'Content-Type': 'application/json'},
//             body: JSON.stringify({command: command})
//         });
//         const data = await response.json();
//         if (data.error) {
//             console.error('Command error:', data.error);
//             return;
//         }
//         if (data.map_data) {
//             worldState.worldMap = data.map_data;
//             worldMap = worldState.worldMap;
//             if (data.location_data) {
//                 worldState.currentLocation = data.location_data;
//             }
//             redraw();
//         }
//         if (data.response) {
//             console.error(data.response);
//             addWorldMessage(data.response); // send response to chat
//             // Append to your existing world chat panel
//             const chatDiv = document.getElementById('world-chat-messages');
//             if (chatDiv) {
//                 const msgDiv = document.createElement('div');
//                 msgDiv.textContent = data.response;
//                 chatDiv.appendChild(msgDiv);
//                 chatDiv.scrollTop = chatDiv.scrollHeight;
//             }

//         }
//     } catch (error) {
//         console.error('Command error:', error);
//     }
// }

document.getElementById('world-chat-messages').addEventListener('submit', function(e) {
    e.preventDefault();
    const input = document.getElementById('world-chat-input');
    const command = input.value.trim();
    if (command) {
        sendWorldCommand(command);
        input.value = '';
    }
})

// Wire up the chat input
document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById('world-chat-input');
    const sendBtn = document.getElementById('world-chat-send');
    if (input && sendBtn) {
        const send = () => {
            const cmd = input.value.trim();
            if (cmd) {
                sendWorldCommand(cmd);
                input.value = '';
            }
        };
        sendBtn.addEventListener('click', send);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') send();
        });
    }
});

// ===== MAP RENDERING HELPERS =====
function drawPaths(ctx, connections, locations) {
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    connections.forEach(conn => {
        const fromLoc = locations.find(loc => loc.id === conn.from_id);
        const toLoc = locations.find(loc => loc.id === conn.to_id);
        if (fromLoc && toLoc) {
            ctx.beginPath();
            ctx.moveTo(fromLoc.x, fromLoc.y);
            ctx.lineTo(toLoc.x, toLoc.y);
            ctx.stroke();
        }
    });
}

function drawLocations(ctx, locations, scale) {
    window.worldState.locations = [];
    const targetScreenRadius = 10; // desired size in screen pixels
    let worldRadius = targetScreenRadius / scale;
    // Clamp to reasonable world units (min 2, max 15)
    worldRadius = Math.max(2, Math.min(15, worldRadius));
    locations.forEach(loc => {
        ctx.fillStyle = 'red';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(loc.x, loc.y, worldRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        window.worldState.locations.push({
            x: loc.x,
            y: loc.y,
            radius: worldRadius,
            id: loc.id,
            data: loc
        });
    });
}

function drawHexagon(ctx, cx, cy, size, color) {
    // Flat‑top hexagons; adjust size if needed
    size = size * 1.17
    let hexScale = 0.83; // local scaling – does not affect global zoom
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        let angle = i * Math.PI / 3; // 0°,60°,120°,...
        let x = cx + size * hexScale * Math.cos(angle);
        let y = cy + size * Math.sin(angle);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 0.5;
    ctx.stroke();
}

function hexagonPath(ctx, cx, cy, size) {
    // flat‑top hexagon keep in sync with drawHexagon as far as values goes
    size = size * 1.17;
    let hexScale = 0.83;
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        let angle = i * Math.PI / 3; // 0°,60°,120°,...
        let x = cx + size * hexScale * Math.cos(angle);
        let y = cy + size * Math.sin(angle);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.closePath();
}

function getTargetHex(col, row, direction) {
    // Map movement direction to hex coordinates (flat‑top)
    const dirMap = {
        'n': [0, -1],
        'ne': [1, -1],
        'se': [1, 0],
        's': [0, 1],
        'sw': [-1, 1],
        'nw': [-1, 0]
    };
    // Handle east/west based on row parity
    if (direction === 'east') {
        direction = (row % 2 === 0) ? 'ne' : 'se';
    } else if (direction === 'west') {
        direction = (row % 2 === 0) ? 'nw' : 'sw';
    }
    const [dc, dr] = dirMap[direction] || [0, 0];
    return [col + dc, row + dr];
}

async function setHexTerrain(col, row, terrain) {
    try {
        await fetch('/api/set-hex-terrain', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({col, row, terrain})
        });
    } catch (e) {
        console.warn('Failed to set hex terrain:', e);
    }
}

function dilateMask(mask, radius = 1) {
    const rows = mask.length;
    const cols = mask[0].length;
    const dilated = Array(rows).fill().map(() => Array(cols).fill(false));
    for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
            if (mask[y][x]) {
                for (let dy = -radius; dy <= radius; dy++) {
                    for (let dx = -radius; dx <= radius; dx++) {
                        const ny = y + dy;
                        const nx = x + dx;
                        if (ny >= 0 && ny < rows && nx >= 0 && nx < cols) {
                            dilated[ny][nx] = true;
                        }
                    }
                }
            }
        }
    }
    return dilated;
}

const FOREST_COLOR = '#2c5e2e';

function generateTerrainImage() {
    if (!worldMap) return;

    const width = worldMap.width;
    const height = worldMap.height;
    const hexes = worldMap.hexes;
    const area = width * height;

    if (typeof TerrainGenerator === 'undefined') {
        console.warn('TerrainGenerator not available');
        return;
    }

    const seed = worldMap.seed || 42;
    const terrainGen = new TerrainGenerator(seed, width, height);
    const heightmap = terrainGen.generateHeightmap(); // no edge‑lowering

    // Moisture map (used for lakes)
    const moistureMap = generateMoistureMap(seed, width, height);

    // Terrain thresholds
    const thresholds = {
        low: 0.3,       // below this: lakes
        plains: 0.54,   // 0.3–0.54 is plains (but we override low to lake)
        forest: 0.65,   // 0.54–0.65 is forest
        hills: 0.73,    // 0.65–0.73 is hills
        mountains: 0.85, // 0.73–0.85 is mountains
        // above 0.85 is snowcaps
    };

    // ---- Step 1: Render base terrain to a temporary canvas ----
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const tempCtx = tempCanvas.getContext('2d');
    const tempId = 'temp-terrain-' + Date.now();
    tempCanvas.id = tempId;
    document.body.appendChild(tempCanvas);
    terrainGen.renderTerrain(terrainGen.generateTerrain(heightmap), tempId);

    // ---- Step 2: Build land mask and location set (used for lakes) ----
    const landMask = Array(height).fill().map(() => Array(width).fill(false));
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            if (heightmap[y][x] >= thresholds.coast) {
                landMask[y][x] = true;
            }
        }
    }

    const locHexSet = new Set();
    const locations = worldMap.locations || [];
    for (let loc of locations) {
        if (loc.col !== undefined && loc.row !== undefined) {
            locHexSet.add(`${loc.col},${loc.row}`);
        } else {
            // Fallback: find hex by pixel
            const locX = loc.x;
            const locY = loc.y;
            for (let hex of hexes) {
                if (Math.abs(hex.x - locX) < 30 && Math.abs(hex.y - locY) < 30) {
                    locHexSet.add(`${hex.grid_x},${hex.grid_y}`);
                    break;
                }
            }
        }
    }

    // ---- Step 3: removed lakes replaced oceans more or less

    // ---- Step 4: River generation (meandering, thin) ----
    const targetRiverCount = Math.floor(area / 8000); // fewer rivers
    let riverMask = Array(height).fill().map(() => Array(width).fill(false));
    const rngRiver = new Math.seedrandom(seed + 10000);

    // Start candidates: hills/mountains (but not snowcaps)
    let startCandidates = [];
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const h = heightmap[y][x];
            if (h >= thresholds.hills && h <= thresholds.mountains) {
                let isLocalMax = true;
                for (let dy = -1; dy <= 1 && isLocalMax; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        if (dx === 0 && dy === 0) continue;
                        const nx = x + dx, ny = y + dy;
                        if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                            if (heightmap[ny][nx] > h) {
                                isLocalMax = false;
                                break;
                            }
                        }
                    }
                }
                if (isLocalMax) startCandidates.push([x, y]);
            }
        }
    }
    if (startCandidates.length === 0) {
        // fallback: use all high-elevation cells
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                if (heightmap[y][x] >= thresholds.hills && heightmap[y][x] <= thresholds.mountains) {
                    startCandidates.push([x, y]);
                }
            }
        }
    }
    // Shuffle
    for (let i = startCandidates.length - 1; i > 0; i--) {
        const j = Math.floor(rngRiver() * (i + 1));
        [startCandidates[i], startCandidates[j]] = [startCandidates[j], startCandidates[i]];
    }

    for (let r = 0; r < targetRiverCount && r < startCandidates.length; r++) {
        let [x, y] = startCandidates[r];
        const visited = new Set();
        const path = [];
        let steps = 0;
        while (true) {
            if (y < 0 || y >= height || x < 0 || x >= width) break;
            const key = `${x},${y}`;
            if (visited.has(key)) break;
            visited.add(key);
            path.push([x, y]);

            const h = heightmap[y][x];
            if (h < thresholds.low ) break;

            // Collect lower neighbors
            const neighbors = [];
            for (let dy = -1; dy <= 1; dy++) {
                for (let dx = -1; dx <= 1; dx++) {
                    if (dx === 0 && dy === 0) continue;
                    const nx = x + dx;
                    const ny = y + dy;
                    if (nx >= 0 && nx < width && ny >= 0 && ny < height && !visited.has(`${nx},${ny}`)) {
                        const nh = heightmap[ny][nx];
                        if (nh < h) {
                            neighbors.push({ x: nx, y: ny, height: nh });
                        }
                    }
                }
            }
            if (neighbors.length === 0) break;

            // Weighted random selection
            let totalWeight = 0;
            const weights = neighbors.map(n => (h - n.height) + 0.1);
            weights.forEach(w => totalWeight += w);
            let rand = rngRiver() * totalWeight;
            let chosen = null;
            for (let i = 0; i < neighbors.length; i++) {
                if (rand < weights[i]) {
                    chosen = neighbors[i];
                    break;
                }
                rand -= weights[i];
            }
            if (!chosen) chosen = neighbors[0];
            [x, y] = [chosen.x, chosen.y];
            steps++;
            if (steps > 300) break;
        }
        for (let [px, py] of path) {
            if (py >= 0 && py < height && px >= 0 && px < width) {
                riverMask[py][px] = true;
            }
        }
    }
    // Draw rivers (thin, 1 pixel wide)
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            if (riverMask[y][x]) {
                tempCtx.fillStyle = '#4a90e2';
                tempCtx.fillRect(x, y, 1, 1);
            }
        }
    }

    // ---- Paint forest on canvas (based on height and moisture) ----
    const forestMinMoisture = 0.6;
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const h = heightmap[y][x];
            const m = moistureMap[y][x];
            if (h >= thresholds.plains && h <= thresholds.forest && m > forestMinMoisture) {
                if (!riverMask[y][x]) {
                    tempCtx.fillStyle = FOREST_COLOR;
                    tempCtx.fillRect(x, y, 1, 1);
                }
            }
        }
    }

    // ---- Step 5: Create final image (offscreen) ----
    const offscreen = document.createElement('canvas');
    offscreen.width = width;
    offscreen.height = height;
    const offCtx = offscreen.getContext('2d');
    offCtx.drawImage(tempCanvas, 0, 0);
    document.body.removeChild(tempCanvas);
    terrainImage = offscreen;

    // ---- Step 6: Build terrain grid by sampling the final image ----
    const terrainNamesGrid = [];
    const terrainColorsGrid = [];
    const imageData = offCtx.getImageData(0, 0, width, height);
    const data = imageData.data;

    const colorToTerrain = {
        '#a2c4c9': 'coast',
        '#689f38': 'plains',
        '#8d9946': 'hills',
        '#8d99ae': 'mountains',
        '#ffffff': 'snowcaps',
        '#4a90e2': 'river',
        '#3a80c2': 'lake',
        [FOREST_COLOR]: 'forest'
    };

    function rgbToHex(r, g, b) {
        return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    function getTerrainFromColor(r, g, b) {
        const hex = rgbToHex(r, g, b).toLowerCase();
        if (colorToTerrain[hex]) return colorToTerrain[hex];
        // fallback: find closest color
        let best = null;
        let bestDist = Infinity;
        for (const [color, terrain] of Object.entries(colorToTerrain)) {
            const cr = parseInt(color.slice(1,3), 16);
            const cg = parseInt(color.slice(3,5), 16);
            const cb = parseInt(color.slice(5,7), 16);
            const dist = (cr - r) ** 2 + (cg - g) ** 2 + (cb - b) ** 2;
            if (dist < bestDist) {
                bestDist = dist;
                best = terrain;
            }
        }
        return best || 'plains';
    }

    // Sample each hex center
    for (let i = 0; i < hexes.length; i++) {
        const hex = hexes[i];
        const x = Math.round(hex.x);
        const y = Math.round(hex.y);
        if (x >= 0 && x < width && y >= 0 && y < height) {
            const idx = (y * width + x) * 4;
            const r = data[idx];
            const g = data[idx+1];
            const b = data[idx+2];
            const terrain = getTerrainFromColor(r, g, b);
            const col = hex.grid_x;
            const row = hex.grid_y;
            if (!terrainNamesGrid[row]) terrainNamesGrid[row] = [];
            terrainNamesGrid[row][col] = terrain;
            if (!terrainColorsGrid[row]) terrainColorsGrid[row] = [];
            terrainColorsGrid[row][col] = `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`;
        }
    }

    // ---- Step 7: River and lake overrides (with coverage) ----
    function hexContainsMask(hex, mask, width, height) {
        const minX = Math.max(0, Math.floor(hex.x - 30));
        const maxX = Math.min(width - 1, Math.ceil(hex.x + 30));
        const minY = Math.max(0, Math.floor(hex.y - 30));
        const maxY = Math.min(height - 1, Math.ceil(hex.y + 30));
        for (let yy = minY; yy <= maxY; yy++) {
            for (let xx = minX; xx <= maxX; xx++) {
                if (mask[yy][xx]) return true;
            }
        }
        return false;
    }

    // River override (skip snowcaps)
    for (let row = 0; row < terrainNamesGrid.length; row++) {
        for (let col = 0; col < terrainNamesGrid[row].length; col++) {
            const hex = hexes.find(h => h.grid_x === col && h.grid_y === row);
            if (hex && hexContainsMask(hex, riverMask, width, height)) {
                if (terrainNamesGrid[row][col] !== 'snowcaps') {
                    terrainNamesGrid[row][col] = 'river';
                    terrainColorsGrid[row][col] = '#4a90e2';
                }
            }
        }
    }

    // ---- Mark low‑lying hexes as lakes ----
    const waterHeight = 0.3;
    for (let row = 0; row < terrainNamesGrid.length; row++) {
        for (let col = 0; col < terrainNamesGrid[row].length; col++) {
            const hex = hexes.find(h => h.grid_x === col && h.grid_y === row);
            if (!hex) continue;
            const x = Math.round(hex.x);
            const y = Math.round(hex.y);
            if (x >= 0 && x < width && y >= 0 && y < height) {
                const h = heightmap[y][x];
                if (h < waterHeight) {
                    terrainNamesGrid[row][col] = 'lake';
                    terrainColorsGrid[row][col] = '#3a80c2';
                }
            }
        }
    }

    // ---- Step 8: Ensure starting location is on land ----
    function getNeighborHex(col, row, dir) {
        const dirMap = {
            'n': [0, -1], 'ne': [1, -1], 'se': [1, 0],
            's': [0, 1], 'sw': [-1, 1], 'nw': [-1, 0]
        };
        const [dc, dr] = dirMap[dir];
        return [col + dc, row + dr];
    }

    if (worldMap.starting_location_id) {
        const startLoc = worldMap.locations.find(l => l.id === worldMap.starting_location_id);
        if (startLoc) {
            let startHex = null;
            if (startLoc.col !== undefined && startLoc.row !== undefined) {
                startHex = hexes.find(h => h.grid_x === startLoc.col && h.grid_y === startLoc.row);
            } else {
                for (let hex of hexes) {
                    if (Math.abs(hex.x - startLoc.x) < 30 && Math.abs(hex.y - startLoc.y) < 30) {
                        startHex = hex;
                        break;
                    }
                }
            }
            if (startHex) {
                const terrain = terrainNamesGrid[startHex.grid_y]?.[startHex.grid_x];
                if (terrain === 'coast' || terrain === 'lake' || terrain === 'river') {
                    const queue = [startHex];
                    const visited = new Set();
                    visited.add(`${startHex.grid_x},${startHex.grid_y}`);
                    let landHex = null;
                    while (queue.length > 0 && !landHex) {
                        const current = queue.shift();
                        const curTerrain = terrainNamesGrid[current.grid_y]?.[current.grid_x];
                        if (curTerrain && !['coast','lake','river'].includes(curTerrain)) {
                            landHex = current;
                            break;
                        }
                        const dirs = ['n','ne','se','s','sw','nw'];
                        for (let d of dirs) {
                            const [nc, nr] = getNeighborHex(current.grid_x, current.grid_y, d);
                            const nKey = `${nc},${nr}`;
                            if (visited.has(nKey)) continue;
                            const nHex = hexes.find(h => h.grid_x === nc && h.grid_y === nr);
                            if (nHex) {
                                visited.add(nKey);
                                queue.push(nHex);
                            }
                        }
                    }
                    if (landHex) {
                        startLoc.col = landHex.grid_x;
                        startLoc.row = landHex.grid_y;
                        startLoc.x = landHex.x;
                        startLoc.y = landHex.y;
                        worldMap.party_position = { col: landHex.grid_x, row: landHex.grid_y };
                        console.log(`Moved starting location from (${startHex.grid_x},${startHex.grid_y}) to (${landHex.grid_x},${landHex.grid_y})`);
                        fetch('/api/update-location', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                id: startLoc.id,
                                col: landHex.grid_x,
                                row: landHex.grid_y,
                                x: landHex.x,
                                y: landHex.y
                            })
                        }).catch(e => console.warn('Failed to update location on backend:', e));
                    } else {
                        console.warn('No land hex found near starting location!');
                    }
                }
            } else {
                console.warn('Starting location not found in any hex');
            }
        }
    }

    // ---- Step 9: Store final grids ----
    worldMap.terrain_grid = terrainNamesGrid;
    worldMap.terrain_colors_grid = terrainColorsGrid;

    // Debug: final terrain counts
    const finalCounts = {};
    for (let row = 0; row < terrainNamesGrid.length; row++) {
        if (!terrainNamesGrid[row]) continue;
        for (let col = 0; col < terrainNamesGrid[row].length; col++) {
            const t = terrainNamesGrid[row][col];
            finalCounts[t] = (finalCounts[t] || 0) + 1;
        }
    }
    console.log("Final terrain counts:", finalCounts);
}

// ----- Moisture map (using a separate Perlin noise) -----
function generateMoistureMap(seed, width, height) {
    const moistureGen = new TerrainGenerator(seed + 1000, width, height);
    const moistureHeightmap = moistureGen.generateHeightmap();
    // Normalize to [0,1] already done in generateHeightmap
    return moistureHeightmap;
}


// ===== MINIMAL MAP =====
let worldMap = null;
let offsetX = 0, offsetY = 0;   // pan offset (world units)
let scale = 1;                   // zoom factor
let isDragging = false;
let dragStartX, dragStartY, startOffsetX, startOffsetY;

// Redraw everything
function redraw() {
    const canvas = document.getElementById('terrain-canvas');
    if (!canvas || !worldMap) return;

    if (worldMap.width <= 0 || worldMap.height <= 0) {
        console.error('Invalid world dimensions, cannot generate terrain');
        return;
    }

    // Set canvas buffer to world dimensions (only once)
    if (canvas.width !== worldMap.width || canvas.height !== worldMap.height) {
        canvas.width = worldMap.width;
        canvas.height = worldMap.height;
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(-offsetX, -offsetY);
    ctx.scale(scale, scale);

    // 1. Draw terrain image (full world)
    if (terrainImage) {
        ctx.drawImage(terrainImage, 0, 0);
    } else {
        ctx.fillStyle = '#0a1729';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    // Debug: draw sampling dots with classification letter
    if (worldMap.terrain_colors_grid && worldMap.terrain_grid && worldMap.hexes) {
        worldMap.hexes.forEach(hex => {
            const col = hex.grid_x;
            const row = hex.grid_y;
            if (row >= 0 && row < worldMap.terrain_colors_grid.length &&
                col >= 0 && col < worldMap.terrain_colors_grid[row].length &&
                row < worldMap.terrain_grid.length &&
                col < worldMap.terrain_grid[row].length) {
                const color = worldMap.terrain_colors_grid[row][col];
                const terrain = worldMap.terrain_grid[row][col];
                const letter = terrain ? terrain.charAt(0).toUpperCase() : '?';
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(hex.x, hex.y, 5, 0, 2 * Math.PI);
                ctx.fill();
                ctx.strokeStyle = 'black';
                ctx.lineWidth = 1;
                ctx.stroke();
                // Draw letter
                ctx.fillStyle = 'white';
                ctx.shadowColor = 'black';
                ctx.shadowBlur = 2;
                ctx.font = 'bold 10px monospace';
                ctx.fillText(letter, hex.x - 3, hex.y + 4);
                ctx.shadowBlur = 0;
            }
        });
    }
    // Debug: draw sampling dots (in world coordinates)
    // if (worldMap.terrain_colors_grid && worldMap.hexes) {
    //     worldMap.hexes.forEach(hex => {
    //         const col = hex.grid_x;
    //         const row = hex.grid_y;
    //         if (row >= 0 && row < worldMap.terrain_colors_grid.length &&
    //             col >= 0 && col < worldMap.terrain_colors_grid[row].length) {
    //             const color = worldMap.terrain_colors_grid[row][col];
    //             ctx.fillStyle = color;
    //             ctx.beginPath();
    //             ctx.arc(hex.x, hex.y, 5, 0, 2 * Math.PI);
    //             ctx.fill();
    //             ctx.strokeStyle = 'black';
    //             ctx.lineWidth = 1;
    //             ctx.stroke();
    //         }
    //     });
    // }

    // 2. Dark overlay (fog) over everything
    ctx.fillStyle = `rgba(0, 0, 0, ${fogOpacity})`;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 3. For discovered hexes, redraw terrain image inside the hex (reveals it)
    if (terrainImage && worldMap.discovered_hexes && worldMap.hexes) {
        const discoveredSet = new Set(worldMap.discovered_hexes.map(h => `${h.col},${h.row}`));
        // console.log('discovered set size:', discoveredSet.size);
        // console.log('hex count:', worldMap.hexes.length);
        worldMap.hexes.forEach(hex => {
            if (!discoveredSet.has(`${hex.grid_x},${hex.grid_y}`)) return;
            ctx.save();
            hexagonPath(ctx, hex.x, hex.y, 30);
            ctx.clip();
            ctx.drawImage(terrainImage, 0, 0);
            ctx.restore();
        });
    }

    // 4. Draw hex outlines for discovered hexes (optional)
    if (worldMap.hexes) {
        ctx.strokeStyle = 'rgba(0,0,0,0.3)';
        ctx.lineWidth = 1;
        const discoveredSet = new Set(worldMap.discovered_hexes?.map(h => `${h.col},${h.row}`) || []);
        worldMap.hexes.forEach(hex => {
            if (!discoveredSet.has(`${hex.grid_x},${hex.grid_y}`)) return;
            drawHexagon(ctx, hex.x, hex.y, 30, ctx.strokeStyle);
        });
    }

    // 5. Draw paths and locations (only discovered ones)
    const discoveredLocations = (worldMap.locations || []).filter(loc => loc.discovered);
    drawPaths(ctx, worldMap.connections || [], discoveredLocations);
    drawLocations(ctx, discoveredLocations, scale);

    // 6. Draw party location
    if (worldMap.party_position) {
        const partyHex = worldMap.hexes.find(h => h.grid_x === worldMap.party_position.col && h.grid_y === worldMap.party_position.row);
        if (partyHex) {
            ctx.fillStyle = 'white';
            ctx.beginPath();
            ctx.arc(partyHex.x, partyHex.y, 8, 0, 2 * Math.PI);
            ctx.fill();
            ctx.fillStyle = worldMap.party_color || '#FFD700';
            ctx.beginPath();
            ctx.arc(partyHex.x, partyHex.y, 4, 0, 2 * Math.PI);
            ctx.fill();
        }
    }

    ctx.restore();
}

// Initial view centered on start location
function setInitialView() {
    if (!worldMap) return;
    const startLoc = window.worldState?.currentLocation; // use the full object, not worldMap.currentLocation
    if (startLoc && typeof startLoc.x === 'number' && typeof startLoc.y === 'number') {
        offsetX = startLoc.x - window.innerWidth / (2 * scale);
        offsetY = startLoc.y - window.innerHeight / (2 * scale);
    } else {
        offsetX = (worldMap.width - window.innerWidth / scale) / 2;
        offsetY = (worldMap.height - window.innerHeight / scale) / 2;
    }
    redraw();
}

// ===== EVENT HANDLERS =====
function onWheel(e) {
    e.preventDefault();
    const zoomFactor = 1.1;
    const mouseWorldX = offsetX + e.clientX / scale;
    const mouseWorldY = offsetY + e.clientY / scale;
    if (e.deltaY < 0) scale *= zoomFactor;
    else scale /= zoomFactor;
    scale = Math.max(0.5, Math.min(3, scale));
    offsetX = mouseWorldX - e.clientX / scale;
    offsetY = mouseWorldY - e.clientY / scale;
    redraw();
}

function onDoubleClick(e) {
    if (!worldMap || !window.worldState?.currentLocation) return;
    const loc = window.worldState.currentLocation;
    offsetX = loc.x - window.innerWidth / (2 * scale);
    offsetY = loc.y - window.innerHeight / (2 * scale);
    redraw();
}

function onMouseMove(e) {
    if (isDragging) return; // don't interfere while dragging
    const canvas = document.getElementById('terrain-canvas');
    if (!canvas || !worldMap) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const worldX = offsetX + mouseX / scale;
    const worldY = offsetY + mouseY / scale;
    if (window.worldState.locations) {
        const hovered = window.worldState.locations.find(loc => {
            const dist = Math.sqrt((worldX - loc.x) ** 2 + (worldY - loc.y) ** 2);
            return dist <= loc.radius;
        });
        if (hovered) {
            canvas.style.cursor = 'pointer';
            locationPreview.show(hovered.data, e.clientX, e.clientY);
        } else {
            canvas.style.cursor = 'grab';
            locationPreview.hide();
        }
    }
}

function onPointerDown(e) {
    if (e.button !== 0) return; // primary button only
    isDragging = true;
    // Store screen start and current offsets
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    startOffsetX = offsetX;
    startOffsetY = offsetY;
    const canvas = document.getElementById('terrain-canvas');
    canvas.style.cursor = 'grabbing';
    canvas.setPointerCapture(e.pointerId);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerup', onPointerUp);
    canvas.addEventListener('pointercancel', onPointerUp);
    e.preventDefault();
}

function onPointerMove(e) {
    if (!isDragging) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    offsetX = startOffsetX - dx;
    offsetY = startOffsetY - dy; 
    redraw();
    e.preventDefault();
}

function onPointerUp(e) {
    if (!isDragging) return;
    isDragging = false;
    const canvas = document.getElementById('terrain-canvas');
    canvas.style.cursor = 'grab';
    canvas.releasePointerCapture(e.pointerId);
    canvas.removeEventListener('pointermove', onPointerMove);
    canvas.removeEventListener('pointerup', onPointerUp);
    canvas.removeEventListener('pointercancel', onPointerUp);
    e.preventDefault();
}

// ===== TRAVEL FUNCTIONS =====
async function travelToLocation(locationId) {
    try {
        const response = await fetch(`/api/travel/${locationId}`, { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            worldState.currentLocation = data.location;
            if (typeof showNotification === 'function') {
                showNotification(`Traveled to ${data.location.name}`, 'success');
            }
            refreshWorldState();
        } else {
            if (typeof showNotification === 'function') {
                showNotification('Failed to travel to location', 'error');
            }
        }
    } catch (error) {
        console.error('Error traveling:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error traveling to location', 'error');
        }
    }
}

async function sendWorldCommand(command) {
    // First, parse the command to see if it's a movement direction
    let dir = command.toLowerCase().trim();
    if (dir.startsWith('go ')) dir = dir.slice(3);
    const directionMap = {
        'n': 'n', 'north': 'n',
        'ne': 'ne', 'northeast': 'ne',
        'se': 'se', 'southeast': 'se',
        's': 's', 'south': 's',
        'sw': 'sw', 'southwest': 'sw',
        'nw': 'nw', 'northwest': 'nw',
        'e': 'east', 'east': 'east',
        'w': 'west', 'west': 'west'
    };
    const direction = directionMap[dir];
    if (!direction) {
        // Not a movement command – send as regular command (chat, etc.)
        try {
            const response = await fetch('/api/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: command})
            });
            const data = await response.json();
            if (data.map_data) {
                worldState.worldMap = data.map_data;
                worldMap = worldState.worldMap;
                generateTerrainImage();  // refresh terrain grid (though it won't change)
                if (data.location_data) {
                    worldState.currentLocation = data.location_data;
                }
                redraw();
            }
            if (data.response) {
                addWorldMessage(data.response);
            }
        } catch (error) {
            console.error('Command error:', error);
        }
        return;
    }

    // Movement command – check passability first
    if (!worldMap.party_position) {
        console.warn('No party position');
        return;
    }
    const {col, row} = worldMap.party_position;
    const [tcol, trow] = getTargetHex(col, row, direction);
    // Check bounds
    if (tcol < 0 || tcol >= worldMap.width || trow < 0 || trow >= worldMap.height) {
        addWorldMessage("You can't go that way (edge of the world).");
        return;
    }
    // Get terrain from the stored grid
    const terrain = worldMap.terrain_grid[trow][tcol];
    const blockedTerrains = ['ocean', 'lake', 'river'];
    if (blockedTerrains.includes(terrain)) {
        addWorldMessage(`The ${terrain} blocks your path.`);
        return;
    }

    // Send movement command with terrain
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: command, target_terrain: terrain})
        });
        const data = await response.json();
        if (data.map_data) {
            worldState.worldMap = data.map_data;
            worldMap = worldState.worldMap;
            generateTerrainImage();  // refresh terrain grid (though it won't change)
            if (data.location_data) {
                worldState.currentLocation = data.location_data;
            }
            redraw();
        }
        if (data.response) {
            addWorldMessage(data.response);
        }
    } catch (error) {
        console.error('Command error:', error);
    }
}

// ===== WORLD DATA LOADING =====
async function loadWorldData() {
    try {
        const response = await fetch('/api/world-state');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        if (!data.worldMap || data.worldMap.error) {
            console.error('World map data not available:', data.worldMap?.error);
            if (typeof showNotification === 'function') {
                showNotification('World data not available yet. Please try again.', 'error');
            }
            return;
        }
        console.log('discovered_hexes:', data.worldMap.discovered_hexes);
        console.log('first hex:', data.worldMap.hexes[0]);
        let currentLocation = null;
        if (data.currentLocation && data.worldMap.locations) {
            // If it's an ID string, find the location in the array
            if (typeof data.currentLocation === 'string') {
                currentLocation = data.worldMap.locations.find(loc => loc.id === data.currentLocation);
            } 
            // If it's an object with an id, find matching location (or use it directly if it has x,y)
            else if (data.currentLocation.id) {
                currentLocation = data.worldMap.locations.find(loc => loc.id === data.currentLocation.id);
                // If not found, fallback to the object itself (maybe it already has x,y)
                if (!currentLocation && data.currentLocation.x) {
                    currentLocation = data.currentLocation;
                }
            }
            // If it's already a full location object with x,y, use it directly
            else if (data.currentLocation.x) {
                currentLocation = data.currentLocation;
            }
        }
        // If we still don't have a valid location, set to null
        worldState.currentLocation = currentLocation;
        worldState = {
            worldMap: data.worldMap,
            currentLocation: currentLocation,
            locations: data.worldMap.locations || [],
            parties: data.parties || [],
            characters: data.characters || {}
        };
        console.log("loadWorldData: worldState.characters after assignment =", worldState.characters);
        window.worldState = worldState;
        worldMap = worldState.worldMap;
        setInitialView();
        generateTerrainImage()
        await loadActiveCharacter();
        // After terrain grid is generated, set starting hex terrain in backend
        if (worldMap.party_position && worldMap.terrain_grid) {
            const {col, row} = worldMap.party_position;
            const terrain = worldMap.terrain_grid[row][col];
            setHexTerrain(col, row, terrain);
        }
    } catch (error) {
        console.error('Error loading world data:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error loading world data.', 'error');
        }
    }
}

async function waitForServerReady(maxRetries = 30, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            if (data.status === 'ready') {
                console.log('Server ready');
                return true;
            }
        } catch (e) { /* ignore */ }
        console.log(`Waiting for server... (${i+1}/${maxRetries})`);
        await new Promise(r => setTimeout(r, delay));
    }
    return false;
}

async function loadWorldDataWithRetry(maxRetries = 3, delay = 1000) {
    if (typeof showLoading === 'function') showLoading(true);
    const ready = await waitForServerReady();
    if (!ready) {
        if (typeof showNotification === 'function') {
            showNotification('Server not ready. Please refresh.', 'error');
        }
        if (typeof showLoading === 'function') showLoading(false);
        return;
    }
    for (let i = 0; i < maxRetries; i++) {
        try {
            await loadWorldData();
            if (worldState && worldState.worldMap && worldState.worldMap.locations) {
                if (typeof showLoading === 'function') showLoading(false);
                return;
            }
        } catch (e) { console.error(e); }
        await new Promise(r => setTimeout(r, delay));
        delay *= 2;
    }
    if (typeof showNotification === 'function') {
        showNotification('Failed to load world data.', 'error');
    }
    if (typeof showLoading === 'function') showLoading(false);
}

// ===== REFRESH =====
async function refreshWorldState() {
    if (document.body && document.body.getAttribute('data-mode') !== 'world') {
        console.log('Skipping refresh – not in world mode');
        return;
    }
    try {
        const response = await fetch('/api/world-state');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        worldState.worldMap = data.worldMap;
        worldState.parties = data.parties || [];
        worldState.characters = data.characters || {};
        if (data.currentLocation) {
            worldState.currentLocation = data.currentLocation;
        }
        window.worldState = worldState;
        if (worldMap) redraw();
    } catch (error) {
        console.error('Error refreshing world state:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error refreshing world data.', 'error');
        }
    }
}

// ===== COMPATIBILITY =====
if (typeof DMChat === 'undefined') {
    window.DMChat = class {
        constructor() { console.log('DMChat placeholder'); }
        sendMessage() {}
        receiveMessage() {}
    };
}
window.showNotification = window.showNotification || function(m,t) { console.log(`[${t}] ${m}`); };
window.showLoading = window.showLoading || function(s) { console.log('Loading:', s); };
window.showPanel = window.showPanel || function(panelId) {
    console.log('showPanel', panelId);
    if (panelId === 'travel-panel' && window.openModal) {
        window.openModal('travel-modal', 'travel-btn');
        if (window.populateTravelModal) window.populateTravelModal();
    } else if (panelId === 'status-panel' && window.openModal) {
        window.openModal('status-modal', 'status-btn');
        if (window.updateStatusContent) window.updateStatusContent();
    } else if (panelId === 'chat-panel' && window.openModal) {
        window.openModal('chat-modal', 'chat-btn');
    } else {
        const tab = document.querySelector(`[data-tab="${panelId.replace('-panel','-tab')}"]`);
        if (tab) tab.click();
    }
};
window.populateTravelPanel = function() {
    if (window.populateTravelModal) window.populateTravelModal();
};
window.updateStatusPanel = function() {
    if (window.updateStatusContent) window.updateStatusContent();
};

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    try {
        window.dmChat = typeof DMChat !== 'undefined' ? new DMChat() : { sendMessage(){}, receiveMessage(){} };
    } catch (e) {
        console.warn('DMChat init failed', e);
        window.dmChat = { sendMessage(){}, receiveMessage(){} };
    }

    const fogCheckbox = document.getElementById('toggle-fog');
    if (fogCheckbox) {
        fogCheckbox.addEventListener('change', function(e) {
            // Set fogOpacity to 0 if checked, 1 if unchecked (or vice versa)
            fogOpacity = e.target.checked ? 0 : 1;
            redraw();
        });
    }

    const canvas = document.getElementById('terrain-canvas');
    if (canvas) {
        canvas.style.cursor = 'grab';
        canvas.addEventListener('pointerdown', onPointerDown);
        canvas.addEventListener('wheel', onWheel);
        canvas.addEventListener('dblclick', onDoubleClick);
        canvas.addEventListener('dragstart', (e) => e.preventDefault()); // prevent native drag
    }

    window.travelToLocation = travelToLocation;
    window.redraw = redraw;
    window.loadWorldDataWithRetry = loadWorldDataWithRetry;

    loadWorldDataWithRetry();
});

// ===== GLOBAL EXPORTS =====
window.worldState = worldState;
window.debug = {
    getWorldState: () => worldState,
    redraw
};

console.log('world.js loaded successfully');