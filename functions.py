import ast
import copy
import math
import random

import cv2
import dill
import numpy as np
from configobj import ConfigObj
from sect.triangulation import constrained_delaunay_triangles
from shapely.geometry import LineString
from shapely.geometry.polygon import Polygon

import re
from subprocess import Popen, PIPE


def get_active_window_title():
    try:
        root = Popen(['xprop', '-root', '_NET_ACTIVE_WINDOW'], stdout=PIPE)

        for line in root.stdout:
            m = re.search('^_NET_ACTIVE_WINDOW.* ([\w]+)$', line.decode("utf-8") )
            if m != None:
                id_ = m.group(1)
                id_w = Popen(['xprop', '-id', id_, 'WM_NAME'], stdout=PIPE)
                break

        if id_w != None:
            for line in id_w.stdout:
                match = re.match("WM_NAME\(\w+\) = (?P<name>.+)$", line.decode("utf-8") )
                if match != None:
                    return match.group("name")
    except FileNotFoundError:
        return "Board"

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


def create_floor_poly(max_width, max_height, slope_times_min, slope_times_max, x_stride_min, x_stride_max, y_stride_min,
                      y_stride_max, full_poly=True):
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
                y_rand = random.randint(int(y_stride_max * 1.3), int(y_stride_max * 2))
            else:
                y_rand = random.randint(y_stride_min, y_stride_max)

            y_rand = y_rand if slope < 2 else -y_rand

        new_coords = copy.copy(coords[-1])
        new_coords[0] += x_rand
        new_coords[1] += y_rand * -1

        if not new_coords[1] > max_height - 100 or not new_coords[1] < 100:
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

    # check if you are allowed to select the floor
    blocks = block_list

    for block in [blo for blo in blocks if blo.is_onscreen]:
        poly = block.translated_position
        # poly_inside_poly(poly,square)
        if poly_inside_poly(poly, shape) is True:
            contained_list.append(block)

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


def get_config(main, sub, config_in=None):
    global config_reads
    if config_in is None:
        global config
    else:
        config = config_in

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
            joined_dic = joined_dic.replace("{", "").replace("}", "")
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
    elif "{" in val:
        return ast.literal_eval(config["blocks_out"]["player_type"])
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


def get_angle(v1, v2):
    y = v2[1] - v1[1]
    x = v2[0] - v1[0]
    return math.atan2(y, x) / math.pi * 180


def unit_vector(vector):
    """ Returns the unit vector of the vector.  """
    return vector / np.linalg.norm(vector)


def get_all_in_poly(phys, coords):
    """
    used for slecting players
    :param phys:
    :param coords:
    :return:
    """
    blocks = []

    poly = Polygon(np.array(coords) + phys.board.translation)

    for bl in [bl for bl in phys.block_list if bl.is_onscreen]:

        inner = [Polygon(fix) for fix in bl.translated_position]
        answers = [poly.contains(inn) for inn in inner]
        if sum(answers) == len(inner):
            blocks.append(bl)

    if len(blocks) == 0:
        return []
    else:
        return blocks


def get_clicked(bodies, x, y, shrink_cir=16, blocks_only=False):
    if blocks_only:
        bodies = [bl for bl in bodies if
                  bl.background is False and bl.foreground is False and bl.sensor["type"] is None and bl.type > 0]

    block = None
    coords = None

    background = [bl for bl in bodies if bl.background]
    blocks = [bl for bl in bodies if not bl.background and not bl.foreground]
    foreground = [bl for bl in bodies if bl.foreground]

    try:
        x += bodies[0].board.translation[0]
        y += bodies[0].board.translation[1]
    except:
        # no blocks
        pass

    for i in np.arange(len(background + foreground + blocks) - 1, -1, -1):
        if bodies:
            bl = bodies[i]

            is_clicked, shape = check_contains(bl.translated_position, (x, y))

            if is_clicked is True:
                block = bl
                coords = shape
                break
    return block, coords


def calculate_distance(x1, y1, x2, y2):
    dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return dist


def poly_inside_poly(v1, inside_v2):
    v1 = Polygon(v1)
    inside_v2 = Polygon(inside_v2)

    # found = []
    # for i in range(v1_len):
    #     founr
    #     found.append(point_inside_polygon(v1[i][0],v1[i][1],inside_v2))
    # if len(found) == v1_len:
    return inside_v2.covers(v1)


def point_inside_polygon(x, y, poly):
    n = len(poly)
    inside = False

    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def get_poly_from_verts(v1):
    return Polygon(v1)


def check_contains(v1, p1):
    """

    :param v1:
    :param p1:
    :return:
    """
    # polygon = v1.get_poly()
    # point = Point(p1[0], p1[1])

    # return polygon.contains(point), list(polygon.exterior.coords)
    for pos in v1:
        if point_inside_polygon(p1[0], p1[1], pos):
            return True, p1
    return False, p1


def get_centroid(vertexes):
    _x_list = [vertex[0] for vertex in vertexes]
    _y_list = [vertex[1] for vertex in vertexes]
    _len = len(vertexes)
    _x = sum(_x_list) / _len
    _y = sum(_y_list) / _len
    return _x, _y


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
