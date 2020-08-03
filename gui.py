import inspect

import PySimpleGUI as sg
import os

import cv2
from configobj import ConfigObj
import numpy as np

from draw_functions import SelectType
from functions import get_config, convert_from_mks, convert_to_mks

from objects import load_state, load

sg.theme('Light Blue 6')
sg.SetOptions(font="TkHeadingFont")


def getVariableName(variable):
    for k, v in globals().copy().items():
        if v == variable:
            return k

def get_key_gui():
    layout = [[sg.Text("Which key should fire this event?")],
              [sg.InputText("",key="input"),sg.Button("Ok",enable_events=True,key="Button")]]
    window = sg.Window('Key Allocation',layout, disable_close=True)

    while True:
        event,values = window.read()

        if event == "Button":
            if values["input"] == "":
                sg.popup("Please enter a key value")
            elif len(values["input"]) > 1:
                sg.popup("Please only enter 1 key")
            elif values["input"] in ["[","]","1","2","3","4","5","6","7","8","9"]:
                sg.popup("Reserved key selected, please choose another")
            else:
                window.close()
                return values["input"]

def get_toolbar():
    gameplay = {"Reset": ["r", SelectType.null, "Reset the board to defaults (r)"],
                "Quit": ["q", SelectType.null, "Quit the game (q)"],
                "Pause": ["o", SelectType.null, "Toggle game play on/off ('o' toggle)"],
                "Save": ["*", SelectType.null, "Save current state (*)"],
                "Load": ["-", SelectType.null, "Load a saves state (-)"]}

    creation = {"Spawn": ["z", None, "Spawn a player from the predefined spawn point (z)"],
                "Set Spawn": ["v", SelectType.null, "Set spawn point on click (v)"],
                "Remove Blocks": ["e", SelectType.null, "Remove all dynamic blocks from scene (e)"],
                "Frag All": ["h", SelectType.null, "Fragment all blocks (h)"],
                "Delete": ["x", SelectType.select, "Delete a player with mouse - click or select (x)"],
                "Delete Joint": ["u", SelectType.select, "Delete attached joints (u)"],
                "Create": ["1", SelectType.select_point, "Create a block on mouse click (1 toggle)"],
                "Fire Poly": ["1", SelectType.vector_direction, "Fire a block on mouse click and drag (1 toggle)"],
                "Generate Terrain": ["i", SelectType.null, "Generate Terrain"]}

    translation = {"Mouse Move": ["m", SelectType.select, "Move selected player with physics (m toggle)"],
                   "Normal Move": ["m", SelectType.null, "Move selected player(s) paused physics (m toggle)"],
                   "Clone Move": ["m", SelectType.null, "Clone selected player(s) paused physics (m toggle)"],
                   "Transform": ["t", SelectType.player_select, "Transform selected player(s) (t toggle)"],
                   "Rotate": ["2", SelectType.player_select, "Rotate player(s) on click or select (2)"]}

    drawing = {"Polygon": ["p", SelectType.draw, "Draw a block polygon that reacts to physics (d toggle)"],
               "Rectangle": ["p", SelectType.rectangle, "Draw a block rectangle that reacts to physics (d toggle)"],
               "Circle": ["p", SelectType.circle, "Draw a block circle that reacts to physics (d toggle)"],

               "Fragment Poly": ["f", SelectType.draw, "Draw a fragmented polygon that reacts to physics (f toggle)"],
               "Frament Rectangle": ["f", SelectType.rectangle,
                                     "Draw a fragmented rectangle that reacts to physics (f toggle)"],
               "Frament Select": ["f", SelectType.select, "Draw a fragmented circle that reacts to physics (f toggle)"],

               "Ground Poly": ["g", SelectType.draw, "Draw a static floor polygon that reacts to physics (g toggle)"],
               "Ground Rectangle": ["g", SelectType.rectangle,
                                    "Draw a static floor rectangle that reacts to physics (g toggle)"],
               "Ground Circle": ["g", SelectType.circle,
                                 "Draw a static floor circle that reacts to physics (g toggle)"],

               "Fore Poly": ["b", SelectType.draw,
                             "Draw a static foreground polygon sits infront of all other elements (b toggle)"],
               "Fore Rectangle": ["b", SelectType.rectangle,
                                  "Draw a static foreground rectangle sits infront of all other elements (b toggle)"],
               "Fore Circle": ["b", SelectType.circle,
                               "Draw a static foreground circle sits infront of all other elements (b toggle)"]
               }

    updating = {"Config Update": ["5", SelectType.null, "Configure the board wide settings (5)"],
                "Background Update": ["6", SelectType.null, "Update the background (6)"],
                "Joint Update": ["4", SelectType.select, "Update connected joints to clicked player (4)"],
                "Player Update": [";", SelectType.select, "Update player (;)"]}

    sensors = {"Pusher Poly": ["k", SelectType.draw,
                               "Polygon draw of sensor that pushes colliding blocks in set direction (k toggle)"],
               "Pusher Rectangle": ["k", SelectType.rectangle,
                                    "Rectangle draw of sensor that pushes colliding blocks in set direction (k toggle)"],
               "Pusher Circle": ["k", SelectType.circle,
                                 "Circle draw of sensor that pushes colliding blocks in set direction (k toggle)"],

               "Splitter Poly": ["l", SelectType.draw,
                                 "Polygon draw of sensor that fragments colliding blocks (l toggle)"],
               "Splitter Rectangle": ["l", SelectType.rectangle,
                                      "Rectangle draw of sensor that pushes fragments blocks (l toggle)"],
               "Splitter Circle": ["l", SelectType.circle,
                                   "Circle draw of sensor that pushes fragments blocks (l toggle)"],

               "Fire Poly": ["/", SelectType.draw,
                             "Polygon draw of sensor that fires fragments blocks in set direction (/toggle)"],
               "Fire Rectangle": ["/", SelectType.rectangle,
                                  "Rectangle draw of sensor that fires fragments blocks in set direction (/ toggle)"],
               "Fire Circle": ["/", SelectType.circle,
                               "Circle draw of sensor that fires fragments blocks in set direction (/ toggle)"],

               "Goal Poly": ["'", SelectType.draw, "Polygon draw of sensor that destroys blocks ('k' toggle)"],
               "Goal Rectangle": ["'", SelectType.rectangle,
                                  "Rectangle draw of sensor that destroys fragments blocks ('k' toggle)"],
               "Goal Circle": ["'", SelectType.circle,
                               "Circle draw of sensor that destroys fragments blocks (' toggle)"]}

    screen_drawing = {"Draw Ground": ["0", SelectType.null, "Toggle drawing of ground blocks on/off ('0' toggle)"],
                      "Draw Blocks": ["9", SelectType.null, "Toggle drawing of dynamic blocks on/off ('9' toggle)"],
                      "Draw Sensors": ["8", SelectType.null, "Toggle drawing of sensors on/off ('8' toggle)"],
                      "Draw Foreground": ["c", SelectType.null,
                                          "Toggle drawing of foreground elements on/off ('c' toggle)"]}

    joints = {"Distance Joint": ["j", SelectType.straight_join,
                                 "Create a joint that attempts to keep a set fixed distance between two players (j toggle)"],
              "Rope Joint": ["j", SelectType.straight_join,
                             "Create a joint that constrains two blocks to a maximum distance but can be less (j toggle)"],
              "Prismatic Joint": ["j", SelectType.straight_join,
                                  "Create a joint that restricts movement to a given axis (j toggle)"],
              "Electric": ["j", SelectType.line_join,
                           "Create an electric appearing joint between two blocks (j toggle)"],
              "Chain": ["j", SelectType.line_join,
                        "Create a chain joint between two blocks (j toggle)"],
              "Springy Rope": ["j", SelectType.line_join, "To Fix (j toggle)"],
              "Weld Joint": ["j", SelectType.straight_join, "Weld two blocks together (j toggle)"],
              "Wheel Joint": ["j", SelectType.circle, "Create a wheel type joint (j toggle)"],
              "Rotation Joint": ["j", SelectType.rotation_select,
                                 "Create a rotation joint between two blocks (j toggle)"],
              "Pulley": ["j", SelectType.d_straight_join,
                         "Create a pulley between two blocks and a static point (j toggle)"]}

    layout = []

    sections = [gameplay, updating, screen_drawing, creation, drawing, translation, sensors, joints]
    section_names = ['Gameplay', 'Edit', 'Screen_drawing', 'Creation', 'Drawing', 'Translation', 'Sensors',
                     'Joints']

    for section, name in zip(sections, section_names):
        buttons = []
        sub_buttons = []
        for k, v in section.items():
            if len(sub_buttons) == 3:
                buttons.append(sub_buttons)
                sub_buttons = []
            sub_buttons.append(
                sg.Button(button_text=k, font=("TkHeadingFont", 8), metadata=v, tooltip=v[2], size=(13, 1)))

        if sub_buttons != []:
            buttons.append(sub_buttons)

        layout.append([sg.Frame(name, buttons, pad=(12, 8), element_justification="center")])

    # drawing section

    translation = {"Screen Move": ["1", SelectType.select, "Move the screen position with click drag (m toggle)"],
                   "Center Clicked": ["2", SelectType.select,
                                      "Center the board on the selected item if nothing selected clears"]}
    player = {"Choose Player": ["[", SelectType.null, "Select player to be controlled by the keyboard arrows ([)"],
              "Fire Bullet": ["]", SelectType.null, "Fire a bullet from the player center to mouse click position (])"]}

    motor = {"Motor Forwards": ["3", SelectType.select, "Move the screen position with click drag (m toggle)"],
             "Motor Backwards": ["4", SelectType.select, "Move the screen position with click drag (m toggle)"]}
    rotate = {"Rotate CCW": ["5", SelectType.select, "Move the screen position with click drag (m toggle)"],
              "Rotate CW": ["6", SelectType.select, "Move the screen position with click drag (m toggle)"]}
    impulse = {"Impulse": ["7", SelectType.select, "Move the screen position with click drag (m toggle)"],
               "Relative Impulse": ["8", SelectType.select, "Move the screen position with click drag (m toggle)"]}
    force = {"Force": ["9", SelectType.select, "Move the screen position with click drag (m toggle)"],
             "Relative Force": ["0", SelectType.select, "Move the screen position with click drag (m toggle)"]}

    sections = [translation, player, motor, rotate, impulse, force]
    section_names = ['Screen', "Player", 'Motors', "Rotate", "Impulse", "Force"]
    layout_2 = []

    for section, name in zip(sections, section_names):
        buttons_2 = []
        sub_buttons = []
        for k, v in section.items():
            if len(sub_buttons) == 3:
                buttons_2.append(sub_buttons)
                sub_buttons = []
            sub_buttons.append(
                sg.Button(button_text=k, font=("TkHeadingFont", 8), metadata=v, tooltip=v[2], size=(13, 1)))

        if sub_buttons != []:
            buttons_2.append(sub_buttons)

        layout_2.append([sg.Frame(name, buttons_2, pad=(12, 8), element_justification="center")])

    layout = [[sg.TabGroup(
        [[sg.Tab('Drawing', layout, key="create_tab"), sg.Tab('Movement', layout_2, key="move_tab")]],
        enable_events=True, key="tabs")]]

    window = sg.Window('Toolbar', [
        [sg.Column([[sg.Button(">", key="expand", pad=(2, 2))]], pad=(2, 2), element_justification="center"),
         sg.Column(layout, key="options")]], disable_close=True)

    return window

