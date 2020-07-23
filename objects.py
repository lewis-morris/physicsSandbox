import datetime
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
from functions import get_random_col, get_config, convert_to_mks, convert_from_mks, get_rand_val, get_poly_from_ob, \
    dent_contour, fragment_poly, calculateDistance
import gc
from Box2D import *

def load(fps, gravity):
    """ Init """
    timer = Timer(fps)
    board = Board()
    phys = Physics(gravity)
    draw = Draw()
    PPM = get_config("running", "PPM")
    block_accuracy = get_config("blocks", "block_accuracy")
    phys = board.load_blocks(get_config("screen", "background_name"), get_config("screen", "backgrond_ext"), phys,
                             draw=get_config("static_blocks", "draw"),
                             block_accuracy=block_accuracy)
    phys.world.contactListener = Contacter()
    msg = Messenger(get_config("screen", "fps"), board.board)
    SCREEN_HEIGHT, SCREEN_WIDTH = board.board.shape[:2]



    phys.height = SCREEN_HEIGHT
    phys.width = SCREEN_WIDTH
    return timer, phys, board, draw, msg

def pickle(pickle_name):
    pass
def load_state(pickle_name):
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
            if get_config("draw", "pause_on_mouse") is True:
                self.pause = True

            if not self.coords is [] and not coords is None:
                self.coords.append(coords)

        elif self.status in ["distance", "weld_pos", "rotation_pos", "wheel_draw", "wheel_move", "rectangle_draw",
                             "circle_draw", "line_draw", "length"]:
            self.locations.append([x, y])

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
        elif len(self.locations) == 1 and not self.status in ["wheel_draw", "wheel_move", "circle_move", "line_draw"]:
            board = cv2.circle(board, tuple(self.locations[0]), 2, (240, 14, 14), -1)

        elif self.status in ["wheel_move"]:
            board = cv2.circle(board, tuple(self.locations[-1]), self.wheel_size if self.wheel_size >= 1 else 1,
                               (240, 14, 14), -1)
        elif self.status in ["wheel_draw", "circle_draw", "circle_move"]:
            board = cv2.circle(board, tuple(self.locations[0]), self.wheel_size if self.wheel_size >= 1 else 1,
                               (240, 14, 14), -1)

        elif len(self.locations) == 2 and self.status == "fire":
            # draw line for fire
            board = cv2.arrowedLine(board, tuple(self.locations[0]), tuple(self.locations[1]), (240, 14, 14), 2)
        elif len(self.locations) >= 2 and self.status == "distance":
            board = cv2.line(board, tuple(self.locations[0]), tuple(self.locations[-1]), (240, 14, 14), 2)

        elif len(self.locations) >= 2 and self.status == "length":
            board = cv2.arrowedLine(board, tuple(self.locations[0]), tuple(self.locations[-1]), (240, 14, 14), 2)

        elif len(self.locations) >= 2 and (self.status in ["poly", "frag"]):
            # used for drawing the rough shape of the polygon
            for i in range(len(self.locations) - 1):
                board = cv2.line(board, tuple(self.locations[i]), tuple(self.locations[i + 1]), (240, 14, 14), 2)
        elif self.status in ["delete", "select", "rectangle_draw", "rectangle_move"]:
            board = cv2.rectangle(board, tuple([int(x) for x in self.locations[0]]),
                                  tuple([int(x) for x in self.locations[-1]]), (240, 14, 14), 2)

        elif self.status in ["line_draw"]:
            if len(self.locations) >= 2:
                for i in range(0, len(self.locations) - 2):
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
                coord = get_poly_from_ob(block, 3).exterior.coords
                for i in range(len(coord)):
                    co1 = tuple([int(x) for x in coord[i]])
                    co2 = tuple([int(x) for x in coord[(i + 1) if i != len(coord) - 1 else 0]])
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

    def __init__(self, gravity=(0, 10), ):

        self.world = b2World(gravity=gravity)
        self.height = None
        self.width = None
        self.block_list = []
        self.draw_objects = {"sensor":True,"ground":True,"blocks":True}
        self.pause = False

    def kill_all(self, static=True):
        for i in np.arange(len(self.block_list) - 1, -1, -1):
            block = self.block_list[i]
            if static:
                self.delete(block)
            else:
                if not block.static:
                    self.delete(block)

    def save_block_as_dict(self, block):

        block_dic = {"type": block.type,
                     "pos": block.pos,
                     "current_position": block.current_position,
                     "sprite": block.sprite,
                     "col": block.col,
                     "active": block.active,
                     "id": block.id,
                     "static": block.static,
                     "center": block.center,
                     "booster": block.booster,
                     "goal": block.goal}


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
            if hasattr(joint.joint, "anchorA"):
                anc = joint.joint.anchorA
                joints_dic["anchorA"] = [anc.x, anc.y]

            if hasattr(joint.joint, "anchorB"):
                anc = joint.joint.anchorB
                joints_dic["anchorB"] = [anc.x, anc.y]

            if hasattr(joint.joint, "bodyA"):
                joints_dic["bodyA"] = joint.joint.bodyA.userData["ob"].id
            if hasattr(joint.joint, "bodyB"):
                joints_dic["bodyB"] = joint.joint.bodyB.userData["ob"].id
            if hasattr(joint.joint, "maxLength"):
                joints_dic["maxLength"] = joint.joint.maxLength

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
            if block_info["block"]["type"] in [1,-1,3]:
                shape = [convert_to_mks(x[0], x[1]) for x in block_info["block"]["shape"]]
                self.block_list.append(
                    Block(create_type(position=block_info["body"]["position"],
                                                         fixtures=b2FixtureDef(
                                                             shape=b2PolygonShape(vertices=shape),
                                                             density=block_info["fixtures"]["density"])),
                          set_sprite=block_info["block"]["sprite"], draw_static=block_info["block"]["draw_static"])

                )

            # if circle
            else:
                rad = convert_to_mks(block_info["block"]["shape"])

                self.block_list.append(
                    Ball(create_type(position=block_info["body"]["position"],
                                                      fixtures=b2FixtureDef(
                                                          shape=b2CircleShape(radius=rad),
                                                          density=block_info["fixtures"]["density"]))
                         , set_sprite=block_info["block"]["sprite"]))

            # get current block and add settings
            block = self.block_list[-1]
            for k, v in block_info["block"].items():
                if hasattr(block, k):
                    setattr(block, k, v)

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
                        setattr(block.body, k, v)

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
        return new_obs

    def get_block_by_id(self, id):

        blocks = [bl for bl in self.block_list if bl.old_id == id]
        if blocks != []:
            return blocks[-1]
        else:
            for bl in self.block_list:
                if bl.id == id:
                    return bl

    def fractal_split(self, block):

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

    def fractal_block(self, ob, create=True, static=True):
        if create is True:
            self.fractal_create(ob, static)
        elif create is False:
            self.fractal_split(ob)

    def create_block(self, shape=None, pos=None, rest=None, density=None, friction=None, poly_type=None,
                     set_sprite=False, draw_static=True, size=None, static=False, draw=None, sq_points=False):
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
            size = get_rand_val("blocks", "size")
        if rest is None:
            rest = get_rand_val("blocks", "rest")
        if density is None:
            density = get_rand_val("blocks", "density")
        if friction is None:
            friction = get_rand_val("blocks", "friction")

        # get the type

        if poly_type is None:
            poly_type = random.choice(get_config("blocks_out", "player_type"))

        # get the shape of the item

        if shape is None:
            if poly_type == 2:
                shape = int(size / 2)
            elif poly_type == 1:
                shape = [[0, 0], [0, size], [size, size], [size, 0]]
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
            pos = (int(self.width * get_rand_val("blocks_out", "start_pos_x")),
                   int(self.height * get_rand_val("blocks_out", "start_pos_y")))

        position = convert_to_mks(pos[0], pos[1])

        if static == True or (poly_type in [-1,-2]):
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
                self.block_list[-1].body.fixtures[0].restitution = get_config("static_blocks", "rest")
                self.block_list[-1].body.fixtures[0].friction = get_config("static_blocks", "friction")
            except AssertionError:
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

            self.block_list[-1].body.fixtures[0].restitution = get_config("static_blocks", "rest")
            self.block_list[-1].body.fixtures[0].friction = get_config("static_blocks", "friction")

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
            except AssertionError:
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
        return True

    def apply_impulses(self):
        for bl in self.block_list:
            bl.boost_block()

    def draw_blocks(self, board, ground_only=False, ground=False):
        """
        Dray all blocks
        :param board: np array
        :return:
        """
        force = False
        if ground is True:
            blocks = [b for b in self.block_list if b.static is True]
            force = True
        else:
            if ground_only is True:
                blocks = []
            else:
                blocks = self.block_list

        # split sensors and blocks
        sensor_blocks = [bl for bl in self.block_list if bl.body.fixtures[0].sensor == True]
        blocks = [bl for bl in self.block_list if bl not in sensor_blocks]

        # draw blocks undernear
        for bl in blocks:
            board = bl.draw(board, force_draw=force)

        # draw sensors on top
        for bl in sensor_blocks:
            board_overlay = board.copy()
            board_overlay = bl.draw(board_overlay, force_draw=force)
            alpha = 0.2
            board = cv2.addWeighted(board_overlay, alpha, board, 1 - alpha, 0)

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

    def create_chain_joint(self, a, b, lines, stretchy=False):
        last_ob = 0
        end = False

        ###FROM STACKOVERFLOW
        ## https://stackoverflow.com/questions/62990029/how-to-get-equally-spaced-points-on-a-line-in-shapely/62994304#62994304
        line = LineString(lines)
        # or to get the distances closest to the desired one:
        # n = round(line.length / desired_distance_delta)
        distances = np.linspace(0, line.length, int(line.length / 10))
        # or alternatively without NumPy:
        # distances = (line.length * i / (n - 1) for i in range(n))
        points = [line.interpolate(distance) for distance in distances]
        multipoint = unary_union(points)
        lines = [(int(p.x), int(p.y)) for p in multipoint]

        lines = [[int(co[0]), int(co[1])] for co in get_enlongated_line(lines)]

        for i in np.arange(0, len(lines) - 1, step=2):
            pos = lines[i]
            last_ob += 1

            self.create_block(pos=pos, draw=False, size=2, poly_type=1, density=0, friction=0.1, rest=0)

            if i == 0:
                blockA = a.body
            else:
                blockA = self.block_list[-2].body

            if i >= len(lines) - 2:
                blockB = b.body
                end = True
            else:
                blockB = self.block_list[-1].body

            if stretchy is False:
                dist = calculateDistance(blockA.worldCenter.x, blockA.worldCenter.y, blockB.worldCenter.x,
                                         blockB.worldCenter.y)

                self.world.CreateRopeJoint(bodyA=blockA,
                                           bodyB=blockB,
                                           anchorA=blockA.worldCenter,
                                           anchorB=blockB.worldCenter,
                                           maxLength=dist,
                                           collideConnected=False)
                self.world.joints[-1].dampingRatio = 1
                self.world.joints[-1].frequency = 0
            else:
                self.world.CreateDistanceJoint(bodyA=blockA,
                                               bodyB=blockB,
                                               anchorA=blockA.worldCenter,
                                               anchorB=blockB.worldCenter,
                                               collideConnected=True)

                self.world.joints[-1].dampingRatio = 200
                self.world.joints[-1].frequencyHz = 10
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

        #delete hit goal items
        for bl in self.block_list:
            if bl.body.userData["goal"] == True:
                goals +=1
                self.delete(bl)
        return goals

