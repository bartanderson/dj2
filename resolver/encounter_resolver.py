# world/resolver/encounter_resolver.py

def resolve_flee(self, character, encounter_difficulty):
    # Use OG system skill: 'athletics' or generic 'finesse'?
    # Roll d20 + modifier against difficulty
    skill_mod = character.get_skill_rank('athletics')
    roll = random.randint(1, 20)
    return (roll + skill_mod) >= encounter_difficulty