def enable_all(toolbar):
    for k, v in toolbar.AllKeysDict.items():
        if type(v) is sg.Button:
            v.update(disabled=False)
    return toolbar

def deal_with_toolbar_event(toolbar, cur_key, cur_key_type, draw, msg):
    force = False
    event, values = toolbar.read(1)
    key = None


    if event == "expand":
        toolbar["options"].Update(visible=not toolbar["options"].Visible)
        toolbar["options"].Visible = not toolbar["options"].Visible

    elif event == "tabs":
        toolbar = enable_all(toolbar)
        if cur_key_type == 0 and values["tabs"] == "move_tab":
            cur_key_type = 1
            msg.set_message("Create Mode Enabled")
            draw.reset()
        elif cur_key_type == 1 and values["tabs"] == "create_tab":
            cur_key_type = 0
            msg.set_message("Create Mode Enabled")
            draw.reset()

    elif event != "__TIMEOUT__":
        toolbar = enable_all(toolbar)
        data = toolbar[event].metadata
        toolbar[event].update(disabled=True)
        draw.reset()
        msg.set_message(event)
        key = data[0]
        force=True

    else:
        event = None

    if cur_key_type == 0:
        toolbar["create_tab"].select()
    elif cur_key_type == 1:
        toolbar["move_tab"].select()

    return toolbar, ord(key) if not key is None else None, event, cur_key_type, draw, msg, force


