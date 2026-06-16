import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.table import Table
from engine.game import Game
from engine.player import Player
from engine.card import Card

def run_test():
    table = Table()
    game = Game(table)

    # Human (You) has 1000 chips
    p1 = Player("You", table)
    p1.chips = 1000
    
    # Bot has 300 chips
    p2 = Player("PokerBot", table)
    p2.chips = 300
    
    game.players = [p1, p2]
    
    # Manually set up all-in state
    p2.chips = 0
    p2.bet_in_round = 300
    p2.all_in = True
    
    p1.chips = 0
    p1.bet_in_round = 1000
    p1.all_in = True
    
    table.pot = 1300
    table.current_bet = 1000
    game.active = [p1, p2]
    
    # Bot has Aces, You have Kings
    p2.hand = [Card("A", "H"), Card("A", "D")]
    p1.hand = [Card("K", "H"), Card("K", "D")]
    
    table.community = [Card("2", "S"), Card("3", "C"), Card("8", "D"), Card("J", "H"), Card("Q", "S")]
    
    game.street = 4
    
    print("Initial chips before showdown:")
    print(f"You: {p1.chips}, Bet: {p1.bet_in_round}")
    print(f"Bot: {p2.chips}, Bet: {p2.bet_in_round}")
    print(f"Pot: {table.pot}")
    
    game.end_game()
    
    print("\nAfter showdown:")
    print(f"You: {p1.chips}")
    print(f"Bot: {p2.chips}")
    print(f"Pot: {table.pot}")
    
    assert p2.chips == 600, f"Expected Bot to have 600 chips, but got {p2.chips}"
    assert p1.chips == 700, f"Expected You to have 700 chips, but got {p1.chips}"
    print("\nSUCCESS: All-in pot distribution is correct! The bot only won the amount it bet (300 from You, returning 700 excess to You).")

if __name__ == "__main__":
    run_test()