class Ball():

    def __init__(self, body, set_sprite=False, draw=True, poly_type=None):
        self.body = body
        self.body.userData = {"ob": self, "joints": [], "impulses": [],"goal":False}
        self.type = poly_type
        self.pos = None
        self.current_position = []
        self.col = get_random_col()
        self.active = True
        self.center = None
        self.radius = int(convert_from_mks(self.body.fixtures[0].shape.radius))
        self.static = False
        self.times_off = 0
        self.old_id = None
        self.draw_me = draw
        self.booster = None
        self.goal = False
        self.id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))
        if set_sprite is True:
            self.set_sprite()
        else:
            self.sprite = None

    def __str__(self):

        str = f"active: {self.active} col: {self.col} id: {self.id} old_id: {self.old_id} static: {self.static} \n"
        for x in self.body.joints:
            str += f"Joint: {type(x.joint)} bodyA id {x.joint.bodyA.userData['ob'].id} oldId {x.joint.bodyA.userData['ob'].old_id} bodyB id {x.joint.bodyB.userData['ob'].id} oldId {x.joint.bodyB.userData['ob'].old_id}\n"

        return str

    def get_current_pos(self):
        self.center = convert_from_mks((self.body.transform * self.body.localCenter).x,
                                       (self.body.transform * self.body.localCenter).y)
        self.current_position = [self.center]

    def set_sprite(self):
        try:
            img = cv2.imread(random.choice(get_config("balls", "sprite")), -1)
            self.sprite = cv2.resize(img, (int(self.radius * 2), int(self.radius * 2)))
            mask = self.sprite[:, :, 3] / 255

            self.mask = np.stack([mask, mask, mask]).transpose([1, 2, 0])
            inv_mask = 1 - mask.copy()
            self.inv_mask = np.stack([inv_mask, inv_mask, inv_mask]).transpose([1, 2, 0])

            self.sprite = self.sprite[:, :, :3] * self.mask
            self.sprite = self.sprite[:, :, ::-1]

        except:
            self.sprite = None
            print("Error reading sprite image file")

    def boost_block(self):

        for impul in self.body.userData["impulses"]:
            self.body.ApplyLinearImpulse((np.array(impul)*self.body.mass)*2, self.body.worldCenter, wake=True)

        self.body.userData["impulses"] = []

    def draw(self, board, force_draw=False):

        self.get_current_pos()

        if not self.sprite is None:

            degrees = np.rad2deg(self.body.angle)
            if degrees != 0:
                sprite = rotate(self.sprite.copy().astype(np.uint8), int(degrees), reshape=False)
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

            board[y_start:y_end, x_start:x_end, :] = (board[y_start:y_end, x_start:x_end, :] * mask) + sprite
            # board[y_start:y_end, x_start:x_end] = board[y_start:y_end, x_start:x_end] * (1 - mask) + (img * mask)
        elif not self.draw_me is False:
            board = cv2.circle(board, tuple([int(x) for x in self.center]), int(self.radius), self.col,
                               thickness=-1)  # .astype(np.uint8)

        return board


