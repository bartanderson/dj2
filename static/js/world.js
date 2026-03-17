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

// ===== MAP STATE =====
let scale = 1;
let panX = 0;
let panY = 0;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let initialPanX = 0;
let initialPanY = 0;
const maxScale = 3;
const minScale = 0.5;

// ===== LOCATION PREVIEW =====
class LocationPreview {
    constructor() {
        this.element = null;
        this.isVisible = false;
        this.create();
    }
    
    create() {
        // Remove existing preview if it exists
        this.remove();
        
        // Create new preview element
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
        
        // Add styles
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

        // Position the preview, ensuring it stays within viewport
        const previewRect = this.element.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        let left = x + 20;
        let top = y - 20;
        
        // Adjust if preview would go off the right edge
        if (left + previewRect.width > viewportWidth) {
            left = x - previewRect.width - 20;
        }
        
        // Adjust if preview would go off the bottom edge
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
        if (existing) {
            existing.remove();
        }
        this.element = null;
        this.isVisible = false;
    }
}

// Create a singleton instance
const locationPreview = new LocationPreview();

// ===== MAP RENDERING FUNCTIONS =====

// Function to draw paths between locations
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

// Function to draw location markers
function drawLocations(ctx, locations, scale) {
    console.error('drawLocations called with', locations.length, 'locations');
    // Clear previous locations for hit detection
    window.worldState.locations = [];
    
    const screenRadius = 125; // desired size in screen pixels (adjust to taste)
    const worldRadius = screenRadius / scale; // convert to world units
    
    locations.forEach(loc => {
        ctx.fillStyle = 'red';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        
        ctx.beginPath();
        ctx.arc(loc.x, loc.y, worldRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        
        // Store for hit detection (use same worldRadius)
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
    size = size * 1.18; // in case we want to adjust width vs height
    hexScale = .83; // set to 1 for no scaling was .83; In case we want to scale later
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        let angle = i * Math.PI / 3; // pointy-top
        let x = cx + size * hexScale * Math.cos(angle);
        let y = cy + size * Math.sin(angle);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.stroke();
}

// The consolidated function to render all map elements
function renderWorldMap(worldMap) {
    const mycontainer = document.getElementById('world-map');
    const mycanvas = document.getElementById('terrain-canvas');
    // Add guard: if canvas has zero dimensions, skip rendering
    if (!mycanvas || mycanvas.width === 0 || mycanvas.height === 0) {
        console.log('Canvas has zero dimensions, skipping render');
        return;
    }
    console.log('DEBUG - Container dimensions:', mycontainer?.clientWidth, 'x', mycontainer?.clientHeight);
    console.log('DEBUG - Canvas dimensions:', mycanvas?.width, 'x', mycanvas?.height);
    console.log('Rendering world map...', worldMap);

    
    // Store world data for later use
    window.worldState = window.worldState || {};
    
    // Ensure we have a valid worldMap object
    if (!worldMap) {
        console.error('renderWorldMap: worldMap is undefined');
        if (typeof showNotification === 'function') {
            showNotification('Error rendering map: No map data available', 'error');
        }
        return;
    }
    
    window.worldState.worldMap = worldMap;

    // Get map container and canvas
    const container = document.getElementById('world-map');
    const terrainCanvas = document.getElementById('terrain-canvas');

    if (!container || !terrainCanvas) {
        console.error('Map container or canvas not found');
        return;
    }
    
    // Set canvas size to match container (fixes blurriness)
    terrainCanvas.width = worldMap.width; //container.clientWidth;
    terrainCanvas.height = worldMap.height; //container.clientHeight;

    console.log('mapInitialized:', window.mapInitialized);
    console.log('worldMap.width:', worldMap.width);

    // --- INITIAL VIEW SETUP (run only once) ---
    if (!window.mapInitialized) {
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const fitScale = Math.min(viewportWidth / worldMap.width, viewportHeight / worldMap.height);
        scale = fitScale * 3; // adjust multiplier as desired
        const startLoc = window.worldState?.currentLocation;
        if (startLoc && startLoc.x !== undefined && startLoc.y !== undefined) {
            panX = viewportWidth / 2 - startLoc.x * scale;
            panY = viewportHeight / 2 - startLoc.y * scale;
        } else {
            panX = (viewportWidth - worldMap.width * scale) / 2;
            panY = (viewportHeight - worldMap.height * scale) / 2;
        }
        console.error('startLoc:', startLoc);
        console.error('Computed panX:', panX, 'panY:', panY);
        window.initialScale = scale;
        window.initialPanX = panX;
        window.initialPanY = panY;
        window.mapInitialized = true;
        updateMapTransform();
        //clampPan();
        updateDebugOverlay();
    }
    // Get canvas context
    const ctx = terrainCanvas.getContext('2d');
    
    // Clear the canvas
    ctx.clearRect(0, 0, terrainCanvas.width, terrainCanvas.height);
    
    // Draw a dark background
    ctx.fillStyle = '#0a1729';
    ctx.fillRect(0, 0, terrainCanvas.width, terrainCanvas.height);
    
    // Ensure seed is defined with a fallback value
    const seed = worldMap.seed || 42;
    
    try {
        // Generate and render terrain if TerrainGenerator is available
        if (typeof TerrainGenerator !== 'undefined') {
            const terrainGen = new TerrainGenerator(seed, mycanvas.width, mycanvas.height); //container.clientWidth, container.clientHeight);
            const heightmap = terrainGen.generateHeightmap();
            const terrain = terrainGen.generateTerrain(heightmap);
            
            // Store terrain for future use
            window.worldState.terrain = terrain;
            
            // Render terrain
            terrainGen.renderTerrain(terrain, 'terrain-canvas');
            
            // Render hex grid if available
            if (typeof HexGridRenderer !== 'undefined') {
                // const gridRenderer = new HexGridRenderer(container.clientWidth, container.clientHeight);
                // gridRenderer.renderGrid('terrain-canvas');
            }
        } else {
            console.warn('TerrainGenerator not found - drawing basic grid');
            // Draw a simple grid as fallback
            ctx.strokeStyle = '#1a2530';
            ctx.lineWidth = 1;
            const gridSize = 50;
            
            // Vertical lines
            for (let x = 0; x < terrainCanvas.width; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, terrainCanvas.height);
                ctx.stroke();
            }
            
            // Horizontal lines
            for (let y = 0; y < terrainCanvas.height; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(terrainCanvas.width, y);
                ctx.stroke();
            }
        }
    } catch (error) {
        console.error('Error rendering terrain:', error);
        // Continue with basic rendering
    }

    // Filter locations and connections based on 'discovered'
    const discoveredLocations = worldMap.locations ? worldMap.locations.filter(loc => loc.discovered) : [];
    const discoveredConnections = worldMap.connections ? worldMap.connections.filter(conn =>
        discoveredLocations.some(loc => loc.id === conn.from_id) &&
        discoveredLocations.some(loc => loc.id === conn.to_id)
    ) : [];

    // Draw hex outlines
    if (worldMap.hexes && worldMap.hexes.length > 0) {
        ctx.strokeStyle = 'rgba(0,0,0,0.6)';
        ctx.lineWidth = 1;
        worldMap.hexes.forEach(hex => {
            drawHexagon(ctx, hex.x, hex.y, 30, ctx.strokeStyle);
        });
    }

    // ---- DEBUG: Draw world boundaries ----/////////////////////
    ctx.save();
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(worldMap.width, 0);
    ctx.lineTo(worldMap.width, worldMap.height);
    ctx.lineTo(0, worldMap.height);
    ctx.closePath();
    ctx.stroke();

    // Draw hex extent lines
    if (worldMap.hexes && worldMap.hexes.length > 0) {
        const xs = worldMap.hexes.map(h => h.x);
        const ys = worldMap.hexes.map(h => h.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);

        ctx.strokeStyle = 'cyan';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(minX, minY);
        ctx.lineTo(maxX, minY);
        ctx.lineTo(maxX, maxY);
        ctx.lineTo(minX, maxY);
        ctx.closePath();
        ctx.stroke();
    }

    // // Mark start location
    // const startLoc = window.worldState?.currentLocation;
    // if (startLoc) {
    //     ctx.fillStyle = 'lime';
    //     ctx.beginPath();
    //     ctx.arc(startLoc.x, startLoc.y, 15, 0, 2*Math.PI);
    //     ctx.fill();
    // }
    // ctx.restore();
    ////////////////////////////////////////////////////////////

    // Draw the paths for discovered connections
    drawPaths(ctx, discoveredConnections, worldMap.locations || []);

    console.error('discoveredLocations count:', discoveredLocations.length);
    if (discoveredLocations.length > 0) {
        console.error('first discovered location id:', discoveredLocations[0].id);
    }

    // Place the locations on top of the paths and terrain
    drawLocations(ctx, discoveredLocations, worldMap);
    
    // Apply initial transform
    updateMapTransform();
    
    // Set up canvas interactions
    setupCanvasInteractions();
    
    console.log('World map rendered successfully');
}

// ===== MAP CONTROLS =====
function updateMapTransform() {
    console.error('updateMapTransform: scale=', scale, 'pan=', panX, panY);
    if (panX === 0 && panY === 0 && scale === 0.6509316770186335) {
        console.trace('Pan reset to zero');
    }
    const terrainCanvas = document.getElementById('terrain-canvas');
    if (terrainCanvas) {
        const transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        terrainCanvas.style.transform = transform;
    }
}

function zoomIn() {
    if (scale < maxScale) {
        scale += 0.25;
        updateMapTransform();
        clampPan();
    }
}

function zoomOut() {
    if (scale > minScale) {
        scale -= 0.25;
        updateMapTransform();
        clampPan();
    }
}

function centerMap() {
    console.trace('centerMap called');
    scale = 1;
    panX = 0;
    panY = 0;
    updateMapTransform();
}

function resetMapView() {
    console.trace('resetMapView called');
    if (window.initialScale !== undefined) {
        scale = window.initialScale;
        panX = window.initialPanX;
        panY = window.initialPanY;
        updateMapTransform();
        clampPan();
        updateDebugOverlay();
    } else {
        centerMap();
    }
}

// ===== TRAVEL FUNCTIONS =====
async function travelToLocation(locationId) {
    try {
        const response = await fetch(`/api/travel/${locationId}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            worldState.currentLocation = data.location;
            
            // Update world map if provided
            if (data.worldMap) {
                worldState.worldMap = data.worldMap;
                if (typeof renderWorldMap === 'function') {
                    renderWorldMap(data.worldMap);
                }
            }
            
            // Show notification
            if (typeof showNotification === 'function') {
                showNotification(`Traveled to ${data.location.name}`, 'success');
            }
            
            // Update UI
            refreshWorldState();
        } else {
            if (typeof showNotification === 'function') {
                showNotification('Failed to travel to location', 'error');
            }
        }
    } catch (error) {
        console.error('Error traveling to location:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error traveling to location', 'error');
        }
    }
}

// ===== WORLD DATA FUNCTIONS =====
async function loadWorldData() {
    try {
        const response = await fetch('/api/world-state');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Handle case where worldMap might be undefined
        if (!data.worldMap || data.worldMap.error) {
            console.error('World map data not available:', data.worldMap?.error);
            if (typeof showNotification === 'function') {
                showNotification('World data not available yet. Please try again.', 'error');
            }
            return;
        }
        
        // Find current location by ID
        let currentLocation = null;
        if (data.currentLocation && data.currentLocation.id && data.worldMap.locations) {
            currentLocation = data.worldMap.locations.find(
                loc => loc.id === data.currentLocation.id
            );
        }
        
        // Store world data
        worldState = {
            worldMap: data.worldMap,
            currentLocation: currentLocation,
            locations: data.worldMap.locations || [],
            parties: data.parties || [],
            characters: data.characters || {}
        };
        
        // Update window state for UI
        window.worldState = worldState;
    
        // Render the map
        if (typeof renderWorldMap === 'function') {
            renderWorldMap(worldState.worldMap);
        }
        
        console.log('World data loaded:', worldState);
    } catch (error) {
        console.error('Error loading world data:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error loading world data.', 'error');
        }
    }
}

async function waitForServerReady(maxRetries = 30, delay = 1000) {
    let retries = 0;
    
    while (retries < maxRetries) {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            if (data.status === 'ready') {
                console.log('Server is ready');
                return true;
            }
            
            retries++;
            if (retries < maxRetries) {
                console.log(`Server not ready yet (${retries}/${maxRetries}). Retrying...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        } catch (error) {
            retries++;
            console.error(`Health check failed (attempt ${retries}/${maxRetries}):`, error);
            if (retries < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, delay));
            } else {
                console.error('Server health check failed after multiple attempts');
                return false;
            }
        }
    }
    return false;
}

