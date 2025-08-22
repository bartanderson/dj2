// static\js\world.js
// Initialize world state
let worldState = {
    currentLocation: null,
    party: [],
    activeQuests: [],
    discoveredLocations: []
};

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
            
            // Correctly populate the globally accessible worldState object
            window.worldState = {
                worldMap: data.worldMap,
                // Check if playerState exists before accessing it
                currentLocation: data.playerState ? data.worldMap.locations.find(loc => loc.id === data.playerState.current_location_id) : null,
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
        // Handle errors gracefully
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
function renderWorldMap(worldMap) {
    const worldMapContainer = document.getElementById('world-map');
    const mapOverlay = document.getElementById('map-overlay');
    if (!worldMapContainer || !mapOverlay) return;
    
    // Rationale: We no longer clear the parent 'world-map' div.
    // Instead, we clear the terrain canvas and the SVG overlay individually.
    
    // Step 1: Generate and render the terrain
    const terrainCanvas = document.getElementById('terrain-canvas');
    if (terrainCanvas) {

        // Clear the canvas to prepare for new rendering
        const ctx = terrainCanvas.getContext('2d');
        ctx.clearRect(0, 0, terrainCanvas.width, terrainCanvas.height);
        
        const seed = worldMap.seed || 42;
        const terrainGen = new TerrainGenerator(seed, worldMap.width, worldMap.height);

        const heightmap = terrainGen.generateHeightmap();

        const terrain = terrainGen.generateTerrain(heightmap);

        terrainGen.renderTerrain(terrain, 'terrain-canvas');
    }

    // Step 2: Render the translucent hexagon grid on top of the terrain
    const gridRenderer = new HexGridRenderer(worldMap.width, worldMap.height);
    gridRenderer.renderGrid('terrain-canvas');

    // Step 3: Clear the SVG overlay before redrawing
    mapOverlay.innerHTML = '';

    // Step 4: Filter locations and connections based on 'discovered'.
    const discoveredLocations = worldMap.locations.filter(loc => loc.discovered);
    const discoveredConnections = worldMap.connections.filter(conn =>
        discoveredLocations.some(loc => loc.id === conn.from_id) &&
        discoveredLocations.some(loc => loc.id === conn.to_id)
    );

    // Step 5: Draw the paths for discovered connections.
    renderPaths(discoveredConnections, worldMap.locations);

    // Step 6: Place the locations on top of the paths and terrain.
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
        marker.setAttribute('r', 10);
        marker.setAttribute('class', 'location-marker');
        marker.setAttribute('fill', 'red');
        marker.setAttribute('data-location-id', loc.id);
        
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = loc.name;
        marker.appendChild(title);

        mapOverlay.appendChild(marker);
    });
}

// function renderWorldMap(mapData) {
//     const worldMap = document.getElementById('world-map');
//     if (!worldMap) return; // Safety check
    
//     worldMap.innerHTML = '';
    
//     const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
//     svg.setAttribute('width', '100%');
//     svg.setAttribute('height', '100%');
//     svg.setAttribute('viewBox', `0 0 ${mapData.width} ${mapData.height}`);

//     // Add background
//     const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
//     bg.setAttribute('width', '100%');
//     bg.setAttribute('height', '100%');
//     bg.setAttribute('fill', '#0d2136'); // Dark blue background
//     svg.appendChild(bg);
    
//     // Define patterns for terrains
//     const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
//     defs.innerHTML = `
//         <pattern id="mountainPattern" width="20" height="20" patternUnits="userSpaceOnUse">
//             <path d="M0,10 L5,0 L10,10 Z" fill="#8d99ae" opacity="0.7" />
//         </pattern>
//         <pattern id="forestPattern" width="20" height="20" patternUnits="userSpaceOnUse">
//             <circle cx="5" cy="15" r="3" fill="#2d6a4f" />
//             <circle cx="15" cy="12" r="4" fill="#2d6a4f" />
//             <circle cx="10" cy="5" r="5" fill="#2d6a4f" />
//         </pattern>
//         <pattern id="waterPattern" width="20" height="10" patternUnits="userSpaceOnUse">
//             <path d="M0,5 C5,2 10,8 15,5 S25,2 30,5" stroke="#4d6fb8" fill="none" />
//         </pattern>
//     `;
//     svg.appendChild(defs);
    
