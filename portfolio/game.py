from typing import Dict, List, Tuple
from enum import Enum
# from termcolor import colored
def colored(text, color=None):
    return text
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

class MoveType(Enum):
    DISCARD = 1
    CHECK = 2
    PLAY_FACE_DOWN = 3
    PLAY_FACE_UP = 4

class Move:
    def __init__(self, move_type: MoveType, chip: Chip = None, target_pos: int = -1, extra_data=None):
        self.move_type = move_type
        self.chip = chip
        self.target_pos = target_pos # 0..3
        self.extra_data = extra_data # For Yellow chip: (from_pos, to_pos) tuple


class Board:
    """Board belongs to the match and spans 2-3 games."""
    def __init__(self):
        # a 2X2 matrix of stacks of chips
        # representation as list of list.
        # self.stacks[0] is position top left, [1] top-right, [2] bottom-left, [3] bottom-right
        self.stacks: List[List[Chip]] = [[] for _ in range(4)]
        

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
    
    def get_move(self, board: Board) -> Move:
        raise NotImplementedError()

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
        # random split
        random.shuffle(draft_batch_6)
        return draft_batch_6[:3], draft_batch_6[3:]
    
    def get_move(self, board: Board) -> Move:
        # Check if we should check (10% chance if hand is low? or just random)
        if random.random() < 0.1:
             return Move(MoveType.CHECK)
        
        # Try to play a chip
        if not self.hand.chips:
             return Move(MoveType.CHECK)
             
        chip = self.hand.chips[0] # Take first for now, or random
        
        # Randomly choose play type
        action_type = random.choice([MoveType.DISCARD, MoveType.PLAY_FACE_DOWN, MoveType.PLAY_FACE_UP])
        
        if action_type == MoveType.DISCARD:
             return Move(MoveType.DISCARD, chip)
             
        # Pick a stack
        target_pos = random.randint(0, 3)
        
        if action_type == MoveType.PLAY_FACE_DOWN:
             return Move(MoveType.PLAY_FACE_DOWN, chip, target_pos)
             
        if action_type == MoveType.PLAY_FACE_UP:
             # Handle constraints for Yellow
             extra_data = None
             if chip.kind == "mover": # Yellow
                 # Need to pick a source and dest
                 # Simplified random logic: pick any occupied stack to move FROM, and any neighbor TO
                 # This needs the board state to be valid.
                 # For now, let's just return check if board is empty, else try to move
                 pass # Logic to be added
             return Move(MoveType.PLAY_FACE_UP, chip, target_pos, extra_data)

        return Move(MoveType.CHECK)


