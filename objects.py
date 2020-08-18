import datetime
import inspect
import random
import string
import time
import cv2
import numpy as np

from sect.triangulation import constrained_delaunay_triangles

from scipy.ndimage import rotate
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union, cascaded_union
from shapely.affinity import rotate as rt
from shapely import affinity

from draw_functions import get_enlongated_line, get_poly_from_two_rectangle_points
from functions import get_config, convert_to_mks, convert_from_mks, dent_contour, fragment_poly, calculateDistance, \
    get_angle, rotate_around_point_highperf

import gc

from Box2D import *

import pickle

from configobj import ConfigObj

config = ConfigObj('config_default.cfg')

from draw_functions import SelectType

def load(height=800, width=1200, b_height=None, b_width=None):
    """ Init """


    config = ConfigObj("config_default.cfg")
    config.filename = "config.cfg"
    config.write()

    timer = Timer(get_config("screen", "fps"))
    board = Board()
    board.board_name = "base"
    board.b_height = b_height
    board.b_width = b_width

    phys = Physics(get_config("physics", "gravity"))
    phys.board = board
    phys.config = config
    draw = Draw()
    draw.board = board
    phys.draw = draw

    block_accuracy = get_config("blocks", "block_accuracy")
    phys = board.load_blocks(phys=phys, block_accuracy=block_accuracy, height=height, width=width)

    phys.world.contactListener = Contacter()
    msg = Messenger(get_config("screen", "fps"), board)

    msg.board = board

    SCREEN_HEIGHT, SCREEN_WIDTH = board.board.shape[:2]

    phys.height = SCREEN_HEIGHT
    phys.width = SCREEN_WIDTH
    board.palette = Palette()
    board.palette.set_palllette(phys.options["screen"]["palette"])

    # create boundry blocks
    width_block = 100
    center = (width / 2, height / 2)
    if not None in [b_height, b_width]:
        # top block
        shape = [[-b_width / 2, -width_block / 2], [b_width / 2, -width_block / 2], [b_width / 2, width_block / 2],
                 [-b_width / 2, width_block / 2]]
        pos = (center[0], -((b_height - height) / 2) - (width_block / 2))
        phys.create_block(shape=shape, pos=pos, poly_type=-1)

        # bottom block
        shape = [[-b_width / 2, -width_block / 2], [b_width / 2, -width_block / 2], [b_width / 2, width_block / 2],
                 [-b_width / 2, width_block / 2]]
        pos = (center[0], height + ((b_height - height) / 2) + (width_block / 2))
        phys.create_block(shape=shape, pos=pos, poly_type=-1)

        # left block
        shape = [[-width_block / 2, -b_height / 2], [width_block / 2, -b_height / 2], [width_block / 2, b_height / 2],
                 [-width_block / 2, b_height / 2]]

        pos = ((-(b_width - width) / 2) - (width_block / 2), center[1])
        phys.create_block(shape=shape, pos=pos, poly_type=-1)

        # right block
        # top block
        shape = [[-width_block / 2, -b_height / 2], [width_block / 2, -b_height / 2], [width_block / 2, b_height / 2],
                 [-width_block / 2, b_height / 2]]
        pos = (width + (((b_width - width) / 2) + (width_block / 2)), center[1])
        phys.create_block(shape=shape, pos=pos, poly_type=-1)

        for bl in phys.block_list:
            bl.sensor["type"] = "boundry"
            bl.colour = (255, 0, 0)

    return timer, phys, board, draw, msg


def pickler(timer, phys, draw, board, msg, pickle_name, blurb):
    config = ConfigObj('config.cfg')
    for k,v in phys.options.items():
        for kk,vv in v.items():
            config[k][kk] = str(vv)
    config.write()

    board.board_name = pickle_name
    pickle_dic = {"timer": timer, "board": board, "msg": msg, "config": config, "blurb": blurb}
    item_list = []
    for bl in phys.block_list:
        item_list.append(phys.save_block_as_dict(bl))

    pickle_dic["blocks"] = item_list
    pickle_dic["phys"] = {k: v for k, v in phys.__dict__.items() if not "b2" in str(type(v)) and not k == "block_list"}
    pickle_dic["draw"] = {k: v for k, v in draw.__dict__.items() if not "b2" in str(type(v)) and not k == "player_list"}
    pickle.dump(pickle_dic, open("saves/" + pickle_name + ".save", "wb"))


def load_state(pickle_name):
    # get pickle
    if type(pickle_name) is list:
        pickle_name = pickle_name[0]

    if pickle_name.find("/") == -1:
        pickle_name = "saves/" + pickle_name

    file = open(pickle_name + ".save", 'rb')
    pickle_dic = pickle.load(file)

    config = pickle_dic["config"]
    #config.write()

    timer = pickle_dic["timer"]
    board = pickle_dic["board"]
    msg = pickle_dic["msg"]
    phys = Physics(pickle_dic["phys"]["options"]["physics"]["gravity"],config)

    for k, v in pickle_dic["phys"].items():
        if k in phys.__dict__.keys():
            phys.__dict__[k] = v

    draw = Draw()
    for k, v in pickle_dic["draw"].items():
        if k in draw.__dict__.keys():
            draw.__dict__[k] = v

    phys.create_pre_def_block(pickle_dic["blocks"], convert_joints=False)
    phys.world.contactListener = Contacter()

    #phys.change_config(config)

    draw.board = board
    phys.board = board
    for bl in phys.block_list:
        bl.board = board
    msg.board = board
    phys.draw = draw

    return timer, phys, draw, board, msg, pickle_dic["blurb"] if "blurb" in pickle_dic.keys() else None


class Game():
    def __init__(self, board, draw, phys, msg, timer, palette):
        self.board = board
        self.draw = draw
        self.phys = phys
        self.msg = msg
        self.timer = timer
        self.palette = palette


class Palette():

    def __init__(self):
        self.palettes = [
            ["256676", "bde267", "972b2d", "5bef8f", "983888", "14bae1", "db11ac", "2ca559", "e88358", "737fc9",
             "6f7d43", "c6c0fe", "2f4285", "c582ef", "84ee15"],
            ["48bf8e", "235e31", "a1def0", "059dc5", "154975", "bf83f8", "474cd3", "3a91fb", "913e88", "f372a8",
             "7c08c5", "baa3c6", "fb0998", "e24afc", "b1e632"],
            ["52ef99", "0a4f4e", "62d7e1", "369094", "b9cf84", "12982d", "8ddc1c", "658114", "fda547", "7e2640",
             "deae9e", "e65216", "f3768e", "f82387", "564147"],
            ["0cc0aa", "115d52", "9acfd8", "545d7f", "fbacf6", "673f93", "cd49dc", "77ce3f", "841e41", "cd7b66",
             "d5dc51", "683c00", "34f50e", "4f8522", "fec9af"],
            ["69ef7b", "30766a", "9be4c0", "21a645", "bde267", "728e24", "bfd6fa", "711f86", "df76dd", "4e4066",
             "8b8dbc", "2580fe", "7129ed", "fd048f", "f7d153"],
            ["a1def0", "2f4b4e", "46ebdc", "048765", "9de866", "6e9f23", "cddb9b", "4a8bae", "5d3676", "cc9cc7",
             "9a23b1", "658bfb", "2b3fff", "eb74c3", "af2168"],
            ["68affc", "104b6d", "26cdca", "4e3b7e", "42f18f", "b70d61", "bce333", "b67262", "e0bfb4", "7d2b22",
             "257950", "a18ff8", "5920af", "cf60f3", "f4d16a"],
            ["72e5ef", "274c56", "34f199", "b12941", "a9d541", "b27373", "498e94", "ccbff5", "544793", "c86be1",
             "67902f", "f1bb99", "6c3640", "bf711e", "34f50e"],
            ["52ef99", "9a2a06", "4be8f9", "b12060", "a7e831", "214d4e", "c3de9b", "67577f", "f1bb99", "5920af",
             "63a122", "d38ffd", "658b83", "f37a6b", "0ba47e"],
            ["52ef99", "a33e12", "64baaa", "972554", "bce333", "116966", "e4bfab", "41369e", "e3a0fa", "67902f",
             "d148d3", "61f22d", "f67a59", "7d525f", "e0c645"],
            ["42952e", "f0ac3a", "399283", "d452a8", "e65216", "9354e7", "c218f1", "8deb71", "c4a499", "832522",
             "6f547f", "c7ce35", "394b3f", "72e5ef", "b29ff4"],
            ["399283", "dd9f4f", "f24325", "9b4c9d", "f228a0", "3027c8", "37d356", "c0cf66", "378811", "754819",
             "d4c3bd", "c697f4", "e24afc", "62ebc9", "2f4d3e"]]

        self.current_palette = None
        self.block = [0, 1, 2, 4, 5, 14]
        self.player = 6
        self.floor = 7
        self.select_player = 8
        self.line = 9
        self.joint = 10
        self.rope = 11
        self.point = 12
        self.floor = 13

    def set_palllette(self, no, randomise=False):
        self.current_palette = [tuple(int(x[i:i + 2], 16) for i in (0, 2, 4)) for x in self.palettes[no]]
        if randomise:
            random.shuffle(self.current_palette)


