# dungeon/generator.py - Enhanced dj.py with AI integration points
import random
import math
from typing import List, Dict, Any, Tuple, Optional, Union
from PIL import ImageFont, Image, ImageDraw
from dungeon.objects import FEATURE_TEMPLATES
from dungeon.renderer import DungeonRenderer 

class DungeonGenerator:
    # Cell bit flags
    NOTHING     = 0x00000000
    BLOCKED     = 0x00000001
    ROOM        = 0x00000002
    CORRIDOR    = 0x00000004
    PERIMETER   = 0x00000010
    ENTRANCE    = 0x00000020
    ROOM_ID     = 0x0000FFC0
    ARCH        = 0x00010000
    DOOR        = 0x00020000
    LOCKED      = 0x00040000
    TRAPPED     = 0x00080000
    SECRET      = 0x00100000
    PORTC       = 0x00200000
    STAIR_DN    = 0x00400000
    STAIR_UP    = 0x00800000
    LABEL       = 0xFF000000

    #OPENSPACE   = ROOM | CORRIDOR # note that any use of self.OPENSPACE was replaced by (self.ROOM | self.CORRIDOR)
    # it is a handy concept but created a slight issue in its use as it is a logical construct and the individual
    # items need to be treated individually and seperated by logic and am doing that
    DOORSPACE   = ARCH | DOOR | LOCKED | TRAPPED | SECRET | PORTC
    ESPACE      = ENTRANCE | DOORSPACE | 0xFF000000
    STAIRS      = STAIR_DN | STAIR_UP
    BLOCK_ROOM  = BLOCKED | ROOM
    BLOCK_CORR  = BLOCKED | PERIMETER | CORRIDOR
    BLOCK_DOOR  = BLOCKED | DOORSPACE

    @property
    def rooms(self):
        """Alias for room attribute to match test expectations"""
        return self.room

    @property
    def stairs(self):
        """Alias for stairList attribute to match test expectations"""
        return self.stairList

    @property
    def corridors(self):
        """Return list of corridor cells"""
        corridors = []
        for row in self.cell:
            for cell in row:
                if cell & self.CORRIDOR:
                    corridors.append(cell)
        return corridors

    def __init__(self, options=None):
        self.opts = {
            'seed': 'None',
            'n_rows': 39,
            'n_cols': 39,
            'dungeon_layout': 'None',
            'room_min': 3,
            'room_max': 9,
            'room_layout': 'Scattered',
            'corridor_layout': 'Bent',
            'remove_deadends': 50,
            'add_stairs': 2,
            'map_style': 'Standard',
            'cell_size': 18,
            'grid': 'Square'
        }
        
        if options:
            self.opts.update(options)

        print (self.opts['seed'])
            
        if self.opts['seed'] is None:
            self.opts['seed'] = random.randint(1, 100000)
            
        self.rand = random.Random(self.opts['seed'])
        
        # Direction vectors
        self.di = {'north': -1, 'south': 1, 'west': 0, 'east': 0}
        self.dj = {'north': 0, 'south': 0, 'west': -1, 'east': 1}
        self.dj_dirs = list(self.dj.keys())
        self.opposite = {
            'north': 'south', 'south': 'north',
            'west': 'east', 'east': 'west'
        }
        
        # Layout configurations
        self.dungeon_layout = {
            'Box': [[1, 1, 1], [1, 0, 1], [1, 1, 1]],
            'Cross': [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        }
        
        self.corridor_layout = {
            'Labyrinth': 0,
            'Bent': 50,
            'Straight': 100
        }
        
        # Stair configurations
        self.stair_end = {
            'north': {
                'walled': [[1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1]],
                'corridor': [[0, 0], [1, 0], [2, 0]],
                'stair': [0, 0],
                'next': [1, 0]
            },
            'south': {
                'walled': [[-1, -1], [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1]],
                'corridor': [[0, 0], [-1, 0], [-2, 0]],
                'stair': [0, 0],
                'next': [-1, 0]
            },
            'west': {
                'walled': [[-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0], [1, 1]],
                'corridor': [[0, 0], [0, 1], [0, 2]],
                'stair': [0, 0],
                'next': [0, 1]
            },
            'east': {
                'walled': [[-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [1, -1]],
                'corridor': [[0, 0], [0, -1], [0, -2]],
                'stair': [0, 0],
                'next': [0, -1]
            }
        }
        
        # Deadend cleaning configurations
        self.close_end = {
            'north': {
                'walled': [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1]],
                'close': [[0, 0]],
                'recurse': [-1, 0]
            },
            'south': {
                'walled': [[0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1]],
                'close': [[0, 0]],
                'recurse': [1, 0]
            },
            'west': {
                'walled': [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0]],
                'close': [[0, 0]],
                'recurse': [0, -1]
            },
            'east': {
                'walled': [[-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0]],
                'close': [[0, 0]],
                'recurse': [0, 1]
            }
        }
        
        # Initialize dungeon structures
        self.cell = None
        self.room = []
        self.doorList = []
        self.stairList = []
        self.n_rooms = 0
        self.last_room_id = 0

    def get_rooms(self):
        return self.room
        
    def get_stairs(self):
        return self.stairList
        
    # Add these properties with proper setters
    @property
    def rooms(self):
        return self.room
        
    @rooms.setter
    def rooms(self, value):
        self.room = value
        
    @property
    def stairs(self):
        return self.stairList
        
    @stairs.setter
    def stairs(self, value):
        self.stairList = value

