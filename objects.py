import datetime
import inspect
import random
import string
import time
import cv2
import numpy as np
from sect.triangulation import constrained_delaunay_triangles
from scipy.ndimage import rotate
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from draw_functions import get_enlongated_line, get_poly_from_two_rectangle_points
from functions import get_random_col, get_config, convert_to_mks, convert_from_mks, get_poly_from_ob, dent_contour, \
    fragment_poly, calculateDistance
import gc
from Box2D import *
import pickle
from configobj import ConfigObj

config = ConfigObj('config_default.cfg')


def load(height=600, width=800):
    """ Init """

    timer = Timer(get_config("screen", "fps"))
    board = Board()
    phys = Physics(get_config("physics", "gravity"))
    draw = Draw()
    block_accuracy = get_config("blocks", "block_accuracy")
    phys = board.load_blocks(phys=phys, block_accuracy=block_accuracy, height=height, width=width)

    phys.world.contactListener = Contacter()
    msg = Messenger(get_config("screen", "fps"), board.board)
    SCREEN_HEIGHT, SCREEN_WIDTH = board.board.shape[:2]

    phys.height = SCREEN_HEIGHT
    phys.width = SCREEN_WIDTH
    return timer, phys, board, draw, msg


def pickler(timer, phys, draw, board, msg, pickle_name):
    config = ConfigObj('config.cfg')
    pickle_dic = {"timer": timer, "board": board, "msg": msg, "config": config}
    item_list = []
    for bl in phys.block_list:
        item_list.append(phys.save_block_as_dict(bl))

    pickle_dic["blocks"] = item_list
    pickle_dic["phys"] = {k: v for k, v in phys.__dict__.items() if not "b2" in str(type(v)) and not k == "block_list"}
    pickle_dic["draw"] = {k: v for k, v in draw.__dict__.items() if not "b2" in str(type(v)) and not k == "player_list"}
    pickle.dump(pickle_dic, open("example_saves/" + pickle_name + ".save", "wb"))


