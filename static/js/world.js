// static\js\world.js
// Initialize world state
let worldState = {
    currentLocation: null,
    party: [],
    activeQuests: [],
    discoveredLocations: []
};

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
            notification.style.background = '#2196F50'; // blue
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


// Add to your existing JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Map zoom and pan variables
    let scale = 1;
    let panX = 0;
    let panY = 0;
    const maxScale = 3;
    const minScale = 0.5;
    
    // Get map elements
    const terrainCanvas = document.getElementById('terrain-canvas');
    const mapOverlay = document.getElementById('map-overlay');

    // Zoom functionality
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const centerBtn = document.getElementById('center-map');
        
    // Zoom in functionality
    if (zoomInBtn) {
        document.getElementById('zoom-in').addEventListener('click', function() {
            if (scale < maxScale) {
                scale += 0.25;
                updateMapTransform();
            }
        });
    }

    // Zoom out functionality
    if(zoomOutBtn) {
        document.getElementById('zoom-out').addEventListener('click', function() {
            if (scale > minScale) {
                scale -= 0.25;
                updateMapTransform();
            }
        });
    }

    // Center map functionality
    if(centerBtn){
        document.getElementById('center-map').addEventListener('click', function() {
            scale = 1;
            panX = 0;
            panY = 0;
            updateMapTransform();
        });
    }

    mapOverlay.addEventListener('mousedown', function(e) {
        isDragging = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
        mapOverlay.style.cursor = 'grabbing';
    });

    document.addEventListener('mouseup', function() {
        isDragging = false;
        mapOverlay.style.cursor = 'grab';
    });

    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        e.preventDefault();
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        updateMapTransform();
    });

    // Update map transform
    function updateMapTransform() {
        const transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        terrainCanvas.style.transform = transform;
        mapOverlay.style.transform = transform;
    }

    // Pan functionality with mouse drag
    let isDragging = false;
    let startX, startY;
    
    mapOverlay.addEventListener('mousedown', function(e) {
        isDragging = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
        mapOverlay.style.cursor = 'grabbing';
    });
    
    document.addEventListener('mouseup', function() {
        isDragging = false;
        mapOverlay.style.cursor = 'grab';
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        e.preventDefault();
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        updateMapTransform();
    });
    
    // Update map transform
    function updateMapTransform() {
        const transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        terrainCanvas.style.transform = transform;
        mapOverlay.style.transform = transform;
    }
    
    // Quick action buttons
    document.getElementById('travel-btn').addEventListener('click', function() {
        console.log('Travel action triggered');
        // Implement travel functionality
    });
    
    document.getElementById('inventory-btn').addEventListener('click', function() {
        console.log('Inventory action triggered');
        // Implement inventory functionality
    });
    
    document.getElementById('quests-btn').addEventListener('click', function() {
        console.log('Quests action triggered');
        // Implement quests functionality
    });
    
    document.getElementById('party-btn').addEventListener('click', function() {
        console.log('Party action triggered');
        // Implement party functionality
    });

    // Check if elements exist before manipulating them
    const worldMapContainer = document.getElementById('world-map');
    
    if (!worldMapContainer || !terrainCanvas || !mapOverlay) {
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
    if(menuItems.length > 0) {
        // Add click event listeners to all menu items
        menuItems.forEach(item => {
            item.addEventListener('click', function() {
                const targetPanel = this.getAttribute('data-target');
                
                if (targetPanel) {
                    // Hide all panels
                    document.querySelectorAll('.panel').forEach(panel => {
                        panel.style.display = 'none';
                    });
                    
                    // Show the target panel
                    const targetElement = document.getElementById(targetPanel);
                    if (targetElement) {
                        targetElement.style.display = 'block';
                    }
                }
            });
        });
    }


});

