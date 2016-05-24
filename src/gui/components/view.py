from ..base import *


class ViewManager(object):

    def __init__(self, menubar, viewport):

        self._menubar = menubar
        menubar.add_menu("view", "View")
        menubar.add_menu("std_views", "Standard views", "view")

        views = ("persp", "ortho", "front", "back", "left", "right", "top")
        accelerators = ("P", "O", "F", "B", "L", "R", "T")
        mod_code = wx.MOD_SHIFT
        hotkeys = [(ord(accel), mod_code) for accel in accelerators]
        get_handler = lambda view: lambda: Mgr.update_remotely("view", "set", view)

        for view, accel, hotkey in zip(views, accelerators, hotkeys):
            menubar.add_menu_item("std_views", view, "%s\tSHIFT+%s" % (view.title(), accel),
                                  get_handler(view), hotkey)

        mod_code = wx.MOD_SHIFT | wx.MOD_ALT
        hotkey = (ord("B"), mod_code)
        menubar.add_menu_item("std_views", "bottom", "Bottom\tSHIFT+ALT+B",
                              get_handler("bottom"), hotkey)
        menubar.add_menu("user_views", "User views", "view")
        menubar.add_menu("edit_user_views", "Edit", "user_views")
        menubar.add_menu_item_separator("user_views")
        menubar.add_menu_item("edit_user_views", "copy_persp", "Create as persp copy",
                              lambda: Mgr.update_remotely("view", "init_copy", "persp"))
        menubar.add_menu_item("edit_user_views", "copy_ortho", "Create as ortho copy",
                              lambda: Mgr.update_remotely("view", "init_copy", "ortho"))
        mod_code = wx.MOD_SHIFT
        hotkey = (ord("U"), mod_code)
        menubar.add_menu_item("edit_user_views", "snapshot", "Create as snapshot\tSHIFT+U",
                              self.__init_snapshot, hotkey)
        menubar.add_menu_item_separator("edit_user_views")
        menubar.add_menu_item("edit_user_views", "convert_persp", "Convert to persp",
                              lambda: Mgr.update_remotely("view", "convert", "persp"))
        menubar.add_menu_item("edit_user_views", "convert_ortho", "Convert to ortho",
                              lambda: Mgr.update_remotely("view", "convert", "ortho"))
        menubar.add_menu_item_separator("edit_user_views")
        hotkey = (wx.WXK_F2, mod_code)
        menubar.add_menu_item("edit_user_views", "rename", "Rename\tSHIFT+F2",
                              lambda: Mgr.update_remotely("view", "init_rename"), hotkey)
        menubar.add_menu_item_separator("edit_user_views")
        hotkey = (wx.WXK_DELETE, mod_code)
        menubar.add_menu_item("edit_user_views", "remove", "Remove\tSHIFT+DEL",
                              lambda: Mgr.update_remotely("view", "init_remove"), hotkey)
        menubar.add_menu_item("edit_user_views", "clear", "Remove all",
                              lambda: Mgr.update_remotely("view", "init_clear"))
        menubar.add_menu_item_separator("view")
        hotkey = (ord("C"), 0)
        func = lambda: wx.CallLater(10., lambda: Mgr.update_remotely("view", "center"))
        menubar.add_menu_item("view", "obj_center", "Center on objects\tC", func, hotkey)
        menubar.add_menu_item("view", "obj_align", "Align to object...",
                              lambda: Mgr.update_remotely("view", "obj_align"))
        menubar.add_menu_item_separator("view")
        hotkey = (wx.WXK_HOME, 0)
        func = lambda: wx.CallLater(10., lambda: Mgr.update_remotely("view", "reset", False, True))
        menubar.add_menu_item("view", "home", "Home\tHOME", func, hotkey)
        menubar.add_menu_item("view", "set_home", "Set current as Home",
                              lambda: Mgr.update_remotely("view", "set_as_home"))
        menubar.add_menu_item("view", "reset_home", "Reset Home",
                              lambda: Mgr.update_remotely("view", "reset_home"))
        menubar.add_menu_item_separator("view")
        menubar.add_menu_item("view", "set_front", "Set current as Front",
                              lambda: Mgr.update_remotely("view", "set_as_front"))
        func = lambda: wx.CallLater(10., lambda: Mgr.update_remotely("view", "reset_front"))
        menubar.add_menu_item("view", "reset_front", "Reset Front", func)
        menubar.add_menu_item_separator("view")
        func = lambda: wx.CallLater(10., lambda: Mgr.update_remotely("view", "reset", True, True))
        menubar.add_menu_item("view", "reset", "Reset", func)
        menubar.add_menu_item("view", "reset_all", "Reset all", lambda: Mgr.update_remotely("view", "reset_all"))

        self._viewport = viewport
        menu_std = wx.Menu()
        menu_user = wx.Menu()
        self._popup_menus = {"std": menu_std, "user": menu_user}

        for menu in (menu_std, menu_user):
            item = menu.Append(-1, "Copy to persp")
            command = lambda evt: Mgr.update_remotely("view", "init_copy", "persp")
            viewport.Bind(wx.EVT_MENU, command, item)
            item = menu.Append(-1, "Copy to ortho")
            command = lambda evt: Mgr.update_remotely("view", "init_copy", "ortho")
            viewport.Bind(wx.EVT_MENU, command, item)
            item = menu.Append(-1, "Take snapshot\tSHIFT+U")
            command = lambda evt: self.__init_snapshot()
            viewport.Bind(wx.EVT_MENU, command, item)

        menu_user.AppendSeparator()
        item = menu_user.Append(-1, "Convert to persp")
        command = lambda evt: Mgr.update_remotely("view", "convert", "persp")
        viewport.Bind(wx.EVT_MENU, command, item)
        item = menu_user.Append(-1, "Convert to ortho")
        command = lambda evt: Mgr.update_remotely("view", "convert", "ortho")
        viewport.Bind(wx.EVT_MENU, command, item)
        menu_user.AppendSeparator()
        item = menu_user.Append(-1, "Rename\tSHIFT+F2")
        command = lambda evt: Mgr.update_remotely("view", "init_rename")
        viewport.Bind(wx.EVT_MENU, command, item)
        item = menu_user.Append(-1, "Remove\tSHIFT+DEL")
        command = lambda evt: Mgr.update_remotely("view", "init_remove")
        viewport.Bind(wx.EVT_MENU, command, item)

        Mgr.add_app_updater("view", self.__update_view)

    def setup(self):

        def enter_obj_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", (0, 255, 255))
            Mgr.do("enable_components")

        add_state = Mgr.add_state
        add_state("view_obj_picking_mode", -75, enter_obj_picking_mode)

    def __update_view(self, update_type, *args):

        if update_type == "get_copy_name":
            self.__get_view_copy_name(*args)
        elif update_type == "add":
            self.__add_user_view(*args)
        elif update_type == "confirm_remove":
            self.__confirm_remove_user_view(*args)
        elif update_type == "remove":
            self.__remove_user_view(*args)
        elif update_type == "confirm_clear":
            self.__confirm_clear_user_views(*args)
        elif update_type == "get_new_name":
            self.__get_new_view_name(*args)
        elif update_type == "rename":
            self.__rename_user_view(*args)
        elif update_type == "menu":
            self.__popup_menu(*args)

    def __get_view_name(self, default_name=None):

        name = "New" if default_name is None else default_name
        view_name = wx.GetTextFromUser(
                                        "Please enter a name for this user view:",
                                        "Name user view", name, None
                                      )

        if GlobalData["shift_down"]:
            GlobalData["shift_down"] = False

        return view_name

    def __get_view_copy_name(self, lens_type, proposed_name):

        name = self.__get_view_name(proposed_name)

        if name:
            Mgr.update_remotely("view", "copy", lens_type, name)

    def __init_snapshot(self):

        name = self.__get_view_name()

        if name:
            Mgr.update_remotely("view", "take_snapshot", name)

    def __add_user_view(self, view_id, view_name):

        get_handler = lambda view: lambda: Mgr.update_app("view", "set", view)
        self._menubar.add_menu_item("user_views", view_id, view_name, get_handler(view_id))

    def __get_new_view_name(self, current_name):

        name = self.__get_view_name(current_name)

        if name and name != current_name:
            Mgr.update_remotely("view", "rename", name)

    def __rename_user_view(self, view_id, view_name):

        self._menubar.rename_menu_item(view_id, view_name)

    def __confirm_remove_user_view(self, view_name):

        msg = "You have chosen to remove the following user view:\n\n" + view_name
        msg += "\n\nAre you sure?"
        answer = wx.MessageBox(msg, "Confirm user view removal",
                               wx.OK|wx.CANCEL|wx.ICON_EXCLAMATION, Mgr.get("main_window"))

        if answer == wx.OK:
            Mgr.update_remotely("view", "remove")

    def __remove_user_view(self, view_id):

        self._menubar.remove_menu_item("user_views", view_id)

    def __confirm_clear_user_views(self, view_count):

        answer = wx.MessageBox("Are you sure you want to remove all %d user views?" % view_count,
                               "Confirm user view removal",
                               wx.OK|wx.CANCEL|wx.ICON_EXCLAMATION, Mgr.get("main_window"))

        if answer == wx.OK:
            Mgr.update_remotely("view", "clear")

    def __popup_menu(self, menu_id):

        menu = self._popup_menus[menu_id]
        self._viewport.PopupMenuXY(menu)
