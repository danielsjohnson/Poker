"""
Trap Bot v1 - Delayed Punishment & Pot Control Teacher

Purpose: Punish auto c-bets, auto double barrels, and overbetting into passive lines.
Teaches pot control, street awareness, and delayed aggression recognition.

Strategy: Appears passive preflop and on flop, but becomes extremely aggressive on
turn and river with strong hands. Disguises hand strength early.
"""

import random
from engine.hand_detection import Hand_Detection


class TrapBot:
    def __init__(self):
        self.rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        self.hand_detector = Hand_Detection()

    def _is_premium(self, hand):
        """Check if hand is AA or KK."""
        if not hand or len(hand) < 2:
            return False

        r1 = str(hand[0].rank)
        r2 = str(hand[1].rank)
        v1 = self.rank_map.get(r1, 0)
        v2 = self.rank_map.get(r2, 0)

        return v1 == v2 and v1 >= 13  # AA or KK

    def _is_decent_hand(self, hand):
        """Check if hand is worth calling with."""
        if not hand or len(hand) < 2:
            return False

        r1 = str(hand[0].rank)
        r2 = str(hand[1].rank)
        v1 = self.rank_map.get(r1, 0)
        v2 = self.rank_map.get(r2, 0)

        # Any pair
        if v1 == v2:
            return True

        # High cards
        if v1 >= 10 or v2 >= 10:
            return True

        # Suited connectors
        if hand[0].suit == hand[1].suit and abs(v1 - v2) <= 2:
            return True

        return False

    def _get_postflop_strength(self, hand, community):
        """
        Evaluate postflop hand strength.
        Returns: 'monster', 'top_pair', 'draw', 'marginal', 'air'
        """
        if not community:
            return 'air'

        hand_result = self.hand_detector.find_hand(hand, community)
        hand_type = hand_result[0]

        # Monster: Two Pair or better
        if hand_type in ['Two Pair', 'Trips', 'Straight', 'Flush', 'Full House', 'Quads', 'StraightFlush', 'RoyalFlush']:
            return 'monster'

        # Top Pair
        if hand_type == 'Pair':
            pair_rank = hand_result[1]
            pair_value = self.rank_map.get(pair_rank, 0)

            # Check if we have top pair
            board_ranks = [self.rank_map.get(str(c.rank), 0) for c in community]
            top_board_card = max(board_ranks)

            if pair_value == top_board_card:
                return 'top_pair'
            elif pair_value >= 11:  # Overpair
                return 'top_pair'
            else:
                return 'marginal'

        # Check for draws
        if self._has_draw(hand, community):
            return 'draw'

        return 'air'

    def _has_draw(self, hand, community):
        """Check if hand has flush draw or straight draw."""
        total_cards = hand + community

        # Check flush draw
        suits = {}
        for card in total_cards:
            suits[card.suit] = suits.get(card.suit, 0) + 1
        if any(count >= 4 for count in suits.values()):
            return True

        # Simplified straight draw check
        ranks = sorted(set([self.rank_map.get(str(c.rank), 0) for c in total_cards]))
        for i in range(len(ranks) - 3):
            window = ranks[i:i+4]
            if window[-1] - window[0] <= 4:
                return True

        return False

    def _is_draw_heavy_board(self, community):
        """Check if board has many draws (suited or connected)."""
        if len(community) < 3:
            return False

        # Check for flush draws (3 of same suit)
        suits = {}
        for card in community:
            suits[card.suit] = suits.get(card.suit, 0) + 1
        if any(count >= 3 for count in suits.values()):
            return True

        # Check for connected cards
        ranks = sorted([self.rank_map.get(str(c.rank), 0) for c in community])
        for i in range(len(ranks) - 2):
            if ranks[i+2] - ranks[i] <= 4:
                return True

        return False

    def select_action(self, valid_actions, hand, community, to_call, pot, street, villain_bet):
        """
        Main decision function.

        Action mapping:
        0: Fold
        1: Check
        2: Call
        3: Raise 50% pot
        4: Raise 75% pot
        5: Raise 100% pot
        6: All-In
        """

        # Pre-flop: mostly passive
        if street == 0:
            return self._preflop_strategy(valid_actions, hand, to_call)

        # Flop: passive with strong hands
        elif street == 1:
            return self._flop_strategy(valid_actions, hand, community, to_call, pot)

        # Turn: aggressive with strong hands
        elif street == 2:
            return self._turn_strategy(valid_actions, hand, community, to_call, pot)

        # River: very aggressive with strong hands
        else:
            return self._river_strategy(valid_actions, hand, community, to_call, pot)

    def _preflop_strategy(self, valid_actions, hand, to_call):
        """Pre-flop: Rarely 3-bet (only AA/KK), mostly flat-call."""
        is_premium = self._is_premium(hand)
        is_decent = self._is_decent_hand(hand)

        if to_call > 0:
            # Only 3-bet with AA/KK
            if is_premium:
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[3] == 1:
                    return 3

            # Flat call with decent hands
            if is_decent:
                if valid_actions[2] == 1:
                    return 2

            # Fold trash
            return 0
        else:
            # Rarely raise, mostly check/limp
            if is_premium and random.random() < 0.3:  # 30% raise with AA/KK
                if valid_actions[3] == 1:
                    return 3

            if valid_actions[1] == 1:
                return 1
            return 0

    def _flop_strategy(self, valid_actions, hand, community, to_call, pot):
        """Flop: Passive - check/call with strong hands, never raise unless draw-heavy."""
        strength = self._get_postflop_strength(hand, community)
        draw_heavy = self._is_draw_heavy_board(community)

        # Strong hands (Two Pair+): Mostly check or call
        if strength == 'monster':
            if to_call > 0:
                # Call small bets 70% of time
                if to_call <= pot * 0.6:
                    if random.random() < 0.7:
                        if valid_actions[2] == 1:
                            return 2

                # Only raise if board is draw-heavy
                if draw_heavy:
                    if valid_actions[4] == 1:
                        return 4
                    if valid_actions[3] == 1:
                        return 3

                # Otherwise call
                if valid_actions[2] == 1:
                    return 2
            else:
                # Checked to us: check 70% of time
                if random.random() < 0.7:
                    if valid_actions[1] == 1:
                        return 1
                else:
                    # Small bet occasionally
                    if valid_actions[3] == 1:
                        return 3
                    if valid_actions[1] == 1:
                        return 1

        # Top Pair: Check-call
        elif strength == 'top_pair':
            if to_call > 0:
                if to_call <= pot * 0.75:
                    if valid_actions[2] == 1:
                        return 2
                return 0
            else:
                if valid_actions[1] == 1:
                    return 1

        # Draws: Check-call, rarely raise
        elif strength == 'draw':
            if to_call > 0:
                if to_call <= pot * 0.6:
                    if valid_actions[2] == 1:
                        return 2
                return 0
            else:
                if valid_actions[1] == 1:
                    return 1

        # Air: Check-fold
        else:
            if to_call > 0:
                return 0
            if valid_actions[1] == 1:
                return 1

        return 0

    def _turn_strategy(self, valid_actions, hand, community, to_call, pot):
        """Turn: Aggressive with strong hands - check-raise or bet large."""
        strength = self._get_postflop_strength(hand, community)

        # Strong hands (Two Pair+): Explode with aggression
        if strength == 'monster':
            if to_call > 0:
                # Check-raise large (75%+ pot)
                if valid_actions[5] == 1:  # Pot-sized raise
                    return 5
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[6] == 1:
                    return 6
                if valid_actions[2] == 1:
                    return 2
            else:
                # Bet large (75%+ pot)
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[5] == 1:
                    return 5
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[1] == 1:
                    return 1

        # Top Pair: Check-call small, fold to overbets
        elif strength == 'top_pair':
            if to_call > 0:
                if to_call <= pot * 0.5:
                    if valid_actions[2] == 1:
                        return 2
                # Fold to overbets
                return 0
            else:
                if valid_actions[1] == 1:
                    return 1

        # Draws: Call if pot odds reasonable
        elif strength == 'draw':
            if to_call > 0:
                if to_call <= pot * 0.6:
                    if valid_actions[2] == 1:
                        return 2
                return 0
            else:
                if valid_actions[1] == 1:
                    return 1

        # Marginal/Air: Check-fold
        else:
            if to_call > 0:
                return 0
            if valid_actions[1] == 1:
                return 1

        return 0

    def _river_strategy(self, valid_actions, hand, community, to_call, pot):
        """River: Very aggressive with strong hands - overbet occasionally."""
        strength = self._get_postflop_strength(hand, community)

        # Strong hands: Overbet or raise large
        if strength == 'monster':
            if to_call > 0:
                # Always raise large if facing bet
                if valid_actions[5] == 1:
                    return 5
                if valid_actions[6] == 1:
                    return 6
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[2] == 1:
                    return 2
            else:
                # Overbet occasionally (via all-in or large bet)
                if random.random() < 0.3:  # 30% overbet
                    if valid_actions[6] == 1:
                        return 6

                # Otherwise bet large
                if valid_actions[5] == 1:
                    return 5
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[1] == 1:
                    return 1

        # Top Pair: Check-call small, fold to big
        elif strength == 'top_pair':
            if to_call > 0:
                if to_call <= pot * 0.4:
                    if valid_actions[2] == 1:
                        return 2
                return 0
            else:
                if valid_actions[1] == 1:
                    return 1

        # Marginal/Draw/Air: Check-fold
        else:
            if to_call > 0:
                return 0
            if valid_actions[1] == 1:
                return 1

        return 0

