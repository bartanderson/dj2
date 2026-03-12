# character_generator.py – OG System version

import random
from world import dnd_data  # this is now your og_data module

# ----------------------------------------------------------------------
# Attribute point buy (OG System: 4 points, max 3 per attribute)
# ----------------------------------------------------------------------
def random_attributes():
    """
    Generate a random distribution of 4 points among the four attributes,
    each between 0 and 4, with no single attribute exceeding 3.
    Returns a dict with keys 'brawn', 'finesse', 'wits', 'will'.
    """
    points = 4
    attrs = {'brawn': 0, 'finesse': 0, 'wits': 0, 'will': 0}
    # Distribute points randomly, respecting max 3
    for _ in range(points):
        # Choose a random attribute that is not already at max (3)
        eligible = [k for k in attrs if attrs[k] < 3]
        if not eligible:
            break  # all at max (shouldn't happen with 4 points)
        chosen = random.choice(eligible)
        attrs[chosen] += 1
    return attrs

# ----------------------------------------------------------------------
# Random skill selection
# ----------------------------------------------------------------------
def random_skills():
    """
    Return a list of 2–3 randomly chosen skills from the OG skill list.
    """
    all_skills = dnd_data.get_skill_list()
    count = random.randint(2, 3)
    return random.sample(all_skills, min(count, len(all_skills)))

# ----------------------------------------------------------------------
# Random fill for a single field (used by random_fill_all)
# ----------------------------------------------------------------------
def random_fill_field(field, current_data=None):
    """
    Generate a random value for a given form field.
    field: string name of the field (e.g., 'race', 'brawn', 'skills')
    current_data: optional dict of existing data (unused here)
    """
    if field == 'race':
        return random.choice(dnd_data.get_race_list())
    elif field == 'class':
        return random.choice(dnd_data.get_class_list())
    elif field == 'background':
        return random.choice(dnd_data.get_background_list())
    elif field in ('brawn', 'finesse', 'wits', 'will'):
        # For individual attributes, we don't generate in isolation;
        # random_attributes handles them together. This function will be called
        # for each attribute by random_fill_all, but we delegate to the batch.
        # We'll just return a placeholder; random_fill_all will override.
        return 1
    elif field == 'skills':
        return random_skills()
    else:
        # For name or other text fields, return empty (or could generate a random name)
        return ''

# ----------------------------------------------------------------------
# Main random fill function: fills all fields with valid OG data
# ----------------------------------------------------------------------
def random_fill_all(current_data=None):
    """
    Return a dictionary with randomly generated values for all character fields.
    Keys match what the form/context expects:
        name, race, class, background,
        brawn, finesse, wits, will,
        selected_skills (list)
    Also includes derived fields for compatibility (hit_die, class_skill_*)
    but those are handled in the endpoint.
    """
    # Generate attributes together
    attrs = random_attributes()

    # Pick random race, class, background
    race = random_fill_field('race')
    class_name = random_fill_field('class')
    background = random_fill_field('background')
    skills = random_fill_field('skills')

    # Generate a simple name (optional)
    name_prefixes = ['Aria', 'Borin', 'Cedric', 'Dorn', 'Elara', 'Finn', 'Greta', 'Hugo']
    name = random.choice(name_prefixes) + str(random.randint(1, 99))

    result = {
        'name': name,
        'race': race,
        'class': class_name,
        'background': background,
        'brawn': attrs['brawn'],
        'finesse': attrs['finesse'],
        'wits': attrs['wits'],
        'will': attrs['will'],
        'selected_skills': skills,
        # For template compatibility (ability_scores dict)
        'ability_scores': {
            'brawn': attrs['brawn'],
            'finesse': attrs['finesse'],
            'wits': attrs['wits'],
            'will': attrs['will'],
        },
        # These are used by the template if present; we set safe defaults
        'hit_die': None,
        'class_skill_choose': 0,
        'class_skill_options': [],
    }
    return result

# ----------------------------------------------------------------------
# Character creation from form data (simplified)
# ----------------------------------------------------------------------
def create_character_from_form(form_data, builder=None):
    """
    Create a Character object from validated form data.
    form_data is a dict (already normalized) containing:
        name, race, class, background,
        brawn, finesse, wits, will (as ints),
        skills (list of selected skill names),
        player_id
    Returns a dict with 'success', 'character', and optionally 'errors'.
    """
    from world.character import Character  # your new og_character

    errors = []

    # Validate required fields
    required = ['name', 'race', 'class', 'background']
    for field in required:
        if not form_data.get(field):
            errors.append(f"Missing {field}")

    # Validate race
    race = form_data.get('race')
    if race and not dnd_data.validate_race(race):
        errors.append(f"Invalid race: {race}")

    # Validate class
    class_name = form_data.get('class')
    if class_name and not dnd_data.validate_class(class_name):
        errors.append(f"Invalid class: {class_name}")

    # Validate background (optional – just check if in list)
    bg = form_data.get('background')
    if bg and bg not in dnd_data.get_background_list():
        errors.append(f"Invalid background: {bg}")

    # Parse attributes (with defaults)
    try:
        brawn = int(form_data.get('brawn', 1))
        finesse = int(form_data.get('finesse', 1))
        wits = int(form_data.get('wits', 1))
        will = int(form_data.get('will', 1))
    except ValueError:
        errors.append("Attributes must be numbers")

    # Optional: enforce point buy total (if you want to prevent cheating)
    if brawn + finesse + wits + will > 4:
        errors.append("Total attribute points cannot exceed 4")
    for attr, val in [('brawn', brawn), ('finesse', finesse), ('wits', wits), ('will', will)]:
        if val < 0 or val > 4:
            errors.append(f"{attr.capitalize()} must be between 0 and 4")

    # Get selected skills (list)
    skills = form_data.get('skills', [])
    if not isinstance(skills, list):
        skills = [skills] if skills else []
    # Validate each skill
    for skill in skills:
        if not dnd_data.validate_skill(skill):
            errors.append(f"Invalid skill: {skill}")

    if errors:
        return {'success': False, 'errors': errors}

    # Create character
    char = Character(
        name=form_data['name'],
        race=race,
        classs=class_name,
        background=bg,
        owner_id=form_data.get('player_id'),
        brawn=brawn,
        finesse=finesse,
        wits=wits,
        will=will,
        level=1
    )

    # Add skills
    for skill in skills:
        char.add_skill(skill, rank=1)

    return {'success': True, 'character': char}