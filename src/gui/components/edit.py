from ..base import *


class EditManager:

    def __init__(self, menubar, uv_edit_command):

        self._menu = menu = menubar.add_menu("edit", "Edit")
        mod_key_codes = GD["mod_key_codes"]

        handler = lambda: Mgr.update_app("history", "undo")
        menu.add("undo", "Undo", handler)
        hotkey = ("z", mod_key_codes["ctrl"])
        menu.set_item_hotkey("undo", hotkey, "Ctrl+Z")
        handler = lambda: Mgr.update_app("history", "redo")
        menu.add("redo", "Redo", handler)
        hotkey = ("y", mod_key_codes["ctrl"])
        menu.set_item_hotkey("redo", hotkey, "Ctrl+Y")
        handler = lambda: Mgr.update_app("history", "edit")
        menu.add("hist", "History...", handler)

        menu.add("sep0", item_type="separator")

        handler = lambda: Mgr.update_remotely("group", "create")
        menu.add("group", "Create group", handler)
        hotkey = ("g", mod_key_codes["ctrl"])
        menu.set_item_hotkey("group", hotkey, "Ctrl+G")

        def handler():

            if GD["active_obj_level"] != "top":
                GD["active_obj_level"] = "top"
                Mgr.update_app("active_obj_level")

            Mgr.enter_state("grouping_mode")

        menu.add("add_to_group", "Add to group...", handler)
        handler = lambda: Mgr.update_remotely("group", "remove_members")
        menu.add("remove_from_group", "Remove from group", handler)

        menu.add("sep1", item_type="separator")

        menu.add("uvs", "Edit UVs", uv_edit_command)
        hotkey = ("u", mod_key_codes["ctrl"])
        menu.set_item_hotkey("uvs", hotkey, "Ctrl+U")

        Mgr.add_app_updater("history", self.__check_undo_redo)

    def setup(self):

        def enter_grouping_mode(prev_state_id, active):

            Mgr.do("set_viewport_border_color", "viewport_frame_group_objects")
            Mgr.do("enable_gui")

        add_state = Mgr.add_state
        add_state("grouping_mode", -10, enter_grouping_mode)

    def __check_undo_redo(self, update_type, *args, **kwargs):

        if update_type != "check":
            return

        to_undo = GD["history_to_undo"]
        to_redo = GD["history_to_redo"]
        menu = self._menu
        menu.enable_item("undo", to_undo)
        menu.enable_item("redo", to_redo)
        menu.enable_item("hist", to_undo or to_redo)
