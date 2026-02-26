from engine.game import *
from engine.table import *

        

        
def main():
    table = Table()
    game = Game(table)
    name = input("Enter name:")
    player = humanPlayer(name, table)
    game.players.append(player)
    computer = humanPlayer("computer", table)
    game.players.append(computer)
    game.smallBlind_Bet = 10
    game.bigBlind_Bet = 20
    for player in game.players:
        player.chips = 1000
    while len(game.players) > 1:
        game.play_hand()




main()
