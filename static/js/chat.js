# static\js\chat.js
class DMChat {
    constructor() {
        this.chatInput = document.getElementById('dm-chat-input');
        this.chatMessages = document.getElementById('chat-messages');
        this.sendButton = document.getElementById('send-chat');
        
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // Load narrative systems
        this.motivationTracker = new MotivationTracker();
        this.narrativeGuide = new NarrativeGuide();

        // Handle character card display
        this.chatMessages.addEventListener('click', (e) => {
            if (e.target.classList.contains('show-character-card')) {
                const characterData = JSON.parse(e.target.dataset.character);
                this.displayCharacterCard(characterData);
            }
        });
    }

    sendMessage() {
        console.log('sendMessage top')
        const message = this.chatInput.value.trim();
        if (message) {
            this.addMessage('player', message);
            this.chatInput.value = '';
            
            // Analyze player motivation
            const motivation = this.motivationTracker.analyzeAction(message);
            console.log(`Player motivation: ${motivation}`);
            
            // Get AI response
            this.getAIResponse(message, motivation);
        }
    }

    getAIResponse(message, motivation) {
        // Show loading indicator
        console.log("Sending message to DM:", message);
        const loadingMsg = this.addMessage('dm', "DM is thinking...");
        
        fetch('/api/dm-response', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message})
        })
        .then(response => response.json())
        .then(data => {
            console.log("Received DM response:", data);
            // Remove loading message
            loadingMsg.remove();
            
            // Add all responses
            data.responses.forEach(response => {
                this.addMessage(response.speaker, response.content);
            });
            
            // Update dialog history display
            this.updateDialogHistory(data.dialog_history);
        }).catch(error => {
            console.error("DM request failed:", error);
        });
    }
    
    updateDialogHistory(history) {
        const historyContainer = document.getElementById('dialog-history');
        if (!historyContainer) return;
        
        historyContainer.innerHTML = '';
        history.forEach(entry => {
            const entryDiv = document.createElement('div');
            entryDiv.className = 'dialog-entry';
            entryDiv.textContent = entry;
            historyContainer.appendChild(entryDiv);
        });
    }

    addMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        // Handle character preview
        if (text.startsWith('PREVIEW_CHARACTER:')) {
            const characterData = JSON.parse(text.split('PREVIEW_CHARACTER:')[1]);
            messageDiv.innerHTML = `
                <div class="character-preview">
                    <h4>${characterData.name}</h4>
                    <p>${characterData.race} ${characterData.class}</p>
                    <div class="preview-traits">
                        <p><strong>Personality:</strong> ${characterData.personality}</p>
                        <p><strong>Ideals:</strong> ${characterData.ideals}</p>
                    </div>
                    <button class="edit-character" data-step="personality">Edit Personality</button>
                    <button class="edit-character" data-step="ideals">Edit Ideals</button>
                    <button class="finalize-character">Finalize Character</button>
                </div>
            `;
        }
        // Handle finalized character
        else if (text.startsWith('FINAL_CHARACTER:')) {
            const characterData = JSON.parse(text.split('FINAL_CHARACTER:')[1]);
            messageDiv.innerHTML = `
                <div class="character-final">
                    <h3>${characterData.name} is Ready!</h3>
                    <p>${characterData.race} ${characterData.class}</p>
                    <button class="show-full-character" 
                            data-character='${JSON.stringify(characterData)}'>
                        View Character Sheet
                    </button>
                    <button class="add-to-party" data-id="${characterData.id}">
                        Add to Party
                    </button>
                </div>
            `;
        }
        else {
            messageDiv.innerHTML = `<p>${text}</p>`;
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        // Add event listeners
        if (text.includes('PREVIEW_CHARACTER')) {
            messageDiv.querySelector('.finalize-character').addEventListener('click', () => {
                this.sendMessage('finalize');
            });
            
            messageDiv.querySelectorAll('.edit-character').forEach(btn => {
                btn.addEventListener('click', () => {
                    const step = btn.dataset.step;
                    this.sendMessage(`edit ${step}`);
                });
            });
        }
        else if (text.includes('FINAL_CHARACTER')) {
            messageDiv.querySelector('.show-full-character').addEventListener('click', (e) => {
                const characterData = JSON.parse(e.target.dataset.character);
                this.displayCharacterCard(characterData);
            });
            
            messageDiv.querySelector('.add-to-party').addEventListener('click', (e) => {
                const characterData = JSON.parse(e.target.closest('.message').querySelector('.show-full-character').dataset.character);
                this.addCharacterToParty(characterData);
            });
        }

        if (text.includes('FINAL_CHARACTER')) {
            messageDiv.querySelector('.add-to-party').addEventListener('click', (e) => {
                const characterData = JSON.parse(e.target.dataset.character);
                this.addCharacterToParty(characterData);
            });
        }
        return messageDiv;
    }
    
    displayCharacterCard(characterData) {
        // Create character card
        const card = document.createElement('div');
        card.className = 'character-card-popup';
        card.innerHTML = `
            <div class="card-header">
                <h3>${characterData.name}</h3>
                <button class="close-card">&times;</button>
            </div>
            <div class="card-body">
                <div class="character-avatar" 
                     style="background-image: url('${characterData.avatar_url}')"></div>
                <div class="character-details">
                    <p><strong>Race:</strong> ${characterData.race}</p>
                    <p><strong>Class:</strong> ${characterData.class}</p>
                    <p><strong>Background:</strong> ${characterData.background}</p>
                    <p><strong>HP:</strong> ${characterData.hit_points}/${characterData.max_hp}</p>
                </div>
                <div class="character-traits">
                    <p><strong>Personality:</strong> ${characterData.personality}</p>
                    <p><strong>Ideals:</strong> ${characterData.ideals}</p>
                    <p><strong>Bonds:</strong> ${characterData.bonds}</p>
                    <p><strong>Flaws:</strong> ${characterData.flaws}</p>
                </div>
                <div class="abilities">
                    <h4>Abilities</h4>
                    <div class="ability-grid">
                        ${Object.entries(characterData.abilities).map(([ability, score]) => `
                            <div class="ability-score">
                                <div class="ability-name">${ability.substring(0, 3).toUpperCase()}</div>
                                <div class="ability-value">${score}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            <div class="card-footer">
                <button class="add-to-party" data-id="${characterData.id}">Add to Party</button>
            </div>
        `;
        
        // Add to DOM
        document.body.appendChild(card);
        
        // Event listeners
        card.querySelector('.close-card').addEventListener('click', () => card.remove());
        card.querySelector('.add-to-party').addEventListener('click', (e) => {
            this.addCharacterToParty(characterData);
            card.remove();
        });
    }
    
    addCharacterToParty(character) {
        // Add character to party UI
        const partyContainer = document.getElementById('party-members');
        const characterCard = document.createElement('div');
        characterCard.className = 'character-card';
        characterCard.innerHTML = `
            <div class="character-avatar" 
                 style="background-image: url('${character.avatar_url}')"></div>
            <div class="character-info">
                <h4>${character.name}</h4>
                <p>${character.race} ${character.class}</p>
                <p>Level ${character.level}</p>
                <div class="health-bar">
                    <div class="health-fill" 
                         style="width: ${(character.hit_points/character.max_hp)*100}%">
                        ${character.hit_points}/${character.max_hp} HP
                    </div>
                </div>
            </div>
        `;
        partyContainer.appendChild(characterCard);
        
        // Dispatch party updated event
        const event = new CustomEvent('party-updated', {
            detail: { size: partyContainer.children.length }
        });
        document.dispatchEvent(event);
    }
}