def load_state(pickle_name):
    # get pickle

    if pickle_name.find("/") == -1:
        pickle_name = "example_saves/" + pickle_name

    file = open(pickle_name + ".save", 'rb')
    pickle_dic = pickle.load(file)

    config = pickle_dic["config"]
    config.write()

    timer = pickle_dic["timer"]
    board = pickle_dic["board"]
    msg = pickle_dic["msg"]

    phys = Physics(pickle_dic["phys"]["gravity"])
    for k, v in pickle_dic["phys"].items():
        if k in phys.__dict__.keys():
            phys.__dict__[k] = v

    draw = Draw()
    for k, v in pickle_dic["draw"].items():
        if k in draw.__dict__.keys():
            draw.__dict__[k] = v

    phys.create_pre_def_block(pickle_dic["blocks"], convert_joints=False)
    phys.world.contactListener = Contacter()
    phys.change_config()

    return timer, phys, draw, board, msg
    pass


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

    def log_player(self, player):
        self.pause = True
        self.player_list.append(player)

        self.coords.append(get_poly_from_ob(player, 3).exterior.coords)
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
                             "circle_draw", "line_draw", "length","bullet"]:
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

    def draw_point(self, board):
        """
        Draw arrow on the screen
        :param board:
        :return:
        """
        board = self.draw_coords(board)

        if len(self.locations) == 0:
            return board
        elif len(self.locations) == 1 and not self.status in ["wheel_draw", "wheel_move", "circle_move", "line_draw",
                                                              "double_dist", "double_dist1","bullet"]:
            board = cv2.circle(board, tuple(self.locations[0]), 2, (240, 14, 14), -1)
        elif self.status in ["double_dist", "double_dist1"] and 1 < len(self.locations) <= 3:
            board = cv2.line(board, tuple(self.locations[0]), tuple(self.locations[1]), (170, 240, 7), 3)
        elif self.status in ["double_dist1"] and len(self.locations) == 4:
            board = cv2.line(board, tuple(self.locations[0]), tuple(self.locations[1]), (170, 240, 7), 3)
            board = cv2.line(board, tuple(self.locations[2]), tuple(self.locations[3]), (170, 240, 7), 3)

        elif self.status in ["wheel_move"]:
            board = cv2.circle(board, tuple(self.locations[-1]), self.wheel_size if self.wheel_size >= 1 else 1,
                               (240, 14, 14), -1)
        elif self.status in ["wheel_draw", "circle_draw", "circle_move"]:
            board = cv2.circle(board, tuple(self.locations[0]), self.wheel_size if self.wheel_size >= 1 else 1,
                               (240, 14, 14), -1)

        elif len(self.locations) == 2 and self.status == "fire":
            # draw line for fire
            board = cv2.arrowedLine(board, tuple(self.locations[0]), tuple(self.locations[1]), (170, 240, 7), 3)
            board = cv2.arrowedLine(board, tuple(self.locations[0]), tuple(self.locations[1]), (240, 14, 14), 2)

        elif len(self.locations) >= 2 and self.status == "distance":
            board = cv2.line(board, tuple(self.locations[0]), tuple(self.locations[1]), (170, 240, 7), 3)
            board = cv2.line(board, tuple(self.locations[0]), tuple(self.locations[-1]), (240, 14, 14), 2)

        elif len(self.locations) >= 2 and self.status == "length":
            board = cv2.arrowedLine(board, tuple(self.locations[0]), tuple(self.locations[1]), (170, 240, 7), 3)
            board = cv2.arrowedLine(board, tuple(self.locations[0]), tuple(self.locations[-1]), (240, 14, 14), 2)

        elif len(self.locations) >= 2 and (self.status in ["poly", "frag"]):
            # used for drawing the rough shape of the polygon
            for i in range(len(self.locations) - 1):
                # board = cv2.line(board, tuple(self.locations[0]), tuple(self.locations[1]), (170, 240, 7), 3)
                board = cv2.line(board, tuple(self.locations[i]), tuple(self.locations[i + 1]), (240, 14, 14), 2)
        elif self.status in ["delete", "select", "rectangle_draw", "rectangle_move"]:
            board = cv2.rectangle(board, tuple([int(x) for x in self.locations[0]]),
                                  tuple([int(x) for x in self.locations[-1]]), (170, 240, 7), 3)


        elif self.status in ["line_draw"]:
            if len(self.locations) >= 2:
                for i in range(0, len(self.locations) - 2):
                    board = cv2.line(board, tuple(self.locations[0]), tuple(self.locations[1]), (170, 240, 7), 3)
                    board = cv2.line(board, tuple(self.locations[i]), tuple(self.locations[i + 1]), (240, 50, 14), 2)

        return board

    def set_distance(self, x, y):
        coord = get_poly_from_ob(self.player_list[0], 3)
        center = coord.centroid
        dist = calculateDistance(x, y, center.x, center.y)
        self.distance.append(dist)

    def draw_coords(self, board):
        # draw poly
        if not len(self.player_list) == 0:
            for block in self.player_list:
                #dont draw if player
                if not block.is_player:
                    coord = get_poly_from_ob(block, 3).exterior.coords
                    for i in range(len(coord)):
                        co1 = tuple([int(x) for x in coord[i]])
                        co2 = tuple([int(x) for x in coord[(i + 1) if i != len(coord) - 1 else 0]])
                        board = cv2.line(board, co1, co2, (170, 240, 7), 3)
                        board = cv2.line(board, co1, co2, (240, 50, 14), 2)

        return board

    def reset(self):
        self.status = None
        self.locations = []
        self.pause = False
        self.coords = []
        self.clone_created = False

        for bl in self.player_list:
            bl.sensor = False

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
        self.draw_objects = {"sensor": True, "ground": True, "blocks": True, "foreground": True}
        self.pause = False
        self.options = {}

        for k, v in config.items():
            self.options[k] = {}
            for kk, vv in config[k].items():
                self.options[k][kk] = get_config(k, kk, config)

    def impulse_player(self, key):

        player = [bl for bl in self.block_list if bl.is_player]
        vec = None
        currentDir = player[0].body.linearVelocity
        if len(player) >= 1 and key in [ord("a"), ord("w"), ord("s"), ord("d")]:

            if key == ord("a"):
                move_func = player[0].body.ApplyLinearImpulse if self.options["player"]["horizontal_impulse"] else \
                player[0].body.ApplyForce
                vec = np.array([-self.options["player"]["horizontal_strength"], currentDir.y])

            elif key == ord("w"):
                if player[0].body.userData["player_allow_impulse"] is True or not self.options["player"]["restrict_jumps"]:
                    y = -self.options["player"]["vertical_strength"]
                else:
                    y = currentDir.y
                move_func = player[0].body.ApplyLinearImpulse if self.options["player"]["vertical_impulse"] else player[0].body.ApplyForce
                vec = np.array([currentDir.x, y])

            elif key == ord("s"):
                move_func = player[0].body.ApplyLinearImpulse if self.options["player"]["vertical_impulse"] else player[
                    0].body.ApplyForce
                vec = np.array([currentDir.x, self.options["player"]["vertical_strength"] if self.options["player"][
                    "allow_downward_movement"] else 0])


            elif key == ord("d"):
                move_func = player[0].body.ApplyLinearImpulse if self.options["player"]["horizontal_impulse"] else \
                player[0].body.ApplyForce
                vec = np.array([self.options["player"]["horizontal_strength"], currentDir.y])

            if not vec is None:
                if self.options["player"]["restrict_speed"]:
                    vec[0] = vec[0] - player[0].body.linearVelocity.x

                vec = vec * player[0].body.mass

                move_func(vec, player[0].body.worldCenter, wake=True)
            else:
                print("Player impulse error")

    def change_config(self, config=None):
        if config is None:
            config = ConfigObj('config.cfg')
        for k, v in config.items():
            self.options[k] = {}
            for kk, vv in config[k].items():
                if k in self.options.keys():
                    self.options[k][kk] = get_config(k, kk, config)
                    if kk == "gravity":
                        grav_val = get_config(k, kk, config)
                        self.world.gravity = b2Vec2(grav_val[0], grav_val[1])

    def kill_all(self, static=True):
        for i in np.arange(len(self.block_list) - 1, -1, -1):
            block = self.block_list[i]
            if static:
                self.delete(block)
            else:
                if not block.static:
                    self.delete(block)

    def save_block_as_dict(self, block):

        """
        used to split the block into a dict of information for pickling
        :param block:
        :return:
        """

        # get main block information
        block_dic = {k: v for k, v in block.__dict__.items() if not "b2" in str(type(v))}

        if block.type == 2 or block.type == -2:
            block_dic["shape"] = block.radius
            block_dic["draw_static"] = True
        else:
            block_dic["shape"] = block.shape
            block_dic["draw_static"] = block.draw_static

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

        mas_dic = {"mass": block.body.massData.mass,
                   "I": block.body.massData.I,
                   "center": [block.body.massData.center.x, block.body.massData.center.y],
                   }

        fixtures_dic = {"restitution": block.body.fixtures[0].restitution,
                        "sensor": block.body.fixtures[0].sensor,
                        "friction": block.body.fixtures[0].friction,
                        "density": block.body.fixtures[0].density}

        all_joints = {}
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
                    joints_dic["bodyA"] = joint.joint.bodyA.userData["ob"].id
                elif attr is "bodyB" and hasattr(joint.joint, "bodyB"):
                    joints_dic["bodyB"] = joint.joint.bodyB.userData["ob"].id
                elif attr is "groundAnchorA" and hasattr(joint.joint, "groundAnchorA"):
                    joints_dic["groundAnchorA"] = joint.joint.groundAnchorA.userData["ob"].id
                elif attr is "groundAnchorB" and hasattr(joint.joint, "groundAnchorB"):
                    joints_dic["groundAnchorB"] = joint.joint.groundAnchorA.userData["ob"].id
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

            all_joints[i] = joints_dic

        return {"block": block_dic, "body": body_dic, "mass": mas_dic, "fixtures": fixtures_dic, "joints": all_joints}

    def create_pre_def_block(self, info, convert_joints=True):

        new_obs = 0
        # loop and create each item again
        for block_info in info:

            new_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))

            if (block_info["block"]["type"] in [-1, -2]):
                create_type = self.world.CreateKinematicBody
            else:
                create_type = self.world.CreateDynamicBody

            # create Object
            if block_info["block"]["type"] in [1, -1, 3]:
                shape = [convert_to_mks(x[0], x[1]) for x in block_info["block"]["shape"]]
                self.block_list.append(
                    Block(create_type(position=block_info["body"]["position"],
                                      fixtures=b2FixtureDef(
                                          shape=b2PolygonShape(vertices=shape),
                                          density=block_info["fixtures"]["density"])),
                          set_sprite=False, draw_static=block_info["block"]["draw_static"])

                )

            # if circle
            else:
                rad = convert_to_mks(block_info["block"]["shape"])

                self.block_list.append(
                    Ball(create_type(position=block_info["body"]["position"],
                                     fixtures=b2FixtureDef(
                                         shape=b2CircleShape(radius=rad),
                                         density=block_info["fixtures"]["density"]))
                         , set_sprite=False))

            # get current block and add settings
            block = self.block_list[-1]

            # set block details
            for k, v in block_info["block"].items():
                if hasattr(block, k):
                    setattr(block, k, v)

            # reseize sprite

            if not block.sprite is None:
                if block_info["block"]["type"] in [-1, 1, 3]:
                    block.sprite = cv2.resize(block.sprite, dsize=(int(block.width), int(block.height)))
                    block.mask = cv2.resize(block.mask, dsize=(int(block.width), int(block.height)))
                    block.inv_mask = cv2.resize(block.inv_mask, dsize=(int(block.width), int(block.height)))
                else:
                    block.sprite = cv2.resize(block.sprite, (int(block.radius * 2), int(block.radius * 2)))
                    block.mask = cv2.resize(block.mask, (int(block.radius * 2), int(block.radius * 2)))
                    block.inv_mask = cv2.resize(block.inv_mask, (int(block.radius * 2), int(block.radius * 2)))

            # not needed any more!!
            # if block.sprite_on and not type(block.sprite) is None:
            #     block.set_sprite(force=True)

            block.id = new_id
            block.old_id = block_info["block"]["id"]

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
                if hasattr(block.body.fixtures[0], k):
                    if type(v) == list and len(v) == 2:
                        setattr(block.body.fixtures[0], k, b2Vec2(v[0], v[1]))
                    else:
                        setattr(block.body.fixtures[0], k, v)

            new_obs += 1

        # get individual joints
        joints = [x["joints"] for x in info]
        i = 0
        new_joints = {}
        for joint in joints:
            for k, v in joint.items():
                if v not in new_joints.values():
                    new_joints[i] = v
                    i += 1
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
                    else:
                        print("help")

                    # loop the sorted values and update
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

        return new_obs

    def get_block_by_id(self, id):

        blocks = [bl for bl in self.block_list if bl.old_id == id]
        if blocks != []:
            return blocks[-1]
        else:
            for bl in self.block_list:
                if bl.id == id:
                    return bl

    def fractal_split(self, block, allow_another=True):

        if not type(block) == list:
            block = [block]

        for bl in block:

            body_dic = {"inertia": bl.body.inertia,
                        "linearVelocity": [bl.body.linearVelocity.x, bl.body.linearVelocity.y],
                        "awake": bl.body.awake,
                        "gravityScale": bl.body.gravityScale,
                        "active": bl.body.active,
                        "angularVelocity": bl.body.angularVelocity}

            poly = get_poly_from_ob(bl, 4)
            shape = list(poly.exterior.coords)[:-1]

            if len(shape) <= 4:
                shape = dent_contour(shape)
            conts = fragment_poly(shape)

            for con in conts:
                poly = Polygon(con)
                new_con = [(int(x[0] - poly.centroid.x), int(x[1] - poly.centroid.y)) for x in con]

                if bl.static:
                    # complete.append(not create_block(pos=(poly.centroid.x,poly.centroid.y), forc=0, out=0, player=1, shape=con))
                    self.create_block(pos=(poly.centroid.x, poly.centroid.y), poly_type=-1, shape=new_con)
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

    def fractal_create(self, shape, static=True):

        shape = shape[:-1]
        if len(shape) <= 4:
            shape = dent_contour(shape)
        conts = fragment_poly(shape)

        for con in conts:
            poly = Polygon(con)
            new_con = [(int(x[0] - poly.centroid.x), int(x[1] - poly.centroid.y)) for x in con]
            if not static:
                # complete.append(not create_block(pos=(poly.centroid.x,poly.centroid.y), forc=0, out=0, player=1, shape=con))
                self.create_block(pos=(poly.centroid.x, poly.centroid.y), poly_type=1, shape=new_con)
            else:
                self.create_block(pos=(poly.centroid.x, poly.centroid.y), poly_type=-1, shape=new_con,
                                  draw_static=True)

    def fractal_block(self, ob, create=True, static=True, allow_another=True):
        if create is True:
            self.fractal_create(ob, static)
        elif create is False:
            self.fractal_split(ob, allow_another=allow_another)

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
                     foreground=False):
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
            types = [1, 2, 3]
            player_options = [k for k, v in self.options["blocks_out"]["player_type"].items() if v == True]
            poly_type = random.choice([types[i] for i, x in enumerate(player_options)])

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
                    Ball(create_type(position=position,
                                     fixtures=b2FixtureDef(
                                         shape=b2CircleShape(radius=rad),
                                         density=density))
                         , set_sprite=set_sprite, poly_type=poly_type)
                )
            except AssertionError:
                print("circle creation error, check me")
                # for when blocks are too small
                return False

            self.block_list[-1].body.fixtures[0].restitution = self.options["static_blocks"]["rest"]
            self.block_list[-1].body.fixtures[0].friction = self.options["static_blocks"]["friction"]

        # if dynamic polygon
        elif poly_type == 1 or poly_type == 3:
            try:
                # shape = [(x[0] + position[0],x[1]+ position[1]) for x in shapes]

                self.block_list.append(
                    Block(create_type(position=position,
                                      fixtures=b2FixtureDef(
                                          shape=b2PolygonShape(vertices=shapes),
                                          density=density))
                          , False, set_sprite=set_sprite, poly_type=poly_type)
                )
            except AssertionError as e:
                print("poly creation error, check me")
                # for when blocks are too small
                return False

        # if circle
        elif poly_type == 2:
            try:
                rad = convert_to_mks(shape)
                self.block_list.append(
                    Ball(create_type(position=position,
                                     fixtures=b2FixtureDef(
                                         shape=b2CircleShape(radius=rad),
                                         density=density))
                         , set_sprite=set_sprite, poly_type=poly_type)
                )
            except AssertionError:
                print("circle creation error, check me")
                # for when blocks are too small
                return False

        self.block_list[-1].body.fixtures[0].restitution = rest
        self.block_list[-1].body.fixtures[0].density = density
        self.block_list[-1].body.fixtures[0].friction = friction
        self.block_list[-1].draw_me = draw

        if foreground:
            self.block_list[-1].foreground = True
            self.block_list[-1].body.fixtures[0].sensor = True

        return True

    def check_sensor_actions(self):
        # loop as a range as new blocks could be created then it would also split thoes possbily
        blocks_length = len(self.block_list) - 1
        for bl in self.block_list:
            bl.boost_block()

        for i in range(blocks_length, -1, -1):
            bl = self.block_list[i]
            if bl.body.userData["bullet_actions"] == "hit":
                if self.options["player"]["bullet_fragment"]:
                    self.fractal_block(bl, False)
                else:
                    self.delete(bl)

            elif bl.body.userData["bullet_actions"] == "kill":
                self.delete(bl)

    def draw_blocks(self, board, ground_only=False, ground=False):
        """
        Dray all blocks
        :param board: np array
        :return:
        """

        # split sensors and blocks
        floor = [bl for bl in self.block_list if
                 bl.body.fixtures[0].sensor is False and bl.static is True]  # and not bl.force_draw is True)]
        sensor_blocks = [bl for bl in self.block_list if bl.body.fixtures[0].sensor == True and bl.foreground == False]
        player = [bl for bl in self.block_list if bl.is_player is True]
        foreground = [bl for bl in self.block_list if bl.body.fixtures[0].sensor == True and bl.foreground == True]

        # and not bl.force_draw is True)]
        blocks = [bl for bl in self.block_list if
                  bl not in sensor_blocks and bl not in floor and bl not in foreground and bl not in player]  # and not bl.force_draw is True)]

        if self.draw_objects["ground"]:
            for bl in floor:
                board = bl.draw(board)
        else:
            for bl in floor:
                if bl.force_draw:
                    board = bl.draw(board)

        if self.draw_objects["sensor"]:
            for bl in sensor_blocks:
                board = bl.draw(board)
        else:
            for bl in sensor_blocks:
                if bl.force_draw:
                    board = bl.draw(board)
                # this was too slow
                # board_overlay = board.copy()
                # board_overlay = bl.draw(board)
                # alpha = 0.2
                # board = cv2.addWeighted(board_overlay, alpha, board, 1 - alpha, 0)

        if self.draw_objects["blocks"]:
            # draw blocks undernear
            for bl in blocks:
                board = bl.draw(board)
            for bl in player:
                board = bl.draw(board)
        else:
            for bl in blocks:
                if bl.force_draw:
                    board = bl.draw(board)

            for bl in player:
                if bl.force_draw:
                    board = bl.draw(board)

        if "foreground" not in self.draw_objects:
            self.draw_objects["foreground"] = True

        if self.draw_objects["foreground"]:
            # draw blocks undernear
            for bl in foreground:
                board = bl.draw(board)
        else:
            for bl in foreground:
                if bl.force_draw:
                    board = bl.draw(board)

        return board

    def draw_joints(self, board):
        for jn in self.world.joints:
            if type(jn) == b2WeldJoint or type(jn) == b2RevoluteJoint:
                an = convert_from_mks(jn.anchorA)
                if type(jn) == b2WeldJoint:
                    col = (233, 23, 100)
                else:
                    col = (150, 23, 240)

                board = cv2.circle(board, tuple([int(x) for x in an]), 1, col, -1)
            elif type(jn) == b2PulleyJoint:
                col = (50, 214, 4)
                startA = convert_from_mks(jn.anchorA.x, jn.anchorA.y)
                endA = convert_from_mks(jn.groundAnchorA.x, jn.groundAnchorA.y)

                startB = convert_from_mks(jn.anchorB.x, jn.anchorB.y)
                endB = convert_from_mks(jn.groundAnchorB.x, jn.groundAnchorB.y)

                board = cv2.line(board, tuple([int(x) for x in startA]), tuple([int(x) for x in endA]), col, 2)
                board = cv2.line(board, tuple([int(x) for x in startB]), tuple([int(x) for x in endB]), col, 2)

            else:
                if type(jn) == b2RopeJoint:
                    col = (23, 233, 123)
                else:
                    col = (50, 200, 110)

                start = convert_from_mks(jn.anchorA.x, jn.anchorA.y)
                end = convert_from_mks(jn.anchorB.x, jn.anchorB.y)

                board = cv2.line(board, tuple([int(x) for x in start]), tuple([int(x) for x in end]), col, 2)

        return board

    def create_weld_joint(self, a, b, pos, convert=True):

        self.world.CreateWeldJoint(bodyA=a.body,
                                   bodyB=b.body,
                                   anchor=(convert_to_mks(pos[0], pos[1]) if convert else pos))

    def create_rotation_joint(self, a, b, pos, convert=True):

        self.world.CreateRevoluteJoint(bodyA=a.body,
                                       bodyB=b.body,
                                       anchor=(convert_to_mks(pos[0], pos[1]) if convert else pos))

        pass

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

    def create_chain(self, a, b, lines, stretchy=False):
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

    def delete(self, bl):
        # destroy joints

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
        self.world.DestroyBody(bl.body)
        del bl
        gc.collect(0)

    def check_off(self, board):
        """
        Used to check if any of all the non static blocks are off the screen
        if they are then remove them

        """
        goals = 0
        h, w, _ = board.shape

        for bl in self.block_list:
            if bl.current_position != [] and bl.static == False:
                x = [x[0] for x in bl.current_position]
                y = [x[1] for x in bl.current_position]

                if max(x) < 0:
                    bl.active = False
                    bl.times_off += 1
                if min(x) > w:
                    bl.active = False
                    bl.times_off += 1
                if min(y) > h:
                    bl.active = False
                    bl.times_off += 1

                if bl.active is False and bl.times_off > 2:
                    self.delete(bl)

        # delete hit goal items
        for bl in self.block_list:
            if bl.body.userData["goal"] == True:
                goals += 1
                self.delete(bl)
        return goals


