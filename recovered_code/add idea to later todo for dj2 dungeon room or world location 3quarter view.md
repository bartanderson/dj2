dj2 Scene Panel — Design Capture

What it is

A visual overlay that appears when entering a room or location. Shows the space, the characters, and what's happening during encounter/combat. Immersion and visibility aid — not a visual mystery game, not replacing narrative. The text runs the story; the panel shows the spatial state.

Perspective and art style

3/4 oblique view (classic RPG perspective — floor and back wall both visible). Flat paper-cutout style, South Park without the talking heads. Simple, stylized, not realistic. Characters are positioned sprites against a generated room background.

Room backgrounds

One generated image per room/location type. Prompt style: "dungeon cell, 3/4 RPG perspective, stone floor and back wall visible, torch lit, flat illustration style." Generated via Qwen in batches. Swapped when the party moves to a new location.

Character sprites — paper doll model

Posture variants are the unit, not naked body + layered clothing. Outfit is baked into each variant. Per character:

idle — standing relaxed
combat — weapon raised, weight forward
casting — arms up, spell forming
wounded — slumped, favoring one side
dead — fallen (or CSS tip-over)
Generate per character class/archetype, reuse across party members of same type. Batch via Qwen: "flat 2D paper cutout, D&D fighter in plate armor, combat ready pose, transparent background, facing right, 3/4 oblique."

Effect and status overlays

Shared pool, transparent PNGs, sit on top of any character sprite. Generated once, used by any caster or target.

Effects (spells, abilities):

fireball_forming, shield_aura, healing_light, lightning_charge, etc.
Status badges (small icon, corner of sprite):

poisoned, blessed, stunned, burning, invisible, etc.
Zone model

12 named zones — the AI picks from a fixed enum, server maps to CSS position. No pixel coordinates, no hallucinated values.

back-left    back-center    back-right      ← high on screen, z-index 1
mid-left     mid-center     mid-right       ← z-index 2
front-left   front-center   front-right     ← low on screen, z-index 3
+ door, cover, corner-a, corner-b
Depth sorting is automatic: front zones draw over back zones via z-index. Sprites in same zone get slight CSS offset to avoid exact overlap.

Facing direction

One boolean per character. facing: right is default. Server flips to left when character turns to engage. Rendered as transform: scaleX(-1) — costs nothing, reads clearly.

Initiative and reveal

Fastest roll appears first, gets highlighted on their turn. Initiative tracker already in dj2 is the source of truth. Scene panel mirrors it — no separate system.

AI integration — update_scene tool

The AI already resolves actions and outputs narrative. Add one more output: a structured scene update. The AI calls update_scene as part of action resolution.

{
  "entities": {
    "garrick":  {"zone": "mid-left",   "facing": "right", "pose": "combat",  "effect": null,           "status": []},
    "mira":     {"zone": "back-right", "facing": "right", "pose": "casting", "effect": "fireball_form","status": []},
    "goblin_1": {"zone": "mid-center", "facing": "left",  "pose": "combat",  "effect": null,           "status": ["poisoned"]}
  }
}
Scene state is included in the AI's prompt as a compact block so positions stay consistent turn to turn:

SCENE: dungeon_cell
garrick: mid-left | mira: back-right | goblin_1: mid-center | goblin_2: back-left
initiative: garrick(18) > mira(14) > goblin_1(12) > goblin_2(9)
Rendering — server side

Flask endpoint serves the scene fragment. Server maps zone enum → CSS left/top%, applies pose sprite src, applies effect overlay src, applies status badge, applies facing transform. SSE pushes the rendered fragment on each update. HTMX swaps it into the overlay panel.

Animation — CSS only, no JS logic

Movement between zones: CSS transition: left 0.4s ease, top 0.4s ease on the sprite element.

Action classes applied by server, removed after transition:

Class   Effect
action-attack   quick translate toward target, bounce back
action-hit  jitter keyframe
action-cast brief pulse/glow
action-death    rotate 90deg + fade
One transitionend JS listener removes the class. That's the only JS logic in the whole panel.

Audio

Separate from the scene panel but same event model. Small JS module (20-30 lines) listens for server-sent events and plays files from /static/audio/. Server decides what plays; JS executes playback. No logic in the client. "functional JS" — the pattern you want everywhere.

Build order

One room, static background, manually-positioned sprites, no AI movement. Prove the overlay looks right.
Wire SSE and HTMX swap. Prove updates work.
Add the update_scene tool to dj2's AI. Prove zone positioning is reliable.
Add posture variants and effect overlays. Prove layering works.
Add audio. Prove event-driven playback works.
Art generation pipeline — batch room backgrounds and character sprites via Qwen.
Don't start until combat and the narrative loop are solid. This is a display layer on top of a working game.