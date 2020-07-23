import configparser
import math
import pickle

import random
import cv2
import dill
import numpy as np
import shapely
from Box2D import b2CircleShape, b2PolygonShape, b2FixtureDef
from sect.triangulation import constrained_delaunay_triangles, delaunay_triangles

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from shapely import affinity
from configobj import ConfigObj


config = ConfigObj('config.cfg')

# config = configparser.ConfigParser(comment_prefixes='#', allow_no_value=True)
# config.read('config.cfg')

config_reads = 0


def convert_to_mks(x, y=None):
    ppm = get_config("running","PPM")
    if not y is None:
        return x / ppm, y / ppm
    else:
        return x / ppm


def convert_from_mks(x, y=None):
    ppm = get_config("running", "PPM")
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


def check_contains_all(block_list, shape):
    """ used to search a rectangular shape for blocks"""

    contained_list = []
    square = Polygon(shape)

    # check if you are allowed to select the floor
    del_floor = get_config("draw", "allow_select_delete_floor")
    if del_floor is True:
        blocks = block_list
    else:
        blocks = [bl for bl in block_list]

    for bl in blocks:
        poly = get_poly_from_ob(bl)
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


def get_rand_val(main, sub):
    if sub + "_min" in config[main]:
        min = get_config(main, sub + "_min")
        max = get_config(main, sub + "_max")
        scale = get_config(main, sub + "_scale")
        if min != max:
            return random.randint(min, max) / scale
        else:
            return min / scale
    else:
        return get_config(main, sub)


def set_config(main, sub, val):
    config[main][sub] = str(val)
    config.write()


def get_config(main, sub):
    global config_reads
    global config

    if config_reads > 200:
        config = ConfigObj('config.cfg')
        # config.read('config.cfg')
        config_reads = 0
    else:
        config_reads += 1

    if not main in config and not sub in config[main]:
        config = ConfigObj('config_defaults.cfg')

    val = config[main][sub]

    if type(val) == list:
        joined = "".join(val)
        if "(" in joined:
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

    elif "true" in val.lower() or "false" in val.lower():
        return True if val.lower() == "true" else False

    elif "." in val:
        return float(val)

    else:
        try:
            return int(val)
        except:
            return val


def get_random_col():
    cols = [[128, 0, 0], [139, 0, 0], [165, 42, 42], [178, 34, 34], [220, 20, 60], [255, 0, 0], [255, 99, 71],
            [255, 127, 80], [205, 92, 92], [240, 128, 128], [233, 150, 122], [250, 128, 114], [255, 160, 122],
            [255, 69, 0], [255, 140, 0], [255, 165, 0], [255, 215, 0], [184, 134, 11], [218, 165, 32], [238, 232, 170],
            [189, 183, 107], [240, 230, 140], [128, 128, 0], [255, 255, 0], [154, 205, 50], [85, 107, 47],
            [107, 142, 35], [124, 252, 0], [127, 255, 0], [173, 255, 47], [0, 100, 0], [0, 128, 0], [34, 139, 34],
            [0, 255, 0], [50, 205, 50], [144, 238, 144], [152, 251, 152], [143, 188, 143], [0, 250, 154], [0, 255, 127],
            [46, 139, 87], [102, 205, 170], [60, 179, 113], [32, 178, 170], [47, 79, 79], [0, 128, 128], [0, 139, 139],
            [0, 255, 255], [0, 255, 255], [224, 255, 255], [0, 206, 209], [64, 224, 208], [72, 209, 204],
            [175, 238, 238], [127, 255, 212], [176, 224, 230], [95, 158, 160], [70, 130, 180], [100, 149, 237],
            [0, 191, 255], [30, 144, 255], [173, 216, 230], [135, 206, 235], [135, 206, 250], [25, 25, 112],
            [0, 0, 128], [0, 0, 139], [0, 0, 205], [0, 0, 255], [65, 105, 225], [138, 43, 226], [75, 0, 130],
            [72, 61, 139], [106, 90, 205], [123, 104, 238], [147, 112, 219], [139, 0, 139], [148, 0, 211],
            [153, 50, 204], [186, 85, 211], [128, 0, 128], [216, 191, 216], [221, 160, 221], [238, 130, 238],
            [255, 0, 255], [218, 112, 214], [199, 21, 133], [219, 112, 147], [255, 20, 147], [255, 105, 180],
            [255, 182, 193], [255, 192, 203], [250, 235, 215], [245, 245, 220], [255, 228, 196], [255, 235, 205],
            [245, 222, 179], [255, 248, 220], [255, 250, 205], [250, 250, 210], [255, 255, 224], [139, 69, 19],
            [160, 82, 45], [210, 105, 30], [205, 133, 63], [244, 164, 96], [222, 184, 135], [210, 180, 140],
            [188, 143, 143], [255, 228, 181], [255, 222, 173], [255, 218, 185], [255, 228, 225], [255, 240, 245],
            [250, 240, 230], [253, 245, 230], [255, 239, 213], [255, 245, 238], [245, 255, 250], [112, 128, 144],
            [119, 136, 153], [176, 196, 222], [230, 230, 250], [255, 250, 240], [240, 248, 255], [248, 248, 255],
            [240, 255, 240], [255, 255, 240], [240, 255, 255], [255, 250, 250]]

    return random.choice(cols)


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

        inner = get_poly_from_ob(bl,6)
        if poly.contains(inner):
            blocks.append(bl)
    if len(blocks) == 0:
        return False
    else:
        return blocks

