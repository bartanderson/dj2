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
    }

    sendMessage() {
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
        const loadingMsg = this.addMessage('dm', "DM is thinking...");
        
        fetch('/api/dm-response', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message})
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading message
            loadingMsg.remove();
            
            // Add all responses
            data.responses.forEach(response => {
                this.addMessage(response.speaker, response.content);
            });
            
            // Update dialog history display
            this.updateDialogHistory(data.dialog_history);
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
        messageDiv.innerHTML = `<p>${text}</p>`;
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        return messageDiv;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new DMChat();
});