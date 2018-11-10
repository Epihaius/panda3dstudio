from ..base import *
from ..dialog import *


class OptionManager(object):

    def __init__(self, menubar):

        main_menu = menubar.add_menu("options", "Options")
        item = main_menu.add("customize", "Customize", item_type="submenu")
        self._customize_menu = menu = item.get_submenu()
        item = menu.add("gui", "GUI", item_type="submenu")
        gui_menu = item.get_submenu()
        item = gui_menu.add("gui_layout", "Layout", item_type="submenu")
        gui_menu.add("sep0", item_type="separator")
        layout_menu = item.get_submenu()
        item = gui_menu.add("gui_skin", "Skin", item_type="submenu")
        layout_menu.add("gui_layout_reset", "Reset", self.__reset_gui_layout)
        layout_menu.add("gui_layout_load", "Load", self.__load_gui_layout)
        layout_menu.add("gui_layout_save", "Save", self.__save_gui_layout)
        layout_menu.add("sep0", item_type="separator")
        command = self.__set_right_dock_side
        item = layout_menu.add("ctrl_pane_left", "Control pane left", command, item_type="check")
        self._menu_items = {"ctrl_pane_left": item}

    def setup(self):

        layout = GlobalData["config"]["gui_layout"]
        self._menu_items["ctrl_pane_left"].check(layout["right_dock"] == "left")

    def __set_right_dock_side(self):

        layout = GlobalData["config"]["gui_layout"]
        side = "right" if layout["right_dock"] == "left" else "left"
        Mgr.do("set_right_dock_side", side)

    def __reset_gui_layout(self):

        interface_id = GlobalData["active_interface"]

        def update_layout(of_all_interfaces=True):

            if of_all_interfaces:
                Mgr.do("reset_layout_data")
            else:
                Mgr.do("reset_layout_data", interface_id)

            Mgr.do("set_right_dock_side", "right")
            Mgr.do("update_{}_layout".format(interface_id))
            self._menu_items["ctrl_pane_left"].check(False)

        if interface_id == "main":
            interface_name = "main"
        elif interface_id == "uv":
            interface_name = "UV"

        MessageDialog(title="Update GUI layout",
                      message="Reset layout of {} interface only?".format(interface_name),
                      choices="yesnocancel",
                      on_yes=lambda: update_layout(of_all_interfaces=False),
                      on_no=update_layout)

    def __load_gui_layout(self):

        def on_yes(filename):

            config_data = GlobalData["config"]
            interface_id = GlobalData["active_interface"]

            with open(filename, "rb") as layout_file:
                try:
                    if pickle.load(layout_file) != "Panda3D Studio GUI Layout":
                        self.__handle_load_error(filename, "id")
                        return
                    layout = pickle.load(layout_file)
                except:
                    self.__handle_load_error(filename, "read")

            def update_layout(of_all_interfaces=True):

                if of_all_interfaces:
                    config_data["gui_layout"] = layout
                else:
                    config_data["gui_layout"][interface_id] = layout[interface_id]
                    config_data["gui_layout"]["right_dock"] = layout["right_dock"]

                with open("config", "wb") as config_file:
                    pickle.dump(config_data, config_file, -1)

                side = layout["right_dock"]
                Mgr.do("set_right_dock_side", side)
                Mgr.do("update_{}_layout".format(interface_id))
                self._menu_items["ctrl_pane_left"].check(side == "left")

            if interface_id == "main":
                interface_name = "main"
            elif interface_id == "uv":
                interface_name = "UV"

            MessageDialog(title="Update GUI layout",
                          message="Update layout of {} interface only?".format(interface_name),
                          choices="yesnocancel",
                          on_yes=lambda: update_layout(of_all_interfaces=False),
                          on_no=update_layout)

        FileDialog(title="Load GUI layout",
                   ok_alias="Load",
                   file_op="read",
                   on_yes=on_yes,
                   file_types=("GUI layouts|p3dslayout", "All types|*"),
                   default_filename="")

    def __handle_load_error(self, filename, error_type):

        if error_type == "read":
            MessageDialog(title="Error loading layout",
                          message="The following file could not be read:\n\n" \
                                  + Filename(filename).to_os_specific(),
                          choices="ok",
                          icon_id="icon_exclamation")
        elif error_type == "id":
            MessageDialog(title="Error loading layout",
                          message="The following file does not appear to be a valid layout:\n\n" \
                                  + Filename(filename).to_os_specific(),
                          choices="ok",
                          icon_id="icon_exclamation")

    def __save_gui_layout(self):

        def on_yes(filename):

                with open(filename, "wb") as layout_file:
                    pickle.dump("Panda3D Studio GUI Layout", layout_file, -1)
                    pickle.dump(GlobalData["config"]["gui_layout"], layout_file, -1)

        FileDialog(title="Save GUI layout",
                   ok_alias="Save", on_yes=on_yes, file_op="write",
                   incr_filename=True, file_types=("GUI layouts|p3dslayout", "All types|*"),
                   default_filename="")
