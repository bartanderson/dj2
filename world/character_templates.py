# world/character_templates.py
"""
Topic templates for conversational character creation.

These are NOT a checklist. They are a DM's prep notes: prompts to draw from,
signals to listen for, and clarifications to offer if the answer is vague.

The CharacterAgent passes these to the LLM. The LLM decides which topics to
weave in based on what the player is actually saying.
"""

CHARACTER_CREATION_TOPICS = [
    {
        "topic": "identity",
        "essential": True,
        "maps_to": ["name"],
        "prompts": [
            "What should I call you?",
            "Who are you, traveler?",
            "By what name will songs be written about you?",
            "What do your friends call you?",
        ],
        "listen_for": (
            "A name or a moniker. Could be formal (Lord Edric), simple (Sara), "
            "descriptive (the Grey Wanderer), or foreign. Treat any proper noun as a candidate."
        ),
        "clarify_if": (
            "The player gives only a title or description ('the Grey Wanderer'). "
            "Ask warmly: 'And what name lives behind the title?'"
        ),
    },
    {
        "topic": "origin",
        "essential": True,
        "maps_to": ["race", "world_region"],
        "prompts": [
            "Where are you from?",
            "What lands shaped you?",
            "Tell me about the place you call home.",
            "Who raised you, and where?",
            "What do you miss most about where you grew up?",
        ],
        "listen_for": (
            "Homeland descriptions, cultures, climates, people. "
            "Mountains and stone → dwarf-leaning; forests and old songs → elf-leaning; "
            "cities, ports, or trade → human or halfling; bloodlines or bargains → tiefling or similar."
        ),
        "clarify_if": (
            "The description fits multiple races. Offer 2-3 concrete options that match what "
            "the player described: 'The Iron Peaks are home to both mountain dwarves and human "
            "highlanders — which fits your character better?'"
        ),
    },
    {
        "topic": "vocation",
        "essential": True,
        "maps_to": ["class"],
        "prompts": [
            "What did you spend your years learning?",
            "When trouble finds you, what do you do?",
            "What is your weapon, or your art?",
            "Who trained you?",
            "What do you do that others cannot?",
        ],
        "listen_for": (
            "Words about combat style, training, faith, magic, stealth, scholarship, "
            "or wilderness. Fighting with steel → fighter/barbarian/paladin; "
            "sneaking and striking → rogue; books and magic → wizard/warlock; "
            "healing or nature → cleric/druid/ranger; songs → bard."
        ),
        "clarify_if": (
            "The description is broad. Offer 2-3 classes: 'A sellsword could be a fighter, "
            "a rogue, or a ranger depending on how they fight — which sounds more like you?'"
        ),
    },
    {
        "topic": "past",
        "essential": True,
        "maps_to": ["background"],
        "prompts": [
            "What did you do before the call to adventure?",
            "What is the thing you carry with you from your past?",
            "How did you earn your living?",
            "Who taught you what you know?",
        ],
        "listen_for": (
            "Jobs, roles, social positions, formative events. "
            "Soldier, acolyte, sage, criminal, urchin, noble, folk hero, hermit, "
            "artisan, merchant, sailor."
        ),
        "clarify_if": (
            "The answer is emotional, not occupational. Draw out the practical: "
            "'That sounds like a hard road. What did you do to survive it?'"
        ),
    },
    {
        "topic": "motivation",
        "essential": False,
        "maps_to": ["ideals", "bonds"],
        "prompts": [
            "What are you chasing, or running from?",
            "Why did you leave home?",
            "What would you not turn your back on?",
            "Who would you die for?",
        ],
        "listen_for": (
            "Emotional stakes, obligations, debts, oaths. These map to ideals (justice, freedom, "
            "power, knowledge) and bonds (family, order, a place, a person, a promise)."
        ),
        "clarify_if": (
            "The player gives an abstraction ('I want power'). Ask a concrete follow-up: "
            "'Power over what, and for whom?'"
        ),
    },
    {
        "topic": "strengths",
        "essential": True,
        "maps_to": ["abilities", "skills"],
        "prompts": [
            "When the fight comes, what do you rely on?",
            "What are you good at?",
            "Where are you weak?",
            "What do people notice first about you?",
        ],
        "listen_for": (
            "Physical description, mental aptitude, social manner. "
            "Big and strong → STR; quick and precise → DEX; hardy → CON; "
            "shrewd or learned → INT; perceptive or wise → WIS; charming → CHA. "
            "Skills follow from the same clues: climbing → Athletics, sneaking → Stealth, "
            "talking → Persuasion, remembering → History."
        ),
        "clarify_if": (
            "The player gives only narrative clues. Interpret what you can, then ask: "
            "'It sounds like you're strong and sturdy. Would you say you're more a brawler "
            "or a careful fighter?'"
        ),
    },
    {
        "topic": "appearance",
        "essential": False,
        "maps_to": ["description"],
        "prompts": [
            "What do others see when they look at you?",
            "Any scars, marks, or oddities?",
            "How do you carry yourself?",
        ],
        "listen_for": (
            "Physical description, mannerisms, dress, distinctive features. Optional — "
            "don't force this if the player is focused elsewhere."
        ),
        "clarify_if": None,
    },
    {
        "topic": "quirks",
        "essential": False,
        "maps_to": ["flaws", "personality"],
        "prompts": [
            "What gets under your skin?",
            "What is your worst habit?",
            "What do people misjudge about you?",
        ],
        "listen_for": (
            "Flaws, vices, fears, contradictions. Optional flavor."
        ),
        "clarify_if": None,
    },
]


def render_templates_for_prompt():
    """Renders the topic templates as a readable block for the LLM prompt."""
    lines = []
    for t in CHARACTER_CREATION_TOPICS:
        tag = "ESSENTIAL" if t["essential"] else "optional"
        lines.append(f"### Topic: {t['topic']} ({tag})")
        lines.append(f"Fills: {', '.join(t['maps_to'])}")
        lines.append("Prompt variations you can adapt (do not use verbatim necessarily):")
        for p in t["prompts"]:
            lines.append(f"  - {p}")
        lines.append(f"Listen for: {t['listen_for']}")
        if t.get("clarify_if"):
            lines.append(f"If unclear: {t['clarify_if']}")
        lines.append("")
    return "\n".join(lines)