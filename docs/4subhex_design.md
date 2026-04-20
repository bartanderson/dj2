Sub‑hex Exploration System – Technical Design
1. Hexagon Geometry & Data Model
1.1 Sub‑hex Grid
Each world hex contains a flat‑topped hexagon of sub‑hexes with radius 5 → 61 cells.

We'll use axial coordinates (q, r) where:

-5 ≤ q ≤ 5

-5 ≤ r ≤ 5

-5 ≤ q+r ≤ 5

Cell centers can be computed from (q, r) for rendering.

1.2 Data Structures
CampaignState gains:

python
self.subhex_maps: Dict[Tuple[int, int], SubhexMap] = {}
SubhexMap contains:

cells: Dict[Tuple[int, int], SubhexCell] (sparse storage for 61 cells)

generated: bool (lazy generation flag)

SubhexCell (dataclass):

python
class SubhexCell:
    terrain: str           # e.g., "forest", "river"
    discovered: bool = False
    explored: bool = False
    poi_id: Optional[str] = None
    modifications: List[Dict] = field(default_factory=list)
    image_overlay: Optional[str] = None
1.3 Party Position
Extend party_position to (col, row, mode, q, r) where mode is "world" or "subhex".

When mode == "world", (q, r) may be None or store the last entry edge.

2. Generation
Lazy generation: when a hex is entered (or first zoomed into), generate its 61 sub‑hex cells using a deterministic random seed based on world seed and hex coordinates.

Terrain distribution: the hex's terrain type determines the base probability for sub‑hex terrains (e.g., a "forest" hex has mostly forest sub‑hexes, plus some clearings, river banks, etc.).

POI placement: each hex has a chance to contain POIs (from the existing POI list). POIs are placed in specific sub‑hex cells.

3. Rendering
3.1 World View (unchanged)
Draw hex grid, terrain, major POIs (icons). Sub‑hex details are hidden.

Fog of war: whole hex is visible if hex.discovered == True.

3.2 Sub‑hex View
When mode == "subhex", the canvas switches to a zoomed‑in view of the current hex.

Draw the 61 sub‑hex cells using axial → pixel conversion.

For each cell:

If discovered: fill with terrain color/image.

If explored: draw a border (e.g., white outline).

If poi_id: draw an icon (e.g., camp, ruin).

If modifications: draw overlays (e.g., bridge sprite).

If not discovered: fill with fog (black or dark gray).

Draw party marker at current (q, r).

3.3 Switching Views
Command zoom in (world view) → set mode = "subhex", generate sub‑hex map if needed, redraw.

Command zoom out (sub‑hex view) → set mode = "world", redraw.

4. Movement Commands
4.1 Hex‑level Movement (go north, etc.)
Only allowed in mode == "world".

Updates (col, row); sets (q, r) to the entry edge cell (e.g., moving north enters at the south edge cell (0, -5)).

After move, mode remains "world".

4.2 Sub‑hex Movement (walk north, etc.)
Only allowed in mode == "subhex".

Compute neighbor axial coordinates: e.g., for flat‑top hexes, directions map to (q, r) offsets:

n: (0, -1)

ne: (1, -1)

se: (1, 0)

s: (0, 1)

sw: (-1, 1)

nw: (-1, 0)

Check if target cell exists (within bounds).

If not discovered, mark as discovered and explored; mark adjacent cells as discovered (fog of war).

Update party position to new (q, r).

If target cell is an edge cell (e.g., q or r at ±5) and the player types exit hex, they can return to world view.

4.3 Command Parsing
Extend `GameEngine._execute_interpretation_phase` to recognize:
zoom in, zoom out
walk n, walk ne, etc. (or reuse go with a flag – but better to have separate command to avoid confusion).

5. Dynamic Changes & Modifications
Modifications stored in SubhexCell.modifications as a list of dicts.

Each modification has:

type: e.g., "bridge", "camp", "barricade"

direction (for bridges): which direction it connects

permanent (bool): if true, never decays

expires (timestamp): for temporary modifications

image: URL of overlay sprite

Player actions (e.g., build bridge north) add a modification to the current cell.

Faction actions: background process (faction turn) can add/remove modifications in hexes where the faction is active.

Passability: when moving, check if the target cell has a modification that allows passage (e.g., bridge) or blocks it (e.g., barricade). The DM can also adjudicate creatively.

6. Integration with Existing Systems
GameEngine: New phases not needed extend `_execute_interpretation_phase` and `_execute_authority_phase` to handle walk and zoom.

Encounter generation: When entering a sub‑hex, use the sub‑hex's terrain and POI to generate encounters (similar to hex encounters but with finer granularity).

World state API: Add mode, subhex_cells (for current hex only) to /api/world-state response when mode == "subhex".

7. Performance Considerations
Lazy generation: only generate sub‑hex maps when a hex is zoomed into.

Use sparse storage (dictionary) for cells; 61 cells per hex is small.

Rendering only discovered cells (fog of war) reduces draw calls.

8. Implementation Phases
We will implement sub‑hex exploration in separate feature branches after Phase 4c is complete:

Phase 1: Data model & lazy generation – Add subhex_maps, implement generation, extend party position.

Phase 2: View switching & basic rendering – zoom in / zoom out, render sub‑hex grid (discovered cells only).

Phase 3: Sub‑hex movement & fog of war – walk command, discover adjacent cells, update party position.

Phase 4: POIs & modifications – Place POIs in sub‑hex cells, allow building bridges/camps, render overlays.

Phase 5: Faction actions & time effects – Background modification system.

9. Open Questions (to be resolved during design)
How to handle major POIs that span multiple sub‑hexes? (e.g., a large ruin could be represented by a group of cells.)

Should sub‑hex view support panning within the hex? (Initially no – just show the whole hex.)

How to transition from world view to sub‑hex view when entering a hex? (We'll use explicit zoom in command; later could auto‑zoom on entry.)

Next Steps
park this sub‑hex design and complete Phase 4c first. Once the core is stable, we can start implementing sub‑hex exploration as a major feature, using this design as the blueprint.

Agreed. it is indeed worthy as a feature to be integrated but that may inform us as to how in depth our current design wants to go since much of it may be redesigned to fit the subhex features. Maybe you can figure a way to slip back and forth since we should be able to operate in either. The subhex giving us the discoverability but still driven to the prime hex encounters driven by subhex navigation perhaps based on commands and time or circumstance we can specifically look at the subhex or let it bubble up as we explore?