"""character_generator.py — Form-data → Character bridge.

All character creation goes through CharacterBuilder._create_character_impl.
This module exists only to adapt HTML form input to that canonical pipeline.
"""
import random
import logging

from world import dnd_data

logger = logging.getLogger(__name__)

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


def random_abilities():
    """Roll 4d6 drop lowest, six times. Scores 3-18."""
    scores = []
    for _ in range(6):
        rolls = sorted(random.randint(1, 6) for _ in range(4))
        scores.append(sum(rolls[1:]))
    return dict(zip(ABILITIES, scores))


def random_skills(count=3):
    all_skills = dnd_data.get_skill_list()
    return random.sample(all_skills, min(count, len(all_skills)))


def random_fill_field(field, current_data=None):
    """Legacy stub — individual field random fill. Prefer random_fill_all."""
    if field == "race":
        return random.choice(dnd_data.get_race_list())
    if field == "class":
        return random.choice(dnd_data.get_class_list())
    if field == "background":
        return random.choice(dnd_data.get_background_list())
    if field == "skills":
        return random_skills()
    if field in ABILITIES:
        return random_abilities().get(field, 10)
    return ""


def random_fill_all(current_data=None):
    """Return a complete context dict for partials/creation_form.html."""
    race_name = random.choice(dnd_data.get_race_list())
    class_name = random.choice(dnd_data.get_class_list())
    background = random.choice(dnd_data.get_background_list())

    race = dnd_data.Race.get(race_name)
    racial_choice = []
    race_choice_options = []
    race_choice_count = 0
    if race:
        spec = race.choice_spec()
        if spec:
            race_choice_options = list(spec["from"])
            race_choice_count = spec["count"]
            racial_choice = random.sample(spec["from"], spec["count"])

    abilities = random_abilities()

    prefixes = ["Aria", "Borin", "Cedric", "Dorn", "Elara", "Finn", "Greta", "Hugo"]
    name = random.choice(prefixes) + str(random.randint(1, 99))

    ability_display = []
    for ab in ABILITIES:
        attr = dnd_data.Attribute.get(ab)
        ability_display.append(attr.name if attr else ab)

    return {
        "name": name,
        "race": race_name,
        "class": class_name,
        "background": background,
        "ability_scores": abilities,
        "ability_names": list(ABILITIES),
        "ability_display": ability_display,
        "racial_choice": racial_choice,
        "race_choice_options": race_choice_options,
        "race_choice_count": race_choice_count,
        "selected_skills": random_skills(),
        "skills_list": dnd_data.get_skill_list(),
        "races": dnd_data.get_race_list(),
        "classes": dnd_data.get_class_list(),
        "backgrounds": dnd_data.get_background_list(),
        "hit_die": None,
        "class_skill_choose": 0,
        "class_skill_options": [],
    }


def create_character_from_form(form_data, builder):
    """Validate form data and route through CharacterBuilder._create_character_impl."""
    errors = []

    for field in ("name", "race", "class"):
        if not form_data.get(field):
            errors.append(f"Missing {field}")
    if form_data.get("race") and not dnd_data.validate_race(form_data["race"]):
        errors.append(f"Invalid race: {form_data['race']}")
    if form_data.get("class") and not dnd_data.validate_class(form_data["class"]):
        errors.append(f"Invalid class: {form_data['class']}")

    abilities = {}
    for ab in ABILITIES:
        raw = form_data.get(ab) or form_data.get(ab.lower()) or "10"
        try:
            score = int(raw)
        except (TypeError, ValueError):
            errors.append(f"{ab} must be an integer")
            score = 10
        if not (3 <= score <= 18):
            errors.append(f"{ab}={score} out of range 3-18")
        abilities[ab] = score

    racial_choice = form_data.get("racial_choice")
    if isinstance(racial_choice, str):
        racial_choice = [s.strip() for s in racial_choice.split(",") if s.strip()]
    elif racial_choice is None:
        racial_choice = []

    skill_profs = form_data.get("skill_proficiencies") or form_data.get("skills") or []
    if isinstance(skill_profs, str):
        skill_profs = [skill_profs]

    if errors:
        return {"success": False, "errors": errors}

    try:
        character = builder._create_character_impl(
            owner_id=form_data.get("player_id", "unknown"),
            char_data={
                "name": form_data["name"],
                "race": form_data["race"],
                "class": form_data["class"],
                "background": form_data.get("background", "unknown"),
                "abilities": abilities,
                "racial_choice": list(racial_choice),
                "skill_proficiencies": list(skill_profs),
            },
        )
        return {"success": True, "character": character}
    except Exception as e:
        logger.exception("character creation failed")
        return {"success": False, "errors": [str(e)]}