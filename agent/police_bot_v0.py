class PoliceBot:
    def __init__(self):
        # Map face cards to numeric values for easy comparison
        self.rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 
            '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }

    def _is_hand_strong(self, hand):
        """
        Helper: Returns True if the hand is good enough to defend with.
        Criteria: Pairs, High Cards (10+), or any Ace.
        """
        if not hand or len(hand) < 2:
            return False

        try:
            r1_str = str(hand[0].rank)
            r2_str = str(hand[1].rank)
            val1 = self.rank_map.get(r1_str, 0)
            val2 = self.rank_map.get(r2_str, 0)
        except AttributeError:
            return False

        # 1. POCKET PAIRS
        if val1 == val2: return True
        # 2. BROADWAY (Both 10+)
        if val1 >= 10 and val2 >= 10: return True
        # 3. HIGH ACE
        if val1 == 14 or val2 == 14: return True

        return False

    def select_action(self, valid_actions, hand, to_call):
        """
        Decides the move based on 'Police' logic.
        RETURNS INTEGERS:
        0: Fold
        1: Check
        2: Call
        6: All-In
        """
        is_strong = self._is_hand_strong(hand)

        # SCENARIO A: Aggression (We have to pay to see the next card)
        if to_call > 0:
            if is_strong:
                # TRAP: Call with good hands
                if valid_actions[2] == 1: # Call available
                    return 2
                elif valid_actions[6] == 1: # Only All-In available
                    return 6
            else:
                # FOLD: Trash hands
                return 0 

        # SCENARIO B: Free Play (Check)
        else:
            # Always take the free card
            if valid_actions[1] == 1: # Check available
                return 1
            return 2 # Fallback to Call (shouldn't happen if to_call is 0)
        
        # Emergency Fallback
        return 0 # Fold