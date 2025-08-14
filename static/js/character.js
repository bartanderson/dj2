# static\js\character.js
class CharacterCreator {
    constructor() {
        this.currentStep = 0;
        this.steps = [
            {
                title: "Race Selection",
                content: `
                    <h3>Choose Your Race</h3>
                    <p>Your race determines your physical characteristics and innate abilities.</p>
                    <div class="option-grid" id="race-options">
                        <div class="option-card" data-race="human">
                            <h4>Human</h4>
                            <p>Adaptable and versatile</p>
                        </div>
                        <div class="option-card" data-race="elf">
                            <h4>Elf</h4>
                            <p>Graceful and long-lived</p>
                        </div>
                        <div class="option-card" data-race="dwarf">
                            <h4>Dwarf</h4>
                            <p>Resilient and strong</p>
                        </div>
                        <div class="option-card" data-race="halfling">
                            <h4>Halfling</h4>
                            <p>Lucky and nimble</p>
                        </div>
                        <div class="option-card" data-race="dragonborn">
                            <h4>Dragonborn</h4>
                            <p>Draconic ancestry</p>
                        </div>
                        <div class="option-card" data-race="tiefling">
                            <h4>Tiefling</h4>
                            <p>Infernal heritage</p>
                        </div>
                    </div>
                `,
                guidance: "Consider how your race complements your intended play style. Humans are versatile, elves are perceptive, dwarves are sturdy."
            },
            {
                title: "Class Selection",
                content: `
                    <h3>Choose Your Class</h3>
                    <p>Your class defines your profession and core abilities.</p>
                    <div class="option-grid" id="class-options">
                        <div class="option-card" data-class="fighter">
                            <h4>Fighter</h4>
                            <p>Master of combat</p>
                        </div>
                        <div class="option-card" data-class="wizard">
                            <h4>Wizard</h4>
                            <p>Arcane spellcaster</p>
                        </div>
                        <div class="option-card" data-class="rogue">
                            <h4>Rogue</h4>
                            <p>Stealth and cunning</p>
                        </div>
                        <div class="option-card" data-class="cleric">
                            <h4>Cleric</h4>
                            <p>Divine magic wielder</p>
                        </div>
                        <div class="option-card" data-class="ranger">
                            <h4>Ranger</h4>
                            <p>Wilderness expert</p>
                        </div>
                        <div class="option-card" data-class="bard">
                            <h4>Bard</h4>
                            <p>Charismatic performer</p>
                        </div>
                    </div>
                `,
                guidance: "Your class determines your primary role in the party. Fighters excel in combat, wizards control magic, rogues specialize in stealth."
            },
            {
                title: "Background",
                content: `
                    <h3>Choose Your Background</h3>
                    <p>Your background shapes your history and skills.</p>
                    <div class="option-grid" id="background-options">
                        <div class="option-card" data-background="acolyte">
                            <h4>Acolyte</h4>
                            <p>Religious service</p>
                        </div>
                        <div class="option-card" data-background="noble">
                            <h4>Noble</h4>
                            <p>Privileged upbringing</p>
                        </div>
                        <div class="option-card" data-background="sage">
                            <h4>Sage</h4>
                            <p>Scholar and researcher</p>
                        </div>
                        <div class="option-card" data-background="criminal">
                            <h4>Criminal</h4>
                            <p>Underworld connections</p>
                        </div>
                        <div class="option-card" data-background="folk-hero">
                            <h4>Folk Hero</h4>
                            <p>Champion of common people</p>
                        </div>
                        <div class="option-card" data-background="soldier">
                            <h4>Soldier</h4>
                            <p>Military experience</p>
                        </div>
                    </div>
                `,
                guidance: "Your background provides context for your character's history. Choose one that complements your race and class."
            },
            {
                title: "Personality & Motivation",
                content: `
                    <h3>Define Your Character</h3>
                    <p>What drives your character? How do they interact with the world?</p>
                    
                    <div class="form-group">
                        <label>Personality Traits</label>
                        <textarea id="personality-traits" placeholder="Describe your character's personality"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Ideals</label>
                        <textarea id="character-ideals" placeholder="What principles guide your character?"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Bonds</label>
                        <textarea id="character-bonds" placeholder="What connections are important to your character?"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Flaws</label>
                        <textarea id="character-flaws" placeholder="What weaknesses does your character have?"></textarea>
                    </div>
                `,
                guidance: "These elements make your character unique. Consider how your traits will influence roleplaying decisions."
            }
        ];
        this.characterData = {};
    }