function showLocationPreview(location, x, y) {
    const preview = document.getElementById('location-preview');
    const img = document.getElementById('preview-image');
    const name = document.getElementById('preview-name');
    const type = document.getElementById('preview-type');
    const desc = document.getElementById('preview-description');

    // Set content
    img.src = location.imageUrl || 'https://dummyimage.com/80x80/333/fff&text=No+Image';
    name.textContent = location.name;
    type.textContent = `Type: ${location.type}`;
    desc.textContent = location.description ? 
      location.description.substring(0, 100) + '...' : 
      'No description available';

    // Position and show
    preview.style.left = `${x + 20}px`;
    preview.style.top = `${y - 20}px`;
    preview.classList.remove('hidden');
}

function hideLocationPreview() {
    document.getElementById('location-preview').classList.add('hidden');
}

// Load world data from server
async function loadWorldData() {
    fetch('/api/world-state')
        .then(response => response.json())
        .then(data => {

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
        })
        .catch(error => {
            console.error('Error loading world data:', error);
            showNotification('Error loading world data.', 'error');
        });
}

function updatePartyDisplay(parties, characters) {
    const container = document.getElementById('party-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    parties.forEach(party => {
        const partyCard = document.createElement('div');
        partyCard.className = 'party-card';
        
        let membersHTML = '';
        party.members.forEach(char_id => {
            const char = characters[char_id];
            membersHTML += `
                <div class="party-member">
                    <div class="member-avatar" 
                         style="background-image: url('${char.avatar_url}')">
                    </div>
                    <span>${char.name}</span>
                    <button class="remove-member" data-char="${char_id}">Remove</button>
                </div>
            `;
        });
        
        partyCard.innerHTML = `
            <h4>${party.name}</h4>
            <div class="party-members">${membersHTML}</div>
            <div class="party-actions">
                <button class="disband-party" data-party="${party.id}">Disband</button>
            </div>
        `;
        
        container.appendChild(partyCard);
    });
    
    // Add event listeners
    document.querySelectorAll('.remove-member').forEach(btn => {
        btn.addEventListener('click', () => {
            const char_id = btn.dataset.char;
            fetch('/api/remove-from-party', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({char_id})
            }).then(refreshWorldState);
        });
    });
    
    document.querySelectorAll('.disband-party').forEach(btn => {
        btn.addEventListener('click', () => {
            const party_id = btn.dataset.party;
            fetch(`/api/disband-party/${party_id}`, {method: 'POST'})
                .then(refreshWorldState);
        });
    });
    
    document.getElementById('create-new-party').addEventListener('click', () => {
        const name = prompt("Enter new party name:");
        if (name) {
            fetch('/api/create-party', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            }).then(refreshWorldState);
        }
    });
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
        } else {
            renderLocationDetails(null);
        }
        
        // Update party display with new party data
        updatePartyDisplay(data.parties, data.characters);
        
        // Update other UI elements as needed
        updateQuestLog(data.parties); // Pass parties instead of activeQuests
        //updateInventory(data.inventory); // todo need to figure out what this is supposed to do. Is this for locations. Has to do with how dm manages inventory, stores, available items, packs, etc.
        
    } catch (error) {
        console.error('Error refreshing world state:', error);
        showNotification('Error refreshing world state.', 'error');
    }
}

function getCurrentPlayerPartyId() {
    // Get current player ID from your authentication system
    const playerId = getCurrentPlayerId(); 
    
    // Find which party the player belongs to
    // This assumes parties have a 'members' array
    for (const party of worldState.parties) {
        if (party.members.includes(playerId)) {
            return party.id;
        }
    }
    
    // Player not in any party
    return null;
}

function updateQuestLog(worldData) {
    try {
        const questLog = document.getElementById('quest-log');
        if (!questLog) return;
        
        // Check if player's party has quests
        const playerParty = worldData.parties.find(p => p.id === playerPartyId);
        
        if (!playerParty || !playerParty.quests || playerParty.quests.length === 0) {
            questLog.innerHTML = '<div class="no-quest">No active quests</div>';
            return;
        }
        
        let html = '';
        for (const quest of playerParty.quests) {
            html += `
                <div class="quest">
                    <div class="quest-header">
                        <h3>${quest.name}</h3>
                        <span class="quest-status">${quest.status}</span>
                    </div>
                    <p class="quest-description">${quest.description}</p>
                    <div class="objectives">`;
            
            // Add objectives
            for (const [key, objective] of Object.entries(quest.objectives)) {
                const status = objective.completed ? '✓' : '◯';
                html += `
                    <div class="objective ${objective.completed ? 'completed' : ''}">
                        <span class="objective-status">${status}</span>
                        ${objective.description}
                    </div>`;
            }
            
            html += `</div></div>`;
        }
        
        questLog.innerHTML = html;
    } catch (error) {
        console.error("Error updating quest log:", error);
        const questLog = document.getElementById('quest-log');
        if (questLog) {
            questLog.innerHTML = '<div class="error">Failed to load quests</div>';
        }
    }
}