class Draw():

    def __init__(self):

        """
        For creating drawings on screen

        """

        self.anchorA = None
        self.anchorB = None
        self.locations = []
        self.status = None
        self.pause = False
        self.coords = []
        self.block = None
        self.player_list = []
        self.mouse = None
        self.distance = []
        self.clone_created = False
        self.draw_ok = True
        self.wheel_size = 3
        self.draw_save = None
        self.vector = None
        self.stage = 0
        self.draw_type = 1

    def set_draw_type(self, ty):
        self.draw_type = ty
    def get_draw_type(self):
        if self.draw_type == 0:
            return SelectType.draw
        elif self.draw_type == 1:
            return SelectType.rectangle
        elif self.draw_type == 2:
            return SelectType.circle

    def log_player(self, player):
        self.pause = True
        self.player_list.append(player)

        self.coords.append(player.get_poly(3).exterior.coords)
        if len(self.player_list) == 2:
            return True
        return False

    def log_point(self, x, y, type_n, coords=None):
        """
        Log fist and last point from mouse events
        :param x:
        :param y:
        :return:
        """
        if self.locations == []:
            self.status = type_n
            self.locations.append([x, y])
            self.pause = True

            if not self.coords is [] and not coords is None:
                self.coords.append(coords)

        elif self.status in ["distance", "weld_pos", "rotation_pos", "wheel_draw", "wheel_move", "rectangle_draw",
                             "circle_draw", "line_draw", "length", "bullet", "screen"]:
            self.locations.append([x, y])
        elif self.status in ["double_dist"] and len(self.player_list) == 1:

            if len(self.locations) == 1:
                self.locations.append([x, y])
            else:
                self.locations[1] = ([x, y])

        elif self.status in ["rotate"] and len(self.player_list) >= 1:

            if len(self.locations) == 1:
                self.locations.append([x, y])
            else:
                self.locations[0] = self.locations[1]
                self.locations[1] = ([x, y])

        elif self.status in ["double_dist1"] and len(self.player_list) == 2:

            if len(self.locations) < 4:
                self.locations.append([x, y])
            else:
                self.locations[3] = ([x, y])

        elif len(self.locations) == 1 and self.status in ["fire", "delete", "trans"]:
            self.locations.append([x, y])

        elif len(self.locations) >= 1 and self.status in ["move", "trans"]:
            self.locations.append([x, y])
            if len(self.locations) == 3:
                self.locations.pop(0)

        elif len(self.locations) >= 1 and self.status in ["select"]:
            if len(self.locations) == 1:
                self.locations.append([x, y])
            else:
                self.locations[1] = [x, y]

        elif self.status in ["fire", "delete"]:
            self.locations[1] = [x, y]

        elif self.status == "poly" or self.status == "frag":
            self.locations.append([x, y])
            if len(self.locations) > 2 and calculateDistance(self.locations[0][0], self.locations[0][1], x, y) < 10:
                return True

    def draw_point(self):
        """
        Draw arrow on the screen
        :param board:
        :return:
        """
        self.draw_coords()

        if len(self.locations) == 0:
            return
        elif len(self.locations) == 1 and not self.status in ["wheel_draw", "wheel_move", "circle_move", "line_draw",
                                                              "double_dist", "double_dist1", "bullet"]:
            self.board.board_copy = cv2.circle(self.board.board_copy,
                                               tuple(np.array(self.locations[0]) + self.board.translation), 2,
                                               self.board.palette.current_palette[self.board.palette.point], -1)
        elif self.status in ["double_dist", "double_dist1"] and 1 < len(self.locations) <= 3:
            self.board.board_copy = cv2.line(self.board.board_copy,
                                             tuple(np.array(self.locations[0]) + self.board.translation),
                                             tuple(np.array(self.locations[1]) + self.board.translation), self.board.palette.current_palette[self.board.palette.line], 2)
        elif self.status in ["double_dist1"] and len(self.locations) == 4:
            self.board.board_copy = cv2.line(self.board.board_copy,
                                             tuple(np.array(self.locations[0]) + self.board.translation),
                                             tuple(np.array(self.locations[1]) + self.board.translation),
                                             self.board.palette.current_palette[self.board.palette.line], 2)
            self.board.board_copy = cv2.line(self.board.board_copy,
                                             tuple(np.array(self.locations[2]) + self.board.translation),
                                             tuple(np.array(self.locations[3]) + self.board.translation),
                                             self.board.palette.current_palette[self.board.palette.line], 2)

        elif self.status in ["wheel_move"]:
            self.board.board_copy = cv2.circle(self.board.board_copy,
                                               tuple(np.array(self.locations[-1]) + self.board.translation),
                                               self.wheel_size if self.wheel_size >= 1 else 1,
                                               self.board.palette.current_palette[self.board.palette.line])
        elif self.status in ["wheel_draw", "circle_draw", "circle_move"]:
            self.board.board_copy = cv2.circle(self.board.board_copy,
                                               tuple(np.array(self.locations[0]) + self.board.translation),
                                               self.wheel_size if self.wheel_size >= 1 else 1,
                                               self.board.palette.current_palette[self.board.palette.line], -1)

        elif len(self.locations) == 2 and self.status == "fire":
            # draw line for fire
            self.board.board_copy = cv2.arrowedLine(self.board.board_copy,
                                                    tuple(np.array(self.locations[0]) + self.board.translation),
                                                    tuple(np.array(self.locations[1]) + self.board.translation),
                                                    self.board.palette.current_palette[self.board.palette.line], 2)

        elif len(self.locations) >= 2 and self.status == "distance":
            self.board.board_copy = cv2.line(self.board.board_copy,
                                             tuple(np.array(self.locations[0]) + self.board.translation),
                                             tuple(np.array(self.locations[-1]) + self.board.translation),
                                             self.board.palette.current_palette[self.board.palette.line], 2)

        elif len(self.locations) >= 2 and self.status == "length":
            self.board.board_copy = cv2.arrowedLine(self.board.board_copy,
                                                    tuple(np.array(self.locations[0]) + self.board.translation),
                                                    tuple(np.array(self.locations[-1]) + self.board.translation),
                                                    self.board.palette.current_palette[self.board.palette.line], 2)

        elif len(self.locations) >= 2 and (self.status in ["poly", "frag"]):
            # used for drawing the rough shape of the polygon
            for i in range(len(self.locations) - 1):
                # board = cv2.line(board, np.array(self.locations[0]), np.array(self.locations[1]), (170, 240, 7), 3)
                self.board.board_copy = cv2.line(self.board.board_copy,
                                                 tuple(np.array(self.locations[i]) + self.board.translation),
                                                 tuple(np.array(self.locations[i + 1]) + self.board.translation),
                                                 self.board.palette.current_palette[self.board.palette.line], 2)
        elif self.status in ["delete", "select", "rectangle_draw", "rectangle_move"]:
            self.board.board_copy = cv2.rectangle(self.board.board_copy, tuple(
                np.array([int(x) for x in self.locations[0]]) + self.board.translation),
                                                  tuple(np.array(
                                                      [int(x) for x in self.locations[-1]]) + self.board.translation),
                                                  self.board.palette.current_palette[self.board.palette.line], 2)


        elif self.status in ["line_draw"]:
            if len(self.locations) >= 2:
                for i in range(0, len(self.locations) - 2):
                    self.board.board_copy = cv2.line(self.board.board_copy,
                                                     tuple(np.array(self.locations[i]) + self.board.translation),
                                                     tuple(np.array(self.locations[i + 1]) + self.board.translation),
                                                     self.board.palette.current_palette[self.board.palette.line], 2)

    def set_distance(self, x, y):
        coord = get_poly_from_ob(self.player_list[0], 3)
        center = coord.centroid
        dist = calculateDistance(x, y, center.x, center.y)
        self.distance.append(dist)

    def draw_coords(self):
        # draw poly
        if not len(self.player_list) == 0:
            for block in self.player_list:
                # dont draw if player
                if not block.is_player:
                    coord = block.get_poly(3).exterior.coords
                    for i in range(len(coord)):
                        co1 = tuple(np.array([int(x) for x in coord[i]]) + self.board.translation)
                        co2 = tuple(np.array(
                            [int(x) for x in coord[(i + 1) if i != len(coord) - 1 else 0]]) + self.board.translation)
                        self.board.board_copy = cv2.line(self.board.board_copy, co1, co2,
                                                         self.board.palette.current_palette[self.board.palette.line], 3)
                        self.board.board_copy = cv2.line(self.board.board_copy, co1, co2,
                                                         self.board.palette.current_palette[self.board.palette.line], 2)

    def reset(self):
        self.status = None
        self.locations = []
        self.pause = False
        self.coords = []
        self.clone_created = False

        # for bl in self.player_list:
        #    bl.sensor = False

        del self.player_list
        self.player_list = []

        self.mouse = None
        self.distance = []
        self.wheel_size = 3
        self.draw_save = None
        self.stage = 0
        self.vector = None
        self.anchorA = None
        self.anchorB = None


