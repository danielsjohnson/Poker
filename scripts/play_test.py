import torch
import time
from engine.game import Game
from engine.table import Table
from engine.player import humanPlayer
from agent.agent import Agent
from agent.police_bot_v0 import PoliceBot

# --- CONFIGURATION ---
MODEL_PATH = "checkpoint_1150000.pth" 
STACK_SIZE = 1000
# ---------------------

def clear_screen():
    # DISABLED: We want to see the history!
    pass 

def format_cards(cards):
    if not cards: return "[]"
    return " ".join([str(c) for c in cards])

def print_game_state(game, p1_bot, p2_human):
    # Print a separator instead of clearing the screen
    print("\n" + "="*50)
    print(f"      TEXAS HOLD'EM - MAN VS MACHINE")
    print("="*50)

    # --- COMMUNITY CARDS ---
    board_str = format_cards(game.table.community)
    
    print(f"  BOARD:  [{board_str}]")
    print(f"  POT:    {game.table.pot}")
    print("-" * 50)

    # --- BOT INFO (Player 1) ---
    p1_status = " (Dealer)" if game.button == 0 else ""
    print(f"  [BOT]   Stack: {p1_bot.chips} {p1_status}")
    print(f"          Cards: [XX] [XX]") 
    print(f"          Bet:   {p1_bot.bet_in_round}")
    print("-" * 50)

    # --- HUMAN INFO (Player 2) ---
    p2_status = " (Dealer)" if game.button == 1 else ""
    human_hand_str = format_cards(p2_human.hand)
    
    print(f"  [YOU]   Stack: {p2_human.chips} {p2_status}")
    print(f"          Cards: {human_hand_str}") 
    print(f"          Bet:   {p2_human.bet_in_round}")
    print("=" * 50 + "\n")

def get_human_action(valid_actions):
    print("  YOUR VALID MOVES:")
    options = []
    if valid_actions[0]: options.append("(F)old")
    if valid_actions[1]: options.append("(C)heck")
    if valid_actions[2]: options.append("(C)all")
    if valid_actions[3]: options.append("(B)et") 
    if valid_actions[6]: options.append("(A)ll-In")
    print("  " + "  |  ".join(options))
    
    while True:
        choice = input("\n  >> Your Action: ").lower().strip()
        if choice in ['f', 'fold'] and valid_actions[0]: return 0
        if choice in ['ch', 'check'] and valid_actions[1]: return 1
        if choice in ['c', 'call']:
            if valid_actions[1]: return 1 
            if valid_actions[2]: return 2 
        if choice in ['b', 'bet', 'r', 'raise'] and valid_actions[3]: return 3
        if choice in ['a', 'all', 'allin', 'shove'] and valid_actions[6]: return 6
        print("  [!] Invalid move or move not allowed. Try again.")

def main():
    table = Table()
    game = Game(table)
    
    p1 = humanPlayer("PokerBot", table)
    p2 = humanPlayer("YOU", table)
    game.players = [p1, p2]
    
    # Initialize "Safety Belt"
    police_guard = PoliceBot()
    
    print("Loading Bot...")
    initial_state = game.reset()
    input_size = len(initial_state)
    
    agent = Agent(input_size, output_size=7)
    
    try:
        agent.policy_net.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
        print(">>> Model loaded successfully!")
    except:
        try:
            agent.policy_net.load_state_dict(torch.load(MODEL_PATH))
            print(">>> Model loaded (legacy mode)!")
        except FileNotFoundError:
            print(f">>> ERROR: Could not find '{MODEL_PATH}'.")
            return
        
    agent.policy_net.eval()
    agent.epsilon = 0.0 
    
    print("\n>>> READY! Press Enter to deal...")
    input()

    while True:
        if p1.chips <= 0:
            print("\n>>> CONGRATULATIONS! You busted the Bot!")
            break
        if p2.chips <= 0:
            print("\n>>> GAME OVER. The Bot busted you.")
            break

        # Record chips BEFORE the hand starts
        p1_start_chips = p1.chips
        p2_start_chips = p2.chips

        state = game.reset()
        done = False
        print_game_state(game, p1, p2)
        
        while not done:
            curr_idx = game.current_player_index
            valid_actions = game.get_valid_actions()
            
            # --- BOT TURN ---
            if curr_idx == 0:
                print("  [Bot is thinking...]")
                time.sleep(1) 
                
                # 1. Ask Neural Net
                action = agent.select_action(state, valid_actions)
                
                
                move_str = ["Fold", "Check", "Call", "Bet", "Raise", "Raise", "ALL-IN"][action]
                print(f"  >>> Bot chooses: {move_str.upper()}")
                time.sleep(1.5)
                
            # --- HUMAN TURN ---
            else:
                action = get_human_action(valid_actions)
            
            # Step Game
            state, reward, done = game.step(action)
            
            if done:
                print("\n  --- HAND OVER ---")
                bot_hand_str = format_cards(p1.hand)
                print(f"  Bot had: {bot_hand_str}")
                
                # --- Result Logic ---
                # Check actual chips to decide winner (robust method)
                winner_found = False
                if p1.chips > p1_start_chips:
                     print(f"  Result: BOT WON this pot (+{p1.chips - p1_start_chips}).")
                elif p2.chips > p2_start_chips:
                     print(f"  Result: YOU WON this pot (+{p2.chips - p2_start_chips}).") 
                else:
                     print(f"  Result: Split Pot or Push.")
                # --------------------

                print("\n  [Press Enter for next hand...]")
                input()
                break
            
            print_game_state(game, p1, p2)

if __name__ == "__main__":
    main()