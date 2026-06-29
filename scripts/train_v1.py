import random
import argparse
from dataclasses import dataclass
from typing import List, Protocol, Dict

import mlflow
import torch

from engine.game import Game
from engine.metrics import MetricsTracker
from engine.player import humanPlayer
from engine.table import Table

from agent.agent import Agent
from agent.calling_station_v0 import calling_station_action
from agent.police_bot_v1 import PoliceBot
from agent.pressure_bot_v1 import PressureBot
from agent.punisher_bot_v1 import PunisherBot
from agent.trap_bot_v1 import TrapBot

EPISODES = 1500000
STACK_SIZE = 1000
TARGET_UPDATE = 1000
RESUME_FILE_PATH = "checkpoint_300000.pth"


@dataclass(frozen=True)
class DecisionContext:
    valid_actions: List[int]
    state: List[float]
    hand: list
    community: list
    to_call: int
    pot: int
    street: int
    hero_bet_in_round: int    # game.players[0].bet_in_round


class OpponentPolicy(Protocol):
    def select_action(self, ctx: DecisionContext) -> int:
        ...


class CallingStationPolicy:
    def select_action(self, ctx: DecisionContext) -> int:
        return calling_station_action(ctx.valid_actions)


class PoliceV1Policy:
    def __init__(self, bot: PoliceBot):
        self.bot = bot

    def select_action(self, ctx: DecisionContext) -> int:
        return self.bot.select_action(
            ctx.valid_actions,
            ctx.hand,
            ctx.community,
            ctx.to_call,
            ctx.pot
        )


class PunisherV1Policy:
    def __init__(self, bot: PunisherBot):
        self.bot = bot

    def select_action(self, ctx: DecisionContext) -> int:
        return self.bot.select_action(
            ctx.valid_actions,
            ctx.hand,
            ctx.community,
            ctx.to_call,
            ctx.pot,
            ctx.street,
            ctx.hero_bet_in_round
        )


class TrapV1Policy:
    def __init__(self, bot: TrapBot):
        self.bot = bot

    def select_action(self, ctx: DecisionContext) -> int:
        return self.bot.select_action(
            ctx.valid_actions,
            ctx.hand,
            ctx.community,
            ctx.to_call,
            ctx.pot,
            ctx.street,
            ctx.hero_bet_in_round
        )


class PressureV1Policy:
    def __init__(self, bot: PressureBot):
        self.bot = bot

    def select_action(self, ctx: DecisionContext) -> int:
        return self.bot.select_action(
            ctx.valid_actions,
            ctx.hand,
            ctx.community,
            ctx.to_call,
            ctx.pot,
            ctx.street,
            ctx.hero_bet_in_round
        )


class SelfPlayPolicy:
    def __init__(self, agent: Agent):
        self.agent = agent

    def select_action(self, ctx: DecisionContext) -> int:
        return self.agent.select_action(ctx.state, ctx.valid_actions)

def sample_villain_type() -> str:
    """
    Opponent Distribution for Exploitative Training:
      station (Loose-Passive):  40%
      police (Tight-Passive):   20%
      pressure (Loose-Aggro):   20%
      punisher (Tight-Aggro):   20%
      self:                     0%  (Disabled for pure exploitative training)
    """
    roll = random.random()
    if roll < 0.40:
        return "station"
    elif roll < 0.60:
        return "police"
    elif roll < 0.80:
        return "pressure"
    else:
        return "punisher"