def get_clicked(bodies, x, y, shrink_cir=16):
    block = None
    coords = None
    for i in np.arange(len(bodies) - 1, -1, -1):
        bl = bodies[i]
        is_clicked, shape = check_contains(bl, (x, y), shrink_cir)
        if is_clicked is True:
            block = bl
            coords = shape
            break
    return block, coords


def change_size(block, up=True):
    body = block.body
    fix = body.fixtures[0]

    dic = {"den": fix.density,
           "rest": fix.restitution,
           "friction": fix.friction,
           "radius":fix.shape.radius,
           "shape":type(fix.shape)}
    try:
        poly = get_poly_from_ob(block)
    except:
        #only for polys
        pass

    #check if going to be too small
    if dic["shape"] == b2CircleShape:
        #get the size of the phys engine
        oneMks = convert_to_mks(2)
        new_rad = dic["radius"] + (oneMks if up else -oneMks)
        # stops it being too small
        if new_rad < convert_to_mks(1):
            del fix
            return block


    #remove old fixture
    del fix
    body.DestroyFixture(body.fixtures[0])



    if dic["shape"] == b2CircleShape:
        dic["type"] = "circle"
        new_rad = dic["radius"] + (oneMks if up else -oneMks)


        body.CreateFixture(shape=b2CircleShape(radius=new_rad),
                           restitution=dic["rest"], density=dic["den"], friction=dic["friction"])
        block.radius = convert_from_mks(new_rad)
    else:

        dic["type"] = "poly"
        if up:
            poly_new = affinity.scale(poly,1.05,1.05)
        else:
            poly_new = affinity.scale(poly, .95, .95)

        verts = [convert_to_mks(co[0],co[1]) for co in list(poly_new.exterior.coords)]

        body.CreateFixture(b2FixtureDef(shape=b2PolygonShape(vertices=verts)), restitution=dic["rest"], density=dic["den"],
                           friction=dic["friction"])


    return block

def calculateDistance(x1, y1, x2, y2):
    dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return dist


def get_poly_from_ob(v1, shrink_cir=16):
    # if not calculated then calc the position
    if v1.current_position == []:
        v1.get_current_pos()

    if hasattr(v1, "shape"):
        # create polygon
        polygon = Polygon(v1.current_position)
    else:
        # if circle get poly
        polygon = Point(v1.center[0], v1.center[1])
        polygon = polygon.buffer(v1.radius, shrink_cir)
    return polygon

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
    polygon = get_poly_from_ob(v1, shrink_cir)
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
