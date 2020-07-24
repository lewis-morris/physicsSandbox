import PySimpleGUI as sg
import os

from configobj import ConfigObj

from functions import get_config
from objects import load_state, load

sg.theme('Dark Brown 6')

def get_files():

    files_out = []
    for root, dirs, files in os.walk("example_saves/"):
        for file in files:
            if file.endswith(".save"):
                files_out.append(file)

    return files_out

def save_gui():
    event, values = sg.Window('Save State As',
                              [[sg.Text('Filename')], [sg.Input()], [sg.OK(), sg.Cancel()]]).read(close=True)

    return values[0]

def load_gui(persistant=True):

    basicLoad = [[sg.Text("Open Blank Playing Board")],
                  [sg.Text("Width"),sg.InputText("800", key="width")],
                  [sg.Text("Height"),sg.InputText("600", key="height")],
                  [sg.OK(button_text="Create")]]


    files = [x.replace(".save","") for x in get_files()]

    savesLoad = [[sg.Text("Load Saved State")],
                  [sg.Listbox(values=files, size=(30, 6),select_mode=sg.LISTBOX_SELECT_MODE_SINGLE,key="files")],
                  [sg.FileBrowse(file_types= (("Save Files", "*.save"))),sg.OK(button_text="Load")]]

    layout = [[sg.TabGroup([[sg.Tab('Basic', basicLoad), sg.Tab('Load', savesLoad)]])]]
    window = sg.Window('Create', layout)

    while True:  # Event Loop
        event, values = window.read(timeout=1)

        if event == sg.WIN_CLOSED:
            if persistant != True:
                break

        #gui if load selected
        if event == "Load":
            if values["files"][0] != "":
                timer, phys, draw, board, msg = load_state(values["files"][0])
                msg.set_message("State Loaded")
                draw.reset()
                break
            else:
                sg.popup(title="No save selected.")

        #gui if create selected
        if event == "Create":
            if values["height"].isnumeric() and values["width"].isnumeric():
                timer, phys, board, draw, msg = load(height=int(values["height"]),width=int(values["width"]))
                msg.set_message("New Board")
                break
            else:
                sg.popup(title="Error in height or width.")

    window.close()

    return timer, phys, draw, board, msg



    return event,values

def update_config(values,config=ConfigObj("config.cfg")):
    ans = ""
    config.interpolation = False
    config.list_values = False

    for k,v in values.items():
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

    #get config file
    config = ConfigObj('config.cfg')
    #set pysimplegui options
    sg.theme('Light Blue 6')
    sg.SetOptions(font="TkHeadingFont")

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
                            tab.append([sg.Text(comment.replace("#", "").strip(), text_color="black",font="TkMenuFont", relief=sg.RELIEF_GROOVE)])
                            first +=1
                        else:
                            tab.append([sg.Text(comment.replace("#", "").strip(), text_color="grey",font="TkMenuFont")])

            if kk.find("min") > -1:
                inner.append(sg.Text("Minimum"))
                inner.append(sg.InputText(vv, key=k + "-" + kk,enable_events=True, size=(10,3),metadata=type(vv)))
            elif kk.find("max") > -1:
                inner.append(sg.Text("Maximum"))
                inner.append(sg.InputText(vv, key=k + "-" + kk,enable_events=True, size=(10,3),metadata=type(vv)))
                tab.append(inner)
                inner = []

            elif type(vv) == dict:
                inner = []
                for key, val in vv.items():
                    inner.append(sg.Checkbox(key, key=k + "-" + kk + ":" + key, default=(True if val is True else False)))
                tab.append(inner)
                inner = []
            elif kk.find("scale") > -1:
                pass
            elif type(vv) == bool:
                tab.append([sg.Checkbox("",default=vv, key = k + "-" + kk)])
            else:
                tab.append([sg.InputText(str(vv), key=k + "-" + kk, enable_events=True, size=(17,3),metadata=type(vv))])



        col.append(tab)
        tab = []
        inner = []

    for tab_nam, co in zip(tab_names, col):
        layout.append(sg.Tab(tab_nam, co,))

    layout = [[sg.TabGroup([layout])]]

    layout = [[sg.Column(layout)],
              [sg.OK(button_text="Save")]]

    # Display the window and get values
    window = sg.Window('Options', layout)

    while True:
        event, values = window.read()
        if "max" in event:
            if float(values[event]) < float(values[event.replace("_max","_min")]):
                sg.Popup("Max value is less than minimum - setting to minimum")
                window[event].update(window[event.replace("max","min")].Get())
        if "min" in event:
            if float(values[event]) > float(values[event.replace("_min","_max")]):
                sg.Popup("Min value is more than maximum - setting to maximum")
                window[event].update(window[event.replace("min","max")].Get())
        if not window[event].metadata is None:
            try:
                #try converting type
                window[event].metadata(window[event].Get())
            except:
                sg.Popup(f"Unexpected data type - clearing value")
                window[event].update("")

        if event == "Save":
            update_config(values)
            window.close()
            break
    window.close()

def update_block():


    layout = [[sg.Column(layout)],
              [sg.OK(button_text="Save")]]

    # Display the window and get values
    window = sg.Window('Options', layout)

    while True:
        event, values = window.read()
        if event == "Save":
            break
    window.close()