"""
Character archetype definitions derived from the actual game system.

Classes: Warrior, Rogue, Mage, Priest, Ranger, Bard, Monk, Warlock
Races:   Human, Dwarf, Elf, Halfling, Orc, Goblin, Troll-blooded, Construct, Fae-touched
Monsters: drawn directly from og_system/06_monsters.json

NPC archetypes are setting roles (innkeeper, guard, etc.) — they can be any race,
so they default to human but the generator can be asked for variants.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Archetype:
    id: str
    label: str
    char_type: str              # "player", "npc", "enemy", "creature"
    role: str                   # class, monster id, or npc role
    gender: str                 # "male", "female", "ambiguous"
    body: str                   # "average", "stout", "lean", "broad", "slight", "massive", "small"
    age: str                    # "young", "middle", "elder", "ageless"
    tags: List[str]
    base_prompt: str
    style_suffix: str = (
        "fantasy art, Rembrandt lighting, detailed, painted portrait style, "
        "dark fantasy, oil painting aesthetic"
    )
    negative_prompt: str = (
        "ugly, deformed, blurry, watermark, text, cartoon, anime, "
        "extra limbs, bad anatomy, modern clothing"
    )
    variants: List[str] = field(default_factory=lambda: [
        "neutral", "friendly", "suspicious", "wounded", "fearful"
    ])


# ---------------------------------------------------------------------------
# Player Character Class Archetypes
# One representative per class — generator can cross with race later
# ---------------------------------------------------------------------------

CLASS_ARCHETYPES = [
    Archetype(
        id="warrior_human_male",
        label="Warrior (human male)",
        char_type="player",
        role="warrior",
        gender="male",
        body="broad",
        age="middle",
        tags=["warrior", "fighter", "human", "male", "armor"],
        base_prompt=(
            "broad-shouldered human warrior, chainmail and shield, battle-worn face, "
            "short dark hair, strong jaw, determined eyes, sword at belt"
        ),
        variants=["neutral", "battle-ready", "wounded", "victorious", "grim"],
    ),
    Archetype(
        id="warrior_dwarf_female",
        label="Warrior (dwarf female)",
        char_type="player",
        role="warrior",
        gender="female",
        body="stout",
        age="middle",
        tags=["warrior", "dwarf", "female", "armor"],
        base_prompt=(
            "stout dwarven woman warrior, intricately braided red hair with iron rings, "
            "heavy armor, axe, fierce proud expression, short but imposing"
        ),
        variants=["neutral", "battle-ready", "wounded", "proud", "grim"],
    ),
    Archetype(
        id="rogue_elf_female",
        label="Rogue (elf female)",
        char_type="player",
        role="rogue",
        gender="female",
        body="slight",
        age="young",
        tags=["rogue", "elf", "female", "leather", "archer"],
        base_prompt=(
            "lithe elven woman rogue, dark leather armor, hood partially down, "
            "silver hair, sharp pointed ears, clever calculating eyes, bow slung over shoulder"
        ),
        variants=["neutral", "alert", "sneaking", "wounded", "smirking"],
    ),
    Archetype(
        id="rogue_goblin_ambiguous",
        label="Rogue (goblin)",
        char_type="player",
        role="rogue",
        gender="ambiguous",
        body="small",
        age="young",
        tags=["rogue", "goblin", "small", "nimble"],
        base_prompt=(
            "goblin rogue, small wiry frame, green-grey skin, large amber eyes, "
            "patchwork leather armor, mismatched daggers, quick grin, urban alley background"
        ),
        variants=["neutral", "alert", "sneaking", "wounded", "mischievous"],
    ),
    Archetype(
        id="mage_human_female",
        label="Mage (human female)",
        char_type="player",
        role="mage",
        gender="female",
        body="lean",
        age="young",
        tags=["mage", "wizard", "human", "female", "robes", "spellcaster"],
        base_prompt=(
            "young human woman mage, dark robes with arcane sigils, intense intelligent eyes, "
            "dark hair with a silver streak, staff topped with glowing crystal, "
            "ink-stained fingers, spellbook tucked under arm"
        ),
        variants=["neutral", "casting", "focused", "exhausted", "triumphant"],
    ),
    Archetype(
        id="mage_construct",
        label="Mage (construct)",
        char_type="player",
        role="mage",
        gender="ambiguous",
        body="average",
        age="ageless",
        tags=["mage", "construct", "artificial", "arcane"],
        base_prompt=(
            "construct mage, humanoid form of animated brass and iron, "
            "glowing arcane runes etched into metal body, glass eye-lenses glowing blue, "
            "robes draped over mechanical frame, staff in metal hand"
        ),
        variants=["neutral", "casting", "processing", "damaged", "awakened"],
    ),
    Archetype(
        id="priest_human_male",
        label="Priest (human male)",
        char_type="player",
        role="priest",
        gender="male",
        body="average",
        age="elder",
        tags=["priest", "cleric", "divine", "human", "male"],
        base_prompt=(
            "weathered human priest, medium armor with holy symbol on chest, "
            "grey temples, kind deep-set eyes, mace at belt, simple robes over armor, "
            "candlelit temple background"
        ),
        variants=["neutral", "praying", "healing", "commanding", "wounded"],
    ),
    Archetype(
        id="ranger_elf_male",
        label="Ranger (elf male)",
        char_type="player",
        role="ranger",
        gender="male",
        body="lean",
        age="young",
        tags=["ranger", "elf", "male", "bow", "forest"],
        base_prompt=(
            "lean elven ranger, muted green-brown leather armor, long bow, "
            "sharp ears, golden eyes, light brown hair tied back, "
            "animal companion hint at edge of frame, forest background"
        ),
        variants=["neutral", "tracking", "alert", "wounded", "focused"],
    ),
    Archetype(
        id="bard_halfling_female",
        label="Bard (halfling female)",
        char_type="player",
        role="bard",
        gender="female",
        body="slight",
        age="young",
        tags=["bard", "halfling", "female", "performer", "small"],
        base_prompt=(
            "small halfling woman bard, colorful slightly worn clothes, "
            "lute strapped to back, curly auburn hair, bright mischievous eyes, "
            "warm confident smile, tavern stage background"
        ),
        variants=["neutral", "performing", "charming", "cunning", "frightened"],
    ),
    Archetype(
        id="monk_human_ambiguous",
        label="Monk (human)",
        char_type="player",
        role="monk",
        gender="ambiguous",
        body="lean",
        age="middle",
        tags=["monk", "human", "unarmed", "ki"],
        base_prompt=(
            "lean human monk, simple worn robes, shaved head, calm meditative expression, "
            "bare feet, hands slightly raised in fighting stance, monastery background"
        ),
        variants=["neutral", "meditating", "fighting stance", "wounded", "focused"],
    ),
    Archetype(
        id="warlock_faetouched_female",
        label="Warlock (fae-touched female)",
        char_type="player",
        role="warlock",
        gender="female",
        body="slight",
        age="young",
        tags=["warlock", "fae-touched", "female", "pact", "arcane"],
        base_prompt=(
            "fae-touched woman warlock, pale ethereal skin, violet eyes with no whites, "
            "dark clothing with subtle silver patterns, eldritch symbol glowing on palm, "
            "unsettling beauty, patron's influence visible as faint shimmer"
        ),
        variants=["neutral", "casting", "bargaining", "corrupted", "triumphant"],
    ),
    Archetype(
        id="warlock_trollblooded_male",
        label="Warlock (troll-blooded male)",
        char_type="player",
        role="warlock",
        gender="male",
        body="broad",
        age="middle",
        tags=["warlock", "troll-blooded", "male", "monstrous"],
        base_prompt=(
            "massive troll-blooded man warlock, grey-green mottled skin, "
            "clawed hands with eldritch runes carved into them, heavy brow, "
            "small yellow eyes, dark odd clothing, unnerving regenerating wounds"
        ),
        variants=["neutral", "casting", "raging", "wounded healing", "intimidating"],
    ),
]

# ---------------------------------------------------------------------------
# NPC Setting Archetypes (setting roles, race-agnostic)
# ---------------------------------------------------------------------------

NPC_ARCHETYPES = [
    Archetype(
        id="innkeeper_female",
        label="Innkeeper (female)",
        char_type="npc",
        role="innkeeper",
        gender="female",
        body="stout",
        age="middle",
        tags=["innkeeper", "female", "tavern", "friendly"],
        base_prompt=(
            "stout middle-aged woman innkeeper, warm smile, apron, simple dress, "
            "hair pulled back, rosy cheeks, kind tired eyes, tavern background"
        ),
    ),
    Archetype(
        id="innkeeper_male",
        label="Innkeeper (male)",
        char_type="npc",
        role="innkeeper",
        gender="male",
        body="broad",
        age="middle",
        tags=["innkeeper", "male", "tavern"],
        base_prompt=(
            "broad middle-aged man innkeeper, bald, thick beard, "
            "leather apron, rolled sleeves, tavern background"
        ),
    ),
    Archetype(
        id="merchant_male",
        label="Merchant (male)",
        char_type="npc",
        role="merchant",
        gender="male",
        body="lean",
        age="middle",
        tags=["merchant", "male", "shopkeeper", "trader"],
        base_prompt=(
            "lean middle-aged merchant, fine but worn traveling clothes, "
            "calculating eyes, thin beard, coin purse at belt"
        ),
    ),
    Archetype(
        id="merchant_female",
        label="Merchant (female)",
        char_type="npc",
        role="merchant",
        gender="female",
        body="slight",
        age="young",
        tags=["merchant", "female", "shopkeeper"],
        base_prompt=(
            "slight young woman merchant, sharp intelligent eyes, practical clothing, "
            "rings on fingers, market stall background"
        ),
    ),
    Archetype(
        id="blacksmith",
        label="Blacksmith",
        char_type="npc",
        role="blacksmith",
        gender="ambiguous",
        body="broad",
        age="middle",
        tags=["blacksmith", "craftsman", "forge"],
        base_prompt=(
            "massive broad-shouldered blacksmith, soot-stained face, "
            "leather apron with burn marks, muscular arms, forge background"
        ),
    ),
    Archetype(
        id="town_guard",
        label="Town Guard",
        char_type="npc",
        role="guard",
        gender="ambiguous",
        body="average",
        age="young",
        tags=["guard", "soldier", "authority"],
        base_prompt=(
            "town guard in chainmail, steel helmet, spear, "
            "watchful expression, stone wall background"
        ),
    ),
    Archetype(
        id="sage_elder",
        label="Sage / Scholar",
        char_type="npc",
        role="sage",
        gender="ambiguous",
        body="slight",
        age="elder",
        tags=["sage", "scholar", "elder", "knowledge"],
        base_prompt=(
            "elderly scholar, ink-stained fingers, layered worn robes, "
            "piercing intelligent eyes, white hair, surrounded by books and scrolls"
        ),
    ),
    Archetype(
        id="noble",
        label="Noble",
        char_type="npc",
        role="noble",
        gender="ambiguous",
        body="average",
        age="middle",
        tags=["noble", "aristocrat", "authority"],
        base_prompt=(
            "noble in fine clothing, proud bearing, jeweled accessories, "
            "cold calculating eyes, manor background"
        ),
    ),
    Archetype(
        id="beggar_informant",
        label="Beggar / Informant",
        char_type="npc",
        role="beggar",
        gender="ambiguous",
        body="slight",
        age="elder",
        tags=["beggar", "informant", "mysterious"],
        base_prompt=(
            "hunched figure in ragged hooded cloak, weathered face with "
            "surprisingly sharp eyes, knowing smirk, alley background"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Enemy Archetypes — from og_system/06_monsters.json
# ---------------------------------------------------------------------------

ENEMY_ARCHETYPES = [
    Archetype(
        id="goblin_scout",
        label="Goblin Scout",
        char_type="enemy",
        role="goblin_scout",
        gender="ambiguous",
        body="small",
        age="young",
        tags=["goblin", "enemy", "small", "nimble", "humanoid"],
        base_prompt=(
            "goblin scout, small wiry green-skinned creature, large yellow eyes, "
            "pointed ears, crude leather armor, rusty dagger, sneering expression"
        ),
        variants=["alert", "attacking", "fleeing"],
    ),
    Archetype(
        id="orc_warrior",
        label="Orc Warrior",
        char_type="enemy",
        role="orc_warrior",
        gender="male",
        body="broad",
        age="middle",
        tags=["orc", "enemy", "warrior", "humanoid"],
        base_prompt=(
            "orc warrior, massive grey-green skinned humanoid, prominent lower tusks, "
            "crude iron armor, battle axe, scarred face, aggressive glare"
        ),
        variants=["alert", "attacking", "wounded", "raging"],
    ),
    Archetype(
        id="skeleton",
        label="Skeleton Warrior",
        char_type="enemy",
        role="skeleton",
        gender="ambiguous",
        body="average",
        age="ageless",
        tags=["skeleton", "undead", "enemy"],
        base_prompt=(
            "animated skeleton warrior, yellowed bones, rusted scraps of old armor, "
            "empty eye sockets with faint blue pinprick glow, corroded sword"
        ),
        variants=["standing", "attacking", "crumbling"],
    ),
    Archetype(
        id="zombie",
        label="Zombie",
        char_type="enemy",
        role="zombie",
        gender="ambiguous",
        body="stout",
        age="ageless",
        tags=["zombie", "undead", "enemy", "shambling"],
        base_prompt=(
            "shambling zombie, decomposing flesh, torn ragged clothing, "
            "milky dead eyes, arms outstretched, decayed face, graveyard background"
        ),
        variants=["shambling", "attacking", "fallen"],
    ),
    Archetype(
        id="gnoll",
        label="Gnoll War Party",
        char_type="enemy",
        role="gnoll_war_party",
        gender="ambiguous",
        body="broad",
        age="middle",
        tags=["gnoll", "enemy", "humanoid", "demon-touched"],
        base_prompt=(
            "gnoll warrior, hyena-headed humanoid with matted mane, "
            "demon-touched markings glowing faintly, crude spear and shield, "
            "wild frenzied eyes, battlefield background"
        ),
        variants=["alert", "attacking", "frenzied"],
    ),
    Archetype(
        id="redcap",
        label="Redcap",
        char_type="enemy",
        role="redcap",
        gender="ambiguous",
        body="slight",
        age="ageless",
        tags=["redcap", "fey", "enemy", "evil", "small"],
        base_prompt=(
            "redcap fey creature, small hunched figure, blood-soaked red cap, "
            "iron boots, long hooked fingers, murderous gleaming eyes, "
            "manic grin with sharp teeth, dark forest background"
        ),
        variants=["lurking", "attacking", "blood-soaked"],
    ),
    Archetype(
        id="hollow_man",
        label="Hollow Man",
        char_type="enemy",
        role="hollow_man",
        gender="ambiguous",
        body="average",
        age="ageless",
        tags=["hollow man", "fey", "horror", "possession", "enemy"],
        base_prompt=(
            "hollow man horror, human-shaped but subtly wrong, skin too smooth, "
            "eyes empty black voids, unsettling stillness, wearing someone else's face "
            "like a mask, faint shimmer at edges where reality bends"
        ),
        variants=["still", "wearing skin", "revealed", "pursuing"],
    ),
    Archetype(
        id="wraith_knight",
        label="Wraith Knight",
        char_type="enemy",
        role="wraith_knight",
        gender="ambiguous",
        body="average",
        age="ageless",
        tags=["wraith", "undead", "incorporeal", "enemy", "knight"],
        base_prompt=(
            "wraith knight, spectral armored figure half-solid half-shadow, "
            "ghostly blue-black armour, face hidden in darkness within helm, "
            "draining sword leaving trails of shadow, incorporeal form drifting"
        ),
        variants=["hovering", "attacking", "draining", "commanding shadows"],
    ),
    Archetype(
        id="vampire_lord",
        label="Vampire Lord",
        char_type="enemy",
        role="vampire_lord",
        gender="ambiguous",
        body="lean",
        age="ageless",
        tags=["vampire", "undead", "enemy", "noble"],
        base_prompt=(
            "vampire lord, pale aristocratic features, predatory grace, "
            "fine dark clothing, red eyes, fangs slightly visible in a cold smile, "
            "castle interior background, commanding presence"
        ),
        variants=["charming", "threatening", "mist form", "feeding", "commanding"],
    ),
    Archetype(
        id="mind_flayer",
        label="Mind Flayer",
        char_type="enemy",
        role="mind_flayer",
        gender="ambiguous",
        body="lean",
        age="ageless",
        tags=["mind flayer", "aberration", "psionic", "enemy"],
        base_prompt=(
            "mind flayer, tall humanoid with writhing tentacles instead of a mouth, "
            "large bulbous purple head, pale lavender skin, white robes, "
            "psionic energy crackling around elongated hands"
        ),
        variants=["observing", "attacking", "extracting", "commanding"],
    ),
    Archetype(
        id="medusa",
        label="Medusa",
        char_type="enemy",
        role="medusa",
        gender="female",
        body="average",
        age="ageless",
        tags=["medusa", "monstrosity", "enemy", "gorgon"],
        base_prompt=(
            "medusa, woman with living serpents for hair, each snake with distinct eyes, "
            "beautiful but terrifying face, averted gaze, stone statues of victims visible "
            "in background, scales at throat and shoulders"
        ),
        variants=["lurking", "gazing", "attacking", "triumphant"],
    ),
    Archetype(
        id="dire_wolf",
        label="Dire Wolf",
        char_type="creature",
        role="dire_wolf",
        gender="ambiguous",
        body="massive",
        age="middle",
        tags=["dire wolf", "beast", "creature", "predator"],
        base_prompt=(
            "massive dire wolf, dark grey fur, amber predatory eyes, "
            "enormous muscular body, snarling to reveal huge teeth, "
            "forest or mountain background"
        ),
        variants=["alert", "prowling", "attacking", "pack"],
    ),
    Archetype(
        id="moon_beast",
        label="Moon Beast",
        char_type="creature",
        role="moon_beast",
        gender="ambiguous",
        body="massive",
        age="ageless",
        tags=["moon beast", "aberration", "cosmic", "creature"],
        base_prompt=(
            "moon beast, massive werewolf-like creature but wrong — too many joints, "
            "fur that shifts like moonlight on water, dream-touched distortion around it, "
            "silver light vulnerability visible as faint halo of pain at edges, "
            "night sky background with oversized moon"
        ),
        variants=["dream hunting", "attacking", "moonlit", "wounded by silver"],
    ),
]

ALL_ARCHETYPES = CLASS_ARCHETYPES + NPC_ARCHETYPES + ENEMY_ARCHETYPES
ARCHETYPE_BY_ID = {a.id: a for a in ALL_ARCHETYPES}


def get_archetype(archetype_id: str) -> Optional[Archetype]:
    return ARCHETYPE_BY_ID.get(archetype_id)


def find_archetypes(char_type: str = None, role: str = None,
                    gender: str = None, tags: List[str] = None) -> List[Archetype]:
    results = ALL_ARCHETYPES
    if char_type:
        results = [a for a in results if a.char_type == char_type]
    if role:
        results = [a for a in results if a.role == role]
    if gender:
        results = [a for a in results if a.gender == gender]
    if tags:
        tag_set = set(tags)
        results = [a for a in results if tag_set & set(a.tags)]
    return results
