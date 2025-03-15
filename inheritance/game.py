from typing import List
import random

TILE_KIND_COUNT = dict(troop=15, agent=20, builder=25, scholar=40)
assert sum(TILE_KIND_COUNT.values()) == 100

class Tile:
    def __init__(self, kind: str):
        if kind not in TILE_KIND_COUNT:
            raise ValueError(f"bad Tile kind {kind}")
        self.kind = kind
    def __str__(self):
        return f"TILE[{self.kind}]"


class Hand:
    def __init__(self):
        self.tiles: List[Tile] = list()

class Reserve:
    def take(self) -> Tile:
        raise NotImplementedError()


class ReserveImpl(Reserve):
    def __init__(self):
        self.tiles: List[Tile] = list()
        for kind, count in TILE_KIND_COUNT.items():
            for i in range(count):
                self.tiles.append(Tile(kind))

    def draw(self) -> Tile:
        tile_index = random.randrange(len(self.tiles))
        tile = self.tiles[tile_index]
        self.tiles.pop(tile_index)
        return tile
    
    def extend(self, tiles: List[Tile]):
        self.tiles.extend(tiles)
    

class CastleCell:
    def __init__(self):
        self.stack: List[Tile] = list()
        self.neighbours: List[CastleCell] = list()

    def top(self):
        if not self.stack:
            return None
        return self.stack[-1]


class Castle:
    def __init__(self):
        self.cells: List[List[CastleCell]] = list()
        # we build a matrix with 3 line in lenght 2,3,2
        self.cells.append(list(CastleCell(), CastleCell()))  # first line
        self.cells.append(list(CastleCell(), CastleCell(), CastleCell()))  # first line
        self.cells.append(list(CastleCell(), CastleCell()))  # first line
        def c(x,y):
            return self.cells[y][x]
        c(0, 0).neighbours = list(c(0,1), c(1,0), c(1,1))
        c(0, 1).neighbours = list(c(0,0), c(1,1), c(1,2))
        c(1, 0).neighbours = list(c(0,0), c(1,1), c(2,0))
        c(1, 1).neighbours = list(c(0,0), c(0,1), c(1,0), c(1,2), c(2,0), c(2,1))
        c(1, 2).neighbours = list(c(0,1), c(1,1), c(2,1))
        c(2, 0).neighbours = list(c(1,0), c(1,1), c(2,1))
        c(2, 1).neighbours = list(c(2,0), c(1,1), c(1,2))
    

class Player:
    def __init__(self, name: str):
        self.name = str
        self.hand = Hand()
        self.castle = Castle()
        self.active = True
    
    def play(self, round: str, table: "Table"):
        pass

class Table:
    def __init__(self, names: List[str]):
        self.players: List[Player] = [Player(name) for name in names]

    def shift(self):
        player0 = self.players.pop(0)
        self.players.append(player0)

class Game:
    def __init__(self, names: List[str]):
        self.table = Table(names)
        self.rounds: List[str] = ["build", "activate"]
        self.cur_round_index = 0
        self.cycle_count = 0
        self.cur_player_index = 0
        # each turn of two rounds each with Nplayers turns and then table shifts

    def run_game_cycle(self):
        for self.cur_round_index, round in enumerate(self.rounds):
            for self.cur_player_index, player in enumerate(self.table.players):
                player.play(round, self.table)



print("DEBUG>>>>") 
r = Reserve()
    