def evaluate_against_villain(agent: Agent, villain_policy) -> dict:
    """Runs a fixed number of hands against a specific villain with zero exploration."""
    EVAL_HANDS = 1000

    # Create an isolated sandbox environment
    eval_table = Table()
    eval_tracker = MetricsTracker(big_blind=20)
    eval_game = Game(eval_table, tracker=eval_tracker)

    eval_game.players = [
        humanPlayer("Hero", eval_table),
        humanPlayer("Villain", eval_table)
    ]

    # Save current agent exploration rate to restore later
    original_epsilon = agent.epsilon
    agent.epsilon = 0.0  # Zero exploration for accurate evaluation
    agent.policy_net.eval()  # Ensure network is in eval mode

    for _ in range(EVAL_HANDS):
        if eval_game.players[0].chips <= 0 or eval_game.players[1].chips <= 0:
            for p in eval_game.players:
                p.chips = STACK_SIZE

        state = eval_game.reset()
        done = False

        while not done:
            curr_idx = eval_game.current_player_index
            valid_actions = eval_game.get_valid_actions()

            if curr_idx == 0:
                # Hero selects best known action
                with torch.no_grad():
                    action = agent.select_action(state, valid_actions)
                next_state, _, done = eval_game.step(action)
                state = next_state
            else:
                ctx = DecisionContext(
                    valid_actions=valid_actions,
                    state=state,
                    hand=eval_game.players[1].hand,
                    community=eval_game.table.community,
                    to_call=eval_game.table.current_bet - eval_game.players[1].bet_in_round,
                    pot=eval_game.table.pot,
                    street=eval_game.street,
                    hero_bet_in_round=eval_game.players[0].bet_in_round,
                )
                action = villain_policy.select_action(ctx)
                next_state, _, done = eval_game.step(action)
                state = next_state

    agent.epsilon = original_epsilon
    agent.policy_net.train()

    hero_stats = eval_tracker.stats.get("Hero")
    if hero_stats:
        return {
            "bb_100": hero_stats.bb_per_100(),
            "vpip": hero_stats.vpip_pct(),
            "pfr": hero_stats.pfr_pct(),
            "af": hero_stats.aggression_factor()
        }
    return {}



