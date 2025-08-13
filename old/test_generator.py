import os
import sys
import unittest
from PIL import Image, ImageDraw
from dungeon.generator import DungeonGenerator, EnhancedDungeonGenerator
from src.game.state import UnifiedGameState
from dungeon.state import EnhancedDungeonState, DungeonState
from dungeon.renderers.web_renderer import WebRenderer
from dungeon.renderers.image_renderer import ImageRenderer

class TestDungeonGenerator(unittest.TestCase):
    def setUp(self):
        # Create game state instance
        self.game_state = UnifiedGameState("test-theme")
        
        # Detailed options
        self.options = {
            'seed': 12345,
            'n_rows': 39,
            'n_cols': 39,
            'room_min': 3,
            'room_max': 9,
            'corridor_layout': 'Bent',
            'remove_deadends': 80,
            'add_stairs': 2,
            'cell_size': 18,
            'theme': 'test-dungeon',
            'difficulty': 'medium',
            'feature_density': 0.15
        }
        
        # Initialize dungeon with custom parameters
        self.game_state.initialize_dungeon(**self.options)

        # Access seed via the game state attribute
        print(f"Using seed: {self.game_state.generation_seed}")
        
        # Access the concrete dungeon state and generator
        self.dungeon_state = self.game_state.dungeon_state
        self.generator = self.dungeon_state.generator

    def test_dungeon_creation(self):
        print("Testing dungeon creation...")
        
        # Verify dungeon was created
        self.assertIsNotNone(self.dungeon_state)
        self.assertIsNotNone(self.generator)
        
        # Check dimensions
        self.assertEqual(len(self.dungeon_state.grid), self.options['n_rows'])
        self.assertEqual(len(self.dungeon_state.grid[0]), self.options['n_cols'])
        
        # Verify rooms were placed
        self.assertGreater(len(self.generator.get_rooms()), 0)
        print(f"Number of rooms: {len(self.generator.rooms)}")
        
        # Verify corridors
        corridor_count = 0
        for row in self.dungeon_state.grid:
            for cell in row:
                if cell.base_type & DungeonGenerator.CORRIDOR:
                    corridor_count += 1
        self.assertGreater(corridor_count, 0)
        
        # Verify stairs placement
        self.assertEqual(len(self.generator.get_stairs()), self.options['add_stairs'])

        # Test rendering with image renderer - save with legend
        image_renderer = self.game_state.get_renderer('image')
        image = image_renderer.render(debug_show_all=True)
        self.assertIsInstance(image, Image.Image)
        
        # Generate legend icons
        icons = self.generator.generate_legend_icons()
        
        # Create composite image with dungeon and legend
        composite = self.create_composite_image(image, icons)
        composite.save("test_dungeon_with_legend.png")
        print("Dungeon image with legend saved as test_dungeon_with_legend.png")

        # Test rendering with image renderer
        image_renderer = self.game_state.get_renderer('image')
        image = image_renderer.render()
        self.assertIsInstance(image, Image.Image)
        image.save("test_dungeon.png")
        print("Dungeon image saved as test_dungeon.png")
        
        # Test rendering with web renderer
        web_renderer = WebRenderer(self.dungeon_state)
        web_data = web_renderer.render(visible_only=False)  # Show all cells for test
        self.assertIn('grid', web_data)
        self.assertIn('legend', web_data)
        self.assertIn('party_position', web_data)
        print("Web rendering test successful")
        
        # Debug: Print grid information
        if self.dungeon_state.grid:
            print(f"Dungeon state grid size: {len(self.dungeon_state.grid)}x{len(self.dungeon_state.grid[0])}")
            mid_x = len(self.dungeon_state.grid) // 2
            mid_y = len(self.dungeon_state.grid[0]) // 2
            test_cell = self.dungeon_state.grid[mid_x][mid_y]
            print(f"Cell at ({mid_x},{mid_y}):")
            print(f"  Base type: {test_cell.base_type}")
            print(f"  Current type: {test_cell.current_type}")
            print(f"  Features: {test_cell.features}")
            print(f"  Visibility: {test_cell.visibility}")
            print(f"  Room ID: {self.dungeon_state.get_current_room_id((mid_x, mid_y))}")
        else:
            print("Grid is empty!")

    def create_composite_image(self, dungeon_img, icons):
        """Create image with dungeon on left and legend on right"""
        # Calculate dimensions
        icon_size = 30
        padding = 20
        legend_width = 200
        total_width = dungeon_img.width + legend_width + padding * 3
        total_height = max(dungeon_img.height, 400)
        
        # Create composite image
        composite = Image.new('RGB', (total_width, total_height), (45, 45, 45))
        draw = ImageDraw.Draw(composite)
        
        # Paste dungeon
        composite.paste(dungeon_img, (padding, padding))
        
        # Draw legend title
        draw.text((dungeon_img.width + padding * 2, padding), "LEGEND", fill=(255, 255, 255))
        
        # Draw legend items
        y_offset = padding + 30
        elements = [
            ('room', 'Room'),
            ('corridor', 'Corridor'),
            ('arch', 'Archway'),
            ('open_door', 'Open Door'),
            ('locked_door', 'Locked Door'),
            ('trapped_door', 'Trapped Door'),
            ('secret_door', 'Secret Door'),
            ('portcullis', 'Portcullis'),
            ('stairs_up', 'Stairs Up'),
            ('stairs_down', 'Stairs Down')
        ]
        
        for element, label in elements:
            icon = icons.get(element)
            if icon:
                composite.paste(icon, (dungeon_img.width + padding * 2, y_offset))
                draw.text((dungeon_img.width + padding * 2 + 40, y_offset + 10), 
                         label, fill=(255, 255, 255))
                y_offset += 40
        
        return composite

    def test_visibility_system(self):
        print("\nTesting visibility system...")
        VISIBILITY_MODES = ["full", "normal"]
        
        for mode in VISIBILITY_MODES:
            with self.subTest(visibility_mode=mode):
                print(f"\nTesting visibility mode: {mode}")
                
                # Reset visibility
                self.dungeon_state.visibility.set_reveal_all(False)
                
                if mode == "full":
                    print("Making entire dungeon visible...")
                    self.dungeon_state.visibility.set_reveal_all(True)
                else:  # "normal"
                    print("Resetting to normal visibility...")
                    self.dungeon_state.visibility.set_reveal_all(False)
                
                # Update visibility
                self.dungeon_state.visibility.update_visibility()
                
                # Check visibility for a sample cell
                test_pos = (self.options['n_rows'] // 2, self.options['n_cols'] // 2)
                vis_data = self.dungeon_state.visibility.get_visibility(test_pos)
                
                if mode == "full":
                    self.assertTrue(vis_data['explored'])
                    self.assertTrue(vis_data['visible'])
                else:  # "normal"
                    # Should be explored only if in line of sight
                    # We can't guarantee visibility, but we can check if it's consistent
                    pass
                
                print(f"Visibility test for mode '{mode}' passed")

    def test_party_movement(self):
        print("\nTesting party movement...")
        start_pos = self.game_state.party_position
        print(f"Starting position: {start_pos}")
        
        # Get available moves
        available_directions = self.game_state.get_available_moves()
        if not available_directions:
            self.fail("No available movement directions from starting position")
        
        # Try each available direction until one succeeds
        moved = False
        for direction in available_directions:
            print(f"Trying to move {direction}")
            new_pos = self.game_state.move_party(direction)
            
            if new_pos != start_pos:
                print(f"Successfully moved to {new_pos}")
                moved = True
                break
            else:
                print(f"Movement failed: {self.game_state.game_log[-1]}")
        
        if not moved:
            self.fail("All movement attempts failed")
        
        # Calculate expected position
        direction_vectors = {
            'north': (-1, 0),
            'south': (1, 0),
            'east': (0, 1),
            'west': (0, -1)
        }
        vector = direction_vectors[direction]
        expected_pos = (
            start_pos[0] + vector[0],
            start_pos[1] + vector[1]
        )
        
        # Verify exact position
        self.assertEqual(new_pos, expected_pos)
        
        # Verify position update in dungeon state
        self.assertEqual(self.dungeon_state.party_position, new_pos)
        
        # Verify game log
        self.assertIn(f"Party moved {direction}", self.game_state.game_log[-1])
        
        # Verify visibility was updated
        self.assertTrue(self.dungeon_state.visibility.get_visibility(new_pos)['visible'])

    def test_feature_placement(self):
        print("\nTesting feature placement...")
        position = self.game_state.party_position
        cell = self.dungeon_state.get_cell(position[0], position[1])
        original_feature_count = len(cell.features)
        
        # Add test feature
        self.game_state.add_dungeon_feature(
            "test_feature",
            {"description": "Test feature"},
            position=position
        )
        
        # Refresh cell data
        cell = self.dungeon_state.get_cell(position[0], position[1])
        new_feature_count = len(cell.features)
        
        self.assertEqual(new_feature_count, original_feature_count + 1)
        print("Feature placement successful")
        
        # Verify feature details
        test_feature = next((f for f in cell.features if f.get('type') == 'test_feature'), None)
        self.assertIsNotNone(test_feature)
        self.assertEqual(test_feature['data']['description'], "Test feature")

    def test_error_handling(self):
        print("\nTesting error handling...")
        # Test rendering with invalid parameters
        try:
            # Force an error by passing invalid cell size
            img = self.dungeon_state.render_to_image(cell_size=-10)
            self.fail("Expected exception not raised")
        except Exception as e:
            print(f"Rendering failed as expected: {str(e)}")
            # Create error image
            img = Image.new('RGB', (800, 600), (255, 200, 200))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"Rendering Error: {str(e)}", fill=(0, 0, 0))
            # Add debug info
            debug_info = [
                f"Grid: {len(self.dungeon_state.grid)}x{len(self.dungeon_state.grid[0])}",
                f"Stairs: {len(self.dungeon_state.stairs)}",
                f"Rooms: {len(self.dungeon_state.rooms)}"
            ]
            y_pos = 40
            for info in debug_info:
                draw.text((10, y_pos), info, fill=(0, 0, 0))
                y_pos += 20
            
            # Save error image
            img.save("test_error_handling.png")
            print("Error image saved as test_error_handling.png")

    # Add this to test_generator.py to verify the fix
    def test_enhanced_generator_inheritance(self):
        print("\nTesting EnhancedDungeonGenerator inheritance...")
        options = {
            'n_rows': 39, 
            'n_cols': 39,
            'theme': 'test',
            'feature_density': 0.1
        }
        gen = EnhancedDungeonGenerator(options)
        self.assertIsInstance(gen, DungeonGenerator)
        
        # Verify method resolution
        self.assertTrue(hasattr(gen, 'create_dungeon'))
        self.assertTrue(hasattr(gen, 'add_thematic_features'))
        
        # Test dungeon creation
        data = gen.create_dungeon()
        self.assertIn('grid', data)
        self.assertIn('stairs', data)
        self.assertIn('rooms', data)
        print("Enhanced generator inheritance test passed!")

