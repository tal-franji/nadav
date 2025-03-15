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
        self.cells: List[List[CastleCell]] = [[None] * 2, [None] * 3, [None] * 2]
        # we build a matrix with 3 line in length 2,3,2
        self.cells.append([CastleCell(), CastleCell()])  # first line
        self.cells.append([CastleCell(), CastleCell(), CastleCell()])  # first line
        self.cells.append([CastleCell(), CastleCell()])  # first line

        def c(x, y):
            cell = self.cells[x][y]
            if cell is None:
                cell = CastleCell()
                self.cells[x][y] = cell
            return cell

        c(0, 0).neighbours = [c(0, 1), c(1, 0), c(1, 1)]
        c(0, 1).neighbours = [c(0, 0), c(1, 1), c(1, 2)]
        c(1, 0).neighbours = [c(0, 0), c(1, 1), c(2, 0)]
        c(1, 1).neighbours = [c(0, 0), c(0, 1), c(1, 0), c(1, 2), c(2, 0), c(2, 1)]
        c(1, 2).neighbours = [c(0, 1), c(1, 1), c(2, 1)]
        c(2, 0).neighbours = [c(1, 0), c(1, 1), c(2, 1)]
        c(2, 1).neighbours = [c(2, 0), c(1, 1), c(1, 2)]
    

class Player:
    def __init__(self, name: str):
        self.name = str
        self.hand = Hand()
        self.castle = Castle()
        self.active = True
    
    def play(self, round: str, table: "Table"):
        if round == "build":
            self.build(table)
        elif round == "activate":
            self.activate(table)
        else:
            raise ValueError(f"bad round {round}")

    def build(self, table: "Table"):
        pass

    def activate(self, table: "Table"):
        pass


class PlayerRandom(Player):
    pass


class Table:
    def __init__(self, names: List[str], player_class=Player):
        self.players: List[Player] = [player_class(name) for name in names]

    def shift(self):
        player0 = self.players.pop(0)
        self.players.append(player0)


class Game:
    def __init__(self, names: List[str], player_class=Player):
        self.table = Table(names, player_class)
        self.rounds: List[str] = ["build", "activate"]
        self.cur_round_index = 0
        self.cycle_count = 0
        self.cur_player_index = 0
        # each turn of two rounds each with Nplayers turns and then table shifts

    def run_game_cycle(self):
        for self.cur_round_index, round in enumerate(self.rounds):
            for self.cur_player_index, player in enumerate(self.table.players):
                player.play(round, self.table)
        self.table.shift()


def main():
    game = Game(["Alice", "Bob", "Charlie"], PlayerRandom)
    game.run_game_cycle()


if __name__ == "__main__":
    main()

    
