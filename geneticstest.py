#!/usr/bin/env python
# coding: utf-8
from configobj import ConfigObj

from gui import update_block, get_fixtures, get_toolbar, deal_with_toolbar_event
from keyboardmouse import *
from objects import load


def add(event, x, y, flags, param):
    global draw
    global cur_key
    global phys
    global msg
    global board
    old_x = x
    old_y = y

    x_new = (x + board.translation[0]*-1)
    y_new = (y + board.translation[1]*-1)

    if cur_key is None or cur_key == "":
        pass

    elif cur_key[0] == "1":
        """
        Used to create fire blocks or create them.
        """
        draw, phys = fire(draw, phys, event, x_new, y_new, cur_key, board)

    elif cur_key[0] == "j":

        """
        Used to create joints
        """

        if cur_key[1:] == SelectType.straight_join.value:
            if msg.message == "Distance Joint":
                draw, phys = distance_draw(draw, phys, event, x_new, y_new, cur_key)
            elif msg.message == "Rope Joint":
                draw, phys = rope(draw, phys, event, x_new, y_new, cur_key)

            elif msg.message == "Prismatic Joint":
                draw, phys = prismatic(draw, phys, event, x_new, y_new, cur_key)

            elif msg.message == "Weld Joint":
                try:
                    draw, phys = weld(draw, phys, event, x_new, y_new, cur_key)
                except AssertionError:
                    draw.reset()
                    print("Weld Selection Error")

        elif cur_key[1:] == SelectType.line_join.value:
            if msg.message == "Electric":
                draw, phys = lightning(draw, phys, event, x_new, y_new, cur_key)
            elif msg.message == "Springy Rope":
                draw, phys = chainish(draw, phys, event, x_new, y_new, cur_key)
        elif cur_key[1:] == SelectType.line_join2.value:
            if msg.message == "Chain":
                draw, phys = chain(draw, phys, event, x_new, y_new, cur_key)

        elif cur_key[1:] == SelectType.d_straight_join.value:
            if msg.message == "Pulley":
                draw, phys = pulley(draw, phys, event, x_new, y_new, cur_key)

        elif cur_key[1:] == SelectType.rotation_select.value:
            if msg.message == "Rotation Joint":
                draw, phys = rotation(draw, phys, event, x_new, y_new, cur_key)

        elif cur_key[1:] == SelectType.rotation_select.value:
            if msg.message == "Pulley Joint":
                draw, phys = pulley(draw, phys, event, x_new, y_new, cur_key)


        elif cur_key[1:] == SelectType.circle.value:
            if msg.message == "Wheel Joint":
                draw, phys = wheel_draw(draw, phys, event, x_new, y_new, cur_key)


    elif cur_key[0] == "u":
        """
        Used to remove joints
        """

        draw, phys = remove_joints(draw, phys, event, x_new, y_new, cur_key)

    elif cur_key[0] == "k":
        """
        Used to create Forces sensors
        """
        draw, phys = draw_sensor(draw, phys, event, x_new, y_new, cur_key, ty="pusher")


    elif cur_key[0] == "l":
        """
        Used to create Splitter sensors
        """
        draw, phys = draw_sensor(draw, phys, event, x_new, y_new, cur_key, ty="splitter")

    elif cur_key[0] == "/":
        """
        Used to create booster sensors
        """
        draw, phys = draw_sensor(draw, phys, event, x_new, y_new, cur_key, ty="fire")

    elif cur_key[0] == "'":
        """
        Used to create Goal sensors
        """
        draw, phys = draw_sensor(draw, phys, event, x_new, y_new, cur_key, ty="goal")

    elif cur_key[0] == ";":
        """
        Used to select blocks and print details (for now)
        """
        draw, phys = select_blocks(draw, phys, event, x_new, y_new, cur_key)
        if len(draw.player_list) >= 1:
            draw.player_list[0] = update_block(draw.player_list[0])
            draw.reset()

    elif cur_key[0] == "4":
        """
        Used to select a blocks joints and print details (for now)
        """
        draw, phys = select_blocks(draw, phys, event, x_new, y_new, cur_key)
        if len(draw.player_list) >= 1:
            draw.player_list[0] = get_fixtures(draw.player_list[0],board)
            draw.reset()

    elif cur_key[0] == "v":
        """
        Used to set spawn point
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            h, w, _ = board.board.shape
            phys.options["blocks_out"]["start_pos_x_min"] = int(x_new / w * 100)
            phys.options["blocks_out"]["start_pos_x_max"] = int(x_new / w * 100)
            phys.options["blocks_out"]["start_pos_y_min"] = int(y_new / h * 100)
            phys.options["blocks_out"]["start_pos_y_max"] = int(y_new / h * 100)


    elif cur_key[0] == "t":
        """
        Used to transform block
        """
        """
        Used to rotate blocks
        """

        if cur_key[1:] == SelectType.player_select.value:
            draw, phys = transform_block(draw, phys, event, x_new, y_new, cur_key, board = board)


    elif cur_key[0] == "2":
        """
        Used to rotate blocks
        """

        if cur_key[1:] == SelectType.player_select.value:
            draw, phys = rotate_block(draw, phys, event, x_new, y_new, cur_key, board = board)

    elif cur_key[0] == "m":
        """
        Used to move or clone blocks
        """

        if cur_key[1:] == SelectType.select.value and msg.message == "Mouse Move":
            draw, phys = mouse_joint_move(draw, phys, x_new, y_new, event, cur_key)
        else:
            if msg.message == "Clone Move":
                draw, phys = move_clone(draw, phys, x_new, y_new, event, True)
            else:
                draw, phys = move_clone(draw, phys, x_new, y_new, event, False)

    elif cur_key[0] == "]":

        """
        Used to select fire bullets from the player on click
        """
        draw, phys = fire_bullet(draw, phys, event, x_new, y_new, cur_key, board = board)

    elif cur_key[0] == "[":

        """
        Used to select objects to be a player click
        """
        draw, phys = make_player(draw, phys, event, x_new, y_new, cur_key)

    elif cur_key[0] == "x":

        """
        Used to delete objects on click
        """
        draw, phys = delete(draw, phys, event, x_new, y_new, cur_key, board = board)

    elif cur_key[0] == "p":
        """
        Used to create polygons

        """
        draw, phys = draw_shape(draw, phys, event, x_new, y_new, cur_key, board = board)

    elif cur_key[0] == "b":
        """
        Used to create polygons

        """
        draw, phys = draw_foreground(draw, phys, event, x_new, y_new, cur_key, board = board)

    elif cur_key[0] == "f":
        """
        Used to create fractals
        """
        draw, phys = draw_fragment(draw, phys, event, x_new, y_new, cur_key, board = board)

    elif cur_key[0] == "g":
        """
        Used to create ground
        """
        draw, phys = draw_ground(draw, phys, event, x_new, y_new, cur_key, board = board)

    if phys.options["screen"]["allow_x_move"] is True:
        if old_x < board.board.shape[1] *.15:
            board.x_trans_do = "up"
        elif old_x > board.board.shape[1] *.85:
            board.x_trans_do = "down"
        else:
            board.x_trans_do = None

    if phys.options["screen"]["allow_y_move"] is True:
        if old_y < board.board.shape[0] *.15:
            board.y_trans_do = "up"
        elif old_y > board.board.shape[0] *.85:
            board.y_trans_do = "down"
        else:
            board.y_trans_do = None

if __name__ == "__main__":

    timer, phys, draw, board, msg = load_gui(persistant=True)

    # init the physics engine, board, and timer.
    conf = ConfigObj("config_default.cfg")
    conf.filename = "config.cfg"
    conf.write()

    cur_key = ""
    loops = 0

    timeStep = 1.0 / 60

    # set window name and mouse callback for mouse events
    cv2.namedWindow("Board")
    cv2.setMouseCallback("Board", add)

    toolbar = get_toolbar()

    # start loop
    if not hasattr(board,"run"):
        setattr(board,"run",True)

    while board.run:

        #read toolbar
        toolbar, key, name = deal_with_toolbar_event(toolbar)
        #move to snap to board
        toolbar.move(cv2.getWindowImageRect("Board")[0]+board.board.shape[1], cv2.getWindowImageRect("Board")[1]-53)

        # get key press
        if key is None:
            key = cv2.waitKey(1) & 0xFF

        # deal with keypress OR spawn per config file
        cur_key,draw,phys,msg,timer,board = action_key_press(key,cur_key,draw,phys,msg,timer,board)

        #load a blank background board
        board.copy_board()

        # draw physics
        board = phys.draw_blocks(board)

        # draw front of board
        board = board.draw_front(board)

        # draw joints
        board = phys.draw_joints(board)

        # write lines for drawing
        board = draw.draw_point(board)

        # write message if needed
        board = msg.draw_message(board, (not draw.pause is True) and (phys.pause is False))

        # show board
        cv2.imshow("Board", board.board_copy[:, :, ::-1])

        # timer log - this handles FPS
        timer.log()

        # increment loops for additional players
        loops += 1

        # step the physics engine if draw needed
        if (not draw.pause is True) and (phys.pause is False):

            # create player if needed
            if loops > phys.options["blocks"]["spawn_every"]:
                phys.create_block()
                loops = 0
            # check players off screen to kill (otherwise they would continue to be calculated off screen wasting CPU) or if they have reached the goal
            goal_hits = phys.check_off(board)
            msg.goal_hits += goal_hits

            #step the physics engine
            phys.world.Step(timeStep, 7, 6)
            phys.world.ClearForces()


        #this applies impulses gathered from any booster sensors.
        phys.check_sensor_actions()

        #check if the player has hit goal and needs reset?
        timer, phys, board, draw, msg = board.reset_me(timer, phys, board, draw, msg)

    cv2.destroyAllWindows()
