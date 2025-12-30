from typing import Dict, List, Tuple, Optional
from enum import Enum
# from termcolor import colored
def colored(text, color=None):
    return text
import random

VERBOSE = False
VERBOS_TURN_BY_TURN = False
SNAPSHOT_SEP = "\n"


def log(*args):
    if VERBOSE:
        print(*args)


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
    def __init__(self) -> None:
        # 3 chips
        self.chips: List[Chip] = list()
    def put(self, chips: List[Chip]) -> None:
        assert len(chips) == 3
        self.chips = chips[:]


class Hand:
    def __init__(self) -> None:
        # 0..15 chips. Hand chips are taken from the player's deck. Deck was created in the draft stage.
        self.chips: List[Chip] = list()
    def add(self, chip: Chip) -> None:
        self.chips.append(chip)
        
    def put(self, chips: List[Chip]) -> None:
        self.chips.extend(chips)


class Deck:
    """Deck blonging to a player. Deck is created in the draft stage.
    From the deck the player takes chips to the Hand and for the Holdings."""
    def __init__(self) -> None:
        # 18 chips (later 3 move to Holdings)
        self.chips: List[Chip] = list()
    def draw(self, count: int) -> List[Chip]:
        assert count <= len(self.chips)
        result = self.chips[:count]
        self.chips = self.chips[count:]
        return result
    def shuffle(self) -> None:
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
    def __init__(self, move_type: MoveType, 
    chip: Optional[Chip] = None, target_pos: int = -1) -> None:
        self.move_type = move_type
        self.chip = chip
        self.target_pos = target_pos # 0..3


class Board:
    """Board belongs to the match and spans 2-3 games."""
    def __init__(self) -> None:
        # a 2X2 matrix of stacks of chips
        # representation as list of list.
        # self.stacks[0] is position top left, [1] top-right, [2] bottom-left, [3] bottom-right
        self.stacks: List[List[Chip]] = [[] for _ in range(4)]
        
    def str_status(self, sep="\n"):
        # Order: TL(0), TR(1), BR(3), BL(2)
        labels = ["TL", "TR", "BR", "BL"]
        indices = [0, 1, 3, 2]
        result = ""
        
        for label, idx in zip(labels, indices):
            stack = self.stacks[idx]
            chips_str = ""
            for chip in stack:
                c = CHIP_KIND_COLOR[chip.kind][0]
                if chip.is_hidden:
                    c = c.lower()
                else:
                    c = c.upper()
                chips_str += c
            result += f"{label}>{chips_str}{sep}"
        
        return result

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

    def get_mover_followup(self, board: Board) -> Tuple[int, int]:
        """Returns (from_pos, to_pos) for Yellow chip move"""
        raise NotImplementedError()
        
    def get_drawer_followup(self, board: Board) -> Tuple[Chip, int]:
        """Returns (chip_to_play_face_down, target_pos) for Red chip move"""
        raise NotImplementedError()

    def _draft_choose_3(self, draft_batch_6: List[Chip]) -> Tuple[List[Chip], List[Chip]]:
        raise NotImplementedError()  # implement by strategy

    def draw_holdings(self):
        self.deck.shuffle()
        self.holdings.put(self.deck.draw(3))
    
    def draw_hand(self, count: int):
        self.hand.put(self.deck.draw(count))

    def consider_update_holdings(self):
        raise NotImplementedError()