async function loadWorldDataWithRetry(maxRetries = 3, delay = 1000) {
    if (typeof showLoading === 'function') {
        showLoading(true);
    }

    // First, wait for the server to be ready
    const serverReady = await waitForServerReady();
    if (!serverReady) {
        if (typeof showNotification === 'function') {
            showNotification('Server is taking too long to initialize. Please refresh the page.', 'error');
        }
        if (typeof showLoading === 'function') {
            showLoading(false);
        }
        return;
    }

    // Now try to load world data
    let retries = 0;

    while (retries < maxRetries) {
        try {
            await loadWorldData();

            // Check if we have valid data
            if (worldState && worldState.worldMap && worldState.worldMap.locations) {
                console.log('World data loaded successfully');
                if (typeof showLoading === 'function') {
                    showLoading(false);
                }
                return;
            }

            // If we don't have valid data, wait and retry
            retries++;
            if (retries < maxRetries) {
                console.log(`Retrying world data load (${retries}/${maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2; // Exponential backoff
            }
        } catch (error) {
            retries++;
            console.error(`Error loading world data (attempt ${retries}/${maxRetries}):`, error);
            if (retries < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, delay));
                delay *= 2; // Exponential backoff
            } else {
                if (typeof showNotification === 'function') {
                    showNotification('Failed to load world data after multiple attempts.', 'error');
                }
                if (typeof showLoading === 'function') {
                    showLoading(false);
                }
                return;
            }
        }
    }
}

// ===== REFRESH FUNCTION =====
async function refreshWorldState() {
    // same as for dungeon, but maybe this is more comprehensive?
    if (!document.getElementById('map-tab').classList.contains('active')) {
        console.log('Map tab not active, skipping render');
        return;
    }

    // FIX: Don't refresh world state when in dungeon mode
    if (document.body && document.body.getAttribute('data-mode') !== 'world') {
        console.log("Skipping world state refresh - in dungeon mode");
        return;
    }
    try {
        const response = await fetch('/api/world-state');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update world state
        worldState.worldMap = data.worldMap;
        worldState.parties = data.parties || [];
        worldState.characters = data.characters || {};
        
        if (data.currentLocation) {
            worldState.currentLocation = data.currentLocation;
        }
        
        // Update window state for UI
        window.worldState = worldState;
        
        // Update map if we have one
        if (data.worldMap && typeof renderWorldMap === 'function') {
            renderWorldMap(data.worldMap);
        }
        
        console.log('World state refreshed');
        
    } catch (error) {
        console.error('Error refreshing world state:', error);
        if (typeof showNotification === 'function') {
            showNotification('Error refreshing world data.', 'error');
        }
    }
}

// ===== MAP INTERACTION FUNCTIONS =====
function initPanFunctionality() {
    const terrainCanvas = document.getElementById('terrain-canvas');
    if (!terrainCanvas) return;
    
    terrainCanvas.addEventListener('mousedown', startDragging);
    terrainCanvas.addEventListener('mousemove', whileDragging);
    terrainCanvas.addEventListener('mouseup', stopDragging);
    terrainCanvas.addEventListener('mouseleave', stopDragging);
    
    // Touch events
    terrainCanvas.addEventListener('touchstart', handleTouchStart, { passive: false });
    terrainCanvas.addEventListener('touchmove', handleTouchMove, { passive: false });
    terrainCanvas.addEventListener('touchend', handleTouchEnd);
    
    terrainCanvas.addEventListener('contextmenu', (e) => e.preventDefault());
}

function clampPan() {
    const canvas = document.getElementById('terrain-canvas');
    if (!canvas || !window.worldState?.worldMap) return;
    const worldMap = window.worldState.worldMap;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const displayedWidth = worldMap.width * scale;
    const displayedHeight = worldMap.height * scale;
    
    // Restrict pan so the canvas always stays within the viewport
    const minPanX = Math.min(0, viewportWidth - displayedWidth);
    const maxPanX = 0;
    const minPanY = Math.min(0, viewportHeight - displayedHeight);
    const maxPanY = 0;
    
    panX = Math.max(minPanX, Math.min(maxPanX, panX));
    panY = Math.max(minPanY, Math.min(maxPanY, panY));
    updateMapTransform();
}

function startDragging(e) {
    if (e.button !== 0) return;
    
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    initialPanX = panX;
    initialPanY = panY;
    
    const terrainCanvas = document.getElementById('terrain-canvas');
    if (terrainCanvas) {
        terrainCanvas.style.cursor = 'grabbing';
    }
    
    e.preventDefault();
}

function whileDragging(e) {
    if (!isDragging) return;
    
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    
    panX = initialPanX + dx;
    panY = initialPanY + dy;
    
    updateMapTransform();
    clampPan();
    e.preventDefault();
}

function stopDragging() {
    isDragging = false;
    
    const terrainCanvas = document.getElementById('terrain-canvas');
    if (terrainCanvas) {
        terrainCanvas.style.cursor = 'grab';
    }
}

function handleTouchStart(e) {
    if (e.touches.length !== 1) return;
    
    const touch = e.touches[0];
    isDragging = true;
    dragStartX = touch.clientX;
    dragStartY = touch.clientY;
    initialPanX = panX;
    initialPanY = panY;
    
    e.preventDefault();
}

function handleTouchMove(e) {
    if (!isDragging || e.touches.length !== 1) return;
    
    const touch = e.touches[0];
    const dx = touch.clientX - dragStartX;
    const dy = touch.clientY - dragStartY;
    
    panX = initialPanX + dx;
    panY = initialPanY + dy;
    
    updateMapTransform();
    clampPan();
    e.preventDefault();
}

function handleTouchEnd() {
    isDragging = false;
}

function setupCanvasInteractions() {
    const terrainCanvas = document.getElementById('terrain-canvas');
    if (!terrainCanvas) return;
    
    // Use a debounce function to prevent excessive preview updates
    let lastHoverTime = 0;
    const hoverDebounce = 100; // ms
    
    terrainCanvas.addEventListener('mousemove', function(e) {
        const now = Date.now();
        if (now - lastHoverTime < hoverDebounce) return;
        lastHoverTime = now;
        
        const rect = terrainCanvas.getBoundingClientRect();
        const scaleX = terrainCanvas.width / rect.width;
        const scaleY = terrainCanvas.height / rect.height;
        
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;
        
        // Check if we're hovering over a location
        if (window.worldState && window.worldState.locations) {
            const hoveredLocation = window.worldState.locations.find(loc => {
                const distance = Math.sqrt(Math.pow(x - loc.x, 2) + Math.pow(y - loc.y, 2));
                return distance <= loc.radius;
            });
            
            if (hoveredLocation) {
                terrainCanvas.style.cursor = 'pointer';
                locationPreview.show(hoveredLocation.data, e.clientX, e.clientY);
            } else {
                terrainCanvas.style.cursor = 'grab';
                locationPreview.hide();
            }
        }
    });
    
    terrainCanvas.addEventListener('mouseleave', function() {
        locationPreview.hide();
    });
    
    terrainCanvas.addEventListener('click', function(e) {
        const rect = terrainCanvas.getBoundingClientRect();
        const scaleX = terrainCanvas.width / rect.width;
        const scaleY = terrainCanvas.height / rect.height;
        
        const x = (e.clientX - rect.left) * scaleX;
        const y = (e.clientY - rect.top) * scaleY;
        
        // Check if we're clicking on a location
        if (window.worldState && window.worldState.locations) {
            const clickedLocation = window.worldState.locations.find(loc => {
                const distance = Math.sqrt(Math.pow(x - loc.x, 2) + Math.pow(y - loc.y, 2));
                return distance <= loc.radius;
            });
            
            if (clickedLocation) {
                // Check if we're already at this location
                if (worldState.currentLocation && worldState.currentLocation.id === clickedLocation.data.id) {
                    if (typeof showNotification === 'function') {
                        showNotification(`You're already at ${clickedLocation.data.name}`, 'info');
                    }
                } else {
                    // Open travel modal with this location pre-selected
                    if (typeof window.openModal === 'function') {
                        window.openModal('travel-modal', 'travel-btn');
                        
                        // Highlight the clicked location in the travel modal
                        setTimeout(() => {
                            const travelLocations = document.getElementById('travel-locations');
                            if (travelLocations) {
                                const locationBtns = travelLocations.querySelectorAll('button');
                                locationBtns.forEach(btn => {
                                    if (btn.textContent.includes(clickedLocation.data.name)) {
                                        btn.style.background = '#40916c';
                                        btn.style.borderColor = '#fff';
                                    }
                                });
                            }
                        }, 100);
                        
                        if (typeof showNotification === 'function') {
                            showNotification(`Selected ${clickedLocation.data.name} for travel`, 'info');
                        }
                    }
                }
            }
        }
    });

    // Call this function to add the panning styles
    addPanningStyles();
}

