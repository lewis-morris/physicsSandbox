import copy
import random

import cv2
import numpy as np

from shapely import affinity

from draw_functions import SelectType
from functions import get_config, convert_from_mks, create_floor_poly, rotate_around_point_highperf
from gui import save_gui, load_gui, load_options, update_background, get_key_gui, get_select_joints_with_motor, \
    terrain_complexity_gui
from objects import Messenger, load, pickler
import PySimpleGUI as sg
from shapely.geometry import Polygon
from functions import get_squ, check_contains_all, get_clicked, convert_to_mks, calculateDistance, get_all_in_poly
from Box2D import b2MouseJoint, b2RevoluteJoint


def action_key_press(key, cur_key_type, cur_key, draw, phys, msg, timer, board, force):
    """
    Deal with the key presses
    :param key:
    :return:
    """

    # delete any old mouse joints prior to dealing with the next keypress
    if key != ord("m") and msg.message != "Mouse Move" and cur_key_type == 0:
        for jn in phys.world.joints:
            if type(jn) is b2MouseJoint:
                phys.world.DestroyJoint(jn)

    if key == 255:
        pass

    elif key == ord("r") and cur_key_type == 0:
        # RESET SCREEN
        if sg.popup_yes_no("Are you sure you want to reset?") == "Yes":
            draw.reset()
            msg = Messenger(phys.options["screen"]["fps"], board)
            msg.set_message("Reset")
            board.reset = True

    elif key == ord("q") and cur_key_type == 0:
        # QUIT
        msg.set_message("Quit")
        val = sg.popup_yes_no("Are you sure you want to quit?")
        if val == "Yes":
            board.run = False


    elif key == ord("z") and cur_key_type == 0:
        # SPAWN
        msg.set_message("Spawn")
        phys.create_block()

    elif key == ord("u") and cur_key_type == 0:
        # draw delete blocks
        draw.reset()
        options = {"Remove Joints": SelectType.select}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("x") and cur_key_type == 0:
        # draw delete blocks
        draw.reset()
        options = {"Delete": SelectType.select}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("p") and cur_key_type == 0:
        # draw polygon
        draw.reset()
        # msg.set = {"Dynamic Block": draw.get_draw_type()}
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Dynamic Block")

    elif key == ord("g") and cur_key_type == 0:
        # draw ground
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Static Block")
        # options = {"Static Block": draw.get_draw_type()}

        # cur_key = msg.auto_set(options, key, force)

    elif key == ord("i") and cur_key_type == 0:
        # draw terrain

        draw.reset()
        options = {"Generate Terrain": SelectType.null}
        cur_key = msg.auto_set(options, key, force)

        draw, phys, board = create_terrain(draw, phys, board=board)


    elif key == ord("f") and cur_key_type == 0:
        # draw fragments or select
        draw.reset()
        options = {
            "Frament Select": SelectType.select}  # "Fragment Poly": SelectType.draw, "Frament Rectangle": SelectType.rectangle,
        # "Frament Select": SelectType.select}
        cur_key = msg.auto_set(options, key, force)


    elif key == ord("1") and cur_key_type == 0:
        # fire polygon
        draw.reset()
        options = {"Create": SelectType.select_point, "Fire Block": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("4") and cur_key_type == 0:
        # select
        # draw ground
        draw.reset()
        options = {"Joint Update": SelectType.select}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord(";") and cur_key_type == 0:
        # select
        # draw ground
        draw.reset()
        options = {"Player Update": SelectType.select}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("2") and cur_key_type == 0:
        # Mouse Move
        draw.reset()
        options = {"Rotate": SelectType.player_select}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("m") and cur_key_type == 0:
        # Mouse Move
        draw.reset()
        options = {"Mouse Move": SelectType.select, "Normal Move": SelectType.null, "Joint Move": SelectType.null,
                   "Clone Move": SelectType.null}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("t") and cur_key_type == 0:
        # Mouse Move
        draw.reset()
        options = {"Transform": SelectType.player_select}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("e") and cur_key_type == 0:
        # draw ropes
        if sg.popup_yes_no("Are you sure you want to kill all blocks?") == "Yes":
            draw.reset()
            phys.kill_all(static=False)
            msg.set_message("Remove Blocks")
            cur_key = "e"

    elif key == ord("v") and cur_key_type == 0:
        # draw ropes
        draw.reset()
        msg.set_message("Set Spawn")
        cur_key = "v"

    elif key == ord("h") and cur_key_type == 0:
        # draw fragment ALL players
        # cur_key = "h"
        msg.set_message("Frag All")
        draw.reset()
        blocks = [bl for bl in phys.block_list if not bl.static is True and not bl.is_terrain is True]
        phys.fractal_block(blocks, create=False, board=board)

    elif key == ord("k") and cur_key_type == 0:
        # draw splitter sensor
        draw.reset()

        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Force")


    elif key == ord("l") and cur_key_type == 0:
        # draw splitter sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Splitter")


    elif key == ord("/") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Impulse")


    elif key == ord("'") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Goal")


    elif key == ord("~") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Motor Switch")

    elif key == ord("&") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Water")


    elif key == ord("^") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Low Gravity")


    elif key == ord("#") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Gravity Switch")

    elif key == ord(")") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Center")

    elif key == ord("%") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Sticky")

    elif key == ord("£") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Enlarger")


    elif key == ord("$") and cur_key_type == 0:
        # draw booster sensor
        draw.reset()
        cur_key = chr(key) + str(draw.get_draw_type().value)
        msg.set_message("Shrinker")


    elif key == ord("0") and cur_key_type == 0:
        # pause physics
        phys.force_draw_all = not phys.force_draw_all
        options = {"Draw All": SelectType.null, "Draw Set": SelectType.null}
        cur_key = msg.auto_set(options, key, force)



    elif key == ord("o") and cur_key_type == 0:
        # pause physics
        draw.reset()
        phys.pause = not phys.pause
        msg.set_message("Pause" + (" On" if phys.pause is True else " Off"))
        cur_key = "o"

    elif key == ord("*") and cur_key_type == 0:
        # PICKLE BOARD
        name, blurb = save_gui()
        if not name == None:
            pickler(timer, phys, draw, board, msg, name, blurb)
            msg.set_message("State Saved")
            cur_key = "*"
            draw.reset()

    elif key == ord("-"):
        # LOAD BOARD

        timer, phys, draw, board, msg = load_gui(timer, phys, draw, board, msg, persistant=False)
        config = phys.config

    elif key == ord("5") and cur_key_type == 0:

        load_options()
        phys.change_config(board=board)

    elif key == ord("6") and cur_key_type == 0:

        board, phys, msg = update_background(board, phys, msg)


    elif key == ord("j") and cur_key_type == 0:
        # draw joints
        draw.reset()
        options = {"Merge Blocks": SelectType.select,
                   "Distance Joint": SelectType.straight_join, "Rope Joint": SelectType.straight_join,
                   "Prismatic Joint": SelectType.straight_join,
                   "Electric": SelectType.line_join, "Springy Rope": SelectType.line_join,
                   "Chain": SelectType.line_join2,
                   "Weld Joint": SelectType.straight_join, "Wheel Joint": SelectType.circle,
                   "Rotation Joint": SelectType.rotation_select, "Pulley": SelectType.d_straight_join}

        cur_key = msg.auto_set(options, key, force)



    elif key == 9:
        # Tab key press, this switches to move mode
        if cur_key_type == 0:
            cur_key_type = 1
            msg.set_message("Drawing Mode Enabled")
            draw.reset()
        else:
            cur_key_type = 0
            msg.set_message("Create Mode Enabled")
            draw.reset()


    # Drawing mode buttons

    elif key == ord("`") and cur_key_type == 1:
        # Mouse Move
        draw.reset()
        options = {"Change Keys": SelectType.select}
        cur_key = msg.auto_set(options, key, force)


    elif key == ord("1") and cur_key_type == 1:
        # Mouse Move
        draw.reset()
        options = {"Screen Move": SelectType.null}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("2") and cur_key_type == 1:
        # Mouse Move
        draw.reset()
        options = {"Center Clicked": SelectType.null}
        cur_key = msg.auto_set(options, key, force)


    elif key == ord("]") and cur_key_type == 1:
        # draw polygon
        draw.reset()
        options = {"Fire Bullet": SelectType.bullet_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("[") and cur_key_type == 1:
        # draw polygon
        draw.reset()
        options = {"Choose Player": SelectType.null}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("3") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        options = {"Motor Forwards": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("4") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        options = {"Motor Backwards": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("9") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        cur_key = chr(key) + str(SelectType.vector_direction.value)
        msg.set_message("Force")

    elif key == ord("0") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        options = {"Relative Force": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("5") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        options = {"Rotate CCW": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("6") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        options = {"Rotate CW": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("7") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        cur_key = chr(key) + str(SelectType.vector_direction.value)
        msg.set_message("Impulse")


    elif key == ord("8") and cur_key_type == 1:
        # draw polygon

        draw.reset()
        options = {"Relative Impulse": SelectType.vector_direction}
        cur_key = msg.auto_set(options, key, force)

    elif key == ord("!") and cur_key_type == 1:
        """
        Used to attach an relative impulse to a block
        """
        board.translation = np.array([0, 0])

    # do move keypresses:
    if cur_key_type == 1:
        phys.do_keypress(key)

    return cur_key_type, cur_key, draw, phys, msg, timer, board


def rotate_block(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.player_select.value:
        if draw.stage == 0:
            draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
            if ans is True:
                if len(draw.player_list) > 0:
                    draw.stage += 1
                    draw.locations = [[x, y]]
                    draw.status = "rotate"
                elif len(draw.locations) > 1:
                    draw, phys = get_set_selected(draw, phys, "rotate", last_loc=True, board=board)
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


def transform_block(draw, phys, event, x, y, type, board=None):
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

                        draw.player_list.append(bl_new)
                        draw.player_list[i].alive = True
                        draw.player_list[i].awake = True
                        del bl

            if ans is True:
                draw.reset()
    return draw, phys


def change_size(phys, block, up=True):
    block_info = phys.save_block_as_dict(block)

    for k, v in block_info["shapes"].items():

        if v["type"].find("Poly") > -1:
            old_poly = Polygon(v["shape"])
            if up:
                poly_new = affinity.scale(old_poly, 1.05, 1.05)

            else:
                poly_new = affinity.scale(old_poly, .95, .95)
                if poly_new.area < convert_to_mks(0.5):
                    poly_new = old_poly

            # new_pos = [[x[0] - center.x, x[1] - center.y] for x in list(old_poly.exterior.coords)]
            block_info["shapes"][k]["shape"] = poly_new.exterior.coords


        else:
            if up:
                block_info["shapes"][k]["radius"] *= 1.05

            else:
                block_info["shapes"][k]["radius"] *= 0.95

                if block_info["shapes"][k]["radius"] < convert_to_mks(4):
                    block_info["shapes"][k]["radius"] = convert_to_mks(4)

    phys.delete(block)
    phys.create_pre_def_block([block_info], resize=True)
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

        block.sensor["type"] = ty

        if ty == "center":
            block.sensor["options"] = {"translation": str(phys.board.translation), "allow_multiple_fires": False,
                                       "fire_action_once_contained": True}

        if ty == "goal":
            block.sensor["options"] = {"reset_on_player_hit": True, "fire_action_once_contained": True}

        if ty == "gravity":
            block.sensor["options"] = {"reverse_keys_on_hit": True, "fire_action_once_contained": True}

        if ty == "lowgravity":
            block.sensor["options"] = {"gravity_scale": 0.05, "fire_action_once_contained": True}

        if ty == "water":
            block.sensor["options"] = {"density": 10}
            block.body.fixtures[0].density = 10
            block.set_mass()

        if ty == "motorsw":
            block.sensor["options"] = {"id_to_switch": ""}

        if ty == "splitter":
            block.sensor["options"] = {"min_split_area": "500", "allow_multiple_fires": False,
                                       "fire_action_once_contained": True}

        if ty == "shrinker":
            block.sensor["options"] = {"min_area": "300", "allow_multiple_fires": True, "shrink_ratio": 0.05,
                                       "fire_action_once_contained": True}

        if ty == "enlarger":
            block.sensor["options"] = {"max_area": "10000", "allow_multiple_fires": True, "enlarge_ratio": 1.05,
                                       "fire_action_once_contained": True}

        block.colour = (66, 218, 245)
        block.draw_me = True

        draw.stage += 1

        draw.locations = []
        # poly = block.get_poly()
        # cenX = int(poly.centroid.x)
        # cenY = int(poly.centroid.y)
        draw.log_point(block.centroid[0] - draw.board.translation[0], block.centroid[1] - draw.board.translation[1],
                       "fire")

        if ty in ["shrinker", "center", "enlarger", "gravity", "splitter", "lowgravity", "goal", "water", "sticky",
                  "motorsw"]:
            block.sensor["data"] = block.id
            block.colour = (162, 239, 242)
            draw.stage = 0
            draw.reset()
            return draw, phys

    if draw.stage == 1:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y,
                                                      type[0] + str(SelectType.vector_direction.value), False)
        if ans == True:

            block = phys.block_list[-1]
            for fix in block.body.fixtures:
                fix.sensor = True
            block.sensor["type"] = ty
            block.sensor["options"] = {"vector": draw.vector, "fire_action_once_contained": True,
                                       "allow_multiple_fires": False}

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


def merge_blocks(draw, phys, event, x, y, type):
    if type[1:] == SelectType.select.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, True)
        if ans is True:
            coors = list(get_poly_from_two_rectangle_points(draw.locations[0], draw.locations[-1]).exterior.coords)
            selected = get_all_in_poly(phys, coors)
            if not selected == []:
                phys.merge_blocks(selected)
                draw.reset()
            else:
                draw.reset()
        elif ans is False:

            pass
        else:
            if len(draw.player_list) == 2:
                phys.merge_blocks(draw.player_list)
                draw.reset()

    # if type[1:] == SelectType.player_select.value:
    #     draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
    #                                                   allow_clicked=True, log_clicked=True,
    #                                                   allow_multiple=True)
    #     if len(set(draw.player_list)) == 2:
    #         phys.merge_blocks(draw.player_list)
    #         draw.reset()
    #     elif ans == True:
    #         coors = list(get_poly_from_two_rectangle_points(draw.locations[0],draw.locations[-1]).exterior.coords)
    #         selected = get_all_in_poly(phys, coors)
    #         if not selected is False or not selected == []:
    #             phys.merge_blocks(selected)
    #             draw.reset()
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


def fire_bullet(draw, phys, event, x, y, typer, board):
    draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, typer,
                                                  allow_clicked=True, log_clicked=True,
                                                  allow_multiple=False, board=board)

    if ans == True:
        player = [bl for bl in phys.block_list if bl.can_fire][0]

        center = player.body.worldCenter
        center = convert_from_mks(center.x, center.y)

        width = 5

        if 5 < width:
            width = 5

        # set speed and restrict to max speed in settings

        if not draw.vector is None:
            vector = np.array(draw.vector)
            phys.create_block(pos=center, poly_type=1, size=width, draw=True)
            phys.block_list[-1].set_as_bullet(vector, player.id, phys.options["player"]["bullets_destory_ground"])

        draw.reset()

    return draw, phys


def rotate_attach(draw, phys, event, x, y, type, board=None, direction=None):
    if event == cv2.EVENT_LBUTTONDOWN:
        draw, phys, clicked, coords = select_player(draw, phys, x, y, None, None, reset_if_not=True, pause=False)
        if not clicked is None:
            key = get_key_gui()
            if not key is None:
                clicked.add_move(key, "rotate", direction)
            draw.reset()

    return draw, phys


def attach_motor_spin(draw, phys, event, x, y, type, board=None, clockwise=True):
    if event == cv2.EVENT_LBUTTONDOWN:
        draw, phys, clicked, coords = select_player(draw, phys, x, y, None, None, reset_if_not=True, pause=False)
        if not clicked is None:
            joint = get_select_joints_with_motor(clicked)
            if not joint is None:
                key = get_key_gui()
                joint_id = clicked.body.joints[int(joint.split("-")[0])].joint.userData["id"]
                dir = "motor backwards" if clockwise else "motor forwards"
                clicked.add_move(key, dir, joint_id, joint_id)
            draw.reset()

    return draw, phys


def add_force(draw, phys, event, x, y, type, board=None, relative=False):
    if type[1:] == SelectType.vector_direction.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
                                                      allow_clicked=True, log_clicked=True, insist_clicked=True,
                                                      allow_multiple=False, board=board)
        if ans == True:
            if len(draw.player_list) > 0:
                for bl in draw.player_list:
                    key = get_key_gui()
                    bl.add_move(key, "relative force" if relative else "force", draw.vector)

                    draw.reset()

    return draw, phys


def add_impulse(draw, phys, event, x, y, type, board=None, relative=False):
    if type[1:] == SelectType.vector_direction.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
                                                      allow_clicked=True, log_clicked=True, insist_clicked=True,
                                                      allow_multiple=False, board=board)
        if ans == True:
            if len(draw.player_list) > 0:
                for bl in draw.player_list:
                    key = get_key_gui()
                    if not key is None:
                        bl.add_move(key, "relative impulse" if relative else "impulse", draw.vector)
                    draw.reset()

    return draw, phys


def fire(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.vector_direction.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type,
                                                      allow_clicked=True, log_clicked=True,
                                                      allow_multiple=False, board=board, blocks_only=True)
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
                                                      allow_multiple=False, blocks_only=True)
        if ans == True:
            phys.create_block(pos=draw.locations[0])
            draw.reset()

    return draw, phys


def select_blocks(draw, phys, event, x, y, type, board=None):
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


def get_spawn(draw, phys, event, x, y, type, board=None):
    if event == cv2.EVENT_LBUTTONDOWN:
        draw.log_point(x, y, "rectangle_draw")

    elif event == cv2.EVENT_MOUSEMOVE:
        if draw.status == "rectangle_draw":
            draw.log_point(x, y, "rectangle_draw")

    elif event == cv2.EVENT_LBUTTONUP:
        draw.log_point(x, y, "rectangle_draw")
        return draw, phys, True, list(
            get_poly_from_two_rectangle_points(draw.locations[0], draw.locations[-1]).exterior.coords)

    return draw, phys, False, None


def wheel_draw(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.circle.value:

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, True, True, True)

        if ans is True:
            phys.create_block(pos=draw.locations[0], poly_type=2, shape=draw.wheel_size, size=draw.wheel_size)
            phys.create_rotation_joint(draw.player_list[0], phys.block_list[-1], draw.locations[0])
            draw.reset()

    return draw, phys


def remove_joints(draw, phys, event, x, y, type, board=None):
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


def weld(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.straight_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_weld_joint(draw.player_list[0], draw.player_list[1], draw.locations[-1])
            draw.reset()
    return draw, phys


def distance_draw(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.straight_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_distance_joint(draw.player_list[0], draw.player_list[1], draw.locations[0], draw.locations[-1])
            draw.reset()

    return draw, phys


def prismatic(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.straight_join.value and draw.stage == 0:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)

        if ans is True:
            draw.stage += 1

    elif type[1:] == SelectType.straight_join.value and draw.stage == 1:

        draw.status = "length"

        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, "a" + str(SelectType.length.value),
                                                      False)
        if ans == True:
            distance = calculateDistance(draw.locations[0][0], draw.locations[0][1], draw.locations[-1][0],
                                         draw.locations[-1][1])

            pt1 = np.array(draw.locations[0])
            pt2 = np.array(draw.locations[-1])
            impulse = (((pt1[0] - pt2[0]) * -1) * 2, ((pt1[1] - pt2[1]) * -1) * 2)
            draw.vector = convert_to_mks(impulse[0], impulse[1])
            phys.create_prismatic(draw.player_list[0], draw.player_list[1], draw.vector, draw.locations[0],
                                  distance=distance)
            draw.reset()

    return draw, phys


def rope(draw, phys, event, x, y, type, board=None):
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


def lightning(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.line_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_lightening_joint(draw.player_list[0], draw.player_list[1], draw.locations)
            draw.reset()
    return draw, phys


def chainish(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.line_join.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            phys.create_chainish_joint(draw.player_list[0], draw.player_list[1], draw.locations)
            draw.reset()
    return draw, phys


def chain(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.line_join2.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            playerA, _ = get_clicked(phys.block_list, draw.locations[0][0], draw.locations[0][1], 4)
            playerB, _ = get_clicked(phys.block_list, draw.locations[0][0], draw.locations[0][1], 4)
            phys.create_chain(playerA, playerB, draw.locations)
            draw.reset()
    return draw, phys


def delete(draw, phys, event, x, y, type, board=None):
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


def create_terrain(draw, phys, board):
    slope_times_min, slope_times_max, x_stride_min, x_stride_max, y_stride_min, y_stride_max = terrain_complexity_gui()
    poly = create_floor_poly(board.b_width, board.b_height, slope_times_min, slope_times_max, x_stride_min,
                             x_stride_max, y_stride_min, y_stride_max, full_poly=True)
    phys.kill_all(terrain=True)

    coords = poly.exterior.coords

    last_coord = coords[-1]
    x_trans = (board.b_width - board.board.shape[1]) / 2
    y_trans = ((board.board.shape[0] - last_coord[1]) / 2) - 20
    coords = [[co[0] - x_trans, co[1] - 100 + y_trans] for co in coords]

    # phys.create_block(poly_type=5,shape=coords)

    phys.fractal_create(coords, terrain=True)

    # phys.merge_blocks(is_terrain=True)

    col = [1, 92, 40]
    for bl in phys.block_list:
        if bl.is_terrain == True:
            bl.colour = col
            col[2] += random.randint(0, 10)
            col[1] += random.randint(0, 10)

    return draw, phys, board


def draw_fragment(draw, phys, event, x, y, type, board=None):
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


def draw_ground(draw, phys, event, x, y, type, board=None):
    # Used to draw the ground elements
    if type[1:] == SelectType.draw.value:
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            starting_loc = len(phys.block_list)
            phys.fractal_block(np.array(draw.locations), create=True, static=True)
            phys.merge_blocks(phys.block_list[starting_loc:])
            phys.block_list[-1].get_current_pos(True)
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


def draw_foreground(draw, phys, event, x, y, type, board=None):
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


def draw_shape(draw, phys, event, x, y, type, board=None):
    if type[1:] == SelectType.draw.value:
        # If polygon draw
        draw, phys, ans = player_draw_click_or_circle(draw, phys, event, x, y, type, False)
        if ans is True:
            # conts = cv2.convexHull(np.array(draw.locations))
            # poly = Polygon(conts.squeeze())
            # coords = poly.exterior.coords
            # cen = poly.centroid
            # coords = [(int(co[0] - cen.x), int(co[1] - cen.y)) for co in coords]
            # phys.create_block(pos=(cen.x, cen.y), poly_type=1, shape=coords)
            starting_loc = len(phys.block_list)
            phys.fractal_block(np.array(draw.locations), create=True, static=False)
            phys.merge_blocks(phys.block_list[starting_loc:])
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
                                insist_clicked=False, allow_multiple=True, board=None, blocks_only=False):
    # get player if clicked
    clicked = None
    if allow_clicked and event == cv2.EVENT_LBUTTONDOWN:
        clicked, coords = get_clicked(phys.block_list, x, y, board, blocks_only=blocks_only)
        if not clicked is None:
            if log_clicked:
                if allow_multiple or len(draw.player_list) == 0:
                    draw.log_player(clicked)
                    if type[1:] == SelectType.bullet_direction.value:
                        phys.set_can_fire(clicked)
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

        elif type[1:] == SelectType.line_join2.value:

            if event == cv2.EVENT_LBUTTONDOWN:
                draw.log_point(x, y, "line_draw")
            elif event == cv2.EVENT_MOUSEMOVE and draw.status == "line_draw":
                if calculateDistance(draw.locations[0][0], draw.locations[0][1], x, y) > 10:
                    draw.log_point(x, y, "line_draw")
            elif event == cv2.EVENT_LBUTTONUP and draw.status == "line_draw":
                draw.log_point(x, y, "line_draw")
                return draw, phys, True

            return draw, phys, False

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
                    draw.log_point(x, y, "distance")

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

            fire_list = [bl for bl in phys.block_list if bl.can_fire]

            if len(fire_list) > 0:
                # set inital
                center = fire_list[0].body.worldCenter
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

                if event == cv2.EVENT_LBUTTONDOWN and draw.status == "bullet" and len(draw.locations) > 1:
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
                draw, phys, clicked, coords = select_player(draw, phys, x, y, "fire", "fire", board=board,
                                                            blocks_only=True)
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


def get_set_selected(draw, phys, new_status, reset_on_none=True, last_loc=False, board=None):
    # gets and sets the selected plays - if nothing selected then then reset
    if len(draw.locations) <= 1:
        draw.reset()
        return draw, phys
    # get poly from select rectangle
    poly = list(get_poly_from_two_rectangle_points(draw.locations[0],
                                                   draw.locations[-1 if last_loc is True else 1]).exterior.coords)
    # check which blocks are contained in it

    contains = get_all_in_poly(phys, poly)
    # contains = check_contains_all(phys.block_list, poly, board=board)
    # if none then reset
    if contains == []:
        draw.reset()
    # else log the players as selected
    [draw.log_player(bl) for bl in contains]
    # turn them into sensors for the move so no collision

    # for bl in draw.player_list:
    #    bl.sensor = True

    draw.status = new_status
    draw.locations = []

    if reset_on_none:
        if draw.player_list == []:
            draw.reset()
    return draw, phys


def select_player(draw, phys, x, y, if_found=None, if_not=None, reset_if_not=False, pause=True, allow_mul=False,
                  select_all=False, board=None, blocks_only=False):
    if blocks_only:
        blocks = [bl for bl in phys.block_list if
                  bl.background == False and bl.foreground == False and bl.sensor["type"] == None and bl.type > 0]
    else:
        blocks = phys.block_list

    clicked, coords = get_clicked(blocks, x, y, board)
    if not clicked is None:
        if len(draw.player_list) == 0 or allow_mul:
            clicked, coords = get_clicked(blocks, x, y)
            draw.log_player(clicked)
            # also add players connected by rotation joints as it messes things up if not
            # if select_all:
            #     players = [clicked]
            #     for pl in players:
            #         for jn in pl.body.joints:
            #             if type(jn.joint) == b2RevoluteJoint:
            #                 if jn.joint.bodyA.userData["ob"] == pl and jn.joint.bodyB.userData[
            #                     "ob"] not in draw.player_list:
            #                     draw.log_player(jn.joint.bodyB.userData["ob"])
            #                     players.append(jn.joint.bodyB.userData["ob"])
            #                 if jn.joint.bodyB.userData["ob"] == pl and jn.joint.bodyA.userData[
            #                     "ob"] not in draw.player_list:
            #                     draw.log_player(jn.joint.bodyA.userData["ob"])
            #                     players.append(jn.joint.bodyA.userData["ob"])

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
                    return pl, None


def clone_players(draw, phys):
    # get items
    item_list = []
    for bl in draw.player_list:
        item_list.append(phys.save_block_as_dict(bl, True))

    # clone them
    new_obs = phys.create_pre_def_block(item_list, convert_joints=False, clone=True)
    draw.clone_created = True
    return draw, phys


def move_players(draw, phys, board, joint_move=False):
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
                if bl_dic["joints"][k]["bodyA"] in ids or joint_move:
                    bl_dic["joints"][k]["anchorA"][0] += convert_to_mks(x_dif)
                    bl_dic["joints"][k]["anchorA"][1] += convert_to_mks(y_dif)
                    anc = [float(x.replace("(", "").replace(")", "")) for x in
                           bl_dic["joints_userData"][0]["bodyA"]["anchorA"].split(",")]
                    anc[0] += convert_to_mks(x_dif)
                    anc[1] += convert_to_mks(y_dif)
                    bl_dic["joints_userData"][0]["bodyA"]["anchorA"] = str(tuple(anc))
                if bl_dic["joints"][k]["bodyB"] in ids or joint_move:
                    bl_dic["joints"][k]["anchorB"][0] += convert_to_mks(x_dif)
                    bl_dic["joints"][k]["anchorB"][1] += convert_to_mks(y_dif)
                    anc = [float(x.replace("(", "").replace(")", "")) for x in
                           bl_dic["joints_userData"][0]["bodyB"]["anchorB"].split(",")]
                    anc[0] += convert_to_mks(x_dif)
                    anc[1] += convert_to_mks(y_dif)
                    bl_dic["joints_userData"][0]["bodyB"]["anchorB"] = str(tuple(anc))
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


def move_clone(draw, phys, x=None, y=None, event=None, clone=None, board=None, joint_move=False):
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
            draw, phys = move_players(draw, phys, board, joint_move=joint_move)
            for bl in draw.player_list:
                bl.body.active = True
                bl.body.awake = True
            phys.set_active()
        else:
            # this is for logging of the movment when selecting to draw the recangle box
            draw.log_point(x, y, "select")

    elif event == cv2.EVENT_LBUTTONUP:
        if draw.status == "move":
            # for bl in draw.player_list:
            #    bl.body.active = True
            #    bl.body.awake = True
            #    bl.body.sensor = False
            for bl in draw.player_list:
                bl.body.active = True
                bl.body.awake = True
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


def move_screen(draw, board, x=None, y=None, event=None):
    if event == cv2.EVENT_LBUTTONDOWN:
        draw.reset()
        draw.log_point(x, y, "screen")

    elif event == cv2.EVENT_MOUSEMOVE and draw.status == "screen":
        draw.log_point(x, y, "screen")
        back = 0
        # while abs(back) < len(draw.locations):
        if calculateDistance(draw.locations[-1][0], draw.locations[-1][1], draw.locations[back][0],
                             draw.locations[back][1]) > 2:
            board.translation[0] += draw.locations[-1][0] - draw.locations[back][0]
            board.translation[1] += draw.locations[-1][1] - draw.locations[back][1]
        #     break
        # back -= 1
        #     if back < -5:
        #         break

    elif event == cv2.EVENT_LBUTTONUP:
        draw.reset()

    return draw, board


def center_clicked(draw, phys, x=None, y=None, event=None, cur_key=None):
    if event == cv2.EVENT_LBUTTONDOWN:

        draw, phys, clicked, coords = select_player(draw, phys, x, y, None, None, pause=False)

        for bl in phys.block_list:
            bl.center_me = False

        if not clicked is None:
            clicked.center_me = True

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
