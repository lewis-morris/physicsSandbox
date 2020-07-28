import cv2
import numpy as np

from shapely import affinity

from draw_functions import SelectType
from functions import get_config, convert_from_mks
from gui import save_gui, load_gui, load_options, update_background
from objects import Messenger, load, pickler

from shapely.geometry import Polygon
from functions import get_squ, check_contains_all, get_clicked, convert_to_mks, calculateDistance, get_all_in_poly, \
    get_poly_from_ob
from Box2D import b2MouseJoint, b2RevoluteJoint


def action_key_press(key, cur_key, draw, phys, msg, timer, board):
    """
    Deal with the key presses
    :param key:
    :return:
    """

    # delete any old mouse joints prior to dealing with the next keypress
    if key != ord("m") and msg.message != "Mouse Move":
        for jn in phys.world.joints:
            if type(jn) is b2MouseJoint:
                phys.world.DestroyJoint(jn)

    if key == 255:
        pass

    elif key == ord("r"):
        # RESET SCREEN
        draw.reset()
        msg = Messenger(phys.options["screen"]["fps"], board.board)
        msg.set_message("Reset")
        timer, phys, board, SCREEN_HEIGHT, SCREEN_WIDTH = load(get_config("screen", "fps"))

    elif key == ord("q"):
        # QUIT
        msg.set_message("Quit")
        board.run = False

    elif key == ord("z"):
        # SPAWN
        msg.set_message("Spawn")
        phys.create_block()

    elif key == ord("u"):
        # draw delete blocks
        draw.reset()
        options = {"Remove Joints": SelectType.select}
        cur_key = msg.auto_set(options, key)

    elif key == ord("x"):
        # draw delete blocks
        draw.reset()
        options = {"Delete": SelectType.select}
        cur_key = msg.auto_set(options, key)

    elif key == ord("]"):
        # draw polygon
        draw.reset()
        options = {"Shoot Bullet": SelectType.bullet_direction}
        cur_key = msg.auto_set(options, key)

    elif key == ord("["):
        # draw polygon
        draw.reset()
        options = {"Choose Player": SelectType.null}
        cur_key = msg.auto_set(options, key)

    elif key in [ord("a"), ord("w"), ord("s"), ord("d")]:
        # draw polygon
        draw.reset()
        phys.impulse_player(key)

    elif key == ord("p"):
        # draw polygon
        draw.reset()
        options = {"Polygon": SelectType.draw, "Rectangle": SelectType.rectangle, "Circle": SelectType.circle}
        cur_key = msg.auto_set(options, key)

    elif key == ord("b"):
        # draw polygon
        draw.reset()
        options = {"Fore Polygon": SelectType.draw, "Fore Rectangle": SelectType.rectangle,
                   "Fore Circle": SelectType.circle}
        cur_key = msg.auto_set(options, key)

    elif key == ord("f"):
        # draw fragments or select
        draw.reset()
        options = {"Fragment Poly": SelectType.draw, "Frament Rectangle": SelectType.rectangle,
                   "Frament Select": SelectType.select}
        cur_key = msg.auto_set(options, key)

    elif key == ord("g"):
        # draw ground
        draw.reset()
        options = {"Ground Poly": SelectType.draw, "Ground Rectangle": SelectType.rectangle,
                   "Ground Circle": SelectType.circle}
        cur_key = msg.auto_set(options, key)

    elif key == ord("1"):
        # fire polygon
        draw.reset()
        options = {"Create": SelectType.select_point, "Fire Poly": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key)

    elif key == ord("4"):
        # select
        # draw ground
        draw.reset()
        options = {"Select Joints": SelectType.select}
        cur_key = msg.auto_set(options, key)

    elif key == ord(";"):
        # select
        # draw ground
        draw.reset()
        options = {"Select/Print": SelectType.select}
        cur_key = msg.auto_set(options, key)

    elif key == ord("2"):
        # Mouse Move
        draw.reset()
        options = {"Rotate": SelectType.player_select}
        cur_key = msg.auto_set(options, key)

    elif key == ord("m"):
        # Mouse Move
        draw.reset()
        options = {"Mouse Move": SelectType.select, "Normal Move": SelectType.null, "Clone Move": SelectType.null}
        cur_key = msg.auto_set(options, key)

    elif key == ord("t"):
        # Mouse Move
        draw.reset()
        options = {"Transform": SelectType.player_select}
        cur_key = msg.auto_set(options, key)

    elif key == ord("e"):
        # draw ropes
        draw.reset()
        phys.kill_all(static=False)
        msg.set_message("Remove Blocks")
        cur_key = "e"

    elif key == ord("v"):
        # draw ropes
        draw.reset()
        msg.set_message("Set Spawn")
        cur_key = "v"

    elif key == ord("h"):
        # draw fragment ALL players
        # cur_key = "h"
        msg.set_message("Frag All")
        draw.reset()
        blocks = [bl for bl in phys.block_list if not bl.static is True]
        phys.fractal_block(blocks, create=False)

    elif key == ord("k"):
        # draw splitter sensor
        draw.reset()
        options = {"Pusher Poly": SelectType.draw, "Pusher Rectangle": SelectType.rectangle,
                   "Pusher Circle": SelectType.circle}
        cur_key = msg.auto_set(options, key)

    elif key == ord("l"):
        # draw splitter sensor
        draw.reset()
        options = {"Splitter Poly": SelectType.draw, "Splitter Rectangle": SelectType.rectangle,
                   "Splitter Circle": SelectType.circle}
        cur_key = msg.auto_set(options, key)

    elif key == ord("/"):
        # draw booster sensor
        draw.reset()
        options = {"Fire Poly": SelectType.draw, "Fire Rectangle": SelectType.rectangle,
                   "Fire Circle": SelectType.circle}
        cur_key = msg.auto_set(options, key)

    elif key == ord("'"):
        # draw booster sensor
        draw.reset()
        options = {"Goal Poly": SelectType.draw, "Goal Rectangle": SelectType.rectangle,
                   "Goal Circle": SelectType.circle}
        cur_key = msg.auto_set(options, key)

    elif key == ord("0"):
        # pause physics
        phys.draw_objects["ground"] = not phys.draw_objects["ground"]
        msg.set_message("Draw Ground" + (" On" if phys.draw_objects["ground"] is True else " Off"))
        cur_key = "0"

    elif key == ord("9"):
        # pause physics
        phys.draw_objects["blocks"] = not phys.draw_objects["blocks"]
        msg.set_message("Draw Blocks" + (" On" if phys.draw_objects["blocks"] is True else " Off"))
        cur_key = "0"

    elif key == ord("8"):
        # pause physics
        phys.draw_objects["sensor"] = not phys.draw_objects["sensor"]
        msg.set_message("Draw Sensors" + (" On" if phys.draw_objects["sensor"] is True else " Off"))
        cur_key = "0"

    elif key == ord("c"):
        # pause physics
        phys.draw_objects["foreground"] = not phys.draw_objects["foreground"]
        msg.set_message("Draw Foreground" + (" On" if phys.draw_objects["foreground"] is True else " Off"))
        cur_key = "0"

    elif key == ord("o"):
        # pause physics
        phys.pause = not phys.pause
        msg.set_message("Pause" + (" On" if phys.pause is True else " Off"))
        cur_key = "o"

    elif key == ord("*"):
        # PICKLE BOARD
        name = save_gui()
        if not name == "":
            pickler(timer, phys, draw, board, msg, name)
            msg.set_message("State Saved")
            cur_key = "*"
            draw.reset()

    elif key == ord("-"):
        # LOAD BOARD
        timer, phys, draw, board, msg = load_gui(timer, phys, draw, board, msg, persistant=False)

    elif key == ord("5"):

        load_options()
        phys.change_config()

    elif key == ord("6"):

        board, phys, msg = update_background(board, phys, msg)


    elif key == ord("j"):
        # draw joints
        draw.reset()
        options = {"Distance Joint": SelectType.straight_join, "Rope Joint": SelectType.straight_join,
                   "Electric": SelectType.line_join, "Springy Rope": SelectType.line_join,
                   "Weld Joint": SelectType.straight_join, "Wheel Joint": SelectType.circle,
                   "Rotation Joint": SelectType.rotation_select, "Pulley": SelectType.d_straight_join}

        cur_key = msg.auto_set(options, key)

    return cur_key, draw, phys, msg, timer, board


