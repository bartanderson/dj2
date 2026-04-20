# world/campaign.py
import uuid
import random
from typing import List, Dict, Optional, Any

# ----------------------------------------------------------------------
# Region
# ----------------------------------------------------------------------
class Region:
    def __init__(self, id: str, name: str, terrain_tags: List[str],
                 faction_control: str, danger_level: int,
                 discovered: bool = False, explored: float = 0.0,
                 settlements: List[str] = None, dungeons: List[str] = None,
                 active_quests: List[str] = None,
                 encounter_points: Dict[str, dict] = None):
        self.id = id
        self.name = name
        self.terrain_tags = terrain_tags
        self.faction_control = faction_control   # faction_id or "contested"
        self.danger_level = danger_level         # 1-20
        self.discovered = discovered
        self.explored = explored                  # percentage 0-100
        self.settlements = settlements or []      # list of potential location IDs
        self.dungeons = dungeons or []            # list of potential dungeon IDs
        self.active_quests = active_quests or []  # list of quest IDs
        self.encounter_points = encounter_points or {}   # dict of point_id → serialized EncounterPoint

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "terrain_tags": self.terrain_tags,
            "faction_control": self.faction_control,
            "danger_level": self.danger_level,
            "discovered": self.discovered,
            "explored": self.explored,
            "settlements": self.settlements,
            "dungeons": self.dungeons,
            "active_quests": self.active_quests,
            "encounter_points": self.encounter_points
        }

    @classmethod
    def from_json(cls, data: dict) -> 'Region':
        return cls(
            id=data["id"],
            name=data["name"],
            terrain_tags=data.get("terrain_tags", []),
            faction_control=data.get("faction_control", "contested"),
            danger_level=data.get("danger_level", 1),
            discovered=data.get("discovered", False),
            explored=data.get("explored", 0.0),
            settlements=data.get("settlements", []),
            dungeons=data.get("dungeons", []),
            active_quests=data.get("active_quests", []),
            encounter_points=data.get("encounter_points", {})
        )


# ----------------------------------------------------------------------
# Faction
# ----------------------------------------------------------------------
class Faction:
    def __init__(self, id: str, name: str, faction_type: List[str],
                 goals: List[str], resources: Dict[str, int],
                 relationships: Dict[str, str], territory: List[str],
                 notable_npcs: List[str], player_standing: int = 0):
        self.id = id
        self.name = name
        self.type = faction_type          # e.g., ["political", "religious"]
        self.goals = goals
        self.resources = resources        # keys: wealth, force, influence, secrets
        self.relationships = relationships  # faction_id -> "hostile|unfriendly|neutral|friendly|allied"
        self.territory = territory          # list of region_ids
        self.notable_npcs = notable_npcs
        self.player_standing = player_standing

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "goals": self.goals,
            "resources": self.resources,
            "relationships": self.relationships,
            "territory": self.territory,
            "notable_npcs": self.notable_npcs,
            "player_standing": self.player_standing
        }

    @classmethod
    def from_json(cls, data: dict) -> 'Faction':
        return cls(
            id=data["id"],
            name=data["name"],
            faction_type=data.get("type", []),
            goals=data.get("goals", []),
            resources=data.get("resources", {"wealth":1, "force":1, "influence":1, "secrets":1}),
            relationships=data.get("relationships", {}),
            territory=data.get("territory", []),
            notable_npcs=data.get("notable_npcs", []),
            player_standing=data.get("player_standing", 0)
        )


# ----------------------------------------------------------------------
# Quest
# ----------------------------------------------------------------------
class Quest:
    def __init__(self, id: str, archetype: str, patron: str, target: str,
                 opposition: List[str], stages: List[Dict],
                 consequences: Dict[str, Any], time_pressure: Dict[str, Any],
                 completed: bool = False):
        self.id = id
        self.archetype = archetype            # "recover", "destroy", etc.
        self.patron = patron                  # npc_id or faction_id
        self.target = target                  # location_id, npc_id, object_id
        self.opposition = opposition           # list of IDs
        self.stages = stages                    # list of dicts (order, type, location, completion_condition, rewards)
        self.consequences = consequences        # dict with success/failure/ignored
        self.time_pressure = time_pressure      # dict with exists, deadline, escalation
        self.completed = completed

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "archetype": self.archetype,
            "patron": self.patron,
            "target": self.target,
            "opposition": self.opposition,
            "stages": self.stages,
            "consequences": self.consequences,
            "time_pressure": self.time_pressure,
            "completed": self.completed
        }

    @classmethod
    def from_json(cls, data: dict) -> 'Quest':
        return cls(
            id=data["id"],
            archetype=data["archetype"],
            patron=data["patron"],
            target=data["target"],
            opposition=data.get("opposition", []),
            stages=data.get("stages", []),
            consequences=data.get("consequences", {}),
            time_pressure=data.get("time_pressure", {"exists": False}),
            completed=data.get("completed", False)
        )