// Also call it on initial load
window.addEventListener('load', () => {
    refreshWorldState();
});

function renderMinimalMap(locations) {
    const worldMap = document.getElementById('world-map');
    worldMap.innerHTML = '';
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('viewBox', '0 0 1000 800');
    
    // Add background
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('width', '100%');
    bg.setAttribute('height', '100%');
    bg.setAttribute('fill', '#0d2136');
    svg.appendChild(bg);
    
    // Render each location
    locations.forEach(location => {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('transform', `translate(${location.x},${location.y})`);
        
        // Location marker
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', '12');
        circle.setAttribute('fill', '#4ecca3');
        circle.setAttribute('stroke', '#fff');
        circle.setAttribute('stroke-width', '2');
        circle.setAttribute('data-location-id', location.id);
        
        // Location name
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', '0');
        text.setAttribute('y', '25');
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', 'white');
        text.setAttribute('font-size', '10px');
        text.textContent = location.name;
        
        group.appendChild(circle);
        group.appendChild(text);
        
        // Event handlers
        group.addEventListener('click', () => travelToLocation(location.id));
        group.addEventListener('mouseenter', () => {
            document.getElementById('location-preview').textContent = location.name;
        });
        group.addEventListener('mouseleave', () => {
            document.getElementById('location-preview').textContent = '';
        });
        
        svg.appendChild(group);
    });
    
    // Error message
    const errorText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    errorText.setAttribute('x', '500');
    errorText.setAttribute('y', '50');
    errorText.setAttribute('text-anchor', 'middle');
    errorText.setAttribute('fill', '#ff6b6b');
    errorText.setAttribute('font-size', '20px');
    errorText.textContent = 'Partial Map Data Loaded';
    svg.appendChild(errorText);
    
    worldMap.appendChild(svg);
}

// The consolidated function to render all map elements
// Replace your renderWorldMap function with this:
function renderWorldMap(worldMap) {
    // Store world data for later use
    window.worldState = window.worldState || {};
    window.worldState.worldMap = worldMap;

    // Get map container and elements
    const container = document.getElementById('world-map');
    const mapOverlay = document.getElementById('map-overlay');
    const terrainCanvas = document.getElementById('terrain-canvas');

    if (!container || !mapOverlay || !terrainCanvas) return;
    
    // Set canvas size to match container (fixes blurriness)
    terrainCanvas.width = container.clientWidth;
    terrainCanvas.height = container.clientHeight;

    // Ensure seed is defined with a fallback value
    const seed = worldMap.seed || 42; // Use current timestamp as fallback

    
    // Generate and render terrain
    console.log('renderWorldMap passing worldMap.seed, container.clientWidth, container.clientHeight to TerrainGenerator', worldMap.seed, container.clientWidth, container.clientHeight)
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

    // Clear the SVG overlay before redrawing
    mapOverlay.innerHTML = '';

    // Filter locations and connections based on 'discovered'
    const discoveredLocations = worldMap.locations.filter(loc => loc.discovered);
    const discoveredConnections = worldMap.connections.filter(conn =>
        discoveredLocations.some(loc => loc.id === conn.from_id) &&
        discoveredLocations.some(loc => loc.id === conn.to_id)
    );

    // Draw the paths for discovered connections
    renderPaths(discoveredConnections, worldMap.locations);

    // Place the locations on top of the paths and terrain
    place_locations(discoveredLocations);
}