def rotate_block(draw, phys, event, x, y, type):
    if type[1:] == SelectType.player_select.value:
        if draw.stage == 0:
            draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
            if ans is True:
                if len(draw.player_list) > 0:
                    draw.stage += 1
                    draw.locations = [[x, y]]
                    draw.status = "rotate"
                elif len(draw.locations) > 1:
                    draw, phys = get_set_selected(draw, phys, "rotate", last_loc=True)
                    if len(draw.player_list) > 0:
                        draw.stage += 1
                        draw.locations = [[x, y]]
                        draw.status = "rotate"
                    else:
                        draw.reset()
        elif draw.stage == 1:

            draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y,
                                                          type[1] + SelectType.player_distance.value, False)
            if len(draw.locations) == 2:
                if draw.locations[0][1] > draw.locations[1][1]:
                    up = True
                elif draw.locations[0][1] < draw.locations[1][1]:
                    up = False
                else:
                    up = None
                if not up is None:
                    for bl in draw.player_list:
                        bl.body.angle += 0.1 if up is True else -0.1
                        bl.body.awake = True
                        bl.body.alive = True
            if ans is True:
                draw.reset()
    return draw, phys


def transform_block(draw, phys, event, x, y, type):
    if type[1:] == SelectType.player_select.value:
        if draw.stage == 0:
            draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
            if ans is True:
                if len(draw.player_list) > 0:
                    draw.stage += 1
                    draw.locations = [[x, y]]
                    draw.status = "rotate"
                elif len(draw.locations) > 1:
                    draw, phys = get_set_selected(draw, phys, "rotate", last_loc=True)
                    if len(draw.player_list) > 0:
                        draw.stage += 1
                        draw.locations = [[x, y]]
                        draw.status = "rotate"
                    else:
                        draw.reset()
        elif draw.stage == 1:

            draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y,
                                                          type[1] + SelectType.player_distance.value, False)
            if len(draw.locations) == 2:
                if draw.locations[0][1] > draw.locations[1][1]:
                    up = True
                elif draw.locations[0][1] < draw.locations[1][1]:
                    up = False
                else:
                    up = None
                if not up is None:
                    for i in np.arange(len(draw.player_list) - 1, -1, -1):
                        bl = draw.player_list[i]
                        phys, bl_new = change_size(phys, bl, up)

                        draw.player_list[i] = bl_new
                        draw.player_list[i].alive = True
                        draw.player_list[i].awake = True
                        del bl

            if ans is True:
                draw.reset()
    return draw, phys