class PlayerRandom(Player):
    def _draft_choose_3(self, draft_batch_6: List[Chip]) -> Tuple[List[Chip], List[Chip]]:
        # random split
        random.shuffle(draft_batch_6)
        return draft_batch_6[:3], draft_batch_6[3:]
    
    def get_move(self, board: Board) -> Move:
        # Check if we should check (10% chance if hand is low? or just random)
        if not self.hand.chips or random.random() < 0.1:
             return Move(MoveType.CHECK)

        chip = self.hand.chips[0] # Take first for now, or random
        
        # Randomly choose play type
        action_type = random.choice([MoveType.DISCARD, MoveType.PLAY_FACE_DOWN, MoveType.PLAY_FACE_UP])
        
        if action_type == MoveType.DISCARD:
             return Move(MoveType.DISCARD, chip)    
        # Pick a stack
        target_pos = random.randint(0, 3)
        assert action_type in [MoveType.PLAY_FACE_DOWN, MoveType.PLAY_FACE_UP]
        return Move(action_type, chip, target_pos)

        
    def get_mover_followup(self, board: Board) -> Tuple[int, int]:
        # Simplified random logic: pick any occupied stack to move FROM, and any neighbor TO
        # Neighbors map (simplified 2x2 grid: 0 1 / 2 3)
        neighbors_map = {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2]}
        
        # Find all valid source stacks (not empty)
        valid_sources = [i for i, stack in enumerate(board.stacks) if stack]
        if not valid_sources:
            return (-1, -1) # No valid move
            
        src = random.choice(valid_sources)
        dst = random.choice(neighbors_map[src])
        return (src, dst)

    def get_drawer_followup(self, board: Board) -> Tuple[Chip, int]:
        # Play a random chip from hand face down to a random pos
        if not self.hand.chips:
             raise RuntimeError("Hand empty in get_drawer_followup but guaranteed to have drawn")
        chip = random.choice(self.hand.chips)
        target_pos = random.randint(0, 3)
        return (chip, target_pos)
    
    def consider_update_holdings(self):
        if random.random() < (1.0 - 0.4):
            return  # do not change holdings      
        self.deck.chips.extend(self.holdings.chips)
        self.holdings.chips.clear()
        self.draw_holdings()
        

