from typing import Iterator

from raidensim.network.node import Node
from raidensim.types import Coord


class Lattice(object):
    def __init__(self):
        self.node_to_coord = {}
        self.coord_to_node = {}
        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0
        self.gaps = set()

    def add_node(self, node: Node, x: int, y: int):
        self.node_to_coord[node] = (x, y)
        self.coord_to_node[x, y] = node

        # TODO: find a nicer, closed expression for these cases.
        if x < self.min_x:
            self.gaps |= {
                (xi, yi)
                for xi in range(x, self.min_x, 1)
                for yi in range(self.min_y, self.max_y + 1)
            }
            self.min_x = x
        elif x > self.max_x:
            self.gaps |= {
                (xi, yi)
                for xi in range(x, self.max_x, -1)
                for yi in range(self.min_y, self.max_y + 1)
            }
            self.max_x = x
        if y < self.min_y:
            self.gaps |= {
                (xi, yi)
                for xi in range(self.min_x, self.max_x + 1)
                for yi in range(y, self.min_y, 1)
            }
            self.min_y = y
        elif y > self.max_y:
            self.gaps |= {
                (xi, yi)
                for xi in range(self.min_x, self.max_x + 1)
                for yi in range(y, self.max_y, -1)
            }
            self.max_y = y
        self.gaps -= {(x, y)}

    @property
    def aspect_ratio(self):
        return (self.max_x - self.min_x) / (self.max_y - self.min_y)

    @property
    def area(self):
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)

    @property
    def density(self):
        return len(self.node_to_coord) / self.area

    def node_neighbors(self, node: Node) -> Iterator[Node]:
        node_pos = self.node_to_coord.get(node)
        if not node_pos:
            return iter(())
        return self.coord_neighbors(*node_pos)

    def coord_neighbors(self, x: int, y: int) -> Iterator[Node]:
        return (
            self.coord_to_node[nx, ny] for nx, ny in self.neighbor_coords(x, y)
            if (nx, ny) in self.coord_to_node
        )

    @staticmethod
    def neighbor_coords(x: int, y: int) -> Iterator[Coord]:
        return ((x + dx, y + dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)])

    def node_distance(self, a: Node, b: Node):
        ax, ay = self.node_to_coord[a]
        bx, by = self.node_to_coord[b]
        return self.coord_distance((ax, ay), (bx, by))

    @staticmethod
    def coord_distance(a: Coord, b: Coord):
        ax, ay = a
        bx, by = b
        return abs(ax - bx) + abs(ay - by)

    def get_free_coord(self) -> Coord:
        if self.gaps:
            return next(iter(self.gaps))

        if not self.node_to_coord:
            return 0, 0

        # No more gaps. Extend lattice in shortest direction.
        if self.max_x - self.min_x > self.max_y - self.min_y:
            x = self.min_x + (self.max_x - self.min_x) // 2
            y = self.min_y - 1 if self.max_y > abs(self.min_y) else self.max_y + 1
        else:
            x = self.min_x - 1 if self.max_x > abs(self.min_x) else self.max_x + 1
            y = self.min_y + (self.max_y - self.min_y) // 2

        return x, y

    def draw_ascii(self) -> str:
        display = ''
        for y in range(self.max_y, self.min_y - 1, -1):
            if y == 0:
                display += '0 '
            else:
                display += '  '
            for x in range(self.min_x, self.max_x + 1, 1):
                display += 'X' if (x,y) in self.coord_to_node else 'O'
            display += '\n'

        if self.min_x <= 0:
            display += ' ' * (2 - self.min_x) + '0'

        return display
