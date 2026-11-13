import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world.narrative_engine import NarrativeEngine
from world.campaign import Quest, CampaignState
from world.world_map import Location


# ----------------------------------------------------------------------
# Mocks
# ----------------------------------------------------------------------

class MockAI:
    def generate_structured_data(self, prompt, response_format):
        return {
            "name": "Test Arc",
            "description": "A test story arc",
            "id": "test_quest",
            "archetype": "test",
            "patron": "NPC",
            "target": "target",
            "opposition": [],
            "stages": [{"type": "explore", "description": "Explore"}],
            "consequences": {"success": "win", "failure": "lose"},
            "time_pressure": {"exists": False},
        }

    def process_prompt(self, prompt, response_format):
        return {
            "description": "Failed",
            "consequences": ["lost opportunity"],
            "new_opportunities": ["new path"],
        }


class MockSession:
    def __init__(self):
        self.started: list = []
        self.completed: list = []
        self.failed: list = []

    def start_quest(self, quest_id):
        self.started.append(quest_id)

    def complete_quest(self, quest_id):
        self.completed.append(quest_id)

    def fail_quest(self, quest_id):
        self.failed.append(quest_id)


def make_engine():
    campaign = CampaignState()
    session = MockSession()
    ai = MockAI()
    engine = NarrativeEngine(ai=ai, campaign=campaign, session=session)
    return engine, campaign, session


# ----------------------------------------------------------------------
# on_arc_completed
# ----------------------------------------------------------------------

def test_on_arc_completed_clears_active_arc():
    engine, _, _ = make_engine()
    engine.active_arc = {"name": "The Dragon's Wrath"}
    engine.on_arc_completed()
    assert engine.active_arc is None


def test_on_arc_completed_appends_event():
    engine, _, _ = make_engine()
    engine.active_arc = {"name": "The Dragon's Wrath"}
    engine.on_arc_completed()
    assert len(engine.global_events) == 1
    ev = engine.global_events[0]
    assert ev["type"] == "arc_completed"
    assert ev["arc_name"] == "The Dragon's Wrath"
    assert "Dragon's Wrath" in ev["message"]


def test_on_arc_completed_no_active_arc():
    engine, _, _ = make_engine()
    engine.on_arc_completed()
    assert engine.active_arc is None
    assert len(engine.global_events) == 0


# ----------------------------------------------------------------------
# start_quest / complete_quest / fail_quest
# ----------------------------------------------------------------------

def test_start_quest_with_missing_quest():
    engine, _, _ = make_engine()
    engine.start_quest("nonexistent")
    # Should not raise


def test_start_quest_with_existing_quest():
    engine, campaign, session = make_engine()
    quest = Quest(
        id="q1", archetype="retrieve", patron="elder", target="ruins",
        opposition=[], stages=[], consequences={}, time_pressure={}
    )
    campaign.quests["q1"] = quest
    engine.start_quest("q1")
    assert "q1" in session.started


def test_complete_quest_with_existing_quest():
    engine, campaign, session = make_engine()
    quest = Quest(
        id="q2", archetype="destroy", patron="king", target="artifact",
        opposition=["monster"], stages=[], consequences={}, time_pressure={}
    )
    campaign.quests["q2"] = quest
    engine.complete_quest("q2")
    assert "q2" in session.completed


def test_fail_quest_with_existing_quest():
    engine, campaign, session = make_engine()
    quest = Quest(
        id="q3", archetype="escort", patron="merchant", target="village",
        opposition=["bandits"], stages=[], consequences={}, time_pressure={}
    )
    campaign.quests["q3"] = quest
    engine.fail_quest("q3")
    assert "q3" in session.failed


# ----------------------------------------------------------------------
# generate_quest
# ----------------------------------------------------------------------

def test_generate_quest_adds_to_campaign():
    engine, campaign, _ = make_engine()
    # Add a location first
    loc = Location(id="loc1", name="Ruins", type="dungeon", description="Ancient ruins")
    campaign.locations["loc1"] = loc

    quest = engine.generate_quest("loc1", "ancient ruins")
    assert quest.id == "test_quest"  # from MockAI
    assert quest.id in campaign.quests
    assert quest.id in engine.active_quests


# ----------------------------------------------------------------------
# on_location_discovered
# ----------------------------------------------------------------------

def test_on_location_discovered_sets_discovered():
    engine, campaign, _ = make_engine()
    loc = Location(id="loc2", name="Forest", type="settlement", description="A forest village")
    campaign.locations["loc2"] = loc

    engine.on_location_discovered("loc2")
    assert loc.discovered is True
    # Should also generate a quest
    assert len(engine.active_quests) == 1


def test_on_location_discovered_missing_location():
    engine, _, _ = make_engine()
    # Should not raise
    engine.on_location_discovered("nonexistent")


# ----------------------------------------------------------------------
# advance_story_arc
# ----------------------------------------------------------------------

def test_advance_story_arc_progresses_step():
    engine, _, _ = make_engine()
    engine.active_arc = {
        "name": "Test Arc",
        "current_step": 0,
        "total_steps": 3,
        "completed": False,
    }
    engine.advance_story_arc()
    assert engine.active_arc["current_step"] == 1
    assert engine.active_arc["completed"] is False


def test_advance_story_arc_completes_at_max_step():
    engine, _, _ = make_engine()
    engine.active_arc = {
        "name": "Test Arc",
        "current_step": 2,
        "total_steps": 3,
        "completed": False,
    }
    engine.advance_story_arc()
    # on_arc_completed sets active_arc to None and logs an event
    assert engine.active_arc is None
    assert len(engine.global_events) == 1
    assert engine.global_events[0]["type"] == "arc_completed"
    assert engine.global_events[0]["arc_name"] == "Test Arc"


def test_advance_story_arc_no_active_arc():
    engine, _, _ = make_engine()
    engine.advance_story_arc()
    assert engine.active_arc is None


# ----------------------------------------------------------------------
# Run all tests
# ----------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_on_arc_completed_clears_active_arc,
        test_on_arc_completed_appends_event,
        test_on_arc_completed_no_active_arc,
        test_start_quest_with_missing_quest,
        test_start_quest_with_existing_quest,
        test_complete_quest_with_existing_quest,
        test_fail_quest_with_existing_quest,
        test_generate_quest_adds_to_campaign,
        test_on_location_discovered_sets_discovered,
        test_on_location_discovered_missing_location,
        test_advance_story_arc_progresses_step,
        test_advance_story_arc_completes_at_max_step,
        test_advance_story_arc_no_active_arc,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
