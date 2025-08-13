class DungeonGenerator {
    constructor(options = {}) {
        // Default options
        this.opts = {
            seed: Date.now(),
            n_rows: 39,
            n_cols: 39,
            dungeon_layout: 'None',
            room_min: 3,
            room_max: 9,
            room_layout: 'Scattered',
            corridor_layout: 'Bent',
            remove_deadends: 50,
            add_stairs: 2,
            map_style: 'Standard',
            cell_size: 18,
            grid: 'Square',
            ...options
        };

        // Cell bit flags
        this.NOTHING     = 0x00000000;
        this.BLOCKED     = 0x00000001;
        this.ROOM        = 0x00000002;
        this.CORRIDOR    = 0x00000004;
        this.PERIMETER   = 0x00000010;
        this.ENTRANCE    = 0x00000020;
        this.ROOM_ID     = 0x0000FFC0;
        this.ARCH        = 0x00010000;
        this.DOOR        = 0x00020000;
        this.LOCKED      = 0x00040000;
        this.TRAPPED     = 0x00080000;
        this.SECRET      = 0x00100000;
        this.PORTC       = 0x00200000;
        this.STAIR_DN    = 0x00400000;
        this.STAIR_UP    = 0x00800000;
        this.LABEL       = 0xFF000000;

        this.OPENSPACE   = this.ROOM | this.CORRIDOR;
        this.DOORSPACE   = this.ARCH | this.DOOR | this.LOCKED | this.TRAPPED | this.SECRET | this.PORTC;
        this.ESPACE      = this.ENTRANCE | this.DOORSPACE | 0xFF000000;
        this.STAIRS      = this.STAIR_DN | this.STAIR_UP;
        this.BLOCK_ROOM  = this.BLOCKED | this.ROOM;
        this.BLOCK_CORR  = this.BLOCKED | this.PERIMETER | this.CORRIDOR;
        this.BLOCK_DOOR  = this.BLOCKED | this.DOORSPACE;

        // Directions
        this.di = { north: -1, south: 1, west: 0, east: 0 };
        this.dj = { north: 0, south: 0, west: -1, east: 1 };
        this.dj_dirs = ['north', 'south', 'west', 'east'];
        this.opposite = { north: 'south', south: 'north', west: 'east', east: 'west' };

        // Layout configurations
        this.dungeon_layout = {
            'Box': [[1,1,1],[1,0,1],[1,1,1]],
            'Cross': [[0,1,0],[1,1,1],[0,1,0]]
        };

        this.corridor_layout = {
            'Labyrinth': 0,
            'Bent': 50,
            'Straight': 100
        };

        // Stair configurations
        this.stair_end = {
            north: { walled: [[1,-1],[0,-1],[-1,-1],[-1,0],[-1,1],[0,1],[1,1]], corridor: [[0,0],[1,0],[2,0]], stair: [0,0], next: [1,0] },
            south: { walled: [[-1,-1],[0,-1],[1,-1],[1,0],[1,1],[0,1],[-1,1]], corridor: [[0,0],[-1,0],[-2,0]], stair: [0,0], next: [-1,0] },
            west: { walled: [[-1,1],[-1,0],[-1,-1],[0,-1],[1,-1],[1,0],[1,1]], corridor: [[0,0],[0,1],[0,2]], stair: [0,0], next: [0,1] },
            east: { walled: [[-1,-1],[-1,0],[-1,1],[0,1],[1,1],[1,0],[1,-1]], corridor: [[0,0],[0,-1],[0,-2]], stair: [0,0], next: [0,-1] }
        };

        // Deadend cleaning configurations
        this.close_end = {
            north: { walled: [[0,-1],[1,-1],[1,0],[1,1],[0,1]], close: [[0,0]], recurse: [-1,0] },
            south: { walled: [[0,-1],[-1,-1],[-1,0],[-1,1],[0,1]], close: [[0,0]], recurse: [1,0] },
            west: { walled: [[-1,0],[-1,1],[0,1],[1,1],[1,0]], close: [[0,0]], recurse: [0,-1] },
            east: { walled: [[-1,0],[-1,-1],[0,-1],[1,-1],[1,0]], close: [[0,0]], recurse: [0,1] }
        };

        // Color chaining for drawing
        this.color_chain = {
            door: 'fill', label: 'fill', stair: 'wall', wall: 'fill', fill: 'black'
        };

        // Map styles
        this.map_style = {
            'Standard': { fill: '000000', open: 'FFFFFF', open_grid: 'CCCCCC' }
        };

        // Initialize random number generator
        this.seed = this.opts.seed;
        this.rand = this.seededRandom(this.seed);
    }

    seededRandom(seed) {
        return function() {
            seed = Math.sin(seed++) * 10000;
            return seed - Math.floor(seed);
        };
    }

    randInt(max) {
        return Math.floor(this.rand() * max);
    }

    shuffle(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(this.rand() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    createDungeon() {
        this.initDungeonSize();
        this.initCells();
        this.emplaceRooms();
        this.openRooms();
        this.labelRooms();
        this.corridors();
        if (this.opts.add_stairs) {
            this.emplaceStairs();
        }
        this.cleanDungeon();
        return this;
    }

    initDungeonSize() {
        this.n_i = Math.floor(this.opts.n_rows / 2);
        this.n_j = Math.floor(this.opts.n_cols / 2);
        this.opts.n_rows = this.n_i * 2;
        this.opts.n_cols = this.n_j * 2;
        this.max_row = this.opts.n_rows - 1;
        this.max_col = this.opts.n_cols - 1;
        this.n_rooms = 0;

        const max = this.opts.room_max;
        const min = this.opts.room_min;
        this.room_base = Math.floor((min + 1) / 2);
        this.room_radix = Math.floor((max - min) / 2) + 1;
    }

    initCells() {
        this.cell = Array.from({ length: this.opts.n_rows + 1 }, () => 
            Array(this.opts.n_cols + 1).fill(this.NOTHING)
        );

        const layout = this.dungeon_layout[this.opts.dungeon_layout];
        if (layout) {
            this.maskCells(layout);
        } else if (this.opts.dungeon_layout === 'Round') {
            this.roundMask();
        }
    }

    maskCells(mask) {
        const r_x = mask.length / (this.opts.n_rows + 1);
        const c_x = mask[0].length / (this.opts.n_cols + 1);
        
        for (let r = 0; r <= this.opts.n_rows; r++) {
            for (let c = 0; c <= this.opts.n_cols; c++) {
                const maskRow = Math.floor(r * r_x);
                const maskCol = Math.floor(c * c_x);
                if (maskRow < mask.length && maskCol < mask[0].length && !mask[maskRow][maskCol]) {
                    this.cell[r][c] = this.BLOCKED;
                }
            }
        }
    }

    roundMask() {
        const center_r = Math.floor(this.opts.n_rows / 2);
        const center_c = Math.floor(this.opts.n_cols / 2);
        const radius = center_c;
        
        for (let r = 0; r <= this.opts.n_rows; r++) {
            for (let c = 0; c <= this.opts.n_cols; c++) {
                const d = Math.sqrt(Math.pow(r - center_r, 2) + Math.pow(c - center_c, 2));
                if (d > radius) {
                    this.cell[r][c] = this.BLOCKED;
                }
            }
        }
    }

    emplaceRooms() {
        if (this.opts.room_layout === 'Packed') {
            this.packRooms();
        } else {
            this.scatterRooms();
        }
    }

    packRooms() {
        for (let i = 0; i < this.n_i; i++) {
            const r = (i * 2) + 1;
            for (let j = 0; j < this.n_j; j++) {
                const c = (j * 2) + 1;
                
                if (this.cell[r][c] & this.ROOM) continue;
                if ((i === 0 || j === 0) && this.randInt(2)) continue;
                
                const proto = { i, j };
                this.emplaceRoom(proto);
            }
        }
    }

    scatterRooms() {
        const n_rooms = this.allocRooms();
        for (let i = 0; i < n_rooms; i++) {
            this.emplaceRoom();
        }
    }

    allocRooms() {
        const dungeon_area = this.opts.n_cols * this.opts.n_rows;
        const room_area = this.opts.room_max * this.opts.room_max;
        return Math.floor(dungeon_area / room_area);
    }

    emplaceRoom(proto = {}) {
        if (this.n_rooms >= 999) return;
        
        proto = this.setRoom(proto);
        const r1 = (proto.i * 2) + 1;
        const c1 = (proto.j * 2) + 1;
        if (proto.height === undefined) {
            proto.height = this.room_base + this.randInt(this.room_radix);
        }
        const r2 = ((proto.i + proto.height) * 2) - 1;
        const c2 = ((proto.j + proto.width) * 2) - 1;
        
        if (r1 < 1 || r2 > this.max_row || c1 < 1 || c2 > this.max_col) return;
        
        const hit = this.soundRoom(r1, c1, r2, c2);
        if (hit.blocked) return;
        const hitList = Object.keys(hit);
        if (hitList.length > 0) return;
        
        const room_id = ++this.n_rooms;
        this.last_room_id = room_id;
        
        for (let r = r1; r <= r2; r++) {
            for (let c = c1; c <= c2; c++) {
                if (this.cell[r][c] & this.ENTRANCE) {
                    this.cell[r][c] &= ~this.ESPACE;
                } else if (this.cell[r][c] & this.PERIMETER) {
                    this.cell[r][c] &= ~this.PERIMETER;
                }
                this.cell[r][c] |= this.ROOM | (room_id << 6);
            }
        }
        
        const height = ((r2 - r1) + 1) * 10;
        const width = ((c2 - c1) + 1) * 10;
        this.room = this.room || [];
        this.room[room_id] = {
            id: room_id, row: r1, col: c1,
            north: r1, south: r2, west: c1, east: c2,
            height, width, area: height * width,
            door: {}
        };
        
        // Block corridors from room boundary
        for (let r = r1 - 1; r <= r2 + 1; r++) {
            if (!(this.cell[r][c1 - 1] & (this.ROOM | this.ENTRANCE))) {
                this.cell[r][c1 - 1] |= this.PERIMETER;
            }
            if (!(this.cell[r][c2 + 1] & (this.ROOM | this.ENTRANCE))) {
                this.cell[r][c2 + 1] |= this.PERIMETER;
            }
        }
        for (let c = c1 - 1; c <= c2 + 1; c++) {
            if (!(this.cell[r1 - 1][c] & (this.ROOM | this.ENTRANCE))) {
                this.cell[r1 - 1][c] |= this.PERIMETER;
            }
            if (!(this.cell[r2 + 1][c] & (this.ROOM | this.ENTRANCE))) {
                this.cell[r2 + 1][c] |= this.PERIMETER;
            }
        }
    }

    setRoom(proto) {
        if (proto.height === undefined) {
            proto.height = this.room_base + this.randInt(this.room_radix);
        }
        if (proto.width === undefined) {
            proto.width = this.room_base + this.randInt(this.room_radix);
        }
        if (proto.i === undefined) {
            proto.i = this.randInt(this.n_i - proto.height);
        }
        if (proto.i !== undefined) {
            const a = this.n_i - this.room_base - proto.i;
            const r = Math.max(0, Math.min(a, this.room_radix));
            proto.height = this.room_base + this.randInt(r);
        }
        if (proto.j === undefined) {
            proto.j = this.randInt(this.n_j - proto.width);
        }
        return proto;
    }

    soundRoom(r1, c1, r2, c2) {
        const hit = {};
        for (let r = r1; r <= r2; r++) {
            for (let c = c1; c <= c2; c++) {
                if (this.cell[r][c] & this.BLOCKED) {
                    return { blocked: true };
                }
                if (this.cell[r][c] & this.ROOM) {
                    const id = (this.cell[r][c] & this.ROOM_ID) >> 6;
                    hit[id] = (hit[id] || 0) + 1;
                }
            }
        }
        return hit;
    }

    openRooms() {
        for (let id = 1; id <= this.n_rooms; id++) {
            this.openRoom(this.room[id]);
        }
        delete this.connect;
    }

    openRoom(room) {
        const sills = this.doorSills(room);
        if (!sills.length) return;
        
        const n_opens = this.allocOpens(room);
        this.connect = this.connect || {};
        
        for (let i = 0; i < n_opens; i++) {
            if (!sills.length) break;
            const idx = this.randInt(sills.length);
            const sill = sills.splice(idx, 1)[0];
            
            const door_r = sill.door_r;
            const door_c = sill.door_c;
            if (this.cell[door_r][door_c] & this.DOORSPACE) continue;
            
            if (sill.out_id) {
                const connectKey = [room.id, sill.out_id].sort().join(',');
                if (this.connect[connectKey]) continue;
                this.connect[connectKey] = true;
            }
            
            const open_dir = sill.dir;
            for (let x = 0; x < 3; x++) {
                const r = sill.sill_r + (this.di[open_dir] * x);
                const c = sill.sill_c + (this.dj[open_dir] * x);
                this.cell[r][c] &= ~this.PERIMETER;
                this.cell[r][c] |= this.ENTRANCE;
            }
            
            const doorType = this.doorType();
            const door = { row: door_r, col: door_c };
            let doorBits;
            
            switch (doorType) {
                case this.ARCH:
                    doorBits = this.ARCH;
                    door.key = 'arch';
                    door.type = 'Archway';
                    break;
                case this.DOOR:
                    doorBits = this.DOOR;
                    door.key = 'open';
                    door.type = 'Unlocked Door';
                    break;
                case this.LOCKED:
                    doorBits = this.LOCKED;
                    door.key = 'lock';
                    door.type = 'Locked Door';
                    break;
                case this.TRAPPED:
                    doorBits = this.TRAPPED;
                    door.key = 'trap';
                    door.type = 'Trapped Door';
                    break;
                case this.SECRET:
                    doorBits = this.SECRET;
                    door.key = 'secret';
                    door.type = 'Secret Door';
                    break;
                case this.PORTC:
                    doorBits = this.PORTC;
                    door.key = 'portc';
                    door.type = 'Portcullis';
                    break;
            }
            
            this.cell[door_r][door_c] |= doorBits;

            if (sill.out_id) {
                door.out_id = sill.out_id;
            }
            
            room.door[open_dir] = room.door[open_dir] || [];
            room.door[open_dir].push(door);
        }
    }

    allocOpens(room) {
        const room_h = ((room.south - room.north) / 2) + 1;
        const room_w = ((room.east - room.west) / 2) + 1;
        const flumph = Math.floor(Math.sqrt(room_w * room_h));
        return flumph + this.randInt(flumph);
    }

    doorSills(room) {
        const sills = [];
        const dirs = ['north', 'south', 'west', 'east'];
        
        dirs.forEach(dir => {
            let r, c;
            if (dir === 'north' && room.north >= 3) {
                for (c = room.west; c <= room.east; c += 2) {
                    const sill = this.checkSill(room, room.north, c, dir);
                    if (sill) sills.push(sill);
                }
            }
            if (dir === 'south' && room.south <= this.opts.n_rows - 3) {
                for (c = room.west; c <= room.east; c += 2) {
                    const sill = this.checkSill(room, room.south, c, dir);
                    if (sill) sills.push(sill);
                }
            }
            if (dir === 'west' && room.west >= 3) {
                for (r = room.north; r <= room.south; r += 2) {
                    const sill = this.checkSill(room, r, room.west, dir);
                    if (sill) sills.push(sill);
                }
            }
            if (dir === 'east' && room.east <= this.opts.n_cols - 3) {
                for (r = room.north; r <= room.south; r += 2) {
                    const sill = this.checkSill(room, r, room.east, dir);
                    if (sill) sills.push(sill);
                }
            }
        });
        
        return this.shuffle(sills);
    }

    checkSill(room, sill_r, sill_c, dir) {
        const door_r = sill_r + this.di[dir];
        const door_c = sill_c + this.dj[dir];
        if (!(this.cell[door_r][door_c] & this.PERIMETER)) return null;
        if (this.cell[door_r][door_c] & this.BLOCK_DOOR) return null;
        
        const out_r = door_r + this.di[dir];
        const out_c = door_c + this.dj[dir];
        if (out_r < 0 || out_r > this.opts.n_rows || out_c < 0 || out_c > this.opts.n_cols) return null;
        if (this.cell[out_r][out_c] & this.BLOCKED) return null;
        
        let out_id = null;
        if (this.cell[out_r][out_c] & this.ROOM) {
            out_id = (this.cell[out_r][out_c] & this.ROOM_ID) >> 6;
            if (out_id === room.id) return null;
        }
        
        return {
            sill_r, sill_c, dir, door_r, door_c, out_id
        };
    }

    doorType() {
        const r = this.randInt(110);
        if (r < 15) return this.ARCH;
        if (r < 60) return this.DOOR;
        if (r < 75) return this.LOCKED;
        if (r < 90) return this.TRAPPED;
        if (r < 100) return this.SECRET;
        return this.PORTC;
    }

    labelRooms() {
        for (let id = 1; id <= this.n_rooms; id++) {
            const room = this.room[id];
            const label = id.toString();
            const len = label.length;
            const label_r = Math.floor((room.north + room.south) / 2);
            const label_c = Math.floor((room.west + room.east - len) / 2) + 1;
            
            for (let c = 0; c < len; c++) {
                const charCode = label.charCodeAt(c);
                this.cell[label_r][label_c + c] |= (charCode << 24);
            }
        }
    }

    corridors() {
        for (let i = 1; i < this.n_i; i++) {
            const r = (i * 2) + 1;
            for (let j = 1; j < this.n_j; j++) {
                const c = (j * 2) + 1;
                if (this.cell[r][c] & this.CORRIDOR) continue;
                this.tunnel(i, j);
            }
        }
    }

    tunnel(i, j, last_dir) {
        const dirs = this.tunnelDirs(last_dir);
        for (const dir of dirs) {
            if (this.openTunnel(i, j, dir)) {
                const next_i = i + this.di[dir];
                const next_j = j + this.dj[dir];
                this.tunnel(next_i, next_j, dir);
            }
        }
    }

    tunnelDirs(last_dir) {
        const dirs = [...this.dj_dirs];
        this.shuffle(dirs);
        const p = this.corridor_layout[this.opts.corridor_layout];
        if (last_dir && p !== undefined && this.randInt(100) < p) {
            dirs.unshift(last_dir);
        }
        return dirs;
    }

    openTunnel(i, j, dir) {
        const this_r = (i * 2) + 1;
        const this_c = (j * 2) + 1;
        const next_i = i + this.di[dir];
        const next_j = j + this.dj[dir];
        const next_r = (next_i * 2) + 1;
        const next_c = (next_j * 2) + 1;
        const mid_r = (this_r + next_r) / 2;
        const mid_c = (this_c + next_c) / 2;
        
        if (this.soundTunnel(mid_r, mid_c, next_r, next_c)) {
            return this.delveTunnel(this_r, this_c, next_r, next_c);
        }
        return false;
    }

    soundTunnel(mid_r, mid_c, next_r, next_c) {
        if (next_r < 0 || next_r > this.opts.n_rows || next_c < 0 || next_c > this.opts.n_cols) {
            return false;
        }
        
        const r1 = Math.min(mid_r, next_r);
        const r2 = Math.max(mid_r, next_r);
        const c1 = Math.min(mid_c, next_c);
        const c2 = Math.max(mid_c, next_c);
        
        for (let r = r1; r <= r2; r++) {
            for (let c = c1; c <= c2; c++) {
                if (this.cell[r][c] & this.BLOCK_CORR) {
                    return false;
                }
            }
        }
        return true;
    }

    delveTunnel(r1, c1, r2, c2) {
        const min_r = Math.min(r1, r2);
        const max_r = Math.max(r1, r2);
        const min_c = Math.min(c1, c2);
        const max_c = Math.max(c1, c2);
        
        for (let r = min_r; r <= max_r; r++) {
            for (let c = min_c; c <= max_c; c++) {
                this.cell[r][c] &= ~this.ENTRANCE;
                this.cell[r][c] |= this.CORRIDOR;
            }
        }
        return true;
    }

    emplaceStairs() {
        const n = this.opts.add_stairs;
        if (!n) return;
        
        const ends = this.stairEnds();
        if (!ends.length) return;
        
        for (let i = 0; i < n; i++) {
            if (!ends.length) break;
            const idx = this.randInt(ends.length);
            const end = ends.splice(idx, 1)[0];
            
            const r = end.row;
            const c = end.col;
            const type = i < 2 ? i : this.randInt(2);
            const stair = { row: r, col: c, ...end };
            
            if (type === 0) {
                this.cell[r][c] |= this.STAIR_DN;
                stair.key = 'down';
            } else {
                this.cell[r][c] |= this.STAIR_UP;
                stair.key = 'up';
            }
            
            this.stairs = this.stairs || [];
            this.stairs.push(stair);
        }
    }
    
    stairEnds() {
        const ends = [];
        for (let i = 0; i < this.n_i; i++) {
            const r = (i * 2) + 1;
            for (let j = 0; j < this.n_j; j++) {
                const c = (j * 2) + 1;
                if (this.cell[r][c] !== this.CORRIDOR) continue;
                if (this.cell[r][c] & this.STAIRS) continue;
                
                for (const dir in this.stair_end) {
                    if (this.checkTunnel(this.cell, r, c, this.stair_end[dir])) {
                        const next = this.stair_end[dir].next;
                        ends.push({
                            row: r, col: c,
                            next_row: r + next[0],
                            next_col: c + next[1]
                        });
                        break;
                    }
                }
            }
        }
        return ends;
    }

    cleanDungeon() {
        if (this.opts.remove_deadends) {
            this.removeDeadends();
        }
        this.cleanDisconnectedDoors();
        this.fixDoors();
        this.emptyBlocks();
    }

    removeDeadends() {
        const p = this.opts.remove_deadends;
        if (!p) return;
        const all = p === 100;

        for (let i = 0; i < this.n_i; i++) {
            const r = (i * 2) + 1;
            for (let j = 0; j < this.n_j; j++) {
                const c = (j * 2) + 1;
                if (!(this.cell[r][c] & this.OPENSPACE)) continue;
                if (this.cell[r][c] & this.STAIRS) continue;
                if (!all && this.randInt(100) >= p) continue;
                
                // Skip removal if cell is adjacent to a door
                if (this.isAdjacentToDoor(r, c)) continue;

                // Add: Skip removal if this corridor leads to a door
                if (this.corridorLeadsToDoor(r, c)) continue;

                this.collapse(r, c, this.close_end);
            }
        }
    }

    // helper method to check if corridor leads to a door
    corridorLeadsToDoor(r, c) {
        if (!(this.cell[r][c] & this.CORRIDOR)) return false;
        
        const neighbors = [
            [0, -1], [0, 1], [-1, 0], [1, 0]  // west, east, north, south
        ];
        
        for (const [dr, dc] of neighbors) {
            const nr = r + dr;
            const nc = c + dc;
            if (nr >= 0 && nr <= this.opts.n_rows && nc >= 0 && nc <= this.opts.n_cols) {
                if (this.cell[nr][nc] & this.DOORSPACE) {
                    return true;
                }
            }
        }
        return false;
    }

    // method to clean up disconnected doors
    cleanDisconnectedDoors() {
        for (let r = 0; r <= this.opts.n_rows; r++) {
            for (let c = 0; c <= this.opts.n_cols; c++) {
                if (this.cell[r][c] & this.DOORSPACE) {
                    let connectedSpaces = 0;
                    
                    // Check all 4 directions
                    const neighbors = [
                        [0, -1], [0, 1], [-1, 0], [1, 0]
                    ];
                    
                    for (const [dr, dc] of neighbors) {
                        const nr = r + dr;
                        const nc = c + dc;
                        if (nr >= 0 && nr <= this.opts.n_rows && nc >= 0 && nc <= this.opts.n_cols) {
                            if (this.cell[nr][nc] & (this.OPENSPACE | this.DOORSPACE)) {
                                connectedSpaces++;
                            }
                        }
                    }
                    
                    // Remove door if not connected to at least 2 spaces (should connect two areas)
                    if (connectedSpaces < 2) {
                        this.cell[r][c] &= ~this.DOORSPACE;
                        this.cell[r][c] |= this.PERIMETER;  // Convert back to wall
                    }
                }
            }
        }
    }

        
    collapse(r, c, xc) {
        if (!(this.cell[r][c] & this.OPENSPACE)) return;
        
        //if (this.isAdjacentToDoor(r, c)) return; // Skip removal if this cell is adjacent to a door

        for (const dir in xc) {
            const check = xc[dir];
            if (!this.checkTunnel(this.cell, r, c, check)) continue;

            for (const p of check.close) {
                this.cell[r + p[0]][c + p[1]] = this.NOTHING;
            }

            if (check.recurse) {
                const recurse = check.recurse;
                this.collapse(r + recurse[0], c + recurse[1], xc);
            }
        }
    }

    // New helper function to check door adjacency
    isAdjacentToDoor(r, c) {
        const neighbors = [
            [0, -1], [0, 1], [-1, 0], [1, 0]  // west, east, north, south
        ];
        
        for (const [dr, dc] of neighbors) {
            const nr = r + dr;
            const nc = c + dc;
            if (nr >= 0 && nr <= this.opts.n_rows && nc >= 0 && nc <= this.opts.n_cols) {
                if (this.cell[nr][nc] & this.DOORSPACE) {
                    return true;
                }
            }
        }
        return false;
    }

    checkTunnel(cell, r, c, check) {
        if (check.corridor) {
            for (const p of check.corridor) {
                const nr = r + p[0];
                const nc = c + p[1];
                if (cell[nr][nc] !== this.CORRIDOR) return false;
            }
        }
        if (check.walled) {
            for (const p of check.walled) {
                const nr = r + p[0];
                const nc = c + p[1];
                if (cell[nr][nc] & this.OPENSPACE) return false;
            }
        }
        return true;
    }

    fixDoors() {
        const fixed = Array.from({ length: this.opts.n_rows + 1 }, () => 
            Array(this.opts.n_cols + 1).fill(false)
        );
        this.doorList = [];
        
        for (let id = 1; id <= this.n_rooms; id++) {
            const room = this.room[id];
            for (const dir in room.door) {
                const shiny = [];
                for (const door of room.door[dir]) {
                    const r = door.row;
                    const c = door.col;
                    if (!(this.cell[r][c] & this.OPENSPACE)) continue;
                    
                    if (fixed[r][c]) {
                        shiny.push(door);
                        continue;
                    }
                    
                    fixed[r][c] = true;
                    if (door.out_id) {
                        const out_dir = this.opposite[dir];
                        const out_room = this.room[door.out_id];
                        out_room.door[out_dir] = out_room.door[out_dir] || [];
                        out_room.door[out_dir].push(door);
                    }
                    shiny.push(door);
                    this.doorList.push(door);
                }
                room.door[dir] = shiny.length ? shiny : undefined;
            }
        }
    }

    emptyBlocks() {
        for (let r = 0; r <= this.opts.n_rows; r++) {
            for (let c = 0; c <= this.opts.n_cols; c++) {
                if (this.cell[r][c] & this.BLOCKED) {
                    this.cell[r][c] = this.NOTHING;
                }
            }
        }
    }

    drawDoor(ctx, door, x, y, cellSize, orientation = null) {
        // Determine orientation if not provided
        if (orientation === null) {
            orientation = this.hasOpenSpace(door.row, door.col - 1) && 
                         this.hasOpenSpace(door.row, door.col + 1) ? 
                         'horizontal' : 'vertical';
        }
        
        const isHorizontal = orientation === 'horizontal';
        const centerX = x + cellSize / 2;
        const centerY = y + cellSize / 2;
        const doorWidth = cellSize / 3;
        const archWidth = cellSize / 6;
        const trapSize = cellSize / 4;

        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.fillStyle = '#ecf0f1'; // Match background

        if (door.key === 'arch') {
            if (isHorizontal) {
                ctx.strokeRect(centerX - doorWidth / 2, y, doorWidth, archWidth); // left post
                ctx.strokeRect(centerX - doorWidth / 2, y + cellSize - archWidth, doorWidth, archWidth); // right post
            } else {
                ctx.strokeRect(x, centerY - doorWidth / 2, archWidth, doorWidth); // top post
                ctx.strokeRect(x + cellSize - archWidth, centerY - doorWidth / 2, archWidth, doorWidth); // bottom post
            }
            return;
        }

        
        // Draw open door
        if (door.key === 'open') {
            if (isHorizontal) {
                ctx.strokeRect(centerX - doorWidth / 2, y, doorWidth, archWidth); // left post
                ctx.strokeRect(centerX - doorWidth / 2, y + archWidth, doorWidth, 4 * archWidth); // center door
                ctx.strokeRect(centerX - doorWidth / 2, y + cellSize - archWidth, doorWidth, archWidth); // right post
            } else {
                ctx.strokeRect(x, centerY - doorWidth / 2, archWidth, doorWidth); // top post
                ctx.strokeRect(x + archWidth, centerY - doorWidth / 2, 4 * archWidth, doorWidth); // middle door
                ctx.strokeRect(x + cellSize - archWidth, centerY - doorWidth / 2, archWidth, doorWidth); // bottom post
            }
        }
        
        // Draw lock
        if (door.key === 'lock') {
            if (isHorizontal) {
                ctx.strokeRect(centerX - doorWidth / 2, y, doorWidth, archWidth); // left post
                ctx.strokeRect(centerX - doorWidth / 2, y + archWidth, doorWidth, 4 * archWidth); // center door
                ctx.strokeRect(centerX - doorWidth / 2, y + cellSize - archWidth, doorWidth, archWidth); // right post
            } else {
                ctx.strokeRect(x, centerY - doorWidth / 2, archWidth, doorWidth); // top post
                ctx.strokeRect(x + archWidth, centerY - doorWidth / 2, 4 * archWidth, doorWidth); // middle door
                ctx.strokeRect(x + cellSize - archWidth, centerY - doorWidth / 2, archWidth, doorWidth); // bottom post
            }

            ctx.beginPath();
            const size = cellSize / 8;
            ctx.moveTo(centerX, centerY - size); // top (north)
            ctx.lineTo(centerX + size, centerY); // right (east)
            ctx.lineTo(centerX, centerY + size); // bottom (south)
            ctx.lineTo(centerX - size, centerY); // left (west)
            ctx.closePath();
            ctx.stroke();
        }
        
        // Draw trap
        if (door.key === 'trap') {
            if (isHorizontal) {
                ctx.strokeRect(centerX - doorWidth / 2, y, doorWidth, archWidth); // left post
                ctx.strokeRect(centerX - doorWidth / 2, y + archWidth, doorWidth, 4 * archWidth); // center door
                ctx.strokeRect(centerX - doorWidth / 2, y + cellSize - archWidth, doorWidth, archWidth); // right post
            } else {
                ctx.strokeRect(x, centerY - doorWidth / 2, archWidth, doorWidth); // top post
                ctx.strokeRect(x + archWidth, centerY - doorWidth / 2, 4 * archWidth, doorWidth); // middle door
                ctx.strokeRect(x + cellSize - archWidth, centerY - doorWidth / 2, archWidth, doorWidth); // bottom post
            }
        }
        
        // Draw secret
        if (door.key === 'secret') {
            ctx.fillStyle = '#34495e'; // Replace with your actual background color variable
            ctx.fillRect(x, y, cellSize, cellSize); // center door
        }
        
        // Draw portcullis as dots
        if (door.key === 'portc') {
            const dotCount = 3;
            const dotSpacing = cellSize / (dotCount + 1);
            const dotRadius = cellSize / 20;
            ctx.fillStyle = '#000';

            if (isHorizontal) {
                ctx.strokeRect(centerX - doorWidth / 2, y, doorWidth, archWidth); // left post
                ctx.strokeRect(centerX - doorWidth / 2, y + cellSize - archWidth, doorWidth, archWidth); // right post
                // Vertical line of dots for horizontal corridor
                for (let i = 1; i <= dotCount; i++) {
                    const dotX = centerX;
                    const dotY = y + i * dotSpacing;
                    ctx.beginPath();
                    ctx.arc(dotX, dotY, dotRadius, 0, Math.PI * 2);
                    ctx.fill();
                }
            } else {
                ctx.strokeRect(x, centerY - doorWidth / 2, archWidth, doorWidth); // top post
                ctx.strokeRect(x + cellSize - archWidth, centerY - doorWidth / 2, archWidth, doorWidth); // bottom post
                // Horizontal line of dots for vertical corridor
                for (let i = 1; i <= dotCount; i++) {
                    const dotX = x + i * dotSpacing;
                    const dotY = centerY;
                    ctx.beginPath();
                    ctx.arc(dotX, dotY, dotRadius, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }
    }

    // Expanded helper method to determine door orientation
    getDoorOrientation(r, c) {
        // Check for vertical room connections (north-south)
        const isRoomToRoomVertical = 
            (this.hasOpenSpace(r-1, c) && (this.cell[r-1][c] & this.ROOM)) && 
            (this.hasOpenSpace(r+1, c) && (this.cell[r+1][c] & this.ROOM));
        
        // Check for horizontal room connections (east-west)
        const isRoomToRoomHorizontal = 
            (this.hasOpenSpace(r, c-1) && (this.cell[r][c-1] & this.ROOM)) && 
            (this.hasOpenSpace(r, c+1) && (this.cell[r][c+1] & this.ROOM));
        
        // Check vertical room-corridor connections
        const isRoomToCorridorVertical = 
            (this.hasOpenSpace(r-1, c) && (this.cell[r-1][c] & this.ROOM)) && 
            (this.hasOpenSpace(r+1, c) && (this.cell[r+1][c] & this.CORRIDOR)) ||
            (this.hasOpenSpace(r+1, c) && (this.cell[r+1][c] & this.ROOM)) && 
            (this.hasOpenSpace(r-1, c) && (this.cell[r-1][c] & this.CORRIDOR));
        
        // Check horizontal room-corridor connections
        const isRoomToCorridorHorizontal = 
            (this.hasOpenSpace(r, c-1) && (this.cell[r][c-1] & this.ROOM)) && 
            (this.hasOpenSpace(r, c+1) && (this.cell[r][c+1] & this.CORRIDOR)) ||
            (this.hasOpenSpace(r, c+1) && (this.cell[r][c+1] & this.ROOM)) && 
            (this.hasOpenSpace(r, c-1) && (this.cell[r][c-1] & this.CORRIDOR));

        // Handle room connections first
        if (isRoomToRoomVertical || isRoomToCorridorVertical) {
            return 'vertical';
        }
        if (isRoomToRoomHorizontal || isRoomToCorridorHorizontal) {
            return 'horizontal';
        }

        // Fallback to general open space detection
        const horizontal = this.hasOpenSpace(r, c-1) && this.hasOpenSpace(r, c+1);
        const vertical = this.hasOpenSpace(r-1, c) && this.hasOpenSpace(r+1, c);
        
        if (horizontal && !vertical) return 'horizontal';
        if (vertical && !horizontal) return 'vertical';
        return 'horizontal'; // Default
    }

    // Add this method to get door type from cell flags
    getDoorType(cell) {
        if (cell & this.ARCH) return 'arch';
        if (cell & this.DOOR) return 'open';
        if (cell & this.LOCKED) return 'lock';
        if (cell & this.TRAPPED) return 'trap';
        if (cell & this.SECRET) return 'secret';
        if (cell & this.PORTC) return 'portc';
        return 'open';
    }



    getDoorOrientation(r, c) {
        const horizontal = this.hasOpenSpace(r, c - 1) && this.hasOpenSpace(r, c + 1);
        const vertical = this.hasOpenSpace(r - 1, c) && this.hasOpenSpace(r + 1, c);
        
        if (horizontal && !vertical) return 'horizontal';
        if (vertical && !horizontal) return 'vertical';
        
        // Default to horizontal if ambiguous
        return 'horizontal';
    }

    drawStairs(ctx, stair, x, y, cellSize) {
        const stepCount = 5;
        const isDown = stair.key === 'down';
        const dx = stair.next_col - stair.col || 0;
        const dy = stair.next_row - stair.row || 0;
        
        // Set drawing parameters
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;

        // Determine orientation and direction
        const isHorizontal = Math.abs(dx) > Math.abs(dy);
        const stepSpacing = cellSize / (stepCount + 1);
        const maxLength = cellSize * 0.8;  // Maximum line length
        
        if (isHorizontal) {
            const centerY = y + cellSize / 2;
            
            for (let i = 1; i <= stepCount; i++) {
                // Calculate line length (tapering effect)
                const length = maxLength * (i / stepCount);
                const xPos = (dx > 0) ? 
                    (isDown ? x + i * stepSpacing : x + cellSize - i * stepSpacing) :
                    (isDown ? x + cellSize - i * stepSpacing : x + i * stepSpacing);
                
                ctx.beginPath();
                ctx.moveTo(xPos, centerY - length/2);
                ctx.lineTo(xPos, centerY + length/2);
                ctx.stroke();
            }
        } else {
            const centerX = x + cellSize / 2;
            
            for (let i = 1; i <= stepCount; i++) {
                // Calculate line length (tapering effect)
                const length = maxLength * (i / stepCount);
                const yPos = (dy > 0) ? 
                    (isDown ? y + i * stepSpacing : y + cellSize - i * stepSpacing) :
                    (isDown ? y + cellSize - i * stepSpacing : y + i * stepSpacing);
                
                ctx.beginPath();
                ctx.moveTo(centerX - length/2, yPos);
                ctx.lineTo(centerX + length/2, yPos);
                ctx.stroke();
            }
        }
    }

    getDoorKey(cell) {
        if (cell & this.ARCH) return 'arch';
        if (cell & this.DOOR) return 'open';
        if (cell & this.LOCKED) return 'lock';
        if (cell & this.TRAPPED) return 'trap';
        if (cell & this.SECRET) return 'secret';
        if (cell & this.PORTC) return 'portc';
        return 'open';
    }

    renderToCanvas(canvas) {
        const ctx = canvas.getContext('2d');
        const cellSize = this.opts.cell_size;
        const width = (this.opts.n_cols + 1) * cellSize;
        const height = (this.opts.n_rows + 1) * cellSize;
        
        canvas.width = width;
        canvas.height = height;
        ctx.clearRect(0, 0, width, height);

        // Define colors
        const colors = {
            //ROOM: '#f1c40f',       // Yellow
            ROOM: '#ffffff',       // Yellow
            //CORRIDOR: '#3498db',    // Blue
            CORRIDOR: '#ffffff',    // Blue
            //DOORSPACE: '#e74c3c',   // Red
            DOORSPACE: '#ffffff',   // Red
            STAIRS: '#9b59b6',      // Purple
            OPENSPACE: '#ecf0f1',   // Light gray
            WALL: '#34495e'         // Dark blue-gray
        };
        
        // Draw all cells
        for (let r = 0; r <= this.opts.n_rows; r++) {
            for (let c = 0; c <= this.opts.n_cols; c++) {
                const cell = this.cell[r][c];
                const x = c * cellSize;
                const y = r * cellSize;
                
                // Modified: Treat doors as open space
                if (cell & (this.OPENSPACE | this.DOORSPACE)) {
                    ctx.fillStyle = (cell & this.ROOM) ? colors.ROOM : colors.CORRIDOR;
                    ctx.fillRect(x, y, cellSize, cellSize);
                } else {
                    ctx.fillStyle = colors.WALL;
                    ctx.fillRect(x, y, cellSize, cellSize);
                }

                if (cell & this.DOORSPACE) {
                    const orientation = this.getDoorOrientation(r, c);
                    const doorType = this.getDoorType(cell);
                    this.drawDoor(ctx, {
                        row: r, 
                        col: c,
                        key: doorType
                    }, x, y, cellSize, orientation);
                }
                
                // Draw stairs
                if (cell & this.STAIRS) {
                    // Find the actual stair object
                    const stair = this.stairs.find(s => s.row === r && s.col === c);
                    if (stair) {
                        this.drawStairs(ctx, stair, x, y, cellSize);
                    }
                }
                                
                // Draw labels
                if (cell & this.LABEL) {
                    const char = String.fromCharCode((cell >> 24) & 0xFF);
                    ctx.fillStyle = '#000';
                    ctx.font = 'bold 14px monospace';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(char, x + cellSize/2, y + cellSize/2);
                }
            }
        }
        // Draw grid
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
        ctx.lineWidth = 1;
        for (let r = 0; r <= this.opts.n_rows; r++) {
            const y = r * cellSize;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        for (let c = 0; c <= this.opts.n_cols; c++) {
            const x = c * cellSize;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
    }

    // Add this helper method to check adjacent cells
    hasOpenSpace(r, c) {
        if (r < 0 || r > this.opts.n_rows || c < 0 || c > this.opts.n_cols) {
            return false;
        }
        return !!(this.cell[r][c] & this.OPENSPACE);
    }

    // Statistics calculation
    getStats() {
        let rooms = 0, doors = 0, corridors = 0;
        
        for (let r = 0; r <= this.opts.n_rows; r++) {
            for (let c = 0; c <= this.opts.n_cols; c++) {
                const cell = this.cell[r][c];
                if (cell & this.ROOM) rooms++;
                if (cell & this.DOORSPACE) doors++;
                if (cell & this.CORRIDOR) corridors++;
            }
        }
        
        return {
            rooms: this.n_rooms,
            doors,
            corridors,
            size: `${this.opts.n_rows}x${this.opts.n_cols}`
        };
    }

    hasOpenSpace(r, c) {
        if (r < 0 || r > this.opts.n_rows || c < 0 || c > this.opts.n_cols) {
            return false;
        }
        return !!(this.cell[r][c] & this.OPENSPACE);
    }

    cellLabel(cell) {
        const i = (cell >> 24) & 0xFF;
        return i ? String.fromCharCode(i) : null;
    }

    isAdjacentToDoor(r, c) {
        const dirs = [
            [0, -1], [0, 1], [-1, 0], [1, 0]  // west, east, north, south
        ];
        for (const [dr, dc] of dirs) {
            const nr = r + dr;
            const nc = c + dc;
            if (nr >= 0 && nr <= this.opts.n_rows && nc >= 0 && nc <= this.opts.n_cols) {
                if (this.cell[nr][nc] & this.DOORSPACE) {
                    return true;
                }
            }
        }
        return false;
    }

    generateRoomDescription(/*room_id*/) {
        const themes = ["dank crypt", "ancient library", "fungal cavern"];
        const hazards = ["collapsing ceiling", "poisonous gas", "shifting floors"];
        const treasures = ["golden idol", "enchanted sword", "ancient scroll"];
        
        const theme = themes[Math.floor(Math.random() * themes.length)];
        let description = `You enter a ${theme}. `;
        
        if (Math.random() > 0.7) {
            description += `You notice ${hazards[Math.floor(Math.random() * hazards.length)]}. `;
        }
        
        if (Math.random() > 0.8) {
            description += `There's a ${treasures[Math.floor(Math.random() * treasures.length)]} visible.`;
        }
        
        return description;
    }
}

// Usage example:
// const generator = new DungeonGenerator();
// generator.createDungeon();
// generator.renderToCanvas(document.getElementById('dungeonCanvas'));