class Block():

    def __init__(self, body, static_shape=True, set_sprite=False, draw_static=True, poly_type=None):
        self.body = body
        self.body.userData = {"ob": self, "joints": [], "impulses": [],"goal":False}
        self.type = poly_type
        self.pos = None
        self.current_position = []
        self.static = static_shape
        self.old_id = None
        self.shape = [convert_from_mks(x, y) for x, y in self.body.fixtures[0].shape.vertices]
        self.width = round(max([x[0] for x in self.shape]))
        self.height = round(max([x[1] for x in self.shape]))
        self.center = None
        self.times_off = 0
        self.draw_me = True
        self.booster = None
        self.goal = False

        if set_sprite:
            self.set_sprite()
        else:
            self.sprite = None

        if static_shape:
            self.col = [234, 123, 23]
        else:
            self.col = get_random_col()
        self.active = True

        self.id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))

        self.draw_static = draw_static

    def __str__(self):
        str = f"active: {self.active} col: {self.col} id: {self.id} old_id: {self.old_id} static: {self.static} \n"
        for x in self.body.joints:
            str += f"Joint: {type(x.joint)} bodyA id {x.joint.bodyA.userData['ob'].id} oldId {x.joint.bodyA.userData['ob'].old_id} bodyB id {x.joint.bodyB.userData['ob'].id} oldId {x.joint.bodyB.userData['ob'].old_id}\n"

        return str

    def boost_block(self):

        for impul in self.body.userData["impulses"]:
            self.body.ApplyLinearImpulse((np.array(impul)*self.body.mass)*2, self.body.worldCenter, wake=True)

        self.body.userData["impulses"] = []

    def get_current_pos(self):

        shapes = [(self.body.transform * v) for v in self.body.fixtures[0].shape.vertices]
        shapes = [(convert_from_mks(val[0], val[1])) for val in shapes]
        shapes = [(v[0], v[1]) for v in shapes]
        self.current_position = np.array(shapes)
        self.center = convert_from_mks((self.body.transform * self.body.localCenter).x,
                                       (self.body.transform * self.body.localCenter).y)

    def set_sprite(self):

        try:
            img = cv2.imread(random.choice(get_config("squares", "sprite")), -1)
            if random.randint(1, 2) == 1:
                img = img[:, ::-1]
            self.sprite = cv2.resize(img, (int(self.width), int(self.height)))

            if self.sprite.shape[2] == 4:
                mask = self.sprite[:, :, 3] / 255
                self.mask = np.stack([mask, mask, mask]).transpose([1, 2, 0])
                self.sprite = self.sprite[:, :, :3][:, :, ::-1]
            else:
                self.mask = np.ones(self.sprite.shape)

            self.inv_mask = 1 - self.mask.copy()

        except:
            self.sprite = None
            print("Error reading sprite image file")

    def draw(self, board, force_draw=True):
        if self.draw_me is False:
            return board
        elif (self.draw_static is True and self.static) or self.static is False or force_draw is True:
            self.get_current_pos()

            if not self.sprite is None:

                center = self.center

                degrees = np.rad2deg(self.body.angle)

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
                return board
            else:
                out_img = cv2.fillConvexPoly(board, self.current_position.astype(np.int32), self.col)
                return out_img
        else:
            return board


