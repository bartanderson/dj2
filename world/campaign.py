# world/campaign.py
import uuid
from typing import List, Dict, Optional, Any

# ----------------------------------------------------------------------
# Region
# ----------------------------------------------------------------------
class Region:
    def __init__(self, id: str, name: str, terrain_tags: List[str],
                 faction_control: str, danger_level: int,
                 discovered: bool = False, explored: float = 0.0,
                 settlements: List[str] = None, dungeons: List[str] = None,
                 active_quests: List[str] = None):
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
            "active_quests": self.active_quests
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
            active_quests=data.get("active_quests", [])
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