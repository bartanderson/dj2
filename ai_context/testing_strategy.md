# Dungeon Journey 2 – Testing Strategy

This document defines the principles, patterns, and practices for writing tests in the Dungeon Journey 2 project. All tests must adhere to these guidelines to ensure maintainability, speed, and alignment with the architectural rules (AI Contract, phase boundaries).

## 1. Core Principles

- **Test behavior, not implementation.** Focus on what the code does, not how it does it internally.
- **Isolate dependencies.** Use fakes, stubs, and mocks to replace external systems (AI, database, file I/O, network).
- **Keep tests fast.** No test should take more than 0.1 seconds. Real I/O is forbidden in unit tests.
- **One logical assertion per test.** Each test should verify a single behavior or outcome.
- **Tests are documentation.** They should be readable and explain the expected behavior through names and docstrings.

## 2. Testing Levels

We adopt a pyramid approach with four levels:

| Level | Type | Purpose | Location | Example |
|-------|------|---------|----------|---------|
| 4 | **Business Logic / Unit** | Test a single class/method in isolation with fakes. | `tests/unit/` | Testing `CharacterBuilder` with a fake `Character` class. |
| 3 | **Integration** | Test interactions between a few components, still with mocked boundaries. | `tests/integration/` | Testing that `CharacterBuilder` correctly uses the `SessionSystem` via an interface. |
| 2 | **Contract** | Verify that an interface (e.g., boundary between AI and Core) conforms to expected input/output. | `tests/contracts/` | Ensuring `dm_chat_ai` always returns a structured response. |
| 1 | **End-to-End** | Full system validation with real dependencies (use sparingly, only for critical paths). | `tests/e2e/` | Complete character creation flow from user input to database. |

**Default:** Most tests should be Level 4 (unit tests with fakes). Level 3 and above are reserved for specific integration points.

## 3. Mocking Strategy

We use `unittest.mock` and prefer **fakes** over pervasive mocking. A fake is a lightweight in‑memory implementation of a dependency.

### 3.1 When to Use What

| Technique | When to Apply | Example |
|-----------|---------------|---------|
| **Fake class** | Replacing a whole class that is used as a dependency. | `MockCharacter` (from working test) |
| **`patch` context manager** | Short-lived mocking inside a single test. | `with patch('module.CONSTANT', value):` |
| **`patch` decorator** | Mocking needed throughout an entire test method. | `@patch('module.function')` |
| **`patch.object`** | Replacing a single method on an existing object. | `mock_ai.generate_text = Mock(return_value=...)` |
| **Module‑level replacement** | When the module binds globals at import time. | `character_builder.Character = MockCharacter` (before import) |

### 3.2 Rules

- **Never leave dangling patches.** Always use context managers or decorators that revert automatically.
- **For fakes, implement only the methods/attributes used by the system under test.** Keep them minimal.
- **Mock return values should be realistic but simple** – enough to enable assertions.

## 4. Fixture Design

Pytest fixtures are the primary way to share setup code. Follow these guidelines:

- **Modular fixtures:** Each fixture provides one dependency.
- **Compose fixtures:** Use fixtures that depend on other fixtures.
- **Yield instead of return** if cleanup is needed.
- **Name fixtures clearly** – e.g., `mock_ai`, `character_builder`, `sample_character_data`.

Example from the working test:
```python
@pytest.fixture
def mock_ai():
    ai = Mock()
    ai.generate_structured_data.return_value = {
        "traits": "Brave but reckless",
        ...
    }
    ai.generate_text.return_value = "Thorin was born..."
    return ai

@pytest.fixture
def builder(mock_ai):
    with patch('world.character_builder.CLASSES', MOCK_CLASSES):
        yield character_builder.CharacterBuilder(mock_ai)
```
5. Test Structure: Arrange-Act-Assert (AAA)
Every test must follow this explicit pattern:

```python
def test_some_behavior(fixtures):
    # ARRANGE: set up inputs, configure mocks
    input_data = {...}
    expected = ...

    # ACT: call the method under test
    result = system_under_test.method(input_data)

    # ASSERT: verify outcomes
    assert result == expected
    mock_dependency.method.assert_called_once_with(...)
```
Arrange – create test data, set mock expectations.

Act – perform the single action being tested.

Assert – verify results and interactions.

6. Handling Architectural Constraints
Your project has specific architectural rules that tests must enforce:

