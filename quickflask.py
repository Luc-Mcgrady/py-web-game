import flask
from flask import request, session
import json
import flask_socketio as socketio


class UserBase:
    def __init__(self, flaskserver: flask.Flask, userdefaults=None):

        if userdefaults is None:
            userdefaults = {}

        assert "messages" not in userdefaults

        self.server = flaskserver
        self.userkeys = userdefaults
        self.users = {}  # Dict as when a user logs off their id wont change
        self.socket = socketio.SocketIO(self.server)
        self._message_handlers = {"void": lambda a: None}

        this = self

        @self.socket.on("json")
        @self.socket.on("message")
        def message_handle(json):
            """Handle the messages sent from the client to the server"""
            print("Got json: %s" % json)

            assert type(json) == dict

            if "type" not in json:
                raise KeyError("Malformed socketio request, %s , \"type\" key required" % json)

            if json["type"] in this._message_handlers:
                resp = this._message_handlers[json["type"]](json)
                if resp is not None:
                    this.socket.send(resp)
            else:
                raise KeyError("Missing json handler '%s'" % json)

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
        session["uid"] = None

    def b_logged_in(self):
        """better than if .current_user() is none because it is for cookies rather than serverside storage"""
        return "uid" in session and session["uid"] in self.users

    def currentuser_set_attribute(self, key, val, localstorage: bool = False):

        assert key in self.current_user()
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

    def new_message_handler(self, json_type):
        """decorator for the functions that deal with socket messages
        the message should have a type json attribute which is what will direct it to the function that is passed in"""

        def wrapper(func):
            self._message_handlers[json_type] = func

        return wrapper


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

    def before_template_after(self, template=None, **kwargs):
        """Main function used to return a template with 2 """

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
