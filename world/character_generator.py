# world/character_generator.py

import random
from world import dnd_data

ABILITY_SCORE_NAMES = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']

def normalize_form_data(raw_data):
    data = dict(raw_data)

    # Ensure race is set if subrace is present
    if data.get('subrace'):
        race = dnd_data.get_race_for_subrace(data['subrace'])
        if race:
            data['race'] = race

    # Convert individual ability fields into a dictionary
    ability_scores = {}
    for key in ABILITY_SCORE_NAMES:  # <-- use the constant
        if key in data and data[key]:
            try:
                ability_scores[key] = int(data[key])
            except ValueError:
                pass
    data['ability_scores'] = ability_scores
    return data

def random_fill_field(field, current_data):
    """
    Generate a random valid value for a field, respecting dependencies.
    current_data is a dict of already chosen fields (values are strings).
    Returns a dict with keys needed to render the field's container template.
    """
    if field == 'name':
        # Generate a random fantasy name (simplified)
        first = ["Aer", "Bal", "Cor", "Dal", "El", "Far", "Gor", "Hal", "Ian", "Jor", "Kal", "Lor", "Mar", "Nor", "Or", "Por", "Qui", "Ral", "Sor", "Tor", "Ul", "Val", "Wor", "Xan", "Yor", "Zor"]
        last = ["as", "en", "ic", "on", "or", "us", "ar", "is", "an", "in", "um", "ax", "ix", "ox"]
        name = random.choice(first) + random.choice(last)
        return {'name': name}

    elif field == 'race':
        races = dnd_data.get_race_list()
        if not races:
            return {'error': 'No races available'}
        chosen = random.choice(races)
        subraces = dnd_data.get_subraces_for_race(chosen)
        subrace = random.choice(subraces) if subraces else None
        return {
            'race': chosen,
            'subraces': subraces,
            'subrace': subrace
        }

    elif field == 'subrace':
        race = current_data.get('race')
        if not race:
            return {'error': 'Race must be chosen first'}
        subraces = dnd_data.get_subraces_for_race(race)
        if not subraces:
            return {'subrace': None}
        chosen = random.choice(subraces)
        return {'subrace': chosen}

    elif field == 'class':
        classes = dnd_data.get_class_list()
        if not classes:
            return {'error': 'No classes available'}
        chosen = random.choice(classes)
        fighting_styles = dnd_data.get_fighting_styles_for_class(chosen)
        fighting_style = random.choice(fighting_styles) if fighting_styles else None
        return {
            'class': chosen,
            'fighting_styles': fighting_styles,
            'fighting_style': fighting_style
        }

    elif field == 'fighting_style':
        class_name = current_data.get('class')
        if not class_name:
            return {'error': 'Class must be chosen first'}
        styles = dnd_data.get_fighting_styles_for_class(class_name)
        if not styles:
            return {'fighting_style': None}
        chosen = random.choice(styles)
        return {'fighting_style': chosen}

    elif field == 'background':
        backgrounds = dnd_data.get_background_list()
        if not backgrounds:
            return {'background': None}
        chosen = random.choice(backgrounds)
        return {'background': chosen}

    elif field == 'skills':
        # For simplicity, we'll pick 2 random skills
        all_skills = dnd_data.get_skill_list()
        chosen = random.sample(all_skills, min(2, len(all_skills)))
        return {'skills': chosen}

    elif field == 'ability_scores':
        # Standard array: 15,14,13,12,10,8 assigned randomly
        scores = [15,14,13,12,10,8]
        random.shuffle(scores)
        abilities = dnd_data.get_ability_score_list()
        # Ensure we have exactly 6 abilities
        if len(abilities) >= 6:
            ability_scores = {abilities[i]: scores[i] for i in range(6)}
        else:
            ability_scores = {}
        return {'ability_scores': ability_scores}

    # Add more fields as needed
    return {}

def random_fill_all(current_data):
    """
    Fill any missing fields with random valid values.
    Returns a complete character dict with all fields set.
    """
    complete = current_data.copy()

    # Define order respecting dependencies
    fields_order = ['name', 'race', 'subrace', 'class', 'fighting_style', 'background', 'skills', 'ability_scores']
    for field in fields_order:
        if field not in complete or not complete[field]:
            result = random_fill_field(field, complete)
            if field in result:
                complete[field] = result[field]
            # Handle dependent fields that might have been generated together
            if field == 'race' and 'subrace' in result and result['subrace']:
                complete['subrace'] = result['subrace']
            if field == 'class' and 'fighting_style' in result and result['fighting_style']:
                complete['fighting_style'] = result['fighting_style']
            if field == 'ability_scores' and 'ability_scores' in result:
                complete['ability_scores'] = result['ability_scores']
            if field == 'skills' and 'skills' in result:
                complete['skills'] = result['skills']
    return complete

def create_character_from_form(form_data, builder):
    """
    Validate and create a character using the provided CharacterBuilder instance.
    form_data should include 'name', 'race', 'class', and optionally
    'background', 'strength', 'dexterity', etc. (ability scores as individual keys).
    Returns dict with 'success' and either 'character' or 'errors'.
    """
    required = ['name', 'race', 'class']
    missing = [f for f in required if not form_data.get(f)]
    if missing:
        return {'success': False, 'errors': [f"Missing required field: {f}" for f in missing]}

    # Validate that subrace belongs to race (if provided)
    race = form_data.get('race')
    subrace = form_data.get('subrace')
    if subrace:
        valid_subraces = dnd_data.get_subraces_for_race(race)
        if subrace not in valid_subraces:
            return {'success': False, 'errors': [f"'{subrace}' is not a valid subrace for {race}"]}

    # Build char_data for the builder
    char_data = {
        'name': form_data['name'],
        'race': race,
        'class': form_data['class'],
        'background': form_data.get('background'),
    }
    # Add ability scores if present
    ability_names = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
    for key in ability_names:
        if key in form_data and form_data[key]:
            try:
                char_data[key] = int(form_data[key])
            except ValueError:
                return {'success': False, 'errors': [f"Invalid value for {key}"]}

    # Add other optional fields if you want to support them
    # e.g., 'age', 'gender', 'alignment', etc.

    try:
        character = builder.create_character(form_data['player_id'], char_data)
        # Optionally store subrace as a custom attribute on the character
        if subrace:
            character.subrace = subrace
        return {'success': True, 'character': character}
    except Exception as e:
        return {'success': False, 'errors': [str(e)]}