class Physics():

    def __init__(self, gravity=(0, 10), config=ConfigObj('config_default.cfg')):

        self.gravity = gravity
        self.world = b2World(gravity=self.gravity)
        self.height = None
        self.width = None
        self.block_list = []
        self.pause = False
        self.draw_objects = {"draw_all": False}
        self.options = {}
        self.config = config
        self.change_config(config=config)
        self.move_keys_list = {}
        self.force_draw_all = False

    def do_keypress(self, key):
        """
        Used to fire the allocated moves to players from predefined keys supplier by user.
        :param key:
        :return:
        """

        for bl in [bl for bl in self.block_list if bl.keys != {}]:
            for k, keys_vals in bl.keys.items():
                for action in keys_vals:
                    if k != None and ord(k) == key:
                        #if cancel rotation
                        if "cancel_rotation" in action.keys():
                            if action["cancel_rotation"]:
                                bl.body.angularVelocity = 0

                        if "cancel_velocity" in action.keys():
                            if action["cancel_velocity"]:
                                bl.body.linearVelocity = (0,0)


                        # if the toggle is activated the switch the toggle on keypress
                        if action["toggle_allowed"] == True and ord(k) == key:
                            action["toggle_status"] = not action["toggle_status"]

                        # if the enforce touchs and player is touching the ground or inforce touches are off then fire the action on key press

                        if (action["enforce_ground_touch"] and bl.body.userData["ground_touches"] > 0) or not action[
                            "enforce_ground_touch"]:

                            if action["type"] == "impulse":
                                vec = np.array(
                                    action["extra"])  # - np.array([bl.body.linearVelocity.x,bl.body.linearVelocity.y])

                                if action["limit_x_speed"]:
                                    vec[0] = vec[0] - bl.body.linearVelocity[0]
                                if action["limit_y_speed"]:
                                    vec[1] = vec[1] - bl.body.linearVelocity[1]

                                impulse = bl.body.mass * vec * action["multiplier"]

                                bl.body.ApplyLinearImpulse(impulse, bl.body.worldCenter, wake=True)

                            elif action["type"] == "force":

                                vec = np.array(
                                    action["extra"])  # - np.array([bl.body.linearVelocity.x,bl.body.linearVelocity.y])

                                if action["limit_x_speed"]:
                                    vec[0] = vec[0] - bl.body.linearVelocity[0]
                                if action["limit_y_speed"]:
                                    vec[1] = vec[1] - bl.body.linearVelocity[1]

                                impulse = bl.body.mass * vec * action["multiplier"]

                                bl.body.ApplyForce(impulse, bl.body.worldCenter, wake=True)

                            elif action["type"] == "relative impulse":

                                vec = np.array(
                                    action["extra"])  # - np.array([bl.body.linearVelocity.x,bl.body.linearVelocity.y])

                                if action["limit_x_speed"]:
                                    vec[0] = vec[0] - bl.body.linearVelocity[0]
                                if action["limit_y_speed"]:
                                    vec[1] = vec[1] - bl.body.linearVelocity[1]

                                impulse = bl.body.mass * vec * action["multiplier"]

                                rotated = rotate_around_point_highperf(impulse, bl.body.angle * -1)
                                bl.body.ApplyLinearImpulse(rotated, bl.body.worldCenter, wake=True)

                            elif action["type"] == "relative force":

                                vec = np.array(
                                    action["extra"])  # - np.array([bl.body.linearVelocity.x,bl.body.linearVelocity.y])

                                if action["limit_x_speed"]:
                                    vec[0] = vec[0] - bl.body.linearVelocity[0]
                                if action["limit_y_speed"]:
                                    vec[1] = vec[1] - bl.body.linearVelocity[1]

                                impulse = bl.body.mass * vec * action["multiplier"]

                                rotated = rotate_around_point_highperf(impulse, bl.body.angle * -1)
                                bl.body.ApplyLinearImpulse(rotated, bl.body.worldCenter, wake=True)

                            elif action["type"] == "rotate":

                                # bl.body.angle += (0.1 if val[2] == "CCW" else -0.1)
                                try:
                                    bl.body.ApplyAngularImpulse(
                                        impulse=(-0.1 if action["extra"] == "CCW" else 0.1) * action["multiplier"],
                                        wake=True)
                                    bl.body.ApplyTorque(
                                        torque=(-0.3 if action["extra"] == "CCW" else 0.3) * action["multiplier"],
                                        wake=True)
                                except IndexError:
                                    print("Block missing error - TODO fix this")

                            elif "motor" in action["type"]:

                                #check its the correct motor
                                motor_id = action["id"]
                                joint = [jn.joint for jn in bl.body.joints if jn.joint.userData["id"] == action["id"]]
                                if joint != []:
                                    joint = joint[0]
                                    #set the current key
                                    joint.userData["key"] = k
                                    joint.motorEnabled = True
                                    #does the motor need to
                                    if action["hold_motor_in_place"]:
                                        lower = float(joint.userData["old_lower_upper"][0])
                                        upper = float(joint.userData["old_lower_upper"][1])
                                        joint.SetLimits(lower, upper)

                                        if "Prismatic" in str(type(joint)):
                                            vector = joint.userData["vector"]
                                            vector = np.array(rotate_around_point_highperf(vector, joint.GetReferenceAngle()))
                                            bl.body.ApplyForce(vector if joint.motorSpeed >= 0 else -vector,bl.body.worldCenter, wake=True)
                                        #joint.limits joint.userData["old_lower_upper"]

                                    if action["type"] == "motor forwards":
                                        if joint.motorSpeed > 0:
                                            joint.motorSpeed *= -1
                                    elif action["type"] == "motor backwards":
                                        if joint.motorSpeed < 0:
                                            joint.motorSpeed *= -1

                    # if not keypress and not toggle
                    else:
                        motor_id = action["id"]
                        joint = [jn.joint for jn in bl.body.joints if jn.joint.userData["id"] == action["id"]]
                        if joint != []:
                            joint = joint[0]
                            if (action["toggle_allowed"] is True and action["toggle_status"] is False) or action["toggle_allowed"] is False:
                                    if k == joint.userData["key"]:
                                        joint.motorEnabled = False

                                        #
                                        if action["hold_motor_in_place"]:
                                            if "Revolute" in str(type(joint)):
                                                joint.userData["current_position"] = joint.angle
                                                pos = joint.userData["current_position"]
                                                if pos != 0:
                                                    joint.SetLimits(pos + (-0.01 if pos > 0 else 0.01),
                                                                    pos + (0.01 if pos > 0 else -0.01))
                                            elif "Prismatic" in str(type(joint)):
                                                joint.userData["current_position"] = joint.translation
                                                pos = joint.userData["current_position"]
                                                if pos != 0:
                                                    joint.SetLimits(pos + (0.3 if pos > 0 else -0.3 ),
                                                                pos + (-0.3 if pos > 0 else 0.3))





    def change_config(self, config=None, board=None):
        if config is None:
            config = ConfigObj('config.cfg')
        for k, v in config.items():
            self.options[k] = {}
            for kk, vv in config[k].items():
                if k in self.options.keys():
                    val = get_config(k, kk, config)
                    if type(val) is dict:
                        val = {k: v for k, v in val.items() if k != "type"}

                    self.options[k][kk] = val
                    if kk == "gravity":
                        grav_val = val
                        self.gravity = grav_val
                        self.world.gravity = (float(grav_val[0]), float(grav_val[1]))
                    elif kk == "palette":
                        if not board is None:
                            palette = val
                            board.palette.set_palllette(palette)

    def set_can_fire(self, fire_bl):
        for bl in self.block_list:
            if bl is fire_bl:
                bl.can_fire = True
            else:
                bl.can_fire = False

    def kill_all(self, static=True, terrain=False):
        for i in np.arange(len(self.block_list) - 1, -1, -1):
            block = self.block_list[i]
            if terrain:
                if block.is_terrain:
                    self.delete(block)
            elif static:
                self.delete(block)
            else:
                if not block.static:
                    self.delete(block)

    def save_block_as_dict(self, block,clone=False):

        """
        used to split the block into a dict of information for pickling
        :param block:
        :return:
        """

        # get main block information
        block_dic = {k: v for k, v in block.__dict__.items() if not "b2" in str(type(v))}

        #create a clone id for identifying the object when recreating
        clone_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))

        # if block.type == 2 or block.type == -2:
        #     block_dic["shape"] = block.radius
        #     block_dic["draw_static"] = True
        # else:
        #     block_dic["shape"] = block.shape

        body_dic = {"inertia": block.body.inertia,
                    "linearDamping": block.body.linearDamping,
                    "linearVelocity": [block.body.linearVelocity.x, block.body.linearVelocity.y],
                    "position": [block.body.position.x, block.body.position.y],
                    "worldCenter": [block.body.worldCenter.x, block.body.worldCenter.y],
                    "localCenter": [block.body.localCenter.x, block.body.localCenter.y],
                    "awake": block.body.awake,
                    "gravityScale": block.body.gravityScale,
                    "active": block.body.active,
                    "angularDamping": block.body.angularDamping,
                    "angularVelocity": block.body.angularVelocity,
                    "awake": block.body.awake,
                    "angle": block.body.angle,
                    "mass": block.body.mass}

        body_user_dict = {k: (v if not "b2" in str(type(v)) else str(type(v))) for k, v in block.body.userData.items()}
        body_user_dict["ob"] = None

        mas_dic = {"mass": block.body.massData.mass,
                   "I": block.body.massData.I,
                   "center": [block.body.massData.center.x, block.body.massData.center.y],
                   }

        fixtures_dic = {}
        shape_dic = {}

        for i, fix in enumerate(block.body.fixtures):

            fixtures_dic[i] = {"restitution": fix.restitution,
                               "sensor": fix.sensor,
                               "friction": fix.friction,
                               "density": fix.density,
                               }

            shape_dic[i] = {"type": str(type(fix.shape)),
                            "radius": fix.shape.radius}
            if hasattr(fix.shape, "vertices"):
                shape_dic[i]["shape"] = fix.shape.vertices  # [block.body.transform * v for v in fix.shape.vertices]

            if hasattr(fix.shape, "pos"):
                shape_dic[i]["pos"] = (fix.shape.pos.x, fix.shape.pos.y)

        all_joints = {}
        all_joints_userData = {}
        for i, joint in enumerate(block.body.joints):
            joints_dic = {"type": type(joint.joint)}

            lower_attributes = [v.lower() for v in dir(joint.joint) if
                                not v.startswith("_") and v not in ["this", "next", "thisown", "type", "userData"]]
            normal_attributes = [v for v in dir(joint.joint) if
                                 not v.startswith("_") and v not in ["this", "next", "thisown", "type", "userData"]]

            for attr in normal_attributes:

                if attr is "anchorA" and hasattr(joint.joint, "anchorA"):
                    anc = joint.joint.anchorA
                    joints_dic["anchorA"] = [anc.x, anc.y]
                elif attr is "anchorB" and hasattr(joint.joint, "anchorB"):
                    anc = joint.joint.anchorB
                    joints_dic["anchorB"] = [anc.x, anc.y]
                elif attr is "bodyA" and hasattr(joint.joint, "bodyA"):
                    joints_dic["bodyA"] = joint.joint.bodyA.userData["ob"].id if joint.joint.bodyA.userData["ob"].id != block.id else clone_id if clone else block.id
                elif attr is "bodyB" and hasattr(joint.joint, "bodyB"):
                    joints_dic["bodyB"] = joint.joint.bodyB.userData["ob"].id if joint.joint.bodyB.userData["ob"].id != block.id else clone_id if clone else block.id
                elif attr is "groundAnchorA" and hasattr(joint.joint, "groundAnchorA"):
                    joints_dic["groundAnchorA"] = joint.joint.groundAnchorA.userData["ob"].id if joint.joint.groundAnchorA.userData["ob"].id != block.id else clone_id if clone else block.id
                elif attr is "groundAnchorB" and hasattr(joint.joint, "groundAnchorB"):
                    joints_dic["groundAnchorB"] = joint.joint.groundAnchorB.userData["ob"].id if joint.joint.groundAnchorB.userData["ob"].id != block.id else clone_id if clone else block.id
                else:
                    ok = False
                    if "get" + attr.lower() in lower_attributes:
                        index = lower_attributes.index("get" + attr.lower())
                        name = normal_attributes[index]
                        attrr = getattr(joint.joint, name)
                        val = attrr()
                        ok = True
                    else:
                        if not inspect.ismethod(getattr(joint.joint, attr)):
                            val = getattr(joint.joint, attr)
                            ok = True
                    if ok and "b2" not in str(type(val)):
                        joints_dic[attr] = val

            try:
                #ax = block.body.GetWorldPoint(joint.joint.GetLocalAxisA())
                joints_dic["axis"] = joint.joint.userData["vector"]
            except:
                pass

            all_joints[i] = joints_dic

            #save joints userdata
            current_joint_userData = {}
            for k,v in joint.joint.userData.items():
                if "b2" in str(type(v)):
                    current_joint_userData[k] = str(type(v))
                else:
                    current_joint_userData[k] = v

            all_joints_userData[i] = current_joint_userData

        return {"block": block_dic, "body": body_dic,"body_user_dict":body_user_dict, "mass": mas_dic, "fixtures": fixtures_dic, "shapes": shape_dic,
                "joints": all_joints,"joints_userData":all_joints_userData,"clone_id":clone_id}

    def create_pre_def_block(self, info, convert_joints=True,clone=False):

        new_obs = 0
        # loop and create each item again
        for block_info in info:

            new_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))

            if (block_info["block"]["type"] in [-1, -2]):
                create_type = self.world.CreateKinematicBody
            else:
                create_type = self.world.CreateDynamicBody

            # create Object
            if block_info["block"]["type"] in [1, -1, 3, 4]:
                shape = block_info["shapes"][0]["shape"]
                self.block_list.append(
                    Block(create_type(position=block_info["body"]["position"],
                                      fixtures=b2FixtureDef(
                                          shape=b2PolygonShape(vertices=shape),
                                          density=block_info["fixtures"][0]["density"])),
                          set_sprite=False, poly_type=block_info["block"]["type"])

                )

            # if circle
            else:

                self.block_list.append(
                    Block(create_type(position=block_info["body"]["position"],
                                      fixtures=b2FixtureDef(
                                          shape=b2CircleShape(radius=block_info["shapes"][0]["radius"]),
                                          density=block_info["fixtures"][0]["density"]))
                          , set_sprite=False, poly_type=block_info["block"]["type"]))

            # get current block and add settings
            block = self.block_list[-1]

            # if found then add other fixtures
            if len(block_info["fixtures"].keys()) > 1:
                for x in range(len(block_info["fixtures"].keys())):
                    if x != 0:
                        fix_key = block_info["fixtures"][x]
                        shape_key = block_info["shapes"][x]
                        if shape_key["type"].find("b2PolygonShape") > -1:
                            shape = shape_key["shape"]
                            block.body.CreateFixture(
                                b2FixtureDef(shape=b2PolygonShape(vertices=shape), restitution=fix_key["restitution"],
                                             density=fix_key["density"], friction=fix_key["friction"]))
                        else:
                            radius = shape_key["radius"]
                            pos = shape_key["pos"]
                            # trans[0] = trans[0] * -1
                            block.body.CreateFixture(b2FixtureDef(shape=b2CircleShape(radius=radius, pos=pos),
                                                                  restitution=fix_key["restitution"],
                                                                  density=fix_key["density"],
                                                                  friction=fix_key["friction"]))
            # set block details
            for k, v in block_info["block"].items():
                if hasattr(block, k):
                    setattr(block, k, v)

            # reseize sprite

            if not block.sprite is None:
                block.set_height_width()

                if block_info["block"]["type"] in [-1, 1, 3]:
                    block.sprite = cv2.resize(block.sprite, dsize=(int(block.width), int(block.height)))
                    block.mask = cv2.resize(block.mask, dsize=(int(block.width), int(block.height)))
                    block.inv_mask = cv2.resize(block.inv_mask, dsize=(int(block.width), int(block.height)))

            # not needed any more!!
            # if block.sprite_on and not type(block.sprite) is None:
            #     block.set_sprite(force=True)

            if clone:
                block.id = block_info["clone_id"]
                block.old_id = block_info["block"]["id"]
                #block.clone_id

            for k, v in block_info["body"].items():
                if hasattr(block.body, k):
                    if type(v) == list and len(v) == 2:
                        try:
                            setattr(block.body, k, b2Vec2(v[0], v[1]))
                        except:
                            if k == "worldCenter":
                                setattr(block.body.worldCenter, "x", v[0])
                                setattr(block.body.worldCenter, "y", v[1])
                            elif k == "localCenter":
                                setattr(block.body.localCenter, "x", v[0])
                                setattr(block.body.localCenter, "y", v[1])
                    else:
                        try:
                            setattr(block.body, k, v)
                        except AssertionError:
                            ##error setting some read only values
                            pass

            for k, v in block_info["mass"].items():
                if hasattr(block.body.massData, k):
                    if type(v) == list and len(v) == 2:
                        setattr(block.body.massData, k, b2Vec2(v[0], v[1]))
                    else:
                        setattr(block.body.massData, k, v)

            for k, v in block_info["fixtures"].items():

                for fix_key, fix_val in v.items():

                    if hasattr(block.body.fixtures[k], fix_key):
                        if type(fix_val) == list and len(fix_val) == 2:
                            setattr(block.body.fixtures[k], fix_key, b2Vec2(fix_val[0], fix_val[1]))
                        else:
                            setattr(block.body.fixtures[k], fix_key, fix_val)

            new_obs += 1

            #set userData
            for k,v in block_info["body_user_dict"].items():
                if not "ob" in k:
                    block.body.userData[k] = v

            block.body.userData["ob"] = block

        # get individual joints

        joints = [x["joints"] for x in info if x["joints"] != {}]
        jointsUser = [x["joints_userData"] for x in info if x["joints_userData"] != {}]
        i = 0
        new_joints = {}
        for joint in joints:
            for k, v in joint.items():
                if v not in new_joints.values():
                    new_joints[i] = v

                    a = self.get_block_by_id(v["bodyA"])
                    b = self.get_block_by_id(v["bodyB"])
                    if v["type"] == b2RopeJoint:
                        self.create_rope_joint(a, b, v["anchorA"], v["anchorB"], v["maxLength"], convert_joints)
                    elif v["type"] == b2DistanceJoint:
                        self.create_distance_joint(a, b, v["anchorA"], v["anchorB"], convert_joints)
                    elif v["type"] == b2RevoluteJoint:
                        self.create_rotation_joint(a, b, v["anchorA"], convert_joints)
                    elif v["type"] == b2WeldJoint:
                        self.create_weld_joint(a, b, v["anchorA"], convert_joints)
                    elif v["type"] == b2PrismaticJoint:
                        self.create_prismatic(a, b, vector=v["axis"], anchor= v["anchorA"], distance=v["upperLimit"],convert=convert_joints)
                    elif v["type"] == b2PulleyJoint:
                        self.create_pulley(a,b,v["lines"])
                    else:
                        print("help")

                    # loop the sorted values and update,v["anchorA"][1],v["anchorA"][1]
                    this_joint = self.world.joints[-1]
                    methods = inspect.getmembers(this_joint, lambda a: (inspect.isroutine(a)))
                    lower_methods = [x[0].lower() for x in
                                     [a for a in methods if not (a[0].startswith('__') and a[0].endswith('__'))]]
                    methods = [x[0] for x in
                               [a for a in methods if not (a[0].startswith('__') and a[0].endswith('__'))]]


                    for key, val in v.items():
                        if not key in ["anchorA", "anchorB", "bodyA", "bodyB", "groundAnchorA", "groundAnchorB",
                                       "type"]:
                            if "set" + key.lower() in lower_methods:
                                method_name = methods[lower_methods.index("set" + key.lower())]
                                set_meth = getattr(this_joint, method_name)
                            else:
                                set_meth = None

                            if not set_meth is None:
                                if type(val) is tuple:
                                    if len(val) == 2:
                                        set_meth(val[0], val[1])
                                    elif len(val) == 3:
                                        set_meth(val[0], val[1], val[2])
                                    elif len(val) == 4:
                                        set_meth(val[0], val[1], val[2], val[3])
                                else:
                                    set_meth(val)
                            else:
                                try:
                                    setattr(this_joint, key, val)
                                except:
                                    pass

                    try:
                        for k,v in jointsUser[i][0].items():
                            self.world.joints[-1].userData[k] = v
                    except IndexError:
                        pass



                i += 1
        return new_obs

    def get_block_by_id(self, id):

        blocks = [bl for bl in self.block_list if bl.id == id]
        if blocks != []:
            return blocks[-1]
        else:
            for bl in self.block_list:
                if bl.id == id:
                    return bl

    def fractal_split(self, block, allow_another=True, convert=False, board=None):

        if not type(block) == list:
            block = [block]

        for bl in block:

            body_dic = {"inertia": bl.body.inertia,
                        "linearVelocity": [bl.body.linearVelocity.x, bl.body.linearVelocity.y],
                        "awake": bl.body.awake,
                        "gravityScale": bl.body.gravityScale,
                        "active": bl.body.active,
                        "angularVelocity": bl.body.angularVelocity}

            poly = bl.get_poly(4)
            shape = list(poly.exterior.coords)[:-1]

            if len(shape) <= 4:
                shape = dent_contour(shape)
            conts = fragment_poly(shape)

            for con in conts:
                poly = Polygon(con)
                new_con = [(int(x[0] - poly.centroid.x), int(x[1] - poly.centroid.y)) for x in con]

                if convert:
                    poly_type = 1
                else:
                    poly_type = -1

                if bl.static:
                    # complete.append(not create_block(pos=(poly.centroid.x,poly.centroid.y), forc=0, out=0, player=1, shape=con))
                    self.create_block(pos=(poly.centroid.x, poly.centroid.y), poly_type=poly_type, shape=new_con)
                else:
                    self.create_block(pos=(poly.centroid.x, poly.centroid.y), poly_type=1, shape=new_con,
                                      draw_static=True)

                block_new = self.block_list[-1]
                for k, v in body_dic.items():
                    if hasattr(block_new.body, k):
                        try:
                            if type(v) == list and len(v) == 2:
                                try:
                                    setattr(block_new.body, k, b2Vec2(v[0], v[1]))
                                except:
                                    if k == "worldCenter":
                                        setattr(block_new.body.worldCenter, "x", v[0])
                                        setattr(block_new.body.worldCenter, "y", v[1])
                                    elif k == "localCenter":
                                        setattr(block_new.body.localCenter, "x", v[0])
                                        setattr(block_new.body.localCenter, "y", v[1])
                            else:
                                setattr(block_new.body, k, v)
                        except Exception as e:
                            print(e)

            self.delete(bl)

    def fractal_create(self, shape, static=True, convert=False, terrain=False):

        shape = shape[:-1]
        if len(shape) <= 4:
            shape = dent_contour(shape)
        conts = fragment_poly(shape)
        blocks = []
        for con in conts:
            poly = Polygon(con)
            new_con = [(int(x[0] - poly.centroid.x), int(x[1] - poly.centroid.y)) for x in con]
            if not static:
                # complete.append(not create_block(pos=(poly.centroid.x,poly.centroid.y), forc=0, out=0, player=1, shape=con))
                self.create_block(pos=(poly.centroid.x, poly.centroid.y), poly_type=1, shape=new_con)
            else:
                if convert:
                    poly_type = 1
                else:
                    poly_type = -1
                self.create_block(pos=(poly.centroid.x, poly.centroid.y), poly_type=poly_type, shape=new_con,
                                  draw_static=True, force_static_block=terrain)
            blocks.append(self.block_list[-1])

        return blocks

    def fractal_block(self, ob, create=True, static=True, allow_another=True, convert=False, board=None):

        if create is True:
            self.fractal_create(ob, static, convert=convert)
        elif create is False:
            self.fractal_split(ob, allow_another=allow_another, convert=convert)

    def get_rand_val(self, main, sub):

        if sub + "_min" in config[main]:
            min = self.options[main][sub + "_min"]
            max = self.options[main][sub + "_max"]
            scale = self.options[main][sub + "_scale"]
            if min != max:
                return random.randint(min, max) / scale
            else:
                return min / scale
        else:
            return self.options[main][sub]

    def create_block(self, shape=None, pos=None, rest=None, density=None, friction=None, poly_type=None,
                     set_sprite=False, draw_static=True, size=None, static=False, draw=None, sq_points=False,
                     foreground=False, force_static_block=False):
        """
        Create the block object

        :param shape: list of points
        :param pos: pos to insert object
        :param static: Is static or dynamic
        :param rest: Restitution Bool or float 0-1
        :param density:  density Bool  or int (0-100)
        :param friction:  friction Bool or float 0-1
        :return:
        """

        # if shape is in two points then transform
        if sq_points:
            poly = get_poly_from_two_rectangle_points(shape[0], shape[-1])
            coords = poly.exterior.coords
            pos = (poly.centroid.x, poly.centroid.y)
            shape = [(int(co[0] - pos[0]), int(co[1] - pos[1])) for co in coords]

        shapes = []

        # clone best
        if size is None:
            size = self.get_rand_val("blocks", "size")
        if rest is None:
            rest = self.get_rand_val("blocks", "rest")
        if density is None:
            density = self.get_rand_val("blocks", "density")
        if friction is None:
            friction = self.get_rand_val("blocks", "friction")

        # get the type

        if poly_type is None:
            types = [1, 2, 3, 4]
            player_options = [k for k, v in self.options["blocks_out"]["player_type"].items() if v == True]
            poly_type = random.choice(
                [list(self.options["blocks_out"]["player_type"].keys()).index(x) + 1 for x in player_options])

        # get the shape of the item

        if shape is None:
            if poly_type == 2:
                shape = int(size / 2)
            elif poly_type == 1:
                size_half = int(size / 2)
                shape = [[-size_half, -size_half], [-size_half, size_half], [size_half, size_half],
                         [size_half, -size_half]]


            elif poly_type == 3:
                shape = [[0, 0], [0, int(size * (random.randint(50, 150) / 100))],
                         [int(size * (random.randint(50, 150) / 100)), int(size * (random.randint(50, 150) / 100))],
                         [int(size * (random.randint(50, 150) / 100)), 0]]

            elif poly_type == 4:

                shape = [[0, -int(size / 2)], [-size / 2, size / 2], [size / 2, size / 2]]

        if not type(shape) == int and not type(shape) == float:
            for x, y in shape:
                xN, yN = convert_to_mks(x, y)
                shapes.append(b2Vec2(xN, yN))

        # get positon of the spawn point
        if pos is None:
            pos = (int(self.width * self.get_rand_val("blocks_out", "start_pos_x")),
                   int(self.height * self.get_rand_val("blocks_out", "start_pos_y")))

        position = convert_to_mks(pos[0], pos[1])

        if static == True or (poly_type in [-1, -2]):
            if force_static_block:
                create_type = self.world.CreateStaticBody
            else:
                create_type = self.world.CreateKinematicBody

        else:
            create_type = self.world.CreateDynamicBody

        # if boarder etc
        if poly_type == -1:

            try:
                self.block_list.append(
                    Block(create_type(position=position,
                                      fixtures=b2FixtureDef(
                                          shape=b2PolygonShape(vertices=shapes),
                                          density=size)),
                          set_sprite=set_sprite, draw_static=draw_static, poly_type=poly_type)

                )
                self.block_list[-1].body.fixtures[0].restitution = self.options["static_blocks"]["rest"]
                self.block_list[-1].body.fixtures[0].friction = self.options["static_blocks"]["friction"]
            except AssertionError as e:
                print("Poly creation error, check me")
                # for when blocks are too small
                return False

        # if boarder etc
        if poly_type == -2:
            try:
                rad = convert_to_mks(shape)
                self.block_list.append(
                    Block(create_type(position=position,
                                      fixtures=b2FixtureDef(
                                          shape=b2CircleShape(radius=rad),
                                          density=density))
                          , set_sprite=set_sprite, poly_type=poly_type, static_shape=True)
                )
            except AssertionError:
                print("circle creation error, check me")
                # for when blocks are too small
                return False

            self.block_list[-1].body.fixtures[0].restitution = self.options["static_blocks"]["rest"]
            self.block_list[-1].body.fixtures[0].friction = self.options["static_blocks"]["friction"]


        # if dynamic polygon
        elif poly_type == 1 or poly_type == 3 or poly_type == 4:
            try:
                # try creating block
                self.block_list.append(
                    Block(create_type(position=position,
                                      fixtures=b2FixtureDef(
                                          shape=b2PolygonShape(vertices=shapes),
                                          density=density))
                          , False, set_sprite=set_sprite, poly_type=poly_type)
                )

                # check if config says to set sprite and load if so
                if self.options["squares"]["sprite_on"]:
                    self.block_list[-1].sprite = self.options["squares"]["sprite"]
                    self.block_list[-1].set_sprite()

            except AssertionError as e:
                print("poly creation error, check me")
                # for when blocks are too small
                return False

        # if circle
        elif poly_type == 2:

            try:
                # try creating block
                rad = convert_to_mks(shape)
                self.block_list.append(
                    Block(create_type(position=position,
                                      fixtures=b2FixtureDef(
                                          shape=b2CircleShape(radius=rad),
                                          density=density))
                          , set_sprite=set_sprite, poly_type=poly_type)
                )
                # check if config says to set sprite and load if so
                if self.options["squares"]["sprite_on"]:
                    self.block_list[-1].sprite = self.options["squares"]["sprite"]
                    self.block_list[-1].set_sprite()

            except AssertionError:
                print("circle creation error, check me")
                # for when blocks are too small
                return False

        block = self.block_list[-1]
        if force_static_block:
            block.is_terrain = True
            block.body.awake = False

        block.body.fixtures[0].restitution = rest
        block.body.fixtures[0].density = density
        block.body.fixtures[0].friction = friction
        block.body.fixedRotation = self.options["blocks_out"]["fixed_rotation"]

        if foreground:
            block.foreground = True
            block.body.fixtures[0].sensor = True

        block.static = static
        block.board = self.board
        block.get_current_pos()

        return True

    def merge_blocks(self, bl_list=None, is_terrain=False):

        if bl_list is None:
            bls = [bl for bl in self.block_list if bl.is_terrain]
        else:
            bls = bl_list

        base_bl = bls.pop(0)

        base_center = base_bl.body.position

        for i in np.arange(len(bls) - 1, -1, -1):
            bl = bls[i]
            for fix in bl.body.fixtures:
                if type(fix.shape) == b2PolygonShape:
                    shape = fix.shape.vertices
                    poly = Polygon(shape)
                    shape = list(rt(poly, bl.body.angle, use_radians=True).exterior.coords)

                    center = bl.body.position
                    trans = (center - base_center) * -1
                    new_shape = [b2Vec2(s) - trans for s in shape]
                    base_bl.body.CreateFixture(b2FixtureDef(shape=b2PolygonShape(vertices=new_shape),
                                                            restitution=bl.body.fixtures[0].restitution,
                                                            density=bl.body.fixtures[0].density,
                                                            friction=bl.body.fixtures[0].friction))
                else:
                    radius = fix.shape.radius
                    center = bl.body.position
                    trans = (base_center - center) * -1
                    # trans[0] = trans[0] * -1
                    base_bl.body.CreateFixture(b2FixtureDef(shape=b2CircleShape(radius=radius, pos=trans),
                                                            restitution=bl.body.fixtures[0].restitution,
                                                            density=bl.body.fixtures[0].density,
                                                            friction=bl.body.fixtures[0].friction))
            self.delete(bl)

        if is_terrain:
            base_bl.poly = base_bl.get_poly()

    def re_add_size(self, bl, sizes):
        for fix, old_shape in zip(bl.body.fixtures, sizes):
            if type(old_shape) != float:
                fix.shape.vertices = old_shape
            else:
                fix.shape.radius = old_shape

    def check_sensor_actions(self):
        # loop as a range as new blocks could be created then it would also split thoes possbily
        blocks_length = len(self.block_list) - 1

        for i in range(blocks_length, -1, -1):
            bl = self.block_list[i]

            userData = bl.body.userData
            if userData["bullet_actions"] == "hit":
                if self.options["player"]["bullet_fragment"]:
                    if bl.type < 0:
                        convert = True
                    else:
                        convert = False
                    self.fractal_block(bl, False, convert=True)
                else:
                    self.delete(bl)

            elif userData["bullet_actions"] == "kill":
                self.delete(bl)

            remove_positions = []
            for i, act in enumerate(userData["actions"]):

                sensor = [bl for bl in self.block_list if bl.id == act["id"]]
                if len(sensor) == 0:
                    remove_positions.append(i)
                    break
                else:
                    sensor = sensor[0]

                contains_poly = sensor.get_poly().contains(bl.get_poly())

                # action for switching gravity
                if act["type"] == "gravity" and act["complete"] is False:
                    if (contains_poly and act["fire_action_once_contained"]) or not act["fire_action_once_contained"]:
                        bl.body.gravityScale *= -1
                        act["complete"] = True
                        if act["reverse_keys"]:
                            for k, v in bl.keys.items():
                                for act in v:
                                    try:
                                        if type(act["extra"]) in [float, int]:
                                            act["extra"] *= -1
                                        elif type(act["extra"]) in [list, tuple]:
                                            act["extra"] = np.array(act["extra"]) * -1
                                        else:
                                            pass
                                    except ValueError:
                                        # error setting value
                                        pass

                if act["type"] == "center" and act["complete"] is False:
                    if (contains_poly and act["fire_action_once_contained"]) or not act["fire_action_once_contained"]:

                        bl.center_me = True
                        bl.death_actions["return_translation"] =  act["translation"]
                        if not act["allow_multiple_fires"]:
                            act["complete"] = True

                if act["type"] == "impulse" and act["complete"] is False:
                    if (contains_poly and act["fire_action_once_contained"]) or not act["fire_action_once_contained"]:

                        bl.body.ApplyLinearImpulse((np.array(act["vector"]) * bl.body.mass) * 2, bl.body.worldCenter,
                                                   wake=True)
                        if not act["allow_multiple_fires"]:
                            act["complete"] = True

                if act["type"] == "force" and act["complete"] is False:
                    if (contains_poly and act["fire_action_once_contained"]) or not act["fire_action_once_contained"]:
                        bl.body.ApplyForce((np.array(act["vector"]) * bl.body.mass) * 2, bl.body.worldCenter,
                                           wake=True)

                        if not act["allow_multiple_fires"]:
                            act["complete"] = True

                # action for Water
                if act["type"] == "water" and act["complete"] is False:

                    sensor = [bl for bl in self.block_list if bl.id == act["id"]]
                    if len(sensor) > 0:
                        sensor = sensor[0]
                        bl_poly = bl.get_poly(4)
                        sensor_poly = sensor.get_poly(4)
                        intersection = sensor_poly.intersection(bl_poly)
                        if type(intersection) is MultiPolygon:
                            intersection = intersection.convex_hull

                        int_area = convert_to_mks(intersection.area) / 42.5
                        if int_area > 0:
                            int_centroid = convert_to_mks(intersection.centroid.x, intersection.centroid.y)
                            water_density = bl.body.fixtures[0].density
                            displaced_mass = water_density * int_area
                            buoyancy_force = displaced_mass * -np.array(self.gravity)

                            bl.body.ApplyForce(buoyancy_force, int_centroid, wake=True)
                            coords = list(intersection.exterior.coords)

                            for i in range(len(coords) - 1):
                                v0 = b2Vec2(convert_to_mks(coords[i][0], coords[i][1]))
                                v1 = b2Vec2(convert_to_mks(coords[i + 1][0], coords[i + 1][1]))
                                mid = 0.5 * (v0 + v1)
                                velDir = b2Vec2(bl.body.GetLinearVelocityFromWorldPoint(
                                    mid) - sensor.body.GetLinearVelocityFromWorldPoint(mid))
                                vel = velDir.Normalize()
                                edge = b2Vec2(v1 - v0)
                                edgeLength = b2Vec2(edge).Normalize()
                                normal = b2Vec2(b2Cross(-1, edge))
                                dragDot = b2Dot(normal, velDir)
                                if dragDot > 0:
                                    dragMag = dragDot * edgeLength * water_density * vel * vel
                                    dragForce = dragMag * -velDir
                                    bl.body.ApplyForce(dragForce, mid, wake=True)

                                    # lift for moving objects
                                    liftDot = b2Dot(edge, velDir);
                                    liftMag = (dragDot * liftDot) * edgeLength * water_density * vel * vel
                                    liftDir = b2Vec2(b2Cross(1, velDir))
                                    liftForce = b2Vec2(liftMag * liftDir)
                                    bl.body.ApplyForce(liftForce, mid, wake=True);

                            angularDrag = int_area * -bl.body.angularVelocity
                            bl.body.ApplyTorque(angularDrag, wake=True)
                    else:
                        pass
                # action for switching gravity to low (almost water like)
                if act["type"] == "lowgravity" and act["complete"] == False:
                    if (contains_poly and act["fire_action_once_contained"]) or not act["fire_action_once_contained"]:
                        bl.body.gravityScale = act["scale"]
                        act["complete"] = True

                # action for switching gravity to normal
                if act["type"] == "lowgravity" and act["complete"] == "switch":

                    bl.body.gravityScale = 1
                    remove_positions.append(i)

                # splitter sensor action
                if act["type"] == "splitter" and act["complete"] == False:
                    if (contains_poly and act["fire_action_once_contained"]) or not act["fire_action_once_contained"]:
                        if bl.get_poly(4).area > float(act["min_split_area"]):
                            self.fractal_block(bl, create=False, static=False)
                            if not act["allow_multiple_fires"]:
                                act["complete"] = True

                # action for shrink,enlarge
                if act["type"] in ["enlarger", "shrinker"] and act["complete"] == False:
                    if (contains_poly and act["fire_action_once_contained"]) or not act["fire_action_once_contained"]:
                        old_shapes = []
                        for fix in bl.body.fixtures:
                            if type(fix.shape) is b2PolygonShape:
                                old_vert = fix.shape.vertices
                                old_shapes.append(fix.shape.vertices)
                                new_poly = affinity.scale(Polygon(fix.shape.vertices),
                                                          act["enlarge_ratio"] if act["type"] == "enlarger" else 1 - act[
                                                              "shrink_ratio"],
                                                          act["enlarge_ratio"] if act["type"] == "enlarger" else 1 - act[
                                                              "shrink_ratio"])
                                if new_poly.area > convert_to_mks(0.5):
                                    fix.shape.vertices = list(new_poly.exterior.coords)
                                area = new_poly.area
                            else:
                                old_shapes.append(fix.shape.radius)
                                fix.shape.radius *= act["enlarge_ratio"] if act["type"] == "enlarger" else 1 - act[
                                    "shrink_ratio"]
                                if fix.shape.radius < convert_to_mks(4):
                                    fix.shape.radius = convert_to_mks(4)

                        if not act["allow_multiple_fires"]:
                            act["complete"] = True
                        if "min_area" in act.keys() and bl.get_poly(4).area < float(act["min_area"]):
                            self.re_add_size(bl, old_shapes)
                        if "max_area" in act.keys() and bl.get_poly(4).area > float(act["max_area"]):
                            self.re_add_size(bl, old_shapes)

                # sensor for switching motor
                if act["type"] == "motorsw" and act["complete"] == False:
                    if act["id_to_switch"] == "":
                        bl_check = bl
                    else:
                        bl_check = [bl for bl in self.block_list if bl.id == act["id_to_switch"]][0]

                    for jn in bl_check.body.joints:
                        if hasattr(jn.joint, "motorSpeed"):
                            jn.joint.motorSpeed *= -1

                    act["complete"] = True

            # remove not needed actions
            for i in np.arange(len(remove_positions) - 1, -1, -1):
                del userData["actions"][i]

    def check_board_translation(self):
        # check if the board needs translating -
        if self.board.x_trans_do == "up":
            self.board.translation[0] += 4
        elif self.board.x_trans_do == "down":
            self.board.translation[0] -= 4

        if self.board.y_trans_do == "up":
            self.board.translation[1] += 4
        elif self.board.y_trans_do == "down":
            self.board.translation[1] -= 4

    def check_sleep_status(self, bl):
        # check if the blocks need to sleep or not
        if not bl.is_onscreen:
            if self.options["off_screen"]["sleep_off_screen"]:
                bl.body.awake = False
                bl.onscreen_status["force_awake"] = True
            if self.options["off_screen"]["alive_off_screen"]:
                bl.body.alive = False
                bl.onscreen_status["force_alive"] = True
        else:
            if bl.onscreen_status["force_awake"]:
                bl.onscreen_status["force_awake"] = False
                bl.body.awake = True
            if bl.onscreen_status["force_alive"]:
                bl.onscreen_status["force_alive"] = False
                bl.body.alive = True

    def check_player_translation(self):

        if self.block_list != []:
            # get all positions
            for bl in self.block_list:
                bl.get_current_pos()
                self.check_sleep_status(bl)

            # get player translation if needed
            block = [bl for bl in self.block_list if bl.center_me]

            if block != []:
                block = block[0]

                max_x = max([max([y[0] for y in x]) for x in block.translated_position])
                max_y = max([max([y[1] for y in x]) for x in block.translated_position])
                min_x = min([min([y[0] for y in x]) for x in block.translated_position])
                min_y = min([min([y[1] for y in x]) for x in block.translated_position])

                if min_x < self.board.board.shape[1] * .35:
                    self.board.translation[0] += int((self.board.board.shape[1] * .35) - min_x)
                elif max_x > self.board.board.shape[1] * .65:
                    self.board.translation[0] -= int(max_x - (self.board.board.shape[1] * .65))

                if min_y < self.board.board.shape[0] * .35:
                    self.board.translation[1] += int((self.board.board.shape[0] * .35) - min_y)
                elif max_y > self.board.board.shape[0] * .65:
                    self.board.translation[1] -= int(max_y - (self.board.board.shape[0] * .65))

    def draw_blocks(self, ground_only=False, ground=False):
        """
        Dray all blocks
        :param board: np array
        :return:
        """

        # check if the coord translation needs doing
        self.check_board_translation()
        self.check_player_translation()

        # split sensors and blocks
        background = [bl for bl in self.block_list if bl.background]
        blocks = [bl for bl in self.block_list if not bl.background and not bl.foreground]
        foreground = [bl for bl in self.block_list if bl.foreground]

        if self.force_draw_all:
            for bl in background:
                bl.draw()
            for bl in blocks:
                bl.draw()
            for bl in foreground:
                bl.draw()
            return
        else:
            for bl in background:
                if bl.force_draw:
                    bl.draw()
            for bl in blocks:
                if bl.force_draw:
                    bl.draw()
            for bl in foreground:
                if bl.force_draw:
                    bl.draw()

    def draw_joints(self):
        for jn in self.world.joints:
            if type(jn) == b2WeldJoint or type(jn) == b2RevoluteJoint:
                an = convert_from_mks(jn.anchorA)
                col = self.board.palette.current_palette[self.board.palette.point]

                self.board.board_copy = cv2.circle(self.board.board_copy,
                                                   tuple(np.array([int(x) for x in an]) + self.board.translation), 1,
                                                   col, -1)
            elif type(jn) == b2PulleyJoint:
                col = self.board.palette.current_palette[self.board.palette.joint]
                startA = convert_from_mks(jn.anchorA.x, jn.anchorA.y)
                endA = convert_from_mks(jn.groundAnchorA.x, jn.groundAnchorA.y)

                startB = convert_from_mks(jn.anchorB.x, jn.anchorB.y)
                endB = convert_from_mks(jn.groundAnchorB.x, jn.groundAnchorB.y)

                self.board.board_copy = cv2.line(self.board.board_copy,
                                                 tuple(np.array([int(x) for x in startA]) + self.board.translation),
                                                 tuple(np.array([int(x) for x in endA]) + self.board.translation), col,
                                                 2)
                self.board.board_copy = cv2.line(self.board.board_copy,
                                                 tuple(np.array([int(x) for x in startB]) + self.board.translation),
                                                 tuple(np.array([int(x) for x in endB]) + self.board.translation), col,
                                                 2)

            else:
                if type(jn) == b2RopeJoint:
                    col = self.board.palette.current_palette[self.board.palette.rope]
                else:
                    col = self.board.palette.current_palette[self.board.palette.rope]

                start = convert_from_mks(jn.anchorA.x, jn.anchorA.y)
                end = convert_from_mks(jn.anchorB.x, jn.anchorB.y)

                try:
                    self.board.board_copy = cv2.line(self.board.board_copy,
                                                 tuple(np.array([int(x) for x in start]) + self.board.translation),
                                                 tuple(np.array([int(x) for x in end]) + self.board.translation), col,
                                                 2)
                except:
                    pass
    def create_weld_joint(self, a, b, pos, convert=True):

        self.world.CreateWeldJoint(bodyA=a.body,
                                   bodyB=b.body,
                                   anchor=(convert_to_mks(pos[0], pos[1]) if convert else pos))

        b.body.active = True
        b.body.awake = True
        a.body.active = True
        a.body.awake = True

        self.world.joints[-1].userData = {
            "id": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))}
    def create_rotation_joint(self, a, b, pos, convert=True):

        self.world.CreateRevoluteJoint(bodyA=a.body,
                                       bodyB=b.body,
                                       anchor=(convert_to_mks(pos[0], pos[1]) if convert else pos))
        b.body.active = True
        b.body.awake = True
        a.body.active = True
        a.body.awake = True

        self.world.joints[-1].userData = {
            "id": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))}
        self.world.joints[-1].userData["old_lower_upper"] = self.world.joints[-1].limits
        self.world.joints[-1].userData["key"] = None
        self.world.joints[-1].userData["current_position"] =  self.world.joints[-1].angle
        self.world.joints[-1].userData["times_allowed"] = 3

    def create_mouse_joint(self, a, x, y):

        if len(self.world.bodies) < 2:
            print("Mouse joint creation error - must have 2+ bodies created)")
            return

        if self.world.bodies[0] == a.body:
            bod = self.world.bodies[1]
        else:
            bod = self.world.bodies[0]

        self.world.CreateMouseJoint(bodyA=bod,
                                    bodyB=a.body,
                                    target=convert_to_mks(x, y),
                                    maxForce=1000.0 * a.body.mass)
        a.body.active = True
        a.body.awake = True

        self.world.joints[-1].userData = {
            "id": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))}

    def create_prismatic(self, a, b, vector, anchor, distance,convert=True):

        if convert:
            anchor = convert_to_mks(anchor[0], anchor[1])

        self.world.CreatePrismaticJoint(bodyA=a.body, bodyB=b.body, anchor=anchor,
                                        axis=vector, enableLimit=True, upperTranslation=convert_to_mks(distance))

        b.body.active = True
        b.body.awake = True
        a.body.active = True
        a.body.awake = True
        self.world.joints[-1].userData = {
            "id": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15)),"vector":(vector[0],vector[1])}
        self.world.joints[-1].userData["old_lower_upper"] = self.world.joints[-1].limits
        self.world.joints[-1].userData["key"] = None
        self.world.joints[-1].userData["current_position"] =  self.world.joints[-1].translation
        self.world.joints[-1].userData["times_allowed"] = 3

    def create_pulley(self, a, b, lines):
        lines = [convert_to_mks(x[0], x[1]) for x in lines]
        self.world.CreatePulleyJoint(bodyA=a.body,
                                     bodyB=b.body,
                                     groundAnchorA=lines[1],
                                     groundAnchorB=lines[3],
                                     anchorA=lines[0],
                                     anchorB=lines[2],
                                     ratio=1)
        # maxLengthA=calculateDistance(lines[0][0], lines[0][1], lines[1][0], lines[1][1]),
        # maxLengthB=calculateDistance(lines[2][0], lines[2][1], lines[3][0], lines[3][1]))
        b.body.active = True
        b.body.awake = True
        a.body.active = True
        a.body.awake = True
        self.world.joints[-1].userData = {
            "id": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))}
        self.world.joints[-1].userData["old_lower_upper"] = self.world.joints[-1].limits
        self.world.joints[-1].userData["key"] = None
        self.world.joints[-1].userData["times_allowed"] = 3

    def create_chain(self, a, b, lines, stretchy=False):
        last_ob = 0
        end = False

        ###FROM STACKOVERFLOW
        ## https://stackoverflow.com/questions/62990029/how-to-get-equally-spaced-points-on-a-line-in-shapely/62994304#62994304
        line = LineString(lines)
        line = line.simplify(2)
        # or to get the distances closest to the desired one:
        # n = round(line.length / desired_distance_delta)

        distance_delta = 25
        distances = np.arange(0, line.length, distance_delta)
        points = [line.interpolate(distance) for distance in distances]
        # multipoint = unary_union(points)
        lines_new = [(int(p.x), int(p.y)) for p in points]
        first_block = None
        for i in np.arange(0, len(lines_new)):

            do_joint = True

            line1 = np.array(lines_new[i])

            if i != len(lines_new) - 1:
                line2 = np.array(lines_new[i + 1])
                angle = np.deg2rad(get_angle(line1, line2))
                # angle = get_angle(line1, line2)
                shape = [[-15, -2], [15, -2], [15, 2], [-15, 2]]
                self.create_block(pos=np.mean([line1, line2], axis=0), draw=True, shape=shape, poly_type=1, density=1,
                                  friction=0.1, rest=0)
                if first_block is None:
                    first_block = self.block_list[-1]
                self.block_list[-1].body.angle = angle

            if i == 0:
                if a is None:
                    do_joint = False
                else:
                    blockA = a.body

            else:
                # on last block select the last else select the second from last
                blockA = self.block_list[-1 if i == len(lines_new) - 1 else -2].body

            # if end rung of rope then select bodyB as the last block else normal last block
            if i >= len(lines_new) - 1:
                if b is None:
                    if calculateDistance(lines_new[-1][0], lines_new[-1][1], lines_new[0][0], lines_new[0][1]) < 15:
                        blockB = first_block.body
                    else:
                        do_joint = False
                else:
                    blockB = b.body
                    end = True
            else:
                blockB = self.block_list[-1].body

            if do_joint:
                self.world.CreateRevoluteJoint(bodyA=blockA,
                                               bodyB=blockB,
                                               anchor=convert_to_mks(line1[0], line1[1]),
                                               collideConnected=False)
                b.body.active = True
                b.body.awake = True
                a.body.active = True
                a.body.awake = True
                # self.world.CreateDistanceJoint(bodyA=blockA,
                # bodyB=blockB,
                # anchorA=convert_to_mks(center_point[0], center_point[1]),
                # anchorB=convert_to_mks(center_point[0], center_point[1]),
                # collideConnected=False)
                # self.world.joints[-1].frequencyHz = 1/20
                # self.world.joints[-1].frequency = 1 / 20
                # self.world.joints[-1].dampingRatio = 2

            if end:
                return

    def create_chainish_joint(self, a, b, lines, stretchy=False):
        last_ob = 0
        end = False

        ###FROM STACKOVERFLOW
        ## https://stackoverflow.com/questions/62990029/how-to-get-equally-spaced-points-on-a-line-in-shapely/62994304#62994304
        line = LineString(lines)
        line = line.simplify(1)
        # or to get the distances closest to the desired one:
        # n = round(line.length / desired_distance_delta)
        distances = np.linspace(0, line.length, int(line.length / 2))
        # or alternatively without NumPy:
        # distances = (line.length * i / (n - 1) for i in range(n))
        points = [line.interpolate(distance) for distance in distances]
        multipoint = unary_union(points)
        lines_new = [(int(p.x), int(p.y)) for p in multipoint]

        # lines_new = [[int(co[0]), int(co[1])] for co in get_enlongated_line(lines)]

        for i in np.arange(0, len(lines_new) - 1, step=1):
            pos = lines_new[i]
            last_ob += 1

            self.create_block(pos=pos, draw=True, size=3, poly_type=1, density=2, friction=0.1, rest=0)

            if i == 0:
                blockA = a.body
            else:
                blockA = self.block_list[-2].body

            if i >= len(lines_new) - 2:
                blockB = b.body
                end = True
            else:
                blockB = self.block_list[-1].body

            self.world.CreateRevoluteJoint(bodyA=blockA,
                                           bodyB=blockB,
                                           anchor=((blockA.worldCenter.x + blockB.worldCenter.x) / 2,
                                                   (blockA.worldCenter.y + blockB.worldCenter.y) / 2))
            b.body.active = True
            b.body.awake = True
            a.body.active = True
            a.body.awake = True
            if end:
                return

    def create_lightening_joint(self, a, b, lines, stretchy=False):
        last_ob = 0
        end = False

        ###FROM STACKOVERFLOW
        ## https://stackoverflow.com/questions/62990029/how-to-get-equally-spaced-points-on-a-line-in-shapely/62994304#62994304
        line = LineString(lines)
        line = line.simplify(1)
        # or to get the distances closest to the desired one:
        # n = round(line.length / desired_distance_delta)
        distances = np.linspace(0, line.length, int(line.length / 3))
        # or alternatively without NumPy:
        # distances = (line.length * i / (n - 1) for i in range(n))
        points = [line.interpolate(distance) for distance in distances]
        multipoint = unary_union(points)
        lines_new = [(int(p.x), int(p.y)) for p in multipoint]

        # lines_new = [[int(co[0]), int(co[1])] for co in get_enlongated_line(lines)]

        for i in np.arange(0, len(lines_new) - 1, step=1):
            pos = lines_new[i]
            last_ob += 1

            self.create_block(pos=pos, draw=False, size=2, poly_type=1, density=0, friction=0.1, rest=0)

            if i == 0:
                blockA = a.body
            else:
                blockA = self.block_list[-2].body

            if i >= len(lines_new) - 2:
                blockB = b.body
                end = True
            else:
                blockB = self.block_list[-1].body

            dist = calculateDistance(blockA.worldCenter.x, blockA.worldCenter.y, blockB.worldCenter.x,
                                     blockB.worldCenter.y)

            self.world.CreateDistanceJoint(bodyA=blockA,
                                           bodyB=blockB,
                                           anchorA=blockA.worldCenter if i != 0 else convert_to_mks(lines[0][0],
                                                                                                    lines[0][1]),
                                           anchorB=blockB.worldCenter if i != len(lines_new) - 2 else convert_to_mks(
                                               lines[-1][0], lines[-1][1]),
                                           collideConnected=False)
            b.body.active = True
            b.body.awake = True
            a.body.active = True
            a.body.awake = True

            self.world.joints[-1].frequency = 50000
            self.world.joints[-1].frequencyHz = 50000
            self.world.joints[-1].dampingRatio = 0

            if end:
                return

    def create_distance_joint(self, a, b, aAnchor, bAnchor, convert=True):

        if convert:
            aAnchor = convert_to_mks(aAnchor[0], aAnchor[1])
            bAnchor = convert_to_mks(bAnchor[0], bAnchor[1])

        self.world.CreateDistanceJoint(bodyA=a.body,
                                       bodyB=b.body,
                                       anchorA=aAnchor,
                                       anchorB=bAnchor,
                                       collideConnected=True)

        self.world.joints[-1].userData = {
            "id": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))}

    def create_rope_joint(self, a, b, aAnchor, bAnchor, maxLength, convert=True):

        if convert:
            maxLength = convert_to_mks(maxLength)
            aAnchor = convert_to_mks(aAnchor[0], aAnchor[1])
            bAnchor = convert_to_mks(bAnchor[0], bAnchor[1])

        self.world.CreateRopeJoint(bodyA=a.body,
                                   bodyB=b.body,
                                   anchorA=aAnchor,
                                   anchorB=bAnchor,
                                   maxLength=maxLength,
                                   collideConnected=True)

        self.world.joints[-1].userData = {
            "id": ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))}

    def delete(self, bl):
        # destroy joints

        for k,v in bl.death_actions.items():
            if k == "return_translation":
                trans = [x.replace("[","").replace("]","").replace(",","") for x in v.split(" ")]
                self.board.translation = [int(x) for x in trans if x != ""]

        for i, joint in enumerate(bl.body.joints):

            self.world.DestroyJoint(joint.joint)
            try:
                self.world.DestroyJoint(joint)
            except:
                pass

            del joint
            gc.collect(0)

        # destroy bodies

        del self.block_list[self.block_list.index(bl)]

        # remove from the keys move list if found.

        self.world.DestroyBody(bl.body)

        if not self.draw.player_list == []:
            if bl in self.draw.player_list:
                del self.draw.player_list[self.draw.player_list.index(bl)]

        del bl

        gc.collect(0)

    def check_off(self):
        """
        Used to check if any of all the non static blocks are off the screen
        if they are then remove them

        """

        # kill blocks that have hit the boundry
        for i in np.arange(len(self.block_list) - 1, -1, -1):
            bl = self.block_list[i]
            if bl.body.userData["kill"]:
                self.delete(bl)

        # old code now uses boundries
        # goals = 0
        # h, w, _ = board.board_copy.shape
        #
        # for bl in self.block_list:
        #     if bl.current_position != [] and bl.static == False:
        #
        #         x = [x[0] for x in bl.current_position]
        #         y = [x[1] for x in bl.current_position]
        #
        #         if max(x) < 0:
        #             bl.active = False
        #             bl.times_off += 1
        #         if min(x) > w:
        #             bl.active = False
        #             bl.times_off += 1
        #         if min(y) > h:
        #             bl.active = False
        #             bl.times_off += 1
        #
        #         if bl.active is False and bl.times_off > 2:
        #             self.delete(bl)

        # delete hit goal items
        goals = 0

        for bl in self.block_list:
            if bl.body.userData["goal"] == "reset":
                self.board.reset = True
            elif bl.body.userData["goal"] == "delete":
                self.delete(bl)

        return goals


