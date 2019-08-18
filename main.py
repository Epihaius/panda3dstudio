#!/usr/bin/env python

from src import *


class App:

    def __init__(self):

        def init_config():

            sel_dialog_config = {
                "sort": "name",
                "sort_case": False,
                "obj_types": ["model", "helper", "group", "light", "camera"],
                "search": {"match_case": True, "part": "start"}
            }
            config_data = {
                "skin": "default", "texfile_paths": [], "custom_colors": [], "recent_dirs": [],
                "sel_dialog": sel_dialog_config
            }

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

            return config_data

        def read_config():

            with open("config", "rb") as config_file:
                return pickle.load(config_file)

        try:
            GlobalData["config"] = read_config()
        except:
            GlobalData["config"] = init_config()

        GlobalData["status"] = {}
        mgr = AppManager()
        gui = GUI(mgr, verbose=True)
        core = Core(mgr, verbose=True)

        core_listener = core.get_listener()
        gui_key_handlers = gui.get_key_handlers()

        mgr.setup(core_listener, gui_key_handlers)
        gui.setup()
        core.setup()

        mgr.set_default_state("main", "selection_mode")

        GlobalData.showbase.run()


App()