def generate_legend_icons(self, icon_size=30):
    """Generate consistent legend icons using the new renderer"""
    try:
        # Try absolute import first
        from dungeon.renderer import DungeonRenderer
        return DungeonRenderer().generate_legend_icons(icon_size)
    except ImportError:
        # Fallback for test environment
        from src.dungeon.renderer import DungeonRenderer
        return DungeonRenderer().generate_legend_icons(icon_size)
    except Exception as e:
        print(f"Legend generation error: {str(e)}")
        return {}

    def create_dungeon(self):
        self.init_dungeon_size()
        print(f"Initialized dungeon size: {self.opts['n_rows']}x{self.opts['n_cols']}")  # Debug
        self.init_cells()
        print("Cells initialized")  # Debug
        self.emplace_rooms()
        print(f"Rooms placed: {len(self.room)}")  # Debug
        self.open_rooms()
        print("Doors placed")  # Debug
        self.label_rooms()
        self.corridors()

        if self.opts['add_stairs']:
            self.emplace_stairs()
            print(f"Stairs placed: {len(self.stairs)}")  # Debug
                
        self.clean_dungeon()
        # Return structured data for DungeonState
        return {
            'grid': self.cell,
            'stairs': self.stairs,
            'doors': self.doorList,
            'rooms': self.room,
            'n_rows': self.opts['n_rows'],
            'n_cols': self.opts['n_cols']
        }

    def init_dungeon_size(self):
        self.n_i = self.opts['n_rows'] // 2
        self.n_j = self.opts['n_cols'] // 2
        self.opts['n_rows'] = self.n_i * 2
        self.opts['n_cols'] = self.n_j * 2
        self.max_row = self.opts['n_rows'] - 1
        self.max_col = self.opts['n_cols'] - 1
        
        max_size = self.opts['room_max']
        min_size = self.opts['room_min']
        self.room_base = (min_size + 1) // 2
        self.room_radix = (max_size - min_size) // 2 + 1

    def init_cells(self):
        self.cell = [
            [self.NOTHING] * (self.opts['n_cols'] + 1)
            for _ in range(self.opts['n_rows'] + 1)
        ]
        
        layout = self.dungeon_layout.get(self.opts['dungeon_layout'])
        if layout:
            self.mask_cells(layout)
        elif self.opts['dungeon_layout'] == 'Round':
            self.round_mask()

    def mask_cells(self, mask):
        r_scale = len(mask) / (self.opts['n_rows'] + 1)
        c_scale = len(mask[0]) / (self.opts['n_cols'] + 1)
        
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                mask_r = int(r * r_scale)
                mask_c = int(c * c_scale)
                if (0 <= mask_r < len(mask) and (0 <= mask_c < len(mask[0]))):
                    if not mask[mask_r][mask_c]:
                        self.cell[r][c] = self.BLOCKED

    def round_mask(self):
        center_r = self.opts['n_rows'] // 2
        center_c = self.opts['n_cols'] // 2
        radius = center_c
        
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                d = math.sqrt((r - center_r) ** 2 + (c - center_c) ** 2)
                if d > radius:
                    self.cell[r][c] = self.BLOCKED

    def emplace_rooms(self):
        if self.opts['room_layout'] == 'Packed':
            self.pack_rooms()
        else:
            self.scatter_rooms()

    def pack_rooms(self):
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if self.cell[r][c] & self.ROOM:
                    continue
                if (i == 0 or j == 0) and self.rand.randint(0, 1):
                    continue
                self.emplace_room({'i': i, 'j': j})

    def scatter_rooms(self):
        n_rooms = self.alloc_rooms()
        for _ in range(n_rooms):
            self.emplace_room()

    def alloc_rooms(self):
        dungeon_area = self.opts['n_cols'] * self.opts['n_rows']
        room_area = self.opts['room_max'] ** 2
        return dungeon_area // room_area

    def emplace_room(self, proto=None):
        if self.n_rooms >= 999:
            return
        
        proto = self.set_room(proto)
        r1 = (proto['i'] * 2) + 1
        c1 = (proto['j'] * 2) + 1
        r2 = ((proto['i'] + proto['height']) * 2) - 1
        c2 = ((proto['j'] + proto['width']) * 2) - 1
        
        if r1 < 1 or r2 > self.max_row or c1 < 1 or c2 > self.max_col:
            return
        
        hit = self.sound_room(r1, c1, r2, c2)
        if hit.get('blocked') or hit:
            return
        
        room_id = self.n_rooms + 1
        self.n_rooms = room_id
        self.last_room_id = room_id
        
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.cell[r][c] & self.ENTRANCE:
                    self.cell[r][c] &= ~self.ESPACE
                elif self.cell[r][c] & self.PERIMETER:
                    self.cell[r][c] &= ~self.PERIMETER
                self.cell[r][c] |= self.ROOM | (room_id << 6)
        
        height = (r2 - r1 + 1) * 10
        width = (c2 - c1 + 1) * 10
        room_data = {
            'id': room_id, 'row': r1, 'col': c1,
            'north': r1, 'south': r2, 'west': c1, 'east': c2,
            'height': height, 'width': width, 'area': height * width,
            'door': {}
        }
        self.room.append(room_data)
        
        # Block corridors from room boundary
        for r in range(r1 - 1, r2 + 2):
            if r <= self.max_row:
                if not (self.cell[r][c1 - 1] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r][c1 - 1] |= self.PERIMETER
                if not (self.cell[r][c2 + 1] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r][c2 + 1] |= self.PERIMETER
        
        for c in range(c1 - 1, c2 + 2):
            if c <= self.max_col:
                if not (self.cell[r1 - 1][c] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r1 - 1][c] |= self.PERIMETER
                if not (self.cell[r2 + 1][c] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r2 + 1][c] |= self.PERIMETER

    def set_room(self, proto):
        if proto is None:
            proto = {}
        
        if 'height' not in proto:
            proto['height'] = self.room_base + self.rand.randint(0, self.room_radix - 1)
        
        if 'width' not in proto:
            proto['width'] = self.room_base + self.rand.randint(0, self.room_radix - 1)
        
        if 'i' not in proto:
            proto['i'] = self.rand.randint(0, self.n_i - proto['height'])
        
        if 'j' not in proto:
            proto['j'] = self.rand.randint(0, self.n_j - proto['width'])
        
        return proto

    def sound_room(self, r1, c1, r2, c2):
        hit = {}
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.cell[r][c] & self.BLOCKED:
                    return {'blocked': True}
                if self.cell[r][c] & self.ROOM:
                    room_id = (self.cell[r][c] & self.ROOM_ID) >> 6
                    hit[room_id] = hit.get(room_id, 0) + 1
        return hit

    def open_rooms(self):
        for room_id in range(1, self.n_rooms + 1):
            self.open_room(self.room[room_id - 1])
        if hasattr(self, 'connect'):
            del self.connect

    def open_room(self, room):
        sills = self.door_sills(room)
        if not sills:
            return
        
        n_opens = self.alloc_opens(room)
        if not hasattr(self, 'connect'):
            self.connect = {}
        
        for _ in range(n_opens):
            if not sills:
                break
            
            idx = self.rand.randint(0, len(sills) - 1)
            sill = sills.pop(idx)
            door_r = sill['door_r']
            door_c = sill['door_c']
            
            if self.cell[door_r][door_c] & self.DOORSPACE:
                continue
            
            if 'out_id' in sill and sill['out_id'] is not None:
                connect_key = ','.join(map(str, sorted([room['id'], sill['out_id']])))
                if connect_key in self.connect:
                    continue
                self.connect[connect_key] = True
            
            open_dir = sill['dir']
            for x in range(3):
                r = sill['sill_r'] + self.di[open_dir] * x
                c = sill['sill_c'] + self.dj[open_dir] * x
                self.cell[r][c] &= ~self.PERIMETER
                self.cell[r][c] |= self.ENTRANCE
            
            door_type = self.door_type()
            door = {'row': door_r, 'col': door_c}
            
            if door_type == self.ARCH:
                self.cell[door_r][door_c] |= self.ARCH
                door['key'] = 'arch'
            elif door_type == self.DOOR:
                self.cell[door_r][door_c] |= self.DOOR
                door['key'] = 'open'
            elif door_type == self.LOCKED:
                self.cell[door_r][door_c] |= self.LOCKED
                door['key'] = 'lock'
            elif door_type == self.TRAPPED:
                self.cell[door_r][door_c] |= self.TRAPPED
                door['key'] = 'trap'
            elif door_type == self.SECRET:
                self.cell[door_r][door_c] |= self.SECRET
                door['key'] = 'secret'
            elif door_type == self.PORTC:
                self.cell[door_r][door_c] |= self.PORTC
                door['key'] = 'portc'
            
            if 'out_id' in sill:
                door['out_id'] = sill['out_id']
            
            if open_dir not in room['door']:
                room['door'][open_dir] = []
            room['door'][open_dir].append(door)

    def alloc_opens(self, room):
        room_h = ((room['south'] - room['north']) // 2) + 1
        room_w = ((room['east'] - room['west']) // 2) + 1
        flumph = int(math.sqrt(room_w * room_h))
        return flumph + self.rand.randint(0, flumph - 1)

    def door_sills(self, room):
        sills = []
        dirs = ['north', 'south', 'west', 'east']
        
        for dir in dirs:
            if dir == 'north' and room['north'] >= 3:
                for c in range(room['west'], room['east'] + 1, 2):
                    sill = self.check_sill(room, room['north'], c, dir)
                    if sill:
                        sills.append(sill)
            
            elif dir == 'south' and room['south'] <= self.opts['n_rows'] - 3:
                for c in range(room['west'], room['east'] + 1, 2):
                    sill = self.check_sill(room, room['south'], c, dir)
                    if sill:
                        sills.append(sill)
            
            elif dir == 'west' and room['west'] >= 3:
                for r in range(room['north'], room['south'] + 1, 2):
                    sill = self.check_sill(room, r, room['west'], dir)
                    if sill:
                        sills.append(sill)
            
            elif dir == 'east' and room['east'] <= self.opts['n_cols'] - 3:
                for r in range(room['north'], room['south'] + 1, 2):
                    sill = self.check_sill(room, r, room['east'], dir)
                    if sill:
                        sills.append(sill)
        
        self.shuffle(sills)
        return sills

    def check_sill(self, room, sill_r, sill_c, dir):
        door_r = sill_r + self.di[dir]
        door_c = sill_c + self.dj[dir]
        
        if not (self.cell[door_r][door_c] & self.PERIMETER):
            return None
        if self.cell[door_r][door_c] & self.BLOCK_DOOR:
            return None
        
        out_r = door_r + self.di[dir]
        out_c = door_c + self.dj[dir]
        
        if out_r < 0 or out_r > self.opts['n_rows'] or out_c < 0 or out_c > self.opts['n_cols']:
            return None
        if self.cell[out_r][out_c] & self.BLOCKED:
            return None
        
        out_id = None
        if self.cell[out_r][out_c] & self.ROOM:
            out_id = (self.cell[out_r][out_c] & self.ROOM_ID) >> 6
            if out_id == room['id']:
                return None
        
        return {
            'sill_r': sill_r, 'sill_c': sill_c,
            'dir': dir, 'door_r': door_r, 'door_c': door_c,
            'out_id': out_id
        }

    def shuffle(self, arr):
        self.rand.shuffle(arr)

    def door_type(self):
        r = self.rand.randint(0, 109)
        if r < 15:
            return self.ARCH
        elif r < 60:
            return self.DOOR
        elif r < 75:
            return self.LOCKED
        elif r < 90:
            return self.TRAPPED
        elif r < 100:
            return self.SECRET
        else:
            return self.PORTC

    def label_rooms(self):
        for room in self.room:
            label = str(room['id'])
            label_len = len(label)
            label_r = (room['north'] + room['south']) // 2
            label_c = (room['west'] + room['east'] - label_len) // 2 + 1
            
            for i, char in enumerate(label):
                char_code = ord(char)
                self.cell[label_r][label_c + i] |= (char_code << 24)

    def corridors(self):
        for i in range(1, self.n_i):
            r = (i * 2) + 1
            for j in range(1, self.n_j):
                c = (j * 2) + 1
                if self.cell[r][c] & self.CORRIDOR:
                    continue
                self.tunnel(i, j)

    def tunnel(self, i, j, last_dir=None):
        dirs = self.tunnel_dirs(last_dir)
        for dir in dirs:
            if self.open_tunnel(i, j, dir):
                next_i = i + self.di[dir]
                next_j = j + self.dj[dir]
                self.tunnel(next_i, next_j, dir)

    def tunnel_dirs(self, last_dir):
        dirs = self.dj_dirs[:]
        self.shuffle(dirs)
        
        if last_dir and self.corridor_layout[self.opts['corridor_layout']] is not None:
            p = self.corridor_layout[self.opts['corridor_layout']]
            if self.rand.randint(0, 99) < p:
                dirs.insert(0, last_dir)
        return dirs

    def open_tunnel(self, i, j, dir):
        this_r = (i * 2) + 1
        this_c = (j * 2) + 1
        next_i = i + self.di[dir]
        next_j = j + self.dj[dir]
        next_r = (next_i * 2) + 1
        next_c = (next_j * 2) + 1
        mid_r = (this_r + next_r) // 2
        mid_c = (this_c + next_c) // 2
        
        if self.sound_tunnel(mid_r, mid_c, next_r, next_c):
            return self.delve_tunnel(this_r, this_c, next_r, next_c)
        return False

    def sound_tunnel(self, mid_r, mid_c, next_r, next_c):
        if next_r < 0 or next_r > self.opts['n_rows'] or next_c < 0 or next_c > self.opts['n_cols']:
            return False
        
        r1 = min(mid_r, next_r)
        r2 = max(mid_r, next_r)
        c1 = min(mid_c, next_c)
        c2 = max(mid_c, next_c)
        
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.cell[r][c] & self.BLOCK_CORR:
                    return False
        return True

    def delve_tunnel(self, r1, c1, r2, c2):
        min_r = min(r1, r2)
        max_r = max(r1, r2)
        min_c = min(c1, c2)
        max_c = max(c1, c2)
        
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                self.cell[r][c] &= ~self.ENTRANCE
                self.cell[r][c] |= self.CORRIDOR
        return True

    def emplace_stairs(self):
        n = self.opts['add_stairs']
        if not n:
            return
        
        ends = self.stair_ends()
        if not ends:
            return
        
        # Create exactly one up and one down stair when n=2
        if n == 2:
            # First stair: down
            if ends:
                end = ends.pop(0)
                r, c = end['row'], end['col']
                self.cell[r][c] |= self.STAIR_DN
                end['key'] = 'down'
                self.stairs.append(end)
            
            # Second stair: up
            if ends:
                end = ends.pop(0)
                r, c = end['row'], end['col']
                self.cell[r][c] |= self.STAIR_UP
                end['key'] = 'up'
                self.stairs.append(end)
        else:
            for i in range(n):
                if not ends:
                    break
                end = ends.pop(0)
                r, c = end['row'], end['col']
                
                # For n != 2, maintain existing random behavior
                stair_type = i if i < 2 else random.randint(0, 1)
                
                if stair_type == 0:
                    self.cell[r][c] |= self.STAIR_DN
                    end['key'] = 'down'
                else:
                    self.cell[r][c] |= self.STAIR_UP
                    end['key'] = 'up'
                
                self.stairs.append(end)

    def stair_ends(self):
        ends = []
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if self.cell[r][c] != self.CORRIDOR:
                    continue
                if self.cell[r][c] & self.STAIRS:
                    continue
                
                for dir, config in self.stair_end.items():
                    if self.check_tunnel(self.cell, r, c, config):
                        next_pos = config['next']
                        end = {
                            'row': r, 'col': c,
                            'next_row': r + next_pos[0],
                            'next_col': c + next_pos[1]
                        }
                        ends.append(end)
                        break
        return ends

    def clean_dungeon(self):
        if self.opts['remove_deadends']:
            self.remove_deadends()
        self.clean_disconnected_doors()
        self.fix_doors()
        self.empty_blocks()

    def remove_deadends(self):
        p = self.opts['remove_deadends']
        all = (p == 100)
        
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if not (self.cell[r][c] & (self.ROOM | self.CORRIDOR)):
                    continue
                if self.cell[r][c] & self.STAIRS:
                    continue
                if not all and self.rand.randint(0, 99) >= p:
                    continue
                if self.is_adjacent_to_door(r, c):
                    continue
                if self.corridor_leads_to_door(r, c):
                    continue
                self.collapse(r, c, self.close_end)

    def clean_disconnected_doors(self):
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.DOORSPACE:
                    connected = 0
                    for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']:
                            if self.cell[nr][nc] & ((self.ROOM | self.CORRIDOR) | self.DOORSPACE):
                                connected += 1
                    if connected < 2:
                        self.cell[r][c] &= ~self.DOORSPACE
                        self.cell[r][c] |= self.PERIMETER

    def collapse(self, r, c, xc):
        if not (self.cell[r][c] & (self.ROOM | self.CORRIDOR)):
            return
        
        for dir, config in xc.items():
            if not self.check_tunnel(self.cell, r, c, config):
                continue
            
            for pos in config['close']:
                self.cell[r + pos[0]][c + pos[1]] = self.NOTHING
            
            if 'recurse' in config:
                recurse = config['recurse']
                self.collapse(r + recurse[0], c + recurse[1], xc)

    def is_adjacent_to_door(self, r, c):
        for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']:
                if self.cell[nr][nc] & self.DOORSPACE:
                    return True
        return False

    def corridor_leads_to_door(self, r, c):
        if not (self.cell[r][c] & self.CORRIDOR):
            return False
        
        for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']:
                if self.cell[nr][nc] & self.DOORSPACE:
                    return True
        return False

    def check_tunnel(self, cell, r, c, check):
        if 'corridor' in check:
            for pos in check['corridor']:
                nr, nc = r + pos[0], c + pos[1]
                if not (0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']):
                    return False
                if cell[nr][nc] != self.CORRIDOR:
                    return False
        
        if 'walled' in check:
            for pos in check['walled']:
                nr, nc = r + pos[0], c + pos[1]
                if not (0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']):
                    continue
                if cell[nr][nc] & (self.ROOM | self.CORRIDOR):
                    return False
        return True

    def fix_doors(self):
        fixed = [[False] * (self.opts['n_cols'] + 1) for _ in range(self.opts['n_rows'] + 1)]
        self.doorList = []
        
        for room in self.room:
            for dir, doors in room['door'].items():
                shiny = []
                for door in doors:
                    r, c = door['row'], door['col']
                    if not (self.cell[r][c] & (self.ROOM | self.CORRIDOR)):
                        continue
                    
                    if fixed[r][c]:
                        shiny.append(door)
                        continue
                    
                    fixed[r][c] = True
                    if 'out_id' in door and door['out_id'] is not None:
                        out_dir = self.opposite[dir]
                        out_room = self.room[door['out_id'] - 1]
                        if out_dir not in out_room['door']:
                            out_room['door'][out_dir] = []
                        out_room['door'][out_dir].append(door)
                    
                    shiny.append(door)
                    self.doorList.append(door)
                
                room['door'][dir] = shiny

    def empty_blocks(self):
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.BLOCKED:
                    self.cell[r][c] = self.NOTHING

    def get_door_orientation(self, r, c):
        """Determine door orientation based on adjacent grid cells"""
        horizontal = (self.has_open_space(r, c-1) and 
                     self.has_open_space(r, c+1))
        vertical = (self.has_open_space(r-1, c) and 
                   self.has_open_space(r+1, c))
        
        if horizontal and not vertical:
            return 'horizontal'
        if vertical and not horizontal:
            return 'vertical'
        return 'horizontal'  # Default to horizontal

    def get_door_type(self, cell):
        if cell & self.ARCH:
            return 'arch'
        if cell & self.DOOR:
            return 'open'
        if cell & self.LOCKED:
            return 'lock'
        if cell & self.TRAPPED:
            return 'trap'
        if cell & self.SECRET:
            return 'secret'
        if cell & self.PORTC:
            return 'portc'
        return 'open'

    def has_open_space(self, r, c):
        if r < 0 or r > self.opts['n_rows'] or c < 0 or c > self.opts['n_cols']:
            return False
        return bool(self.cell[r][c] & (self.ROOM | self.CORRIDOR))


    def cell_label(self, cell):
        """Extract character label from cell"""
        char_code = (cell >> 24) & 0xFF
        return chr(char_code) if 32 <= char_code <= 126 else None

    def has_open_space(self, r, c):
        """Check if cell is open space"""
        if r < 0 or r > self.opts['n_rows'] or c < 0 or c > self.opts['n_cols']:
            return False
        return bool(self.cell[r][c] & (self.ROOM | self.CORRIDOR))



    def render_to_image(self):
        from dungeon.renderer import DungeonRenderer
        from dungeon.state import DungeonState
        from dungeon.renderers.image_renderer import ImageRenderer
        
        state = DungeonState(self)
        state.visibility.set_reveal_all(True)
        renderer = ImageRenderer(state)
        return renderer.render()


    def create_puzzle(self, location: Tuple[int, int], 
                    description: str, 
                    success_effect: str,
                    hints: Optional[List[str]] = None) -> str:
        """Create a new puzzle and register it with the state"""
        puzzle_id = f"puzzle_{location[0]}_{location[1]}"
        cell = self.dungeon_state.grid[location[0]][location[1]]
        
        # Store hints in cell metadata
        hint_data = hints or []
        cell.add_puzzle(puzzle_id, description, success_effect, hint_data)
        return puzzle_id

    def add_hint_to_puzzle(self, puzzle_id: str, hint: str, level: int = 0):
        """Add a hint to an existing puzzle"""
        for x in range(len(self.dungeon_state.grid)):
            for y in range(len(self.dungeon_state.grid[0])):
                cell = self.dungeon_state.grid[x][y]
                for obj in cell.objects:
                    if obj.get('type') == 'puzzle' and obj.get('puzzle_id') == puzzle_id:
                        if 'hints' not in obj:
                            obj['hints'] = []
                        obj['hints'].append({"text": hint, "level": level})

class EnhancedDungeonGenerator(DungeonGenerator):
    def __init__(self, options=None):
        DungeonGenerator.__init__(self, options)
        self.theme = options.get("theme", "dungeon")
        self.feature_density = options.get("feature_density", 0.1)
        
    def create_dungeon(self):
        dungeon_data = DungeonGenerator.create_dungeon()
        self.add_thematic_features()
        self.add_random_puzzles()  
        return dungeon_data

    def add_random_puzzles(self):
        """Add puzzles to various locations in the dungeon"""
        puzzle_density = 0.05  # 5% of open spaces get puzzles
        
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & (self.ROOM | self.CORRIDOR):
                    if random.random() < puzzle_density:
                        puzzle_type = random.choice(["riddle", "lever", "symbol", "pressure plate"])
                        puzzle_id = f"puzzle_{r}_{c}"
                        puzzle_data = {
                            "id": puzzle_id,
                            "type": puzzle_type,
                            "description": f"A {puzzle_type} puzzle",
                            "difficulty": random.choice(["easy", "medium", "hard"])
                        }
                        # Add to dungeon state
                        if hasattr(self, 'dungeon_state'):
                            self.dungeon_state.add_puzzle((r, c), puzzle_data)
        
    def add_thematic_features(self):
        """Add AI-selected features based on dungeon theme"""
        theme_features = {
            "cavern": ["water", "stalagmites", "fungus", "crystals"],
            "ruins": ["rubble", "broken_column", "cracks", "ancient_inscription"],
            "temple": ["altar", "holy_symbol", "offerings", "fresco"],
            "labyrinth": ["hedges", "fountain", "statue", "maze_marker"]
        }
        
        feature_pool = theme_features.get(self.theme, [])
        if not feature_pool:
            return
            
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & (self.ROOM | self.CORRIDOR):
                    if random.random() < self.feature_density:
                        feature_type = random.choice(feature_pool)
                        feature_data = FEATURE_TEMPLATES.get(feature_type, {})
                        # Add feature to dungeon state
                        if hasattr(self, 'dungeon_state'):
                            self.dungeon_state.add_feature((r, c), feature_type, feature_data)

    def generate_room_description(self, room_id: int) -> str:
        """Use AI to generate rich room description"""
        room = next((r for r in self.room if r['id'] == room_id), None)
        if not room:
            return "A mysterious room"
            
        prompt = (
            f"Describe a dungeon room in {self.theme} theme. "
            f"Size: {room['width']}x{room['height']} feet. "
            "Include sensory details and notable features."
        )
        # In practice, call your AI model here
        return "A dimly lit chamber with damp stone walls echoing with distant drips"

# Example usage
if __name__ == "__main__":
    options = {
        'seed': 12345,
        'n_rows': 39,
        'n_cols': 39,
        'room_min': 3,
        'room_max': 9,
        'corridor_layout': 'Bent',
        'remove_deadends': 50,
        'add_stairs': 2
    }
    
    generator = DungeonGenerator(options)
    generator.create_dungeon()
    image = generator.render_to_image()
    image.save('dungeon.png')