class Game:
    def __init__(self, match: "Match"):
        self.match = match
        self.board = match.board
        self.players = match.players
        self.active_player_idx = 0
        self.players_checked = [False, False]
        self.finished = False

    @property
    def current_player(self) -> Player:
        return self.players[self.active_player_idx]

    def run_game(self):
        while not self.finished:
            self.play_turn()
            
            # Check if game is over (both checked)
            if all(self.players_checked):
                self.finished = True
                break
                
            # Switch player if next player hasn't checked
            next_idx = (self.active_player_idx + 1) % 2
            if not self.players_checked[next_idx]:
                 self.active_player_idx = next_idx
            # If next player checked, we stay on current player (unless they also checked, handled above)

    def play_turn(self):
        player = self.current_player
        if self.players_checked[self.active_player_idx]:
            return

        move = player.get_move(self.board)
        self.execute_move(move, player)

    def execute_move(self, move: Move, player: Player):
        if move.move_type == MoveType.CHECK:
            self.players_checked[self.active_player_idx] = True
            return

        elif move.move_type == MoveType.DISCARD:
            # Just remove from hand, effectively discard
            if move.chip in player.hand.chips:
                player.hand.chips.remove(move.chip)
            return

        elif move.move_type == MoveType.PLAY_FACE_DOWN:
             if move.chip in player.hand.chips:
                 player.hand.chips.remove(move.chip)
                 move.chip.is_hidden = True
                 self.board.stacks[move.target_pos].append(move.chip)
             return

        elif move.move_type == MoveType.PLAY_FACE_UP:
             if move.chip in player.hand.chips:
                 player.hand.chips.remove(move.chip)
                 move.chip.is_hidden = False
                 self.board.stacks[move.target_pos].append(move.chip)
                 
                 # Special effects
                 if move.chip.kind == "mover": # Yellow
                     # Logic for moving: user should have provided extra_data=(from_pos, to_pos)
                     # Validation required (neighbor, etc) - for now assuming PlayerRandom handles it or we skip
                     if move.extra_data:
                         src, dst = move.extra_data
                         if 0 <= src < 4 and 0 <= dst < 4 and self.board.stacks[src]:
                             moved_chip = self.board.stacks[src].pop()
                             self.board.stacks[dst].append(moved_chip)
                 
                 elif move.chip.kind == "drawer": # Red
                     # Draw a card
                     if player.deck.chips:
                        new_chips = player.deck.draw(1)
                        player.hand.chips.extend(new_chips)
                        # Force play face down
                        # We need to ask player for another move, or simpler: just play it randomly for now?
                        # Rule says "must play face down". 
                        # Ideally ask player.get_move() again with constraint? 
                        # For simulation, let's just force the LAST card drawn to be played at Random pos
                        if new_chips:
                            forced_chip = new_chips[0]
                            forced_pos = random.randint(0, 3) # Simplified
                            player.hand.chips.remove(forced_chip)
                            forced_chip.is_hidden = True
                            self.board.stacks[forced_pos].append(forced_chip)

    def calculate_score(self) -> Dict[str, int]:
        scores = {}
        for player in self.players:
            score = 0
            # Holdings counts
            holdings_counts = {}
            for chip in player.holdings.chips:
                holdings_counts[chip.kind] = holdings_counts.get(chip.kind, 0) + 1
            
            for i, stack in enumerate(self.board.stacks):
                if not stack:
                    continue
                top_chip = stack[-1]
                if top_chip.is_hidden:
                    continue
                
                chip_score = 1
                if top_chip.kind == "stacker": # Green
                    chip_score = len(stack)
                elif top_chip.kind == "binder": # Blue
                    # Count face-up neighbors
                    # Neighbors map (simplified 2x2 grid: 0 1 / 2 3)
                    neighbors_map = {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2]}
                    neighbors = neighbors_map[i]
                    face_up_neighbors = 0
                    for n_idx in neighbors:
                        if self.board.stacks[n_idx] and not self.board.stacks[n_idx][-1].is_hidden:
                            face_up_neighbors += 1
                    chip_score = 1 + face_up_neighbors
                
                # Multiply by holdings
                multiplier = holdings_counts.get(top_chip.kind, 0)
                score += chip_score * multiplier
            scores[player.name] = score
        return scores

    def cleanup_board(self):
        discard_pile = [] # We could track this if needed
        for stack in self.board.stacks:
            # Remove all face-up chips from top
            while stack and not stack[-1].is_hidden:
                discard_pile.append(stack.pop())
            
            # If stack not empty, flip the new top to face up
            if stack:
                stack[-1].is_hidden = False

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
        
        # Initial draw for Game 1
        for p in self.players:
             p.draw_holdings() # Choose 3 for holdings per rules? 
             # Wait, rules say: "choose 3 chips that will be Scoring rack... remaining 15 shuffled to be deck... draw 7"
             # My Player.draft_3_from_6 handles putting into deck.
             # I need to separate holdings from deck.
             # Let's assume draft put everything in Deck?
             # Player.draft_3_from_6 implementation: `self.deck.put(keep)`
             # So deck has 18 chips.
             # I need to pick 3 for holdings.
             p.draw_holdings() # Helper I defined: `self.holdings.put(self.deck.draw(3))`
             p.hand.chips.extend(p.deck.draw(7))

        match_scores = []
        
        # Game 1
        self.stage = MatchStage.GAME1
        game1 = Game(self)
        self.games.append(game1)
        game1.run_game()
        match_scores.append(game1.calculate_score())
        # print(f"Game 1 Scores: {match_scores[-1]}")
        game1.cleanup_board()
        
        # Draw for Game 2
        for p in self.players:
            count = min(3, len(p.deck))
            p.hand.chips.extend(p.deck.draw(count))
            
        # Game 2
        self.stage = MatchStage.GAME2
        game2 = Game(self)
        self.games.append(game2)
        game2.run_game()
        match_scores.append(game2.calculate_score())
        # print(f"Game 2 Scores: {match_scores[-1]}")
        game2.cleanup_board()
        
        # Draw for Game 3
        for p in self.players:
             count = min(3, len(p.deck))
             p.hand.chips.extend(p.deck.draw(count))
             
        # Game 3
        self.stage = MatchStage.GAME3
        game3 = Game(self)
        self.games.append(game3)
        game3.run_game()
        match_scores.append(game3.calculate_score())
        # print(f"Game 3 Scores: {match_scores[-1]}")
        
    
def main():
    for game_i in range(1000): # Run 1000 for stats
        match = Match()
        match.run_match()

if __name__ == "__main__":
    main()

    
