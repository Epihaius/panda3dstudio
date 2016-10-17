from ..base import *


class EditManager(object):

    def __init__(self, menubar, uv_edit_command):

        menubar.add_menu("edit", "Edit")

        handler = lambda: Mgr.update_app("history", "undo")
        menubar.add_menu_item("edit", "undo", "Undo\tCTRL+Z", handler)
        handler = lambda: Mgr.update_app("history", "redo")
        menubar.add_menu_item("edit", "redo", "Redo\tSHIFT+CTRL+Z", handler)
        handler = lambda: Mgr.update_app("history", "edit")
        menubar.add_menu_item("edit", "hist", "History...", handler)

        menubar.add_menu_item_separator("edit")

        handler = lambda: Mgr.update_remotely("group", "create")
        hotkey = (ord("G"), wx.MOD_CONTROL)
        menubar.add_menu_item("edit", "group", "Create group\tCTRL+G", handler, hotkey)
        handler = lambda: Mgr.enter_state("grouping_mode")
        menubar.add_menu_item("edit", "add_to_group", "Add to group...", handler)
        handler = lambda: Mgr.update_remotely("group", "remove_members")
        menubar.add_menu_item("edit", "remove_from_group", "Remove from group", handler)

        menubar.add_menu_item_separator("edit")

        hotkey = (ord("U"), wx.MOD_CONTROL)
        menubar.add_menu_item("edit", "uvs", "Edit UVs\tCTRL+U", uv_edit_command, hotkey)

    def setup(self):

        def enter_grouping_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (255, 128, 255))
            Mgr.do("enable_components")

        add_state = Mgr.add_state
        add_state("grouping_mode", -10, enter_grouping_mode)