def get_files():
    files_out = []
    for root, dirs, files in os.walk("saves/"):
        for file in files:
            if file.endswith(".save"):
                files_out.append(file)

    return files_out


def create_windows(block, board, selected=0):
    if len(block.body.joints) > 0:
        joints = []
        for i, jn in enumerate(block.body.joints):
            joints.append(f"""{i}-{str(type(jn.joint)).replace("<class 'Box2D.Box2D.b2", "").replace("'>", "")}""")

        savesLoad = [[sg.Text("Joint List")],
                     [sg.Listbox(values=joints, size=(30, 6), enable_events=True,
                                 select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, key="joints")]]

        current_joint = block.body.joints[int(joints[selected].split("-")[0])].joint

        lower_attributes = [v.lower() for v in dir(current_joint) if
                            not v.startswith("_") and v not in ["this", "next", "thisown", "type", "userData"]]
        normal_attributes = [v for v in dir(current_joint) if
                             not v.startswith("_") and v not in ["this", "next", "thisown", "type", "userData"]]
        val_dic = {}
        for att in normal_attributes:

            ok_continue = False
            if "get" + att.lower() in lower_attributes:
                index = lower_attributes.index("get" + att.lower())
                name = normal_attributes[index]
                attr = getattr(current_joint, name)
                val_dic[att] = []
                val_dic[att].append(attr())
                ok_continue = True
            else:
                if not inspect.ismethod(getattr(current_joint, att)):
                    val = getattr(current_joint, att)
                    val_dic[att] = []
                    val_dic[att].append(val)
                    ok_continue = True

            if ok_continue:
                try:
                    if "set" + att.lower() in lower_attributes:
                        index = lower_attributes.index("set" + att.lower())
                        name = normal_attributes[index]
                        attr = getattr(current_joint, name)
                        if type(val) is tuple:
                            attr(val[0], val[1])
                            ok_val = False
                        else:
                            attr(val)
                            ok_val = False
                    else:
                        setattr(current_joint, att, val_dic[att][0])
                        ok_val = False
                except:
                    ok_val = True

                val_dic[att].append(ok_val)

        details = []

        for k, v in val_dic.items():
            if not "body" in k:
                if "length" in k or "Length" in k:
                    v[0] = convert_from_mks(v[0])
                details.append([sg.Text(str(k) + (" (disabled)" if v[1] == True else ""), size=(25, 1)),
                                sg.Checkbox(" On?", key=k, disabled=v[1], default=bool(v[0])) if type(
                                    v[0]) is bool else sg.InputText(str(v[0]), key=k, disabled=v[1], size=(18, 1))])

        details.append([sg.Button("Delete", key="delete")])

        layout = [[sg.Column(savesLoad, key="list"), sg.Column(details, key="details")],
                  [sg.Button("Update Current", key="update"), sg.OK("Close", key="close")]]
        window = sg.Window('Create', layout, finalize=True)
        window["joints"].Update(set_to_index=selected)

        return window
    else:
        return False


