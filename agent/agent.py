import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque

EPSILON_DECAY = 0.9999
EPSILON_MIN = 0.05
GAMMA = 0.99
BATCH_SIZE = 1024
LEARNING_RATE = 0.0001

class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super().__init__()
        # Shared Feature Network
        self.feature_layer1 = nn.Linear(input_size, 512)
        self.feature_layer2 = nn.Linear(512, 512)
        
        # Value Stream
        self.value_layer1 = nn.Linear(512, 256)
        self.value_layer2 = nn.Linear(256, 1)
        
        # Advantage Stream
        self.adv_layer1 = nn.Linear(512, 256)
        self.adv_layer2 = nn.Linear(256, output_size)

    def forward(self, x):
        features = F.leaky_relu(self.feature_layer1(x))
        features = F.leaky_relu(self.feature_layer2(features))
        
        value = F.leaky_relu(self.value_layer1(features))
        value = self.value_layer2(value)
        
        adv = F.leaky_relu(self.adv_layer1(features))
        adv = self.adv_layer2(adv)
        
        return value + (adv - adv.mean(dim=1, keepdim=True))

class Agent:
    def __init__(self, input_size, output_size):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Agent running on: {self.device}")
        self.policy_net = DQN(input_size, output_size).to(self.device)
        self.target_net = DQN(input_size, output_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=LEARNING_RATE)
        self.memory = deque(maxlen=100000)

        self.epsilon = 1.0
        self.epsilon_min = EPSILON_MIN
        self.epsilon_decay = EPSILON_DECAY
        self.gamma = GAMMA
        self.batch_size = BATCH_SIZE
        self.learning_rate = LEARNING_RATE

    def select_action(self, state, valid_actions):
        if random.random() < self.epsilon:
            choices = [i for i, valid in enumerate(valid_actions) if valid == 1]
            if not choices: return 0
            return random.choice(choices)
        else:
            state_tensor = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            with torch.no_grad():
                q_values = self.policy_net(state_tensor)
                
            mask = torch.tensor(valid_actions, dtype=torch.bool, device=self.device)
            q_values[0, ~mask] = -1e9
            
            return q_values.argmax().item()
        
    def optimize_model(self):
        if len(self.memory) < BATCH_SIZE:
            return
        
        experiences = random.sample(self.memory, BATCH_SIZE)
        batch_state, batch_action, batch_reward, batch_next_state, batch_done = zip(*experiences)
        
        state_batch = torch.tensor(batch_state, dtype=torch.float32, device=self.device)
        action_batch = torch.tensor(batch_action, dtype=torch.long, device=self.device).unsqueeze(1)
        reward_batch = torch.tensor(batch_reward, dtype=torch.float32, device=self.device)

        non_final_mask = torch.tensor([s is not None for s in batch_next_state], device=self.device, dtype=torch.bool)
        non_final_next_states_list = [s for s in batch_next_state if s is not None]

        if len(non_final_next_states_list) > 0:
            non_final_next_states = torch.tensor(non_final_next_states_list, dtype=torch.float32, device=self.device)
        else:
            non_final_next_states = torch.empty(0, device=self.device)
        next_state_values = torch.zeros(BATCH_SIZE, device=self.device)
        if len(non_final_next_states) > 0:
            next_state_values[non_final_mask] = self.target_net(non_final_next_states).max(1)[0].detach()

        expected_state_action_values = reward_batch + (next_state_values * self.gamma)

        q_values = self.policy_net(state_batch).gather(1, action_batch)

        loss = F.smooth_l1_loss(q_values, expected_state_action_values.unsqueeze(1))
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
