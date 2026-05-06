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

// Camera: world coordinate at top-left of map div
let camera = { x: 0, y: 0, zoom: 1 };

function withSession(url) {
    const sid = localStorage.getItem('session_id');
    if (!sid) return url;
    const sep = url.includes('?') ? '&' : '?';
    return `${url}${sep}session_id=${encodeURIComponent(sid)}`;
}

let fogOpacity = 1.0;
let terrainImage = null;
let worldMap = null;
let isDragging = false;
let dragStartX, dragStartY, startOffsetX, startOffsetY;
window.currentPartyId = null;  // Will be set when player joins/creates party
window.currentLocationId = null;  // Will be set from world state

function getMapDivRect() {
    return document.getElementById('world-map').getBoundingClientRect();
}

function worldToScreen(worldX, worldY) {
    const rect = getMapDivRect();
    const screenX = rect.left + (worldX - camera.x) * camera.zoom;
    const screenY = rect.top + (worldY - camera.y) * camera.zoom;
    return { screenX, screenY };
}

function screenToWorld(screenX, screenY) {
    const rect = getMapDivRect();
    const worldX = camera.x + (screenX - rect.left) / camera.zoom;
    const worldY = camera.y + (screenY - rect.top) / camera.zoom;
    return { worldX, worldY };
}



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

function enterDungeon() {
    const partyId = window.currentPartyId;
    const locationId = window.worldState?.currentLocation?.id;
    if (!partyId || !locationId) {
        addWorldMessage("Cannot enter dungeon: missing party or location.");
        return;
    }
    // Navigate to dungeon server
    window.location.href = `http://localhost:5005/?party_id=${encodeURIComponent(partyId)}&location_id=${encodeURIComponent(locationId)}&world_url=${encodeURIComponent(window.location.origin)}`;
}

// ===== PARTY UI FUNCTIONS =====

function showCreatePartyModal() {
    const partyName = prompt("Enter party name:", "My Party");
    if (!partyName) return;
    
    fetch('/api/party/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name: partyName })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert("Failed to create party: " + (data.error || "Unknown error"));
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error creating party: " + err.message);
    });
}

function showJoinPartyModal() {
    const partyId = prompt("Enter party ID to join:");
    if (!partyId) return;
    console.log("partyId", partyId)
    
    fetch(withSession('/api/party/join', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ party_id: partyId })
    }))
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert("Failed to join party: " + (data.error || "Unknown error"));
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error joining party: " + err.message);
    });
}

function leaveParty() {
    if (!confirm("Are you sure you want to leave your current party?")) return;
    
    fetch(withSession('/api/party/leave', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    }))
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert("Failed to leave party: " + (data.error || "Unknown error"));
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error leaving party: " + err.message);
    });
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

function updateUIState() {
    const state = window.sessionState || {};

    const loggedIn = !!state.player_id;

    console.log("UI STATE:", { loggedIn });

    if (loggedIn) {
        closeModal();
    } else {
        openModal();
    }
}