def update_blocks_joint(values, block, joint_index, window):
    # updates the values stored in the GUI
    joint = block.body.joints[joint_index].joint

    methods = inspect.getmembers(joint, lambda a: (inspect.isroutine(a)))
    lower_methods = [x[0].lower() for x in
                     [a for a in methods if not (a[0].startswith('__') and a[0].endswith('__'))]]
    methods = [x[0] for x in [a for a in methods if not (a[0].startswith('__') and a[0].endswith('__'))]]

    for k, v in values.items():
        if window[k].Disabled is False:
            if "set" + k.lower() in lower_methods:
                method_name = methods[lower_methods.index("set" + k.lower())]
                set_meth = getattr(joint, method_name)
            else:
                set_meth = None

            if not type(v) in [bool]:
                if v[0].isnumeric() or v[0] == "-":
                    v = float(v)
                elif type(v) is str:
                    if v.find("(") > -1 or v.find("[") > -1:
                        v = tuple([float(x) for x in
                                   v.replace("[", "").replace("]", "").replace("(", "").replace(")", "").split(
                                       ",")])

            try:
                if k.find("length") > -1 or k.find("Length") > -1:
                    v = convert_to_mks(v)

                if not set_meth is None:
                    if type(v) is tuple:
                        if len(v) == 2:
                            set_meth(v[0], v[1])
                        elif len(v) == 3:
                            set_meth(v[0], v[1], v[2])
                        elif len(v) == 4:
                            set_meth(v[0], v[1], v[2], v[3])
                    else:
                        set_meth(v)
                else:
                    setattr(joint, k, v)

            except AttributeError:
                sg.Popup(f"Unable to set '{k}'")

    return block


def get_fixtures(block, board):
    window = create_windows(block, board)
    if window is False:
        sg.Popup("No joints found")
        return block

    joint_index = 0

    while True:  # Event Loop
        event, values = window.read()
        location = window.CurrentLocation()

        if event == "joints":
            # get the clicked list item and redraw the window
            clicked = window["joints"].get()[0]
            if type(clicked) is list:
                clicked = clicked[0]
            all_vals = window["joints"].get_list_values()
            joint_index = all_vals.index(clicked)
            window.close()
            window = create_windows(block, board, joint_index)

        elif event == "update":
            block = update_blocks_joint(values, block, joint_index, window)
            sg.Popup("Block Updated")

        elif event == "delete":
            block.body.world.DestroyJoint(block.body.joints[joint_index].joint)
            sg.Popup("Joint Deleted")
            window.close()
            window = create_windows(block, board)


        elif event == "close":
            break

        if window is False:
            sg.Popup("No joints found")
            return block
        else:
            window.move(location[0], location[1])

    window.close()
    return block


def save_gui():
    files = [x.replace(".save", "") for x in get_files()]
    frame_one = [[sg.Text("Save State")],
                 [sg.Text("Enter file name"), sg.InputText("", key="filename")],
                 [sg.Button(button_text="Save As", key="saveas", enable_events=True)]]

    frame_two = [[sg.Listbox(values=files, size=(60, 6), select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, enable_events=True,
                             key="files")],
                 [sg.Text("Enter a blurb below.")],
                 [sg.Button(button_text="Save Over", key="saveover", enable_events=True)]]

    blurb = [[sg.Text("Enter a blurb to save")], [sg.Multiline(default_text="", key="blurb_text", size=(60, 4))]]

    layout = [[sg.Frame('Save New', frame_one)], [sg.Frame('Overwrite', frame_two)],
              [sg.Frame('Save Additional Information', blurb)]]

    window = sg.Window('Save', layout)

    leave_ok = False
    while True:  # Event Loop
        event, values = window.read(timeout=1)
        if event == "files":
            window["blurb"].update(load_state(window["files"])[5])
        elif event == "saveas":
            if window["filename"].get() in files:
                ans = sg.popup_yes_no(
                    f"There is already a save with this name. Are you sure you want to save as '{window['filename'].get()}'")
                if ans == "Yes":
                    leave_ok = True
                    filename = window["filename"].get()
                    break
            else:
                leave_ok = True
                filename = window["filename"].get()
                break
        elif event == "saveover":
            ans = sg.popup_yes_no(
                f"Save over current file '{window['filename']}'?")
            if ans == "Yes":
                leave_ok = True
                filename = window["files"].get()

        elif event == sg.WIN_CLOSED:
            break

    window.close()

    if leave_ok:
        return filename, values["blurb_text"],
    else:
        return None, None