function addPanningStyles() {
    // Already included in world.html CSS
}

// ===== COMPATIBILITY LAYER =====

// DMChat placeholder for compatibility
if (typeof DMChat === 'undefined') {
    window.DMChat = class {
        constructor() {
            console.log('DMChat placeholder loaded');
        }
        sendMessage() {
            console.log('DMChat.sendMessage called (placeholder)');
        }
        receiveMessage() {
            console.log('DMChat.receiveMessage called (placeholder)');
        }
    };
}

// Placeholder notification functions (overridden by world.html)
window.showNotification = window.showNotification || function(message, type = 'info') {
    console.log(`Notification [${type}]: ${message}`);
};

window.showLoading = window.showLoading || function(show) {
    console.log(`Loading: ${show}`);
};

// showPanel compatibility (redirects to new UI system)
window.showPanel = window.showPanel || function(panelId) {
    console.log(`showPanel called: ${panelId}`);
    
    if (panelId === 'travel-panel') {
        if (typeof window.openModal === 'function') {
            window.openModal('travel-modal', 'travel-btn');
            if (typeof populateTravelPanel === 'function') {
                populateTravelPanel();
            }
        }
    } else if (panelId === 'status-panel') {
        if (typeof window.openModal === 'function') {
            window.openModal('status-modal', 'status-btn');
            if (typeof updateStatusPanel === 'function') {
                updateStatusPanel();
            }
        }
    } else if (panelId === 'chat-panel') {
        if (typeof window.openModal === 'function') {
            window.openModal('chat-modal', 'chat-btn');
        }
    } else if (panelId === 'inventory-panel') {
        const inventoryTab = document.querySelector('[data-tab="inventory-tab"]');
        if (inventoryTab) inventoryTab.click();
    } else if (panelId === 'quests-panel') {
        const questsTab = document.querySelector('[data-tab="quests-tab"]');
        if (questsTab) questsTab.click();
    } else if (panelId === 'party-panel') {
        const partyTab = document.querySelector('[data-tab="party-tab"]');
        if (partyTab) partyTab.click();
    }
};

