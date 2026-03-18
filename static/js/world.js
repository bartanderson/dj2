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
    const screenRadius = 15; // screen pixels – adjust to taste
    const worldRadius = screenRadius / scale;
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
        let angle = i * Math.PI / 3; // pointy‑top (0°,60°,...)
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

    // Validate world dimensions
    if (!worldMap.width || !worldMap.height || worldMap.width <= 0 || worldMap.height <= 0) {
        console.warn('Invalid world dimensions, skipping redraw');
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

    // Terrain (if TerrainGenerator exists)
    if (typeof TerrainGenerator !== 'undefined') {
        try {
            const terrainGen = new TerrainGenerator(worldMap.seed || 42, worldMap.width, worldMap.height);
            const heightmap = terrainGen.generateHeightmap();
            const terrain = terrainGen.generateTerrain(heightmap);
            window.worldState.terrain = terrain;
            terrainGen.renderTerrain(terrain, 'terrain-canvas');
        } catch (e) {
            console.error('Terrain rendering failed, drawing fallback grid', e);
            drawFallbackGrid(ctx);
        }
    } else {
        drawFallbackGrid(ctx);
    }

    // Hex outlines (if available)
    if (worldMap.hexes && worldMap.hexes.length > 0) {
        ctx.strokeStyle = 'rgba(0,0,0,0.3)';
        ctx.lineWidth = 1;
        worldMap.hexes.forEach(hex => {
            drawHexagon(ctx, hex.x, hex.y, 30, ctx.strokeStyle);
        });
    }

    // Only draw discovered locations
    const discoveredLocations = (worldMap.locations || []).filter(loc => loc.discovered);
    drawPaths(ctx, worldMap.connections || [], discoveredLocations);
    drawLocations(ctx, discoveredLocations, scale);

    ctx.restore();
}

function drawFallbackGrid(ctx) {
    ctx.strokeStyle = '#1a2530';
    ctx.lineWidth = 1;
    const gridSize = 50;
    for (let x = 0; x < worldMap.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, worldMap.height);
        ctx.stroke();
    }
    for (let y = 0; y < worldMap.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(worldMap.width, y);
        ctx.stroke();
    }
}

// Pan limits (world units)
function clampOffsets() {
    const visibleWorldWidth = window.innerWidth / scale;
    const visibleWorldHeight = window.innerHeight / scale;
    const minX = 0;
    const maxX = Math.max(0, worldMap.width - visibleWorldWidth);
    const minY = 0;
    const maxY = Math.max(0, worldMap.height - visibleWorldHeight);
    offsetX = Math.max(minX, Math.min(maxX, offsetX));
    offsetY = Math.max(minY, Math.min(maxY, offsetY));
}

// Initial view centered on start location
function setInitialView() {
    if (!worldMap) return;
    const startLoc = worldMap.currentLocation;
    if (startLoc) {
        offsetX = startLoc.x - window.innerWidth / (2 * scale);
        offsetY = startLoc.y - window.innerHeight / (2 * scale);
    } else {
        offsetX = (worldMap.width - window.innerWidth / scale) / 2;
        offsetY = (worldMap.height - window.innerHeight / scale) / 2;
    }
    clampOffsets();
    redraw();
}

// ===== EVENT HANDLERS =====
function startDrag(e) {
    if (e.button !== 0) return;
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    startOffsetX = offsetX;
    startOffsetY = offsetY;
    document.getElementById('terrain-canvas').style.cursor = 'grabbing';
    e.preventDefault();
}

function whileDrag(e) {
    if (!isDragging) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    offsetX = startOffsetX - dx / scale;
    offsetY = startOffsetY - dy / scale;
    clampOffsets();
    redraw();
    e.preventDefault();
}

function stopDrag() {
    isDragging = false;
    document.getElementById('terrain-canvas').style.cursor = 'grab';
}

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
    clampOffsets();
    redraw();
}

function onDoubleClick(e) {
    if (!worldMap || !worldMap.currentLocation) return;
    const loc = worldMap.currentLocation;
    offsetX = loc.x - window.innerWidth / (2 * scale);
    offsetY = loc.y - window.innerHeight / (2 * scale);
    clampOffsets();
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
        let currentLocation = null;
        if (data.currentLocation && data.currentLocation.id && data.worldMap.locations) {
            currentLocation = data.worldMap.locations.find(loc => loc.id === data.currentLocation.id);
        }
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
        console.log('World data loaded:', worldState);
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
        console.log('World state refreshed');
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
    console.log('world.js initialized');

    try {
        window.dmChat = typeof DMChat !== 'undefined' ? new DMChat() : { sendMessage(){}, receiveMessage(){} };
    } catch (e) {
        console.warn('DMChat init failed', e);
        window.dmChat = { sendMessage(){}, receiveMessage(){} };
    }

    const canvas = document.getElementById('terrain-canvas');
    if (canvas) {
        canvas.style.cursor = 'grab';
        canvas.addEventListener('mousedown', startDrag);
        canvas.addEventListener('mousemove', onMouseMove);
        canvas.addEventListener('mousemove', whileDrag);
        canvas.addEventListener('mouseup', stopDrag);
        canvas.addEventListener('mouseleave', stopDrag);
        canvas.addEventListener('wheel', onWheel);
        canvas.addEventListener('dblclick', onDoubleClick);
    }

    // Remove any old button listeners if present (optional)
    // ...

    window.travelToLocation = travelToLocation;
    window.redraw = redraw;
    window.loadWorldDataWithRetry = loadWorldDataWithRetry;

    loadWorldDataWithRetry();

    setInterval(() => {
        if (worldMap) redraw();
    }, 30000);
});

// ===== GLOBAL EXPORTS =====
window.worldState = worldState;
window.debug = {
    getWorldState: () => worldState,
    redraw
};

console.log('world.js loaded successfully');