from src import *


class App(object):

    def __init__(self):

        mgr = AppManager(verbose=False)
        mgr.set_global("status_data", {})
        gui = GUI(mgr, verbose=True)
        core = Core(mgr, verbose=True)

        core_listener = core.get_listener()
        core_key_handlers = core.get_key_handlers()
        core_key_evt_ids = core.get_key_event_ids()
        gui_key_handlers = gui.get_key_handlers()
        gui_key_evt_ids = gui.get_key_event_ids()
        gui_mod_key_codes = gui.get_mod_key_codes()
        core_color_max = core.get_max_color_value()
        gui_color_max = gui.get_max_color_value()

        viewport_data = gui.get_viewport_data()
        eventloop_handler = gui.get_event_loop_handler()

        mgr.setup(core_listener, core_key_handlers, core_key_evt_ids,
                  gui_key_handlers, gui_key_evt_ids, gui_mod_key_codes,
                  core_color_max, gui_color_max)
        gui.setup()
        core.setup(viewport_data, eventloop_handler)

        mgr.set_initial_state("", "selection_mode")

        core.run()


App()
