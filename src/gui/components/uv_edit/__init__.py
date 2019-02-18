from ...base import *
from ...toolbar import *
from .transform import TransformToolbar
from .uv_set import UVSetPanel
from .subobj import SubobjectPanel
from .background import BackgroundPanel
from .export import ExportPanel


class UVEditGUI(object):

    def __init__(self, main_components):

        self._display_region = None
        self._mouse_watcher = None
        self._main_components = main_components
        self._components = components = {}
        docks = main_components["docks"]
        dock = docks["top"]
        toolbar = TransformToolbar(dock)
        toolbar.hide()

        panel_stack = main_components["panel_stack"]
        components["uv_set_panel"] = UVSetPanel(panel_stack)
        components["subobj_panel"] = SubobjectPanel(panel_stack)
        components["background_panel"] = BackgroundPanel(panel_stack)
        components["export_panel"] = ExportPanel(panel_stack)
        self._hotkey_prev = None
        self._is_enabled = False

        Mgr.accept("update_uv_layout", self.__update_layout)

    def __create_layout(self):

        layout_data = GlobalData["config"]["gui_layout"]["uv"]
        Mgr.do("create_layout", layout_data)

    def __clear_layout(self):

        layout_data = GlobalData["config"]["gui_layout"]["uv"]
        Mgr.do("clear_layout", layout_data)

    def __update_layout(self):

        self.__clear_layout()
        self.__create_layout()
        Mgr.do("update_window")

    def setup(self):

        def enter_editing_mode(prev_state_id, is_active):

            color = Skin["colors"]["viewport_frame_edit_uvs"]
            index = GlobalData["viewport"]["active"]
            GlobalData["viewport"]["border_color{:d}".format(index)] = color
            GlobalData["viewport"]["border{:d}".format(index)].set_clear_color(color)

            if not is_active:

                key_handlers = {
                    "down": self.__on_key_down,
                    "up": self.__on_key_up
                }
                Mgr.add_interface("uv", key_handlers)
                Mgr.add_state("uv_edit_mode", 0, lambda prev_state_id, is_active:
                              Mgr.do("enable_gui"), interface_id="uv")
                Mgr.add_state("region_selection_mode", -11, lambda prev_state_id, is_active:
                              Mgr.do("enable_gui", False), interface_id="uv")
                base = Mgr.get("base")

                GlobalData["viewport"][1] = "uv"
                GlobalData["viewport"][2] = "main"
                GlobalData["viewport"]["border_color2"] = color

                main_components = self._main_components
                components = self._components

                context_submenu_items = main_components["main_context_submenu_items"]
                context_submenu = main_components["main_context_submenu"]
                context_submenu.remove("edit")
                context_submenu.remove("create")
                context_submenu.update(update_initial_pos=False)
                menubar = main_components["menubar"]
                menubar.hide_menu("edit")
                menubar.hide_menu("create")
                menubar.get_menu("edit").enable_hotkeys(False)
                menubar.get_menu("create").enable_hotkeys(False)
                menu = menubar.get_menu("file")
                menu.enable_item("export", False)
                menu.enable_item("import", False)
                disabler = lambda: "uv" in (GlobalData["viewport"][1], GlobalData["viewport"][2])
                Mgr.do("disable_selection_dialog", "uv", disabler)

                Mgr.do("clear_main_layout")
                self.__create_layout()

                panel_stack = main_components["panel_stack"]

                # Show all panels used in the UV interface

                for panel_id in ("uv_set", "subobj", "background", "export"):
                    panel = components["{}_panel".format(panel_id)]
                    panel.enable_hotkeys()
                    panel_stack.show_panel(panel)

                toolbars = Toolbar.registry

                for toolbar_id in ("transform", "material", "history", "snap_align"):
                    toolbars[toolbar_id].enable_hotkeys(False)

                transform_toolbar = toolbars["uv_transform"]
                transform_toolbar.setup()
                transform_toolbar.add_interface_updaters()
                transform_toolbar.enable_hotkeys()

                components["subobj_panel"].setup()
                components["subobj_panel"].add_interface_updaters()
                components["uv_set_panel"].add_interface_updaters()
                components["background_panel"].add_interface_updaters()
                components["export_panel"].add_interface_updaters()

                # Hide all panels used in the main interface

                for panel_id in ("hierarchy", "prop", "material"):
                    panel = main_components["{}_panel".format(panel_id)]
                    panel.enable_hotkeys(False)
                    panel_stack.show_panel(panel, False)

                on_close = lambda: Mgr.update_remotely("uv_interface", False)
                region, mouse_watcher_node = Mgr.do("open_aux_viewport", "uv_edit", "UV", on_close)
                self._display_region = region
                self._mouse_watcher = mouse_watcher_node

                Mgr.do("update_window")
                Mgr.update_remotely("uv_interface", True, region, mouse_watcher_node)
                Mgr.do("set_interface_status", "uv")
                Mgr.update_app("status", ["select_uvs", ""], "uv")

        def exit_editing_mode(next_state_id, is_active):

            if not is_active:

                base = Mgr.get("base")
                region = self._display_region
                self._display_region = None
                base.win.remove_display_region(region)
                mouse_watcher = NodePath(self._mouse_watcher)
                self._mouse_watcher = None
                mouse_watcher.remove_node()
                GlobalData["active_obj_level"] = "top"

                main_components = self._main_components
                docking_targets = main_components["docking_targets"]
                components = self._components

                context_submenu_items = main_components["main_context_submenu_items"]
                context_submenu = main_components["main_context_submenu"]
                context_submenu.add_item(context_submenu_items["edit"], index=1)
                context_submenu.add_item(context_submenu_items["create"], index=2)
                context_submenu.update(update_initial_pos=False)
                menubar = main_components["menubar"]
                menubar.show_menu("edit", index=1)
                menubar.show_menu("create", index=2)
                menubar.get_menu("edit").enable_hotkeys()
                menubar.get_menu("create").enable_hotkeys()
                menu = menubar.get_menu("file")
                menu.enable_item("export")
                menu.enable_item("import")
                Mgr.do("enable_selection_dialog", "uv")

                toolbars = Toolbar.registry

                for toolbar_id in ("transform", "material", "history", "snap_align"):
                    toolbars[toolbar_id].enable_hotkeys()

                transform_toolbar = toolbars["uv_transform"]
                transform_toolbar.enable_hotkeys(False)

                self.__clear_layout()
                Mgr.do("create_main_layout")

                panel_stack = main_components["panel_stack"]

                # Hide all panels used in the UV interface

                for panel_id in ("uv_set", "subobj", "background", "export"):
                    panel = components["{}_panel".format(panel_id)]
                    panel.enable_hotkeys(False)
                    panel_stack.show_panel(panel, False)

                # Show all panels used in the main interface

                for panel_id in ("hierarchy", "prop", "material"):
                    panel = main_components["{}_panel".format(panel_id)]
                    panel.enable_hotkeys()
                    panel_stack.show_panel(panel)

                Mgr.do("update_window")

        add_state = Mgr.add_state
        add_state("uv_edit_mode", -10, enter_editing_mode, exit_editing_mode)

        panel_stack = self._main_components["panel_stack"]
        components = self._components
        components["uv_set_panel"].setup()
        components["subobj_panel"].setup()
        components["background_panel"].setup()
        components["export_panel"].setup()
        panel_stack.show_panel(components["uv_set_panel"], False)
        panel_stack.show_panel(components["subobj_panel"], False)
        panel_stack.show_panel(components["background_panel"], False)
        panel_stack.show_panel(components["export_panel"], False)

    def __on_key_down(self, key=None):

        if not self._is_enabled:
            return

        mod_code = 0
        mod_key_codes = GlobalData["mod_key_codes"]

        if GlobalData["alt_down"]:
            mod_code |= mod_key_codes["alt"]

        if GlobalData["ctrl_down"]:
            mod_code |= mod_key_codes["ctrl"]

        if GlobalData["shift_down"]:
            mod_code |= mod_key_codes["shift"]

        hotkey = (key, mod_code)

        if self._hotkey_prev == hotkey:
            hotkey_repeat = True
        else:
            hotkey_repeat = False
            self._hotkey_prev = hotkey

        HotkeyManager.handle_widget_hotkey(hotkey, hotkey_repeat, "uv")

    def __on_key_up(self, key=None):

        self._hotkey_prev = None

    def enable(self, enable=True):

        self._is_enabled = enable
