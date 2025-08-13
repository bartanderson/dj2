class GridSystem:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[None] * width for _ in range(height)]
    
    def get_cell(self, x: int, y: int):
        """Get cell at world coordinates (x,y)"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return None
    
    def set_cell(self, x: int, y: int, value):
        """Set cell at world coordinates (x,y)"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = value
    
    def is_valid_position(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height
    
    def get_neighbors(self, x: int, y: int, directions: list) -> list:
        """Get valid neighbor positions in specified directions"""
        neighbors = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_valid_position(nx, ny):
                neighbors.append((nx, ny))
        return neighbors