"""
Punisher Bot v1 - Immediate Aggression Enforcement

Purpose: Punish over-bluffing, auto c-betting, blind all-ins, and overbet spew.
Forces the agent to learn equity gating, selective aggression, and stack awareness.

Strategy: Tight-aggressive with no slowplay. Applies strong pressure with value hands
and aggressively defends against bluffs.
"""

import random
from engine.hand_detection import Hand_Detection


class PunisherBot:
    def __init__(self):
        self.rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        self.hand_detector = Hand_Detection()

    def _get_hand_tier(self, hand):
        """
        Classify preflop hand into tiers.
        Returns: 'premium', 'strong', 'playable', or 'trash'
        """
        if not hand or len(hand) < 2:
            return 'trash'

        r1 = str(hand[0].rank)
        r2 = str(hand[1].rank)
        v1 = self.rank_map.get(r1, 0)
        v2 = self.rank_map.get(r2, 0)
        suited = hand[0].suit == hand[1].suit

        # Sort for easier comparison
        high, low = max(v1, v2), min(v1, v2)

        # Tier A: Premiums (AA-QQ, AK)
        if high == low and high >= 12:  # QQ+
            return 'premium'
        if high == 14 and low == 13:  # AK
            return 'premium'

        # Tier B: Strong (JJ-99, AQ, AJ, KQ)
        if high == low and 9 <= high <= 11:  # 99-JJ
            return 'strong'
        if high == 14 and low >= 11:  # AJ, AQ (AK already covered)
            return 'strong'
        if high == 13 and low == 12:  # KQ
            return 'strong'

        # Tier C: Playable (suited connectors, small pairs, suited broadways)
        if high == low:  # Small pairs
            return 'playable'
        if suited and (high - low <= 2):  # Suited connectors/gappers
            return 'playable'
        if suited and high >= 10 and low >= 10:  # Suited broadways
            return 'playable'

        return 'trash'

    def _get_postflop_strength(self, hand, community):
        """
        Evaluate postflop hand strength.
        Returns: 'monster', 'top_pair', 'draw', 'air'
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
            elif pair_value >= 11:  # JJ+ as overpair
                return 'top_pair'
            else:
                return 'air'

        # Check for draws
        if self._has_draw(hand, community):
            return 'draw'

        return 'air'

    def _has_draw(self, hand, community):
        """Check if hand has flush draw or straight draw."""
        total_cards = hand + community

        # Check flush draw (4 of same suit)
        suits = {}
        for card in total_cards:
            suits[card.suit] = suits.get(card.suit, 0) + 1
        if any(count >= 4 for count in suits.values()):
            return True

        # Simplified straight draw check
        ranks = sorted(set([self.rank_map.get(str(c.rank), 0) for c in total_cards]))
        for i in range(len(ranks) - 3):
            window = ranks[i:i+4]
            if window[-1] - window[0] <= 4:  # 4 cards within 5 ranks
                return True

        return False

    def _get_kicker_strength(self, hand, community):
        """Evaluate kicker quality for top pair."""
        hand_ranks = [self.rank_map.get(str(c.rank), 0) for c in hand]
        return max(hand_ranks)

    def select_action(self, valid_actions, hand, community, to_call, pot, street, villain_bet):
        """
        Main decision function.

        Action mapping:
        0: Fold
        1: Check (if to_call=0) / Fold (if to_call>0)
        2: Call
        3: Raise 50% pot
        4: Raise 75% pot
        5: Raise 100% pot
        6: All-In
        """

        # Pre-flop strategy
        if street == 0:
            return self._preflop_strategy(valid_actions, hand, to_call, villain_bet)

        # Post-flop strategy
        else:
            return self._postflop_strategy(valid_actions, hand, community, to_call, pot, street, villain_bet)

    def _preflop_strategy(self, valid_actions, hand, to_call, villain_bet):
        """Pre-flop decision logic."""
        tier = self._get_hand_tier(hand)

        # Tier A: Premiums (AA-QQ, AK)
        if tier == 'premium':
            if to_call > 0:
                # Facing aggression: 4-bet jam
                if valid_actions[6] == 1:
                    return 6
                # Or raise large
                if valid_actions[5] == 1:
                    return 5
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[2] == 1:
                    return 2
            else:
                # Unopened: Always raise
                if valid_actions[5] == 1:
                    return 5
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[1] == 1:
                    return 1

        # Tier B: Strong (JJ-99, AQ, AJ, KQ)
        elif tier == 'strong':
            if to_call > 0:
                # Facing aggression: 50% 3-bet, 50% call
                if villain_bet > 100:  # Facing large bet: mostly fold unless JJ+
                    is_pair = hand[0].rank == hand[1].rank
                    pair_value = self.rank_map.get(str(hand[0].rank), 0) if is_pair else 0

                    if is_pair and pair_value >= 11:  # JJ+
                        if random.random() < 0.5:
                            if valid_actions[5] == 1:
                                return 5
                            if valid_actions[6] == 1:
                                return 6
                        if valid_actions[2] == 1:
                            return 2
                    else:
                        return 0  # Fold non-pairs to large bets

                # Normal bet: 3-bet 50% or call
                if random.random() < 0.5:
                    if valid_actions[4] == 1:
                        return 4
                    if valid_actions[3] == 1:
                        return 3
                if valid_actions[2] == 1:
                    return 2
            else:
                # Unopened: raise
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[1] == 1:
                    return 1

        # Tier C: Playable
        elif tier == 'playable':
            if to_call > 0:
                # Defend vs small raises only
                if to_call <= 40:  # Small raise
                    if valid_actions[2] == 1:
                        return 2
                return 0  # Fold to large raises
            else:
                # Check or limp
                if valid_actions[1] == 1:
                    return 1

        # Trash
        return 0

    def _postflop_strategy(self, valid_actions, hand, community, to_call, pot, street, villain_bet):
        """Post-flop decision logic."""
        strength = self._get_postflop_strength(hand, community)

        # MONSTER (Two Pair+): Ultra aggressive, no slowplay
        if strength == 'monster':
            if to_call > 0:
                # Facing bet: raise immediately
                if valid_actions[5] == 1:  # Raise pot
                    return 5
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[6] == 1:  # All-in if can't raise
                    return 6
                if valid_actions[2] == 1:
                    return 2
            else:
                # Checked to us: bet large (75-100% pot)
                if valid_actions[5] == 1:
                    return 5
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[1] == 1:
                    return 1

        # TOP PAIR: Aggressive but cautious of overbets
        elif strength == 'top_pair':
            kicker = self._get_kicker_strength(hand, community)

            if to_call > 0:
                # Facing small bet: raise
                if to_call < pot * 0.5:
                    if valid_actions[4] == 1:
                        return 4
                    if valid_actions[3] == 1:
                        return 3
                    if valid_actions[2] == 1:
                        return 2

                # Facing medium bet: call if good kicker
                elif to_call < pot:
                    if kicker >= 11:  # J+ kicker
                        if valid_actions[2] == 1:
                            return 2
                    else:
                        # Weak kicker: fold to pressure
                        return 0

                # Facing overbet: fold unless strong kicker
                else:
                    if kicker >= 13:  # K+ kicker
                        if valid_actions[2] == 1:
                            return 2
                    return 0
            else:
                # Checked to us: bet
                if valid_actions[4] == 1:
                    return 4
                if valid_actions[3] == 1:
                    return 3
                if valid_actions[1] == 1:
                    return 1

        # DRAW: Semi-bluff aggressively
        elif strength == 'draw':
            if to_call > 0:
                # Raise 40% of the time
                if random.random() < 0.4:
                    if valid_actions[4] == 1:
                        return 4
                    if valid_actions[3] == 1:
                        return 3

                # Call reasonable bets
                if to_call <= pot * 0.75:
                    if valid_actions[2] == 1:
                        return 2

                # Fold to extreme pressure
                return 0
            else:
                # Checked to us: bet 50% of time
                if random.random() < 0.5:
                    if valid_actions[3] == 1:
                        return 3
                if valid_actions[1] == 1:
                    return 1

        # AIR: Occasional bluff, mostly fold
        else:
            if to_call > 0:
                # Fold to any bet
                return 0
            else:
                # Bluff 15% of time with small bet
                if random.random() < 0.15:
                    if valid_actions[3] == 1:
                        return 3
                if valid_actions[1] == 1:
                    return 1

        # Fallback
        if valid_actions[1] == 1:
            return 1
        return 0

