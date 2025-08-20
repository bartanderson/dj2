// static\js\inventory.js
function updateInventory(inventoryData) {
    const container = document.getElementById('inventory-container');
    container.innerHTML = `
        <div class="narrative-description">
            <p>${inventoryData.description}</p>
            <p class="inventory-stats">
                Carrying: ${inventoryData.weight} ${inventoryData.campaign_rules.weight_units} | 
                Currency: ${inventoryData.currency} ${inventoryData.campaign_rules.currency}
            </p>
        </div>
        <div class="significant-items">
            <h3>Notable Items</h3>
            ${inventoryData.significant_items.map(item => `
                <div class="significant-item" data-item="${item.name}">
                    <h4>${item.name}</h4>
                    <p>${item.description}</p>
                    ${item.significance ? `<p class="significance">${item.significance}</p>` : ''}
                </div>
            `).join('')}
        </div>
    `;
    
    // Add item interaction
    document.querySelectorAll('.significant-item').forEach(item => {
        item.addEventListener('click', () => {
            showItemOptions(item.dataset.item);
        });
    });
}

function showItemOptions(itemName) {
    const actionOptions = [
        "Describe in detail",
        "Use creatively",
        "Trade or gift",
        "Examine closely",
        "Store for later"
    ];
    
    const dmInput = document.getElementById('dm-chat-input');
    dmInput.value = `What can I do with my ${itemName}?`;
    
    // Show options in chat UI
    const optionsHtml = actionOptions.map(option => 
        `<button class="inventory-option">${option}</button>`
    ).join('');
    
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML += `
        <div class="inventory-options">
            <p>Choose how to interact with ${itemName}:</p>
            <div class="option-grid">${optionsHtml}</div>
        </div>
    `;
    
    // Add option handlers
    document.querySelectorAll('.inventory-option').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.textContent;
            handleInventoryAction(itemName, action);
        });
    });
}

function handleInventoryAction(itemName, action) {
    // Send to AI DM for narrative resolution
    const message = `[Inventory Action] ${action} ${itemName}`;
    document.getElementById('dm-chat-input').value = message;
    document.querySelector('#send-chat').click();
}