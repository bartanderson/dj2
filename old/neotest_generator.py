import os
import sys
import unittest
import hashlib # for hashing images for comparison
from PIL import Image, ImageDraw
from dungeon_neo.generator_neo import DungeonGeneratorNeo
from dungeon_neo.state_neo import DungeonStateNeo
from dungeon_neo.renderer_neo import DungeonRendererNeo

class TestDungeonGeneratorNeo(unittest.TestCase):
    def setUp(self):
        # Detailed options for Neo generator
        self.options = {
            'seed': 12345,
            'n_rows': 39,
            'n_cols': 39,
            'room_min': 3,
            'room_max': 9,
            'corridor_layout': 'Bent',
            'remove_deadends': 80,
            'add_stairs': 2,
            'cell_size': 18
        }
        
        # Initialize Neo generator
        self.generator = DungeonGeneratorNeo(self.options)
        self.dungeon_state = DungeonStateNeo(self.generator)
        self.renderer = DungeonRendererNeo(cell_size=self.options['cell_size'])
        
        print(f"Using seed: {self.options['seed']}")

    def test_dungeon_creation(self):
        print("Testing dungeon creation with Neo system...")
        
        # Verify dungeon was created
        self.assertIsNotNone(self.dungeon_state)
        self.assertIsNotNone(self.generator)
        
        # Check dimensions - should be actual grid size
        self.assertEqual(self.dungeon_state.height, len(self.dungeon_state.grid))
        self.assertEqual(self.dungeon_state.width, len(self.dungeon_state.grid[0]))
        print(f"Dungeon dimensions: {self.dungeon_state.height}x{self.dungeon_state.width}")
        
        # Verify rooms were placed
        self.assertGreater(len(self.dungeon_state.rooms), 0)
        print(f"Number of rooms: {len(self.dungeon_state.rooms)}")
        
        # Verify corridors
        corridor_count = 0
        for row in self.dungeon_state.grid:
            for cell in row:
                if cell.base_type & DungeonGeneratorNeo.CORRIDOR:
                    corridor_count += 1
        self.assertGreater(corridor_count, 0)
        print(f"Corridor count: {corridor_count}")
        
        # Verify stairs placement
        self.assertEqual(len(self.dungeon_state.stairs), self.options['add_stairs'])
        print(f"Stairs placed: {len(self.dungeon_state.stairs)}")
        
        # Test rendering
        try:
            image = self.renderer.render(self.dungeon_state, debug_show_all=True)
            self.assertIsInstance(image, Image.Image)
            image.save("test_dungeon_neo.png")
            print("Neo dungeon image saved as test_dungeon_neo.png")
        except Exception as e:
            print(f"Rendering failed: {str(e)}")
            # Create error image for debugging
            img = Image.new('RGB', (800, 600), (255, 200, 200))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"Rendering Error: {str(e)}", fill=(0, 0, 0))
            img.save("test_dungeon_error.png")

    def test_visibility_rendering(self):
        print("\nTesting visibility rendering...")
        
        # Store initial state
        start_pos = self.dungeon_state.party_position
        print(f"Start position: {start_pos}")
        
        # Render initial visibility
        initial_img = self.renderer.render(
            self.dungeon_state, 
            debug_show_all=False,
            include_legend=False
        )
        initial_img.save("test_visibility_initial.png")
        
        # Move party south
        success, message = self.dungeon_state.move_party('south')
        self.assertTrue(success, f"Move south failed: {message}")
        after_south_pos = self.dungeon_state.party_position
        print(f"Position after south move: {after_south_pos}")
        
        # Render after first move
        after_south_img = self.renderer.render(
            self.dungeon_state, 
            debug_show_all=False,
            include_legend=False
        )
        after_south_img.save("test_visibility_after_south.png")
        
        # Move party east
        success, message = self.dungeon_state.move_party('east')
        self.assertTrue(success, f"Move east failed: {message}")
        final_pos = self.dungeon_state.party_position
        print(f"Final position: {final_pos}")
        
        # Render final visibility
        final_img = self.renderer.render(
            self.dungeon_state, 
            debug_show_all=False,
            include_legend=False
        )
        final_img.save("test_visibility_final.png")
        
        # Verify position changed
        self.assertNotEqual(start_pos, after_south_pos, "Party position didn't change after south move")
        self.assertNotEqual(after_south_pos, final_pos, "Party position didn't change after east move")
        
        # Compare visibility at key positions
        start_visibility = self.dungeon_state.visibility.get_visibility(start_pos)
        final_visibility = self.dungeon_state.visibility.get_visibility(final_pos)
        print(f"Visibility at start position: {start_visibility}")
        print(f"Visibility at final position: {final_visibility}")
        
        # Verify visibility changed at final position
        self.assertTrue(final_visibility['visible'], "Final position should be visible")
        
        # Generate diagnostic image
        self._generate_visibility_diagnostic(
            initial_img, 
            after_south_img, 
            final_img, 
            start_pos, 
            after_south_pos, 
            final_pos
        )
        
        print("Visibility rendering tests completed. Diagnostic images saved.")

    def _generate_visibility_diagnostic(self, img1, img2, img3, pos1, pos2, pos3):
        """Create a composite image showing visibility changes"""
        width = max(img1.width, img2.width, img3.width)
        height = img1.height + img2.height + img3.height + 60
        composite = Image.new('RGB', (width, height), (240, 240, 240))
        draw = ImageDraw.Draw(composite)
        
        # Add labels
        font = ImageFont.load_default()
        draw.text((10, 10), "Initial Visibility", fill=(0, 0, 0))
        composite.paste(img1, (0, 30))
        
        draw.text((10, 40 + img1.height), "After South Move", fill=(0, 0, 0))
        composite.paste(img2, (0, 60 + img1.height))
        
        draw.text((10, 70 + img1.height + img2.height), "After East Move", fill=(0, 0, 0))
        composite.paste(img3, (0, 90 + img1.height + img2.height))
        
        # Mark positions
        self._mark_position(composite, pos1, 30, "Start")
        self._mark_position(composite, pos2, 60 + img1.height, "After South")
        self._mark_position(composite, pos3, 90 + img1.height + img2.height, "After East")
        
        composite.save("test_visibility_diagnostic.png")
        print("Diagnostic image saved as test_visibility_diagnostic.png")

    def _mark_position(self, composite, pos, y_offset, label):
        """Mark a position on the image"""
        x = pos[1] * self.renderer.cell_size + self.renderer.cell_size // 2
        y = pos[0] * self.renderer.cell_size + self.renderer.cell_size // 2 + y_offset
        draw = ImageDraw.Draw(composite)
        
        # Draw crosshair
        size = self.renderer.cell_size // 2
        draw.line([(x-size, y), (x+size, y)], fill=(255, 0, 0), width=2)
        draw.line([(x, y-size), (x, y+size)], fill=(255, 0, 0), width=2)
        
        # Add label
        draw.text((x+10, y-10), label, fill=(255, 0, 0))

    def test_party_movement(self):
        print("\nTesting party movement in Neo system...")
        start_pos = self.dungeon_state.party_position
        print(f"Starting position: {start_pos}")
        
        # Test valid move
        success, message = self.dungeon_state.move_party('south')
        if success:
            new_pos = self.dungeon_state.party_position
            self.assertEqual(new_pos, (start_pos[0] + 1, start_pos[1]))
            print(f"Moved to: {new_pos}")
        else:
            print(f"Movement failed: {message}")
        
        # Test invalid move
        original_pos = self.dungeon_state.party_position
        success, message = self.dungeon_state.move_party('north')
        if not success:
            self.assertEqual(self.dungeon_state.party_position, original_pos)
            print(f"Correctly blocked invalid move: {message}")
        else:
            print("Unexpectedly allowed invalid move")

    def test_error_handling(self):
        print("\nTesting Neo error handling...")
        # Test rendering with invalid parameters
        try:
            # Force an error by passing invalid cell size
            self.renderer.cell_size = -10
            image = self.renderer.render(self.dungeon_state)
            self.fail("Expected exception not raised")
        except Exception as e:
            print(f"Rendering failed as expected: {str(e)}")
            # Create error image
            img = Image.new('RGB', (800, 600), (255, 200, 200))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"Neo Rendering Error: {str(e)}", fill=(0, 0, 0))
            img.save("test_error_handling_neo.png")
            print("Error image saved as test_error_handling_neo.png")

    def test_visibility_rendering(self):
        print("\nTesting visibility rendering...")
        
        # Create diagnostic directory
        os.makedirs("visibility_diagnostics", exist_ok=True)
        
        # Get starting position
        start_pos = self.dungeon_state.party_position
        print(f"Start position: {start_pos}")
        
        # Render initial state with party marker
        self._save_diagnostic_image("00_initial_state", start_pos)
        
        # Get valid moves
        valid_moves = self.dungeon_state.get_valid_moves()
        print(f"Valid moves: {valid_moves}")
        
        # Try all valid moves with diagnostics
        for i, direction in enumerate(valid_moves):
            print(f"\nTesting move {i+1}: {direction}")
            
            # Reset to start position
            self.dungeon_state.party_position = start_pos
            print(f"Reset to position: {self.dungeon_state.party_position}")
            
            # Render before move
            self._save_diagnostic_image(f"{i+1:02d}_before_{direction}", start_pos)
            
            # Attempt move
            success, message = self.dungeon_state.move_party(direction)
            new_pos = self.dungeon_state.party_position
            print(f"Move result: {success} - {message}")
            print(f"New position: {new_pos}")
            
            # Render after move
            self._save_diagnostic_image(f"{i+1:02d}_after_{direction}", new_pos)
            
            # Verify movement
            if success:
                self.assertNotEqual(start_pos, new_pos, "Position didn't change after move")
            
            # Check visibility at new position
            if success:
                visibility = self.dungeon_state.visibility.get_visibility(new_pos)
                print(f"Visibility at new position: {visibility}")
                self.assertTrue(visibility['visible'], "New position should be visible")
        
        print("\nVisibility diagnostics saved to 'visibility_diagnostics' folder")
    
    def _save_diagnostic_image(self, name, party_pos):
        """Render and save image with visual markers"""
        # Render dungeon with visibility
        img = self.renderer.render(
            self.dungeon_state, 
            debug_show_all=False,
            include_legend=False
        )
        
        # Create a copy to draw on
        diagnostic = img.copy()
        draw = ImageDraw.Draw(diagnostic)
        
        # Mark party position with red crosshair
        x_pixel = party_pos[1] * self.renderer.cell_size + self.renderer.cell_size // 2
        y_pixel = party_pos[0] * self.renderer.cell_size + self.renderer.cell_size // 2
        size = self.renderer.cell_size // 2
        
        # Draw crosshair
        draw.line([(x_pixel-size, y_pixel), (x_pixel+size, y_pixel)], 
                 fill=(255, 0, 0), width=2)
        draw.line([(x_pixel, y_pixel-size), (x_pixel, y_pixel+size)], 
                 fill=(255, 0, 0), width=2)
        
        # Add position label
        draw.text((x_pixel+10, y_pixel-10), f"Party: {party_pos}", 
                 fill=(255, 0, 0))
        
        # Save to diagnostics folder
        path = os.path.join("visibility_diagnostics", f"{name}.png")
        diagnostic.save(path)
        print(f"Saved diagnostic image: {path}")