def change_size(phys, block, up=True):
    block_info = phys.save_block_as_dict(block)
    old_poly = get_poly_from_ob(block, 3)
    center = old_poly.centroid

    if block_info["block"]["type"] in [-1, 1, 3]:
        old_poly = Polygon(block_info["block"]["shape"])
        if up:
            poly_new = affinity.scale(old_poly, 1.05, 1.05)

        else:
            poly_new = affinity.scale(old_poly, .95, .95)
            if poly_new.area < 100:
                poly_new = old_poly

        max_width = max([x[0] for x in list(poly_new.exterior.coords)])
        min_width = min([x[0] for x in list(poly_new.exterior.coords)])
        max_height = max([x[1] for x in list(poly_new.exterior.coords)])
        min_height = min([x[1] for x in list(poly_new.exterior.coords)])
        width = max_width - min_width
        height = max_height - min_height
        block_info["block"]["height"] = height
        block_info["block"]["width"] = width

        # new_pos = [[x[0] - center.x, x[1] - center.y] for x in list(old_poly.exterior.coords)]
        block_info["block"]["shape"] = poly_new.exterior.coords


    else:
        if up:
            block_info["block"]["radius"] *= 1.05

        else:
            block_info["block"]["radius"] *= 0.95

            if block_info["block"]["radius"] < 4:
                block_info["block"]["radius"] = 4

    phys.delete(block)
    phys.create_pre_def_block([block_info])
    block = phys.block_list[-1]

    return phys, block


def draw_sensor(draw, phys, event, x, y, type, ty):
    upstage = False
    if type[1:] == SelectType.draw.value and draw.stage == 0:
        # If polygon draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            conts = cv2.convexHull(np.array(draw.locations))
            poly = Polygon(conts.squeeze())
            coords = poly.exterior.coords
            cen = poly.centroid
            coords = [(int(co[0] - cen.x), int(co[1] - cen.y)) for co in coords]
            phys.create_block(pos=(cen.x, cen.y), poly_type=-1, shape=coords)
            upstage = True


    elif type[1:] == SelectType.rectangle.value and draw.stage == 0:
        # if rectangle draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(0, 0),
                              shape=(draw.locations[0], draw.locations[-1]),
                              poly_type=-1,
                              static=False,
                              sq_points=True
                              )
            upstage = True
    elif type[1:] == SelectType.circle.value and draw.stage == 0:
        # if circle draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(draw.locations[0]),
                              shape=int(draw.wheel_size),
                              size=int(draw.wheel_size),
                              poly_type=-2,
                              static=False
                              )
            upstage = True

    if upstage is True:
        draw.reset()
        block = phys.block_list[-1]
        for fix in block.body.fixtures:
            fix.sensor = True
        block.colour = (66, 218, 245)
        block.draw_me = True
        draw.stage += 1

        draw.locations = []
        cenX = int(get_poly_from_ob(block).centroid.x)
        cenY = int(get_poly_from_ob(block).centroid.y)
        draw.log_point(cenX, cenY, "fire")
        if ty == "goal":
            phys.block_list[-1].goal = True
            phys.block_list[-1].colour = (169, 252, 179)
            draw.reset()
        elif ty == "splitter":
            phys.block_list[-1].splitter = True
            phys.block_list[-1].colour = (162, 239, 242)
            draw.reset()

    if draw.stage == 1:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y,
                                                      type[0] + str(SelectType.vector_direction.value), False)
        if ans == True:
            if ty == "fire":
                phys.block_list[-1].booster = draw.vector
                phys.block_list[-1].colour = (242, 222, 162)
            elif ty == "pusher":
                phys.block_list[-1].forcer = draw.vector
                phys.block_list[-1].colour = (233, 162, 242)
            draw.reset()

    return draw, phys


def pulley(draw, phys, event, x, y, type):
    if type[1:] == SelectType.d_straight_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
                                                      allow_clicked=False, log_clicked=False,
                                                      allow_multiple=True)
        if ans is True:
            phys.create_pulley(draw.player_list[0], draw.player_list[1], draw.locations)
            draw.reset()

    return draw, phys


def rotation(draw, phys, event, x, y, type):
    if type[1:] == SelectType.rotation_select.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
                                                      allow_clicked=False, log_clicked=False,
                                                      allow_multiple=True)
        if ans == True:
            phys.create_rotation_joint(draw.player_list[0], draw.player_list[1], draw.locations[-1])
            draw.reset()

    return draw, phys


def fire_bullet(draw, phys, event, x, y, typer):
    draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, typer,
                                                  allow_clicked=True, log_clicked=True,
                                                  allow_multiple=False)

    if ans == True:
        player = [bl for bl in phys.block_list if bl.is_player][0]
        center = player.body.worldCenter
        center = convert_from_mks(center.x, center.y)
        if hasattr(player, "width"):
            width = int(player.width / 3)
        else:
            width = player.radius / 2

        if 5 < width:
            width = 5

        # set speed and restrict to max speed in settings

        if not draw.vector is None:
            vector = np.array(draw.vector)
            phys.create_block(pos=center, poly_type=1, size=width, draw=True)
            phys.block_list[-1].set_as_bullet(vector, player.id)

        draw.reset()

    return draw, phys


