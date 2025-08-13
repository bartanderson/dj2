class EnvironmentalEffect:
    def __init__(self, effect_type, position, intensity=1):
        self.effect_type = effect_type
        self.position = position
        self.intensity = intensity
        self.duration = -1  # -1 = permanent
        
    def apply_effect(self, character):
        """Apply effect to character"""
        if self.effect_type == 'difficult_terrain':
            character.movement_speed *= 0.5
        elif self.effect_type == 'slippery':
            character.dexterity_modifier -= 2
        elif self.effect_type == 'toxic_gas':
            character.take_damage(self.intensity)
        elif self.effect_type == 'magical_conduit':
            character.spell_power += self.intensity
            
    def update(self):
        """Update effect duration"""
        if self.duration > 0:
            self.duration -= 1
        return self.duration > 0

class MonsterTemplate:
    def __init__(self, name, stats, abilities, description):
        self.name = name
        self.stats = stats # {hp, ac, attack, damage}
        self.abilities = abilities  # [list of special abilities]
        self.description = description
        
MONSTER_DB = {
    'goblin': MonsterTemplate(
        name="Goblin",
        stats={'hp': 7, 'ac': 15, 'attack': 4, 'damage': '1d6+2'},
        abilities=['Nimble Escape'],
        description="A small, green humanoid with beady eyes and sharp teeth"
    ),
    'zombie': MonsterTemplate(
        name="Zombie",
        stats={'hp': 22, 'ac': 8, 'attack': 3, 'damage': '1d6+1'},
        abilities=['Undead Fortitude'],
        description="A shambling corpse with rotting flesh"
    ),
    # Add more monsters
}

# Predefined feature templates
FEATURE_TEMPLATES = {
    'water': {
        'description': "A pool of stagnant water",
        'effect': "difficult_terrain"
    },
    'rubble': {
        'description': "Collapsed stone and debris",
        'effect': "difficult_terrain"
    },
    'bloodstain': {
        'description': "Dried blood on the floor",
        'effect': None
    },
    'statue': {
        'description': "A stone statue of a forgotten deity",
        'effect': None
    }
}