# ----------------------------------------------------------------------
# Merchant System (Phase 1)
# ----------------------------------------------------------------------
from typing import Optional, Set, List, Dict, Any, Union, Literal
from datetime import datetime
import uuid

class MerchantPersonality:
    """Drives merchant behavior and pricing."""
    def __init__(self, greed: int = 5, paranoia: int = 3, honor: int = 5,
                 sociability: int = 5, risk_tolerance: int = 5):
        self.greed = greed          # 0-10
        self.paranoia = paranoia    # 0-10
        self.honor = honor          # 0-10
        self.sociability = sociability
        self.risk_tolerance = risk_tolerance

    def to_dict(self) -> dict:
        return {
            "greed": self.greed,
            "paranoia": self.paranoia,
            "honor": self.honor,
            "sociability": self.sociability,
            "risk_tolerance": self.risk_tolerance
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MerchantPersonality':
        return cls(
            greed=data.get("greed", 5),
            paranoia=data.get("paranoia", 3),
            honor=data.get("honor", 5),
            sociability=data.get("sociability", 5),
            risk_tolerance=data.get("risk_tolerance", 5)
        )

class MerchantConstraints:
    """Hard limits on merchant behavior."""
    def __init__(self, max_discount: float = 0.5, max_markup: float = 2.0,
                 refuses_if_hostile: bool = True, guards_present: bool = False,
                 barter_allowed: bool = True, credit_allowed: bool = False):
        self.max_discount = max_discount
        self.max_markup = max_markup
        self.refuses_if_hostile = refuses_if_hostile
        self.guards_present = guards_present
        self.barter_allowed = barter_allowed
        self.credit_allowed = credit_allowed

    def to_dict(self) -> dict:
        return {
            "max_discount": self.max_discount,
            "max_markup": self.max_markup,
            "refuses_if_hostile": self.refuses_if_hostile,
            "guards_present": self.guards_present,
            "barter_allowed": self.barter_allowed,
            "credit_allowed": self.credit_allowed
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MerchantConstraints':
        return cls(
            max_discount=data.get("max_discount", 0.5),
            max_markup=data.get("max_markup", 2.0),
            refuses_if_hostile=data.get("refuses_if_hostile", True),
            guards_present=data.get("guards_present", False),
            barter_allowed=data.get("barter_allowed", True),
            credit_allowed=data.get("credit_allowed", False)
        )

class VisibilityRule:
    """Rule for when an item becomes visible to a character."""
    def __init__(self, rule_type: Literal["affinity","trust","fear","respect","flag","quest"],
                 threshold: Union[int, str], hint: Optional[str] = None):
        self.type = rule_type
        self.threshold = threshold
        self.hint = hint

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "threshold": self.threshold,
            "hint": self.hint
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'VisibilityRule':
        return cls(
            rule_type=data["type"],
            threshold=data["threshold"],
            hint=data.get("hint")
        )

class MerchantItem:
    """An item that a merchant may sell."""
    def __init__(self, item_id: str, item_name: str, base_price: int,
                 steal_dc: int = 15, barter_value: int = None,
                 quantity: Optional[int] = None, tags: Set[str] = None,
                 visibility_rules: List[VisibilityRule] = None):
        self.id = item_id
        self.name = item_name
        self.base_price = int(base_price)
        self.steal_dc = steal_dc
        self.barter_value = barter_value if barter_value is not None else self.base_price // 2 # integer division
        self.quantity = quantity      # None = unlimited/elastic
        self.tags = tags or set()
        self.visibility_rules = visibility_rules or []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "base_price": self.base_price,
            "steal_dc": self.steal_dc,
            "barter_value": self.barter_value,
            "quantity": self.quantity,
            "tags": list(self.tags),
            "visibility_rules": [r.to_dict() for r in self.visibility_rules]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MerchantItem':
        return cls(
            item_id=data["id"],
            item_name=data["name"],
            base_price=data["base_price"],
            steal_dc=data.get("steal_dc", 15),
            barter_value=data.get("barter_value"),
            quantity=data.get("quantity"),
            tags=set(data.get("tags", [])),
            visibility_rules=[VisibilityRule.from_dict(r) for r in data.get("visibility_rules", [])]
        )

class MerchantRelationship:
    """Per‑character relationship with a merchant."""
    def __init__(self, merchant_id: str, character_id: str,
                 affinity: int = 0, trust: int = 0, fear: int = 0, respect: int = 0,
                 flags: Set[str] = None, last_interaction: datetime = None):
        self.merchant_id = merchant_id
        self.character_id = character_id
        self.affinity = affinity      # -10..10
        self.trust = trust            # -10..10
        self.fear = fear              # -10..10
        self.respect = respect        # -10..10
        self.flags = flags or set()
        self.last_interaction = last_interaction or datetime.now()

    def to_dict(self) -> dict:
        return {
            "merchant_id": self.merchant_id,
            "character_id": self.character_id,
            "affinity": self.affinity,
            "trust": self.trust,
            "fear": self.fear,
            "respect": self.respect,
            "flags": list(self.flags),
            "last_interaction": self.last_interaction.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MerchantRelationship':
        return cls(
            merchant_id=data["merchant_id"],
            character_id=data["character_id"],
            affinity=data.get("affinity", 0),
            trust=data.get("trust", 0),
            fear=data.get("fear", 0),
            respect=data.get("respect", 0),
            flags=set(data.get("flags", [])),
            last_interaction=datetime.fromisoformat(data["last_interaction"]) if "last_interaction" in data else None
        )

class PartyMerchantState:
    """Optional party‑level overlay (ambient tension, shared flags)."""
    def __init__(self, merchant_id: str, shared_flags: Set[str] = None,
                 heat_level: int = 0, last_visit: datetime = None):
        self.merchant_id = merchant_id
        self.shared_flags = shared_flags or set()
        self.heat_level = heat_level
        self.last_visit = last_visit or datetime.now()

    def to_dict(self) -> dict:
        return {
            "merchant_id": self.merchant_id,
            "shared_flags": list(self.shared_flags),
            "heat_level": self.heat_level,
            "last_visit": self.last_visit.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PartyMerchantState':
        return cls(
            merchant_id=data["merchant_id"],
            shared_flags=set(data.get("shared_flags", [])),
            heat_level=data.get("heat_level", 0),
            last_visit=datetime.fromisoformat(data["last_visit"]) if "last_visit" in data else None
        )

class Merchant:
    """Complete merchant definition."""
    def __init__(self, merchant_id: str, name: str, location: str,
                 personality: MerchantPersonality = None,
                 constraints: MerchantConstraints = None,
                 inventory: List[MerchantItem] = None,
                 faction: Optional[str] = None,
                 schedule: Optional[Dict] = None,
                 global_bias: int = 0):
        self.id = merchant_id
        self.name = name
        self.location = location        # e.g., "Adventurer's Respite", "traveling"
        self.personality = personality or MerchantPersonality()
        self.constraints = constraints or MerchantConstraints()
        self.inventory = inventory or []
        self.faction = faction
        self.schedule = schedule or {}
        self.global_bias = global_bias

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "personality": self.personality.to_dict(),
            "constraints": self.constraints.to_dict(),
            "inventory": [item.to_dict() for item in self.inventory],
            "faction": self.faction,
            "schedule": self.schedule,
            "global_bias": self.global_bias
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Merchant':
        return cls(
            merchant_id=data["id"],
            name=data["name"],
            location=data["location"],
            personality=MerchantPersonality.from_dict(data.get("personality", {})),
            constraints=MerchantConstraints.from_dict(data.get("constraints", {})),
            inventory=[MerchantItem.from_dict(i) for i in data.get("inventory", [])],
            faction=data.get("faction"),
            schedule=data.get("schedule", {}),
            global_bias=data.get("global_bias", 0)
        )

# ----------------------------------------------------------------------
# CampaignState
# ----------------------------------------------------------------------
class CampaignState:
    def __init__(self, world_seed: Optional[str] = None,
                 generation_timestamp: Optional[str] = None,
                 og_system_version: Optional[str] = None):
        self.world_seed = world_seed
        self.generation_timestamp = generation_timestamp
        self.og_system_version = og_system_version

        # World layers
        self.surface_regions: Dict[str, Region] = {}      # id -> Region
        self.underworld_layers: List[Dict] = []            # list of depth layers

        # Factions and quests
        self.factions: Dict[str, Faction] = {}            # id -> Faction
        self.quests: Dict[str, Quest] = {}                 # id -> Quest

        # Time tracking
        self.current_date = {
            "day": 1,
            "week": 1,
            "month": 1,
            "year": 1,
            "season": "spring",
            "moon": "waxing"
        }

        # Persistent changes
        self.persistent_changes = {
            "destroyed_locations": [],
            "dead_npcs": [],
            "claimed_territory": [],     # [{"faction_id": "region_id"}]
            "unlocked_dungeons": [],
            "sealed_dungeons": [],
            "active_plagues": [],
            "prosperous_settlements": []
        }

        # Calendar rules (from 14_campaign.json)
        self.days_per_week = 7
        self.weeks_per_month = 4
        self.months_per_year = 12
        self.seasons = ["spring", "summer", "fall", "winter"]
        self.moon_phases = ["new", "waxing", "full", "waning"]
        self.lunar_effects = {}

        # Game time (used by engine)
        self.game_time = 0
        self.time_factor = 1
        self.game_started = False

        # World hex/Party
        self.hex_grid = []                # list of hex dicts
        self.party_position = (0, 0)      # (col, row)
        self.grid_width = 0
        self.grid_height = 0
        self.hex_size = 0

        # Merchant system storage
        self.merchants: Dict[str, Merchant] = {}
        self.merchant_relationships: Dict[str, MerchantRelationship] = {}  # key: f"{merchant_id}:{character_id}"
        self.party_merchant_states: Dict[str, PartyMerchantState] = {}  # key: merchant_id

    def to_dict(self) -> dict:
        return {
            "world_seed": self.world_seed,
            "generation_timestamp": self.generation_timestamp,
            "og_system_version": self.og_system_version,
            "surface_regions": {rid: r.to_dict() for rid, r in self.surface_regions.items()},
            "underworld_layers": self.underworld_layers,
            "factions": {fid: f.to_dict() for fid, f in self.factions.items()},
            "quests": {qid: q.to_dict() for qid, q in self.quests.items()},
            "current_date": self.current_date,
            "persistent_changes": self.persistent_changes,
            "game_time": self.game_time,
            "time_factor": self.time_factor,
            "game_started": self.game_started
        }

    @classmethod
    def from_json(cls, data: dict) -> 'CampaignState':
        state = cls(
            world_seed=data.get("world_seed"),
            generation_timestamp=data.get("generation_timestamp"),
            og_system_version=data.get("og_system_version")
        )
        # Load regions
        for rid, rdata in data.get("surface_regions", {}).items():
            state.surface_regions[rid] = Region.from_json(rdata)
        # Load underworld layers
        state.underworld_layers = data.get("underworld_layers", [])
        # Load factions
        for fid, fdata in data.get("factions", {}).items():
            state.factions[fid] = Faction.from_json(fdata)
        # Load quests
        for qid, qdata in data.get("quests", {}).items():
            state.quests[qid] = Quest.from_json(qdata)
        # Load time data
        state.current_date.update(data.get("current_date", {}))
        state.persistent_changes.update(data.get("persistent_changes", {}))
        state.game_time = data.get("game_time", 0)
        state.time_factor = data.get("time_factor", 1)
        state.game_started = data.get("game_started", False)
        return state

    def get_active_quests(self) -> List[Quest]:
        """Return list of active (not completed) quests."""
        return [q for q in self.quests.values() if not q.completed]

    def load_calendar_rules(self, calendar_data: dict):
        """Load calendar configuration from 14_campaign.json"""
        if not calendar_data:
            return
        self.days_per_week = calendar_data.get("days_per_week", 7)
        self.weeks_per_month = calendar_data.get("weeks_per_month", 4)
        self.months_per_year = calendar_data.get("months_per_year", 12)
        self.seasons = calendar_data.get("seasons", self.seasons)
        # moon_phases is a list
        moon_phases = calendar_data.get("moon_phases")
        if moon_phases and isinstance(moon_phases, list):
            self.moon_phases = moon_phases
        # lunar_effects is a dict
        self.lunar_effects = calendar_data.get("lunar_effects", {})

    def get_current_date(self) -> dict:
        """Compute current date from game_time using calendar rules."""
        total_days = self.game_time // (24 * 60)  # minutes per day

        day_in_week = (total_days % self.days_per_week) + 1
        week = ((total_days // self.days_per_week) % self.weeks_per_month) + 1
        month = ((total_days // (self.days_per_week * self.weeks_per_month)) % self.months_per_year) + 1
        year = (total_days // (self.days_per_week * self.weeks_per_month * self.months_per_year)) + 1

        # Season (simplified: divide year into 4 equal parts)
        season_index = ((month - 1) * 4) // self.months_per_year
        if season_index >= len(self.seasons):
            season_index = 0
        season = self.seasons[season_index]

        # Moon phase (simplified: 28-day cycle)
        moon_cycle = 28  # days
        moon_day = total_days % moon_cycle
        if moon_day < 2:
            moon = "new"
        elif moon_day < 9:
            moon = "waxing"
        elif moon_day < 11:
            moon = "full"
        else:
            moon = "waning"

        return {
            "day": day_in_week,
            "week": week,
            "month": month,
            "year": year,
            "season": season,
            "moon": moon,
            "time_of_day": self._get_time_of_day()
        }

    def _get_time_of_day(self) -> str:
        """Return time of day based on minutes within current day."""
        minutes_in_day = self.game_time % (24 * 60)
        if minutes_in_day < 6 * 60:          # 0-6
            return "night"
        elif minutes_in_day < 12 * 60:       # 6-12
            return "morning"
        elif minutes_in_day < 18 * 60:       # 12-18
            return "afternoon"
        else:
            return "evening"

    def advance_time(self, minutes: int):
        """Advance game time by given minutes."""
        self.game_time += minutes
        # You can add logic here to trigger events, faction turns, etc. based on date changes.

    def get_hex(self, col, row):
        """Return the hex dict at grid coordinates (col, row) or None."""
        for h in self.hex_grid:
            if h['grid_x'] == col and h['grid_y'] == row:
                return h
        return None

    def get_or_generate_pois(self, hex):
        """Return list of POIs for a hex, generating lazily if needed."""
        if hex.get('pois') is not None:
            return hex['pois']
        # Use deterministic RNG based on world seed and hex coordinates
        rng = random.Random(f"{self.world_seed}:{hex['grid_x']},{hex['grid_y']}")
        num = rng.randint(0, 3)      # 0‑3 POIs per hex
        pois = []
        for i in range(num):
            poi_type = self._choose_poi_type(hex['terrain'], rng)
            pois.append({
                "id": f"poi_{hex['grid_x']}_{hex['grid_y']}_{i}",
                "type": poi_type,
                "name": self._generate_poi_name(poi_type, rng),
                "discovered": False,
                "description": None
            })
        hex['pois'] = pois
        return pois

    def _choose_poi_type(self, terrain, rng):
        """Choose a POI type based on terrain (simplified)."""
        # For now, just a static list; later we can make it more varied.
        types = ["settlement", "ruin", "lair", "resource", "shrine", "oddity"]
        return rng.choice(types)

    def _generate_poi_name(self, poi_type, rng):
        """Generate a simple name for a POI."""
        prefixes = ["Old", "New", "Dark", "Hidden", "Sacred", "Forgotten"]
        suffixes = ["Keep", "Tower", "Grove", "Mine", "Shrine", "Crossroads"]
        if poi_type == "settlement":
            return f"{rng.choice(prefixes)} {rng.choice(suffixes)}"
        else:
            return f"{rng.choice(prefixes)} {poi_type.capitalize()}"

    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        return self.merchants.get(merchant_id)

    def get_merchant_relationship(self, merchant_id: str, character_id: str) -> MerchantRelationship:
        key = f"{merchant_id}:{character_id}"
        if key not in self.merchant_relationships:
            self.merchant_relationships[key] = MerchantRelationship(merchant_id, character_id)
        return self.merchant_relationships[key]

    def get_party_merchant_state(self, merchant_id: str) -> PartyMerchantState:
        if merchant_id not in self.party_merchant_states:
            self.party_merchant_states[merchant_id] = PartyMerchantState(merchant_id)
        return self.party_merchant_states[merchant_id]

    def update_merchant_relationship(self, merchant_id: str, character_id: str,
                                     affinity_delta: int = 0, trust_delta: int = 0,
                                     fear_delta: int = 0, respect_delta: int = 0,
                                     add_flags: Set[str] = None, remove_flags: Set[str] = None):
        rel = self.get_merchant_relationship(merchant_id, character_id)
        rel.affinity = max(-10, min(10, rel.affinity + affinity_delta))
        rel.trust = max(-10, min(10, rel.trust + trust_delta))
        rel.fear = max(-10, min(10, rel.fear + fear_delta))
        rel.respect = max(-10, min(10, rel.respect + respect_delta))
        if add_flags:
            rel.flags.update(add_flags)
        if remove_flags:
            rel.flags.difference_update(remove_flags)
        rel.last_interaction = datetime.now()