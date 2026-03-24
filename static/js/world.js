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

async function sendWorldCommand(command) {
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: command})
        });
        const data = await response.json();
        if (data.error) {
            console.error('Command error:', data.error);
            return;
        }
        if (data.map_data) {
            worldState.worldMap = data.map_data;
            worldMap = worldState.worldMap;
            if (data.location_data) {
                worldState.currentLocation = data.location_data;
            }
            redraw();
        }
        if (data.response) {
            console.error(data.response);
            addWorldMessage(data.response); // send response to chat
            // Append to your existing world chat panel
            const chatDiv = document.getElementById('world-chat-messages');
            if (chatDiv) {
                const msgDiv = document.createElement('div');
                msgDiv.textContent = data.response;
                chatDiv.appendChild(msgDiv);
                chatDiv.scrollTop = chatDiv.scrollHeight;
            }

        }
    } catch (error) {
        console.error('Command error:', error);
    }
}

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

function generateTerrainImage() {
    if (!worldMap) return;

    const width = worldMap.width;
    const height = worldMap.height;

    if (typeof TerrainGenerator === 'undefined') {
        console.warn('TerrainGenerator not available');
        return;
    }

    const terrainGen = new TerrainGenerator(worldMap.seed || 42, width, height);
    const heightmap = terrainGen.generateHeightmap();

    // Generate color grid and terrain grid
    const terrainColorsGrid = [];
    const terrainNamesGrid = [];
    const colorMap = {
        'ocean': '#4d6fb8',
        'coast': '#a2c4c9',
        'plains': '#689f38',
        'hills': '#8d9946',
        'mountains': '#8d99ae',
        'snowcaps': '#ffffff'
    };

    for (let y = 0; y < height; y++) {
        terrainColorsGrid[y] = [];
        terrainNamesGrid[y] = [];
        for (let x = 0; x < width; x++) {
            const h = heightmap[y][x];
            let terrain;
            if (h >= 0.73) terrain = 'snowcaps';
            else if (h >= 0.65) terrain = 'mountains';
            else if (h >= 0.58) terrain = 'hills';
            else if (h >= 0.5) terrain = 'plains';
            else if (h >= 0.45) terrain = 'coast';
            else terrain = 'ocean';
            terrainNamesGrid[y][x] = terrain;
            terrainColorsGrid[y][x] = colorMap[terrain];
        }
    }

    // Render the image
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = width;
    tempCanvas.height = height;
    const ctx = tempCanvas.getContext('2d');
    const imgData = ctx.createImageData(width, height);
    const data = imgData.data;
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const color = terrainColorsGrid[y][x];
            const r = parseInt(color.substring(1,3), 16);
            const g = parseInt(color.substring(3,5), 16);
            const b = parseInt(color.substring(5,7), 16);
            const idx = (y * width + x) * 4;
            data[idx] = r;
            data[idx+1] = g;
            data[idx+2] = b;
            data[idx+3] = 255;
        }
    }
    ctx.putImageData(imgData, 0, 0);
    const offscreen = document.createElement('canvas');
    offscreen.width = width;
    offscreen.height = height;
    const offCtx = offscreen.getContext('2d');
    offCtx.drawImage(tempCanvas, 0, 0);
    terrainImage = offscreen;

    // Store terrain grid in worldMap
    worldMap.terrain_grid = terrainNamesGrid;
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

    // 2. Dark overlay (fog) over everything
    ctx.fillStyle = 'rgba(0, 0, 0, 1.0)'; // made fully opaque now
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 3. For discovered hexes, redraw terrain image inside the hex (reveals it)
    if (terrainImage && worldMap.discovered_hexes && worldMap.hexes) {
        const discoveredSet = new Set(worldMap.discovered_hexes.map(h => `${h.col},${h.row}`));
        console.log('discovered set size:', discoveredSet.size);
        console.log('hex count:', worldMap.hexes.length);
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
    console.log(`Target hex (${tcol},${trow}) terrain: ${terrain}`);
    const blockedTerrains = ['ocean'];   // add 'river' if needed
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
        window.worldState = worldState;
        worldMap = worldState.worldMap;
        setInitialView();
        generateTerrainImage()
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