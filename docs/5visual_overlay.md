1) Core distinction (this will keep you sane)
Overlay = visual annotation

Does not change movement or connectivity.

Replacement = topology change

Must change:

passability
adjacency logic
pathfinding graph

You were already leaning this way—commit to it explicitly.

2) Door state model (keep it orthogonal)

Don’t encode everything as separate types like:

“locked-open-broken-portcullis”

That explodes quickly.

Instead:

class Door:
    def __init__(self):
        self.kind = "wood"          # wood, stone, portcullis, hidden
        self.is_open = False
        self.is_locked = False
        self.is_broken = False
        self.is_trapped = False
        self.is_hidden = False

Then rendering becomes state projection, not lookup tables.

Rendering logic example
def render_door(tile, door, knowledge):
    draw_base_door(tile, door.kind)

    if not door.is_hidden or knowledge.detected_secret:
        if door.is_open:
            draw_open_gap(tile)

        if door.is_broken:
            draw_damage(tile)

        if door.is_locked and knowledge.detected_lock:
            draw_lock_marker(tile)

        if door.is_trapped and knowledge.detected_trap:
            draw_trap_marker(tile)

This prevents:

combinatorial sprite explosion
leaking hidden info
3) Wall destruction (this is the real complexity)

You called it out correctly:

requires full dungeon knowledge + reconfiguration

Yes—and here’s the clean way to do it.

Step 1: Promote wall → transitional state

Instead of:

wall → floor

Do:

WALL → BREACHED_WALL → FLOOR
Step 2: BREACHED_WALL tile

This is a replacement tile, not overlay.

It:

is passable
still visually reads as “former wall”
Step 3: Connectivity update

When a wall is breached:

def breach_wall(x, y):
    tile = dungeon[x][y]

    tile.type = "breached_wall"
    tile.passable = True

    update_adjacency(x, y)

You only need to update local neighbors, not the whole map.

Step 4: Rendering BREACHED_WALL

This is where overlays come back in:

hole (center or edge depending on direction)
debris (1–3 pixels)
jagged edges

Important:

align breach to the direction of entry

Directional breach example
def draw_breach(tile, direction):
    if direction == "E":
        # hole on right edge
    elif direction == "N":
        # hole on top edge

This preserves spatial logic visually.

4) Portcullis and special doors

These benefit from partial openness, which you can fake visually without complex geometry.

Portcullis states:
closed → vertical bars
open → bars shifted up (leave gap)
broken → missing bars (random gaps)

No need for animation—just swap pixel patterns.

5) Overlay vs replacement rules (hard rules)

Use these consistently:

Overlay when:
cosmetic damage
interaction residue
known state markers
Replacement when:
passability changes
line-of-sight changes
adjacency changes
6) Hidden → revealed transitions (important for your design)

You want discovery to feel meaningful without visual cheating.

Before discovery:
render as normal wall
After discovery:
replace tile OR add minimal overlay

Example:

hidden door → becomes door tile
secret passage → becomes breached wall variant
7) World hex consistency (same system, different scale)

You can reuse the exact same logic:

overlay = camp, ruins, tracks
replacement = settlement, dungeon entrance

Example:

if hex.has_settlement:
    replace_with("settlement_tile")
else:
    apply_overlays(hex)
8) Keep your overlay system intentionally weak

This is counterintuitive, but important.

If overlays are too expressive:

you’ll start encoding mechanics visually
players will reverse-engineer hidden systems

So:

overlays should suggest, not declare

9) Minimal breach variants (don’t overbuild this)

You only need:

small breach (1-tile opening)
large breach (wider, rough)
collapsed (blocked but damaged)

That’s enough to cover:

digging
explosions
structural failure
10) What I would implement next (concrete steps)
Add BREACHED_WALL tile type
Add directional breach rendering
Convert your door system to state-based (if not already)
Add 3 overlays:
crack
debris
damage marks
Add knowledge-gated rendering flags

That gets you:

destructibility
subtle storytelling
no asset explosion
Final take

You’re building something closer to a simulation renderer than a sprite system.

The winning approach here is:

state-driven rendering
minimal visual vocabulary
strict separation of truth vs knowledge

You’re already aligned with that—just formalize it like above and you won’t paint yourself into a corner later.

If you want, next I can:

give you actual pixel coordinate patterns for:
breaches (directional)
cracks
portcullis states
and a drop-in renderer using Pillow that matches your 20×20 tiles exactly

That would let you test this visually in under an hour.