class Ball():

    def __init__(self, body, set_sprite=False, sprite=None, draw=True, poly_type=None):
        self.body = body
        self.body.userData = {"ob": self, "joints": [], "impulses": [], "forces": [], "goal": False, "player_allow_impulse": True, "bullet_actions":None}
        self.type = poly_type
        self.pos = None
        self.current_position = []
        self.colour = get_random_col()
        self.active = True
        self.center = None
        self.radius = int(convert_from_mks(self.body.fixtures[0].shape.radius))
        self.static = False
        self.times_off = 0
        self.old_id = None
        self.force_draw = draw

        self.foreground = False
        self.booster = None
        self.goal = False
        self.splitter = False
        self.forcer = None

        self.bullet = False
        self.bullet_creator = None

        self.id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))
        self.sprite = sprite
        self.mask = None
        self.inv_mask = None
        self.sprite_on = False
        if set_sprite is True:
            self.set_sprite()

        self.is_player = False

    def __str__(self):

        str = f"active: {self.active} col: {self.colour} id: {self.id} old_id: {self.old_id} static: {self.static} \n"
        for x in self.body.joints:
            str += f"Joint: {type(x.joint)} bodyA id {x.joint.bodyA.userData['ob'].id} oldId {x.joint.bodyA.userData['ob'].old_id} bodyB id {x.joint.bodyB.userData['ob'].id} oldId {x.joint.bodyB.userData['ob'].old_id}\n"

        return str

    def get_poly(self):
        return get_poly_from_ob(self,3)

    def get_current_pos(self):
        self.center = convert_from_mks((self.body.transform * self.body.localCenter).x,
                                       (self.body.transform * self.body.localCenter).y)
        self.current_position = [self.center]

    def set_sprite(self, force=False):
        if not self.sprite is None:
            try:

                if not force:
                    img = cv2.imread(self.sprite, -1)
                    self.sprite = cv2.resize(img, (int(self.radius * 2), int(self.radius * 2)))

                mask = self.sprite[:, :, 3] / 255

                self.mask = np.stack([mask, mask, mask]).transpose([1, 2, 0])
                inv_mask = 1 - mask.copy()
                self.inv_mask = np.stack([inv_mask, inv_mask, inv_mask]).transpose([1, 2, 0])

                self.sprite = self.sprite[:, :, :3] * self.mask
                self.sprite = self.sprite[:, :, ::-1]
                self.sprite_on = True
            except:
                self.sprite = None
                print("Error reading sprite image file")

    def boost_block(self):

        for impul in self.body.userData["impulses"]:
            self.body.ApplyLinearImpulse((np.array(impul) * self.body.mass) * 2, self.body.worldCenter, wake=True)

        for force in self.body.userData["forces"]:
            self.body.ApplyForce((np.array(force) * self.body.mass) * 2, self.body.worldCenter, wake=True)

        self.body.userData["impulses"] = []
        self.body.userData["forces"] = []

    def draw(self, board, force_draw=False):

        self.get_current_pos()

        if self.sprite_on and type(self.sprite) != None:

            degrees = np.rad2deg(self.body.angle)
            if degrees != 0:
                sprite = rotate(self.sprite.copy().astype(np.uint8), int(degrees * -1), reshape=False)
            else:
                sprite = self.sprite.copy()

            mask = self.inv_mask.copy()

            # x_start = int(self.center[0]) - self.radius
            # y_start = int(self.center[1]) - self.radius
            # x_end = x_start + (self.radius*2)
            # y_end = y_start + (self.radius*2)

            # get shape
            height, width, _ = sprite.shape
            x_start = int(self.center[0] - int(width / 2))
            y_start = int(self.center[1] - int(height / 2))
            x_end = int(x_start + (width))
            y_end = int(y_start + (height))

            # if out of bounds return not drawn
            if y_start > board.shape[0] or x_start > board.shape[1] or x_end < 0 or y_end < 0:
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

            if y_end > board.shape[0]:
                val = abs(y_end - board.shape[0])
                sprite = sprite[:sprite.shape[0] - val, :]
                mask = mask[:sprite.shape[0], :]
                y_end = board.shape[0]

            if x_end > board.shape[1]:
                val = abs(x_end - board.shape[1])
                sprite = sprite[:, :sprite.shape[1] - val]
                mask = mask[:, :sprite.shape[1]]
                x_end = board.shape[1]

            board[y_start:y_end, x_start:x_end, :] = (board[y_start:y_end, x_start:x_end, :] * mask) + sprite
            # board[y_start:y_end, x_start:x_end] = board[y_start:y_end, x_start:x_end] * (1 - mask) + (img * mask)
        else:
            try:
                board = cv2.circle(board, tuple([int(x) for x in self.center]), int(self.radius), self.colour,
                                   thickness=-1)  # .astype(np.uint8)
            except cv2.error:
                # error in drawing circle size
                print("Circle draw error")
                pass
        if self.is_player:
            board = cv2.circle(board, tuple([int(x) for x in self.center]), int(self.radius), (143, 255, 145),
                               thickness=2)
        return board