document.addEventListener('DOMContentLoaded', function() {

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await fetch('/api/logout', { method: 'POST' });
            location.reload();
        });
    }
    
    // ===== World chat panel: send messages to AI DM =====

    const chatInput = document.getElementById('world-chat-input');
    const chatSend = document.getElementById('world-chat-send');
    if (chatInput && chatSend) {
        console.log("got here")
        const sendToAI = async () => {
            const message = chatInput.value.trim();
            console.log("sendToAI message:", message);
            if (!message) return;
            chatInput.value = '';
            addWorldMessage(`You: ${message}`); // display user message

            // Show loading indicator
            const loadingId = 'loading-' + Date.now();
            const loadingDiv = document.createElement('div');
            loadingDiv.id = loadingId;
            loadingDiv.textContent = 'DM is thinking...';
            loadingDiv.style.color = '#888';
            document.getElementById('world-chat-messages').appendChild(loadingDiv);

            try {
                console.log("Fetching /api/dm-response with message:", message);
                const response = await fetch(withSession('/api/dm-response'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                document.getElementById(loadingId)?.remove();

                if (!response.ok) {
                    addWorldMessage(`Error: ${response.status}`);
                    return;
                }

                const data = await response.json();

                // Display AI responses
                if (data.responses && Array.isArray(data.responses)) {
                    data.responses.forEach(r => {
                        addWorldMessage(`${r.speaker}: ${r.content}`);
                    });
                } else if (data.response) {
                    addWorldMessage(`DM: ${data.response}`);
                }

                // Update map if map_data is returned (from tool calls)
                if (data.map_data) {
                    worldState.worldMap = data.map_data;
                    worldMap = worldState.worldMap;
                    redraw();
                    if (data.action === 'centerOnParty') centerOnParty();
                }

                // Refresh other UI components (inventory, party, etc.)
                if (typeof refreshWorldState === 'function') {
                    refreshWorldState();
                }

            } catch (err) {
                document.getElementById(loadingId)?.remove();
                addWorldMessage(`Network error: ${err.message}`);
                console.error(err);
            }
        };

        chatSend.addEventListener('click', sendToAI);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendToAI();
        });
    }

    // ===== SocketIO for real‑time updates =====
    const sessionId = getCookie("session_id");

    const socket = io({
        auth: {
            session_id: sessionId
        }
    });

    socket.on("player_selected", (data) => {
        console.log("PLAYER SELECTED:", data);

        // update local state immediately
        window.sessionState = {
            ...(window.sessionState || {}),
            player_id: data.player_id
        };

        closeModal();
        updateUIState();
    });

    socket.on("connected", (data) => {
        console.log("CONNECTED STATE:", data);

        // CRITICAL: persist state
        window.sessionState = data;

        if (data.player_id) {
            closeModal();
        } else {
            openModal(); // or whatever shows it
        }

        updateUIState();
    });

    socket.on('party_update', () => {
        htmx.ajax('GET', '/api/party/list-html', { target: '#party-list-container', swap: 'innerHTML' });
    });

    socket.on('party_moved', (data) => {
        console.log('party_moved received', data);
        console.log('window.currentPartyId:', window.currentPartyId);
        if (data.party_id === window.currentPartyId) {
            console.log('Updating party position to', data.col, data.row);
            if (data.map_data) {
                worldState.worldMap = data.map_data;
                worldMap = worldState.worldMap;
            } else if (worldMap) {
                worldMap.party_position = { col: data.col, row: data.row };
                console.log('worldMap.party_position updated:', worldMap.party_position);
            } else {
                console.log('worldMap not defined');
            }
            redraw();
            centerOnParty();
        } else {
            console.log('Party ID mismatch');
        }
    });

    // ===== Map initialization (original code) =====
    if (typeof loadWorldDataWithRetry === 'function') {
        loadWorldDataWithRetry();
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
    size = size * 1.165
    let hexScale = 0.86; // local scaling – does not affect global zoom
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
    ctx.lineWidth = .1;
    ctx.stroke();
}

