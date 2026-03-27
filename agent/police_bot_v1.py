from engine.hand_detection import Hand_Detection

class PoliceBot:
    def __init__(self):
        self.detector = Hand_Detection()

    def select_action(self, valid_actions, hand, community_cards, amount_to_call, pot_size):
        """
        THE POLICE BOT (FIXED)
        - Pre-flop: Strict ranges (Premiums Raise, Pocket Pairs Call).
        - Post-flop: Fit-or-Fold.
        - Math: Uses Pot Odds, not absolute chips.
        """
        # --- 0. PARSE VALID ACTIONS ---
        can_fold   = valid_actions[0]
        can_check  = valid_actions[1]
        can_call   = valid_actions[2]
        can_bet    = valid_actions[3]
        can_raise  = valid_actions[4]
        can_all_in = valid_actions[6]

        # --- 1. IDENTIFY STATE ---
        is_preflop = (len(community_cards) == 0)

        # Avoid division by zero
        if pot_size == 0: pot_size = 1 
        pot_odds = amount_to_call / (pot_size + amount_to_call)

        # --- 2. PRE-FLOP STRATEGY (Explicit Ranges) ---
        if is_preflop:
            # Map ranks to integers for easy comparison
            rank_map = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
            
            r1 = rank_map[hand[0].rank]
            r2 = rank_map[hand[1].rank]
            is_pair = (r1 == r2)
            is_suited = (hand[0].suit == hand[1].suit)
            high_card = max(r1, r2)
            low_card = min(r1, r2)

            # TIER A: PREMIUMS (AA, KK, QQ, AK) -> RAISE/SHOVE
            if (is_pair and r1 >= 12) or (high_card == 14 and low_card == 13):
                if can_raise: return 4
                if can_bet: return 3
                if can_all_in: return 6
                return 2

            # TIER B: STRONG (JJ, TT, 99, AQ, AJ, KQ) -> CALL/RAISE SMALL
            is_strong = (is_pair and r1 >= 9) or \
                        (high_card == 14 and low_card >= 11) or \
                        (high_card == 13 and low_card >= 12)
            
            if is_strong:
                # If it's a huge bet (All-In), just Call. Don't re-raise huge unless Tier A.
                if can_call: return 2
                return 0

            # TIER C: SPECULATIVE (Pairs 22-88, Suited Connectors) -> CALL CHEAP
            # We only play these if it's cheap (Pot Odds < 10% or just a limp)
            is_speculative = (is_pair) or \
                             (is_suited and high_card >= 10) or \
                             (is_suited and (high_card - low_card) == 1) # Suited Connector
            
            if is_speculative:
                if amount_to_call == 0: return 1 # Check free
                if pot_odds < 0.15: # Call if cheap relative to pot
                     return 2 if can_call else 0
                return 0

            # TIER D: TRASH -> FOLD
            if can_check: return 1
            return 0

        # --- 3. POST-FLOP STRATEGY (Real Awareness) ---
        else:
            # Detect Hand Strength
            result = self.detector.find_hand(hand, community_cards)

            # Extract the string name of the hand (handles both raw strings and tuples)
            hand_name = result[0] if isinstance(result, tuple) else result

            # Map the string name to an integer strength
            hand_rank_map = {
                "HighCard": 0,
                "Pair": 1,
                "Two Pair": 2,
                "Trips": 3,
                "Straight": 4,
                "Flush": 5,
                "Full House": 6,
                "Quads": 7,
                "StraightFlush": 8,
                "RoyalFlush": 9
            }

            strength = hand_rank_map.get(hand_name, 0)
            # LOGIC:
            
            # 1. STRONG (Two Pair or Better) -> BET/RAISE
            if strength >= 2:
                if can_raise: return 4
                if can_bet: return 3
                return 2 # Call if we can't raise

            # 2. DECENT (One Pair) -> CHECK/CALL
            if strength == 1:
                # If they bet huge (Overbet), Fold (Police plays safe)
                if amount_to_call > pot_size: return 0 
                
                # Otherwise Call or Check
                if amount_to_call > 0: return 2 if can_call else 0
                return 1 # Check back

            # 3. WEAK (High Card) -> GIVE UP
            # Unless we have a flush draw (4 cards to flush)? 
            # (For now, keep it simple: Police doesn't chase draws)
            if can_check: return 1
            return 0