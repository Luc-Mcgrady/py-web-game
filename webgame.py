import quickflask
from flask import session

_user = None
_room = None
_initiated = False


def init(user: quickflask.UserBase, room: quickflask.RoomBase,
         fail_on_reinit=True):  # I like this as much as you do but I cant figure out a way around it
    """ Initiates this library using a given user and room
    fail_on_reinit determinse if the program should raise an error if it has been initiated previously"""

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

        game = room["game"]
        gamestate = game.get_state()
        assert "player_uid" not in gamestate, "Reserved key: player_uid"
        gamestate["player_uid"] = session["uid"]
        # For technichal reasons you can only retrive the player uid on a return message instead of one sent
        # by the backend

        for key in keys:
            gamestate = gamestate[key]

        quickflask.return_socket('game_state_return', gamestate, keys)

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
    def _handle_keys(json: dict, o__: dict):  # I saw someone use o__ and thought it looked cool todo unused, delete
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

    @staticmethod
    def title():
        """Should be overloaded to return the title of the game"""
        return "WebGameGeneric"

    def __init__(self):
        """This should be overloaded with at least:
             setting template_url to the appropriate filename. (should be in templates/game/rooms)
        You can then put whatever else you want here
         """
        assert _initiated, "run webgame.init(user, room) first"

        self.template_url = ""  # Should be set to the html of the room that recives the socket.

        self.players = {}
        self.max_players = None
        self.closed = False

    def close_room(self):
        """Locks the room so other people cant get in"""
        self.closed = True
        _room["open"] = False

    def set_max_players(self, val: int):
        """Set the max players"""
        self.max_players = val

    def get_players(self):
        """Get the list of all players in the form of WebGamePlayer objects or whatever object you overloaded """
        return self.players

    def get_users(self):
        """Gets the non game attributes of the users playing the game, mostly useful for names"""
        return [_user.users[player] for player in self.players]

    def get_users_attr(self, key):
        """same as the above except gets a specific attribute of all the users, for example get_users_attr(name) for names"""
        return [_user.users[player][key] for player in self.players]

    def get_state(self):
        """Should be overloaded with a dict of all variables that need to be retrived by the client"""
        return self.__dict__

    def send_state(self, keys: list = None):
        """Sends the gamestate to the clientside javascript to update any values in the state that changed
        Keys can be used to send only specific values if you want to save bandwidth.
        """
        if keys is None:
            keys = []

        state = self.get_state()

        for key in keys:
            state = state[key]

        self.emit_room_event("game_state_return", state)

    def new_player(self):
        """This function is called whenever a new player enters the room"""
        self.players[session["uid"]] = self.get_player_type()(self)

        if self.max_players is not None and len(
                self.players) >= self.max_players:  # TODO, implement a max players system
            _room["open"] = False

        return session["uid"]

    @staticmethod
    def get_player_type():
        """Should be overridden to return the WebGamePlayer class that you want"""
        return WebGamePlayer

    def action_handle(self, ty, *args):
        """Handles any actions passed to it via javascript: socket.emit("game_action",ty,*args)"""
        pass

    def player_leave(self, uid):
        """Called everytime a player leaves a game"""
        self.players.pop(uid)
        if self.max_players is not None and not self.closed:  # In case a custom open and close system is wanted
            _room["open"] = True


class WebGamePlayer:
    """todo Not yet fully implimented
    can be used to easily impliment player specific functions and store player variables. e.g. adding a player score"""

    def __init__(self, game):
        self.game = game

    def get_game(self):
        return self.game

    def get_state(self):
        """should be overloaded to return a dict with all the data relavent to this player in game"""
        return self.__dict__