    init() {
        this.modal = document.getElementById('character-modal');
        this.stepsContainer = document.getElementById('creation-steps');
        this.prevBtn = document.getElementById('prev-step');
        this.nextBtn = document.getElementById('next-step');
        this.finishBtn = document.getElementById('finish-creation');
        
        this.prevBtn.addEventListener('click', () => this.prevStep());
        this.nextBtn.addEventListener('click', () => this.nextStep());
        this.finishBtn.addEventListener('click', () => this.completeCharacter());
        
        document.querySelector('.close').addEventListener('click', () => {
            this.modal.classList.add('hidden');
        });
    }

    open() {
        this.currentStep = 0;
        this.characterData = {};
        this.renderStep(0);
        this.modal.classList.remove('hidden');
    }

    renderStep(stepIndex) {
        this.stepsContainer.innerHTML = `
            <div class="step-guidance">
                <p>${this.steps[stepIndex].guidance}</p>
            </div>
            <div class="creation-step active">
                <h3>${this.steps[stepIndex].title}</h3>
                ${this.steps[stepIndex].content}
            </div>
        `;
        
        // Add event listeners for option cards
        if (stepIndex === 0) {
            document.querySelectorAll('#race-options .option-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    document.querySelectorAll('#race-options .option-card').forEach(c => {
                        c.classList.remove('selected');
                    });
                    card.classList.add('selected');
                    this.characterData.race = card.dataset.race;
                });
            });
        } else if (stepIndex === 1) {
            document.querySelectorAll('#class-options .option-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    document.querySelectorAll('#class-options .option-card').forEach(c => {
                        c.classList.remove('selected');
                    });
                    card.classList.add('selected');
                    this.characterData.class = card.dataset.class;
                });
            });
        } else if (stepIndex === 2) {
            document.querySelectorAll('#background-options .option-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    document.querySelectorAll('#background-options .option-card').forEach(c => {
                        c.classList.remove('selected');
                    });
                    card.classList.add('selected');
                    this.characterData.background = card.dataset.background;
                });
            });
        }
        
        // Update navigation buttons
        this.prevBtn.disabled = stepIndex === 0;
        this.nextBtn.classList.toggle('hidden', stepIndex === this.steps.length - 1);
        this.finishBtn.classList.toggle('hidden', stepIndex !== this.steps.length - 1);
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.renderStep(this.currentStep);
        }
    }

    nextStep() {
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.renderStep(this.currentStep);
        }
    }

    completeCharacter() {
        // Save text-based fields
        this.characterData.personality = document.getElementById('personality-traits').value;
        this.characterData.ideals = document.getElementById('character-ideals').value;
        this.characterData.bonds = document.getElementById('character-bonds').value;
        this.characterData.flaws = document.getElementById('character-flaws').value;
        
        // Save character to server
        fetch('/api/create-character', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(this.characterData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.modal.classList.add('hidden');
                // Add character to party UI
                this.addCharacterToParty(data.character);
            }
        });
    }

    addCharacterToParty(character) {
        const partyContainer = document.getElementById('party-members');
        const characterCard = document.createElement('div');
        characterCard.className = 'character-card';
        characterCard.innerHTML = `
            <div class="character-avatar" style="background-image: url('${character.avatar}')"></div>
            <div class="character-info">
                <h4>${character.name}</h4>
                <p>${character.race} ${character.class}</p>
                <p>${character.background}</p>
            </div>
        `;
        partyContainer.appendChild(characterCard);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.characterCreator = new CharacterCreator();
    characterCreator.init();
    
    // Open character creation when button clicked
    document.getElementById('create-character').addEventListener('click', () => {
        characterCreator.open();
    });
});