// Function to draw paths between locations
function renderPaths(connections, locations) {
    const mapOverlay = document.getElementById('map-overlay');
    if (!mapOverlay) return;

    let existingPaths = mapOverlay.querySelectorAll('.path');
    existingPaths.forEach(p => p.remove());

    connections.forEach(conn => {
        const fromLoc = locations.find(loc => loc.id === conn.from_id);
        const toLoc = locations.find(loc => loc.id === conn.to_id);

        if (fromLoc && toLoc) {
            const path = document.createElementNS("http://www.w3.org/2000/svg", "line");
            path.setAttribute('x1', fromLoc.x);
            path.setAttribute('y1', fromLoc.y);
            path.setAttribute('x2', toLoc.x);
            path.setAttribute('y2', toLoc.y);
            path.setAttribute('class', 'path');
            mapOverlay.appendChild(path);
        }
    });
}


// Function to get the terrain color based on its name
function getTerrainColor(terrainType) {
    const terrainTypes = {
        "ocean": {"color": "#4d6fb8"},
        "coast": {"color": "#a2c4c9"},
        "plains": {"color": "#689f38"},
        "hills": {"color": "#8d9946"},
        "mountains": {"color": "#8d99ae"},
        "snowcaps": {"color": "#ffffff"}
    };
    return terrainTypes[terrainType] ? terrainTypes[terrainType].color : "#888888";
}

class HexGridGenerator {
    constructor(width, height, hexSize) {
        this.width = width;
        this.height = height;
        this.hexSize = hexSize;
    }

    // Helper function to calculate hex coordinates
    getHexCenter(x, y) {
        const hexWidth = this.hexSize * 2;
        const hexHeight = Math.sqrt(3) / 2 * hexWidth;
        const center_x = x * hexWidth * 0.75;
        const center_y = y * hexHeight + (x % 2) * hexHeight / 2;
        return { x: center_x, y: center_y };
    }

    // This is the core function for drawing a single hex
    drawHex(ctx, x, y, terrainType) {
        const center = this.getHexCenter(x, y);
        const color = getTerrainColor(terrainType);
        
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle_deg = 60 * i;
            const angle_rad = Math.PI / 180 * angle_deg;
            const point_x = center.x + this.hexSize * Math.cos(angle_rad);
            const point_y = center.y + this.hexSize * Math.sin(angle_rad);
            if (i === 0) {
                ctx.moveTo(point_x, point_y);
            } else {
                ctx.lineTo(point_x, point_y);
            }
        }
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = "#444"; // Hex border color
        ctx.stroke();
    }
    
    // Main function to generate and render the entire hex grid
    renderHexGrid(canvasId, terrainData) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        
        canvas.width = this.width;
        canvas.height = this.height;
        ctx.clearRect(0, 0, this.width, this.height);
        
        terrainData.forEach(hex => {
            this.drawHex(ctx, hex.x, hex.y, hex.type);
        });
    }
}


// Function to place location markers on the map
function place_locations(locations) {
    const mapOverlay = document.getElementById('map-overlay');
    if (!mapOverlay) return;

    let existingMarkers = mapOverlay.querySelectorAll('.location-marker');
    existingMarkers.forEach(m => m.remove());

    locations.forEach(loc => {
        const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        marker.setAttribute('cx', loc.x);
        marker.setAttribute('cy', loc.y);
        marker.setAttribute('r', 10); // Changed from 100 to 10
        marker.setAttribute('class', 'location-marker');
        marker.setAttribute('fill', 'red');
        marker.setAttribute('data-location-id', loc.id);
        
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = loc.name;
        marker.appendChild(title);

        mapOverlay.appendChild(marker);
    });
}


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
        
    } catch (error) {
        console.error('Error rendering location details:', error);
        locationImage.style.backgroundImage = "url('https://dummyimage.com/300x200/333/fff&text=Error')";
        description.innerHTML = '<p>Error loading location details</p>';
    }
}

