// Initialize world state
let worldState = {
    currentLocation: null,
    party: [],
    activeQuests: [],
    discoveredLocations: []
};

// Load world data from server
async function loadWorldData() {
    try {
        const response = await fetch('/api/world-state');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data) {
            throw new Error('Empty response from server');
        }
        
        renderWorldMap(data.worldMap);
        
        if (data.currentLocation) {
            worldState.currentLocation = data.currentLocation;
            renderLocationDetails(data.currentLocation);
        } else {
            renderLocationDetails(null); // Handle no current location
        }
    } catch (error) {
        console.error('Error loading world data:', error);
        
        // Try to get location data even if full map failed
        let locations = [];
        try {
            const locResponse = await fetch('/api/locations');
            if (locResponse.ok) {
                const locData = await locResponse.json();
                locations = locData.locations || [];
            }
        } catch (e) {
            console.error('Failed to load locations:', e);
        }
        
        renderMinimalMap(locations);
        renderLocationDetails(null);
    }
}

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

function renderWorldMap(mapData) {
    const worldMap = document.getElementById('world-map');
    worldMap.innerHTML = '';
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('viewBox', `0 0 ${mapData.width} ${mapData.height}`);
    
    // Define patterns for terrains
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
        <pattern id="mountainPattern" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M0,10 L5,0 L10,10 Z" fill="#8d99ae" opacity="0.7" />
        </pattern>
        <pattern id="forestPattern" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="5" cy="15" r="3" fill="#2d6a4f" />
            <circle cx="15" cy="12" r="4" fill="#2d6a4f" />
            <circle cx="10" cy="5" r="5" fill="#2d6a4f" />
        </pattern>
        <pattern id="waterPattern" width="20" height="10" patternUnits="userSpaceOnUse">
            <path d="M0,5 C5,2 10,8 15,5 S25,2 30,5" stroke="#4d6fb8" fill="none" />
        </pattern>
    `;
    svg.appendChild(defs);
    
    // Draw terrain hexes safely
    if (mapData.hexes && Array.isArray(mapData.hexes)) {
        mapData.hexes.forEach(hex => {
            const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
            polygon.setAttribute('points', hex.points);

            // Get terrain colors safely
            const terrainColors = mapData.terrainColors || {
                "ocean": "#4d6fb8",
                "coast": "#a2c4c9",
                "lake": "#4d6fb8",
                "river": "#4d6fb8",
                "plains": "#689f38",
                "hills": "#8d9946",
                "mountains": "#8d99ae",
                "snowcaps": "#ffffff"
            };
            
            // Apply terrain-specific styling
            switch(hex.terrain) {
                case "mountains":
                    polygon.setAttribute('fill', "url(#mountainPattern)");
                    break;
                case "forest":
                    polygon.setAttribute('fill', "url(#forestPattern)");
                    break;
                case "ocean":
                    polygon.setAttribute('fill', "url(#oceanPattern)");
                    polygon.setAttribute('filter', "url(#deep-water-filter)");
                    break;
                case "coast":
                    polygon.setAttribute('fill', "url(#waterPattern)");
                    polygon.setAttribute('filter', "url(#shallow-water-filter)");
                    break;
                case "lake":
                    polygon.setAttribute('fill', terrainColors["lake"]);
                    polygon.setAttribute('filter', "url(#lake-filter)");
                    break;
                case "river":
                    polygon.setAttribute('fill', terrainColors["river"]);
                    polygon.setAttribute('filter', "url(#river-filter)");
                    break;
                case "snowcaps":
                    polygon.setAttribute('fill', terrainColors["snowcaps"]);
                    polygon.setAttribute('stroke', '#aaa');
                    break;
                default:
                    // Use color from terrainColors if available
                    if (terrainColors[hex.terrain]) {
                        polygon.setAttribute('fill', terrainColors[hex.terrain]);
                    } else {
                        polygon.setAttribute('fill', '#689f38'); // Default plains color
                    }
            }
            
            polygon.setAttribute('stroke', '#333');
            polygon.setAttribute('stroke-width', '0.5');
            polygon.setAttribute('opacity', '0.8');
            svg.appendChild(polygon);
        });
    }

    
    // Draw organic paths safely
    if (mapData.paths && Array.isArray(mapData.paths)) {
        mapData.paths.forEach(path => {
            const pathElem = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            pathElem.setAttribute('d', `M ${path.points.replace(/ /g, ' L ')}`);
            
            // Style based on path type
            switch(path.type) {
                case "mountain_pass":
                    pathElem.setAttribute('stroke', '#5d4037');
                    pathElem.setAttribute('stroke-dasharray', '10,5');
                    pathElem.setAttribute('stroke-width', '2');
                    break;
                case "lake_route":
                case "sea_route":
                    pathElem.setAttribute('stroke', '#1565c0');
                    pathElem.setAttribute('stroke-dasharray', '5,10');
                    pathElem.setAttribute('stroke-width', '2');
                    break;
                case "river_path":
                    pathElem.setAttribute('stroke', '#5f3300');
                    pathElem.setAttribute('stroke-dasharray', '5,10');
                    pathElem.setAttribute('stroke-width', '2');
                    break;
                default:
                    pathElem.setAttribute('stroke', '#ffffff' /*'#8d6e63'*/);
                    pathElem.setAttribute('stroke-width', '2');
            }
            
            pathElem.setAttribute('fill', 'none');
            pathElem.setAttribute('stroke-width', '4');
            pathElem.setAttribute('stroke-linecap', 'round');
            pathElem.setAttribute('stroke-linejoin', 'round');
            svg.appendChild(pathElem);
        });
    }    

    
    // Draw locations
    mapData.locations.forEach(location => {
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('transform', `translate(${location.x},${location.y})`);
        
        // Base circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', '12');
        circle.setAttribute('fill', location.isCurrent ? '#4ecca3' : '#3a5f85');
        circle.setAttribute('stroke', '#fff');
        circle.setAttribute('stroke-width', '2');
        circle.setAttribute('data-location-id', location.id);
        circle.classList.add('location-marker');
        
        // Location type icon
        let icon;
        if (location.type === "mountain_pass") {
            icon = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            icon.setAttribute('d', 'M -6,-6 L 0,6 L 6,-6 Z');
            icon.setAttribute('fill', '#fff');
        } else if (location.type === "port") {
            icon = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            icon.setAttribute('d', 'M -8,0 L 0,-8 L 8,0 L 0,8 Z');
            icon.setAttribute('fill', '#fff');
        } else {
            icon = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            icon.setAttribute('r', '4');
            icon.setAttribute('fill', '#fff');
        }
        
        group.appendChild(circle);
        group.appendChild(icon);
        
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
    
    worldMap.appendChild(svg);
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
// function renderLocationDetails(location) {
//     const locationImage = document.getElementById('location-image');
//     const description = document.getElementById('location-description');
    
//     // Set background image with fallback
//     if (location.imageUrl) {
//         locationImage.style.backgroundImage = `url('${location.imageUrl}')`;
//     } else {
//         // Create placeholder based on location name
//         const name = location?.name ? location.name.replace(/ /g, '+') : 'Unknown';
//         locationImage.style.backgroundImage = 
//             `url('https://via.placeholder.com/300x200?text=${name}')`;
//     }

//     // Only proceed if location exists
//     if (!location) {
//         console.error("No location data provided");
//         return;
//     }
    
//     description.innerHTML = `
//         <h2>${location.name}</h2>
//         <p>${location.description}</p>
//         <div class="location-features">
//             <h4>Features:</h4>
//             <ul>
//                 ${location.features.map(f => `<li>${f}</li>`).join('')}
//             </ul>
//         </div>
//         <div class="location-services">
//             <h4>Services:</h4>
//             <ul>
//                 ${location.services.map(s => `<li>${s}</li>`).join('')}
//             </ul>
//         </div>
//     `;
// }

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