def fire(draw, phys, event, x, y, type):
    if type[1:] == SelectType.vector_direction.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
                                                      allow_clicked=True, log_clicked=True,
                                                      allow_multiple=False)
        if ans == True:
            if len(draw.player_list) > 0:
                try:
                    for bl in draw.player_list:
                        bl.body.ApplyLinearImpulse(np.array(draw.vector) * bl.body.mass, bl.body.worldCenter, wake=True)
                    # print(draw.block.body.mass)
                    # print(draw.block.body.fixtures[0].density)
                except AttributeError:
                    print("linear impulse error, check me")
                    # block not properly spawned yet and already clicked.
                    pass
            else:
                phys.create_block(pos=draw.locations[0])
                body = phys.block_list[-1].body
                body.ApplyLinearImpulse(np.array(draw.vector) * body.mass, phys.block_list[-1].body.worldCenter,
                                        wake=True)
            draw.reset()

    elif type[1:] == SelectType.select_point.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
                                                      allow_clicked=True, log_clicked=True,
                                                      allow_multiple=False)
        if ans == True:
            phys.create_block(pos=draw.locations[0])
            draw.reset()

    return draw, phys


def select_blocks(draw, phys, event, x, y, type):
    if type[1:] == SelectType.select.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, allow_clicked=True,
                                                      log_clicked=True,
                                                      allow_multiple=True)
        if ans is True:
            coors = list(get_poly_from_two_rectangle_points(draw.locations[0], draw.locations[-1]).exterior.coords)
            selected = get_all_in_poly(phys, coors)
            players = set(draw.player_list + ([] if selected is False else selected))
            if len(players) >= 1:
                for bl in players:
                    print(bl)
            draw.reset()
    return draw, phys


def wheel_draw(draw, phys, event, x, y, type):
    if type[1:] == SelectType.circle.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, True, True, True)

        if ans is True:
            phys.create_block(pos=draw.locations[0], poly_type=2, shape=draw.wheel_size, size=draw.wheel_size)
            phys.create_rotation_joint(draw.player_list[0], phys.block_list[-1], draw.locations[0])
            draw.reset()

    return draw, phys


def remove_joints(draw, phys, event, x, y, type):
    if type[1:] == SelectType.select.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, allow_clicked=True,
                                                      log_clicked=True,
                                                      allow_multiple=True)
        if ans is True:
            coors = list(get_poly_from_two_rectangle_points(draw.locations[0], draw.locations[-1]).exterior.coords)
            selected = get_all_in_poly(phys, coors)
            players = set(draw.player_list + ([] if selected is False else selected))
            if len(players) >= 1:
                for bl in players:
                    for jn in bl.body.joints:
                        phys.world.DestroyJoint(jn.joint)
            draw.reset()
    return draw, phys


def weld(draw, phys, event, x, y, type):
    if type[1:] == SelectType.straight_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_weld_joint(draw.player_list[0], draw.player_list[1], draw.locations[-1])
            draw.reset()
    return draw, phys


def distance_draw(draw, phys, event, x, y, type):
    if type[1:] == SelectType.straight_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_distance_joint(draw.player_list[0], draw.player_list[1], draw.locations[0], draw.locations[-1])
            draw.reset()

    return draw, phys


def rope(draw, phys, event, x, y, type):
    if type[1:] == SelectType.straight_join.value and draw.stage == 0:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)

        if ans is True:
            draw.stage += 1

    elif type[1:] == SelectType.straight_join.value and draw.stage == 1:

        draw.status = "length"
        if draw.anchorA is None:
            draw.anchorA = draw.locations[0]
            draw.anchorB = draw.locations[-1]

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, "a" + str(SelectType.length.value),
                                                      False)

        if ans == True:
            distance = calculateDistance(draw.locations[0][0], draw.locations[0][1], draw.locations[-1][0],
                                         draw.locations[-1][1])
            phys.create_rope_joint(draw.player_list[0], draw.player_list[1], draw.anchorA, draw.anchorB,
                                   distance)
            draw.reset()

    return draw, phys


def lightning(draw, phys, event, x, y, type):
    if type[1:] == SelectType.line_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_lightening_joint(draw.player_list[0], draw.player_list[1], draw.locations)
            draw.reset()
    return draw, phys


def chainish(draw, phys, event, x, y, type):
    if type[1:] == SelectType.line_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_chain(draw.player_list[0], draw.player_list[1], draw.locations)
            draw.reset()
    return draw, phys


def delete(draw, phys, event, x, y, type):
    # used for the fragment tool

    if type[1:] == SelectType.select.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, True)
        if ans is True:
            coors = list(get_poly_from_two_rectangle_points(draw.locations[0], draw.locations[-1]).exterior.coords)
            selected = get_all_in_poly(phys, coors)
            if not selected is False:
                for bl in selected:
                    phys.delete(bl)
            draw.reset()
        elif ans is False:
            pass
        else:
            phys.delete(ans)
            draw.reset()
    return draw, phys


def draw_fragment(draw, phys, event, x, y, type):
    # used for the fragment tool
    if type[1:] == SelectType.draw.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, True)
        if ans is True:
            phys.fractal_block(np.array(draw.locations), create=True, static=False)
            draw.reset()
        elif ans is False:
            pass
        else:
            phys.fractal_block(ans, create=False, static=False)
            draw.reset()

    elif type[1:] == SelectType.rectangle.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            coors = list(get_poly_from_two_rectangle_points(draw.locations[0], draw.locations[-1]).exterior.coords)
            phys.fractal_block(np.array(coors), create=True, static=False)
            draw.reset()

    elif type[1:] == SelectType.select.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            coors = list(get_poly_from_two_rectangle_points(draw.locations[0], draw.locations[-1]).exterior.coords)
            selected = get_all_in_poly(phys, coors)
            if not selected is False:
                for bl in selected:
                    phys.fractal_block(bl, create=False, static=False)
            draw.reset()

    return draw, phys