def load_gui(timer=None, phys=None, draw=None, board=None, msg=None, persistant=True):
    basicLoad = [[sg.Text("Open Blank Playing Board")],
                 [sg.Text("Width"), sg.InputText("1200", key="width", size=(15, 1))],
                 [sg.Text("Height"), sg.InputText("800", key="height", size=(15, 1))],

                 [sg.Text("Boundry Width"), sg.InputText("3000", key="bwidth", size=(15, 1))],
                 [sg.Text("Boundry Height"), sg.InputText("2000", key="bheight", size=(15, 1))],

                 [sg.OK(button_text="Create")]]

    files = [x.replace(".save", "") for x in get_files()]

    savesLoad = [[sg.Text("Load Saved State")],
                 [sg.Listbox(values=files, size=(50, 6), select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, key="files",
                             enable_events=True)],
                 [sg.Multiline("", key="blurb", size=(50, 4), disabled=True)],
                 [sg.FileBrowse(file_types=(("Save Files", "*.save"))), sg.OK(button_text="Load")]
                 ]

    layout = [[sg.TabGroup([[sg.Tab('Basic', basicLoad), sg.Tab('Load', savesLoad)]])]]
    window = sg.Window('Create/Load', layout)

    while True:  # Event Loop
        event, values = window.read(timeout=1)

        if event == sg.WIN_CLOSED:
            if persistant != True:
                break

        # gui if load selected
        if event == "Load":
            if values["files"][0] != "":
                timer, phys, draw, board, msg, blurb = load_state(values["files"][0])
                msg.set_message("State Loaded")
                draw.reset()
                sg.popup("Don't forget to unpause before playing")
                break
            else:
                sg.popup(title="No save selected.")

        # gui if create selected
        elif event == "Create":
            if values["height"].isnumeric() and values["width"].isnumeric():
                timer, phys, board, draw, msg = load(height=int(values["height"]), width=int(values["width"]),
                                                     b_height=int(values["bheight"]), b_width=int(values["bwidth"]))
                msg.set_message("New Board")
                break
            else:
                sg.popup(title="Error in height or width.")

        # event on click list
        elif event == "files":
            window["blurb"].update(load_state(values["files"])[5])

    window.close()

    return timer, phys, draw, board, msg


def update_config(values, config=ConfigObj("config.cfg"), window=None):
    ans = ""
    config.interpolation = False
    config.list_values = False

    for k, v in values.items():
        if type(k) is str:
            keys = k.split("-")
            main = keys[0]
            sub = keys[1]
            if ":" in sub:
                sub_list = sub.split(":")
                ans = ans + sub_list[1] + ":" + str(v) + ","
                config[main][sub_list[0]] = ans if ans[-1] != "," else ans[:-1]
            else:
                ans = ""
                config[main][sub] = v

    config.write()