6.1 AI Contract
AI NEVER owns state. Tests for AI‑Facing modules must assert that they do not mutate core state directly.

AI NEVER mutates state directly. If a method in an AI‑Facing file attempts to call SessionSystem.update, the test must fail.

AI ONLY requests actions via interfaces. Verify that calls go through approved boundary methods (e.g., dm_chat_ai.request_action).

6.2 Phase Boundaries
The phase sequence is: Input → Interpretation → Authority → Mutation → Consequence → Persistence → View.

Tests for Core modules may allow mutations, but they must happen through proper channels (e.g., repositories, not directly on global state).

Tests for Adapter modules should verify that they correctly translate external requests into internal phase calls.

Tests for Boundary files (e.g., dm_chat_ai) must ensure they do not skip phases (e.g., no direct mutation from AI).

6.3 Role‑Specific Rules
Role	Allowed Actions	Test Focus
Core	Business logic, state management	Verify correctness of mutations, enforce phase rules.
Adapter	Translate external input, call Core	Check that input is parsed and correct Core methods are invoked.
AI‑Facing	Read‑only, request actions via interfaces	Ensure no mutations, verify that requests are formatted correctly.

7. Test Data
Keep test data minimal and inline within each test, unless reused across many tests (then use fixtures).

Use descriptive variable names that reflect the domain (e.g., dwarf_character_data, owner_id).

Avoid magic numbers/strings – define constants or use meaningful literals.

8. What Not to Test (Anti‑Patterns)
Do NOT write tests that:

Call subprocesses.

Read/write the filesystem.

Make network requests (including real AI calls).

Depend on external services (database, APIs).

Use @patch on every single dependency – prefer injection and fakes.

Test private methods that are only implementation details (exception: small helper methods that are worth isolating, like `_generate_personality`).

Share mutable state between tests – each test must start fresh.

9. Integration with arch_recon.py Template System
We have a tool arch_recon.py that can extract test templates from existing test files and generate new tests using those templates.

Extract a template:

```bash
python tools/analysis/arch_recon.py --extract-template tests/unit/test_character_builder.py --template-dir tools/analysis/templates
This creates a JSON file capturing the structure, mocking patterns, and example tests.
```

Generate a new test using a template:

```bash
python tools/analysis/arch_recon.py --test "your feature" --db ai_context/scout.db --output tests/unit/test_feature.py --test-with-template --template-dir tools/analysis/templates
```
The AI will adapt the template to the new feature, respecting the architectural rules embedded in the template.

10. Putting It All Together: A Complete Example
The following test (based on your working test) demonstrates all the principles:

```python
import pytest
from unittest.mock import Mock, patch

# ----------------------------------------------------------------------
# Fakes
# ----------------------------------------------------------------------
class MockCharacter:
    def __init__(self, owner_id=None, name=None, classs=None, level=None,
                 background=None, race=None):
        self.owner_id = owner_id
        self.name = name
        self.classs = classs
        self.level = level
        self.background = background
        self.race = race
        self.add_custom_item = Mock()

# ----------------------------------------------------------------------
# Module patching (before import)
# ----------------------------------------------------------------------
from world import character_builder
character_builder.Character = MockCharacter

# ----------------------------------------------------------------------
# Constants for patching
# ----------------------------------------------------------------------
MOCK_CLASSES = {
    'fighter': Mock(name='FighterClass'),
    'wizard': Mock(name='WizardClass'),
    # ... etc
}

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def mock_ai():
    ai = Mock()
    ai.generate_structured_data.return_value = {...}
    ai.generate_text.return_value = "..."
    return ai

@pytest.fixture
def builder(mock_ai):
    with patch('world.character_builder.CLASSES', MOCK_CLASSES):
        yield character_builder.CharacterBuilder(mock_ai)

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_create_character_calls_ai_and_builds_character(builder, mock_ai):
    """Test that create_character() uses AI and returns a properly built Character."""
    # Arrange
    char_data = {...}
    owner_id = "player123"

    # Act
    character = builder.create_character(owner_id, char_data)

    # Assert
    assert mock_ai.generate_structured_data.called
    assert character.owner_id == owner_id
    # ... more assertions
```
11. Continuous Improvement
Review tests during code reviews. Enforce the guidelines.

Update this document as we discover better patterns or new architectural constraints.

Refine templates as we write more tests, capturing recurring patterns.