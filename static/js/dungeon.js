// static/js/dungeon.js

console.log("dungeon.js loaded");

let dungeonDebugMode = false;
// Global game ID for dungeon session
window.dungeonGameId = null;

async function switchToDungeon() {
    console.log("Entering dungeon...");

    const partyId = window.currentPartyId;
    const locationId = window.worldState?.currentLocation?.id;
    const activeParty = worldState.parties.find(p => p.id === partyId);
    
    if (!activeParty) {
        console.error("No active party found for partyId", partyId);
        addWorldMessage("You are not in a party.", 'error');
        return;
    }
    
    const characters = activeParty.members.map(charId => {
        const char = worldState.characters[charId];
        if (!char) return null;
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
    
    // Step 1: Tell world server we're entering
    const worldResponse = await fetch('/api/enter-dungeon', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            party_id: partyId,
            location_id: locationId,
            characters: characters
        })
    });
    const worldData = await worldResponse.json();
    if (!worldData.success) {
        addWorldMessage(worldData.message || "Cannot enter dungeon.");
        return;
    }
    
    // Step 2: Tell dungeon server to create party instance
    const partyData = {
        party_id: partyId,
        location_id: locationId,
        characters: characters,
        world_url: window.location.origin
    };
    
    const dungeonResponse = await fetch('http://localhost:5005/api/dungeon/enter', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(partyData)
    });
    const dungeonData = await dungeonResponse.json();
    if (!dungeonData.success) {
        addWorldMessage(dungeonData.message || "Failed to create dungeon instance.");
        return;
    }
    
    // Step 3: Set dungeonGameId and switch UI
    window.dungeonGameId = dungeonData.dungeon_id;
    
    // Switch mode
    await fetch('/api/engine/mode', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mode: 'dungeon'})
    });
    
    updateUIForMode('dungeon');
    addToChatLog(dungeonData.message || "Entered dungeon.", 'system');
    
    // Initialize dungeon display
    if (typeof refreshDungeonImage === 'function') refreshDungeonImage();
    if (typeof updateDungeonPosition === 'function') updateDungeonPosition();
}

function switchToWorld() {
    console.log("Exiting dungeon...");
    
    const partyId = window.currentPartyId;
    if (!partyId) {
        // No party, just switch UI
        fetch('/api/engine/mode', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: 'world'})
        }).then(() => updateUIForMode('world'));
        return;
    }
    
    // Step 1: Tell dungeon server we're exiting (whole party)
    fetch('http://localhost:5005/api/dungeon/exit', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            party_id: partyId,
            exiting_character_ids: [],
            all_characters: true
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            throw new Error(data.message || "Cannot exit dungeon");
        }
        
        // Step 2: Switch UI to world mode
        return fetch('/api/engine/mode', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: 'world'})
        }).then(() => data);
    })
    .then((data) => {
        updateUIForMode('world');
        addWorldMessage(data.message || "Returned to the world.");
        
        // Refresh world state to get updated characters
        if (typeof refreshWorldState === 'function') {
            refreshWorldState();
        }
    })
    .catch(error => {
        console.error("Exit dungeon error:", error);
        addWorldMessage(error.message);
        
        // Force exit UI anyway
        fetch('/api/engine/mode', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mode: 'world'})
        }).then(() => updateUIForMode('world'));
    });
}

function toggleDebug() {
    dungeonDebugMode = !dungeonDebugMode;
    const img = document.getElementById('dungeon-map');
    if (img && window.dungeonGameId) {
        const debug = dungeonDebugMode ? 'true' : 'false';
        img.src = `http://localhost:5005/dungeon-image?game_id=${window.dungeonGameId}&debug=${debug}&t=${Date.now()}`;
    }
    addToChatLog(`Debug mode ${dungeonDebugMode ? 'enabled' : 'disabled'}`, 'system');
}

function addToChatLog(text, sender = 'system') {
    const chat = document.getElementById('dungeon-chat');
    if (!chat) return;
    
    const div = document.createElement('div');
    div.style.marginBottom = '5px';
    div.style.padding = '5px';
    div.style.borderRadius = '3px';
    div.style.backgroundColor = 
        sender === 'user' ? 'rgba(78, 204, 163, 0.2)' :
        sender === 'DM' ? 'rgba(15, 52, 96, 0.3)' :
        'rgba(0,0,0,0.3)';
    
    div.innerHTML = `<strong>${sender}:</strong> ${text}`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function resetDungeon() {
    if (!window.dungeonGameId) return;
    
    fetch('http://localhost:5005/reset', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({game_id: window.dungeonGameId})
    })
    .then(r => r.json())
    .then(data => {
        addToChatLog(data.message || 'Dungeon reset', 'system');
        refreshDungeonImage();
        updateDungeonPosition();
    })
    .catch(err => {
        addToChatLog(`Error resetting dungeon: ${err}`, 'error');
    });
}

