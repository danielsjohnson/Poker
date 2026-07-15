import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random

EPSILON_DECAY = 0.999998
EPSILON_MIN = 0.05
GAMMA = 0.99
BATCH_SIZE = 2048
LEARNING_RATE = 0.0001

class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super().__init__()
        # LSTM layer processes the sequence (batch, seq_len, features)
        self.lstm = nn.LSTM(input_size, 256, batch_first=True)
        
        # Value Stream
        self.value_layer1 = nn.Linear(256, 128)
        self.value_layer2 = nn.Linear(128, 1)
        
        # Advantage Stream
        self.adv_layer1 = nn.Linear(256, 128)
        self.adv_layer2 = nn.Linear(128, output_size)

    def forward(self, x):
        # Run through LSTM
        lstm_out, _ = self.lstm(x)
        
        # We only care about the features at the final time step of the sequence
        features = lstm_out[:, -1, :]
        
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
        
        # GPU Tensor Sequence Replay Buffer
        self.mem_size = 500000
        self.seq_len = 12
        self.ptr = 0
        self.size = 0
        
        self.state_mem = torch.zeros((self.mem_size, self.seq_len, input_size), dtype=torch.float32, device=self.device)
        self.next_state_mem = torch.zeros((self.mem_size, self.seq_len, input_size), dtype=torch.float32, device=self.device)
        self.action_mem = torch.zeros((self.mem_size, 1), dtype=torch.long, device=self.device)
        self.reward_mem = torch.zeros((self.mem_size,), dtype=torch.float32, device=self.device)
        self.done_mem = torch.zeros((self.mem_size,), dtype=torch.bool, device=self.device)

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
        
    def store_transition(self, state, action, reward, next_state, done):
        self.state_mem[self.ptr] = torch.tensor(state, dtype=torch.float32, device=self.device)
        self.action_mem[self.ptr] = action
        self.reward_mem[self.ptr] = reward
        self.done_mem[self.ptr] = done
        
        if next_state is not None:
            self.next_state_mem[self.ptr] = torch.tensor(next_state, dtype=torch.float32, device=self.device)
        else:
            self.next_state_mem[self.ptr] = 0.0
            
        self.ptr = (self.ptr + 1) % self.mem_size
        self.size = min(self.size + 1, self.mem_size)

    def optimize_model(self):
        if self.size < self.batch_size:
            return
        
        idxs = torch.randint(0, self.size, (self.batch_size,), device=self.device)
        
        state_batch = self.state_mem[idxs]
        action_batch = self.action_mem[idxs]
        reward_batch = self.reward_mem[idxs]
        next_state_batch = self.next_state_mem[idxs]
        done_batch = self.done_mem[idxs]
        
        non_final_mask = ~done_batch
        non_final_next_states = next_state_batch[non_final_mask]
        
        next_state_values = torch.zeros(self.batch_size, device=self.device)
        if len(non_final_next_states) > 0:
            best_next_actions = self.policy_net(non_final_next_states).argmax(1).unsqueeze(1)
            next_state_values[non_final_mask] = self.target_net(non_final_next_states).gather(1, best_next_actions).squeeze(1).detach()

        expected_state_action_values = reward_batch + (next_state_values * self.gamma)

        q_values = self.policy_net(state_batch).gather(1, action_batch)

        loss = F.smooth_l1_loss(q_values, expected_state_action_values.unsqueeze(1))
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