//     // Draw terrain hexes safely
//     if (mapData.hexes && Array.isArray(mapData.hexes)) {
//         mapData.hexes.forEach(hex => {
//             const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
//             polygon.setAttribute('points', hex.points);

//             // Get terrain colors safely
//             const terrainColors = mapData.terrainColors || {
//                 "ocean": "#4d6fb8",
//                 "coast": "#a2c4c9",
//                 "lake": "#4d6fb8",
//                 "river": "#4d6fb8",
//                 "plains": "#689f38",
//                 "hills": "#8d9946",
//                 "mountains": "#8d99ae",
//                 "snowcaps": "#ffffff"
//             };
            
//             // Apply terrain-specific styling
//             switch(hex.terrain) {
//                 case "mountains":
//                     polygon.setAttribute('fill', "url(#mountainPattern)");
//                     break;
//                 case "forest":
//                     polygon.setAttribute('fill', "url(#forestPattern)");
//                     break;
//                 case "ocean":
//                     polygon.setAttribute('fill', terrainColors["ocean"]);
//                     break;
//                 case "coast":
//                     polygon.setAttribute('fill', terrainColors["coast"]);
//                     break;
//                 case "lake":
//                     polygon.setAttribute('fill', terrainColors["lake"]);
//                     break;
//                 case "river":
//                     polygon.setAttribute('fill', terrainColors["river"]);
//                     break;
//                 case "snowcaps":
//                     polygon.setAttribute('fill', terrainColors["snowcaps"]);
//                     polygon.setAttribute('stroke', '#aaa');
//                     break;
//                 default:
//                     // Use color from terrainColors if available
//                     if (terrainColors[hex.terrain]) {
//                         polygon.setAttribute('fill', terrainColors[hex.terrain]);
//                     } else {
//                         polygon.setAttribute('fill', '#689f38'); // Default plains color
//                     }
//             }
            
//             polygon.setAttribute('stroke', '#333');
//             polygon.setAttribute('stroke-width', '0.5');
//             polygon.setAttribute('opacity', '0.8');
//             svg.appendChild(polygon);
//         });
//     }

//     // Draw organic paths between locations
//     if (mapData.paths && Array.isArray(mapData.paths)) {
//         mapData.paths.forEach(path => {
//             const pathElem = document.createElementNS('http://www.w3.org/2000/svg', 'path');
//             pathElem.setAttribute('d', `M ${path.points.replace(/ /g, ' L ')}`);
            
//             // Style based on path type
//             switch(path.type) {
//                 case "mountain_pass":
//                     pathElem.setAttribute('stroke', '#5d4037');
//                     pathElem.setAttribute('stroke-dasharray', '10,5');
//                     pathElem.setAttribute('stroke-width', '2');
//                     break;
//                 case "lake_route":
//                 case "sea_route":
//                     pathElem.setAttribute('stroke', '#1565c0');
//                     pathElem.setAttribute('stroke-dasharray', '5,10');
//                     pathElem.setAttribute('stroke-width', '2');
//                     break;
//                 case "river_path":
//                     pathElem.setAttribute('stroke', '#5f3300');
//                     pathElem.setAttribute('stroke-dasharray', '5,10');
//                     pathElem.setAttribute('stroke-width', '2');
//                     break;
//                 default:
//                     pathElem.setAttribute('stroke', '#8d6e63');
//                     pathElem.setAttribute('stroke-width', '2');
//             }
            
//             pathElem.setAttribute('fill', 'none');
//             pathElem.setAttribute('stroke-linecap', 'round');
//             pathElem.setAttribute('stroke-linejoin', 'round');
//             svg.appendChild(pathElem);
//         });
//     }

//     // === FOG OF WAR LOCATION RENDERING ===
//     // Filter locations based on fog of war
//     const visibleLocations = mapData.fog_of_war 
//         ? mapData.locations.filter(loc => mapData.known_locations.includes(loc.id))
//         : mapData.locations;

//     // Get preview element
//     const preview = document.getElementById('location-preview');
    
//     // Render only visible locations
//     visibleLocations.forEach(location => {
//         const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
//         group.setAttribute('transform', `translate(${location.x},${location.y})`);
        
