# This is the main file to run the website, Though you can use the other files to make your own website, they are
# Geared towards making this website work so i wouldent reccomend it, though i would be slightly flattered.

# Todo make imports markdown safe, (html is incredibly easy to inject into the username and likely other places)
import flask
from flask import request, session
import quickflask
import shutthebox


def make_server():  # In a function to avoid globals
    server = flask.Flask(__name__)
    server.secret_key = "Well damn you got me, have fun hacking!!"

    user = quickflask.UserBase(server, {
        "name": None,
    })

    room = quickflask.RoomBase(user, {
        "name": None,
    })

    headerfooter = quickflask.TemplateCombiner(["header.html"], None, {
        "username": lambda: user["name"],
        "logedin": user.b_logged_in,
        "inroom": lambda: user["room"] is not None,
    })

    shutthebox.init(user, room)

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
        if user["room"] is None:
            user.logout()
            return flask.redirect("/")
        else:
            return flask.redirect("/play/room")

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
        return headerfooter("game/matchlist.html", all_redirects,
                            lobbys=sorted(list(a for a in room.rooms.items() if a[1]["open"]),
                                          key=lambda x: -len(x[1]["uids"]))
                            )  # TODO Open feature of webpage instead of ommiting room entirely

    @server.route("/play/createroom", methods=["GET", "POST"])
    def creategame():
        if request.method == "POST":
            return flask.redirect("/play/room")
        return headerfooter("game/matchcreator.html", all_redirects)

    @server.route("/play/room")
    def gameroom():
        redirect = redirect_login()
        if redirect is not None:
            return redirect
        return headerfooter("game/shutthebox.html", players=room["game"].get_users_attr("name"))

    @user.socket.on("create")  # Todo This SHOULD NOT BE A SOCKET, convert a server.route(method=post)
    def createroom():
        room_id = room.new_room()
        room.join_room(room_id)

        room["name"] = user["name"]
        room["game"] = shutthebox.ShutTheBox()  # <<<<< THIS HERE
        user["playerid"] = room["game"].new_player()

        quickflask.return_socket('redirect', "/play/room")

    @user.socket.on("join")  # todo this should also not be a socket.
    def joining(room_id):
        if room.rooms[room_id]["open"]:
            room.join_room(room_id)
            user["playerid"] = room["game"].new_player()

            quickflask.return_socket('redirect', "/play/room")

    @user.socket.on("leave")  # Maybe you can justify this being a socket instead of a post though i somewhat doubt it
    def leaving():
        room.leave_room()
        quickflask.return_socket('redirect', "/play/rooms")

    @user.socket.on("game_start")
    def return_button_press():  # todo I have no idea what this does
        socket.emit("setnum", room["number"], room=user["room"])

    return user.socket, server


socket, app = make_server()
if __name__ == '__main__':
    print("Server running on http://localhost:5000")
    socket.run(app)