// In your tavern completion handler
async function completeTavernIntro() {
    const playerId = getCurrentPlayerId();
    const playerPartyId = getCurrentPlayerPartyId();
    
    if (!playerPartyId) {
        console.error("Player not in a party");
        return;
    }
    
    try {
        const response = await fetch('/complete_tavern_intro', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                party_id: playerPartyId,
                player_id: playerId 
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // Refresh world state to show quests
            await refreshWorldState();
            
            // Transition from tavern to world view
            document.getElementById('tavern-scene').style.display = 'none';
            document.getElementById('world-map').style.display = 'block';
        } else {
            console.error('Failed to complete tavern intro:', result.error);
        }
    } catch (error) {
        console.error('Error completing tavern intro:', error);
    }
}

function showTavernIntroduction() {
    const descriptionDiv = document.getElementById('location-description');
    if (descriptionDiv) {
        descriptionDiv.innerHTML += `
            <div class="tavern-intro">
                <h3>Welcome Adventurer!</h3>
                <p>This is where your journey begins. Explore the tavern to:</p>
                <ul>
                    <li>Form a party with other players</li>
                    <li>Learn about local quests</li>
                    <li>Discover rumors of distant lands</li>
                </ul>
                <button id="explore-tavern">Begin Exploration</button>
            </div>
        `;
        
        document.getElementById('explore-tavern').addEventListener('click', startTavernExperience);
    }
}

// Update your resizeMapCanvas function to use the TerrainGenerator
function resizeMapCanvas() {
    const canvas = document.getElementById('terrain-canvas');
    const container = document.getElementById('world-map');
    
    if (canvas && container) {
        // Get container dimensions
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        // Set canvas size
        canvas.width = width;
        canvas.height = height;
        
        // Re-render terrain if world data is available
        if (window.worldState && window.worldState.worldMap && window.worldState.terrain) {
            // Use the TerrainGenerator to render the terrain
            console.log('resizeMapCanvas params seed, width, height passed to TerrainGenerator', window.worldState.worldMap.seed, width, height)
            const terrainGen = new TerrainGenerator(
                window.worldState.worldMap.seed, 
                width, 
                height
            );
            
            // Regenerate heightmap and terrain
            const heightmap = terrainGen.generateHeightmap();
            const terrain = terrainGen.generateTerrain(heightmap);
            
            // Store the terrain for future use
            window.worldState.terrain = terrain;
            
            // Render the terrain
            terrainGen.renderTerrain(terrain, 'terrain-canvas');
            
            // Re-render hex grid if needed
            const gridRenderer = new HexGridRenderer(width, height);
            gridRenderer.renderGrid('terrain-canvas');
        }
    }
}

// Initial render
window.addEventListener('load', function() {
    if (window.worldState && window.worldState.worldMap) {
        renderWorldMap(window.worldState.worldMap);
    } else {
        // Load world data if not already available
        loadWorldData();
    }
});

function startTavernExperience() {
    // Fetch initial rumors
    fetch(`/api/location/${worldState.currentLocation.id}/rumors`)
        .then(response => response.json())
        .then(rumors => {
            // Display rumors to player
            showRumors(rumors);
        });
}

// Travel to a new location
async function travelToLocation(locationId) {
    const response = await fetch(`/api/travel/${locationId}`, { method: 'POST' });
    const data = await response.json();
    
    if (data.success) {
        worldState.currentLocation = data.location;
        renderLocationDetails(data.location);
        renderWorldMap(data.worldMap);
    }
}

// Initialize on load
window.addEventListener('load', () => {
    loadWorldData();
    
    // Set up event listeners
    //document.getElementById('create-character').addEventListener('click', createCharacter);
    //document.getElementById('manage-inventory').addEventListener('click', openInventory);
    //document.getElementById('talk-to-npcs').addEventListener('click', talkToNPCs);

    window.addEventListener('resize', () => {
        // Only re-render if a world map has been loaded
        if (window.worldState && window.worldState.worldMap) {
            renderWorldMap(window.worldState.worldMap);
            resizeMapCanvas();
        }
    });
});


// Enter dungeon from current location
function enterDungeon() {
    // Generate dungeon based on current location
    fetch('/api/generate-dungeon', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Switch to dungeon view
                window.location.href = '/dungeon';
            }
        });
}