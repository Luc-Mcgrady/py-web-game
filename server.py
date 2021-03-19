# This is the main file to run the website, Though you can use the other files to make your own website, they are
# Geared towards making this website work so i wouldn't recommend it, though i would be slightly flattered.

# Todo make imports markdown safe, (html is incredibly easy to inject into the username and likely other places)
import flask
from flask import request
import quick_flask
import web_games
import web_game

GAME_LIST = [web_games.ShutTheBox, web_games.BottomCards]


def make_server(m_game_list=None):  # In a function to avoid globals
    if m_game_list is None:
        m_game_list = []

    server = flask.Flask(__name__)
    server.secret_key = "Well damn you got me, have fun hacking!!"

    user = quick_flask.UserBase(server, {
        "name": None,
    })

    room = quick_flask.RoomBase(user, {
        "name": None,
    })

    header_footer = quick_flask.TemplateCombiner(["header.html"], None, {
        "username": lambda: user["name"],
        "logged_in": user.b_logged_in,
        "in_room": lambda: user["room"] is not None,
    })

    web_game.init(user, room)

    def redirect_login():
        if not user.b_logged_in():
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
        return header_footer("home.html", [redirect_room], playercount=sum(len(a["uids"]) for a in room.rooms.values()))

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
        if user.b_logged_in():
            return flask.redirect("index")
        return header_footer("login.html", [redirect_room])

    @server.route("/play/rooms")
    def match_list():
        return header_footer("game/match_list.html", all_redirects,
                             lobbys=sorted(list(a for a in room.rooms.items() if a[1]["open"]),
                                           key=lambda x: -len(x[1]["uids"]))
                             )  # TODO Open feature of webpage instead of omitting room entirely

    @server.route("/play/create_room", methods=["GET", "POST"])
    def create_game():
        if request.method == "POST":
            return flask.redirect("/play/room")
        return header_footer("game/game_list.html", all_redirects, gamelist=m_game_list)

    @server.route("/play/room")
    def game_room():
        redirect = redirect_login()
        if redirect is not None:
            return redirect
        if user["room"] is None:
            flask.abort(401)

        return header_footer("game/rooms/%s" % room["game"].template_url, players=room["game"].get_users_attr("name"))

    @user.socket.on("create")
    def create_room(game_type: str):
        if not user.b_logged_in():
            quick_flask.return_socket("redirect", "/login")
            return

        game_type = [a for a in m_game_list if a.__name__ == game_type][0]

        room_id = room.new_room()
        room.join_room(room_id)

        room["name"] = user["name"]
        room["game"] = game_type()
        user["player_id"] = room["game"].new_player()

        quick_flask.return_socket('redirect', "/play/room")

    @user.socket.on("join")
    def joining(room_id):
        if room_id not in room.rooms:  # Catch if the player tries to join a non existent room
            return

        if room.rooms[room_id]["open"]:
            room.join_room(room_id)
            user["player_id"] = room["game"].new_player()

            quick_flask.return_socket('redirect', "/play/room")

    @user.socket.on("leave")
    def leaving():
        room.leave_room()
        quick_flask.return_socket('redirect', "/play/rooms")

    return user.socket, server


socket, app = make_server(GAME_LIST)
if __name__ == '__main__':
    print("Server running on http://localhost:5000")
    socket.run(app)
