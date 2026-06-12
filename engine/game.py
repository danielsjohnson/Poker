from engine.deck import *
from engine.card import *
from engine.player import Player
from engine.player import humanPlayer
from engine.player import aiPlayer
from engine.table import Table
from engine.hand_detection import Hand_Detection
from engine.metrics import MetricsTracker


class Game():
    def __init__(self, table, tracker: MetricsTracker = None):
        self.deck = Deck()
        self.judge = Hand_Detection()
        self.players = []
        self.active = []
        self.button = 0
        self.smallBlind_Bet = 10
        self.bigBlind_Bet = 20
        self.current_player_index = 0
        self.current_player: "Player" = None
        self.last_raiser: "Player" = None
        self.turns_taken = 0
        self.table: "Table" = table
        self.last_raise_amount = 0
        self.street = 0
        self.tracker = tracker
        self.hand_over = False
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.suits = ['H', 'S', 'D', 'C']
        self.hand_rankings = [
            "HighCard", 
            "Pair", 
            "Two Pair", 
            "Trips", 
            "Straight", 
            "Flush", 
            "Full House", 
            "Quads",          
            "StraightFlush",
            "RoyalFlush"   
        ]

    def get_valid_actions(self):
        player = self.active[self.current_player_index]
        opponent = self.players[1 - self.current_player_index]
        amount_to_call = self.table.current_bet - player.bet_in_round

        valid = [0] * 7

        if player.chips <= 0:
            valid[1] = 1 
            return valid
        
        if opponent.chips <= 0:
            if amount_to_call == 0:
                valid[0] = 0 
                valid[1] = 1 
            else:
                valid[0] = 1 
                valid[2] = 1 
            return valid
        
        if amount_to_call == 0:
             valid[0] = 0  
             valid[1] = 1  
        else:
             valid[0] = 1 
             valid[2] = 1  

        if player.chips > amount_to_call:
             valid[3] = 1
             valid[4] = 1
             valid[5] = 1
        
        if player.chips > 0:
            valid[6] = 1
            
        return valid
    
    def render(self):
        street_names = {0: "Pre-Flop", 1: "Flop", 2: "Turn", 3: "River"}
        street_name = street_names.get(self.street, "Unknown")

        community_str = " ".join([str(c) for c in self.table.community])
        print(f"STREET: {street_name} | POT: {self.table.pot} | BET: {self.table.current_bet}")
        print(f"BOARD:  [{community_str}]")
        self.table.display()

        for player in self.players:
            if self.isButton(player):
                button = "D"
            else:
                button = " "

            status = ""
            if player.all_in: status = "(ALL-IN)"
            
            
            print(f"{button}: {player.name}, {player.chips} chips, {status}")
            player.displayHand()

    def reset(self):
        for player in self.players:
            if player.chips <= 0:
                player.chips = 1000
        
        self.resetPlayers()
        self.resetGame()
        self.table.reset()
        self.deck = Deck()
        self.deck.shuffle()
        
        for player in self.players:
            player.total_bet = 0
            player.bet_in_round = 0
            player.final_hand = None
            player.clear_hand()
            player.all_in = False

        if self.tracker:
            self.tracker.on_hand_start(self.players)
            
        self.postBlinds()
        self.preflop()
        self.last_raiser = self.bigBlind()
        
        return self.get_state()
    
    def postBlinds(self):
        sb = self.smallBlind()
        sbet = min(sb.chips, self.smallBlind_Bet)
        sb.updateChips(-sbet)
        self.table.updatePot(sbet)
        sb.bet_in_round = sbet
        self.isAllIn(sb)
        
        bb = self.bigBlind()
        bbet = min(bb.chips, self.bigBlind_Bet)
        bb.updateChips(-bbet)
        self.table.updatePot(bbet)
        bb.bet_in_round = bbet
        self.isAllIn(bb)

        self.table.current_bet = max(sbet, bbet)

    def isAllIn(self, player):
        if player.chips == 0:
            player.all_in = True
    
    def resetPlayers(self):
        self.active = self.players[:]
    
    def resetGame(self):
        self.current_player_index = 0
        self.hand_over = False
        self.current_player = None
        self.last_raiser = None
        self.turns_taken = 0
        self.last_raise_amount = 0
        self.incrementButton()

    def preflop(self):
        self.street = 0
        for player in self.active:
            player.receiveCard(self.deck.deal(2))

    def flop(self):
        self.street = 1
        if len(self.active) == 1:
            self.end_game()
            return
        self.endRound()
        self.table.receive(self.deck.deal(3))

    def turn(self):
        self.street = 2
        if len(self.active) == 1:
            self.end_game()
            return
        self.endRound()
        self.table.receive(self.deck.deal(1))

    def river(self):
        self.street = 3
        if len(self.active) == 1:
            self.end_game()
            return
        self.endRound()
        self.table.receive(self.deck.deal(1))

    def step(self, action):
        player = self.active[self.current_player_index]
        
        prev_chips = player.chips
        
        self.execute_action(action)
        self.incrementTurn()

        if self.check_endRound():
            self.advance_street()
        
        done = False
        if len(self.active) == 1 or self.street > 3:
            self.end_game()
            done = True
        
        current_chips = player.chips
        reward = (current_chips - prev_chips) / 100.0
        
        return self.get_state(), reward, done        

    def get_state(self):
        hero = self.active[self.current_player_index]
        villain_index = (self.current_player_index + 1) % len(self.active)
        villain = self.active[villain_index]
        MAX_CHIPS = 1000.0 

        state = []


        for card in hero.hand:
            state.append(self.ranks.index(card.rank) / 12.0)
            suit_encoding = [0, 0, 0, 0]
            suit_encoding[self.suits.index(card.suit)] = 1
            state.extend(suit_encoding)



        for i in range(5):
            if i < len(self.table.community):
                card = self.table.community[i]
                state.append(self.ranks.index(card.rank) / 12.0)
                suit_encoding = [0, 0, 0, 0]
                suit_encoding[self.suits.index(card.suit)] = 1
                state.extend(suit_encoding)
            else:
                state.extend([-1.0, 0, 0, 0, 0])

        state.append(hero.chips / MAX_CHIPS)
        state.append(villain.chips / MAX_CHIPS)
        state.append(self.table.pot / MAX_CHIPS)
        state.append(self.table.current_bet / MAX_CHIPS)
        state.append(self.street / 4.0)
        
        state.append(self.isButton(hero)) 
        state.append(hero.bet_in_round / MAX_CHIPS)
        state.append(villain.bet_in_round / MAX_CHIPS)
        amount_to_call = self.table.current_bet - hero.bet_in_round
        state.append(amount_to_call / MAX_CHIPS)

        return state

    def showdown(self):
        judge = Hand_Detection()
        for player in self.active:
            hand = judge.find_hand(player.hand, self.table.community)
            player.final_hand = []
            player.final_hand.append(self.hand_rankings.index(hand[0]))
            for i in range(1, len(hand)):
                try:
                    val = self.ranks.index(hand[i].rank)
                except:
                    val = self.ranks.index(hand[i])
                player.final_hand.append(val)
            player.final_hand = tuple(player.final_hand)

    def end_game(self):
        if self.hand_over == True:
            return
        self.hand_over = True
        if len(self.active) == 1:
            winner = self.active[0]
            winner.updateChips(self.table.pot)
            self.table.pot = 0
            if self.tracker:
                self.tracker.on_hand_end(self.players)
            return
        
        self.showdown()
        
        best_hand = (-1,)
        winners = []

        for player in self.active:
            if player.final_hand > best_hand:
                best_hand = player.final_hand
                winners = [player]
            elif player.final_hand == best_hand:
                winners.append(player)
        
        if len(winners) == 1:
            winner = winners[0]
            loser = self.players[0] if self.players[0] is not winner else self.players[1]
            
            c_winner = winner.total_bet + winner.bet_in_round
            c_loser = loser.total_bet + loser.bet_in_round
            
            win_amount = c_winner + min(c_winner, c_loser)
            return_amount = max(0, c_loser - c_winner)
            
            winner.updateChips(win_amount)
            if return_amount > 0:
                loser.updateChips(return_amount)
        elif len(winners) == 2:
            for player in self.players:
                c_player = player.total_bet + player.bet_in_round
                player.updateChips(c_player)
        
        self.table.pot = 0
        if self.tracker:
            self.tracker.on_hand_end(self.players)

    def incrementButton(self):
        self.button = ((self.button + 1 ) % len(self.players))
    
    def folded(self, other):
        if other in self.active:
            self.active.remove(other)
        if self.current_player_index >= len(self.active):
            self.current_player_index = 0
    
    def UTG(self): 
        return self.players[(self.button + 3) % len(self.players)]
    
    def bigBlind(self): 
        return self.players[(self.button + 2) % len(self.players)]
    
    def smallBlind(self): 
        return self.players[(self.button + 1) % len(self.players)]
    
    def UTG_index(self): 
        return (self.button + 3) % len(self.players)
    
    def bigBlind_index(self): 
        return (self.button + 2) % len(self.players)
    
    def smallBlind_index(self): 
        return (self.button + 1) % len(self.players)
    
    
    def check_endRound(self):
        active_player = self.active[self.current_player_index]
        
        if active_player != self.last_raiser: 
            return False
            
        for player in self.active:
            if active_player.bet_in_round != player.bet_in_round:
                if player.all_in: continue
                return False
                
        return True

    def endRound(self):
        for player in self.active:
            player.total_bet += player.bet_in_round
            player.bet_in_round = 0
        
        self.table.current_bet = 0
        self.last_raise_amount = 0

        if self.players and self.active:
            self.last_raiser = self.players[self.button]

 
    def incrementTurn(self):
        if len(self.active) == 0: return
        self.current_player_index = (self.current_player_index + 1) % len(self.active)

    def isButton(self, player):
        if self.players.index(player) == self.button: return 1.0
        return 0.0
    
    def advance_street(self):
        self.street += 1
        if self.street == 1: self.flop()
        elif self.street == 2: self.turn()
        elif self.street == 3: self.river()
        
        if len(self.active) >= 2 and self.street <= 3 and sum(1 for p in self.active if p.chips > 0) <= 1:
            self.advance_street()
    
    def execute_action(self, action):
        player = self.active[self.current_player_index]
        amount_to_call = self.table.current_bet - player.bet_in_round
        if self.tracker:
            self.tracker.on_action(player.name, self.street, action, amount_to_call)

        if action == 0:
            self.folded(player)
        
        elif action == 1 and amount_to_call > 0:
            self.folded(player)
        
        elif action == 2:
            bet = min(player.chips, amount_to_call)
            player.updateChips(-bet)
            player.bet_in_round += bet
            self.table.updatePot(bet)
            self.isAllIn(player)

        elif action in [3, 4, 5]:
            if action == 3: multiplier = 0.5
            elif action == 4: multiplier = 0.75
            else: multiplier = 1.0
            
            raise_amount = int(self.table.pot * multiplier)
            raise_amount = max(raise_amount, self.last_raise_amount)
            total_cost = raise_amount + amount_to_call
            
            if total_cost >= player.chips:
                total_cost = player.chips 
                player.all_in = True
                actual_raise = total_cost - amount_to_call
                if actual_raise > 0:
                    self.last_raise_amount = actual_raise
                    self.last_raiser = player
                    self.table.current_bet = player.bet_in_round + total_cost
            else:
                self.last_raise_amount = raise_amount
                self.last_raiser = player
                self.table.current_bet = player.bet_in_round + total_cost

            player.updateChips(-total_cost)
            player.bet_in_round += total_cost
            self.table.updatePot(total_cost)

        elif action == 6:
            bet = player.chips
            player.updateChips(-bet)
            player.bet_in_round += bet
            self.table.updatePot(bet)
            player.all_in = True
            if player.bet_in_round > self.table.current_bet:
                self.last_raise_amount = player.bet_in_round - self.table.current_bet
                self.last_raiser = player
                self.table.current_bet = player.bet_in_round