class Game:
    def __init__(self, match: "Match"):
        self.match = match
        self.board = match.board
        self.players = match.players
        self.active_player_idx = 0
        self.players_checked = [False, False]
        self.finished = False
        self.scores: Dict[str, int] = {}
        self.winner: Optional[str] = None

    @property
    def current_player(self) -> Player:
        return self.players[self.active_player_idx]

    def snapshot_game(self, sep="\n") -> str:
        result = ""
        result += f"GM>{self.match.stage.value - 1}{sep}"
        for p in self.players:
            # HD
            hd_str = ""
            for c in sorted(p.hand.chips, key=lambda c: c.kind):
                 hd_str += CHIP_KIND_COLOR[c.kind][0].upper()
            result += f"hand({p.name})>{hd_str}{sep}"
            
            # HO
            ho_str = ""
            for c in sorted(p.holdings.chips, key=lambda c: c.kind):
                 ho_str += CHIP_KIND_COLOR[c.kind][0].upper()
            result += f"HOLD({p.name})>{ho_str}{sep}"
            
        result += self.board.str_status(sep)
        return result

    def run_game(self):
        while not self.finished:
            self.play_turn()
            if VERBOSE and VERBOS_TURN_BY_TURN:
                print(self.snapshot_game(SNAPSHOT_SEP))
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
            log(f"  Player {player.name}: Check")
            self.players_checked[self.active_player_idx] = True
            return
        elif move.move_type == MoveType.DISCARD:
            log(f"  Player {player.name}: Discard {move.chip}")
            # Just remove from hand, effectively discard
            assert move.chip in player.hand.chips
            player.hand.chips.remove(move.chip)
            # Currently not tracking the "trash pile"
            return
        elif move.move_type == MoveType.PLAY_FACE_DOWN:
            assert move.chip in player.hand.chips
            player.hand.chips.remove(move.chip)
            move.chip.is_hidden = True
            self.board.stacks[move.target_pos].append(move.chip)
            log(f"  Player {player.name}: Play Face DOWN at {move.target_pos} (chip hidden)")
            return
        elif move.move_type == MoveType.PLAY_FACE_UP:
            assert move.chip in player.hand.chips
            player.hand.chips.remove(move.chip)
            move.chip.is_hidden = False
            self.board.stacks[move.target_pos].append(move.chip)
            log(f"  Player {player.name}: Play Face UP {move.chip} at {move.target_pos}")
            
            # Special effects
            if move.chip.kind == "mover": # Yellow
                # Logic for moving: user callback
                src, dst = player.get_mover_followup(self.board)
                assert 0 <= src < 4 and 0 <= dst < 4 and self.board.stacks[src]
                # Validate neighbor (optional but good)
                neighbors_map = {0: [1, 2], 1: [0, 3], 2: [0, 3], 3: [1, 2]}
                assert dst in neighbors_map.get(src, [])
                moved_chip = self.board.stacks[src].pop()
                self.board.stacks[dst].append(moved_chip)

            elif move.chip.kind == "drawer": # Red
                # Draw a card
                if not player.deck.chips:
                    return  # no cards to draw
                player.draw_hand(1)
                
                # Get follow-up move from player
                chip_to_play, pos_to_play = player.get_drawer_followup(self.board)
                
                # Validate and execute
                assert chip_to_play in player.hand.chips
                player.hand.chips.remove(chip_to_play)
                chip_to_play.is_hidden = True
                self.board.stacks[pos_to_play].append(chip_to_play)

    def calculate_score(self) -> Dict[str, int]:
        scores = {}
        for player in self.players:
            score = 0
            # Holdings counts
            holdings_counts: Dict[str, int] = {}
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
        
        self.scores = scores
        # Determine winner
        p0 = self.players[0].name
        p1 = self.players[1].name
        if scores[p0] > scores[p1]:
            self.winner = p0
        elif scores[p1] > scores[p0]:
            self.winner = p1
        else:
            self.winner = None # Tie
            
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
    def __init__(self) -> None:
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
             p.draw_holdings()
             p.draw_hand(7)

        # Game 1
        log("=== Starting Game 1 ===")
        self.stage = MatchStage.GAME1
        game1 = Game(self)
        self.games.append(game1)
        game1.run_game()
        game1.calculate_score()
        log(game1.snapshot_game(";"))
        log(f"Game 1 Scores: {game1.scores}, Winner: {game1.winner}")
        game1.cleanup_board()
        
        if not game1.winner:
            # in case of tie - choose new hand
            for p in self.players:
                p.consider_update_holdings()
            
        # Draw for Game 2
        for p in self.players:
            count = min(3, len(p.deck))
            p.draw_hand(count)
            
        # Game 2
        self.stage = MatchStage.GAME2
        game2 = Game(self)
        self.games.append(game2)
        game2.run_game()
        game2.calculate_score()
        log(game2.snapshot_game(";"))
        log(f"Game 2 Scores: {game2.scores}, Winner: {game2.winner}")
        game2.cleanup_board()
        
        # Check termination
        match_winner = self._check_match_winner()
        if match_winner:
             log(f"Match End! Match Winner: {match_winner}")
             return
             
        if not game1.winner:
            # in case of tie - choose new hand
            for p in self.players:
                p.consider_update_holdings()
        # Draw for Game 3
        for p in self.players:
             count = min(3, len(p.deck))
             p.hand.chips.extend(p.deck.draw(count))
             
        # Game 3
        self.stage = MatchStage.GAME3
        game3 = Game(self)
        self.games.append(game3)
        game3.run_game()
        game3.calculate_score()
        score_str = ";".join([f"score({p.name})>{game3.scores[p.name]}" for p in self.players])
        log(game3.snapshot_game(";") + score_str)
        
        match_winner = self._check_match_winner()
        if not match_winner:
            match_winner = "Tie"
        log(f"Match End! Match Winner: {match_winner}")

    def _check_match_winner(self) -> Optional[str]:
        p0 = self.players[0].name
        p1 = self.players[1].name
        wins = {p0: 0, p1: 0}
        ties = 0
        
        for game in self.games:
            if game.winner == p0:
                wins[p0] += 1
            elif game.winner == p1:
                wins[p1] += 1
            else:
                ties += 1
        
        if wins[p0] >= 2: return p0
        if wins[p1] >= 2: return p1
        if wins[p0] == 1 and ties >= 1: return p0
        if wins[p1] == 1 and ties >= 1: return p1
        
        if len(self.games) == 3:
            if wins[p0] > wins[p1]: return p0
            if wins[p1] > wins[p0]: return p1
            return None
            
        return None
        
    
def main():
    global VERBOSE
    VERBOSE = True
    for game_i in range(5000): # Run 1000 for stats
        match = Match()
        match.run_match()

if __name__ == "__main__":
    main()

    
