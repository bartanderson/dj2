import pytest
from unittest.mock import patch, MagicMock
from world.ai_integration import BaseAI, WorldAI, DungeonAI
from world.authority_system import AuthoritySystem
from world.game_state import GameState
from world.session_system import SessionState, SessionSystem
from world.narrative_system import NarrativeGuide, ConsequenceSystem, MotivationTracker, ChoiceArchitect, PacingController

def test_baseai():
    ai = BaseAI()
    assert hasattr(ai, 'generate_embedding')

def test_worldai():
    ai = WorldAI(campaign_state=None)
    assert hasattr(ai, '_create_system_prompt')

def test_dungeonai():
    ai = DungeonAI(dungeon_state=None)
    assert hasattr(ai, '_process_command')

def test_authoritysystem():
    authority = AuthoritySystem()
    assert hasattr(authority, 'validate_action')

def test_gamestate():
    game_state = GameState()
    assert hasattr(game_state, 'move')

def test_sessionsystem():
    session_system = SessionSystem()
    assert hasattr(session_system, 'get_or_create_session')

def test_narrativesystem():
    narrative_system = NarrativeGuide()
    assert hasattr(narrative_system, 'get_gentle_nudge')