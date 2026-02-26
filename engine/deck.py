from engine.card import Card
import random

class Deck:
    def __init__(self):
        suits = ['H', 'S', 'D', 'C']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = []
        for suit in suits:
            for rank in ranks:
                card = Card(rank, suit)
                self.deck.append(card)
        
    def shuffle(self):
        random.shuffle(self.deck)
    
    def dealCard(self):
        return self.deck.pop(0)
    
    def display(self):
        for card in self.deck:
            card.display()

    def deal(self, x):
        dealtcards = []
        for i in range(x):
            dealtcards.append(self.dealCard())
        return dealtcards
            