class Block():

    def __init__(self, body, static_shape=True, set_sprite=False, sprite=None, draw_static=True, poly_type=None):
        self.body = body
        self.body.userData = {"ob": self, "joints": [], "impulses": [], "forces": [], "goal": False, "player_allow_impulse": True, "bullet_actions":None}
        self.type = poly_type
        self.pos = None
        self.current_position = []

        self.static = static_shape

        self.shape = [convert_from_mks(x, y) for x, y in self.body.fixtures[0].shape.vertices]
        self.width = round(max([x[0] for x in self.shape])) + abs(round(min([x[0] for x in self.shape])))
        self.height = round(max([x[1] for x in self.shape])) + abs(round(min([x[1] for x in self.shape])))
        self.center = None

        self.draw_static = draw_static
        self.draw_me = True

        self.times_off = 0

        self.booster = None
        self.splitter = None
        self.forcer = None
        self.goal = False
        self.force_draw = False
        self.foreground = False

        self.bullet = False
        self.bullet_creator = None

        self.sprite = sprite
        self.mask = None
        self.inv_mask = None
        self.sprite_on = False
        self.is_player = False
        if set_sprite:
            self.set_sprite()

        if static_shape:
            self.colour = [234, 123, 23]
        else:
            self.colour = get_random_col()

        self.active = True

        self.id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))
        self.old_id = None

    def __str__(self):
        str = f"active: {self.active} col: {self.colour} id: {self.id} old_id: {self.old_id} static: {self.static} \n"
        for x in self.body.joints:
            str += f"Joint: {type(x.joint)} bodyA id {x.joint.bodyA.userData['ob'].id} oldId {x.joint.bodyA.userData['ob'].old_id} bodyB id {x.joint.bodyB.userData['ob'].id} oldId {x.joint.bodyB.userData['ob'].old_id}\n"

        return str
    def get_poly(self):
        return get_poly_from_ob(self,3)
    def set_as_bullet(self,vector,id):
        self.bullet_creator = id
        #set the block as a bullet for colision detection
        self.bullet = True
        self.colour = (255, 17, 0)
        #set as a sensor
        self.body.fixtures[0].sensor = True

        #turn off the gravity so it just keeps going with no effect on the physics
        self.body.gravityScale = 0

        #impulse the bullet
        if vector is None:
            vector
        try:
            self.body.ApplyLinearImpulse(vector*self.body.mass,self.body.worldCenter,wake=True)
        except:
            pass
        #stop rotation
        self.body.fixedRotation = True
    def boost_block(self):

        for impul in self.body.userData["impulses"]:
            self.body.ApplyLinearImpulse((np.array(impul) * self.body.mass) * 2, self.body.worldCenter, wake=True)

        for force in self.body.userData["forces"]:
            self.body.ApplyForce((np.array(force) * self.body.mass) * 2, self.body.worldCenter, wake=True)

        self.body.userData["impulses"] = []
        self.body.userData["forces"] = []

    def get_current_pos(self):

        shapes = [(self.body.transform * v) for v in self.body.fixtures[0].shape.vertices]
        shapes = [(convert_from_mks(val[0], val[1])) for val in shapes]
        shapes = [(v[0], v[1]) for v in shapes]
        self.current_position = np.array(shapes)
        self.center = convert_from_mks((self.body.transform * self.body.localCenter).x,
                                       (self.body.transform * self.body.localCenter).y)

    def set_sprite(self, force=False):
        if not self.sprite is None:
            try:
                img = cv2.imread(self.sprite, -1)
                if random.randint(1, 2) == 1:
                    img = img[:, ::-1]

                if not force:
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

    def draw(self, board, force_draw=True):
        if self.draw_me is False:
            return board
        elif (self.draw_static is True and self.static) or self.static is False:
            self.get_current_pos()

            if self.sprite_on and type(self.sprite) != None:

                center = self.center

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
                if y_start > board.shape[0] or x_start > board.shape[1] or x_end < 0 or y_end < 0:
                    return board

                if y_start < 0:
                    val = abs(y_start)
                    sprite = sprite[val:, :]
                    mask = mask[val:, :]
                    y_start = 0

                if x_start < 0:
                    val = abs(y_start)
                    sprite = sprite[:, val:]
                    mask = mask[:, val:]
                    x_start = 0

                if y_end > board.shape[0]:
                    val = abs(y_end - board.shape[0])
                    sprite = sprite[:sprite.shape[0] - val, :]
                    mask = mask[:sprite.shape[0], :]
                    y_end = board.shape[0]

                if x_end > board.shape[1]:
                    val = abs(x_end - board.shape[1])
                    sprite = sprite[:, :sprite.shape[1] - val]
                    mask = mask[:, :sprite.shape[1]]
                    x_end = board.shape[1]

                board[y_start:y_end, x_start:x_end, :] = (board[y_start:y_end, x_start:x_end, :] * (1 - mask)) + sprite
                # board[y_start:y_end, x_start:x_end] = board[y_start:y_end, x_start:x_end] * (1 - mask) + (img * mask)
            else:
                board = cv2.fillConvexPoly(board, self.current_position.astype(np.int32), self.colour)

            if self.is_player:
                for i in range(len(self.current_position) - 1):
                    board = cv2.line(board, tuple([int(x) for x in self.current_position[i]]),
                                     tuple([int(x) for x in self.current_position[i + 1]]), (143, 255, 145),
                                     thickness=2)

                board = cv2.line(board, tuple([int(x) for x in self.current_position[-1]]),
                                 tuple([int(x) for x in self.current_position[0]]), (143, 255, 145), thickness=2)

            return board
        else:
            return board


