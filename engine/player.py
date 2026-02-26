#player
from engine.card import *
from engine.deck import *
from engine.table import *
from engine.hand_detection import *

class Player():
    def __init__(self, name, table):
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.hand = [] 
        self.table = table
        self.name = name
        self.chips = 0
        self.bet = 0
        self.bet_in_round = 0
        self.total_hand = []
        self.final_hand = None
        self.all_in = False
        self.total_bet = 0


    def receiveCard(self, cards):
        for card in cards:
            self.hand.append(card)
            
    def displayHand(self):
        print(f"{self.name}'s cards:")
        for card in self.hand:
            card.display()

    def displayChips(self):
        print(self.chips)

    def updateChips(self, change):
        self.chips += change
    
    def clear_hand(self):
        self.hand = []
        self.total_hand = []
    
    




class humanPlayer(Player):
    def get_action(self, valid_actions, amount_to_call = 0, pot = 0):
        print(f"--- {self.name}'s Turn ---")
        print(f"Chips: {self.chips} | Pot: {pot} | To Call: {amount_to_call}")
        self.displayHand()
        print()
        self.table.display()
        print("\nYour options are:")
        for i, action in enumerate(valid_actions):
            print(f"{i+1}. {action}")
        
        while True:
            try:
                choice_index = int(input("Enter choice number: ")) - 1
                if 0 <= choice_index < len(valid_actions):
                    return valid_actions[choice_index]
                else: 
                    print("Invalid choice.")
            except ValueError:
                print("Enter a valid number.")
                
    def get_bet_amount(self,min_amount, max_amount):
        while True:
            try:
                prompt = f"Enter amount (min: {min_amount}, max: {max_amount}):"
                amount = int(input(prompt))
                if min_amount<= amount <= max_amount:
                    return amount
                else:
                    print("Not in the valid range.")
            except ValueError:
                print("Please enter a valid number.")


class aiPlayer(Player):
    def get_action(self):
        raise NotImplementedError