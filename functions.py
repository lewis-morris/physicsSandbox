import configparser
import copy
import math
import pickle

import random
import cv2
import dill
import numpy as np
import shapely
from Box2D import b2CircleShape, b2PolygonShape, b2FixtureDef
from sect.triangulation import constrained_delaunay_triangles, delaunay_triangles

from shapely.geometry import Point, LineString
from shapely.geometry.polygon import Polygon
from shapely import affinity
from configobj import ConfigObj
from shapely.ops import unary_union


def rotate_around_point_highperf(xy, radians, origin=(0, 0)):
    """Rotate a point around a given point.

    I call this the "high performance" version since we're caching some
    values that are needed >1 time. It's less readable than the previous
    function but it's faster.
    """
    x, y = xy
    offset_x, offset_y = origin
    adjusted_x = (x - offset_x)
    adjusted_y = (y - offset_y)
    cos_rad = math.cos(radians)
    sin_rad = math.sin(radians)
    qx = offset_x + cos_rad * adjusted_x + sin_rad * adjusted_y
    qy = offset_y + -sin_rad * adjusted_x + cos_rad * adjusted_y

    return qx, qy



def get_config_object(name):
    config = ConfigObj(name)
    if config == {}:
        config = ConfigObj("../" + name)
    return config

config = get_config_object('config.cfg')

# config = configparser.ConfigParser(comment_prefixes='#', allow_no_value=True)
# config.read('config.cfg')

config_reads = 0
ppm = 45

def convert_to_mks(x, y=None):
    global ppm
    if not y is None:
        return x / ppm, y / ppm
    else:
        return x / ppm


def convert_from_mks(x, y=None):
    global ppm
    if not y is None:
        return x * ppm, y * ppm
    else:
        return x * ppm

def fragment_poly(conts):


    conts = constrained_delaunay_triangles([tuple(x) for x in np.array(conts).squeeze()])
    final_contours = []
    for cn in conts:
        final_contours.append(cn)
    return final_contours

def create_floor_poly(max_width, max_height,slope_times_min,slope_times_max,x_stride_min,x_stride_max,y_stride_min,y_stride_max,full_poly=True):

    coords = [[0, 0], [400, 0]]
    slope_times = 0
    slope = 0
    slope = random.randint(0, 4)

    while True:
        if random.randint(0, 10) == 10:
            x_rand = random.randint(int(x_stride_max * 1.3), int(x_stride_max * 2))
        else:
            x_rand = random.randint(x_stride_min, x_stride_max)

        if slope_times == 0:
            if slope < 4:
                slope = 4
            else:
                slope = random.randint(0, 4)
            slope_times = random.randint(slope_times_min, slope_times_max)

        if slope == 4:
            y_rand = 0

        else:

            if random.randint(0, 10) == 10:
                y_rand = random.randint(int(y_stride_max*1.3), int(y_stride_max*2))
            else:
                y_rand = random.randint(y_stride_min, y_stride_max)

            y_rand = y_rand if slope < 2 else -y_rand

        new_coords = copy.copy(coords[-1])
        new_coords[0] += x_rand
        new_coords[1] += y_rand*-1

        if not new_coords[1] > max_height-100 or not new_coords[1] < 100:
            coords.append(new_coords)

        slope_times -= 1

        if new_coords[0] > max_width:
            break
    #     if new_coords[0] > 2000
    #     min_h = -2000

    min_y = max([co[1] for co in coords]) + 50

    if full_poly:
        coords.append([coords[-1][0], min_y])
        coords.append([0, min_y])
        return Polygon(coords)

    else:
        return LineString(coords)

def check_contains_all(block_list, shape, board):
    """ used to search a rectangular shape for blocks"""

    contained_list = []
    square = Polygon(shape)

    # check if you are allowed to select the floor


    blocks = block_list

    for bl in blocks:
        poly = bl.get_poly(board)
        if square.covers(poly) is True:
            contained_list.append(bl)

    return contained_list


def get_squ(pt1, pt2):
    pt11 = (pt2[0], pt1[1])
    pt22 = (pt1[0], pt2[1])

    return [pt1, pt11, pt2, pt22]


def pickle_objects(ob, file):
    f = open(file, "wb")
    dill.dump(ob, f)
    f.close()


def read_pickle(file):
    f = open(file, "rb")
    return dill.load(f)


def set_config(main, sub, val):
    config[main][sub] = str(val)
    config.write()

