import flask
from flask import request, session
import flask_socketio as socketio
import quickflask
import os


def make_server():
    server = flask.Flask(__name__)
    server.secret_key = os.urandom(16)

    user = quickflask.UserBase(server, {
        "name": None,
    })

    room = quickflask.RoomBase(user, {
        "name": None,
        "number": 0
    })

    headerfooter = quickflask.TemplateCombiner(["header.html"], None, {
        "username": lambda: user["name"],
        "logedin": user.b_logged_in
    })

    def redirect_login():
        if "uid" not in session:
            return flask.redirect("/login")

    def redirect_room():
        if user["room"] is not None:
            return flask.redirect("/play/room")

    all_redirects = [redirect_login, redirect_room]

    @server.route("/index")
    def home():
        return flask.redirect("/")

    @server.route("/")
    def index():
        return headerfooter("home.html", [redirect_room], playercount=sum(len(a["uids"]) for a in room.rooms.values()))

    @server.route("/logout")
    def logout():
        user.logout()
        return flask.redirect("/")

    @server.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user.new_logon()
            user["name"] = request.form["name"]
        if "uid" in session:
            return flask.redirect("index")
        return headerfooter("login.html", [redirect_room])

    @server.route("/play/rooms")
    def matchlist():
        print(room.rooms)
        return headerfooter("game/matchlist.html", all_redirects,
                            lobbys=sorted(list(room.rooms.items()), key=lambda x: len(x[1]["uids"]))
                            )

    @server.route("/play/createroom", methods=["GET", "POST"])
    def creategame():
        if request.method == "POST":
            return flask.redirect("/play/room")
        return headerfooter("game/matchcreator.html", all_redirects)

    @server.route("/play/room")
    def gameroom():
        return headerfooter("game/room.html", [redirect_login], number=room["number"])

    @user.socket.on("create")
    def createroom():
        room_id = room.new_room()
        room.join_room(room_id)
        room["name"] = user["name"]

        quickflask.return_socket('redirect', "/play/room")

    @user.socket.on("join")
    def joining(room_id):
        room.join_room(room_id)

        quickflask.return_socket('redirect', "/play/room")

    @user.socket.on("leave")
    def leaving():
        room.leave_room()
        quickflask.return_socket('redirect', "/play/rooms")

    @user.socket.on("button_press")
    def return_button_press():
        room["number"] += 1
        socket.emit("setnum", room["number"], room=user["room"])

    return user.socket, server


if __name__ == '__main__':
    socket, server = make_server()

    socket.run(server, "192.168.0.2", )
