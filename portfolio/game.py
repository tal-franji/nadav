from typing import Dict, List, Tuple
from enum import Enum
from termcolor import colored
import random

CHIP_KIND_COUNT = dict(mover=9, stacker=9, drawer=9, binder=9)
CHIP_KIND_COLOR = dict(mover="yellow", stacker="green", drawer="red", binder="blue")
assert sum(CHIP_KIND_COUNT.values()) == 36
assert set(CHIP_KIND_COUNT.keys()) == set(CHIP_KIND_COLOR.keys())


class Chip:
    def __init__(self, kind: str):
        if kind not in CHIP_KIND_COUNT:
            raise ValueError(f"bad Chip kind {kind}")
        self.kind = kind
        self.is_hidden = False  # when true - face down
    def print(self):
        color = CHIP_KIND_COLOR[self.kind]
        if self.is_hidden:
            return colored(f"[{self.kind:6}]", color)
        return colored(f"{self.kind:6}", color)
    
    def __str__(self) -> str:
        return f"CHIP[{self.kind}]"

def watchdog_loop(max_iter: int):
    for i in range(max_iter):
        yield i
    raise RuntimeError("Watchdog max iter exceeded")

class Holdings:
    def __init__(self):
        # 3 chips
        self.chips: List[Chip] = list()
    def put(self, chips: List[Chip]):
        assert len(chips) == 3
        self.chips = chips[:]


class Hand:
    def __init__(self):
        # 0..15 chips. Hand chips are taken from the player's deck. Deck was created in the draft stage.
        self.chips: List[Chip] = list()
    def add(self, chip: Chip) -> None:
        self.chips.append(chip)


class Deck:
    """Deck blonging to a player. Deck is created in the draft stage.
    From the deck the player takes chips to the Hand and for the Holdings."""
    def __init__(self):
        # 18 chips (later 3 move to Holdings)
        self.chips: List[Chip] = list()
    def draw(self, count: int) -> List[Chip]:
        assert count <= len(self.chips)
        result = self.chips[:count]
        self.chips = self.chips[count:]
        return result
    def shuffle(self):
        random.shuffle(self.chips)
    def __len__(self):
        return len(self.chips)

    def put(self, chips: List[Chip]):
        self.chips.extend(chips)

class Board:
    """Board belongs to the match and spans 2-3 games."""
    def __init__(self):
        # a 2X2 matrix of stacks of chips
        # representation as list of list.
        self.stacks = [[]] * 4
        # self.stacks[0] is position top left, [1] top-right, [2] bottom-left, [3] bottom-right
        

class Player:
    """Match contains two players. This class may be inherited to implement different strategies"""
    def __init__(self, name: str):
        self.name = name
        self.hand = Hand()
        self.deck = Deck()
        self.holdings = Holdings()
        self.active = True
        self.game = None

    def draft_3_from_6(self, draft_batch_6: List[Chip], other_players: List["Player"]):
        assert len(draft_batch_6) == 6
        assert len(self.deck) + 3 <= 18
        keep, give = self._draft_choose_3(draft_batch_6)
        assert len(keep) == 3
        assert len(give) == 3
        self.deck.put(give)
        other_players[0]._draft_accept_3(keep)

    def _draft_accept_3(self, chips: List[Chip]):
        assert len(chips) == 3
        self.deck.put(chips)
    
    def _draft_choose_3(self, draft_batch_6: List[Chip]) -> Tuple[List[Chip], List[Chip]]:
        raise NotImplementedError()  # implement by strategy

    def draw_holdings(self):
        self.deck.shuffle()
        self.holdings.put(self.deck.draw(3))
    
    
        
    

# match (draft, game(2..3), turn(0..), )
"""
{match:
    [
    {draft: ""}
    {games: [
       {"game":
          [
          {"turns" :[],
          "scoring": "",
          "clear": ""}
          ]
      ]}]}
"""

class PlayerRandom(Player):
    def _draft_choose_3(self, draft_batch_6: List[Chip]) -> Tuple[List[Chip], List[Chip]]:
        return draft_batch_6[:3], draft_batch_6[3:]


class Game:
    def __init__(self, match: "Match"):
        self.match = match


class MatchStage(Enum):
    DRAFT = 1
    GAME1 = 2
    GAME2 = 3
    GAME3 = 4
    

class Match:
    """Represent a set of 2-3 games. After two games - if there is a tie - a third game is played."""
    def __init__(self):
        self.players = [PlayerRandom("Alice"), PlayerRandom("Bob")]
        self.games: List[Game] = list()
        self.board = Board()
        self.stage = MatchStage.DRAFT
    
    def draft(self):
        assert self.stage == MatchStage.DRAFT
        all_chips = [Chip(kind) for kind in CHIP_KIND_COUNT for _ in range(CHIP_KIND_COUNT[kind])]
        assert len(all_chips) == 36
        random.shuffle(all_chips)
        player_0 = self.players[0]
        player_1 = self.players[1]
        for draft_round in range(6):
            draft_batch_6 = all_chips[:6]
            all_chips = all_chips[6:]
            player_0.draft_3_from_6(draft_batch_6, [player_1])
            player_0, player_1 = player_1, player_0  # switch who chooses
        self.stage = MatchStage.GAME1

    def run_match(self):
        self.draft()
        
    
def main():
    for game_i in range(1000):
        match = Match()
        match.run_match()

if __name__ == "__main__":
    main()

    