class _Base_Block():

    def __init__(self, body, static_shape=False, set_sprite=False, sprite=None, draw_static=True, poly_type=None):
        self.body = body
        self.body.userData = {"ob": self, "joints": [], "impulses": [], "forces": [], "goal": False, "actions": [],
                              "player_allow_impulse": True, "bullet_actions": None, "bullets_destory_ground": False,
                              "kill": False, "ground_touches": 0, "sensor_touch_id": []}
        self.type = poly_type

        self.static = static_shape
        self.board = None

        self.center = None
        self.poly = None
        self.pos = None
        self.current_position = []
        self.translated_position = []

        self.force_draw = True

        self.sensor = {"type": None}

        self.foreground = False
        self.background = False

        self.bullet = False
        self.bullet_creator = None

        self.centroid = None

        self.sprite = sprite
        self.mask = None
        self.inv_mask = None
        self.sprite_on = False
        self.is_player = False
        self.center_me = False
        self.is_boundry = False
        self.is_terrain = False
        self.can_fire = False
        self.is_player = False
        self.is_onscreen = True
        self.onscreen_status = {"force_awake": False, "force_alive": False}

        self.death_actions = {}

        if set_sprite:
            self.set_sprite()

        if poly_type < 0:
            self.colour = 10
        else:
            self.colour = random.choice([0, 1, 2, 4, 5, 14])

        self.active = True

        self.id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))
        self.base_id = ''

        self.keys = {}

        self.old_id = None

    def __str__(self):
        str = f"active: {self.active} col: {self.colour} id: {self.id} old_id: {self.old_id} static: {self.static} \n"
        for x in self.body.joints:
            str += f"Joint: {type(x.joint)} bodyA id {x.joint.bodyA.userData['ob'].id} oldId {x.joint.bodyA.userData['ob'].old_id} bodyB id {x.joint.bodyB.userData['ob'].id} oldId {x.joint.bodyB.userData['ob'].old_id}\n"

        return str

    def set_mass(self):

        density = sum([fix.density for fix in self.body.fixtures])
        poly = self.get_poly(4)
        self.body.mass = convert_to_mks(poly.area) / 45 * density

    def add_move(self, key, type, extra,id=None):
        """
        Used to add keys and actions to be fired on keypress

        :param key:
        :param id:
        :param type:
        :param extra:
        :return:
        """

        if key in self.keys:
            self.keys[key].append(
                {"type": type, "extra": extra, "multiplier": 1, "limit_x_speed": False, "limit_y_speed": False,
                 "enforce_ground_touch": False, "toggle_allowed": False, "toggle_status": False,"cancel_rotation":False,"cancel_velocity":False,
                 "hold_motor_in_place":False, "id": id})
        else:
            self.keys[key] = [
                {"type": type, "extra": extra, "multiplier": 1, "limit_x_speed": False, "limit_y_speed": False,
                 "enforce_ground_touch": False, "toggle_allowed": False, "toggle_status": False, "cancel_rotation":False,"cancel_velocity":False,
                  "hold_motor_in_place":False, "id": id}]

    def get_poly(self, rad=5):

        # if static block or terrain then poly is already set as un moveable.
        # if not self.poly is None:
        #    return self.poly

        polys = []
        for fix, pos in zip(self.body.fixtures, self.current_position):
            if type(fix.shape) == b2PolygonShape:
                polys.append(Polygon(pos))
            elif type(fix.shape) == b2CircleShape:
                # if circle get poly
                pos = pos.squeeze()
                polygon = Point(pos[0], pos[1])
                rad = 5
                polys.append(polygon.buffer(convert_from_mks(fix.shape.radius), rad))
            else:
                pass

        poly = unary_union(polys)
        if not type(poly) == Polygon:
            poly = poly.convex_hull

        return poly

    def set_as_bullet(self, vector, id, destroy_ground):
        self.sensor["type"] = "bullet"
        self.sensor["data"] = id

        # set the block as a bullet for colision detection

        self.colour = (255, 17, 0)
        # set as a sensor
        self.body.fixtures[0].sensor = True
        self.body.userData["bullets_destory_ground"] = destroy_ground
        # turn off the gravity so it just keeps going with no effect on the physics
        self.body.gravityScale = 0

        # impulse the bullet
        self.body.ApplyLinearImpulse(vector * self.body.mass, self.body.worldCenter, wake=True)
        self.body.bullet = True
        # stop rotation
        self.body.fixedRotation = True

    def get_current_pos(self):

        self.translated_position = []
        self.current_position = []
        poly = []
        for i, fix in enumerate(self.body.fixtures):
            if type(fix.shape) == b2PolygonShape:
                shapes = [(self.body.transform * v) for v in fix.shape.vertices]
                shapes = [(convert_from_mks(val[0], val[1])) for val in shapes]
                self.translated_position.append(np.array(shapes) + self.board.translation)
                self.current_position.append(np.array(shapes))
                self.poly = Polygon(self.translated_position[i])
                self.centroid = (self.poly.centroid.x, self.poly.centroid.y)
            else:
                # for circles add center
                shape = self.body.transform * fix.shape.pos
                shape = [convert_from_mks(shape[0], shape[1])]
                self.translated_position.append(np.array(shape) + self.board.translation)
                self.current_position.append(np.array(shape))
                self.poly = Polygon(np.array(self.get_poly(3).exterior.coords) + self.board.translation)
                self.centroid = self.translated_position[0].squeeze()

        center = (self.body.transform * self.body.localCenter)
        self.center = convert_from_mks(center.x, center.y)

        # on screen?
        if max([max([y[0] for y in x]) if len(x) != 2 else x[0] for x in self.translated_position]) < 0 or min(
                [min([y[0] for y in x]) if len(x) != 2 else x[0] for x in self.translated_position]) > \
                self.board.board.shape[1]:
            self.is_onscreen = False
        elif max([max([y[1] for y in x]) if len(x) != 2 else x[0] for x in self.translated_position]) < 0 or min(
                [min([y[1] for y in x]) if len(x) != 2 else x[0] for x in self.translated_position]) > \
                self.board.board.shape[0]:
            self.is_onscreen = False
        else:
            self.is_onscreen = True

    def set_height_width(self):
        coords = list(self.get_poly(4).exterior.coords)
        widthMax = max([x[0] for x in coords])
        widthMin = min([x[0] for x in coords])
        heightMax = max([x[1] for x in coords])
        heightMin = min([x[1] for x in coords])
        self.height = heightMax - heightMin
        self.width = widthMax - widthMin

    def set_sprite(self, force=False):
        if not self.sprite is None:
            try:
                img = cv2.imread(self.sprite, -1)
                if random.randint(1, 2) == 1:
                    img = img[:, ::-1]

                if not force:
                    coords = list(self.get_poly(4).exterior.coords)
                    widthMax = max([x[0] for x in coords])
                    widthMin = min([x[0] for x in coords])
                    heightMax = max([x[1] for x in coords])
                    heightMin = min([x[1] for x in coords])
                    self.height = heightMax - heightMin
                    self.width = widthMax - widthMin

                    self.sprite = cv2.resize(img, (int(self.width), int(self.height)))

                if self.sprite.shape[2] == 4:
                    mask = self.sprite[:, :, 3] / 255
                    self.mask = np.stack([mask, mask, mask]).transpose([1, 2, 0])
                    self.sprite = self.sprite[:, :, :3][:, :, ::-1]
                else:
                    self.mask = np.ones(self.sprite.shape)

                self.inv_mask = 1 - self.mask.copy()
                self.sprite_on = True
            except:
                print("Error reading sprite image file")

    def draw(self, force_draw=True):

        if self.is_onscreen:
            if self.sprite_on and type(self.sprite) != None:

                center = self.centroid

                degrees = np.rad2deg(self.body.angle * -1)

                if degrees != 0:
                    sprite = rotate(self.sprite.copy().astype(np.uint8), int(degrees), reshape=True)
                    mask = rotate(self.mask.copy(), int(degrees), reshape=True, mode="constant", cval=0)

                    sprite = sprite * mask

                else:
                    sprite = self.sprite.copy()
                    mask = self.mask.copy()

                # get shape
                height, width, _ = sprite.shape
                x_start = int(center[0] - (width / 2))
                y_start = int(center[1] - (height / 2))
                x_end = int(x_start + (width))
                y_end = int(y_start + (height))

                # if out of bounds return not drawn
                if y_start > self.board.board_copy.shape[0] or x_start > self.board.board_copy.shape[
                    1] or x_end < 0 or y_end < 0:
                    return board

                if y_start < 0:
                    val = abs(y_start)
                    sprite = sprite[val:, :]
                    mask = mask[val:, :]
                    y_start = 0

                if x_start < 0:
                    val = abs(x_start)
                    sprite = sprite[:, val:]
                    mask = mask[:, val:]
                    x_start = 0

                if y_end > self.board.board_copy.shape[0]:
                    val = abs(y_end - self.board.board_copy.shape[0])
                    sprite = sprite[:sprite.shape[0] - val, :]
                    mask = mask[:sprite.shape[0], :]
                    y_end = self.board.board_copy.shape[0]

                if x_end > self.board.board_copy.shape[1]:
                    val = abs(x_end - self.board.board_copy.shape[1])
                    sprite = sprite[:, :sprite.shape[1] - val]
                    mask = mask[:, :sprite.shape[1]]
                    x_end = self.board.board_copy.shape[1]

                self.board.board_copy[y_start:y_end, x_start:x_end, :] = (self.board.board_copy[y_start:y_end,
                                                                          x_start:x_end,
                                                                          :] * (1 - mask)) + sprite
                # board[y_start:y_end, x_start:x_end] = board[y_start:y_end, x_start:x_end] * (1 - mask) + (img * mask)
            else:
                if type(self.colour) is tuple or type(self.colour) is list:
                    colour = self.colour
                else:
                    colour = self.board.palette.current_palette[self.colour]
                for pos, fix in zip(self.translated_position, self.body.fixtures):
                    if type(fix.shape) == b2PolygonShape:
                        self.board.board_copy = cv2.fillConvexPoly(self.board.board_copy, pos.astype(np.int32), colour)
                    else:
                        self.board.board_copy = cv2.circle(self.board.board_copy,
                                                           tuple([int(x) for x in pos.squeeze()]),
                                                           int(convert_from_mks(fix.shape.radius)),
                                                           colour,
                                                           thickness=-1)

        return self.board