def load_options():
    # get config file
    config = ConfigObj('config.cfg')
    # set pysimplegui options

    # blank window
    # Column layout
    tab = []
    col = []
    layout = []
    tab_names = []
    inner = []
    for k, v in config.items():
        tab_names.append(k)
        # tab.append([sg.Text(k,border_width=2, relief=sg.RELIEF_RAISED)])
        for kk, vv in config[k].items():
            group = []
            vv = get_config(k, kk)
            if sum([len(x) for x in config[k].comments[kk]]) > 0:
                first = 0
                for comment in config[k].comments[kk]:
                    if len(comment) > 0 and comment.find("touch") == -1:
                        if first == 0:
                            tab.append(
                                [sg.Text(comment.replace("#", "").strip(), text_color="black", font="TkMenuFont",
                                         relief=sg.RELIEF_GROOVE)])
                            first += 1
                        else:
                            tab.append(
                                [sg.Text(comment.replace("#", "").strip(), text_color="grey", font="TkMenuFont")])

            if kk.find("min") > -1:
                inner.append(sg.Text("Minimum"))
                inner.append(
                    sg.InputText(vv, key=k + "-" + kk, enable_events=True, size=(10, 3), metadata=type(vv)))
            elif kk.find("max") > -1:
                inner.append(sg.Text("Maximum"))
                inner.append(
                    sg.InputText(vv, key=k + "-" + kk, enable_events=True, size=(10, 3), metadata=type(vv)))
                tab.append(inner)
                inner = []

            elif type(vv) == dict:
                inner = []
                options_found = False
                for key, val in vv.items():
                    if key.find("type") > -1:
                        input_type = key[-1]
                        options_found = True
                    if input_type == "c":
                        inner.append(
                            sg.Radio(key, group_id=k + "-" + kk, key=k + "-" + kk + ":" + key,
                                     visible=False if options_found else True,
                                     default=(True if val is True else False)))

                    else:
                        inner.append(
                            sg.Checkbox(key, key=k + "-" + kk + ":" + key, visible=False if options_found else True,
                                        default=(True if val is True else False)))
                    options_found = False
                tab.append(inner)
                inner = []
            elif kk.find("scale") > -1:
                pass
            elif type(vv) == bool:
                tab.append([sg.Checkbox("", default=vv, key=k + "-" + kk)])
            else:
                tab.append(
                    [sg.InputText(str(vv), key=k + "-" + kk, enable_events=True, size=(17, 3), metadata=type(vv))])

        col.append(tab)
        tab = []
        inner = []

    for tab_nam, co in zip(tab_names, col):
        layout.append(sg.Tab(tab_nam, co, ))

    layout = [[sg.TabGroup([layout])]]

    layout = [[sg.Column(layout)],
              [sg.OK(button_text="Save")]]

    # Display the window and get values
    window = sg.Window('Options', layout)

    while True:
        event, values = window.read()

        if event == "Save":
            # validation
            found = 0
            for k, v in values.items():
                if "max" in str(k):
                    if float(values[k]) < float(values[k.replace("_max", "_min")]):
                        sg.Popup("Max value is less than minimum - setting to minimum")
                        window[k].update(window[k.replace("max", "min")].Get())
                        found += 1
                if "min" in str(k):
                    if float(values[k]) > float(values[k.replace("_min", "_max")]):
                        sg.Popup("Min value is more than maximum - setting to maximum")
                        window[k].update(window[k.replace("min", "max")].Get())
                        found += 1
                if not window[k].metadata is None:
                    try:
                        # try converting type
                        window[k].metadata(window[k].Get())
                    except:
                        sg.Popup(f"Unexpected data type - clearing value")
                        window[k].update("")
                        window[k].focus()
                        found += 1
            if found == 0:
                update_config(values, window=window)
                window.close()
                break
    window.close()