class Board():
    def __init__(self):
        self.board = None
        self.board_front = None
        self.run = True

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

    def draw_front(self, img):
        if not self.board_front is None:
            return ((img * self.board_front_mask_inv) + self.board_front_conv).astype(np.uint8)
        else:
            return img


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
        self.load_pannel(board)
        self.goal_hits = 0

    def load_pannel(self, board):
        self.pannel = np.zeros((30, board.shape[1], 3), dtype=np.uint8)
        self.pannel[:, :] = (123, 123, 123)
        self.pannel[2:-2, 2:-2] = (170, 170, 170)
        self.pannel[2:-2, -105:-4] = (210, 210, 210)
        self.display_pannel_pause = self.pannel.copy()

    def auto_set(self, options, key):
        messages = [k for k, v in options.items()]
        types = [v for k, v in options.items()]
        keys = [chr(key) + ty.value for ty in types]

        if not self.old_message in messages:
            self.old_message = None
        if self.old_message == None:
            index = 0
        else:
            index = messages.index(self.old_message) + 1
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

    def draw_message(self, board, pause):
        self.display_pannel = cv2.putText(self.display_pannel_pause.copy(),
                                          ("Pause Off" if pause == True else "Pause On"), (board.shape[1] - 100, 20),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                                          (50, 50, 50), 1, bottomLeftOrigin=False)

        return np.vstack((board, self.display_pannel))