def draw_ground(draw, phys, event, x, y, type):
    # Used to draw the ground elements
    if type[1:] == SelectType.draw.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.fractal_block(np.array(draw.locations), create=True, static=True)
            draw.reset()
    elif type[1:] == SelectType.rectangle.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(0, 0),
                              shape=(draw.locations[0], draw.locations[-1]),
                              poly_type=-1,
                              static=True,
                              sq_points=True
                              )
            draw.reset()

    elif type[1:] == SelectType.circle.value:
        # if circle draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(draw.locations[0]),
                              shape=int(draw.wheel_size),
                              size=int(draw.wheel_size),
                              poly_type=-2,
                              static=False
                              )
            draw.reset()
    return draw, phys


def draw_foreground(draw, phys, event, x, y, type):
    if type[1:] == SelectType.draw.value:
        # If polygon draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            conts = cv2.convexHull(np.array(draw.locations))
            poly = Polygon(conts.squeeze())
            coords = poly.exterior.coords
            cen = poly.centroid
            coords = [(int(co[0] - cen.x), int(co[1] - cen.y)) for co in coords]
            phys.create_block(pos=(cen.x, cen.y), poly_type=-1, shape=coords, static=True, foreground=True)
            draw.reset()

    elif type[1:] == SelectType.rectangle.value:
        # if rectangle draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(0, 0),
                              shape=(draw.locations[0], draw.locations[-1]),
                              poly_type=-1,
                              static=True,
                              sq_points=True,
                              foreground=True
                              )
            draw.reset()
    if type[1:] == SelectType.circle.value:
        # if circle draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(draw.locations[0]),
                              shape=int(draw.wheel_size),
                              size=int(draw.wheel_size),
                              poly_type=-2,
                              static=True,
                              foreground=True
                              )
            draw.reset()
    return draw, phys


def draw_shape(draw, phys, event, x, y, type):
    if type[1:] == SelectType.draw.value:
        # If polygon draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            conts = cv2.convexHull(np.array(draw.locations))
            poly = Polygon(conts.squeeze())
            coords = poly.exterior.coords
            cen = poly.centroid
            coords = [(int(co[0] - cen.x), int(co[1] - cen.y)) for co in coords]
            phys.create_block(pos=(cen.x, cen.y), poly_type=1, shape=coords)
            draw.reset()
    elif type[1:] == SelectType.rectangle.value:
        # if rectangle draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(0, 0),
                              shape=(draw.locations[0], draw.locations[-1]),
                              poly_type=1,
                              static=False,
                              sq_points=True
                              )
            draw.reset()
    if type[1:] == SelectType.circle.value:
        # if circle draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_block(pos=(draw.locations[0]),
                              shape=int(draw.wheel_size),
                              size=int(draw.wheel_size),
                              poly_type=2,
                              static=False
                              )
            draw.reset()
    return draw, phys