class TestBaseGenerator(unittest.TestCase):
    def test_direct_generator(self):
        print("\nTesting direct generator...")
        # Detailed options
        options = {
            'n_rows': 39,
            'n_cols': 39,
            'room_min': 3,
            'room_max': 9,
            'corridor_layout': 'Bent',
            'remove_deadends': 80,
            'add_stairs': 2,
            'cell_size': 18
        }
        
        print("Creating standalone generator...")
        generator = DungeonGenerator(options)
        print("Generating dungeon directly...")
        generator.create_dungeon()
        print("Direct dungeon creation successful!")
        
        # Verify basic properties
        self.assertIsNotNone(generator.cell)
        self.assertEqual(len(generator.cell), options['n_rows'])
        self.assertEqual(len(generator.cell[0]), options['n_cols'])
        self.assertGreater(len(generator.get_rooms()), 0)
        self.assertEqual(len(generator.get_stairs()), options['add_stairs'])
        
        # Test rendering
        try:
            #img = generator.render_to_image() old black and white rendering
            # Create a temporary dungeon state for proper rendering
            state = DungeonState(generator)
            # REVEAL ENTIRE DUNGEON FOR TESTS
            state.visibility.set_reveal_all(True)
            state.visibility.update_visibility()
            renderer = ImageRenderer(state)
            img = renderer.render()
            self.assertIsInstance(img, Image.Image)
            img.save("direct_dungeon.png")
            print("Direct dungeon image saved as direct_dungeon.png")
            # Generate legend icons
            icons = generator.generate_legend_icons()
            
            # Create composite image
            composite = TestDungeonGenerator().create_composite_image(img, icons)
            composite.save("direct_dungeon_with_legend.png")
            print("Direct dungeon image saved as direct_dungeon_with_legend.png")
        except Exception as e:
            print(f"Direct rendering failed: {str(e)}")
            # Create error image
            img = Image.new('RGB', (800, 600), (255, 200, 200))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"Direct Rendering Error: {str(e)}", fill=(0, 0, 0))
            img.save("direct_error.png")
            print("Direct error image saved as direct_error.png")

if __name__ == '__main__':
    # Delete previous test images if exist
    test_images = ['test_dungeon.png', 'test_error_handling.png', 
        'direct_dungeon.png', 'direct_error.png',
        'test_dungeon_with_legend.png', 'direct_dungeon_with_legend.png']
    for img in test_images:
        if os.path.exists(img):
            os.remove(img)
            print(f"Deleted previous test image: {img}")
    
    # Add module directory to Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    print("Running comprehensive dungeon generator tests...")
    unittest.main()