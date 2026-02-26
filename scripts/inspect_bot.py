import torch
from engine.game import Game
from engine.table import Table
from engine.player import humanPlayer
from agent.agent import Agent
import time

EPISODES = 20
STACK_SIZE = 1000
MODEL_PATH = "poker_agent_final.pth"


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
    
    agent = Agent(input_size, output_size=7)
    agent.policy_net.load_state_dict(torch.load(MODEL_PATH))
    agent.policy_net.eval()
    agent.epsilon = 0.0
    print("Starting Training...")

    best_profit = -float('inf')
    
    for episode in range(EPISODES):
        if game.players[0].chips <= 0 or game.players[1].chips <= 0:
            for p in game.players:
                p.chips = STACK_SIZE

        state = game.reset()        
        done = False
        while not done:
            valid_actions = game.get_valid_actions()
            action = agent.select_action(state, valid_actions)
            
            next_state, reward, done = game.step(action)
            state = next_state
            game.render()
            print(f"P1: {p1.chips} | P2: {p2.chips}")
            time.sleep(2)

            
if __name__ == "__main__":
    main()