function hexagonPath(ctx, cx, cy, size) {
    // flat‑top hexagon keep in sync with drawHexagon as far as values goes
    size = size * 1.165;
    let hexScale = 0.86;
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

function redraw() {
    const canvas = document.getElementById('terrain-canvas');
    if (!canvas || !worldMap) return;

    const rect = getMapDivRect();
    const viewportWidth = rect.width;
    const viewportHeight = rect.height;

    // Resize canvas to match map div size
    if (canvas.width !== viewportWidth || canvas.height !== viewportHeight) {
        canvas.width = viewportWidth;
        canvas.height = viewportHeight;
    }

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, viewportWidth, viewportHeight);
    ctx.save();

    // Apply transform: world → screen
    // screenX = (worldX - camera.x) * camera.zoom + rect.left
    // But we want the canvas origin (0,0) to be the top-left of the map div,
    // so we set transform to map world coordinates to canvas pixels.
    // Canvas pixel (0,0) corresponds to world (camera.x, camera.y).
    // So: canvasX = (worldX - camera.x) * camera.zoom
    // canvasY = (worldY - camera.y) * camera.zoom
    ctx.setTransform(camera.zoom, 0, 0, camera.zoom, -camera.x * camera.zoom, -camera.y * camera.zoom);

    // Fill background (world coordinates)
    ctx.fillStyle = '#0a1729';
    ctx.fillRect(0, 0, worldMap.width, worldMap.height);

    // Draw terrain image inside discovered hexes (clipping)
    if (terrainImage && worldMap.discovered_hexes && worldMap.hexes) {
        const discoveredSet = new Set(worldMap.discovered_hexes.map(h => `${h.col},${h.row}`));
        const drawAll = (fogOpacity === 0);
        for (const hex of worldMap.hexes) {
            if (!drawAll && !discoveredSet.has(`${hex.grid_x},${hex.grid_y}`)) continue;
            ctx.save();
            hexagonPath(ctx, hex.x, hex.y, 30);
            drawHexagon(ctx, hex.x, hex.y, 30, "#000000");
            ctx.clip();
            ctx.drawImage(terrainImage, 0, 0);
            ctx.restore();
        }
    }

    // Draw paths and locations (only discovered)
    const discoveredLocations = (worldMap.locations || []).filter(loc => loc.discovered);
    drawPaths(ctx, worldMap.connections || [], discoveredLocations);
    drawLocations(ctx, discoveredLocations, camera.zoom);

    // Draw party location
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

function getHexWorldCoords(gx, gy) {
    // Purpose: Converts hex grid coordinates (gx, gy) to world pixel coordinates
    // Used by: centerOnParty() and any function that needs to center on a specific hex.

    const hex = worldMap.hexes.find(h => h.grid_x === gx && h.grid_y === gy);
    return hex ? { x: hex.x, y: hex.y } : null;
}

function centerOnWorld(worldX, worldY) {
    // Purpose: Pans the camera so that the given world point (worldX, worldY) is exactly at the center of the map div.
    // Used by: centerOnParty() and any other centering logic.

    const rect = getMapDivRect();
    const viewportCenterX = rect.width / 2;
    const viewportCenterY = rect.height / 2;
    camera.x = worldX - viewportCenterX / camera.zoom;
    camera.y = worldY - viewportCenterY / camera.zoom;
    redraw();
}

function centerOnWindowCenter(worldX, worldY) {
    const winCenterX = window.innerWidth / 2;
    const winCenterY = window.innerHeight / 2;
    camera.x = worldX - winCenterX / camera.zoom;
    camera.y = worldY - winCenterY / camera.zoom;
    redraw();
}

function centerOnParty() {
    // Purpose: Finds the party’s current hex grid coordinates (from worldMap.party_position), converts them to world coordinates, and calls centerOnWorld() to center the map on the party.
    // Used by: setInitialView() (after a hard reload) and optionally by AI commands or UI buttons.
    if (!worldMap.party_position) {
        console.warn('Party position not found');
        return;
    }
    const { col, row } = worldMap.party_position;
    const coords = getHexWorldCoords(col, row);
    if (coords) {
        centerOnWindowCenter(coords.x, coords.y);
    } else {
        console.warn(`Hex (${col},${row}) not found`);
    }
}

function setInitialView() {
    if (!worldMap) return;

    const rect = getMapDivRect();
    const viewportWidth = rect.width;
    const viewportHeight = rect.height;
    const worldWidth = worldMap.width;
    const worldHeight = worldMap.height;

    // Zoom to fit the whole world inside the viewport
    const zoomX = viewportWidth / worldWidth;
    const zoomY = viewportHeight / worldHeight;
    // didn't like either of these, so scaled it up 8 times
    //const newZoom = Math.min(zoomX, zoomY);
    //const newZoom = viewportWidth / worldWidth
    const newZoom = viewportWidth / worldWidth * 8;
    camera.zoom = newZoom;

    // If party exists, center on party; otherwise center on world center
    if (worldMap.party_position && worldMap.party_position.col !== undefined) {
        centerOnParty();
    } else {
        const worldCenterX = worldWidth / 2;
        const worldCenterY = worldHeight / 2;
        camera.x = worldCenterX - (viewportWidth / 2) / newZoom;
        camera.y = worldCenterY - (viewportHeight / 2) / newZoom;
    }
    redraw();
}

function onWheel(e) {
    e.preventDefault();
    const zoomFactor = 1.1;
    const oldZoom = camera.zoom;
    let newZoom = oldZoom;
    if (e.deltaY < 0) newZoom *= zoomFactor;
    else newZoom /= zoomFactor;
    newZoom = Math.max(0.1, Math.min(3, newZoom));
    if (newZoom === oldZoom) return;

    const rect = getMapDivRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;
    const worldX = camera.x + canvasX / oldZoom;
    const worldY = camera.y + canvasY / oldZoom;

    camera.zoom = newZoom;
    camera.x = worldX - canvasX / newZoom;  // factor = 1.0
    camera.y = worldY - canvasY / newZoom;
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
    if (isDragging) return;
    const canvas = document.getElementById('terrain-canvas');
    if (!canvas || !worldMap) return;
    const { worldX, worldY } = screenToWorld(e.clientX, e.clientY);
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
    startCameraX = camera.x;
    startCameraY = camera.y;
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
    camera.x = startCameraX - dx / camera.zoom;
    camera.y = startCameraY - dy / camera.zoom;
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
    console.log("sendWorldCommand called with:", command);
    try {
        const response = await fetch(withSession('/api/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: command})
        }));
        const data = await response.json();
        if (data.map_data) {
            worldState.worldMap = data.map_data;
            worldMap = worldState.worldMap;
            if (data.location_data) {
                worldState.currentLocation = data.location_data;
            }
            redraw();
            if (data.action === 'centerOnParty') {
                centerOnParty();
            }
        }
        // Handle encounter if present
        if (data.encounter) {
            addWorldMessage(`⚠️ Encounter: ${data.encounter.description}`);
            // Ask AI DM to narrate the encounter
            fetch(withSession('/api/dm-response'), {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    message: `We encountered: ${data.encounter.description}. What happens?`,
                    encounter: data.encounter 
                })
            })
            .then(r => r.json())
            .then(dmData => {
                if (dmData.responses) {
                    dmData.responses.forEach(r => addWorldMessage(r.content));
                }
            })
            .catch(err => console.error('DM response error:', err));
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
        const response = await fetch(withSession('/api/world-state'));
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

        console.log("terrain_image_url from backend:", worldMap.terrain_image_url);
        if (worldMap.terrain_image_url) {
            const img = new Image();
            img.onload = () => {
                terrainImage = img;
                console.log("Terrain image loaded successfully");
                redraw();
            };
            img.onerror = (err) => {
                console.error("Failed to load terrain image:", worldMap.terrain_image_url, err);
            };
            img.src = worldMap.terrain_image_url;
        } else {
            console.warn("No terrain_image_url in worldMap");
        }

        setInitialView();
        await loadActiveCharacter();

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
        const response = await fetch(withSession('/api/world-state'));
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
            console.error("just before redraw...............................")
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
    // window.loadWorldDataWithRetry = loadWorldDataWithRetry;

    // loadWorldDataWithRetry();
});

// ===== GLOBAL EXPORTS =====
window.worldState = worldState;
window.debug = {
    getWorldState: () => worldState,
    redraw
};

console.log('world.js loaded successfully');