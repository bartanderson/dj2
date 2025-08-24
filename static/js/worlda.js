// static\js\world.js
// Initialize world state
let worldState = {
    currentLocation: null,
    party: [],
    activeQuests: [],
    discoveredLocations: []
};

// Map zoom and pan variables
let scale = 1;
let panX = 0;
let panY = 0;
const maxScale = 3;
const minScale = 0.5;

// Location preview class
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
            <img id="preview-image" src="" alt="Location image">
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
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px'
        });
        
        // Add image styles
        const img = this.element.querySelector('#preview-image');
        Object.assign(img.style, {
            width: '80px',
            height: '80px',
            borderRadius: '4px',
            objectFit: 'cover'
        });
        
        // Add content styles
        const content = this.element.querySelector('.preview-content');
        Object.assign(content.style, {
            flex: '1',
            minWidth: '0'
        });
        
        document.body.appendChild(this.element);
        return this;
    }
    
    show(location, x, y) {
        if (!this.element) this.create();
        
        const img = this.element.querySelector('#preview-image');
        const name = this.element.querySelector('#preview-name');
        const type = this.element.querySelector('#preview-type');
        const desc = this.element.querySelector('#preview-description');

        img.src = location.imageUrl || 'https://dummyimage.com/80x80/333/fff&text=No+Image';
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
        this.element.classList.remove('hidden');
        this.isVisible = true;
    }
    
    hide() {
        if (this.element) {
            this.element.classList.add('hidden');
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

// Function to show notifications
function showNotification(message, type = 'info') {
    // Create notification container if it doesn't exist
    let notificationContainer = document.querySelector('.notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.className = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '20px';
        notificationContainer.style.right = '20px';
        notificationContainer.style.zIndex = '1000';
        document.body.appendChild(notificationContainer);
    }

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add basic styling
    notification.style.padding = '10px 15px';
    notification.style.marginBottom = '10px';
    notification.style.borderRadius = '4px';
    notification.style.color = 'white';
    notification.style.fontFamily = 'Arial, sans-serif';
    notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
    
    // Set background color based on type
    switch(type) {
        case 'error':
            notification.style.background = '#f44336'; // red
            break;
        case 'success':
            notification.style.background = '#4CAF50'; // green
            break;
        case 'warning':
            notification.style.background = '#ff9800'; // orange
            break;
        default: // info
            notification.style.background = '#2196F3'; // blue
    }
    
    notificationContainer.appendChild(notification);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
        notification.remove();
        // Remove container if it's empty
        if (notificationContainer.children.length === 0) {
            notificationContainer.remove();
        }
    }, 5000);
}

// Update map transform
function updateMapTransform() {
    const terrainCanvas = document.getElementById('terrain-canvas');
    const mapOverlay = document.getElementById('map-overlay');
    
    if (terrainCanvas && mapOverlay) {
        const transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        terrainCanvas.style.transform = transform;
        mapOverlay.style.transform = transform;
    }
}

// Function to safely add event listeners
function safeAddEventListener(selector, event, handler) {
    const element = document.querySelector(selector);
    if (element) {
        element.addEventListener(event, handler);
        return true;
    }
    return false;
}

// Add event listeners to the canvas for hover interactions
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
                terrainCanvas.style.cursor = 'default';
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
                travelToLocation(clickedLocation.id);
            }
        }
    });
}

// Function to draw paths between locations on the canvas
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