function updateDungeonPosition() {
    if (!window.dungeonGameId) return;
    
    fetch(`http://localhost:5005/position?game_id=${window.dungeonGameId}`)
    .then(r => r.json())
    .then(data => {
        if (data.position) {
            const [x, y] = data.position;
            document.getElementById('dungeon-position').textContent = `(${x}, ${y})`;
        } else if (data.error) {
            console.log("Position error:", data.error);
            document.getElementById('dungeon-position').textContent = `(?, ?)`;
        }
    })
    .catch(err => {
        console.log("Could not get position:", err);
        document.getElementById('dungeon-position').textContent = `(?, ?)`;
    });
}

function sendAICommand() {
    if (!window.dungeonGameId) return;
    
    const input = document.getElementById('dungeon-ai-command');
    const command = input.value.trim();
    if (!command) return;
    
    addToChatLog(`> ${command}`, 'user');
    input.value = '';
    
    fetch('http://localhost:5005/ai-command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            command: command,
            game_id: window.dungeonGameId
        })
    })
    .then(r => r.json())
    .then(data => {
        // Check if we need to exit the dungeon (stairs confirmation or explicit exit)
        if (data.refresh_map || data.exit_dungeon) {
            // Exit dungeon and return to world
            switchToWorld();
        } else if (data.success) {
            addToChatLog(`${data.message}`, 'ai');
            refreshDungeonImage();
            updateDungeonPosition();
        } else {
            addToChatLog(data.message || "Command failed.", 'error');
        }
    })
    .catch(error => {
        console.error("AI command error:", error);
        addToChatLog("Error communicating with dungeon server.", 'error');
    });
}

function addDungeonChat(text, sender = 'system') {
    const chat = document.getElementById('dungeon-chat');
    if (!chat) return;
    
    const div = document.createElement('div');
    div.style.marginBottom = '8px';
    div.style.padding = '6px';
    div.style.borderRadius = '4px';
    div.style.backgroundColor = 
        sender === 'user' ? 'rgba(78, 204, 163, 0.2)' :
        sender === 'ai' ? 'rgba(31, 31, 61, 0.8)' :
        sender === 'error' ? 'rgba(74, 26, 26, 0.8)' :
        'rgba(15, 52, 96, 0.4)';
    div.style.color = 
        sender === 'error' ? '#ff9999' :
        sender === 'user' ? '#4ecca3' :
        sender === 'ai' ? '#e6e6e6' :
        '#cccccc';
    
    const label = sender === 'ai' ? 'DM' : sender;   // display "DM" for AI
    div.innerHTML = `<strong>${sender}:</strong> ${text}`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function refreshDungeonImage() {
    const img = document.getElementById('dungeon-map');
    if (img && window.dungeonGameId) {
        const debug = dungeonDebugMode ? 'true' : 'false';
        img.src = `http://localhost:5005/dungeon-image?game_id=${window.dungeonGameId}&debug=${debug}&t=${Date.now()}`;
    }
}

function moveDungeon(direction) {
    if (!window.dungeonGameId) return;
    
    addToChatLog(`Moving ${direction}...`, 'user');
    
    fetch('http://localhost:5005/move', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            direction: direction, 
            steps: 1,
            game_id: window.dungeonGameId
        })
    })
    .then(r => r.json())
    .then(data => {
        addToChatLog(data.message || `Moved ${direction}`, 'system');
        refreshDungeonImage();
        updateDungeonPosition();
    });
}

function dungeonWait() {
    addDungeonOutput("You wait and observe...");
}

function sendDungeonCommand(text) {
    const command = text || document.getElementById('dungeon-command').value;
    if (!command) return;
    
    addDungeonOutput(`> ${command}`);
    document.getElementById('dungeon-command').value = '';
    
    fetch('/api/dungeon/command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: command})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success && data.result) {
            if (data.result.message) {
                addDungeonOutput(data.result.message);
            }
            if (data.result.position) {
                addDungeonOutput(`Position: (${data.result.position[0]}, ${data.result.position[1]})`);
            }
            
            // Add this: Refresh dungeon image after successful command
            const dungeonMap = document.getElementById('dungeon-map');
            if (dungeonMap) {
                dungeonMap.src = `http://localhost:5005/dungeon-image?t=${Date.now()}`;
            }
        }
    });
}

function addDungeonOutput(text) {
    const output = document.getElementById('dungeon-output');
    const div = document.createElement('div');
    div.textContent = text;
    output.appendChild(div);
    output.scrollTop = output.scrollHeight;
}