def player_draw_click_or_circle(draw, phys, event, x, y, type, allow_clicked=True, log_clicked=False,
                                insist_clicked=False, allow_multiple=True):
    # get player if clicked
    clicked = None
    if allow_clicked and event == cv2.EVENT_LBUTTONDOWN:
        clicked, coords = get_clicked(phys.block_list, x, y)
        if not clicked is None:
            if log_clicked:
                if allow_multiple or len(draw.player_list) == 0:
                    draw.log_player(clicked)
            else:
                return draw, phys, clicked

    if not clicked is None or (insist_clicked is False or len(draw.player_list) > 0):
        # if poly draw poly and return coords if found
        if type[1:] == SelectType.draw.value:
            if event == cv2.EVENT_LBUTTONDOWN:
                if draw.status == None or draw.status == "poly":
                    ans = draw.log_point(x, y, "poly")
                if ans is True:
                    return draw, phys, True

        elif type[1:] == SelectType.player_select.value:
            if event == cv2.EVENT_LBUTTONDOWN:
                draw, phys, clicked, coords = select_player(draw, phys, x, y, "rotate", "rectangle_draw",
                                                            allow_mul=True)
                if not clicked is None:
                    return draw, phys, True

            elif event == cv2.EVENT_MOUSEMOVE and draw.status in ["rectangle_draw"]:
                draw.log_point(x, y, draw.status)

            elif event == cv2.EVENT_LBUTTONUP:
                if draw.status in ["rectangle_draw"]:
                    return draw, phys, True

            return draw, phys, False

        elif type[1:] == SelectType.player_distance.value:
            if event == cv2.EVENT_MOUSEMOVE and draw.status in ["rotate"]:
                draw.log_point(x, y, draw.status)
            elif event == cv2.EVENT_LBUTTONUP:
                draw.log_point(x, y, draw.status)
                return draw, phys, True
            return draw, phys, False

        # if rectangle draw and return if found
        elif type[1:] == SelectType.rectangle.value or type[1:] == SelectType.select.value or type[
                                                                                              1:] == SelectType.rectangle_and_move.value:
            if event == cv2.EVENT_LBUTTONDOWN:
                if draw.status is None:
                    draw.log_point(x, y, "rectangle_draw")

                elif draw.status in ["rectangle_draw"]:

                    draw.status = "rectangle_move"

                elif draw.status in ["rectangle_move"]:
                    return draw, phys, True

            elif event == cv2.EVENT_MOUSEMOVE and draw.status in ["rectangle_draw"]:
                draw.log_point(x, y, draw.status)

            ##removed this and added
            elif event == cv2.EVENT_MOUSEMOVE and draw.status in ["rectangle_move"]:
                arr = np.array((draw.locations[0], [draw.locations[-1][0], draw.locations[0][1]], draw.locations[-1],
                                [draw.locations[0][0], draw.locations[-1][1]]))
                poly = Polygon(arr)
                x_diff = int(x - poly.centroid.x)
                y_diff = int(y - poly.centroid.y)
                from shapely import affinity as af
                poly = af.translate(poly, x_diff, y_diff)

                draw.locations[0] = poly.exterior.coords[0]
                draw.locations[-1] = poly.exterior.coords[2]

                draw.status = "rectangle_move"

            elif event == cv2.EVENT_LBUTTONUP:
                if type[1:] == SelectType.select.value and draw.status in ["rectangle_draw"]:
                    return draw, phys, True
                elif type[1:] == SelectType.rectangle.value and draw.status in ["rectangle_draw"]:
                    return draw, phys, True

        elif type[1:] == SelectType.circle.value or type[1:] == SelectType.circle_and_move.value:

            if event == cv2.EVENT_LBUTTONDOWN:
                if draw.status is None:
                    draw.log_point(x, y, "circle_draw")
                elif draw.status in ["circle_move"]:
                    return draw, phys, True
                elif draw.status in ["circle_draw"]:
                    if type[1:] == SelectType.circle_and_move.value:
                        draw.status = "circle_move"
                        draw.locations = [[x, y]]
                    else:
                        return draw, phys, True

            elif event == cv2.EVENT_MOUSEMOVE and draw.status in ["circle_draw"]:
                draw.log_point(x, y, "circle_draw")
                distance = calculateDistance(draw.locations[-1][0], draw.locations[-1][1], draw.locations[0][0],
                                             draw.locations[0][1])
                old_distance = calculateDistance(draw.locations[-2][0], draw.locations[-2][1], draw.locations[0][0],
                                                 draw.locations[0][1])
                if distance > old_distance:
                    draw.wheel_size += 2
                else:
                    draw.wheel_size -= 2
                draw.status = "circle_draw"
            elif draw.status in ["circle_move"]:
                draw.status = "circle_move"
                draw.locations = [[x, y]]


        elif type[1:] == SelectType.line_join.value:

            if event == cv2.EVENT_LBUTTONDOWN:
                draw, phys, clicked, coords = select_player(draw, phys, x, y, "line_draw", allow_mul=True)

            elif event == cv2.EVENT_MOUSEMOVE and draw.status == "line_draw":

                if calculateDistance(draw.locations[0][0], draw.locations[0][1], x, y) > 10:
                    draw.log_point(x, y, "line_draw")
                if len(draw.player_list) == 2 and draw.status == "line_draw":
                    return draw, phys, True

        elif type[1:] == SelectType.d_straight_join.value:

            if event == cv2.EVENT_LBUTTONDOWN:

                clicked, shape = get_clicked(phys.block_list, x, y, 8)

                # get inital player
                if not clicked is None and draw.status is None:
                    draw.log_player(clicked)
                    draw.log_point(x, y, "double_dist")
                # log second click
                elif not clicked is None and draw.status == "double_dist":
                    draw.log_point(x, y, "double_dist")
                    draw.status = "double_dist1"

                elif not clicked is None and draw.status == "double_dist1" and len(draw.player_list) == 1:
                    draw.log_player(clicked)
                    draw.log_point(x, y, "double_dist1")

                elif not clicked is None and draw.status == "double_dist1" and len(draw.player_list) == 2:
                    draw.log_point(x, y, "double_dist1")
                    return draw, phys, True

            elif event == cv2.EVENT_MOUSEMOVE:
                if draw.status in ["double_dist", "double_dist1"]:
                    draw.log_point(x, y, draw.status)

            return draw, phys, False

        elif type[1:] == SelectType.straight_join.value:

            if event == cv2.EVENT_LBUTTONDOWN:

                clicked, shape = get_clicked(phys.block_list, x, y, 8)

                if not clicked is None:
                    draw.log_player(clicked)
                    draw.log_point(x, y, "distance", )

                if draw.status == "distance" and len(draw.locations) != 1 and len(draw.player_list) == 2:
                    return draw, phys, True

            if event == cv2.EVENT_MOUSEMOVE:
                if draw.status == "distance":
                    draw.log_point(x, y, "distance")

        elif type[1:] == SelectType.distance.value:

            if len(draw.locations) == 0:
                draw.status = "distance"
                draw.log_point(x, y, "distance")
            else:
                if event == cv2.EVENT_LBUTTONDOWN:
                    if len(draw.locations) > 1:
                        return draw, phys, True
                elif event == cv2.EVENT_MOUSEMOVE:
                    draw.log_point(x, y, "distance")

            return draw, phys, False

        elif type[1:] == SelectType.length.value:

            if len(draw.locations) == 0:
                draw.status = "length"
                draw.log_point(x, y, "length")
            else:
                if event == cv2.EVENT_LBUTTONDOWN:
                    if len(draw.locations) > 1:
                        return draw, phys, True
                elif event == cv2.EVENT_MOUSEMOVE:
                    draw.log_point(x, y, "length")

            return draw, phys, False

        elif type[1:] == SelectType.bullet_direction.value:

            """
            used to fire objects from mouse click/drag
            """

            # remove status if new type
            # print(draw.status)

            players = [bl for bl in phys.block_list if bl.is_player]

            if len(players) > 0:
                # set inital
                center = players[0].body.worldCenter
                draw.status = "bullet"
                if draw.locations == []:
                    draw.locations.append([int(x) for x in convert_from_mks(center.x, center.y)])
                else:
                    draw.locations[0] = [int(x) for x in convert_from_mks(center.x, center.y)]

                if event == cv2.EVENT_MOUSEMOVE and draw.status == "bullet":
                    draw.log_point(x, y, "bullet")
                    pt1 = np.array(draw.locations[0])
                    pt2 = np.array(draw.locations[-1])
                    impulse = (((pt1[0] - pt2[0]) * -1) * 2, ((pt1[1] - pt2[1]) * -1) * 2)
                    draw.vector = convert_to_mks(impulse[0], impulse[1])

                if event == cv2.EVENT_LBUTTONDOWN and draw.status == "bullet":
                    return draw, phys, True

            return draw, phys, False

        elif type[1:] == SelectType.vector_direction.value:

            """
            used to fire objects from mouse click/drag
            """

            # remove status if new type
            # print(draw.status)
            returnme = False
            if event == cv2.EVENT_LBUTTONDOWN and draw.status == None:
                # check if player clicked or empty space
                draw, phys, clicked, coords = select_player(draw, phys, x, y, "fire", "fire")
            elif event == cv2.EVENT_LBUTTONDOWN and draw.status == "fire":
                returnme = True

            elif event == cv2.EVENT_MOUSEMOVE and draw.status == "fire":
                draw.log_point(x, y, "fire")

            elif event == cv2.EVENT_LBUTTONUP:  # and draw.status == "fire":
                returnme = True

            if returnme and len(draw.locations) > 1:
                draw.log_point(x, y, "fire")
                pt1 = np.array(draw.locations[0])
                pt2 = np.array(draw.locations[-1])
                impulse = (((pt1[0] - pt2[0]) * -1) * 2, ((pt1[1] - pt2[1]) * -1) * 2)
                draw.vector = convert_to_mks(impulse[0], impulse[1])
                return draw, phys, True

            return draw, phys, False

        elif type[1:] == SelectType.rotation_select.value:

            if event == cv2.EVENT_LBUTTONDOWN:

                draw, phys, clicked, coords = select_player(draw, phys, x, y, "rotation", allow_mul=True)

                if len(draw.player_list) == 2 and draw.status == "rotation":
                    draw.locations = []
                    draw.status = "rotation_pos"
                    draw.log_point(x, y, "rotation_pos")

                elif draw.status == "rotation_pos":

                    draw.log_point(x, y, "rotation_pos")
                    return draw, phys, True
        elif type[1:] == SelectType.select_point.value:
            if event == cv2.EVENT_LBUTTONDOWN:
                draw.locations.append([x, y])
                return draw, phys, True
        return draw, phys, False



    else:
        draw.reset()
        return draw, phys, False


