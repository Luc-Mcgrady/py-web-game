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
    _user.userkeys["playerid"] = None

    @_user.socket.on("game_state")
    def gamestate_parse(keys=None):

        if keys is None:
            keys = []

        gamestate = room["game"].get_state()

        for key in keys:
            gamestate = gamestate[key]

        quickflask.return_socket('game_state_return', gamestate, tuple(keys))

    # @_user.socket.on("game_playerstate")
    # def playerstate_parse(json: dict):
    #    state = room["game"].players[json["uid"]].get_player_state()
    #    state = WebGame.handle_keys(json, state)

    #    quickflask.return_socket(state)

    @_user.socket.on("game_action")
    def action_parse(ty, *args):
        room["game"].action_handle(ty, *args)

    _initiated = True


def get_room():
    return _room


def get_user():
    return _user


class WebGame:
    @staticmethod
    def _handle_keys(json: dict, o__: dict):  # I saw someone use o__ and thought it looked cool
        if "keys" in json:
            assert type(json["keys"]) == list
            for key in json["keys"]:
                o__ = o__[key]
        elif "key" in json:
            o__ = o__[json["key"]]

        return o__

    @staticmethod
    def emit_room_event(ty, *args):
        """Sends a message back to the client javascript, caught with a socket.on(ty,(*args) => {function})"""
        _room.socket_emit(ty, *args)

    def __init__(self):
        assert _initiated, "run webgame.init(user, room) first"

        self.players = {}
        self.max_players = None
        self.closed = False

    def close_room(self):
        self.closed = True
        _room["open"] = False

    def set_max_players(self, val: int):
        self.max_players = val

    def get_players(self):
        return self.players

    def get_users(self):
        return [_user.users[player] for player in self.players]

    def get_users_attr(self, key):
        return [_user.users[player][key] for player in self.players]

    def get_state(self):
        """Should be overloaded with a dict of all variables that need to be retrived by the client"""
        return self.__dict__

    def send_state(self, keys: list = None):
        if keys is None:
            keys = []

        state = self.get_state()

        for key in keys:
            state = state[key]

        self.emit_room_event("game_state_return", state)

    def new_player(self):
        self.players[session["uid"]] = self.get_player_type()(self)

        if self.max_players is not None and len(
                self.players) >= self.max_players:  # TODO, implement a max players system
            _room["open"] = False

        return session["uid"]

    @staticmethod
    def get_player_type():
        """Should be overridden to return the webplayer class that you want"""
        return WebGamePlayer

    def action_handle(self, ty, *args):
        """Handles any actions passed to it via javascript: socket.emit("game_action",ty,*args)"""
        pass

    def player_leave(self, uid):
        self.players.pop(uid)
        if self.max_players is not None and not self.closed:  # In case a custom open and close system is wanted
            _room["open"] = True


class WebGamePlayer:
    def __init__(self, game):
        self.game = game

    def get_game(self):
        return self.game

    def get_player_state(self):
        """should be overloaded to return a dict with all the data relavent to the game"""
        return self.__dict__