// Function to draw location markers on the canvas
function drawLocations(ctx, locations) {
    // Clear previous locations
    window.worldState.locations = [];
    
    locations.forEach(loc => {
        // Draw outer circle
        ctx.fillStyle = 'red';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        
        ctx.beginPath();
        ctx.arc(loc.x, loc.y, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        
        // Store location data for hit detection
        window.worldState.locations.push({
            x: loc.x,
            y: loc.y,
            radius: 10,
            id: loc.id,
            data: loc
        });
    });
}

// The consolidated function to render all map elements
function renderWorldMap(worldMap) {
    // Store world data for later use
    window.worldState = window.worldState || {};
    
    // Ensure we have a valid worldMap object
    if (!worldMap) {
        console.error('renderWorldMap: worldMap is undefined');
        showNotification('Error rendering map: No map data available', 'error');
        return;
    }
    
    window.worldState.worldMap = worldMap;

    // Get map container and elements
    const container = document.getElementById('world-map');
    const terrainCanvas = document.getElementById('terrain-canvas');

    if (!container || !terrainCanvas) {
        console.error('Map container or canvas not found');
        return;
    }
    
    // Set canvas size to match container (fixes blurriness)
    terrainCanvas.width = container.clientWidth;
    terrainCanvas.height = container.clientHeight;
    
    // Get canvas context
    const ctx = terrainCanvas.getContext('2d');
    
    // Ensure seed is defined with a fallback value
    const seed = worldMap.seed || 42;
    
    // Generate and render terrain
    const terrainGen = new TerrainGenerator(seed, container.clientWidth, container.clientHeight);
    const heightmap = terrainGen.generateHeightmap();
    const terrain = terrainGen.generateTerrain(heightmap);
    
    // Store terrain for future use
    window.worldState.terrain = terrain;
    
    // Render terrain
    terrainGen.renderTerrain(terrain, 'terrain-canvas');
    
    // Render hex grid
    const gridRenderer = new HexGridRenderer(container.clientWidth, container.clientHeight);
    gridRenderer.renderGrid('terrain-canvas');

    // Filter locations and connections based on 'discovered'
    const discoveredLocations = worldMap.locations ? worldMap.locations.filter(loc => loc.discovered) : [];
    const discoveredConnections = worldMap.connections ? worldMap.connections.filter(conn =>
        discoveredLocations.some(loc => loc.id === conn.from_id) &&
        discoveredLocations.some(loc => loc.id === conn.to_id)
    ) : [];

    // Draw the paths for discovered connections
    drawPaths(ctx, discoveredConnections, worldMap.locations || []);

    // Place the locations on top of the paths and terrain
    drawLocations(ctx, discoveredLocations);
    
    // Apply initial transform
    updateMapTransform();
    
    // Set up canvas interactions
    setupCanvasInteractions();
}
// function renderWorldMap(worldMap) {
//     // Store world data for later use
//     window.worldState = window.worldState || {};
//     window.worldState.worldMap = worldMap;

//     // Get map container and elements
//     const container = document.getElementById('world-map');
//     const terrainCanvas = document.getElementById('terrain-canvas');

//     if (!container || !terrainCanvas) return;
    
//     // Set canvas size to match container (fixes blurriness)
//     terrainCanvas.width = container.clientWidth;
//     terrainCanvas.height = container.clientHeight;
    
//     // Get canvas context
//     const ctx = terrainCanvas.getContext('2d');
    
//     // Ensure seed is defined with a fallback value
//     const seed = worldMap.seed || 42;
    
//     // Generate and render terrain
//     const terrainGen = new TerrainGenerator(seed, container.clientWidth, container.clientHeight);
//     const heightmap = terrainGen.generateHeightmap();
//     const terrain = terrainGen.generateTerrain(heightmap);
    
//     // Store terrain for future use
//     window.worldState.terrain = terrain;
    
//     // Render terrain
//     terrainGen.renderTerrain(terrain, 'terrain-canvas');
    
//     // Render hex grid
//     const gridRenderer = new HexGridRenderer(container.clientWidth, container.clientHeight);
//     gridRenderer.renderGrid('terrain-canvas');

//     // Filter locations and connections based on 'discovered'
//     const discoveredLocations = worldMap.locations.filter(loc => loc.discovered);
//     const discoveredConnections = worldMap.connections.filter(conn =>
//         discoveredLocations.some(loc => loc.id === conn.from_id) &&
//         discoveredLocations.some(loc => loc.id === conn.to_id)
//     );

//     // Draw the paths for discovered connections
//     drawPaths(ctx, discoveredConnections, worldMap.locations);

//     // Place the locations on top of the paths and terrain
//     drawLocations(ctx, discoveredLocations);
    
//     // Apply initial transform
//     updateMapTransform();
    
//     // Set up canvas interactions
//     setupCanvasInteractions();
// }

// Render location details
function renderLocationDetails(location) {
    const locationImage = document.getElementById('location-image');
    const description = document.getElementById('location-description');
    
    // Return early if elements are missing
    if (!locationImage || !description) return;
    
    try {
        // Reset elements
        locationImage.style.backgroundImage = '';
        description.innerHTML = '';
        
        // Handle missing location
        if (!location) {
            locationImage.style.backgroundImage = "url('https://dummyimage.com/300x200/333/fff&text=No+Location')";
            description.innerHTML = '<p>No location data available</p>';
            return;
        }
        
        // Set background image with fallback
        if (location.imageUrl) {
            locationImage.style.backgroundImage = `url('${location.imageUrl}')`;
        } else {
            const name = location.name ? encodeURIComponent(location.name) : 'Location';
            locationImage.style.backgroundImage = 
                `url('https://dummyimage.com/300x200/333/fff&text=${name}')`;
        }
        
        // Safely handle features and services
        const features = Array.isArray(location.features) ? location.features : [];
        const services = Array.isArray(location.services) ? location.services : [];
        
        // Build HTML content
        let html = `<h2>${location.name || 'Unknown Location'}</h2>
                   <p>${location.description || 'No description available'}</p>`;
        
        if (features.length > 0) {
            html += `<div class="location-features">
                     <h4>Features:</h4>
                     <ul>${features.map(f => `<li>${f}</li>`).join('')}</ul>
                     </div>`;
        }
        
        if (services.length > 0) {
            html += `<div class="location-services">
                     <h4>Services:</h4>
                     <ul>${services.map(s => `<li>${s}</li>`).join('')}</ul>
                     </div>`;
        }
        
        description.innerHTML = html;
        
        // Also update the location details panel if it's visible
        if (document.getElementById('location-details').style.display === 'block') {
            updateLocationDetailsPanel(location);
        }
        
    } catch (error) {
        console.error('Error rendering location details:', error);
        locationImage.style.backgroundImage = "url('https://dummyimage.com/300x200/333/fff&text=Error')";
        description.innerHTML = '<p>Error loading location details</p>';
    }
}
// Load world data from server
async function loadWorldData() {
    try {
        const response = await fetch('/api/world-state');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();

        // Find current location by ID
        let currentLocation = null;
        if (data.currentLocation && data.currentLocation.id) {
            currentLocation = data.worldMap.locations.find(
                loc => loc.id === data.currentLocation.id
            );
        }
        
        // Correctly populate the globally accessible worldState object
        window.worldState = {
            worldMap: data.worldMap,
            currentLocation: currentLocation,
            locations: data.worldMap.locations
        };
    
        // Render the map for the first time
        renderWorldMap(window.worldState.worldMap);
        
        // Render location details if available
        if (currentLocation) {
            renderLocationDetails(currentLocation);
        }
    } catch (error) {
        console.error('Error loading world data:', error);
        showNotification('Error loading world data.', 'error');
    }
}

async function refreshWorldState() {
    try {
        const response = await fetch('/api/world-state');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update world map and location details
        renderWorldMap(data.worldMap);
        
        if (data.currentLocation) {
            worldState.currentLocation = data.currentLocation;
            renderLocationDetails(data.currentLocation);
            updateLocationDetailsPanel(data.currentLocation);
        } else {
            renderLocationDetails(null);
        }
        
        // Update party display with new party data
        updatePartyDisplay(data.parties, data.characters);
        
        // Update quest log
        updateQuestLog(data.parties);
        
    } catch (error) {
        console.error('Error refreshing world state:', error);
        showNotification('Error refreshing world data.', 'error');
    }
}


// Travel to a new location
async function travelToLocation(locationId) {
    try {
        const response = await fetch(`/api/travel/${locationId}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            worldState.currentLocation = data.location;
            renderLocationDetails(data.location);
            
            // Check if worldMap is provided in the response, otherwise use the existing one
            if (data.worldMap) {
                renderWorldMap(data.worldMap);
            } else {
                // If no worldMap in response, just update the current location
                // and keep the existing world map
                if (window.worldState && window.worldState.worldMap) {
                    // Just update the current location in the existing world map
                    window.worldState.currentLocation = data.location;
                }
            }
            
            showNotification(`Traveled to ${data.location.name}`, 'success');
        } else {
            showNotification('Failed to travel to location', 'error');
        }
    } catch (error) {
        console.error('Error traveling to location:', error);
        showNotification('Error traveling to location', 'error');
    }
}
// async function travelToLocation(locationId) {
//     try {
//         const response = await fetch(`/api/travel/${locationId}`, { method: 'POST' });
//         const data = await response.json();
        
//         if (data.success) {
//             worldState.currentLocation = data.location;
//             renderLocationDetails(data.location);
//             renderWorldMap(data.worldMap);
//             showNotification(`Traveled to ${data.location.name}`, 'success');
//         } else {
//             showNotification('Failed to travel to location', 'error');
//         }
//     } catch (error) {
//         console.error('Error traveling to location:', error);
//         showNotification('Error traveling to location', 'error');
//     }
// }

// Enter dungeon from current location
function enterDungeon() {
    // Generate dungeon based on current location
    fetch('/api/generate-dungeon', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Switch to dungeon view
                window.location.href = '/dungeon';
            } else {
                showNotification('Failed to enter dungeon', 'error');
            }
        })
        .catch(error => {
            console.error('Error entering dungeon:', error);
            showNotification('Error entering dungeon', 'error');
        });
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    // Map zoom and pan variables
    let isDragging = false;
    let startX, startY;
    
    // Get map elements
    const terrainCanvas = document.getElementById('terrain-canvas');
    //const mapOverlay = document.getElementById('map-overlay');

    // Zoom functionality
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const centerBtn = document.getElementById('center-map');
    
    // Add event listeners safely
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', function() {
            if (scale < maxScale) {
                scale += 0.25;
                updateMapTransform();
            }
        });
    }
    
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', function() {
            if (scale > minScale) {
                scale -= 0.25;
                updateMapTransform();
            }
        });
    }
    
    if (centerBtn) {
        centerBtn.addEventListener('click', function() {
            scale = 1;
            panX = 0;
            panY = 0;
            updateMapTransform();
        });
    }
    
    // // Pan functionality with mouse drag
    // if (mapOverlay) {
    //     mapOverlay.addEventListener('mousedown', function(e) {
    //         isDragging = true;
    //         startX = e.clientX - panX;
    //         startY = e.clientY - panY;
    //         mapOverlay.style.cursor = 'grabbing';
    //     });
    // }
    
    // document.addEventListener('mouseup', function() {
    //     isDragging = false;
    //     if (mapOverlay) {
    //         mapOverlay.style.cursor = 'grab';
    //     }
    // });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        e.preventDefault();
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        updateMapTransform();
    });
    
    // Quick action buttons
    const travelBtn = document.getElementById('travel-btn');
    const inventoryBtn = document.getElementById('inventory-btn');
    const questsBtn = document.getElementById('quests-btn');
    const partyBtn = document.getElementById('party-btn');
    
    if (travelBtn) {
        travelBtn.addEventListener('click', function() {
            console.log('Travel action triggered');
            // Implement travel functionality
        });
    }
    
    if (inventoryBtn) {
        inventoryBtn.addEventListener('click', function() {
            console.log('Inventory action triggered');
            // Implement inventory functionality
        });
    }
    
    if (questsBtn) {
        questsBtn.addEventListener('click', function() {
            console.log('Quests action triggered');
            // Implement quests functionality
        });
    }
    
    if (partyBtn) {
        partyBtn.addEventListener('click', function() {
            console.log('Party action triggered');
            // Implement party functionality
        });
    }
    
    // Check if elements exist before manipulating them
    const worldMapContainer = document.getElementById('world-map');
    
    if (!worldMapContainer || !terrainCanvas) {
        console.error('Required map elements not found in DOM');
        return;
    }
    
    // Initialize your map only if elements exist
    loadWorldData();
    
    // Add event listeners only if elements exist
    const enterDungeonBtn = document.getElementById('enter-dungeon');
    if (enterDungeonBtn) {
        enterDungeonBtn.addEventListener('click', enterDungeon);
    }

    // Get all menu items
    const menuItems = document.querySelectorAll('.menu-item');
    
    // Add click event listeners to all menu items
    menuItems.forEach(item => {
        const targetPanel = item.getAttribute('data-target');
        
        if (targetPanel) {
            item.addEventListener('click', function() {
                // Hide all panels
                document.querySelectorAll('.panel').forEach(panel => {
                    panel.style.display = 'none';
                });
                
                // Show the target panel
                const targetElement = document.getElementById(targetPanel);
                if (targetElement) {
                    targetElement.style.display = 'block';
                }
            });
        }
    });

    // Add event listeners for navigation tabs
    const navTabs = document.querySelectorAll('.nav-tab');
    navTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            const targetPanel = e.target.dataset.target;
            if (targetPanel) {
                showPanel(targetPanel);
                
                // If showing location details, update them
                if (targetPanel === 'location-details' && worldState.currentLocation) {
                    updateLocationDetailsPanel(worldState.currentLocation);
                }
                
                // If showing party details, refresh world state to get latest data
                if (targetPanel === 'party-management') {
                    refreshWorldState();
                }
            }
        });
    });
    
    // Add event listener for create party button
    const createPartyBtn = document.getElementById('create-party-btn');
    if (createPartyBtn) {
        createPartyBtn.addEventListener('click', createParty);
    }
    
    // Add event listener for travel button
    const travelBtn = document.getElementById('travel-btn');
    if (travelBtn) {
        travelBtn.addEventListener('click', () => {
            showPanel('travel-panel');
            // You might want to populate the travel panel with available locations
        });
    }
    
    // Add event listener for inventory button
    const inventoryBtn = document.getElementById('inventory-btn');
    if (inventoryBtn) {
        inventoryBtn.addEventListener('click', () => {
            showPanel('inventory-panel');
            // You might want to populate the inventory panel
        });
    }
    
    // Add event listener for quests button
    const questsBtn = document.getElementById('quests-btn');
    if (questsBtn) {
        questsBtn.addEventListener('click', () => {
            showPanel('quests-panel');
            // Refresh to get latest quests
            refreshWorldState();
        });
    }


});

// Also call refreshWorldState on initial load
window.addEventListener('load', () => {
    refreshWorldState();
});

// Function to update the location details panel
function updateLocationDetailsPanel(location) {
    const locationName = document.getElementById('location-name');
    const locationType = document.getElementById('location-type');
    const locationDescription = document.getElementById('location-description');
    const locationFeatures = document.getElementById('location-features');
    const locationServices = document.getElementById('location-services');
    const locationImage = document.getElementById('location-image');

    if (locationName) locationName.textContent = location.name || 'Unknown Location';
    if (locationType) locationType.textContent = location.type || 'Unknown Type';
    if (locationDescription) locationDescription.textContent = location.description || 'No description available';
    
    // Update features list
    if (locationFeatures) {
        locationFeatures.innerHTML = '';
        if (location.features && location.features.length > 0) {
            location.features.forEach(feature => {
                const li = document.createElement('li');
                li.textContent = feature;
                locationFeatures.appendChild(li);
            });
        } else {
            locationFeatures.innerHTML = '<li>No features available</li>';
        }
    }
    
    // Update services list
    if (locationServices) {
        locationServices.innerHTML = '';
        if (location.services && location.services.length > 0) {
            location.services.forEach(service => {
                const li = document.createElement('li');
                li.textContent = service;
                locationServices.appendChild(li);
            });
        } else {
            locationServices.innerHTML = '<li>No services available</li>';
        }
    }
    
    // Update image
    if (locationImage) {
        if (location.imageUrl) {
            locationImage.src = location.imageUrl;
            locationImage.style.display = 'block';
        } else {
            locationImage.style.display = 'none';
        }
    }
}

// Function to show/hide UI panels
function showPanel(panelId) {
    // Hide all panels
    document.querySelectorAll('.panel').forEach(panel => {
        panel.style.display = 'none';
    });
    
    // Show the requested panel
    const panel = document.getElementById(panelId);
    if (panel) {
        panel.style.display = 'block';
    }
}

// Function to update the party display
function updatePartyDisplay(parties, characters) {
    const partyList = document.getElementById('party-list');
    if (!partyList) return;
    
    partyList.innerHTML = '';
    
    if (!parties || parties.length === 0) {
        partyList.innerHTML = '<div class="no-party">No active parties</div>';
        return;
    }
    
    parties.forEach(party => {
        const partyCard = document.createElement('div');
        partyCard.className = 'party-card';
        
        let membersHTML = '';
        if (party.members && party.members.length > 0) {
            party.members.forEach(memberId => {
                const character = characters[memberId];
                if (character) {
                    membersHTML += `
                        <div class="party-member">
                            <div class="member-avatar" 
                                 style="background-image: url('${character.avatar_url || '/static/images/default_avatar.png'}')">
                            </div>
                            <span>${character.name}</span>
                            <button class="remove-member" data-char="${memberId}">Remove</button>
                        </div>
                    `;
                }
            });
        } else {
            membersHTML = '<div class="no-members">No members in this party</div>';
        }
        
        partyCard.innerHTML = `
            <h4>${party.name}</h4>
            <div class="party-members">${membersHTML}</div>
            <div class="party-actions">
                <button class="disband-party" data-party="${party.id}">Disband</button>
            </div>
        `;
        
        partyList.appendChild(partyCard);
    });
    
    // Add event listeners for remove member buttons
    document.querySelectorAll('.remove-member').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const charId = e.target.dataset.char;
            removeFromParty(charId);
        });
    });
    
    // Add event listeners for disband party buttons
    document.querySelectorAll('.disband-party').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const partyId = e.target.dataset.party;
            disbandParty(partyId);
        });
    });
}

// Function to update the quest log
function updateQuestLog(parties) {
    const questLog = document.getElementById('quest-log');
    if (!questLog) return;
    
    questLog.innerHTML = '';
    
    // Find the player's party
    const playerPartyId = getCurrentPlayerPartyId();
    const playerParty = parties.find(p => p.id === playerPartyId);
    
    if (!playerParty || !playerParty.quests || playerParty.quests.length === 0) {
        questLog.innerHTML = '<div class="no-quest">No active quests</div>';
        return;
    }
    
    playerParty.quests.forEach(quest => {
        const questElement = document.createElement('div');
        questElement.className = 'quest';
        
        let objectivesHTML = '';
        if (quest.objectives) {
            for (const [key, objective] of Object.entries(quest.objectives)) {
                const status = objective.completed ? '✓' : '◯';
                objectivesHTML += `
                    <div class="objective ${objective.completed ? 'completed' : ''}">
                        <span class="objective-status">${status}</span>
                        ${objective.description}
                    </div>
                `;
            }
        }
        
        questElement.innerHTML = `
            <div class="quest-header">
                <h3>${quest.title}</h3>
                <span class="quest-status">${quest.status || 'Active'}</span>
            </div>
            <p class="quest-description">${quest.description}</p>
            <div class="objectives">${objectivesHTML}</div>
        `;
        
        questLog.appendChild(questElement);
    });
}

// Function to remove a character from a party
async function removeFromParty(charId) {
    try {
        const response = await fetch('/api/remove-from-party', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({char_id: charId})
        });
        
        if (response.ok) {
            showNotification('Character removed from party', 'success');
            refreshWorldState();
        } else {
            showNotification('Failed to remove character from party', 'error');
        }
    } catch (error) {
        console.error('Error removing from party:', error);
        showNotification('Error removing from party', 'error');
    }
}

// Function to disband a party
async function disbandParty(partyId) {
    try {
        const response = await fetch(`/api/disband-party/${partyId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showNotification('Party disbanded', 'success');
            refreshWorldState();
        } else {
            showNotification('Failed to disband party', 'error');
        }
    } catch (error) {
        console.error('Error disbanding party:', error);
        showNotification('Error disbanding party', 'error');
    }
}

// Function to create a new party
async function createParty() {
    const name = prompt("Enter new party name:");
    if (name) {
        try {
            const response = await fetch('/api/create-party', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });
            
            if (response.ok) {
                showNotification('Party created', 'success');
                refreshWorldState();
            } else {
                showNotification('Failed to create party', 'error');
            }
        } catch (error) {
            console.error('Error creating party:', error);
            showNotification('Error creating party', 'error');
        }
    }
}

function getCurrentPlayerId() {
    // TODO: Implement getting current player ID
    return 'default_player_id';
}

function getCurrentPlayerPartyId() {
    // TODO: Implement getting current player party ID
    return 'default_party_id';
}