// static/js/dungeon.js

// TODO: Remove generateTerrainImage() and related calls once backend terrain is fully working
// TODO: Add travel modal/list of discovered locations for fast travel
// TODO: Add inventory UI panel and equipment slots

console.log("dungeon.js loaded");

let dungeonDebugMode = false;
window.dungeonGameId = null;

// ===== HELPER: Initialize dungeon display =====
function initDungeonDisplay() {
    refreshDungeonImage();
    updateDungeonPosition();
    addToChatLog("You are in the dungeon.", 'DM');
}

// ===== INTEGRATED MODE (via sessionStorage) =====
function enterIntegratedMode(partyId, locationId, worldUrl) {
    window.currentPartyId = partyId;
    window.currentWorldUrl = worldUrl || 'http://localhost:5000';
    fetch('/api/dungeon/enter', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            party_id: partyId,
            location_id: locationId,
            world_url: worldUrl
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.dungeonGameId = data.dungeon_id;
            initDungeonDisplay();
        } else {
            alert("Failed to enter dungeon: " + data.message);
            window.location.href = worldUrl;
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error entering dungeon");
        window.location.href = worldUrl;
    });
}

// ===== STANDALONE MODE (create new game) =====
function enterStandaloneMode(gameIdFromUrl) {
    let gameId = gameIdFromUrl;
    if (!gameId) {
        gameId = 'standalone_' + Date.now();
    }
    window.dungeonGameId = gameId;

    // Create new dungeon game via the server
    fetch('/api/new-game', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ game_id: gameId })
    })
    .then(r => r.json())
    .then(data => {
        if (data.created || data.exists) {
            initDungeonDisplay();
        } else {
            alert("Failed to create dungeon");
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error creating dungeon");
    });
}

// ===== MAIN INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    console.log("Full URL:", window.location.href);
    console.log("URL params:", window.location.search);
    const urlParams = new URLSearchParams(window.location.search);
    const partyId = urlParams.get('party_id');
    const locationId = urlParams.get('location_id');
    const worldUrl = urlParams.get('world_url');
    if (partyId && locationId) {
        // Integrated mode
        enterIntegratedMode(partyId, locationId, worldUrl || 'http://localhost:5000');
    } else {
        // Standalone mode: check URL for game_id
        const urlParams = new URLSearchParams(window.location.search);
        const gameId = urlParams.get('game_id');
        enterStandaloneMode(gameId);
    }
});

// ===== EXIT FUNCTION =====
function exitDungeon() {
    console.log("exitDungeon called, partyId=", window.currentPartyId, "worldUrl=", window.currentWorldUrl);
    if (!window.currentPartyId) {
        console.error("No party ID available");
        return;
    }
    fetch('/api/dungeon/exit', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ party_id: window.currentPartyId, all_characters: true })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            window.location.href = window.currentWorldUrl;
        } else {
            alert("Failed to exit dungeon: " + data.message);
        }
    })
    .catch(err => {
        console.error(err);
        alert("Error exiting dungeon");
    });
}

// ===== UI FUNCTIONS =====
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

    // Set text color to light gray/white for all messages
    div.style.color = '#f0f0f0';    
    const label = sender === 'DM' ? 'DM' : sender;
    div.innerHTML = `<strong>${label}:</strong> ${text}`;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function refreshDungeonImage() {
    const img = document.getElementById('dungeon-map');
    if (img && window.dungeonGameId) {
        const debug = dungeonDebugMode ? 'true' : 'false';
        img.src = `/dungeon-image?game_id=${window.dungeonGameId}&debug=${debug}&t=${Date.now()}`;
    }
}

function updateDungeonPosition() {
    if (!window.dungeonGameId) return;
    
    fetch(`/position?game_id=${window.dungeonGameId}`)
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

function moveDungeon(direction) {
    if (!window.dungeonGameId) return;
    // Instead of calling /move directly, use the AI command
    // Set the AI command input value and call sendAICommand
    const input = document.getElementById('dungeon-ai-command');
    input.value = direction;
    sendAICommand();
}

function sendAICommand() {
    if (!window.dungeonGameId) return;
    
    const input = document.getElementById('dungeon-ai-command');
    const command = input.value.trim();
    if (!command) return;
    
    addToChatLog(`> ${command}`, 'user');
    input.value = '';
    
    fetch('/ai-command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            command: command,
            game_id: window.dungeonGameId
        })
    })
    .then(r => r.json())
    .then(data => {
        console.log("AI response data:", data);
        if (data.exit_dungeon) {
            console.log("Exit dungeon flag received, calling exitDungeon()");
            exitDungeon();
        } else if (data.success) {
            addToChatLog(data.message, 'DM');
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

function toggleDebug() {
    dungeonDebugMode = !dungeonDebugMode;
    refreshDungeonImage();
    addToChatLog(`Debug mode ${dungeonDebugMode ? 'enabled' : 'disabled'}`, 'system');
}

function resetDungeon() {
    if (!window.dungeonGameId) return;
    
    fetch('/reset', {
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