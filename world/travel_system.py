# world\travel_system.py
class TravelSystem:
    def __init__(self, world_controller, ai_system):
        self.world = world_controller
        self.ai = ai_system  # DungeonAI instance
        self.current_path = []
        self.current_segment = 0
        self.encounter = None

    def start_journey(self, destination_id):
        """Begin travel to a location using path segments"""
        destination = self.world.world_map.get_location(destination_id)
        if not destination or not self.world.current_location:
            return False
        
        # Get path segments between locations
        self.current_path = self.get_path_segments(
            self.world.current_location, 
            destination
        )
        self.current_segment = 0
        return bool(self.current_path)

    def get_path_segments(self, start, end):
        """Get path segments from world data"""
        # In real implementation, this would use your path data
        segments = []
        current = start
        
        while current != end:
            # Find next connected location
            next_loc = self.get_next_location_toward(current, end)
            if not next_loc:
                break
                
            segment = {
                "start": current,
                "end": next_loc,
                "distance": self.calculate_distance(current, next_loc),
                "terrain": self.get_terrain_between(current, next_loc)
            }
            segments.append(segment)
            current = next_loc
            
        return segments

    def progress_journey(self):
        """Move to next path segment with AI narration"""
        if not self.current_path or self.current_segment >= len(self.current_path):
            return None
        
        segment = self.current_path[self.current_segment]
        self.current_segment += 1
        
        # Generate AI narration for this segment
        narration = self.ai.generate_travel_description(
            segment["start"],
            segment["end"],
            segment["terrain"]
        )
        
        # Generate potential encounter
        if random.random() < 0.3:  # 30% chance per segment
            self.encounter = self.generate_encounter(segment["terrain"])
            narration += f"\n\n{self.encounter['description']}"
        
        # Update world position
        self.world.current_location = segment["end"]
        
        return {
            "narration": narration,
            "encounter": self.encounter,
            "progress": f"{self.current_segment}/{len(self.current_path)}",
            "at_destination": self.current_segment == len(self.current_path)
        }

    def generate_encounter(self, terrain):
        """Create encounter with AI-generated description"""
        encounter_type = random.choice(["combat", "social", "exploration"])
        prompt = f"Generate a {terrain} {encounter_type} encounter during travel"
        description = self.ai.generate_text(prompt)
        
        return {
            "type": encounter_type,
            "description": description,
            "options": self.get_encounter_options(encounter_type)
        }

    def get_encounter_options(self, encounter_type):
        """Get resolution options for encounter"""
        options = {
            "combat": ["Fight", "Flee", "Negotiate"],
            "social": ["Talk", "Ignore", "Help"],
            "exploration": ["Investigate", "Document", "Ignore"]
        }
        return options.get(encounter_type, [])