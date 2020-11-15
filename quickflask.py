import flask
from flask import request, session
from copy import deepcopy
import flask_socketio as socketio


# import logging
# logging.getLogger('werkzeug').setLevel(logging.ERROR)


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
        try:
            return self.users[session["uid"]]
        except KeyError:
            return None

    def new_logon(self):
        newuid = len(self.users)
        self.users[newuid] = self.userkeys.copy()
        session["uid"] = newuid
        return self.users[newuid]

    @staticmethod
    def logout():
        session.pop("uid", None)

    def b_logged_in(self):
        """better than if .current_user() is none because it is for cookies rather than serverside storage"""
        return "uid" in session and session["uid"] in self.users

    def currentuser_set_attribute(self, key, val, localstorage: bool = False):

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
        self.socket.send(message, broadcast=True)

    def currentuser_get_attribute(self, item):
        try:
            return self.current_user()[item]
        except (TypeError, KeyError):
            return

    def __getitem__(self, item):
        return self.currentuser_get_attribute(item)

    def __setitem__(self, key, value):
        self.currentuser_set_attribute(key, value)


class RoomBase:
    def __init__(self, userbase: UserBase, default_roomkeys=None):

        if default_roomkeys is None:
            default_roomkeys = {}

        self.rooms = {}
        self.rooms_len = 0
        self.user = userbase
        self.user.userkeys["room"] = None

        assert "uids" not in default_roomkeys, "reserved key 'uids'"
        self.roomkeys = default_roomkeys
        self.roomkeys["uids"] = []

        @self.user.socket.on('connect')
        def re_room():
            if self.user["room"] is not None:
                socketio.join_room(self.user["room"])

    def join_room(self, room_id):
        """Makes the user join a room, returns if the room is new or not"""
        if self.user["room"] is not None:
            self.leave_room()

        socketio.join_room(room_id)
        self.user["room"] = room_id

        self.rooms[room_id]["uids"].append(session["uid"])

    def new_room(self):
        room_id = self.rooms_len
        self.rooms_len += 1
        self.rooms[room_id] = deepcopy(self.roomkeys)
        return room_id

    def leave_room(self):
        assert self.user["room"] is not None
        room_id = self.user["room"]
        socketio.leave_room(room_id)
        self.user["room"] = None
        self.rooms[room_id]["uids"].remove(session["uid"])
        if len(self.rooms[room_id]["uids"]) < 1:
            self.rooms.pop(room_id)

    def socket_emit(self, event, *args):
        socketio.emit(event, *args, room=self.user["room"])

    def __getitem__(self, item):
        try:
            return self.rooms[self.user["room"]][item]
        except KeyError:
            return None

    def __setitem__(self, key, value):
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


def return_socket(*args, **kwargs):
    assert "room" not in kwargs
    return_room = -session["uid"]  # Unique room just in case, untested if just -1 would work
    socketio.join_room(return_room)
    socketio.emit(*args,**kwargs,room=return_room)
    socketio.leave_room(return_room)