def get_enlongated_line(coordsStart):
    changes = 999
    new_coords = []
    while True:
        changes = 0
        if new_coords == []:
            coords = coordsStart
        new_coords = []
        for i in range(len(coords) - 2):
            pointA = coords[i]
            pointB = coords[i + 1]
            distance = calculateDistance(pointA[0], pointA[1], pointB[0], pointB[1])
            new_coords.append(pointA)
            if distance > 10:
                new_coords.append((((pointA[0] + pointB[0]) / 2), ((pointA[1] + pointB[1]) / 2)))
                changes += 1

            if i == len(coords) - 3:
                new_coords.append(pointB)

        coords = new_coords
        if changes == 0:
            break
    return coords


def get_poly_from_two_rectangle_points(loca, locb):
    arr = np.array((loca, [locb[0], loca[1]], locb, [loca[0], locb[1]]))
    poly = Polygon(arr)
    return poly


def get_set_selected(draw, phys, new_status, reset_on_none=True, last_loc=False):
    # gets and sets the selected plays - if nothing selected then then reset
    if len(draw.locations) <= 1:
        draw.reset()
        return draw, phys
    # get poly from select rectangle
    poly = np.array(get_squ(draw.locations[0], draw.locations[-1 if last_loc is True else 1]))
    # check which blocks are contained in it
    contains = check_contains_all(phys.block_list, poly)
    # if none then reset
    if contains == []:
        draw.reset()
    # else log the players as selected
    [draw.log_player(bl) for bl in contains]
    # turn them into sensors for the move so no colision
    for bl in draw.player_list:
        bl.sensor = True
    draw.status = new_status
    draw.locations = []

    if reset_on_none:
        if draw.player_list == []:
            draw.reset()
    return draw, phys


def select_player(draw, phys, x, y, if_found=None, if_not=None, reset_if_not=False, pause=True, allow_mul=False,
                  select_all=False):
    clicked, coords = get_clicked(phys.block_list, x, y)
    if not clicked is None:
        if len(draw.player_list) == 0 or allow_mul:
            clicked, coords = get_clicked(phys.block_list, x, y)
            draw.log_player(clicked)
            # also add players connected by rotation joints as it messes things up if not
            if select_all:
                players = [clicked]
                for pl in players:
                    for jn in pl.body.joints:
                        if type(jn.joint) == b2RevoluteJoint:
                            if jn.joint.bodyA.userData["ob"] == pl and jn.joint.bodyB.userData[
                                "ob"] not in draw.player_list:
                                draw.log_player(jn.joint.bodyB.userData["ob"])
                                players.append(jn.joint.bodyB.userData["ob"])
                            if jn.joint.bodyB.userData["ob"] == pl and jn.joint.bodyA.userData[
                                "ob"] not in draw.player_list:
                                draw.log_player(jn.joint.bodyA.userData["ob"])
                                players.append(jn.joint.bodyA.userData["ob"])

            draw.pause = pause
            if not if_found is None:
                draw.log_point(x, y, if_found)
                return draw, phys, clicked, coords

    if not if_not is None:
        draw.log_point(x, y, if_not)
    if reset_if_not and len(draw.player_list) == 0:
        draw.reset()

    return draw, phys, clicked, coords


