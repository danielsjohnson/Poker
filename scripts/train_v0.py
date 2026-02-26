import torch
from engine.game import Game
from engine.table import Table
from engine.player import humanPlayer
from agent.agent import Agent
import random
from agent.calling_station_v0 import calling_station_action
from agent.police_bot_v0 import PoliceBot

EPISODES = 1500000
STACK_SIZE = 1000
TARGET_UPDATE = 1000
RESUME_FILE_PATH = "poker_agent_final.pth"

def main():
    print("Setting up the table...")
    table = Table()
    game = Game(table)
    
    p1 = humanPlayer("Hero", table)
    p2 = humanPlayer("Villain", table)
    game.players = [p1, p2]
    
    initial_state = game.reset()
    input_size = len(initial_state) 
    print(f"State Size: {input_size}")

    police = PoliceBot()
    
    agent = Agent(input_size=44, output_size=7)

    try:
        
        saved_weights = torch.load(RESUME_FILE_PATH)
        
        agent.policy_net.load_state_dict(saved_weights)
        agent.target_net.load_state_dict(saved_weights)
        
        agent.epsilon = 0.05
        
        start_episode = 500001
        print(f">>> SUCCESS: Resuming from Episode {start_episode}")

    except FileNotFoundError:
        print(">>> WARNING: Save file not found. Starting from scratch.")
        start_episode = 0

    print("Starting Training...")

    total_profit = 0
    best_profit = -float('inf')

    villain_type = "station"
    
    for episode in range(start_episode, EPISODES):
        if game.players[0].chips <= 0 or game.players[1].chips <= 0:
            for p in game.players:
                p.chips = STACK_SIZE
        
        roll = random.random()
        if roll < 0.30:
            villain_type = "station"
        elif roll < 0.60:
            villain_type = "self" 
        else:
            villain_type = "police"

        state = game.reset()
        hero = game.players[0]
        starting_stack = hero.chips
        hero_state = None
        hero_action = None
        hero_stack_at_action = 0
        
        done = False
        while not done:
            curr_player_index = game.current_player_index
            valid_actions = game.get_valid_actions()
            
            if curr_player_index == 0:
                if hero_state is not None:
                    reward = hero.chips - hero_stack_at_action
                    
                    agent.memory.append((hero_state, hero_action, reward, state, False))
                    agent.optimize_model()
                
                hero_state = state
                hero_stack_at_action = hero.chips
                hero_action = agent.select_action(state, valid_actions)
                
                next_state, _, done = game.step(hero_action)
                
                if done:
                    reward = hero.chips - hero_stack_at_action
                    agent.memory.append((hero_state, hero_action, reward, None, True))
                    agent.optimize_model()
                
                state = next_state

            else:
                villain_hand = game.players[1].hand
                villain_to_call = game.table.current_bet - game.players[1].bet_in_round

                if villain_type == "station":
                    action = calling_station_action(valid_actions)
                    
                elif villain_type == "police":
                    action = police.select_action(valid_actions, villain_hand, villain_to_call)
                    
                else: 
                    action = agent.select_action(state, valid_actions)
                
                next_state, _, done = game.step(action)
                
                if done:
                    if hero_state is not None:
                        reward = hero.chips - hero_stack_at_action
                        agent.memory.append((hero_state, hero_action, reward, None, True))
                        agent.optimize_model()
                
                state = next_state

        profit = hero.chips - starting_stack
        total_profit += profit

        if episode % TARGET_UPDATE == 0:
            agent.target_net.load_state_dict(agent.policy_net.state_dict())

        if agent.epsilon > agent.epsilon_min:
            agent.epsilon *= agent.epsilon_decay

        if episode % 1000 == 0 and episode > 0:
            avg_profit = total_profit / 1000
            
            print(f"Ep {episode}: Avg Profit: {avg_profit:.2f} | Epsilon: {agent.epsilon:.4f} | Last Opponent: {villain_type}")
            
            if avg_profit > best_profit:
                best_profit = avg_profit
                torch.save(agent.policy_net.state_dict(), "poker_shark_best.pth")
            
            total_profit = 0

        if episode % 50000 == 0 and episode > 0:
            torch.save(agent.policy_net.state_dict(), f"checkpoint_{episode}.pth")

    print("Training Complete.")
    torch.save(agent.policy_net.state_dict(), "poker_agent_final.pth")

if __name__ == "__main__":
    main()