"""
Pressure Bot v1 - Reverse Aggression Stress Test

Purpose: Teach agent how to handle aggression, bluff-catching discipline,
stack defense, and not over-folding.

Strategy: Opens wide preflop, continuation bets frequently, applies multi-street
aggression with occasional bluffs. Forces agent to learn when to fight back.
"""

import random
from engine.hand_detection import Hand_Detection


class PressureBot:
    def __init__(self):
        self.rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        self.hand_detector = Hand_Detection()
        self.c_bet_frequency = 0.7  # 70% c-bet
        self.double_barrel_freq = 0.5  # 50% turn barrel
        self.triple_barrel_freq = 0.25  # 25% river barrel

    def _is_playable_preflop(self, hand):
        """Wide opening range: 40-60% of hands."""
        if not hand or len(hand) < 2:
            return False

        r1 = str(hand[0].rank)
        r2 = str(hand[1].rank)
        v1 = self.rank_map.get(r1, 0)
        v2 = self.rank_map.get(r2, 0)
        suited = hand[0].suit == hand[1].suit

        high, low = max(v1, v2), min(v1, v2)

        # Any pair
        if high == low:
            return True

        # Any ace
        if high == 14:
            return True

        # High cards (10+)
        if low >= 10:
            return True

        # Suited connectors and one-gappers
        if suited and (high - low <= 2):
            return True

        # King-high
        if high == 13 and low >= 8:
            return True

        # Random hands to reach 50% range
        if random.random() < 0.3:
            return True

        return False

    def _is_strong_preflop(self, hand):
        """Premium hands for aggressive play."""
        if not hand or len(hand) < 2:
            return False

        r1 = str(hand[0].rank)
        r2 = str(hand[1].rank)
        v1 = self.rank_map.get(r1, 0)
        v2 = self.rank_map.get(r2, 0)

        # Pairs 77+
        if v1 == v2 and v1 >= 7:
            return True

        # AJ+, KQ
        high, low = max(v1, v2), min(v1, v2)
        if high == 14 and low >= 11:
            return True
        if high == 13 and low >= 12:
            return True

        return False

    def _get_postflop_strength(self, hand, community):
        """
        Evaluate postflop hand strength.
        Returns: 'strong', 'medium', 'weak'
        """
        if not community:
            return 'weak'

        hand_result = self.hand_detector.find_hand(hand, community)
        hand_type = hand_result[0]

        # Strong: Two Pair or better
        if hand_type in ['Two Pair', 'Trips', 'Straight', 'Flush', 'Full House', 'Quads', 'StraightFlush', 'RoyalFlush']:
            return 'strong'

        # Medium: Pair or strong draw
        if hand_type == 'Pair':
            return 'medium'

        if self._has_draw(hand, community):
            return 'medium'

        return 'weak'

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

    def select_action(self, valid_actions, hand, community, to_call, pot, street, villain_bet, was_preflop_aggressor=False):
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

        # Pre-flop: wide and aggressive
        if street == 0:
            return self._preflop_strategy(valid_actions, hand, to_call)

        # Post-flop: frequent c-betting and multi-street aggression
        else:
            return self._postflop_strategy(valid_actions, hand, community, to_call, pot, street, villain_bet)

    def _preflop_strategy(self, valid_actions, hand, to_call):
        """Pre-flop: Open wide, 3-bet medium frequency, occasional 4-bet bluff."""
        is_playable = self._is_playable_preflop(hand)
        is_strong = self._is_strong_preflop(hand)

        if to_call > 0:
            # Facing aggression
            if is_strong:
                # 3-bet or call with strong hands
                if random.random() < 0.6:  # 60% 3-bet
                    if valid_actions[4] == 1:
                        return 4
                    if valid_actions[3] == 1:
                        return 3

                if valid_actions[2] == 1:
                    return 2

            elif is_playable:
                # Call with playable hands if price is right
                if to_call <= 40:
                    if valid_actions[2] == 1:
                        return 2

                # Occasional 3-bet bluff (10%)
                if random.random() < 0.1:
                    if valid_actions[3] == 1:
                        return 3

            # Fold weak hands
            return 0

        else:
            # Unopened pot
            if is_playable:
                # Open raise with playable hands
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[4] == 1:
                    return 4

            # Otherwise check
            if valid_actions[1] == 1:
                return 1
            return 0

    def _postflop_strategy(self, valid_actions, hand, community, to_call, pot, street, villain_bet):
        """Post-flop: Frequent c-betting, multi-street aggression."""
        strength = self._get_postflop_strength(hand, community)

        # If facing aggression
        if to_call > 0:
            return self._facing_bet(valid_actions, strength, to_call, pot)

        # If checked to us (aggression opportunity)
        else:
            return self._checked_to_us(valid_actions, strength, pot, street)

    def _facing_bet(self, valid_actions, strength, to_call, pot):
        """Defend against aggression based on hand strength."""

        # Strong hands: Raise immediately
        if strength == 'strong':
            if valid_actions[4] == 1:
                return 4
            if valid_actions[5] == 1:
                return 5
            if valid_actions[3] == 1:
                return 3
            if valid_actions[2] == 1:
                return 2

        # Medium hands: Call or raise occasionally
        elif strength == 'medium':
            # Raise with draws/pairs 30% of time (semi-bluff)
            if random.random() < 0.3:
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[4] == 1:
                    return 4

            # Call reasonable bets
            if to_call <= pot * 0.75:
                if valid_actions[2] == 1:
                    return 2

            # Fold to large bets
            return 0

        # Weak hands: Fold to pressure, but don't over-fold
        else:
            # Bluff-raise occasionally (10%) to keep opponent honest
            if random.random() < 0.1 and to_call <= pot * 0.5:
                if valid_actions[3] == 1:
                    return 3

            # Bluff-call occasionally (15%) vs small bets
            if random.random() < 0.15 and to_call <= pot * 0.3:
                if valid_actions[2] == 1:
                    return 2

            # Usually fold
            return 0

    def _checked_to_us(self, valid_actions, strength, pot, street):
        """Apply pressure when checked to."""

        # Strong hands: Always bet large
        if strength == 'strong':
            if valid_actions[4] == 1:
                return 4
            if valid_actions[5] == 1:
                return 5
            if valid_actions[3] == 1:
                return 3
            if valid_actions[1] == 1:
                return 1

        # Medium hands: Bet with draws and pairs
        elif strength == 'medium':
            # Bet 80% of time
            if random.random() < 0.8:
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[4] == 1:
                    return 4

            if valid_actions[1] == 1:
                return 1

        # Weak hands: C-bet frequency based on street
        else:
            bet_freq = self.c_bet_frequency if street == 1 else \
                      self.double_barrel_freq if street == 2 else \
                      self.triple_barrel_freq

            if random.random() < bet_freq:
                # Small bet (30-50% pot) for bluffs
                if valid_actions[3] == 1:
                    return 3

            if valid_actions[1] == 1:
                return 1

        return 0 if valid_actions[0] == 1 else 1

