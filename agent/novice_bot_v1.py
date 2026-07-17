import random
from engine.hand_detection import Hand_Detection

class NoviceBot:
    def __init__(self):
        self.hand_detector = Hand_Detection()
        # Probabilistic parameters to prevent overfitting
        self.limp_call_prob = 0.95 # 95% of the time plays loose passive preflop, 5% folds garbage to big raises
        self.fit_bet_prob = 0.85 # 85% of the time bets when they hit a pair or better
        self.miss_fold_prob = 0.90 # 90% of the time folds if they miss and face a bet

    def _is_made_hand(self, hand, community):
        """Checks if the bot has at least a pair."""
        if not hand:
            return False
        
        # Pocket pair
        if hand[0].rank == hand[1].rank:
            return True
            
        if not community:
            return False
            
        # Check if any hole card matches any community card
        hole_ranks = [c.rank for c in hand]
        comm_ranks = [c.rank for c in community]
        for hr in hole_ranks:
            if hr in comm_ranks:
                return True
                
        return False

    def select_action(self, ctx) -> int:
        """
        Returns action index.
        0: Fold, 1: Check, 2: Call, 3: Min Raise, 4: 50% Pot, 5: Pot, 6: All-In
        """
        valid = ctx.valid_actions
        street = ctx.street
        
        # Always prioritize checking if it's free
        can_check = (valid[1] == 1)
        can_call = (valid[2] == 1)
        
        # Preflop: Limp / Call with almost everything
        if street == 0:
            if random.random() < self.limp_call_prob:
                if can_check: return 1
                if can_call: return 2
            # Rarely folds preflop if facing a raise
            if can_check: return 1
            return 0
            
        # Postflop: Fit or Fold
        made_hand = self._is_made_hand(ctx.hand, ctx.community)
        
        if made_hand:
            # We hit the board! 
            if random.random() < self.fit_bet_prob:
                # Bet/Raise if we can
                if valid[4] == 1: return 4 # 50% pot bet
                if valid[3] == 1: return 3 # Min raise
            
            # If we don't bet, or can't bet, we check/call (passive behavior)
            if can_check: return 1
            if can_call: return 2
            return 0
        else:
            # We completely missed the board
            if not can_check:
                # Facing a bet
                if random.random() < self.miss_fold_prob:
                    return 0 # Fold
                else:
                    if can_call: return 2 # Random sticky call
            
            # If it's checked to us, just check
            if can_check: return 1
            return 0

class NoviceV1Policy:
    def __init__(self, bot: NoviceBot):
        self.bot = bot
    
    def select_action(self, ctx) -> int:
        return self.bot.select_action(ctx)
