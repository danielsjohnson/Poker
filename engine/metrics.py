from dataclasses import dataclass
from typing import Dict, List

@dataclass
class PlayerStats:
    hands: int = 0
    net_bb: float = 0.0

    vpip_hands: int = 0
    pfr_hands: int = 0
    preflop_calls: int = 0
    preflop_raises: int = 0
    preflop_allins: int = 0

    post_calls: int = 0
    post_bets_raises: int = 0

    def vpip_pct(self) -> float:
        return 100.0 * self.vpip_hands / self.hands if self.hands else 0.0

    def pfr_pct(self) -> float:
        return 100.0 * self.pfr_hands / self.hands if self.hands else 0.0

    def bb_per_100(self) -> float:
        return 100.0 * self.net_bb / self.hands if self.hands else 0.0

    def aggression_factor(self) -> float:
        return (self.post_bets_raises / self.post_calls) if self.post_calls else float(self.post_bets_raises)


class MetricsTracker:
    def __init__(self, big_blind: int):
        self.big_blind = big_blind
        self.stats: Dict[str, PlayerStats] = {}
        self._hand_start_chips: Dict[str, int] = {}
        self._hand_flags: Dict[str, Dict[str, bool]] = {}

    def _ps(self, name: str) -> PlayerStats:
        if name not in self.stats:
            self.stats[name] = PlayerStats()
        return self.stats[name]

    def on_hand_start(self, players: List[object]):
        self._hand_start_chips = {p.name: p.chips for p in players}
        self._hand_flags = {p.name: {"vpip": False, "pfr": False} for p in players}
        for p in players:
            self._ps(p.name).hands += 1

    def on_action(self, player_name: str, street: int, action: int, amount_to_call: int):
        ps = self._ps(player_name)

        if street == 0:
            if action in (2, 3, 4, 5, 6):
                if not self._hand_flags[player_name]["vpip"]:
                    self._hand_flags[player_name]["vpip"] = True
                    ps.vpip_hands += 1

            if action in (3, 4, 5, 6):
                if not self._hand_flags[player_name]["pfr"]:
                    self._hand_flags[player_name]["pfr"] = True
                    ps.pfr_hands += 1

            if action == 2:
                ps.preflop_calls += 1
            elif action in (3, 4, 5):
                ps.preflop_raises += 1
            elif action == 6:
                ps.preflop_allins += 1

        if street >= 1:
            if action == 2:
                ps.post_calls += 1
            elif action in (3, 4, 5, 6):
                ps.post_bets_raises += 1

    def on_hand_end(self, players: List[object]):
        for p in players:
            start = self._hand_start_chips.get(p.name, p.chips)
            self._ps(p.name).net_bb += (p.chips - start) / float(self.big_blind)