import quickflask
from flask import session

_user = None
_room = None
_initiated = False


def init(user: quickflask.UserBase, room: quickflask.RoomBase, fail_on_reinit=True):
    global _user, _room, _initiated
    assert fail_on_reinit or not _initiated
    _user = user
    _room = room

    _room.roomkeys["game"] = None

    @_user.socket.on("request_gamestate")
    def gamestate_parse(json: dict):
        gamestate = room["game"].get_state()

        gamestate = WebGame.handle_keys(json, gamestate)

        quickflask.return_socket('receive_gamestate', gamestate)

    @_user.socket.on("request_playerinfo")
    def playerstate_parse(json: dict):
        state = room["game"].players[json["uid"]].get_player_state()
        state = WebGame.handle_keys(json, state)

        quickflask.return_socket(state)

    _initiated = True


class WebGame:
    @staticmethod
    def handle_keys(json: dict, o__: dict):  # I saw someone use o__ and thought it looked cool
        if "keys" in json:
            assert type(json["keys"]) == list
            for key in json["keys"]:
                o__ = o__[key]
        elif "key" in json:
            o__ = o__[json["key"]]

        return o__

    def __init__(self):
        assert _initiated, "run webgame.init(user, room) first"

        self.players = {}

    def get_players(self):
        return self.players

    def get_players_attr(self, key):
        return [_user.users[player][key] for player in self.players]

    def get_state(self):
        """Should be overloaded with a dict of all variables that need to be retrived by the client"""
        return self.__dict__

    def new_player(self):
        self.players[session["uid"]] = self.get_player_type()(self)
        return session["uid"]

    @staticmethod
    def get_player_type():
        """Should be overridden to return the webplayer class that you want"""
        return WebGamePlayer


class WebGamePlayer:
    def __init__(self, game):
        self.game = game

    def get_game(self):
        return self.game

    def get_player_state(self):
        """should be overloaded to return a dict with all the data relavent to the game"""
        return self.__dict__
