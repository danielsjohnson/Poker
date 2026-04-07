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
        if not hand or len(hand) < 2:
            return 'trash'

        r1 = str(hand[0].rank)
        r2 = str(hand[1].rank)
        v1 = self.rank_map.get(r1, 0)
        v2 = self.rank_map.get(r2, 0)
        suited = hand[0].suit == hand[1].suit

        high, low = max(v1, v2), min(v1, v2)

        if high == low and high >= 12:  # QQ+
            return 'premium'
        if high == 14 and low == 13:  # AK
            return 'premium'
        if high == low and 9 <= high <= 11:  # 99-JJ
            return 'strong'
        if high == 14 and low >= 11:  # AJ, AQ
            return 'strong'
        if high == 13 and low == 12:  # KQ
            return 'strong'
        if high == low:
            return 'playable'
        if suited and (high - low <= 2):
            return 'playable'
        if suited and high >= 10 and low >= 10:
            return 'playable'

        return 'trash'

    def _get_postflop_strength(self, hand, community):
        if not community:
            return 'air'

        hand_result = self.hand_detector.find_hand(hand, community)
        hand_type = hand_result[0]

        if hand_type in ['Two Pair', 'Trips', 'Straight', 'Flush', 'Full House', 'Quads', 'StraightFlush', 'RoyalFlush']:
            return 'monster'

        if hand_type == 'Pair':
            pair_rank = hand_result[1]
            pair_value = self.rank_map.get(pair_rank, 0)
            board_ranks = [self.rank_map.get(str(c.rank), 0) for c in community]
            top_board_card = max(board_ranks)

            if pair_value == top_board_card:
                return 'top_pair'
            elif pair_value >= 11:
                return 'top_pair'
            else:
                return 'air'

        if self._has_draw(hand, community):
            return 'draw'

        return 'air'

    def _has_draw(self, hand, community):
        total_cards = hand + community
        suits = {}
        for card in total_cards:
            suits[card.suit] = suits.get(card.suit, 0) + 1
        if any(count >= 4 for count in suits.values()):
            return True

        ranks = sorted(set([self.rank_map.get(str(c.rank), 0) for c in total_cards]))
        for i in range(len(ranks) - 3):
            window = ranks[i:i+4]
            if window[-1] - window[0] <= 4:
                return True
        return False

    def _get_kicker_strength(self, hand, community):
        hand_ranks = [self.rank_map.get(str(c.rank), 0) for c in hand]
        return max(hand_ranks)

    def select_action(self, valid_actions, hand, community, to_call, pot, street, villain_bet):
        if street == 0:
            return self._preflop_strategy(valid_actions, hand, to_call, villain_bet)
        else:
            return self._postflop_strategy(valid_actions, hand, community, to_call, pot, street, villain_bet)

    def _preflop_strategy(self, valid_actions, hand, to_call, villain_bet):
        tier = self._get_hand_tier(hand)

        if tier == 'premium':
            if to_call > 0:
                if valid_actions[6] == 1: return 6
                if valid_actions[5] == 1: return 5
                if valid_actions[4] == 1: return 4
                if valid_actions[2] == 1: return 2
                return 0 # Fallback
            else:
                if valid_actions[5] == 1: return 5
                if valid_actions[4] == 1: return 4
                if valid_actions[3] == 1: return 3
                if valid_actions[1] == 1: return 1
                return 0 # Fallback

        elif tier == 'strong':
            if to_call > 0:
                if villain_bet > 100:
                    is_pair = hand[0].rank == hand[1].rank
                    pair_value = self.rank_map.get(str(hand[0].rank), 0) if is_pair else 0

                    if is_pair and pair_value >= 11:
                        if random.random() < 0.5:
                            if valid_actions[5] == 1: return 5
                            if valid_actions[6] == 1: return 6
                        if valid_actions[2] == 1: return 2
                        return 0 # Fallback
                    else:
                        return 0
                else:
                    if random.random() < 0.5:
                        if valid_actions[4] == 1: return 4
                        if valid_actions[3] == 1: return 3
                    if valid_actions[2] == 1: return 2
                    return 0 # Fallback
            else:
                if valid_actions[4] == 1: return 4
                if valid_actions[3] == 1: return 3
                if valid_actions[1] == 1: return 1
                return 0 # Fallback

        elif tier == 'playable':
            if to_call > 0:
                if to_call <= 40:
                    if valid_actions[2] == 1: return 2
                return 0
            else:
                if valid_actions[1] == 1: return 1
                return 0 # Fallback

        if valid_actions[1] == 1 and to_call == 0: return 1
        return 0

    def _postflop_strategy(self, valid_actions, hand, community, to_call, pot, street, villain_bet):
        strength = self._get_postflop_strength(hand, community)

        if strength == 'monster':
            if to_call > 0:
                if valid_actions[5] == 1: return 5
                if valid_actions[4] == 1: return 4
                if valid_actions[6] == 1: return 6
                if valid_actions[2] == 1: return 2
                return 0 # Fallback
            else:
                if valid_actions[5] == 1: return 5
                if valid_actions[4] == 1: return 4
                if valid_actions[3] == 1: return 3
                if valid_actions[1] == 1: return 1
                return 0 # Fallback

        elif strength == 'top_pair':
            kicker = self._get_kicker_strength(hand, community)
            if to_call > 0:
                if to_call < pot * 0.5:
                    if valid_actions[4] == 1: return 4
                    if valid_actions[3] == 1: return 3
                    if valid_actions[2] == 1: return 2
                    return 0 # Fallback
                elif to_call < pot:
                    if kicker >= 11:
                        if valid_actions[2] == 1: return 2
                    return 0 # Fallback
                else:
                    if kicker >= 13:
                        if valid_actions[2] == 1: return 2
                    return 0 # Fallback
            else:
                if valid_actions[4] == 1: return 4
                if valid_actions[3] == 1: return 3
                if valid_actions[1] == 1: return 1
                return 0 # Fallback

        elif strength == 'draw':
            if to_call > 0:
                if random.random() < 0.4:
                    if valid_actions[4] == 1: return 4
                    if valid_actions[3] == 1: return 3
                if to_call <= pot * 0.75:
                    if valid_actions[2] == 1: return 2
                return 0 # Fallback
            else:
                if random.random() < 0.5:
                    if valid_actions[3] == 1: return 3
                if valid_actions[1] == 1: return 1
                return 0 # Fallback

        else:
            if to_call > 0:
                return 0
            else:
                if random.random() < 0.15:
                    if valid_actions[3] == 1: return 3
                if valid_actions[1] == 1: return 1
                return 0 # Fallback

        return 0 # Final bulletproof fallback