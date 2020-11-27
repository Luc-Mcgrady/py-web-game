import flask
from flask import request, session
from copy import deepcopy
import flask_socketio as socketio


# Todo add a sweep function which automaticaly logs out users and kicks them out of rooms if they have been afk (not sent or recived events) long enough.

class UserBase:
    def __init__(self, flaskserver: flask.Flask, userdefaults=None):

        if userdefaults is None:
            userdefaults = {}

        assert "messages" not in userdefaults

        self.server = flaskserver
        self.userkeys = userdefaults
        self.users = {}  # Dict as when a user logs off their room_id wont change
        self.socket = socketio.SocketIO(self.server)

    def current_user(self):
        """Get the current user that sent the HTTP request and all their attributes"""
        try:
            return self.users[session["uid"]]
        except KeyError:
            return None

    def new_logon(self):
        """Creates a new user and returns the users key"""
        newuid = len(self.users)
        self.users[newuid] = self.userkeys.copy()
        session["uid"] = newuid
        return self.users[newuid]

    @staticmethod
    def logout():
        """This logs the player out so that they are no longer on the browser.
        This does NOT remove the player from the player list meaning that theoreticaly they could log back in
        todo Add re-login (would required password and be risky since the site isnt the best secure site ever)"""
        session.pop("uid", None)

    def b_logged_in(self):
        """ Returns true if there is a player logged in the current browser, otherwise returns false
        better than if self.current_user() is none because it is uses cookies rather than serverside storage"""
        return "uid" in session and session["uid"] in self.users

    def currentuser_set_attribute(self, key, val, localstorage: bool = False):
        """Basicaly obsolete due to self[key] = val
        but contains a "localstorage" argument for weather you want to store a value as a cookie as well as serverside
        for whatever reason"""

        assert key in self.current_user(), """
The key "{key}" was not already in the template of a user .
ensure that all users keys remain consistant.
The fix would be to add "{key}" to the default template""".format(key=key)
        self.current_user()[key] = val

        if localstorage:
            session[key] = val

    # def send_message(self, key: int, message: str):
    #    self.users[key]["messages"].append(message)

    def global_message(self, message: dict):
        """Sends a socketIO message to every player in the game, does not work on pages without socketio"""
        self.socket.send(message, broadcast=True)

    def currentuser_get_attribute(self, item):
        """The same as self[item] todo Delete"""
        try:
            return self.current_user()[item]
        except (TypeError, KeyError):
            return

    def __getitem__(self, item):
        """Returns an attribute of the current player."""
        return self.currentuser_get_attribute(item)

    def __setitem__(self, key, value):
        """Sets an attribute of the current player"""
        self.currentuser_set_attribute(key, value)


class RoomBase:
    def __init__(self, userbase: UserBase, default_roomkeys=None):
        """
        Arguments:
            userbase: self explanatory
            default_roomkeys: all the keys that are relavent to the room, No new keys should be created after start to
            keep all the user attributes concurrent. For differing attributes use the game class.

        The reserved keys should be used as follows

        uids: Untouched,
        open: Simply set this to false to prevent people joining that room, You can do this from the game object or (inadvisably) directly.
        game: should be a webgame.WebGame object or child object, this object will contain this logic of the room.
        """

        if default_roomkeys is None:
            default_roomkeys = {}

        self.rooms = {}
        self.rooms_len = 1  # Tried 0 but it doesnt work with socketio, maybe a reseved room by the socketio library?
        self.user = userbase
        self.user.userkeys["room"] = None

        for key in ["uids", "open", "game"]:
            assert key not in default_roomkeys, "reserved key '%s'" % key
        self.roomkeys = default_roomkeys
        self.roomkeys["uids"] = []
        self.roomkeys["open"] = True
        self.roomkeys["game"] = None

        @self.user.socket.on('connect')
        def re_room():  # This is needed because the clientside socketio forgets which room its in every time the page changes.
            if self.user["room"] is not None:
                socketio.join_room(self.user["room"])

    def join_room(self, room_id):
        """Makes the user join a room.
        if the user is already in a room, leave that room and then join the room"""
        if self.user["room"] is not None:
            self.leave_room()
        if not self.rooms[room_id]["open"]:
            return

        socketio.join_room(room_id)
        self.user["room"] = room_id

        self.rooms[room_id]["uids"].append(session["uid"])

    def new_room(self):
        """Creates a new room and returns the rooms uid"""
        room_id = self.rooms_len
        self.rooms_len += 1
        self.rooms[room_id] = deepcopy(self.roomkeys)
        return room_id

    def leave_room(self):
        """Removes the user from the room that they are currently in"""
        assert self.user["room"] is not None
        room_id = self.user["room"]
        socketio.leave_room(room_id)
        try:
            self.rooms[room_id]["uids"].remove(session["uid"])
        except ValueError:
            pass

        if self["game"] is not None:
            self.rooms[room_id]["game"].player_leave(session[
                                                         "uid"])  # todo I havent touched this code in a while but feel like this should remove game the users your attribute
            # Also when pycharm autoformats it does that wierd line breaky thing automaticaly, not my fault
        if len(self.rooms[room_id]["uids"]) < 1:
            self.rooms.pop(room_id)

        self.user["room"] = None

    def socket_emit(self, event, *args):
        """Sends a socketio message to all the users in the room."""
        socketio.emit(event, *args, room=self.user["room"])

    def __getitem__(self, item):
        """Gets the current room's attributes"""
        try:
            return self.rooms[self.user["room"]][item]
        except KeyError:
            return None

    def __setitem__(self, key, value):
        """Sets an attribute of the current room"""
        assert key in self.roomkeys
        self.rooms[self.user["room"]][key] = value


class TemplateCombiner:
    """Takes in 2 sets of templates one to be rendered before a given templates and one to be rendered after.
        useful for headers and footers"""

    def __init__(self, before: list = None, after: list = None, func_default_kwargs: dict = None):
        """List for header templates, list for footer templates, dict for functions that return default kwargs"""

        if func_default_kwargs is None:
            self.defaultkwargs = {}
        else:
            self.defaultkwargs = func_default_kwargs
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

        kwargs = {**{k: v() for k, v in self.defaultkwargs.items()}, **kwargs}

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
    """Returns a socketio message to soely the user that sent it.
    For this function to work properly there must not be any negative socketio rooms"""
    assert "room" not in kwargs
    return_room = -session["uid"]  # Unique room just in case, untested if just -1 would work

    socketio.join_room(
        return_room)  # todo I feel like there is some library inbuilt way of doing this but the one i tried didnt work so i gave up.
    socketio.emit(ty, args, **kwargs, room=return_room)
    socketio.leave_room(return_room)
