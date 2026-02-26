from dataclasses import dataclass, field
from typing import Dict, Optional

class PlayerStats:
    hands: int = 0
    net_bb: float = 0.0

    #preflop
    vpip_hands: int = 0 #voluntarily put in pot
    pfr_hands: int = 0 #preflop raise percentage
    preflop_calls: int = 0
    preflop_raises: int = 0
    preflop_allins: int = 0

    #postflop
    post_calls: int = 0
    post_bets_raises: int = 0

    def vpip_pct(self):
        if self.hands:
            return 100.0 * self.vpip_hands / self.hands

        else:
            return 0.0

    def pfr_pct(self):
        if self.hands:
            return 100.0 * self.pfr_hands / self.hands
        else:
            return 0.0
        
    def bb_per_100(self):
        if self.hands:
            return 100.0 *  self.net_bb / self.hands
        else:
            return 0.0
        
    def aggression_factor(self) -> float:
            # AF = (bets+raises) / calls ; if no calls, treat as "infinite" -> just return bets_raises
            if self.post_calls:
                return (self.post_bets_raises / self.post_calls)
            else:
                return float(self.post_bets_raises)
            

class MetricsTracker:
    def __init__(self, big_blind: int, game):
        self.big_blind = big_blind
        self.stats: Dict[str, PlayerStats] = {}
        self._hand_start_chips: Dict[str, int] = {}
        self._hand_flags: Dict[str, Dict[str, bool]] = {} # Track if player has done certain actions in the current hand
        self.game = game
        def _ps(self, name: str) -> PlayerStats:
            if name not in self.stats:
                self.stats[name] = PlayerStats()
            return self.stats[name]
        
    def on_hand_start(self, player_name: str, chips: int):
        self._hand_start_chips = {p.name: p.chips for p in self.game.players}
        self._hand_flags = {p.name: {'vpip': False, 'pfr': False} for p in self.game.players}

    def on_action(self, player_name: str, street: int, action: int, amount_to_call: int):
        ps = self._ps(player_name)
        if street == 0:
            # VPIP if player voluntarily put chips in pot (call/raise/all-in)
            if action in (2, 3, 4, 5, 6):
                if not self._hand_flags[player_name]["vpip"]:
                    self._hand_flags[player_name]["vpip"] = True
                    ps.vpip_hands += 1

            # PFR if player raised (including all-in as raise) at any point preflop
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

        # Postflop aggression (streets 1-3)
        if street >= 1:
            if action == 2:
                ps.post_calls += 1
            elif action in (3, 4, 5, 6):
                ps.post_bets_raises += 1
    
    def on_hand_end(self, players):
        # net bb over the whole hand
        for p in players:
            start = self._hand_start_chips.get(p.name, p.chips)
            delta_chips = p.chips - start
            self._ps(p.name).net_bb += (delta_chips / float(self.big_blind))

    def summary_lines(self):
        lines = []
        for name, ps in self.stats.items():
            lines.append(
                f"{name:>12} | hands={ps.hands:>6} | bb/100={ps.bb_per_100():>7.2f} | "
                f"VPIP={ps.vpip_pct():>5.1f}% | PFR={ps.pfr_pct():>5.1f}% | AF={ps.aggression_factor():>6.2f}"
            )