def update_block_values(values, block):
    # update the block attributes
    for k, v in values.items():
        if v != "":
            if not type(v) is bool:
                try:
                    v = float(v)
                except:
                    pass
            if k == "colour":
                v = tuple(int(values["colour"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            if hasattr(block, k):

                setattr(block, k, v)
                if k == "sprite":
                    block.set_sprite()
            elif hasattr(block.body, k):
                setattr(block.body, k, v)
            elif hasattr(block.body.fixtures[0], k):
                setattr(block.body.fixtures[0], k, v)
    return block


def update_block(block):
    # load upadte block GUI
    layout = [[sg.Checkbox(text="Is Awake?", key="awake", default=block.body.awake)],
              [sg.Checkbox(text="Is Active?", key="active", default=block.body.active)],
              [sg.Checkbox(text="Has fixed rotation?", key="fixedRotation", default=block.body.fixedRotation)],
              [sg.Checkbox(text="Is colidable?", key="sensor", default=block.body.fixtures[0].sensor)],
              [sg.Text("Linear Damping"), sg.InputText(round(block.body.linearDamping, 3), key="linearDamping")],
              [sg.Text("angularDamping"), sg.InputText(round(block.body.angularDamping, 3), key="angularDamping")],
              [sg.Text("gravityScale"), sg.InputText(round(block.body.gravityScale, 3), key="gravityScale")],
              [sg.Text("angle"), sg.InputText(round(block.body.angle, 4), key="angle")],
              [sg.Text("mass"), sg.InputText(round(block.body.mass, 4), key="mass")],
              [sg.Text("density"), sg.InputText(round(block.body.fixtures[0].density, 3), key="density")],
              [sg.Text("friction"), sg.InputText(round(block.body.fixtures[0].friction, 3), key="friction")],
              [sg.Text("restitution"),
               sg.InputText(round(block.body.fixtures[0].restitution, 3), key="restitution")],
              [sg.ColorChooserButton(button_text="Choose Colour", key="colour")],
              [sg.Text("Choose Sprite"), sg.FileBrowse(key="sprite")],
              [sg.Checkbox(text="Force Draw?", key="force_draw", default=block.force_draw)]
              ]
    layout = [[sg.Column(layout)],
              [sg.OK(button_text="Save")]]

    # Display the window and get values
    window = sg.Window('Block Settings', layout)

    while True:
        event, values = window.read(1)
        try:
            if values["sprite"] != "":
                if cv2.imread(values["sprite"]) is None:
                    sg.Popup(title="Error reading file")
                    window["sprite"].update("")

            if event == "Save":
                block = update_block_values(values, block)
                break
        except TypeError:
            # user closed window unexpectedly
            pass
    window.close()
    return block


def update_background(board, phys, msg):
    # load update background GUI
    background = [
        sg.Frame('Choose Background', layout=[[sg.Text("Backgrounds are displayed behind ALL other elements")],
                                              [sg.FileBrowse(key="background",
                                                             metadata={"status": "ok", "size": None}, pad=(4, 12)),
                                               sg.Button("Clear", key="clear-background", target="background_path",
                                                         pad=(4, 12))],
                                              [sg.Text("None", key="background_path", size=(80, 1))],
                                              [sg.Text("None", key="background_size", visible=False,
                                                       size=(50, 1))]])]

    foreground = [sg.Frame('Choose Foreground', layout=[
        [sg.Text("Foregrounds are displayed in front of ALL other elements")],
        [sg.Text("and must have an transparency layer.")],
        [sg.FileBrowse(key="foreground", target="foreground_path", metadata={"status": "ok", "size": None},
                       pad=(4, 12)),
         sg.Button("Clear", key="clear-foreground", pad=(4, 12))],
        [sg.Text("None", key="foreground_path", size=(80, 1))],
        [sg.Text("None", key="foreground_size", visible=False, size=(50, 1))]])]

    middleground = [sg.Frame('Choose Blocks Layer',
                             layout=[[sg.Text("The block layer will automatically draw ground blocks for you")],
                                     [sg.FileBrowse(key="middleground", target="middleground_path",
                                                    metadata={"status": "ok", "size": None}, pad=(4, 12)),
                                      sg.Button("Clear", key="clear-middleground", pad=(4, 12))],
                                     [sg.Text("None", key="middleground_path", size=(80, 1))],
                                     [sg.Text("None", key="middleground_size", visible=False, size=(50, 1))]])]

    # layout = [[sg.Text("Choose Background")],
    #           [sg.Text("Backgrounds are displayed behind ALL other elements")],
    #           [sg.FileBrowse(key="background")],
    #           [sg.Text("None",key="background_path",size = (80,3)),sg.Text("None",key="background_size",visible=False)],
    #           [sg.Text("Choose Foreground")],
    #           [sg.Text("Foregrounds are displayed in front of ALL other elements and should utilise an alpha channel")],
    #           [sg.FileBrowse(key="foreground")],
    #           [sg.Text("None",key="foreground_path",size = (80,3)),sg.Text("None",key="foreground_size",visible=False)],
    #           [sg.Text("Choose Blocks Layer")],
    #           [sg.FileBrowse(key="middleground")],
    #           [sg.Text("None",key="middleground_path",size = (80,3)),sg.Text("None",key="middleground_size",visible=False)],
    #           [sg.OK(button_text="Save")]
    #           ]

    layout = [[sg.Column([background, foreground, middleground])],
              [sg.Ok("Load")]]

    # Display the window and get values
    window = sg.Window('Background Settings', layout)

    while True:
        event, values = window.read(1)
        back_img = None
        mid_img = None
        fore_img = None

        if event == sg.WIN_CLOSED:
            break

        # check button press to clear the file browse fields
        if event == "clear-background":
            # window["background"].update("")
            window["background"].metadata = {"status": "nok", "size": None}
            window["background_path"].update("None", text_color="black")
            window["background_size"].update(visible=False)

        elif event == "clear-foreground":
            # window["foreground"].update("")
            window["foreground"].metadata = {"status": "nok", "size": None}
            window["foreground_path"].update("None", text_color="black")
            window["foreground_size"].update(visible=False)

        elif event == "clear-middleground":
            # window["middleground"].update("")
            window["middleground"].metadata = {"status": "nok", "size": None}
            window["middleground_path"].update("None", text_color="black")
            window["middleground_size"].update(visible=False)

        ##set forground and check for aplha channel - this must be here or you will only see the foreground
        if values["foreground"] != "":
            error = False
            error_text = None
            fore_img = cv2.imread(values["foreground"], -1)
            if not type(fore_img) is type(None):
                if fore_img.shape[2] > 3:
                    mean_val = np.mean(fore_img[:, :, 3])
                    if mean_val == 0 or mean_val == 255:
                        error = True
                        error_text = "Transparency Missing From Image"
                    else:
                        window["foreground"].metadata = {"status": "ok", "size": fore_img.shape}
                        window["foreground_path"].update(values['foreground'], text_color="black")
                        window["foreground_size"].update(f"{fore_img.shape[0]} x {fore_img.shape[1]}", visible=True)
                else:
                    error = True
                    error_text = "Transparency Missing From Image"
            else:
                error = True
                error_text = "Not an image"

            if error:
                window["foreground"].metadata = {"status": "nok", "size": None}
                window["foreground_size"].update(visible=False)
                window["foreground_path"].update("Size Image Load Error" if error_text is None else error_text,
                                                 text_color="red")

        # check background
        if values["background"] != "":
            back_img = cv2.imread(values["background"])
            if not type(back_img) is type(None):
                window["background"].metadata = {"status": "ok", "size": back_img.shape}
                window["background_path"].update(values['background'], text_color="black")
                window["background_size"].update(f"Size {back_img.shape[0]} x {back_img.shape[1]}", visible=True)
            else:
                window["background"].metadata = {"status": "nok", "size": None}
                window["background_path"].update("Image Load Error", text_color="red")
                window["background_size"].update(visible=False)

        # check background
        if values["middleground"] != "":
            mid_img = cv2.imread(values["middleground"])
            if not type(mid_img) is type(None):
                window["middleground"].metadata = {"status": "ok", "size": mid_img.shape}
                window["middleground_path"].update(values['middleground'], text_color="black")
                window["middleground_size"].update(f"Size {mid_img.shape[0]} x {mid_img.shape[1]}", visible=True)
            else:
                window["middleground"].metadata = {"status": "nok", "size": None}
                window["middleground_path"].update("Image Load Error", text_color="red")
                window["middleground_size"].update(visible=False)

        if event == "Load":
            types = ["middleground", "background", "foreground"]

            # on "load" click check if all images are ok. If they are check if the sizes match. If not ask the user
            # if they want to resize the images.
            # once all complete then load into the board and close.

            if sum([1 if window[x].metadata["status"] == "ok" else 0 for x in types]) == len(types):
                sizes = [window[x].metadata["size"] for x in types if x != None]
                set_size = set(sizes)
                if len(sizes) == len(set_size):
                    ans = sg.popup("All images must be the same size. Please fix before continuing.",
                                   button_type=sg.POPUP_BUTTONS_YES_NO)
                else:
                    phys = board.load_blocks(back_img, mid_img, fore_img, phys)
                    phys.height = board.board.shape[0]
                    phys.width = board.board.shape[1]
                    msg.load_pannel(board.board)
                    break
            else:
                sg.popup("Image Error - please fix before continuing")

    window.close()
    return board, phys, msg

def get_select_joints_with_motor(clicked):

    if len(clicked.body.joints) > 0:
        layout = [[sg.Text("Please select the joint you want to attach key to")]]
        items = []
        for i,jn in enumerate(clicked.body.joints):
            joint = jn.joint
            lower_attributes = [v.lower() for v in dir(joint) if
                                not v.startswith("_") and v not in ["this", "next", "thisown", "type", "userData"]]
            if "motorenabled" in lower_attributes:
                try:
                    setattr(joint, "motorEnabled", False)
                    items.append(str(i) + "-" + str(type(joint)))
                except:
                    pass
        if len(items) > 0:
            layout.append([sg.Listbox(values=(items), size=(30, 3),key="listbox",enable_events=True)])

            window = sg.Window('Background Settings', layout)
            while True:
                event,values = window.read(1)

                if event == "listbox":
                    window.close()
                    return values["listbox"][0]

    return None


def terrain_complexity_gui():

    layout = [[sg.Text("Slope Times",relief=sg.RELIEF_GROOVE)],
              [sg.Text("The amount of times to go in a given direction before POSSIBLY changing direction",font="TkHeadingFont 8")],
              [sg.Text("Min"),sg.InputText(4,key="slope_times_min",size=(5,1)),sg.Text("Max"),sg.InputText(20,key="slope_times_max",size=(5,1))],
              [sg.Text("X Stride",relief=sg.RELIEF_GROOVE)],
              [sg.Text("The possible min/max stride length of each X movement",font="TkHeadingFont 8")],
              [sg.Text("Min"),sg.InputText(20, key="x_stride_min",size=(5,1)),sg.Text("Max"),sg.InputText(80,key="x_stride_max",size=(5,1))],
              [sg.Text("Y Stride",relief=sg.RELIEF_GROOVE)],
              [sg.Text("The possible min/max stride length of each Y movement",font="TkHeadingFont 8")],
              [sg.Text("Min"), sg.InputText(5, key="y_stride_min",size=(5,1)), sg.Text("Max"), sg.InputText(20, key="y_stride_max",size=(5,1))],
              [sg.Button("Generate",key="button")]]

    window = sg.Window("Generate Terrain",layout)

    while True:
        event, values = window.read()

        if event == "button":
            if int(values["slope_times_min"]) > int(values["slope_times_max"]) or int(values["slope_times_max"]) < int(values["slope_times_min"]):
                sg.popup("Error with slope times")

            elif "" in values:
                sg.popup("There can be no empty values")

            elif int(values["x_stride_min"]) > int(values["x_stride_max"]) or int(values["x_stride_max"]) < int(values["x_stride_min"]):
                sg.popup("Error with X stride values")

            elif int(values["y_stride_min"]) > int(values["y_stride_max"]) or int(values["y_stride_max"]) < int(values["y_stride_min"]):
                sg.popup("Error with Y stride values")

            else:
                window.close()
                return int(values["slope_times_min"]), int(values["slope_times_max"]),int(values["x_stride_min"]),int(values["x_stride_max"]),int(values["y_stride_min"]),int(values["y_stride_max"])
