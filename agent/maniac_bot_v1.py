import random

class ManiacBot:
    def __init__(self):
        # Probabilistic parameters to prevent overfitting
        self.random_all_in_prob = 0.12 # 12% chance to randomly shove all-in regardless of hand
        self.aggression_prob = 0.85    # 85% chance to bet/raise when not shoving all-in

    def select_action(self, ctx) -> int:
        """
        Returns action index.
        0: Fold, 1: Check, 2: Call, 3: Min Raise, 4: 50% Pot, 5: Pot, 6: All-In
        """
        valid = ctx.valid_actions
        
        # 1. Random All-In Bluff!
        if valid[6] == 1 and random.random() < self.random_all_in_prob:
            return 6
            
        # 2. Hyper-Aggressive Play
        if random.random() < self.aggression_prob:
            if valid[5] == 1: return 5 # Pot bet
            if valid[4] == 1: return 4 # 50% pot bet
            if valid[3] == 1: return 3 # Min raise
            
        # 3. If we didn't bet/raise, or couldn't, default to check/call
        if valid[1] == 1: return 1
        if valid[2] == 1: return 2
        
        return 0

class ManiacV1Policy:
    def __init__(self, bot: ManiacBot):
        self.bot = bot
    
    def select_action(self, ctx) -> int:
        return self.bot.select_action(ctx)