def get_config(main, sub, configIn=None):
    global config_reads
    if configIn is None:
        global config
    else:
        config = configIn

    if config_reads > 200:
        config = get_config_object('config.cfg')

        # config.read('config.cfg')
        config_reads = 0
    else:
        config_reads += 1

    if not main in config and not sub in config[main]:
        config = get_config_object('config_defaults.cfg')

    val = config[main][sub]

    if type(val) == list:

        joined = "".join(val)
        joined_dic = ",".join(val)
        if ":" in joined_dic:
            joined_dic = joined_dic.replace("{","").replace("}","")
            dic = {}
            for val in joined_dic.split(","):
                k, v = val.split(":")
                dic[k] = True if v.lower() == "true" else False if v.lower() == "false" else v
            return dic
        elif "(" in joined:
            val = [x.replace("(", "").replace(")", "") for x in val]
            try:
                return tuple([float(x) if "." in str(x) else int(x) for x in val])
            except:
                return tuple([x.strip() for x in val])

        if "[" in joined:
            val = [x.replace("[", "").replace("]", "") for x in val]

            try:
                return list([float(x) if "." in str(x) else int(x) for x in val])
            except:
                return list([x.strip() for x in val])
    elif "(" in val:
        return tuple([float(x.replace("(", "").replace(")", "")) for x in val.split(",")])
    elif "true" in val.lower() or "false" in val.lower():
        return True if val.lower() == "true" else False

    elif "." in val:
        try:
            return float(val)
        except ValueError:
            return val

    else:
        try:
            return int(val)
        except:
            return val



def get_angle(v1,v2):

    y = v2[1] - v1[1]
    x = v2[0] - v1[0]
    return math.atan2(y, x) / math.pi * 180

def unit_vector(vector):
    """ Returns the unit vector of the vector.  """
    return vector / np.linalg.norm(vector)

def get_all_in_poly(phys,coords):
    """
    used for slecting players
    :param phys:
    :param coords:
    :return:
    """
    blocks = []
    poly = Polygon(coords)
    for bl in phys.block_list:

        inner = bl.get_poly(6)
        if poly.contains(inner):
            blocks.append(bl)
    if len(blocks) == 0:
        return False
    else:
        return blocks

def get_clicked(bodies, x, y, shrink_cir=16):
    block = None
    coords = None

    background = [bl for bl in bodies if bl.background]
    blocks = [bl for bl in bodies if not bl.background and not bl.foreground]
    foreground = [bl for bl in bodies if bl.foreground]



    for i in np.arange(len(background+foreground+blocks) - 1, -1, -1):
        if bodies != []:
            bl = bodies[i]
            is_clicked, shape = check_contains(bl, (x, y), shrink_cir)
            if is_clicked is True:
                block = bl
                coords = shape
                break
    return block, coords


def calculateDistance(x1, y1, x2, y2):
    dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return dist



def get_poly_from_verts(v1):
    return Polygon(v1)

def check_contains(v1, p1, shrink_cir=16):
    """

    :param v1:
    :param p1:
    :param return_shape:
    :param shrink_cir: Used to lower the amount of lines to create the shape - helps with fragmenting
    :return:
    """
    polygon = v1.get_poly()
    point = Point(p1[0], p1[1])

    return polygon.contains(point), list(polygon.exterior.coords)


def dent_contour(cont):
    leng = len(cont)
    cont = np.array(cont).squeeze()
    new_cont = []
    for i in range(leng):
        rand = random.randint(150, 850) / 1000

        new_cont.append(cont[i])
        p1 = np.array(cont[i])
        p2 = np.array(cont[(i + 1) if i != leng - 1 else 0])

        new_point = (1 - rand) * p1 + rand * p2
        new_cont.append([round(x) for x in new_point])

    new_cont.append(cont[0])
    return new_cont


def angle_between(v1, v2):
    """ Returns the angle in radians between vectors 'v1' and 'v2'::

            >>> angle_between((1, 0, 0), (0, 1, 0))
            1.5707963267948966
            >>> angle_between((1, 0, 0), (1, 0, 0))
            0.0
            >>> angle_between((1, 0, 0), (-1, 0, 0))
            3.141592653589793
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


def get_center(pos):
    cx = 0
    cy = 0
    for p in pos:
        cx += p[0]
        cy += p[1]
    cx = cx / len(pos)
    cy = cy / len(pos)
    return cx, cy


def rotate(points, center, angle):
    cx, cy = center
    m = cv2.getRotationMatrix2D((cx, cy), angle, 1)

    return cv2.transform(points, m, None).astype(np.int32)
