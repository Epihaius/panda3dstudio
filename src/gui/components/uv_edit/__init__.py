from ...base import *
from ...toolbar import *
from .transform import TransformToolbar
from .uv_set import UVSetPanel
from .subobj import SubobjectPanel
from .background import BackgroundPanel
from .export import ExportPanel


class UVEditGUI:

    def __init__(self, main_components):

        self.display_region = None
        self._mouse_watcher = None
        self._main_components = main_components
        self._components = components = {}
        docks = main_components["docks"]
        dock = docks["top"]
        toolbar = TransformToolbar(dock)
        toolbar.hide()

        control_pane = main_components["control_pane"]
        components["panels"] = panels = {}
        panel_classes = {}
        panel_classes["uv_set"] = UVSetPanel
        panel_classes["subobj"] = SubobjectPanel
        panel_classes["background"] = BackgroundPanel
        panel_classes["export"] = ExportPanel

        for panel_id in Skin.layout.control_panels["uv"]:
            if panel_id in panel_classes:
                panels[panel_id] = panel_classes[panel_id](control_pane)

        self._hotkey_prev = None
        self._is_enabled = False

        Mgr.accept("update_uv_toolbar_layout", self.__update_toolbar_layout)

    def __create_toolbar_layout(self):

        config_data = GD["config"]

        if config_data["gui_view"]["toolbars"]:
            layout_data = config_data["gui_layout"]["toolbars"]["uv"]
            Mgr.do("create_toolbar_layout", layout_data)

    def __clear_toolbar_layout(self):

        config_data = GD["config"]

        if config_data["gui_view"]["toolbars"]:
            layout_data = config_data["gui_layout"]["toolbars"]["uv"]
            Mgr.do("clear_toolbar_layout", layout_data)

    def __update_toolbar_layout(self):

        self.__clear_toolbar_layout()
        self.__create_toolbar_layout()
        Mgr.do("update_window")

    def setup(self):

        def enter_editing_mode(prev_state_id, active):

            color = Skin.colors["viewport_frame_edit_uvs"]
            index = GD["viewport"]["active"]
            GD["viewport"][f"border_color{index}"] = color
            GD["viewport"][f"border{index}"].clear_color = color

            if not active:

                key_handlers = {
                    "down": self.__on_key_down,
                    "up": self.__on_key_up
                }
                Mgr.add_interface("uv", key_handlers)
                Mgr.add_state("uv_edit_mode", 0, lambda prev_state_id, active:
                              Mgr.do("enable_gui"), interface_id="uv")
                Mgr.add_state("region_selection_mode", -11, lambda prev_state_id, active:
                              Mgr.do("enable_gui", False), interface_id="uv")

                GD["viewport"][1] = "uv"
                GD["viewport"][2] = "main"
                GD["viewport"]["border_color2"] = color

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
                menubar.get_menu("view").enable_item("obj_align", False)
                disabler = lambda: "uv" in (GD["viewport"][1], GD["viewport"][2])
                Mgr.do("disable_selection_dialog", "uv", disabler)

                Mgr.do("clear_main_toolbar_layout")
                self.__create_toolbar_layout()

                control_pane = main_components["control_pane"]
                main_panel_ids = set(Skin.layout.control_panels["main"])
                uv_panel_ids = set(Skin.layout.control_panels["uv"])

                # show all panels used in the UV interface
                for panel_id in uv_panel_ids - main_panel_ids:
                    panel = components["panels"][panel_id]
                    panel.enable_hotkeys()
                    control_pane.show_panel(panel)

                toolbars = Toolbar.registry

                for toolbar_id in ("transform", "material", "history", "snap_align"):
                    toolbars[toolbar_id].enable_hotkeys(False)

                transform_toolbar = toolbars["uv_transform"]
                transform_toolbar.setup()
                transform_toolbar.add_interface_updaters()
                transform_toolbar.enable_hotkeys()

                components["panels"]["subobj"].setup()

                for panel in components["panels"].values():
                    panel.add_interface_updaters()

                # hide all panels used in the main interface
                for panel_id in main_panel_ids - uv_panel_ids:
                    panel = main_components["panels"][panel_id]
                    panel.enable_hotkeys(False)
                    control_pane.show_panel(panel, False)

                on_close = lambda: Mgr.update_remotely("uv_interface", False)
                region, mouse_watcher_node = Mgr.do("open_aux_viewport", "uv_edit", "UV", on_close)
                self.display_region = region
                self._mouse_watcher = mouse_watcher_node

                Mgr.do("update_window")
                Mgr.update_remotely("uv_interface", True, region, mouse_watcher_node)
                Mgr.do("set_interface_status", "uv")
                Mgr.update_app("status", ["select_uvs", ""], "uv")

        def exit_editing_mode(next_state_id, active):

            if not active:

                region = self.display_region
                self.display_region = None
                GD.window.remove_display_region(region)
                mouse_watcher = NodePath(self._mouse_watcher)
                self._mouse_watcher = None
                mouse_watcher.detach_node()
                GD["active_obj_level"] = "top"

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
                view_ids = ("front", "back", "left", "right", "bottom", "top")
                enable = GD["view"] not in view_ids
                menubar.get_menu("view").enable_item("obj_align", enable)
                Mgr.do("enable_selection_dialog", "uv")

                toolbars = Toolbar.registry

                for toolbar_id in ("transform", "material", "history", "snap_align"):
                    toolbars[toolbar_id].enable_hotkeys()

                transform_toolbar = toolbars["uv_transform"]
                transform_toolbar.enable_hotkeys(False)

                self.__clear_toolbar_layout()
                Mgr.do("create_main_toolbar_layout")

                control_pane = main_components["control_pane"]
                main_panel_ids = set(Skin.layout.control_panels["main"])
                uv_panel_ids = set(Skin.layout.control_panels["uv"])

                # hide all panels used in the UV interface
                for panel_id in uv_panel_ids - main_panel_ids:
                    panel = components["panels"][panel_id]
                    panel.enable_hotkeys(False)
                    control_pane.show_panel(panel, False)

                # show all panels used in the main interface
                for panel_id in main_panel_ids - uv_panel_ids:
                    panel = main_components["panels"][panel_id]
                    panel.enable_hotkeys()
                    control_pane.show_panel(panel)

                Mgr.do("update_window")

        add_state = Mgr.add_state
        add_state("uv_edit_mode", -10, enter_editing_mode, exit_editing_mode)

        control_pane = self._main_components["control_pane"]
        panels = self._components["panels"]

        for panel in panels.values():
            panel.setup()
            control_pane.show_panel(panel, False)

    def __on_key_down(self, key=None):

        if not self._is_enabled:
            return

        mod_code = 0
        mod_key_codes = GD["mod_key_codes"]

        if GD["alt_down"]:
            mod_code |= mod_key_codes["alt"]

        if GD["ctrl_down"]:
            mod_code |= mod_key_codes["ctrl"]

        if GD["shift_down"]:
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
