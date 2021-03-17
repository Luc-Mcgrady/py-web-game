import flask
from flask import session
from copy import deepcopy
import flask_socketio as f_socketio


# Todo add a sweep function which automatically logs out users and kicks them out of rooms if they have been afk (not
#  sent or received events) long enough.

class UserBase:
    def __init__(self, flask_server: flask.Flask, user_defaults=None):

        if user_defaults is None:
            user_defaults = {}

        assert "messages" not in user_defaults

        self.server = flask_server
        self.user_keys = user_defaults
        self.users = {}  # Dict as when a user logs off their room_id wont change
        self.socket = f_socketio.SocketIO(self.server)

    def current_user(self):
        """Get the current user that sent the HTTP request and all their attributes"""
        try:
            return self.users[session["uid"]]
        except KeyError:
            return None

    def new_logon(self):
        """Creates a new user and returns the users key"""
        new_uid = len(self.users)
        self.users[new_uid] = self.user_keys.copy()
        session["uid"] = new_uid
        return self.users[new_uid]

    @staticmethod
    def logout():
        """This logs the player out so that they are no longer on the browser.
        This does NOT remove the player from the player list meaning that theoretically they could log back in
        todo Add re-login (would required password and be risky since the site isn't the best secure site ever)"""
        session.pop("uid", None)

    def b_logged_in(self):
        """ Returns true if there is a player logged in the current browser, otherwise returns false
        better than if self.current_user() is none because it is uses cookies rather than serverside storage"""
        return "uid" in session and session["uid"] in self.users

    def current_user_set_attribute(self, key, val, local_storage: bool = False):
        """Basically obsolete due to self[key] = val
        but contains a "local_storage" argument for weather you want to store a value as a cookie as well as serverside
        for whatever reason"""

        assert key in self.current_user(), """
The key "{key}" was not already in the template of a user .
ensure that all users keys remain consistent.
The fix would be to add "{key}" to the default template""".format(key=key)
        self.current_user()[key] = val

        if local_storage:
            session[key] = val

    # def send_message(self, key: int, message: str):
    #    self.users[key]["messages"].append(message)

    def global_message(self, message: dict):
        """Sends a socketIO message to every player in the game, does not work on pages without f_socketio"""
        self.socket.send(message, broadcast=True)

    def current_user_get_attribute(self, item):
        """The same as self[item] todo Delete"""
        try:
            return self.current_user()[item]
        except (TypeError, KeyError):
            return

    def __getitem__(self, item):
        """Returns an attribute of the current player."""
        return self.current_user_get_attribute(item)

    def __setitem__(self, key, value):
        """Sets an attribute of the current player"""
        self.current_user_set_attribute(key, value)


