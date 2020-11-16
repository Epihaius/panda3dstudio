from ..base import *
from ..button import *
from ..toolbar import *
from ..dialogs import *


class SnapToolbar(Toolbar):

    def __init__(self, parent, toolbar_id):

        Toolbar.__init__(self, parent, toolbar_id)

        self.widgets = widgets = Skin.layout.create(self, "snap_align")

        self._btns = btns = {}

        btn = widgets["buttons"]["snap"]
        btn.command = lambda: Mgr.update_locally("object_snap", "snap")
        hotkey = ("s", 0)
        btn.set_hotkey(hotkey, "S")
        btn.enable(False)
        btns["snap"] = btn

        btn = widgets["buttons"]["snap_options"]
        btn.command = lambda: SnapDialog()
        btn.enable(False)
        btns["snap_options"] = btn

        tools_menu = Mgr.get("main_gui_components")["main_context_tools_menu"]
        item = tools_menu.add("snap", "Snap", self._btns["snap"].press, item_type="check")
        item.enable(False)
        self._tools_menu_item = item
        tools_menu = Mgr.get("tool_options_menu")
        item = tools_menu.add("snap", "Snap", lambda: self.__update_snapping("show_options"))
        item.enable(False)
        self._tool_options_menu_item = item

        Mgr.add_app_updater("object_snap", self.__update_snapping)

    def setup(self):

        def enter_transf_start_snap_mode(prev_state_id, active):

            Mgr.do("enable_gui", False)

        def exit_transf_start_snap_mode(next_state_id, active):

            Mgr.do("enable_gui")

        add_state = Mgr.add_state
        add_state("transf_start_snap_mode", -1, enter_transf_start_snap_mode,
                  exit_transf_start_snap_mode)

    def __update_snapping(self, update_type, *args):

        if update_type == "reset":

            self._btns["snap"].active = False
            self._btns["snap"].enable(False)
            self._btns["snap_options"].enable(False)
            self._tools_menu_item.enable(False)
            self._tool_options_menu_item.enable(False)

        elif update_type == "enable":

            enable, force_snap_on = args

            if enable:

                self._btns["snap"].enable()
                self._btns["snap_options"].enable()
                self._tools_menu_item.enable()
                self._tool_options_menu_item.enable()

                if force_snap_on:
                    self._btns["snap"].active = True
                    self._tools_menu_item.check()
                else:
                    snap_settings = GD["snap"]
                    snap_type = snap_settings["type"]
                    active = snap_settings["on"][snap_type]
                    self._btns["snap"].active = active
                    self._tools_menu_item.check(active)

            else:

                if not (Mgr.is_state_active("creation_mode")
                        or GD["active_transform_type"]):
                    self._btns["snap"].enable(False)
                    self._btns["snap_options"].enable(False)
                    self._tools_menu_item.enable(False)
                    self._tools_menu_item.check(False)
                    self._tool_options_menu_item.enable(False)
                else:
                    snap_settings = GD["snap"]
                    snap_type = snap_settings["prev_type"]
                    active = snap_settings["on"][snap_type]
                    self._btns["snap"].active = active
                    self._tools_menu_item.check(active)

        elif update_type == "show_options":

            SnapDialog()

        elif update_type == "snap":

            snap_settings = GD["snap"]
            snap_type = snap_settings["type"]

            if snap_type in ("transf_center", "coord_origin"):
                self._btns["snap"].active = True
                self._tools_menu_item.check()
                return

            snap_on = not snap_settings["on"][snap_type]
            snap_settings["on"][snap_type] = snap_on
            self._btns["snap"].active = snap_on
            self._tools_menu_item.check(snap_on)

            transf_type = GD["active_transform_type"]
            state_id = Mgr.get_state_id()

            if transf_type and state_id == "selection_mode":
                if GD["snap"]["on"][transf_type]:
                    Mgr.update_app("status", ["select", transf_type, "snap_idle"])
                else:
                    Mgr.update_app("status", ["select", transf_type, "idle"])
            elif state_id == "creation_mode":
                creation_type = GD["active_creation_type"]
                if GD["snap"]["on"]["creation"]:
                    Mgr.update_app("status", ["create", creation_type, "snap_idle"])
                else:
                    Mgr.update_app("status", ["create", creation_type, "idle"])

            Mgr.update_remotely("object_snap")
