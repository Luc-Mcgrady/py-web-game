import webgame
from webgame import init
from flask import session
import random


def get_possible_addends_sum(arr):  # I copied this from my tkinter version, dont ask me
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


class Box:  # On second thought a list of bools with the index being the value is probably more approprite but this is more verbose
    def __init__(self, val):
        self.value = val
        self.locked = False

    def lock(self):
        self.locked = True


class ShutTheBox(webgame.WebGame):
    def __init__(self):
        super().__init__()
        self.boxes = None  # variables used for game itself
        self.player_turn = 0
        self.target = None

        self.set_max_players(2)  # Used for lobby

        self.min_players = 2  # Used for starting the game
        self.started = False

        self.settings = {
            "boxes": 9,
        }

    def random_target(self):
        self.target = random.randint(1, 6) + random.randint(1, 6)

    def player_check(self):
        if self.player_turn > len(self.players):
            self.player_turn = 0
            self.send_state()

    def game_start(self):
        self.started = True
        self.random_target()
        self.boxes = [Box(a) for a in range(1, 10)]
        self.emit_room_event("game_turn", self.get_users()[self.player_turn]["name"])
        self.send_state()
        self.emit_room_event("cancel_reset")

    def player_leave(self, uid):
        super().player_leave(uid)
        self.player_check()

    def new_player(self):
        super().new_player()
        if len(self.players) >= self.min_players:
            self.game_start()

    def action_handle(self, ty, *args):
        if not self.started:
            if ty == "restart":
                self.game_start()
            return
        if ty == "boxes":
            # Ideally all this could be a function for neatness but for demonstration ill leave it inline
            assert len(args) == 1
            choices = args[0]
            assert type(choices) == list
            total = 0

            if list(self.players.keys())[self.player_turn] != session["uid"]:  # verify its the players turn
                return

            for boxid in choices:  # Verify the choices are valid
                box = self.boxes[boxid - 1]
                if box.locked:
                    return
                total += box.value
            if total != self.target:
                return

            [self.boxes[a - 1].lock() for a in choices]
            self.random_target()
            self.player_turn = (self.player_turn + 1) & len(self.players) - 1
            # ^ I havent a clue why its this complicated to move to the next value in the players dict

            if 0 == len([a for a in get_possible_addends_sum([a.value for a in self.boxes if not a.locked]) if
                         a[1] == self.target]):  # If there are no possible answers
                self.emit_room_event("game_over",
                                     self.get_users()[self.player_turn - 1]["name"])
                # Return the player who its not the current turn of
                self.started = False
            else:
                self.send_state()

    def get_state(self):
        try:
            boxes = [a.locked for a in self.boxes]
        except TypeError:
            boxes = None

        return {"boxes": boxes,
                "target": self.target,
                "playerturn": self.get_users()[self.player_turn]["name"],
                }
