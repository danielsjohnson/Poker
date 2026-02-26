import requests
import time
from engine.game import Game
from engine.table import Table
from engine.player import Player

API_URL = "http://127.0.0.1:8000/get_action"

def main():
    print("Setting up the poker table...")
    table = Table()
    game = Game(table)
    p1 = Player("Hero", table)
    game.players.append(p1)
    p2 = Player("Villain", table)
    game.players.append(p2)
    p1.chips = 1000
    p2.chips = 1000
    game.reset()
    done = False
    turn_count = 0

    print("\nStarting hand...")

    while not done:
        turn_count += 1
        current_player = game.active[game.current_player_index]
        state_vector = game.get_state()
        valid_actions = game.get_valid_actions()
        print(f"\nTurn {turn_count}: {current_player.name}'s turn")
        print("Asking API for action...")
        payload = {
            "state_vector": state_vector,
            "valid_actions": valid_actions
        }
        try:
            response = requests.post(API_URL, json=payload)
            response_data = response.json()

            print(f"Debug: API response data: {response_data}")

            action_index = response_data["action_index"]
            bot_action = response_data["bot_action"]

            print(f"API chose action: {bot_action} (index {action_index})")

        except requests.exceptions.ConnectionError:
            print("Could not connect to API. Make sure the server is running.")
            return

        next_state, reward, done = game.step(action_index)
        time.sleep(1)

        if turn_count > 50:
            print("Ending hand due to turn limit.")
            break

        print("Hand over.")

if __name__ == "__main__":
    main()

