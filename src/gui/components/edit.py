from ..base import *


class EditManager(object):

    def __init__(self, menubar, uv_edit_command):

        menu = menubar.add_menu("edit", "Edit")
        mod_key_codes = GlobalData["mod_key_codes"]

        handler = lambda: Mgr.update_app("history", "undo")
        menu.add("undo", "Undo", handler)
        hotkey = ("z", mod_key_codes["ctrl"])
        menu.set_item_hotkey("undo", "CTRL+Z", hotkey)
        handler = lambda: Mgr.update_app("history", "redo")
        menu.add("redo", "Redo", handler)
        mod_code = mod_key_codes["shift"] | mod_key_codes["ctrl"]
        hotkey = ("z", mod_code)
        menu.set_item_hotkey("redo", "SHIFT+CTRL+Z", hotkey)
        handler = lambda: Mgr.update_app("history", "edit")
        menu.add("hist", "History...", handler)

        menu.add("sep0", item_type="separator")

        handler = lambda: Mgr.update_remotely("group", "create")
        menu.add("group", "Create group", handler)
        hotkey = ("g", mod_key_codes["ctrl"])
        menu.set_item_hotkey("group", "CTRL+G", hotkey)
        handler = lambda: Mgr.enter_state("grouping_mode")
        menu.add("add_to_group", "Add to group...", handler)
        handler = lambda: Mgr.update_remotely("group", "remove_members")
        menu.add("remove_from_group", "Remove from group", handler)

        menu.add("sep1", item_type="separator")

        menu.add("uvs", "Edit UVs", uv_edit_command)
        hotkey = ("u", mod_key_codes["ctrl"])
        menu.set_item_hotkey("uvs", "CTRL+U", hotkey)

    def setup(self):

        def enter_grouping_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_group_objects")
            Mgr.do("enable_gui")

        add_state = Mgr.add_state
        add_state("grouping_mode", -10, enter_grouping_mode)