class Contacter(b2ContactListener):

    def __init__(self):
        b2ContactListener.__init__(self)

    def BeginContact(self, contact):
        # booster
        if contact.fixtureA.sensor == True and contact.fixtureA.body.userData["ob"].booster != None:
            contact.fixtureB.body.userData["impulses"].append(contact.fixtureA.body.userData["ob"].booster)
            return
        if contact.fixtureB.sensor == True and contact.fixtureB.body.userData["ob"].booster != None:
            contact.fixtureA.body.userData["impulses"].append(contact.fixtureB.body.userData["ob"].booster)
            return

        # booster
        if contact.fixtureA.sensor == True and contact.fixtureA.body.userData["ob"].forcer != None:
            contact.fixtureB.body.userData["forces"].append(contact.fixtureA.body.userData["ob"].forcer)
            return
        if contact.fixtureB.sensor == True and contact.fixtureB.body.userData["ob"].forcer != None:
            contact.fixtureA.body.userData["forces"].append(contact.fixtureB.body.userData["ob"].forcer)
            return

        # goal
        if contact.fixtureA.sensor == True and contact.fixtureA.body.userData["ob"].goal == True:
            contact.fixtureB.body.userData["goal"] = True
            return
        if contact.fixtureB.sensor == True and contact.fixtureB.body.userData["ob"].goal == True:
            contact.fixtureA.body.userData["goal"] = True
            return

        # goal
        # if contact.fixtureA.sensor == True and contact.fixtureA.body.userData["ob"].splitter == True:
        #     contact.fixtureB.body.userData["split_me"]["do"] = True
        #     return
        # if contact.fixtureB.sensor == True and contact.fixtureB.body.userData["ob"].splitter == True:
        #     contact.fixtureA.body.userData["split_me"]["do"] = True
        #     return

        if "ob" in contact.fixtureA.body.userData and "ob" in contact.fixtureB.body.userData:
            #check for if off ground and allowed another jump
            if contact.fixtureA.body.userData["ob"].is_player and contact.fixtureB.body.userData["ob"].static:
                contact.fixtureA.body.userData["player_allow_impulse"] = True

            #is bullet and has hit dynamic block?
            is_bullet = contact.fixtureA.body.userData["ob"].bullet
            ignore_id = contact.fixtureA.body.userData["ob"].bullet_creator
            contact_id = contact.fixtureB.body.userData["ob"].id

            if is_bullet and ignore_id != contact_id:
                # check if small then dont destroy the bullet
                if contact.fixtureB.body.userData["ob"].get_poly().area > 200:
                    contact.fixtureA.body.userData["bullet_actions"] = "kill"

                if not contact.fixtureB.body.userData["ob"].static:
                    contact.fixtureB.body.userData["bullet_actions"] = "hit"

        if "ob" in contact.fixtureB.body.userData and "ob" in contact.fixtureA.body.userData:
            #check for if off ground and allowed another jump
            if contact.fixtureB.body.userData["ob"].is_player and contact.fixtureA.body.userData["ob"].static:
                contact.fixtureB.body.userData["player_allow_impulse"] = True

            # is bullet and has hit dynamic block?
            is_bullet = contact.fixtureB.body.userData["ob"].bullet
            ignore_id = contact.fixtureB.body.userData["ob"].bullet_creator
            contact_id = contact.fixtureA.body.userData["ob"].id

            if is_bullet and ignore_id != contact_id:
                #check if small then dont destroy the bullet
                if contact.fixtureA.body.userData["ob"].get_poly().area > 200:
                    contact.fixtureB.body.userData["bullet_actions"] = "kill"

                if not contact.fixtureA.body.userData["ob"].static:
                    contact.fixtureA.body.userData["bullet_actions"] = "hit"

    def PreSolve(self, contact, impulse):
        pass

    def PostSolve(self, contact, impulse):
        pass

    def EndContact(self, contact):

        if "ob" in contact.fixtureA.body.userData and "ob" in contact.fixtureB.body.userData:
            if contact.fixtureA.body.userData["ob"].is_player and contact.fixtureB.body.userData["ob"].static:
                contact.fixtureA.body.userData["player_allow_impulse"] = False
        if "ob" in contact.fixtureB.body.userData and "ob" in contact.fixtureA.body.userData:
            if contact.fixtureB.body.userData["ob"].is_player and contact.fixtureA.body.userData["ob"].static:
                contact.fixtureB.body.userData["player_allow_impulse"] = False