def get_players_with_mouse(draw, return_joint=False):
    for pl in draw.player_list:
        for jn in pl.body.joints:
            if type(jn.joint) == b2MouseJoint:
                if return_joint:
                    return pl, jn.joint
                else:
                    return pl


def clone_players(draw, phys):
    # get items
    item_list = []
    for bl in draw.player_list:
        item_list.append(phys.save_block_as_dict(bl))

    # clone them
    new_obs = phys.create_pre_def_block(item_list, convert_joints=False)
    draw.player_list = phys.block_list[-new_obs:]
    draw.clone_created = True
    return draw, phys


def move_players(draw, phys):
    blocks_to_create = []
    players = 0
    # get mouse difference
    x_dif = draw.locations[1][0] - draw.locations[0][0]
    y_dif = draw.locations[1][1] - draw.locations[0][1]
    # loop players backwards so they can be deleted
    for i in np.arange(len(draw.player_list) - 1, -1, -1):
        # get last player
        bl = draw.player_list[i]
        # pickle the details
        bl_dic = phys.save_block_as_dict(bl)
        # update the position
        bl_dic["body"]["position"][0] += convert_to_mks(x_dif)
        bl_dic["body"]["position"][1] += convert_to_mks(y_dif)

        # update the anchors for rotation and weld_joints
        for k, v in bl_dic["joints"].items():
            if "anchorA" in bl_dic["joints"][k]:
                ids = [x.id for x in draw.player_list]
                if bl_dic["joints"][k]["bodyA"] in ids:
                    bl_dic["joints"][k]["anchorA"][0] += convert_to_mks(x_dif)
                    bl_dic["joints"][k]["anchorA"][1] += convert_to_mks(y_dif)
                if bl_dic["joints"][k]["bodyB"] in ids:
                    bl_dic["joints"][k]["anchorB"][0] += convert_to_mks(x_dif)
                    bl_dic["joints"][k]["anchorB"][1] += convert_to_mks(y_dif)

        # delete old
        del draw.player_list[draw.player_list.index(bl)]
        phys.delete(bl)
        # add pickle details to list
        blocks_to_create.append(bl_dic)
        players += 1

    # recreate new players
    phys.create_pre_def_block(blocks_to_create, convert_joints=False)
    # log players
    for x in range(players):
        ite = x + 1
        draw.log_player(phys.block_list[-ite])

    return draw, phys


def move_clone(draw, phys, x=None, y=None, event=None, clone=None):
    if event == cv2.EVENT_LBUTTONDOWN:

        # for moving selected
        if draw.status == "move":
            draw.log_point(x, y, "move")
            return draw, phys

        # for fresh select if no player selected then log as select
        draw, phys, clicked, coords = select_player(draw, phys, x, y, "move", "select", select_all=True)


    elif event == cv2.EVENT_MOUSEMOVE and len(draw.locations) > 0:
        # for actually moving players
        if draw.status == "move":
            draw.log_point(x, y, "move")
            # save_details of each item in list - this method is used to pickling their state.
            # this is for cloning the players
            if clone is True and not draw.clone_created:
                draw, phys = clone_players(draw, phys)
            ##
            # this is for moving the players
            ##
            draw, phys = move_players(draw, phys)
        else:
            # this is for logging of the movment when selecting to draw the recangle box
            draw.log_point(x, y, "select")

    elif event == cv2.EVENT_LBUTTONUP:
        if draw.status == "move":
            for bl in draw.player_list:
                bl.body.active = True
                bl.body.awake = True
                bl.body.sensor = False
            draw.reset()
            draw.pause = False
        elif draw.status == "select":
            # set players if move is
            try:
                draw, phys = get_set_selected(draw, phys, "move")
            except:
                # select error
                draw.reset()

    return draw, phys


def make_player(draw, phys, event, x, y, cur_key):
    if event == cv2.EVENT_LBUTTONDOWN:
        draw, phys, clicked, coords = select_player(draw, phys, x, y, None, None, reset_if_not=True, pause=False)
        if not clicked is None:
            for bl in phys.block_list:
                if bl == clicked:
                    bl.is_player = True
                else:
                    bl.is_player = False
            draw.reset()
    return draw, phys


def mouse_joint_move(draw, phys, x=None, y=None, event=None, cur_key=None):
    if event == cv2.EVENT_LBUTTONDOWN:

        draw, phys, clicked, coords = select_player(draw, phys, x, y, None, None, pause=False)

        if not clicked is None:
            # cant move static blocks
            if clicked.static is True:
                draw.reset()
                return draw, phys
            phys.create_mouse_joint(clicked, x, y)
            draw.status = "move"
            clicked.body.awake = True
            clicked.body.active = True
            clicked.body.awake = True

    elif event == cv2.EVENT_MOUSEMOVE and draw.status == "move":
        # change location to move to
        # phys.world.joints
        block, joint = get_players_with_mouse(draw, True)
        joint.target = convert_to_mks(x, y)
        block.body.active = True
        block.body.awake = True


    elif event == cv2.EVENT_LBUTTONUP and draw.status == "move":
        block, joint = get_players_with_mouse(draw, True)
        # del draw.mouse
        phys.world.DestroyJoint(joint)
        draw.reset()

    return draw, phys