//         // Create location marker circle
//         const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
//         circle.setAttribute('r', '12');
        
//         // Apply special styling for starting location
//         if (location.id === mapData.starting_location) {
//             circle.setAttribute('fill', '#ff9900');  // Orange for starting tavern
//             circle.setAttribute('stroke', '#ff6600');
//         } 
//         // Regular styling for current location
//         else if (location.isCurrent) {
//             circle.setAttribute('fill', '#4ecca3');  // Green for current location
//             circle.setAttribute('stroke', '#fff');
//         }
//         // Regular styling for other locations
//         else {
//             circle.setAttribute('fill', '#3a5f85');  // Blue for other locations
//             circle.setAttribute('stroke', '#fff');
//         }
        
//         circle.setAttribute('stroke-width', '2');
//         circle.setAttribute('data-location-id', location.id);
//         circle.classList.add('location-marker');
        
//         // Create location type icon
//         let icon;
//         if (location.type === "mountain_pass") {
//             icon = document.createElementNS('http://www.w3.org/2000/svg', 'path');
//             icon.setAttribute('d', 'M -6,-6 L 0,6 L 6,-6 Z');
//             icon.setAttribute('fill', '#fff');
//         } else if (location.type === "port") {
//             icon = document.createElementNS('http://www.w3.org/2000/svg', 'path');
//             icon.setAttribute('d', 'M -8,0 L 0,-8 L 8,0 L 0,8 Z');
//             icon.setAttribute('fill', '#fff');
//         } else {
//             icon = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
//             icon.setAttribute('r', '4');
//             icon.setAttribute('fill', '#fff');
//         }
        
//         // Add elements to group
//         group.appendChild(circle);
//         group.appendChild(icon);
        
//         // Add event handlers
//         group.addEventListener('click', () => travelToLocation(location.id));
//         // Preview event handlers
//         group.addEventListener('mouseenter', (e) => {
//             if (preview) {
//                 preview.textContent = location.name;
//                 preview.classList.remove('hidden');
//             }
//         });
        
//         group.addEventListener('mousemove', (e) => {
//             if (preview) {
//                 const rect = worldMap.getBoundingClientRect();
//                 preview.style.left = `${e.clientX - rect.left + 15}px`;
//                 preview.style.top = `${e.clientY - rect.top - 15}px`;
//             }
//         });
        
//         group.addEventListener('mouseleave', () => {
//             if (preview) {
//                 preview.textContent = '';
//                 preview.classList.add('hidden');
//             }
//         });
        
//         // Add group to SVG
//         svg.appendChild(group);
//     });
    
//     // Add SVG to DOM
//     worldMap.appendChild(svg);
    
//     // Show tavern introduction if at starting location
//     if (worldState.currentLocation?.id === mapData.starting_location) {
//         showTavernIntroduction();
//     }
// }

// Minimal CSS for location preview
const previewStyles = `
    .location-preview {
        position: absolute;
        background: rgba(30, 30, 40, 0.9);
        border: 2px solid #5d4037;
        border-radius: 8px;
        padding: 8px 12px;
        color: white;
        font-family: 'MedievalSharp', cursive;
        font-size: 14px;
        z-index: 1000;
        pointer-events: none;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.7);
        max-width: 200px;
        text-align: center;
        transition: opacity 0.2s;
    }
    
    .location-preview.hidden {
        opacity: 0;
    }
`;

// Add styles to document head
const styleEl = document.createElement('style');
styleEl.innerHTML = previewStyles;
document.head.appendChild(styleEl);

// Initialize preview element
const previewEl = document.createElement('div');
previewEl.id = 'location-preview';
previewEl.className = 'location-preview hidden';
document.querySelector('.world-container').appendChild(previewEl);


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
    document.getElementById('enter-dungeon').addEventListener('click', enterDungeon);
    //document.getElementById('create-character').addEventListener('click', createCharacter);
    //document.getElementById('manage-inventory').addEventListener('click', openInventory);
    //document.getElementById('talk-to-npcs').addEventListener('click', talkToNPCs);

    window.addEventListener('resize', () => {
        // Only re-render if a world map has been loaded
        if (window.worldState && window.worldState.worldMap) {
            renderWorldMap(window.worldState.worldMap);
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