class RoomBase:
    def __init__(self, user_base: UserBase, default_room_keys=None):
        """
        Arguments:
            user_base: self explanatory
            default_room_keys: all the keys that are relevant to the room, No new keys should be created after start to
            keep all the user attributes concurrent. For differing attributes use the game class.

        The reserved keys should be used as follows

        uids: Untouched, open: Simply set this to false to prevent people joining that room, You can do this from the
        game object or (in-advisably) directly. game: should be a web_game.WebGame object or child object, this object
        will contain this logic of the room.
        """

        if default_room_keys is None:
            default_room_keys = {}

        self.rooms = {}
        self.rooms_len = 1
        # Tried 0 but it doesnt work with socketio, maybe a reserved room by the f_socketio library?
        self.user = user_base
        self.user.user_keys["room"] = None

        for key in ["uids", "open", "game"]:
            assert key not in default_room_keys, "reserved key '%s'" % key
        self.room_keys = default_room_keys
        self.room_keys["uids"] = []
        self.room_keys["open"] = True
        self.room_keys["game"] = None

        @self.user.socket.on('connect')
        def re_room():  # This is needed because the clientside f_socketio forgets which room its in every time the
            # page changes.
            if self.user["room"] is not None:
                f_socketio.join_room(self.user["room"])

    def join_room(self, room_id):
        """Makes the user join a room.
        if the user is already in a room, leave that room and then join the room"""
        if self.user["room"] is not None:
            self.leave_room()
        if not self.rooms[room_id]["open"]:
            return

        f_socketio.join_room(room_id)
        self.user["room"] = room_id

        self.rooms[room_id]["uids"].append(session["uid"])

    def new_room(self):
        """Creates a new room and returns the rooms uid"""
        room_id = self.rooms_len
        self.rooms_len += 1
        self.rooms[room_id] = deepcopy(self.room_keys)
        return room_id

    def leave_room(self):
        """Removes the user from the room that they are currently in"""
        assert self.user["room"] is not None
        room_id = self.user["room"]
        f_socketio.leave_room(room_id)
        try:
            self.rooms[room_id]["uids"].remove(session["uid"])
        except ValueError:
            pass

        if self["game"] is not None:
            self.rooms[room_id]["game"].player_leave(session["uid"])
            # todo I haven't touched this code in a while but feel like this should remove game the users your attribute
            # Also when pycharm auto-formats it does that weird line breaky thing automatically, not my fault
        if len(self.rooms[room_id]["uids"]) < 1:
            self.rooms.pop(room_id)

        self.user["room"] = None

    def socket_emit(self, event, *args):
        """Sends a f_socketio message to all the users in the room."""
        f_socketio.emit(event, *args, room=self.user["room"])

    def __getitem__(self, item):
        """Gets the current room's attributes"""
        try:
            return self.rooms[self.user["room"]][item]
        except KeyError:
            return None

    def __setitem__(self, key, value):
        """Sets an attribute of the current room"""
        assert key in self.room_keys
        self.rooms[self.user["room"]][key] = value


class TemplateCombiner:
    """Takes in 2 sets of templates one to be rendered before a given templates and one to be rendered after.
        useful for headers and footers"""

    def __init__(self, before: list = None, after: list = None, func_default_kwargs: dict = None):
        """List for header templates, list for footer templates, dict for functions that return default kwargs"""

        if func_default_kwargs is None:
            self.default_kwargs = {}
        else:
            self.default_kwargs = func_default_kwargs
        if before is None:
            self.before = []
        else:
            self.before = before
        if after is None:
            self.after = []
        else:
            self.after = after

    def before_template_after(self, template=None, login_redirect_funcs=None, **kwargs):
        """Main function used to return a template with the header and footer designated on initialisation

        login_redirect_funcs should be an array of funcs that return a flask.redirect or none
        It will redirect in the priority of going down the list.

        kwargs can be used to add more kwargs than the default one.
        """

        if login_redirect_funcs is None:
            login_redirect_funcs = []

        for func in login_redirect_funcs:
            redirect = func()
            if redirect is not None:
                return redirect

        kwargs = {**{k: v() for k, v in self.default_kwargs.items()}, **kwargs}

        out = ""

        out += self.render_templates(self.before, **kwargs)
        out += flask.render_template(template, **kwargs)
        out += self.render_templates(self.after, **kwargs)

        return out

    def __call__(self, *args, **kwargs):
        return self.before_template_after(*args, **kwargs)

    @staticmethod
    def render_templates(templates: list, **kwargs):
        out = ""
        for template in templates:
            out += flask.render_template(template, **kwargs)
        return out


def return_socket(ty, *args, **kwargs):
    """Returns a f_socketio message to solely the user that sent it.
    For this function to work properly there must not be any negative f_socketio rooms"""
    assert "room" not in kwargs
    return_room = -session["uid"]  # Unique room just in case, untested if just -1 would work

    f_socketio.join_room(
        return_room)
    # todo I feel like there is some library inbuilt way of doing this but the one i tried didn't
    #  work so i gave up.
    f_socketio.emit(ty, args, **kwargs, room=return_room)
    f_socketio.leave_room(return_room)
