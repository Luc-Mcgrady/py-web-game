# This is an "example game" to see how the library works although it is fully functional. To change the game that
# is created when you join a room look for the clearly marked comment in "server.py" and change that line.
# Please not there are more functions you can see the descriptions of in "web_game.py".

import web_game
from web_game import init  # This should not be removed because it is called in the server function.
from flask import session
import random


def get_possible_addends_sum(
        arr):
    # I copied this from my tkinter version, don't ask me how it works, used to check if its possible to move.
    """Gets a list of tuples of possible sums from a given list of addends in the format
    (addends to make sum, sum)
    """
    top_threshold = 2 ** len(arr)
    for i in range(0, top_threshold):
        current_sum = 0
        addends = []
        for z, do_add in enumerate("{0:b}".format(i)[::-1]):
            if do_add == '1':
                current_sum += arr[z]
                addends.append(arr[z])
        yield addends, current_sum


class Box:
    # On second thought a list of bools with the index being the value is probably more appropriate but this
    #  is more verbose
    def __init__(self, val):
        self.value = val
        self.locked = False

    def lock(self):
        self.locked = True


class ShutTheBox(web_game.WebGame):
    @staticmethod
    def title():
        return "Shut The Box"

    def __init__(self):
        super().__init__()
        self.template_url = "shut_the_box.html"

        self.boxes = None
        # variables used for game itself
        self.player_turn = session["uid"]
        # Also feel like a player turn system is needed although not every game uses one.
        self.target = None

        self.set_max_players(
            2)  # Used for lobby to make the game disappear and un-joinable when full, todo make room grey out instead

        self.min_players = 2
        # Used for starting the game
        self.started = False
        # I think that most games need a started element so im considering moving it into the main library

        self.settings = {  # These settings will be able to be changed by the player in a future version (todo)
            "boxes": 9,
        }

    def random_target(self):
        """Rolls 2, 6 sided dice and sets the target to the sum"""
        self.target = random.randint(1, 6) + random.randint(1, 6)

    def player_check(self):
        """Checks that the player who's turn it is is still in the game"""
        if self.player_turn not in self.players and len(self.players) > 0:
            self.player_turn = list(self.players)[0]
            self.send_state()

    def next_turn(self):
        player_list = list(self.players)
        self.player_turn = player_list[
            (player_list.index(self.player_turn) + 1) % len(player_list)]  # Move on to the next player
        # ^ I haven't a clue why its this complicated to move to the next value in the players dict
        # todo Make this a library function

    def game_start(self):
        """Starts (or restarts) the game"""
        self.started = True
        self.random_target()
        self.boxes = [Box(a) for a in range(1, 10)]
        self.send_state()
        self.emit_room_event("cancel_reset")

    def player_leave(self, uid):
        """This is an inherited function which is called whenever the player leaves the room"""
        super().player_leave(uid)
        self.player_check()

    def new_player(self):
        """This is an inherited function which is called whenever a player joins the room"""
        super().new_player()
        if len(self.players) >= self.min_players:
            self.game_start()

    def action_handle(self, ty, *args):
        """This is an inherited function which is called when a "game_action" is sent, it contains 2 args which
        are sent from the javascript.

        This function in particular handles 2 things, resetting the game and the choices that are sent by players.
        """
        if not self.started:
            if ty == "restart":
                self.game_start()
            return
        elif ty == "boxes":
            # Ideally all this could be a function for neatness but for demonstration ill leave it inline
            assert len(args) == 1  # Make sure exactly one argument is received
            choices = args[0]  # set a variable to represent the argument for neatness
            assert type(choices) == list  # ensure that the argument is a list
            total = 0

            if self.player_turn != session["uid"]:  # verify its the players turn
                return

            for box_id in choices:  # Verify the choices are valid (sum up to the target and arent locked)
                box = self.boxes[box_id - 1]
                if box.locked:
                    # It is important that we do all the game logic checking on the server side so the player cant
                    # cheat by using js functions.
                    return
                total += box.value
            if total != self.target:
                return

            [self.boxes[a - 1].lock() for a in choices]  # Lock the boxes that the player chose
            self.random_target()  # Set a new target
            self.next_turn()

            if 0 == len([a for a in get_possible_addends_sum([a.value for a in self.boxes if not a.locked]) if
                         a[1] == self.target]):  # If there are no possible answers
                self.emit_room_event("game_over",
                                     self.get_users()[self.player_turn - 1]["name"])
                # Return the player who its not the current turn of for the win screen
                # p.s. This should probably be done through get_state although there is no harm in it.
                self.started = False
            else:
                self.send_state()

    def get_state(self):
        """This is an inherited function that represents all the variables that are in play at a given time that
        arent player specific This dict can be requested at any time by any of the players client side javascript
        using socket.emit("getstate") """
        try:
            boxes = [a.locked for a in self.boxes]
        except TypeError:
            boxes = None

        return {"boxes": boxes,
                "target": self.target,
                "turn_name": web_game.get_user().users[self.player_turn]["name"],
                "turn_uid": self.player_turn,
                }