class Board():
    def __init__(self):
        self.board = None
        self.board_front = None

    def load_blank(self, x, y):
        "Used for a blank board"
        self.board = np.zeros((y, x, 3), dtype=np.uint8)

    def load_blocks(self, basename, ext, phys, draw=False, block_accuracy=0.1):

        # get Background
        board = cv2.imread(basename + "Back." + ext)
        if not board is None:
            self.board = board[:, :, ::-1]

        # get forground
        board_front = cv2.imread(basename + "Front." + ext, -1)
        if not board_front is None:
            self.board_front = board_front
            self.board_front_mask = (self.board_front[:, :, 3] / 255)
            self.board_front_mask = np.stack(
                [self.board_front_mask, self.board_front_mask, self.board_front_mask]).transpose([1, 2, 0])
            self.board_front_conv = (self.board_front[:, :, :3] * self.board_front_mask)  # .astype(np.uint8)
            self.board_front_conv = self.board_front_conv[:, :, ::-1]
            self.board_front_mask_inv = 1 - self.board_front_mask

        # get blocks
        blocks = cv2.imread(basename + "Blocks." + ext)

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
            self.board = np.zeros((800, 1200, 3), dtype=np.uint8)

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
        self.pannel = np.zeros((30, board.shape[1], 3), dtype=np.uint8)
        self.pannel[:, :] = (123, 123, 123)
        self.pannel[2:-2, 2:-2] = (170, 170, 170)
        self.pannel[2:-2, -105:-4] = (210, 210, 210)
        self.goal_hits = 0
        self.display_pannel_pause = self.pannel.copy()

    def auto_set(self, options, key):
        messages = [k for k,v in options.items()]
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

        self.highest_impulse = 0
        self.lowest_impulse = 9999
        self.check_break = get_config("draw", "break_on_impact")
        self.break_val = get_config("draw", "impulse_break")
        self.config_times = 0

    def check_config(self):
        if self.config_times > 100:
            self.check_break = get_config("draw", "break_on_impact")
            self.break_val = get_config("draw", "impulse_break")
            self.config_times = 0
        else:
            self.config_times += 1

    def BeginContact(self, contact):
        #booster
        if contact.fixtureA.sensor == True and contact.fixtureA.body.userData["ob"].booster != None:
            contact.fixtureB.body.userData["impulses"].append(contact.fixtureA.body.userData["ob"].booster)
        if contact.fixtureB.sensor == True and contact.fixtureB.body.userData["ob"].booster != None:
            contact.fixtureA.body.userData["impulses"].append(contact.fixtureB.body.userData["ob"].booster)

        #goal
        if contact.fixtureA.sensor == True and contact.fixtureA.body.userData["ob"].goal == True:
            contact.fixtureB.body.userData["goal"] = True
        if contact.fixtureB.sensor == True and contact.fixtureB.body.userData["ob"].goal == True:
            contact.fixtureA.body.userData["goal"] = True

    def PreSolve(self, contact, impulse):
        if contact.fixtureA.sensor == True and contact.fixtureA.body.userData["ob"].booster != None:
            contact.fixtureB.body.userData["impulses"].append(contact.fixtureA.body.userData["ob"].booster)
        if contact.fixtureB.sensor == True and contact.fixtureB.body.userData["ob"].booster != None:
            contact.fixtureA.body.userData["impulses"].append(contact.fixtureA.body.userData["ob"].booster)

    def PostSolve(self, contact, impulse):
        pass
        return
        # self.check_config()
        # # print(impulse)
        # if self.check_break is True and impulse.normalImpulses[0] > self.break_val:
        #     if contact.fixtureA.body.mass > contact.fixtureB.body.mass:
        #         contact.fixtureB.body.userData["break"] = True
        #     elif contact.fixtureB.body.mass > contact.fixtureA.body.mass:
        #         contact.fixtureA.body.userData["break"] = True
        #     else:
        #         contact.fixtureB.body.userData["break"] = True
        #         contact.fixtureB.body.userData["break"] = True

    def EndContact(self, contact):
        pass
        return
        if "break" in contact.fixtureB.body.userData.keys() and contact.fixtureB.body.userData["break"] == True:
            contact.fixtureB.body.userData["break_now"] = True
        if "break" in contact.fixtureA.body.userData.keys() and contact.fixtureA.body.userData["break"] == True:
            contact.fixtureA.body.userData["break_now"] = True
