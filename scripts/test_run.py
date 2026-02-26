from engine.game import Game
from engine.table import Table
from engine.player import humanPlayer
from agent.agent import Agent

def main():
    # --- 1. SETUP THE GAME BOARD ---
    print("Setting up table...")
    table = Table()
    game = Game(table)

    # Create two players with chips
    p1 = humanPlayer("Hero", table)
    p1.chips = 1000
    game.players.append(p1)

    p2 = humanPlayer("Villain", table)
    p2.chips = 1000
    game.players.append(p2)

    # --- 2. INITIALIZE STATE & AGENT ---
    # We reset the game once to get the initial state and measure its size
    print("Resetting game to measure state vector...")
    initial_state = game.reset()
    
    input_size = len(initial_state)
    output_size = 7 # Fold, Check, Call, 1/2 Pot, 3/4 Pot, Pot, All-In
    
    print(f"State Vector Size: {input_size}")
    print("Initializing DQN Agent...")
    
    # Create the agent
    agent = Agent(input_size, output_size)

    # --- 3. THE BLIND TEST LOOP ---
    print("\n--- STARTING BLIND PLAY TEST ---")
    
    done = False
    turn_count = 0
    
    while not done:
        turn_count += 1
        
        # A. Get what the current player sees
        state = game.get_state()
        
        # B. Ask Agent what to do (will likely be random exploration)
        action = agent.select_action(state)
        
        # Debug Print
        current_player = game.active[game.current_player_index]
        print(f"Turn {turn_count}: {current_player.name} chooses Action {action}")
        
        # C. Execute the move
        # Note: step() returns (next_state, reward, done)
        next_state, reward, done = game.step(action)

        # Safety break (in case the bot keeps checking infinitely)
        if turn_count > 50:
            print("Force stopping loop (infinite game detected).")
            break

    print(f"\n--- GAME OVER ---")
    print(f"Winner declared or Showdown reached.")
    print(f"Remaining Chips: {p1.name}: {p1.chips}, {p2.name}: {p2.chips}")

if __name__ == "__main__":
    main()