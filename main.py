from src import *


class App(object):

    def __init__(self):

        def init_config():

            config_data = {"skin": "default", "texfile_paths": [], "custom_colors": [], "recent_dirs": []}

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

        GlobalData["status_data"] = {}
        mgr = AppManager(verbose=False)
        gui = GUI(mgr, verbose=True)
        core = Core(mgr, verbose=True)

        core_listener = core.get_listener()
        gui_key_handlers = gui.get_key_handlers()

        mgr.setup(core_listener, gui_key_handlers)
        gui.setup()
        core.setup()

        mgr.set_default_state("main", "selection_mode")

        mgr.get_base().run()


App()
