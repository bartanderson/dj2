# static\js\travel.js
class TravelUI {
    constructor() {
        this.travelInterface = document.getElementById('travel-interface');
        this.narrationElement = document.getElementById('travel-narration');
        this.imageElement = document.getElementById('travel-image');
        this.optionsElement = document.getElementById('travel-options');
        this.encounterElement = document.getElementById('encounter-options');
        this.progressElement = document.getElementById('travel-progress');
        this.titleElement = document.getElementById('travel-title');
        
        this.continueButton = document.getElementById('continue-journey');
        this.continueButton.addEventListener('click', () => this.progressJourney());
    }
    
    startJourney(destinationId) {
        fetch('/api/start-journey', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({destination_id: destinationId})
        })
        .then(response => response.json())
        .then(data => this.showNextSegment());
    }
    
    showNextSegment() {
        fetch('/api/travel-progress')
        .then(response => response.json())
        .then(data => {
            this.narrationElement.innerHTML = `<p>${data.narration}</p>`;
            
            if (data.encounter) {
                this.showEncounterOptions(data.encounter);
            } else {
                this.showTravelOptions();
            }
            
            this.progressElement.textContent = data.progress;
        });
    }
    
    showTravelOptions() {
        this.optionsElement.innerHTML = `
            <button id="continue-btn">Continue Journey</button>
            <button id="camp-btn">Make Camp</button>
            <button id="scout-btn">Scout Ahead</button>
        `;
        
        document.getElementById('continue-btn').onclick = () => this.showNextSegment();
    }
    
    showEncounterOptions(encounter) {
        let optionsHTML = '<div class="encounter-options">';
        encounter.options.forEach(option => {
            optionsHTML += `<button class="encounter-option">${option}</button>`;
        });
        optionsHTML += '</div>';
        
        this.optionsElement.innerHTML = optionsHTML;
        
        document.querySelectorAll('.encounter-option').forEach(btn => {
            btn.onclick = (e) => this.resolveEncounter(e.target.textContent);
        });
    }
    
    resolveEncounter(choice) {
        fetch('/api/resolve-encounter', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({choice: choice})
        })
        .then(response => response.json())
        .then(data => {
            this.narrationElement.innerHTML += `<div class="resolution">${data.result}</div>`;
            this.showTravelOptions();
        });
    }

    startJourney(destination) {
        // Hide main UI elements
        document.querySelector('.world-map').classList.add('hidden');
        document.querySelector('.location-panel').classList.add('hidden');
        document.querySelector('.character-manager').classList.add('hidden');
        
        // Show travel interface
        this.travelInterface.classList.remove('hidden');
        this.titleElement.textContent = `Journey to ${destination.name}`;
        
        // Initial narration
        this.narrationElement.innerHTML = `<p>Preparing to travel to ${destination.name}...</p>`;
        this.progressElement.textContent = 'Progress: 0/0';
        
        // Start journey
        this.progressJourney();
    }
    
    progressJourney() {
        fetch('/api/travel-progress')
            .then(response => response.json())
            .then(data => this.updateJourney(data));
    }
    
    updateJourney(data) {
        // Update narration
        this.narrationElement.innerHTML = `<p>${data.narration}</p>`;
        
        // Update image if available
        if (data.image_url) {
            this.imageElement.style.backgroundImage = `url('${data.image_url}')`;
        }
        
        // Update progress
        this.progressElement.textContent = `Progress: ${data.progress}`;
        
        // Handle encounters
        if (data.encounter) {
            this.showEncounter(data.encounter);
        } else {
            this.showTravelOptions(data.at_destination);
        }
    }
    
    showTravelOptions(atDestination) {
        this.encounterElement.classList.add('hidden');
        this.optionsElement.classList.remove('hidden');
        
        // Update button text based on journey status
        this.continueButton.textContent = atDestination ? 
            'Arrive at Destination' : 
            'Continue Journey';
    }
    
    showEncounter(encounter) {
        this.optionsElement.classList.add('hidden');
        this.encounterElement.classList.remove('hidden');
        
        // Clear previous options
        this.encounterElement.innerHTML = '';
        
        // Add new options
        encounter.options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option;
            button.addEventListener('click', () => this.resolveEncounter(option));
            this.encounterElement.appendChild(button);
        });
    }
    
    resolveEncounter(choice) {
        fetch('/api/resolve-encounter', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({choice: choice})
        })
        .then(response => response.json())
        .then(data => {
            // Add resolution to narration
            const resolution = document.createElement('div');
            resolution.className = 'resolution';
            resolution.innerHTML = `<p>${data.result}</p>`;
            this.narrationElement.appendChild(resolution);
            
            // Return to travel options
            this.showTravelOptions(false);
        });
    }
    
    endJourney() {
        // Show main UI elements
        document.querySelector('.world-map').classList.remove('hidden');
        document.querySelector('.location-panel').classList.remove('hidden');
        document.querySelector('.character-manager').classList.remove('hidden');
        
        // Hide travel interface
        this.travelInterface.classList.add('hidden');
    }
}
// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.travelUI = new TravelUI();
    
    // Hook up travel initiation to location clicks
    document.querySelectorAll('.location-marker').forEach(marker => {
        marker.addEventListener('click', () => {
            const locationId = marker.dataset.locationId;
            const location = getLocationData(locationId); // You'll need to implement this
            window.travelUI.startJourney(location);
        });
    });
});