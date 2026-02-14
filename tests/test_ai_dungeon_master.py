import pytest
from unittest.mock import patch, MagicMock
from dungeon_neo.ai_integration import DungeonAI
from dungeon_neo.generator_neo import DungeonGeneratorNeo
from dungeon_neo.state_neo import DungeonStateNeo
from dungeon_neo.movement_service import MovementService
from dungeon_neo.constants import *
from flask import Blueprint, jsonify

@pytest.fixture
def game_state():
    return MagicMock()

@pytest.fixture
def ai_integrator(game_state):
    return DungeonAI(game_state)

@patch('dungeon_neo.ai_integration.DungeonAI.process_command')
def test_ai_command(ai_integrator, mock_process_command):
    data = {'command': 'move north'}
    result = ai_integrator.process_command(data)
    assert result['success']

@patch('dungeon_neo.generator_neo.DungeonGeneratorNeo.create_dungeon')
def test_generate_dungeon(create_dungeon_mock):
    create_dungeon_mock.return_value = {'grid': [[1, 2], [3, 4]]}
    dungeon_system = MagicMock()
    state = DungeonStateNeo(game_state)
    assert state.width == 2
    assert state.height == 2

@patch('dungeon_neo.movement_service.MovementService.update_visibility')
def test_update_visibility(update_visibility_mock):
    movement_service = MovementService(DungeonStateNeo(game_state))
    data = {'command': 'move north'}
    result = game_state.dungeon.movement.process_command(data)
    update_visibility_mock.assert_called_once()

@pytest.fixture
def blueprint():
    return MagicMock(spec=Blueprint)

@patch('dungeon_neo.api.get_dungeon_image')
def test_get_dungeon_image(get_dungeon_image_mock, blueprint):
    data = {'debug': 'true'}
    result = blueprint.get_dungeon_image(data)
    assert result is not None

@pytest.fixture
def character():
    return MagicMock()

@pytest.fixture
def get_character(character):
    return character

@patch('dungeon_neo.api.get_character')
def test_get_character(get_character_mock, character):
    data = {'player_id': '123'}
    result = get_character_mock(data)
    assert result is not None