from typing import Dict, List
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


def pop_random(lst: List):
    index = random.randrange(len(lst))
    return lst.pop(index)


class ReserveImpl(Reserve):
    def __init__(self):
        self.tiles: List[Tile] = list()
        for kind, count in TILE_KIND_COUNT.items():
            for i in range(count):
                self.tiles.append(Tile(kind))

    def draw(self) -> Tile:
        return pop_random(self.tiles)

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

    def count_tile_contacts(self) -> Dict[str, int]:
        result = dict()
        for x, cell_line in enumerate(self.cells):
            for y, cell in enumerate(cell_line):
                if cell is None:
                    continue
                for neighbour in cell.neighbours:
                    if neighbour is None:
                        continue
                    cell_top = cell.top()
                    neighbour_top = neighbour.top()
                    if cell_top is None or neighbour_top is None:
                        continue
                    if cell_top.kind == neighbour_top.kind:
                        result[cell_top.kind] = result.get(cell_top.kind, 0) + 1
        assert all((x % 2) == 0 for x in result.values())  # we should count every edge twice
        return {kind: count // 2 for kind, count in result.items()}


class Player:
    def __init__(self, name: str, game: "Game"):
        self.name = name
        self.hand = Hand()
        self.castle = Castle()
        self.active = True
        self.game = game
    
    def play(self, round: str):
        if round == "build":
            self.build()
        elif round == "activate":
            self.activate()
        else:
            raise ValueError(f"bad round {round}")

    def build(self):
        pass

    def activate(self):
        pass

    def print(self):
        # each tile is 8 characters wide so we can have "half" tile of 4 spaces. So we can print line 0 and
        # line 2 in half offset and get the "hexagon effect"
        print(f"==== Player {self.name}  ====")
        print(f"Castle:")
        for x, cell_line in enumerate(self.castle.cells):
            print()
            text = ""
            if x % 2 == 0:
                text = " " * 4
            print(text, end="")
            for y, cell in enumerate(cell_line):
                tile = cell.top()
                if tile is None:
                    text = "|" + " " * 6 + "|"
                else:
                    text = f"|{tile.kind:6}|"
                print(text, end="")
        need_to_activate = self.castle.count_tile_contacts()
        print("\nActivations in Castle: ", need_to_activate)

        print(f"\nHand:")
        for tile in self.hand.tiles:
            print(f"  {tile.kind}")


class PlayerRandom(Player):
    def random_cell(self) -> CastleCell:
        while True:
            x = random.randrange(3)
            if x >= len(self.castle.cells):
                continue
            y = random.randrange(3)
            if y >= len(self.castle.cells[x]):
                continue
            break
        return self.castle.cells[x][y]

    def build(self):
        new_tile = self.game.reserve.draw()
        self.hand.tiles.append(new_tile)
        played_tile = self.choose_tile_to_play()
        cell = self.random_cell()
        cell.stack.append(played_tile)

    def choose_tile_to_play(self) -> Tile:
        return pop_random(self.hand.tiles)

    def activate(self):
        need_to_activate = self.castle.count_tile_contacts()
        kinds_to_play = list(need_to_activate.keys())
        random.shuffle(kinds_to_play)
        for kind in kinds_to_play:
            for i in range(need_to_activate[kind]):
                self.play_activation(kind)

    def play_activation(self, kind: str):
        print(f"DEBUG>>> player {self.name} plays activation {kind}")


class Table:
    def __init__(self, names: List[str], player_class, game):
        self.players: List[Player] = [player_class(name, game) for name in names]

    def shift(self):
        player0 = self.players.pop(0)
        self.players.append(player0)


class Game:
    def __init__(self, names: List[str], player_class=Player):
        self.reserve = ReserveImpl()
        self.table = Table(names, player_class, self)
        self.rounds: List[str] = ["build", "activate"]
        self.cur_round_index = 0
        self.cycle_count = 0
        self.cur_player_index = 0
        # each turn of two rounds each with Nplayers turns and then table shifts

    def run_game_cycle(self):
        for self.cur_round_index, round in enumerate(self.rounds):
            for self.cur_player_index, player in enumerate(self.table.players):
                player.play(round)
        self.table.shift()

    def print_table(self):
        for player in self.table.players:
            player.print()
        self.cycle_count += 1

def main():
    game = Game(["Alice", "Bob", "Charlie"], PlayerRandom)
    for i in range(10):
        game.print_table()
        game.run_game_cycle()


if __name__ == "__main__":
    main()

    
