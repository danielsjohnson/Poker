class Card():
    
    def __init__(self, rank, suit):
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.rank = rank
        self.suit = suit

    def display(self):
        print(f"{self.rank}{self.suit}", end = " ")

    def __str__(self):
        return f"{self.rank}{self.suit}"
    
    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        if isinstance(other, Card):
            if (self.rank == other.rank):
                return True
        elif isinstance(other, str):
            if (self.rank == other):
                return True
        return False
    
    
    
    def __add__(self, other):
        if isinstance(other, int):
            index = self.ranks.index(self.rank)
            index = (index + 1) % len(self.ranks)
            return Card(Card.ranks[index], self.suit)
        else:
            return TypeError
    
    def __radd__(self, value):
        return self.__add__(value)
    
    def __lt__(self, other):
        if (self.ranks.index(self.rank) < self.ranks.index(other.rank)):
            return True
        return False
    
    def __gt__(self, other):
        if (self.ranks.index(self.rank) > self.ranks.index(other.rank)):
            return True
        return False
    
    
    def __hash__(self):
        return hash(self.rank)