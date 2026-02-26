class Hand_Detection():
    def __init__(self):
        self.total_hand = None
        self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

    def find_hand(self, player_hand, community):
        self.total_hand = player_hand[:] + community[:]
        hand = self.isRoyalFlush()
        if hand: return hand
        hand = self.isStraightFlush()
        if hand: return hand
        hand = self.isQuads()
        if hand: return hand
        hand = self.isFullHouse()
        if hand: return hand
        hand = self.isFlush()
        if hand: return hand
        hand = self.isStraight()
        if hand: return hand
        hand = self.isTrips()
        if hand: return hand
        hand = self.isTwoPair()
        if hand: return hand
        hand = self.isPair()
        if hand: return hand
        return self.HighCard()


    def HighCard(self):
        self.total_hand.sort(reverse= True)
        return ("HighCard",) + tuple(self.total_hand[i].rank for i in range(0,5))
    
    def isPair(self):
        high_pair = None
        for i in range(len(self.total_hand)):
            for j in range(i+1,len(self.total_hand)):
                if self.total_hand[i] == self.total_hand[j]:
                    if high_pair is None:
                        high_pair = self.total_hand[i]
                    else:
                        high_pair = max(self.total_hand[i], high_pair)

        if high_pair != None:
            hand = []
            for card in self.total_hand:
                if card != high_pair:
                    hand.append(card)
            hand.sort(reverse=True)
            return ("Pair", high_pair.rank) + tuple(hand[i] for i in range(0,3))
        return False
        
     
    def isTwoPair(self):
        pairs = []
        for i in range(len(self.total_hand)):
            for j in range(i+1,len(self.total_hand)):
                if self.total_hand[i] == self.total_hand[j]:
                    pairs.append(self.total_hand[i])
        pairs = sorted(set(pairs), reverse=True)
        hand = []
        for card in self.total_hand:
            if card not in pairs:
                hand.append(card)
        hand.sort(reverse=True)
        if len(pairs) >= 2:
            return ("Two Pair", pairs[0].rank, pairs[1].rank) + (hand[0].rank,)
        return False
    
    def isTrips(self):
        high_card = None
        for i in range(len(self.total_hand)):
            for j in range(i+1,len(self.total_hand)):
                for k in range(j+1, len(self.total_hand)):
                    if self.total_hand[i] == self.total_hand[j] == self.total_hand[k]:
                        if high_card == None: high_card = self.total_hand[i]
                        high_card = max(high_card, self.total_hand[i])
        if high_card != None:
            hand = []
            for card in self.total_hand:
                if card != high_card:
                    hand.append(card)
            hand.sort(reverse=True)
            return ("Trips", high_card.rank) + tuple(hand[i].rank for i in range (0,2))
        return False
    
    def isStraight(self):
        self.total_hand.sort()

        indices = sorted(set(self.ranks.index(c.rank) for c in self.total_hand))

        if self.ranks.index("A") in indices:
            indices.insert(0, -1)

        count = 1
        best_high = None
        for i in range(1, len(indices)):
            if indices[i] == indices[i - 1] + 1:
                count += 1
                if count >= 5:
                    best_high = indices[i]  
            else:
                count = 1

        if best_high is not None:
            return ("Straight", self.ranks[best_high])  
        return False 
    
    def isFlush(self):
        suits = {"H":[], "D":[], "S":[], "C":[]}

        for card in self.total_hand:
            suits[card.suit].append(card)
        
        for suit_cards in suits.values():
            if len(suit_cards) >= 5:
                suit_cards.sort(reverse=True)
                return ("Flush",) + tuple(suit_cards[i].rank for i in range(0, 5))
            
        return False
    
    def isFullHouse(self):
        card_count = {}
        for card in self.total_hand:
            if card.rank in card_count:
                card_count[card.rank] += 1
            else: card_count[card.rank] = 1
        trips = []
        pair = []
        for rank, count in card_count.items():
            if count == 3:
                trips.append(self.ranks.index(rank))
            if count == 2:
                pair.append(self.ranks.index(rank))
        trips.sort(reverse=True)
        pair.sort(reverse=True)
        if (len(trips) == 1) and (len(pair)>= 1):
            return ("Full House", self.ranks[trips[0]], self.ranks[pair[0]])
        elif (len(trips) == 2):
            return ("Full House", self.ranks[trips[0]], self.ranks[trips[1]])
        else: return False

    
    def isQuads(self):
        for i in range(len(self.total_hand)):
            for j in range(i+1,len(self.total_hand)):
                for k in range(j+1, len(self.total_hand)):
                    for l in range(k+1, len(self.total_hand)):
                        if self.total_hand[i] == self.total_hand[j] == self.total_hand[k] == self.total_hand[l]:
                            hand = []
                            for card in self.total_hand:
                                if card !=self.total_hand[i]:
                                    hand.append(card)
                                    hand.sort(reverse=True)
                            return ("Quads", self.total_hand[j].rank) + (hand[0].rank,)
        return False

    def isStraightFlush(self):
        if (self.isStraight() != False and self.isFlush() != False):
            suits = {"H":[], "D":[], "S":[], "C":[]}

            for card in self.total_hand:
                suits[card.suit].append(card)
            
            for suit_cards in suits.values():
                if len(suit_cards) >= 5:
                    suit_cards.sort()

                    indices = sorted(set(self.ranks.index(c.rank) for c in suit_cards))

                    if self.ranks.index("A") in indices:
                        indices.insert(0, -1)

                    count = 1
                    best_high = None
                    for i in range(1, len(indices)):
                        if indices[i] == indices[i - 1] + 1:
                            count += 1
                            if count >= 5:
                                best_high = indices[i]  
                        else:
                            count = 1

                    if best_high is not None:
                        return ("StraightFlush", self.ranks[best_high])  
        return False
    
    def isRoyalFlush(self):
        sf = self.isStraightFlush()
        if sf and sf[1] == "A":
            return ("RoyalFlush", "A")

        return False