class Block(_Base_Block):

    def __init__(self, body, static_shape=False, set_sprite=False, sprite=None, draw_static=True, poly_type=None):
        super().__init__(body, static_shape=static_shape, set_sprite=set_sprite, sprite=sprite, draw_static=draw_static,
                         poly_type=poly_type)


class Board():

    def __init__(self):
        self.board_name = None
        self.board = None
        self.board_front = None
        self.board_copy = None
        self.run = True
        self.palette = None
        self.reset = False
        self.translation = np.array([0, 0])
        self.x_trans_do = None
        self.y_trans_do = None
        self.b_height = None
        self.b_width = None

    def reset_me(self, timer, phys, board, draw, msg, force=False):
        if self.reset or force:
            if self.board_name == "base":
                timer, phys, board, draw, msg = load(self.board.shape[0], self.board.shape[1])
                phys.config = config
            else:
                timer, phys, draw, board, msg, blurb = load_state(self.board_name)
                phys.config = config

        return timer, phys, board, draw, msg

    def copy_board(self):
        self.board_copy = self.board.copy()

    def load_blank(self, x, y):
        "Used for a blank board"
        self.board = np.zeros((y, x, 3), dtype=np.uint8)

    def load_blocks(self, back=None, middle=None, front=None, phys=None, draw=False, block_accuracy=0.1, width=None,
                    height=None):
        if width is None:
            width = 800
        if height is None:
            height = 600

        # get Background
        if type(back) is str:
            self.board = cv2.imread(back)[:, :, ::-1]
        elif type(back) is type(None):
            self.board = None
        else:
            self.board = back[:, :, ::-1]

        if type(front) is str:
            self.board_front = cv2.imread(front, -1)
        elif type(front) is type(None):
            self.board_front = None
        else:
            self.board_front = front

        if not self.board_front is None:
            self.board_front_mask = (self.board_front[:, :, 3] / 255)
            self.board_front_mask = np.stack(
                [self.board_front_mask, self.board_front_mask, self.board_front_mask]).transpose([1, 2, 0])
            self.board_front_conv = (self.board_front[:, :, :3] * self.board_front_mask)  # .astype(np.uint8)
            self.board_front_conv = self.board_front_conv[:, :, ::-1]
            self.board_front_mask_inv = 1 - self.board_front_mask

        # get blocks
        if type(middle) is str:
            blocks = cv2.imread(middle)
        elif type(middle) is type(None):
            blocks = None
        else:
            blocks = middle

        if sum([1 for x in [blocks, self.board] if not x is None]) > 0:
            if not blocks is None:
                self.blocks = blocks

                if self.board is None:
                    self.board = np.zeros((self.blocks.shape[0], self.blocks.shape[1], 3))

                imgray = cv2.cvtColor(self.blocks[:, :, ::-1], cv2.COLOR_BGR2GRAY)
                contours, hierarchy = cv2.findContours(imgray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                contours = sorted(contours, key=cv2.contourArea)
                if len(contours) > 1:
                    if (self.board.shape[0] * self.board.shape[1]) * .9 < cv2.contourArea(contours[-1]):
                        contours = contours[:-1]

                    final_contours = []
                    for cnt in contours:
                        epsilon = block_accuracy * cv2.arcLength(cnt, True)
                        approx = cv2.approxPolyDP(cnt, epsilon, True, True)
                        if len(approx) > 1:
                            conts = constrained_delaunay_triangles([tuple(x) for x in approx.squeeze()])

                            for cn in conts:
                                phys.create_block(cn, (0, 0), draw_static=draw)
                                final_contours.append(cn)
        else:
            self.board = np.zeros((height, width, 3), dtype=np.uint8)

        return phys

    def draw_front(self):
        if not self.board_front is None:
            self.board_copy = ((self.board_copy * self.board_front_mask_inv) + self.board_front_conv).astype(np.uint8)


class Timer:

    def __init__(self, fps):
        self.time_start = datetime.datetime.now()
        self.last_time = datetime.datetime.now()
        self.time_now = datetime.datetime.now()

        self.times = 0
        self.fps = fps
        self.time_per_frame = 1 / fps

    def log(self):
        self.times += 1
        self.last_time = self.time_now
        self.time_now = datetime.datetime.now()
        if (self.time_now - self.last_time).total_seconds() < self.time_per_frame:
            time.sleep(self.time_per_frame - (self.time_now - self.last_time).total_seconds())


class Messenger:
    def __init__(self, fps, board):

        self.old_message = None
        self.message = None
        self.board = board
        self.load_pannel()
        self.goal_hits = 0

    def load_pannel(self):
        self.pannel = np.zeros((30, self.board.board.shape[1], 3), dtype=np.uint8)
        self.pannel[:, :] = (123, 123, 123)
        self.pannel[2:-2, 2:-2] = (170, 170, 170)
        self.pannel[2:-2, -105:-4] = (210, 210, 210)
        self.display_pannel_pause = self.pannel.copy()

    def auto_set(self, options, key, force):
        messages = [k for k, v in options.items()]
        types = [v for k, v in options.items()]
        keys = [chr(key) + ty.value for ty in types]

        if force:
            self.old_message = self.message
        elif not self.old_message in messages:
            self.old_message = None

        if self.old_message == None:
            index = 0
        else:
            index = messages.index(self.old_message) + (1 if not force else 0)
            if index > len(messages) - 1:
                index = 0
        self.set_message(messages[index], set_old=True)
        return keys[index]

    def set_message(self, message, sub_message=None, set_old=False):
        if set_old:
            self.old_message = message
        else:
            self.old_message = None

        self.message = message
        self.display_pannel_pause = self.pannel.copy()

        self.display_pannel_pause = cv2.putText(self.display_pannel_pause, message, (5, 22), cv2.FONT_HERSHEY_SIMPLEX,
                                                0.75, (135, 135, 135), 2,
                                                bottomLeftOrigin=False)
        self.display_pannel_pause = cv2.putText(self.display_pannel_pause, message, (5, 22), cv2.FONT_HERSHEY_SIMPLEX,
                                                0.75, (50, 50, 50), 1,
                                                bottomLeftOrigin=False)

        if not sub_message is None:
            self.display_pannel_pause = cv2.putText(self.display_pannel_pause, sub_message, (300, 22),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (135, 135, 135), 2,
                                                    bottomLeftOrigin=False)
            self.display_pannel_pause = cv2.putText(self.display_pannel_pause, sub_message, (300, 22),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 50, 50), 1,
                                                    bottomLeftOrigin=False)

    def draw_message(self, pause):
        self.display_pannel = cv2.putText(self.display_pannel_pause.copy(),
                                          ("Pause Off" if pause == True else "Pause On"),
                                          (self.board.board_copy.shape[1] - 100, 20),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                                          (50, 50, 50), 1, bottomLeftOrigin=False)

        self.board.board_copy = np.vstack((self.board.board_copy, self.display_pannel))


