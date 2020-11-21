import webgame
from webgame import init
from flask import session
import random
import flask_socketio


def get_possible_addends_sum(arr):  # I copied this from my tkinter version, dont ask me
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
    def __init__(self, val):
        self.value = val
        self.locked = False

    def lock(self):
        self.locked = True


class ShutTheBox(webgame.WebGame):
    def __init__(self):
        super().__init__()
        self.boxes = [Box(a) for a in range(1, 10)]
        self.winner = None
        self.player_turn = 0

        self.target = None
        self.random_target()

    def random_target(self):
        self.target = random.randint(1, 9)

    def player_check(self):
        if self.player_turn > len(self.players):
            self.player_turn = 0
            self.emit_room_event("game_state_receive", self.get_state())

    def new_player(self):
        super().new_player()
        if len(self.players) >= 2:  # TODO, implement a max players system
            webgame.get_room()["open"] = False

    def player_leave(self, uid):
        super().player_leave(uid)
        self.player_check()

    def action_handle(self, ty, *args):
        if ty == "boxes":
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
            # I havent a clue why its this complicated to move to the next value in the players dict

            if 0 == len([a for a in get_possible_addends_sum([a.value for a in self.boxes if not a.locked]) if
                         a[1] == self.target]):  # If there are no possible answers
                self.emit_room_event("game_over",
                                     self.get_users()[self.player_turn - 1]["name"])  # Return the player who its not
            else:
                self.emit_room_event("game_turn", self.get_users()[self.player_turn]["name"])

    def get_state(self):
        return {"boxes": [a.locked for a in self.boxes], "target": self.target, "playerturn": self.player_turn}
