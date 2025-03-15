from typing import Dict, List, Tuple
from termcolor import colored
import random

TILE_KIND_COUNT = dict(troop=15, agent=20, builder=25, scholar=40)
TILE_KIND_COLOR = dict(troop="yellow", agent="green", builder="red", scholar="blue")
assert sum(TILE_KIND_COUNT.values()) == 100
MAX_HAND_TILES = 10
MAX_CELL_HEIGHT = 7

class Tile:
    def __init__(self, kind: str):
        if kind not in TILE_KIND_COUNT:
            raise ValueError(f"bad Tile kind {kind}")
        self.kind = kind
    def print(self):
        color = TILE_KIND_COLOR[self.kind]
        return colored(f"{self.kind:6}", color)
    
    def __str__(self) -> str:
        return f"TILE[{self.kind}]"

def watchdog_loop(max_iter: int):
    for i in range(max_iter):
        yield i
    raise RuntimeError("Watchdog max iter exceeded")

class Hand:
    def __init__(self):
        self.tiles: List[Tile] = list()
    def empty(self):
        return len(self.tiles) == 0
    def add(self, tile: Tile) -> None:
        self.tiles.append(tile)


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
    
    def empty(self):
        return len(self.stack) == 0


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
                    text = "[" + " " * 6 + "]"
                else:
                    tile_text = tile.print()
                    text = f"[{tile_text}]"
                print(text, end="")
        need_to_activate = self.castle.count_tile_contacts()
        print("\nActivations in Castle: ", need_to_activate)

        print(f"\nHand:")
        for i, tile in enumerate(sorted(self.hand.tiles, key=lambda tile: tile.kind)):
            end = ""
            if i % 3 == 0:
                end = "\n"
            print(f"  {tile.print()}", end=end)
        print()

    def win(self):
        raise RuntimeError(f"I win! {self.name}")

class PlayerRandom(Player):
    @staticmethod
    def random_cell(player) -> Tuple[int, int, CastleCell]:
        for _ in watchdog_loop(1000):
            x = random.randrange(3)
            if x >= len(player.castle.cells):
                continue
            y = random.randrange(3)
            if y >= len(player.castle.cells[x]):
                continue
            break
        return x, y, player.castle.cells[x][y]

    def build(self):
        assert self.active
        if self.hand.empty():
            self.active = False
            return
        for _ in watchdog_loop(1000):  # loop for the case agent to skip over empty cells
            played_tile = self.choose_tile_to_play()
            agent = False
            if played_tile.kind == "agent":
                agent = True
            player = random.choice(self.game.table.players)
            x, y, cell = self.random_cell(player)
            if agent and cell.empty():
                self.hand.add(played_tile)  # could not play - return to my hand to choose another
                continue  # cannot replace
            if agent:
                replaced_tile = cell.stack[-1]
                self.hand.add(replaced_tile)
                cell.stack[-1] = played_tile
                print(f"{self.name} places [agent] instead of [{replaced_tile.kind}] at ({x}, {y})@{player.name}")
            else:
                over_kind = "None"
                if cell.top():
                    over_kind = cell.top().kind
                cell.stack.append(played_tile)
                if len(cell.stack) >= MAX_CELL_HEIGHT:
                    player.win()
                print(f"{self.name} places [{played_tile.kind}] over [{over_kind}] at ({x}, {y})@{player.name}")
            break

    def choose_tile_to_play(self) -> Tile:
        return pop_random(self.hand.tiles)

    def activate(self):
        assert self.active
        need_to_activate = self.castle.count_tile_contacts()
        print(f"DEBUG>>> {self.name} activations: ", need_to_activate)
        kinds_to_play = list(need_to_activate.keys())
        random.shuffle(kinds_to_play)
        for kind in kinds_to_play:
            for i in range(need_to_activate[kind]):
                self.play_activation(kind)
                if not self.activate:
                    return
        tiles_to_return = list()
        while len(self.hand.tiles) > MAX_HAND_TILES:
            tiles_to_return.append(pop_random(self.hand.tiles))
        if tiles_to_return:
            print(f"Player {self.name} discarding: {tiles_to_return}")
            self.game.reserve.extend(tiles_to_return)

    def play_activation(self, kind: str):
        print(f"DEBUG>>> player {self.name} plays activation {kind}")
        if kind == "agent":
            return
        if kind == "builder":
            self.build()
            return
        if kind == "scholar":
            card = self.game.reserve.draw()
            self.hand.add(card)
            return
        if kind == "troop":
            for _ in watchdog_loop(1000):
                player = random.choice(self.game.table.players)
                x, y, cell = self.random_cell(player)
                if cell.empty():
                    continue
                taken = cell.stack.pop()
                self.game.reserve.extend([taken])
                print(f"{self.name} takes [{taken.kind}] from ({x}, {y})@{player.name}")
                break
            


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
        # each turn of two rounds each with N players turns and then table shifts
        self.init_hands()

    def init_hands(self):
        for player in self.table.players:
            for _ in range(7):
                card = self.reserve.draw()
                player.hand.add(card)

    def run_game_cycle(self):
        self.print_table()
        for self.cur_round_index, round in enumerate(self.rounds):
            print(f"----- round {round} -------")
            for self.cur_player_index, player in enumerate(self.table.players):
                if not player.active:
                    print(f"skipping {player.name}...")
                    continue
                player.play(round)
                active_players = [p for p in self.table.players if p.active]
                if len(active_players) <= 1:
                    print(f"ALL LOST but {active_players[0].name} who is the winner!")
                    return False
            self.print_table()
        self.table.shift()
        return True

    def print_table(self):
        for player in self.table.players:
            player.print()
        self.cycle_count += 1

def main():
    game = Game(["Alice", "Bob", "Charlie"], PlayerRandom)
    for i in range(100):
        print(f"===== CYCLE {i} ======")
        more = game.run_game_cycle()
        if not more:
            print(f"stopping at cycle {i}")
            break
        #input("next?")


if __name__ == "__main__":
    main()

    