class TestBaseGeneratorNeo(unittest.TestCase):
    def test_direct_generator(self):
        print("\nTesting direct Neo generator...")
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
        
        print("Creating standalone Neo generator...")
        generator = DungeonGeneratorNeo(options)
        print("Generating dungeon directly...")
        dungeon_data = generator.create_dungeon()
        print("Direct dungeon creation successful!")
        
        # Verify basic properties
        self.assertIn('grid', dungeon_data)
        self.assertIn('stairs', dungeon_data)
        self.assertIn('rooms', dungeon_data)
        self.assertEqual(len(dungeon_data['grid']), options['n_rows'])
        self.assertEqual(len(dungeon_data['grid'][0]), options['n_cols'])
        self.assertGreater(len(dungeon_data['rooms']), 0)
        self.assertEqual(len(dungeon_data['stairs']), options['add_stairs'])
        
        # Test rendering through state
        state = DungeonStateNeo(generator)
        renderer = DungeonRendererNeo(cell_size=options['cell_size'])
        try:
            image = renderer.render(state, debug_show_all=True)
            self.assertIsInstance(image, Image.Image)
            image.save("direct_dungeon_neo.png")
            print("Direct Neo dungeon image saved as direct_dungeon_neo.png")
        except Exception as e:
            print(f"Direct rendering failed: {str(e)}")
            # Create error image
            img = Image.new('RGB', (800, 600), (255, 200, 200))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), f"Direct Rendering Error: {str(e)}", fill=(0, 0, 0))
            img.save("direct_error_neo.png")

if __name__ == '__main__':
    # Delete previous test images if exist
    test_images = [
        'test_dungeon_neo.png', 
        'test_error_handling_neo.png',
        'direct_dungeon_neo.png'
    ]
    for img in test_images:
        if os.path.exists(img):
            os.remove(img)
            print(f"Deleted previous test image: {img}")
    
    print("Running comprehensive Neo dungeon generator tests...")
    unittest.main()