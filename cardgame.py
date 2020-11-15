import random
import quickflask
import webgame
from webgame import init
from copy import deepcopy, copy

class Card:
    def __init__(self, game):
        """Cards values will be set to random values during construction"""
        game: Game
        self.game = game

        self.layer = 0
        self.value = 0
        self.priority = 0
        self.name = ""

        self.randomise()

    def randomise(self):
        self.layer = random.randint(0, 2)
        self.value = random.choice(range(self.layer + 2, self.layer + 4))
        self.calc_name()

    def get_layer_name(self):
        return self.game.layer_labels[self.layer]

    def calc_name(self):
        """Sets and returns the visible name of this card using the cards values"""
        self.name = "%s%s" % (self.value, self.get_layer_name())
        return self.name

    def on_play(self, player):
        """Function that is called whenever the card is played"""
        pass

    def on_sum(self, value):
        """Function that is called whenever the card is attempted to be summed"""
        return value + self.value

    def __call__(self, *args, **kwargs):
        return self.on_sum(*args, **kwargs)


class SpyCard(Card):
    def on_play(self, player):
        player.draw_card()
        player.draw_card()

    def on_sum(self, value):
        return value - self.value

    def calc_name(self):
        self.name = '-' + Card.calc_name(self)
        return self.name


class NukeCard(Card):
    def on_play(self, player):
        for player in player.game.players:
            player.board_layers[self.layer] = []

    def calc_name(self):
        self.name = "-(%s)" % self.get_layer_name()
        return self.name


class MultCard(Card):
    def __init__(self, game):
        super().__init__(game)
        self.priority = -100
        self.value = 2
        self.calc_name()

    def on_sum(self, value):
        return value * self.value

    def calc_name(self):
        self.name = "%sx%s" % (self.value, self.get_layer_name())


class Player(webgame.WebGamePlayer):
    def __init__(self, game):
        super().__init__(game)

        game: Game
        self.game = game

        self.hand = []
        self.board_layers = [[], [], []]

        self.passed = False
        self.lives = self.game.start_player_lives

    def layer_score(self, index):
        score = 0
        for card in sorted(self.board_layers[index], key=lambda card: card.priority, reverse=True):
            score = card(score)
        return score

    def player_score(self):
        return sum(self.layer_score(a) for a in range(len(self.board_layers)))

    def draw_card(self):
        card = random.choices(self.game.deck, self.game.deck_weights)[0]
        self.hand.append(copy(card))
        card.randomise()

    def play_card(self, card_index):
        to_play: Card
        to_play = self.hand.pop(card_index)
        self.board_layers[to_play.layer] += [to_play]
        to_play.on_play(self)

    @staticmethod
    def get_layer_names(layer: list):
        return [card.name for card in layer]


class Game(webgame.WebGame):
    def __init__(self, cards_weights=None):

        super().__init__()
        if cards_weights is None:
            cards_weights = []

        self.boards = []
        self.deck = []
        self.deck_weights = []
        self.player_index = 0
        self._started = False

        self.start_player_lives = 2
        self.start_card_count = 5

        self.layer_labels = {0: "A", 1: "B", 2: "C"}

        self.deck_from_tuples(cards_weights)

    def deck_add(self, card: Card, weight: int = 1):
        self.deck.append(card)
        self.deck_weights.append(weight)

    def get_alive_players(self):
        return [a for a in self.players if a.lives > 0]

    def end_round(self):
        assert self._started

        lowest_scorers = []
        lowest_score = None
        for player in self.get_alive_players():
            score = player.player_score()
            if lowest_score is None or lowest_score > score:
                lowest_scorers = [player]
                lowest_score = score
            elif lowest_score == score:
                lowest_scorers.append(player)

            player.board_layers = [[] for _ in player.board_layers]  # Clear the players board
            player.passed = False
            player.draw_card()

        for player in lowest_scorers:
            player.lives -= 1

        self.player_index = 0

    def deck_from_tuples(self, tuples: list):
        tuples = [(a(self), b) for a, b in tuples]
        [self.deck_add(*args) for args in tuples]

    def start(self):
        self._started = True
        for player in self.players:
            [player.draw_card() for _ in range(self.start_card_count)]

    def new_player(self):
        """Returns the index of a new player in the self.players array"""
        assert not self._started
        super().new_player()

    def get_player_type(self):
        return Player

    def current_player(self) -> Player:
        return self.players[self.player_index]

    def next_unpassed_player(self):

        if len(["" for a in self.players if not a.passed]) == 0:
            self.end_round()
            return

        self.player_index = (self.player_index + 1) % len(self.players)
        while self.current_player().passed or self.current_player().lives < 0:
            self.player_index = (self.player_index + 1) % len(
                self.players)  # Find the next player in the list who isnt passed
        return self.player_index

    def player_index_turn(self, hand_id):
        """Hand id should either be the index of the card in the players hand to be played """
        self.current_player().play_card(hand_id)

        self.next_unpassed_player()

    def player_pass(self):
        self.current_player().passed = True
        self.next_unpassed_player()
        return False not in [a.passed for a in self.players]  # Never returns true

    def __getitem__(self, item) -> Player:
        return self.players[item]


if __name__ == '__main__':
    game = Game(None)
    game.deck_from_tuples([
        (Card, 7),
        (SpyCard, 2),
        (NukeCard, 1),
        (MultCard, 1),
    ])
    game.new_player()
    game.new_player()
    game.start()

    while True:
        currentplayer = game.current_player()
        print("Player %i" % (game.player_index + 1))
        print("hand: %s" % currentplayer.get_layer_names(currentplayer.hand))
        print("layer scores: %s" % [currentplayer.layer_score(a) for a in range(len(currentplayer.board_layers))])
        print("score: %i" % currentplayer.player_score())
        print("lives: %s" % currentplayer.lives)
        cardtoplay = input()

        if len(currentplayer.hand) < 1 or cardtoplay == "pass":
            game.player_pass()
            if len(game.get_alive_players()) <= 1:  # Check if someone has won every round
                playerids = [game.players.index(player) + 1 for player in game.get_alive_players()]
                print("the winner is Player(s): %s" % playerids)
                break

        if cardtoplay != "pass":
            game.player_index_turn(int(cardtoplay) - 1)

    print(game.__dict__)