// UI compatibility functions
window.populateTravelPanel = function() {
    if (typeof window.populateTravelModal === 'function') {
        window.populateTravelModal();
    }
};

window.updateStatusPanel = function() {
    if (typeof window.updateStatusContent === 'function') {
        window.updateStatusContent();
    }
};

function updateDebugOverlay() {
    const overlay = document.getElementById('debug-overlay');
    if (!overlay) return;
    if (overlay.style.display === 'none') return; // only update if visible

    const canvas = document.getElementById('terrain-canvas');
    if (!canvas || !window.worldState?.worldMap) return;

    const worldMap = window.worldState.worldMap;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const worldWidth = worldMap.width;
    const worldHeight = worldMap.height;

    document.getElementById('debug-world').textContent = `${Math.round(worldWidth)} x ${Math.round(worldHeight)}`;
    document.getElementById('debug-viewport').textContent = `${viewportWidth} x ${viewportHeight}`;
    document.getElementById('debug-scale').textContent = scale.toFixed(3);
    document.getElementById('debug-pan').textContent = `${panX.toFixed(1)}, ${panY.toFixed(1)}`;

    // Compute visible world coordinates
    const leftWorld = -panX / scale;
    const topWorld = -panY / scale;
    const rightWorld = leftWorld + viewportWidth / scale;
    const bottomWorld = topWorld + viewportHeight / scale;
    document.getElementById('debug-visible').textContent = `${leftWorld.toFixed(0)}-${rightWorld.toFixed(0)}, ${topWorld.toFixed(0)}-${bottomWorld.toFixed(0)}`;

    // Fit scale
    const fitScale = Math.min(viewportWidth / worldWidth, viewportHeight / worldHeight);
    document.getElementById('debug-fitscale').textContent = fitScale.toFixed(3);
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('world.js initialized');
    
    // Initialize DMChat safely
    try {
        if (typeof DMChat !== 'undefined') {
            window.dmChat = new DMChat();
        } else {
            window.dmChat = {
                sendMessage: function() {},
                receiveMessage: function() {}
            };
        }
    } catch (e) {
        console.warn('Failed to initialize DMChat:', e);
        window.dmChat = {
            sendMessage: function() {},
            receiveMessage: function() {}
        };
    }
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'd' || e.key === 'D') {
            const overlay = document.getElementById('debug-overlay');
            if (overlay) {
                overlay.style.display = overlay.style.display === 'none' ? 'block' : 'none';
                if (overlay.style.display === 'block') updateDebugOverlay();
            }
        }
    });

    // Set up map interactions
    initPanFunctionality();
    
    // Set up canvas interactions
    setupCanvasInteractions();
    
    // Add panning styles
    addPanningStyles();
    
    // Set initial cursor
    const terrainCanvas = document.getElementById('terrain-canvas');
    if (terrainCanvas) {
        terrainCanvas.style.cursor = 'grab';
    }
    
    // Initialize map controls
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const centerBtn = document.getElementById('center-map');
    const resetBtn = document.getElementById('reset-view');
    
    if (zoomInBtn) zoomInBtn.addEventListener('click', zoomIn);
    if (zoomOutBtn) zoomOutBtn.addEventListener('click', zoomOut);
    if (centerBtn) centerBtn.addEventListener('click', centerMap);
    if (resetBtn) resetBtn.addEventListener('click', resetMapView);
    
    // Make functions globally available for new UI
    window.zoomIn = zoomIn;
    window.zoomOut = zoomOut;
    window.centerMap = centerMap;
    window.resetMapView = resetMapView;
    window.travelToLocation = travelToLocation;
    window.refreshWorldState = refreshWorldState;
    window.renderWorldMap = renderWorldMap;
    window.loadWorldDataWithRetry = loadWorldDataWithRetry;
    
    // Initialize world data
    loadWorldDataWithRetry();
    
    // Set up periodic refresh
    setInterval(() => {
        refreshWorldState();
    }, 30000); // Refresh every 30 seconds
});

// ===== GLOBAL EXPORTS =====
// Make worldState globally available
window.worldState = worldState;

// Export functions for use in console debugging
window.debug = {
    getWorldState: () => worldState,
    refreshWorld: refreshWorldState,
    travelTo: travelToLocation,
    zoomIn: zoomIn,
    zoomOut: zoomOut,
    centerMap: centerMap,
    renderWorldMap: renderWorldMap
};

console.log('world.js loaded successfully');