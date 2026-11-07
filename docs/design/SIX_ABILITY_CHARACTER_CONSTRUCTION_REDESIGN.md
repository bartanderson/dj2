# Six-Ability Character Construction Redesign

## RESUME POINT FOR NEXT CHATGPT SESSION

**Current state:** Conceptual architecture is settled enough to begin numerical design; implementation has not started.

**Last settled decision:** Character creation should be conversational at the player interface but deterministic underneath. The AI DM extracts and confirms the player's concept and priorities; deterministic rules choose the generation profile, perform permitted random generation/concept protection, and exhaustively assign the resulting six-score pool across STR/DEX/CON/INT/WIS/CHA.

**Exact next task:** Define the concrete generation profiles and their numerical rules, then test them with executable probability/balance simulations.

**Do not restart from:** whether to use four or six abilities; whether creation can be conversational; whether AI directly grants scores; whether generation and assignment are separate. Those decisions are already recorded below.

**Repository:** bartanderson/dj2

**How to resume:** Read this document first, then continue with the exact next task. Consult the authoritative design hierarchy and only relevant existing code when numerical rules need integration constraints.


## Status

**Design specification in progress. No implementation cutover yet.**

This document records the decisions reached during the redesign of the legacy OG four-attribute model so future sessions do not restart discovery or reinterpret settled decisions.

## Problem Being Solved

The legacy model uses:

- Brawn
- Finesse
- Wits
- Will

Investigation found that these concepts are applied inconsistently across character creation, derived statistics, spellcasting, saves, racial bonuses, persistence, monsters, and interfaces.

This is therefore a mechanical redesign, not a compatibility rename.

Legacy ontology is to be removed from the new canonical design rather than preserved through hidden mappings.

## Settled Design Direction

### Six canonical abilities

The replacement model is:

- STR — Strength
- DEX — Dexterity
- CON — Constitution
- INT — Intelligence
- WIS — Wisdom
- CHA — Charisma

### Ability scores

Normal character scores use:

- range: 3–18
- baseline: 10
- derived modifier:

    floor((score - 10) / 2)

Modifiers are derived values, not independently authoritative stored state.

### Responsibility boundaries

- STR: physical force, lifting, pushing, grappling, forceful melee
- DEX: coordination, precision, agility, reflexes, ranged accuracy
- CON: health contribution, endurance, poison/disease/physical resilience
- INT: knowledge, memory, reasoning, analysis, learned arcane understanding
- WIS: perception, awareness, intuition, situational judgment
- CHA: presence, influence, leadership, force of personality and personal agency

Strength and health are deliberately separated.

Charisma is not a renamed version of legacy Will.

### Ability + skill resolution

The working check model is:

    d20 + ability modifier + skill bonus + explicit situational modifiers >= TN

Abilities represent capability.

Skills represent training and expertise.

Skills are not permanently bound to one ability. The action and approach determine the ability/skill pairing, subject to deterministic adjudication.

Example:

- physical intimidation may use STR + Intimidation
- personal intimidation may use CHA + Intimidation

The AI may interpret the player's approach and propose structured intent/adjudication inputs. It does not authoritatively calculate outcomes.

### Saving throws

Saves are selected by the nature of the threat rather than by vague inherited categories.

Working semantic model:

- STR: resisting force, displacement, overpowering
- DEX: avoiding sudden physical danger
- CON: bodily endurance, poison, disease, exhaustion
- INT: threats to structured thought, memory, reasoning where mechanically appropriate
- WIS: perception, awareness, sensory distortion, confusion/illusion where appropriate
- CHA: domination, possession, direct attacks on agency/identity where appropriate

New rules must not merely replace legacy labels such as "Will save" with another generic label without describing the threat mechanism.

### Combat baseline

- melee attacks: normally STR, with explicit weapon/fighting-style exceptions
- ranged attacks: normally DEX
- initiative: working baseline is DEX
- WIS should primarily affect awareness, detection, and surprise rather than arbitrary initiative tie-breaking

Attack resolution and damage contribution are separate mechanical questions.

### Class-specific casting

Casting ability is class/feature-defined rather than universal.

Working candidates to test:

- Mage: INT
- Priest: WIS
- Bard: CHA
- Warlock: CHA

These remain balance hypotheses until tested.

### Resources and derived statistics

Do not use abilities as universal resource batteries.

Working principle:

> Abilities modify capability. Classes define progression. Features define resources.

Each derived resource must have one authoritative formula.

Do not preserve conflicting legacy formulas merely because they already exist.

