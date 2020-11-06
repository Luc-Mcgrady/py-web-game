import flask
from flask import request, session
import flask_socketio as socketio
import quickflask
import os


def make_server():
    server = flask.Flask(__name__)
    server.secret_key = os.urandom(16)

    user = quickflask.UserBase(server, {"name": None})

    headerfooter = quickflask.TemplateCombiner(["header.html"], None, {"username": lambda: user["name"]})

    @server.route("/")
    def index():
        return headerfooter("home.html")

    @server.route("/index")
    def home():
        return flask.redirect("/")

    @server.route("/logout")
    def logout():
        user.logout()
        return flask.redirect("/")

    @server.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user.new_logon()
            user.currentuser_set_attribute("name", request.form["name"])
            return flask.redirect("index")
        return headerfooter("login.html")


if __name__ == '__main__':
    socket, server = make_server()

    socket.run(server)
