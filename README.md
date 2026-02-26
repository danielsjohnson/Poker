### PokerRL: Deep Q-Network Agent for Texas Hold'em
This project implements a Deep Q-Network (DQN) agent for Heads-Up No-Limit Texas Hold’em with the goal of consistently exploiting novice-style opponents rather than converging to theoretical Nash equilibrium.

The agent utilizes a Deep Q-Network (DQN) with Experience Replay to approximate optimal strategies. The project demonstrates advanced RL concepts, including Curriculum Learning and Self-Play, to overcome the non-transitive dynamics of poker.

Key Features
Custom Environment: A fully functional, rule-based Texas Hold'em engine built from scratch (not a wrapper like OpenAI Gym), handling complex logic like side-pots, split pots, and hand evaluation.

Deep Q-Learning: Implemented a DQN with Target Networks and Experience Replay to stabilize training in a high-variance environment.

Curriculum Learning: Addressed "Nash Equilibrium Drift" (where agents became hyper-aggressive in self-play) by introducing heuristic baselines ("Calling Station" bots) to enforce value-betting discipline.

Optimized Feature Engineering: Utilized One-Hot Encoding for card suits to eliminate ordinal bias, ensuring the neural network interprets card inputs correctly.

Tech Stack
Language: Python 3.12

ML Framework: PyTorch

Architecture: Deep Q-Network (Linear layers with Leaky ReLU activations)

Optimization: Adam Optimizer, Epsilon-Greedy Exploration
🧠 Core Architecture
Model

Fully connected DQN

44-dimensional state vector

Architecture:

| Component      | Value                    |
| -------------- | ------------------------ |
| Input Size     | 44                       |
| Hidden Layers  | 2                        |
| Hidden Units   | 128                      |
| Activation     | ReLU                     |
| Output         | Discrete masked Q-values |
| Target Network | Yes                      |
| Replay Buffer  | Yes                      |
Actions: Fold | Check | Call | Geometric Raise | All-in


🎯 Design Philosophy

Instead of training exclusively via self-play, this project emphasizes:

1. Exploitative Learning

The agent is optimized to beat novice-style players rather than converge to equilibrium.

2. Curriculum Learning

Opponents are introduced in stages to shape specific behavioral traits.

3. Adversarial Opponent Design

Bots are intentionally constructed to expose weaknesses such as:

Over-aggression

Spew bluffs

Blind continuation betting

4. Controlled Iteration

Only one axis is changed per training iteration:

Opponents

Architecture

Features

Reward shaping

Never multiple at once.
### Milestones

Milestone 1:
Create Poker engine

Milestone 2:
Make the Poker engine a valid environment for DQN

Milestone 3:
Self-play + cirriculum based bots

After self play, the bot was way to over agressive.  It would often go all in preflop and try to get the opponant to fold.  This,k combined with the one hot encoding for the suits, made me want to start training from scratch.  I trained it first on a calling station so it could quickly learn the hand strengths and to not bluff, then i transitioned to mixed training so it would self play or play against the calling station randomly.

The bot is still too agressive.  I am going to train it more using the same strategy.

I implimented a police bot that would only call or jam with good hands so the agent gets lucky less often.  When I inspected, the bot stopped jamming preflop but would jam on the flop every single time.  I am going to try to let it run a million games overnight.  I think it just needs to get unlucky more to learn that this is not correct play.

Still too aggressive. I need to make the opponents more aggressive.  They never raise so the bot is not sure what to do when i raise.  This is where the bot will be frozen at v0 and retrained.

Milestone 4:
Make the bot able to beat a rule-based bot

Miestone 5:
Make the bot able to beat one of five rule based bots with different personalities, chosen at random at the start of the game(general strategy).

Milestone 6:
Make the bot able to exploit one of 5 random bots chosen at random, based on aggression metrics, such as VPIP and avg preflop bet.

Engineering Challenges & Solutions
(This section highlights the problem-solving process during development)

1. Enforcing the rules
Problem: The bot would fold after already going all in or try to do other illegal actions.
Solution: Implemented a mask to set the illegal actions' q-values to -infinity so the bot will never choose an illegal action

2. The "Maniac" Phase (Nash Equilibrium Drift)
Problem: During the initial 200,000 episodes of pure self-play, the agent discovered a local optimum of hyper-aggression. Since its clone opponent would often fold to pressure, the agent learned to "shove" (Go All-In) pre-flop with almost any two cards. 
Solution: I implemented a Curriculum Learning phase. Instead of pure self-play, I introduced a "Calling Station" bot (a rule-based agent that never folds) into the training loop. This forced the RL agent to relearn "Value Betting"—betting only when it actually holds a strong hand—stabilizing the policy.

3.  Feature Bias in State Representation
Problem: Initially, card suits were fed into the network as normalized scalars (e.g., Hearts=0.0, Clubs=1.0). The network incorrectly inferred a mathematical magnitude relationship between suits (i.e., treating Clubs as "greater than" Hearts). 
Solution: I refactored the state space to use One-Hot Encoding for suits. This increased the state vector size but allowed the network to correctly identify flushes without false ordinal bias.