## Character Creation Direction

The default experience should support a natural conversation between the player and the AI DM.

The AI helps the player express the desired character concept.

The deterministic system owns:

- generation profile selection rules
- random rolls
- score limits
- reroll permissions
- concept-protection rules
- score assignment
- validation
- final canonical state

The AI owns:

- conversation
- understanding player preferences
- summarizing the concept for confirmation
- explaining generation choices
- recommending valid options
- narrating the resulting character

The AI must not simply grant high scores because a player requests them.

## Creation Profiles

The system should offer a menu of creation approaches while allowing the player to reach them conversationally.

Candidate profiles include:

1. **Guided Character Creation** — recommended default; AI conversation produces structured preferences.
2. **Random Destiny** — deterministic/random score generation; player or assignment engine places the resulting scores.
3. **Concept-Guided Generation** — generate a legitimate score pool, then assign it to best satisfy the player's stated concept.
4. **Heroic Character** — higher campaign-approved power profile with explicitly defined limits.
5. **Balanced Character** — controlled predictable distribution for players/campaigns preferring reduced randomness.

These are profiles, not permissions for the AI to arbitrarily create exceptional characters.

## Concept Priorities

Conversation should be converted into structured preferences such as:

- defining strengths
- strong traits
- supporting traits
- neutral traits
- intentional weaknesses

Example:

    defining: DEX
    important: WIS
    supporting: CON
    intentional weakness: STR

The player should be shown a summary and confirm it before irreversible generation.

## Generation and Assignment Are Separate

This is a key architectural decision.

### Phase 1: Generate a valid score pool

A profile produces a legitimate pool, for example:

    [18, 16, 14, 11, 9, 7]

The profile defines how such a pool can be produced.

### Phase 2: Assign the pool

The deterministic assignment system evaluates:

- player concept priorities
- class fit
- explicit player preferences
- intentional weaknesses
- campaign/profile constraints

There are only:

    6! = 720

possible assignments of six scores to six abilities.

The engine can exhaustively evaluate all valid assignments rather than relying on an LLM to choose one.

The selected assignment should be reproducible and explainable.

## Concept Protection

Some concepts legitimately require an exceptional defining quality.

The system may provide bounded concept-protection mechanisms, but these must be deterministic/profile-defined rather than discretionary AI gifts.

Candidate mechanisms include:

- additional candidate roll for a defining ability
- replacement of the lowest score if a permitted protection roll is higher
- minimum placement requirement using the best valid generated score
- higher-power generation profile selected explicitly

Concept protection must not allow every requested ability to become exceptional simultaneously.

If requested strengths exceed the selected power budget, the system should expose the tradeoff rather than silently granting all maxima.

## Deterministic Assignment Objective

The exact numeric objective is not yet canonical, but the optimizer should evaluate every valid assignment against explicit criteria such as:

- defining-strength satisfaction
- strong-trait satisfaction
- supporting-trait satisfaction
- intentional-weakness satisfaction
- class mechanical viability
- explicit profile constraints

Invalid assignments must be rejected before optimization.

The optimizer should not secretly override player-confirmed priorities.

## Required Confirmation Boundary

Recommended creation flow:

    player conversation
        ↓
    AI extracts concept/preferences
        ↓
    player confirms structured summary
        ↓
    deterministic profile selection
        ↓
    deterministic/random score generation
        ↓
    permitted concept-protection processing
        ↓
    exhaustive deterministic assignment
        ↓
    player reviews result
        ↓
    permitted bounded adjustments
        ↓
    canonical character creation

## Architecture Boundary

This redesign must remain consistent with the project authority hierarchy:

- deterministic rules own mechanical truth
- state mutation follows authoritative action paths
- AI interprets and presents; it does not become mechanical authority
- narration presents resolved facts and does not alter outcomes

## Next Work

Before implementation:

1. Define exact generation profiles and score distributions.
2. Define the deterministic assignment objective and tie-breaking rules.
3. Build executable probability/balance simulations.
4. Establish skill bonus values and progression.
5. Define HP and class-resource formulas.
6. Validate representative character concepts and classes.
7. Convert the approved design into canonical rules/data schemas.
8. Only then replace legacy character interfaces and tests.

## Explicit Non-Goals

Do not:

- patch the legacy four-attribute model indefinitely
- silently map legacy concepts into the new ontology
- allow AI narration to alter mechanical generation or resolution
- guarantee every requested defining trait is maximized
- choose arbitrary high scores without profile authority
- begin broad implementation before the numerical model and invariants are established