class Contacter(b2ContactListener):

    def __init__(self):
        b2ContactListener.__init__(self)

    def get_sensor_block(self, contact):

        # check if objects have the correct user data
        if "ob" in contact.fixtureA.body.userData.keys():
            blockA = contact.fixtureA.body.userData["ob"]
        else:
            return None, None

        if "ob" in contact.fixtureB.body.userData.keys():
            blockB = contact.fixtureB.body.userData["ob"]
        else:
            return None, None

        sensor = None
        block = None

        if not blockA.sensor["type"] is None and blockB.sensor["type"] is None:
            sensor = blockA
            block = blockB
        elif not blockB.sensor["type"] is None and blockA.sensor["type"] is None:
            sensor = blockB
            block = blockA
        elif blockB.static is True and blockA.sensor["type"] is None:
            sensor = blockB
            block = blockA
        elif blockA.static is True and blockB.sensor["type"] is None:
            sensor = blockB
            block = blockA
        elif blockB.is_boundry is True and blockA.sensor["type"] is None:
            sensor = blockB
            block = blockA
        elif blockA.is_boundry is True and blockB.sensor["type"] is None:
            sensor = blockB
            block = blockA

        elif blockB.sensor["type"] == "bullet" and blockA.sensor["type"] is None:
            sensor = blockB
            block = blockA
        elif blockA.sensor["type"] == "bullet" and blockB.sensor["type"] is None:
            sensor = blockB
            block = blockA

        if sensor is None or block is None:
            return None, None
        else:
            return sensor, block

    def BeginContact(self, contact):

        ## log sensor and block
        ## log sensor and block

        sensor, block = self.get_sensor_block(contact)

        if sensor is None or block is None:
            return

        # if floor touches
        if sensor.static:
            block.body.userData["ground_touches"] += 1

        block.body.userData["sensor_touch_id"].append(sensor.id)

        ## log sensor touches
        ## log sensor touches

        # impulse or force
        if sensor.sensor["type"] in ["force", "impulse"]:

            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "vector": sensor.sensor["options"]["vector"],
                     "allow_multiple_fires": sensor.sensor["options"]["allow_multiple_fires"],
                     "fire_action_once_contained": sensor.sensor["options"]["fire_action_once_contained"]})

        # goal
        if sensor.sensor["type"] == "goal":
            block.body.userData["goal"] = "reset" if sensor.sensor["options"][
                                                         "reset_on_player_hit"] and block.is_player else "delete"

        # if floor touches
        if sensor.static:
            block.body.userData["ground_touches"] += 1

        # is boundry
        if sensor.sensor["type"] == "boundry":
            block.body.userData["kill"] = True

        # check if gravity
        if sensor.sensor["type"] == "gravity":
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "reverse_keys": sensor.sensor["options"]["reverse_keys_on_hit"],
                     "fire_action_once_contained": sensor.sensor["options"]["fire_action_once_contained"]})

        # check if low gravity
        if sensor.sensor["type"] == "lowgravity":
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "scale": sensor.sensor["options"]["gravity_scale"],
                     "fire_action_once_contained": sensor.sensor["options"]["fire_action_once_contained"]})

        # check if motorSw
        if sensor.sensor["type"] == "motorsw":
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "id_to_switch": sensor.sensor["options"]["id_to_switch"]})

        # check if motorSw
        if sensor.sensor["type"] in ["enlarger"]:
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "allow_multiple_fires": sensor.sensor["options"]["allow_multiple_fires"],
                     "max_area": sensor.sensor["options"]["max_area"],
                     "enlarge_ratio": sensor.sensor["options"]["enlarge_ratio"],
                     "fire_action_once_contained": sensor.sensor["options"]["fire_action_once_contained"]})

        # check if motorSw
        if sensor.sensor["type"] in ["shrinker"]:
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "allow_multiple_fires": sensor.sensor["options"]["allow_multiple_fires"],
                     "min_area": sensor.sensor["options"]["min_area"],
                     "shrink_ratio": sensor.sensor["options"]["shrink_ratio"],
                     "fire_action_once_contained": sensor.sensor["options"]["fire_action_once_contained"]})

        # check if motorSw
        if sensor.sensor["type"] in ["splitter"]:
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "allow_multiple_fires": sensor.sensor["options"]["allow_multiple_fires"],
                     "min_split_area": sensor.sensor["options"]["min_split_area"],
                     "fire_action_once_contained": sensor.sensor["options"]["fire_action_once_contained"]})

        # check if motorSw
        if sensor.sensor["type"] in ["sticky"]:
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            block.body.awake = False

        # check if water
        if sensor.sensor["type"] in ["water"]:
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False})

        # check if water
        if sensor.sensor["type"] in ["center"]:
            done = sum([1 for act in block.body.userData["actions"] if act["id"] == sensor.id])
            if done == 0:
                block.body.userData["actions"].append(
                    {"type": sensor.sensor["type"], "id": sensor.id, "complete": False,
                     "allow_multiple_fires": sensor.sensor["options"]["allow_multiple_fires"],
                     "translation": sensor.sensor["options"]["translation"],
                     "fire_action_once_contained": sensor.sensor["options"]["fire_action_once_contained"]})

        # check if bullet
        if sensor.sensor["type"] == "bullet" and sensor.sensor["data"] != block.id:
            # destroy bullets on hitting object with a mass > 200 else let it keep moving
            if block.get_poly().area > 200:
                sensor.body.userData["bullet_actions"] = "kill"

            # kill blocks if hit by bullet and not static unless the options allow it
            if not block.static or sensor.body.userData["bullets_destory_ground"]:
                # print("")
                block.body.userData["bullet_actions"] = "hit"

    def PreSolve(self, contact, impulse):
        pass

    def PostSolve(self, contact, impulse):
        pass

    def EndContact(self, contact):

        sensor, block = self.get_sensor_block(contact)
        if sensor is None or block is None:
            return

        ## log sensor touches
        ## log sensor touches

        block.body.userData["sensor_touch_id"].remove(sensor.id)

        # if floor touches
        if sensor.static:
            block.body.userData["ground_touches"] -= 1

        # force
        if sensor.sensor["type"] == "force":
            block.body.userData["forces"] = []

        try:
            # check if gravity
            if sensor.sensor["type"] in ["impulse", "force", "gravity", "motorsw", "enlarger", "shrinker", "splitter",
                                         "sticky", "water","center"]:
                self.remove_action(sensor, block)

            # check if water leave
            # if sensor.sensor["type"] == "water":
            #
            #     ind = block.body.userData["actions"].index({"type":"water","id":sensor.id, "complete":True})
            #     block.body.userData["actions"][ind]["complete"] = "reverse"

            # check if lowgravity
            if sensor.sensor["type"] == "lowgravity":
                ind = block.body.userData["actions"].index({"type": "lowgravity", "id": sensor.id, "complete": True,
                                                            "scale": sensor.sensor["options"]["gravity_scale"]})
                block.body.userData["actions"][ind]["complete"] = "switch"


        except ValueError:
            # this is for when a fixeutre is added to a block
            pass

    def remove_action(self, sensor, block):
        rem_id = None
        for i, itm in enumerate(block.body.userData["actions"]):
            if itm["id"] == sensor.id:
                rem_id = i
        if not rem_id is None:
            del block.body.userData["actions"][rem_id]
