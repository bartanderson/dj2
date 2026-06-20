# task: review impact of changes to `generate_location_from_potential`
Generated 2026-06-20 by tools/analysis task_generator.

---

## Direct callers (confirmed)

_These call `{symbol}` directly. Any signature or behavior change here
requires updating each caller._

- (no direct callers found in graph)

## Impact zone (may need review)

_These symbols are in the reverse-closure neighborhood of `generate_location_from_potential`. Not all
will be affected by every change, but they depend on something in the call chain._

- (no additional impact zone symbols found)

---

## Notes

- Direct callers list is exact (from `graph_edges WHERE callee = ?`).
- Impact zone is a neighborhood superset - cross-check before treating
  every entry as a required change.
- Re-run this generator after changes land to verify the zone shrinks.