def main():
    parser = argparse.ArgumentParser(description="Train poker agent")
    parser.add_argument("--run-id", type=str, default=None, help="The unique MLflow run ID to resume")
    parser.add_argument("--run-name", type=str, default=None, help="The name of the new MLflow run (required if not resuming)")
    parser.add_argument("--checkpoint", type=str, default=None, help="The file path to the .pth weights file")
    parser.add_argument("--start-episode", type=int, default=0, help="The episode number to begin the training loop from")
    args = parser.parse_args()

    if not args.run_id and not args.run_name:
        parser.error("A --run-name is required when starting a fresh training run.")

    opponent_distribution = """
    Opponent Distribution :
      station (Loose-Passive):  40%
      police (Tight-Passive):   20%
      pressure (Loose-Aggro):   20%
      punisher (Tight-Aggro):   20%
      self:                     0%  
    """
    agent = Agent(input_size=44, output_size=7)
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("poker_agent_v1")
    if args.run_id:
        mlflow.start_run(run_id=args.run_id)
    else:
        mlflow.start_run(run_name=args.run_name)
    mlflow.set_tag("architectural_change", "Switched from intermediate step rewards to terminal hand rewards")

    print("Setting up the table...")
    table = Table()
    tracker = MetricsTracker(big_blind=20)
    game = Game(table, tracker=tracker)

    p1 = humanPlayer("Hero", table)
    p2 = humanPlayer("Villain", table)
    game.players = [p1, p2]

    initial_state = game.reset()
    input_size = len(initial_state)
    print(f"State Size: {input_size}")

    agent = Agent(input_size=44, output_size=7)

    punisher = PunisherBot()
    trap = TrapBot()
    pressure = PressureBot()
    police = PoliceBot()

    mlflow.log_params({
        "episodes_target": EPISODES,
        "stack_size": STACK_SIZE,
        "target_update_freq": TARGET_UPDATE,
        "batch_size": agent.batch_size,
        "gamma": agent.gamma,
        "epsilon_decay": agent.epsilon_decay,
        "learning_rate": agent.learning_rate,
        "opponent_distribution": opponent_distribution,
        "reward_type": "terminal_only"
    })

    if args.checkpoint:
        try:
            saved_weights = torch.load(args.checkpoint)
            agent.policy_net.load_state_dict(saved_weights)
            agent.target_net.load_state_dict(saved_weights)
            agent.epsilon = max(agent.epsilon_min, 1.0 * (agent.epsilon_decay ** args.start_episode))
            print(f">>> SUCCESS: Loaded checkpoint from '{args.checkpoint}'")
            print(f">>> Start Episode: {args.start_episode} | Recalculated Epsilon: {agent.epsilon:.6f}")
        except FileNotFoundError:
            print(f">>> ERROR: Checkpoint file '{args.checkpoint}' not found. Starting from scratch.")
            args.start_episode = 0
    else:
        print(">>> Info: Starting training from scratch to establish a clean baseline.")

    policies: Dict[str, OpponentPolicy] = {
        "station": CallingStationPolicy(),
        "police": PoliceV1Policy(police),
        "punisher": PunisherV1Policy(punisher),
        "trap": TrapV1Policy(trap),
        "pressure": PressureV1Policy(pressure),
        "self": SelfPlayPolicy(agent),
    }

    print("Starting Training...")

    total_profit = 0

    for episode in range(args.start_episode, EPISODES):
        if game.players[0].chips <= 0 or game.players[1].chips <= 0:
            for p in game.players:
                p.chips = STACK_SIZE

        villain_type = sample_villain_type()
        villain_policy = policies[villain_type]

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
                    reward = 0
                    agent.memory.append((hero_state, hero_action, reward, state, False))
                    agent.optimize_model()

                hero_state = state
                hero_stack_at_action = hero.chips
                hero_action = agent.select_action(state, valid_actions)

                next_state, _, done = game.step(hero_action)

                if done:
                    reward = hero.chips - starting_stack
                    agent.memory.append((hero_state, hero_action, reward, None, True))
                    agent.optimize_model()

                state = next_state

            else:
                villain_hand = game.players[1].hand
                villain_to_call = game.table.current_bet - game.players[1].bet_in_round
                villain_community = game.table.community

                ctx = DecisionContext(
                    valid_actions=valid_actions,
                    state=state,
                    hand=villain_hand,
                    community=villain_community,
                    to_call=villain_to_call,
                    pot=game.table.pot,
                    street=game.street,
                    hero_bet_in_round=game.players[0].bet_in_round,
                )

                action = villain_policy.select_action(ctx)

                next_state, _, done = game.step(action)

                if done and hero_state is not None:
                    reward = hero.chips - starting_stack
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

            print(
                f"Ep {episode}: Avg Profit: {avg_profit:.2f} | Epsilon: {agent.epsilon:.4f} | Last Opponent: {villain_type}")

            mlflow.log_metric("avg_profit", avg_profit, step=episode)
            mlflow.log_metric(key='epsilon', value=agent.epsilon, step=episode)

            hero_stats = tracker.stats.get("Hero")
            if hero_stats:
                mlflow.log_metric("hero_vpip", hero_stats.vpip_pct(), step=episode)
                mlflow.log_metric("hero_pfr", hero_stats.pfr_pct(), step=episode)
                mlflow.log_metric("hero_af", hero_stats.aggression_factor(), step=episode)
                mlflow.log_metric("hero_bb_100", hero_stats.bb_per_100(), step=episode)

            total_profit = 0

            if episode % 1000 == 0 and episode > 0:
                print(f"\n--- Running Evaluation Gauntlet (Episode {episode}) ---")

                gauntlet = {
                    "station": CallingStationPolicy(),
                    "police": PoliceV1Policy(police),
                    "pressure": PressureV1Policy(pressure),
                    "punisher": PunisherV1Policy(punisher)
                }

                for villain_name, policy in gauntlet.items():
                    print(f"  Evaluating vs {villain_name.upper()}...")
                    results = evaluate_against_villain(agent, policy)

                    if results:
                        # Log metrics prefixed by the villain's name
                        mlflow.log_metric(f"eval_vs_{villain_name}_bb100", results["bb_100"], step=episode)
                        mlflow.log_metric(f"eval_vs_{villain_name}_vpip", results["vpip"], step=episode)
                        mlflow.log_metric(f"eval_vs_{villain_name}_pfr", results["pfr"], step=episode)
                        mlflow.log_metric(f"eval_vs_{villain_name}_af", results["af"], step=episode)

                        print(f"    -> Winrate: {results['bb_100']:.2f} BB/100 | VPIP: {results['vpip']:.1f}%")

                print("--- Evaluation Complete ---\n")

                torch.save(agent.policy_net.state_dict(), f"checkpoint_{episode}.pth")

    print("Training Complete.")
    mlflow.end_run()
    torch.save(agent.policy_net.state_dict(), "poker_agent_v1.pth")



if __name__ == "__main__":
    main()