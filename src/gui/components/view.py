from ..base import *
from ..text import Text
from ..button import *
from ..menu import Menu
from ..dialog import *
from ..scroll import *


class BackgroundInputField(DialogInputField):

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, parent, width):

        if not self._field_borders:
            self.__set_field_borders()

        DialogInputField.__init__(self, parent, INSET1_BORDER_GFX_DATA, width)

        self.set_image_offset(self._img_offset)

    def get_outer_borders(self):

        return self._field_borders


class BackgroundDialog(Dialog):

    def __init__(self):

        extra_button_data = (("Apply", "", self.__on_yes, None, 1.),)

        Dialog.__init__(self, "View background", "okcancel", on_yes=self.__on_yes,
                        extra_button_data=extra_button_data)

        self._fields = fields = {}
        self._checkboxes = checkboxes = {}
        self._data = data = {}
        current_view_id = GlobalData["view"]
        view_ids = ("front", "back", "left", "right", "bottom", "top")
        view_id = current_view_id if current_view_id in view_ids else "front"
        data.update(GlobalData["view_backgrounds"][view_id])
        data["view"] = view_id
        client_sizer = self.get_client_sizer()

        subsizer = Sizer("horizontal")
        borders = (20, 20, 10, 20)
        client_sizer.add(subsizer, expand=True, borders=borders)

        text = "File..."
        tooltip_text = "Load background image"
        btn = DialogButton(self, text, "", tooltip_text, self.__load_image)
        subsizer.add(btn, alignment="center_v")
        field = BackgroundInputField(self, 100)
        val_id = "filename"
        field.add_value(val_id, "string", handler=self.__handle_value)
        field.show_value(val_id)
        filename = data["filename"]
        field.set_text(val_id, os.path.basename(filename) if filename else "<None>")
        field.set_input_init(val_id, self.__init_filename_input)
        field.set_input_parser(val_id, self.__check_filename)
        field.set_value_parser(val_id, self.__parse_filename)
        fields[val_id] = field
        borders = (10, 0, 0, 0)
        subsizer.add(field, proportion=1., alignment="center_v", borders=borders)

        subsizer = Sizer("horizontal")
        borders = (20, 20, 10, 0)
        client_sizer.add(subsizer, borders=borders)

        get_command = lambda val_id: lambda val: self.__handle_value(val_id, val)

        val_id = "show"
        checkbox = DialogCheckBox(self, get_command(val_id))
        checkbox.check(data[val_id])
        checkboxes[val_id] = checkbox
        subsizer.add(checkbox, alignment="center_v")
        text = DialogText(self, "Show image")
        borders = (5, 20, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        val_id = "in_foreground"
        checkbox = DialogCheckBox(self, get_command(val_id))
        checkbox.check(data[val_id])
        checkboxes[val_id] = checkbox
        subsizer.add(checkbox, alignment="center_v")
        text = DialogText(self, "in foreground instead of background")
        borders = (5, 0, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        subsizer = Sizer("horizontal")
        borders = (20, 20, 10, 0)
        client_sizer.add(subsizer, expand=True, borders=borders)

        text = DialogText(self, "Opacity:")
        subsizer.add(text, alignment="center_v")
        field = BackgroundInputField(self, 100)
        val_id = "alpha"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_value(val_id, data["alpha"])
        field.set_input_parser(val_id, self.__parse_alpha)
        fields[val_id] = field
        borders = (10, 0, 0, 0)
        subsizer.add(field, proportion=1., alignment="center_v", borders=borders)

        group = DialogWidgetGroup(self, "Image offset")
        borders = (20, 20, 0, 0)
        client_sizer.add(group, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        group.add(subsizer, expand=True)

        text = DialogText(group, "Local X:")
        borders = (0, 10, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)
        field = BackgroundInputField(group, 100)
        val_id = "x"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_value(val_id, data["x"])
        fields[val_id] = field
        subsizer.add(field, proportion=1., alignment="center_v")

        text = DialogText(group, "Local Y:")
        borders = (20, 10, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)
        field = BackgroundInputField(group, 100)
        val_id = "y"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_value(val_id, data["y"])
        fields[val_id] = field
        subsizer.add(field, proportion=1., alignment="center_v")

        group = DialogWidgetGroup(self, "Image size")
        borders = (20, 20, 0, 10)
        client_sizer.add(group, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        group.add(subsizer, expand=True)

        text = DialogText(group, "Width:")
        borders = (0, 10, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)
        field = BackgroundInputField(group, 100)
        val_id = "width"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_value(val_id, data["width"])
        field.set_input_parser(val_id, self.__parse_size)
        fields[val_id] = field
        subsizer.add(field, proportion=1., alignment="center_v")

        text = DialogText(group, "Height:")
        borders = (20, 10, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)
        field = BackgroundInputField(group, 100)
        val_id = "height"
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        field.set_value(val_id, data["height"])
        field.set_input_parser(val_id, self.__parse_size)
        fields[val_id] = field
        subsizer.add(field, proportion=1., alignment="center_v")

        subsizer = Sizer("horizontal")
        borders = (0, 0, 0, 2)
        group.add(subsizer, expand=True, borders=borders)

        val_id = "fixed_aspect_ratio"
        checkbox = DialogCheckBox(group, get_command(val_id))
        checkbox.check(data[val_id])
        checkboxes[val_id] = checkbox
        subsizer.add(checkbox, alignment="center_v")
        text = DialogText(group, "Maintain bitmap aspect ratio")
        borders = (5, 0, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        group = DialogWidgetGroup(self, "Flip image")
        borders = (20, 20, 0, 10)
        client_sizer.add(group, expand=True, borders=borders)

        subsizer = Sizer("horizontal")
        group.add(subsizer)

        val_id = "flip_h"
        checkbox = DialogCheckBox(group, get_command(val_id))
        checkbox.check(data[val_id])
        checkboxes[val_id] = checkbox
        subsizer.add(checkbox, alignment="center_v")
        text = DialogText(group, "Horizontally")
        borders = (5, 20, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        val_id = "flip_v"
        checkbox = DialogCheckBox(group, get_command(val_id))
        checkbox.check(data[val_id])
        checkboxes[val_id] = checkbox
        subsizer.add(checkbox, alignment="center_v")
        text = DialogText(group, "Vertically")
        borders = (5, 0, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        text = "Reset"
        tooltip_text = "Clear background and set default values"
        btn = DialogButton(self, text, "", tooltip_text, self.__reset)
        borders = (0, 0, 0, 20)
        client_sizer.add(btn, alignment="center_h", borders=borders)

        subsizer = Sizer("horizontal")
        borders = (20, 20, 20, 20)
        client_sizer.add(subsizer, expand=True, borders=borders)

        text = DialogText(self, "Apply to view:")
        borders = (0, 5, 0, 0)
        subsizer.add(text, alignment="center_v", borders=borders)

        combobox = DialogComboBox(self, 150, tooltip_text="View")
        self._combobox = combobox
        subsizer.add(combobox, proportion=1., alignment="center_v")

        def get_command(view_id):

            def set_view():

                self._combobox.select_item(view_id)
                self.__handle_value("view", view_id)

            return set_view

        for view_id in ("front", "back", "left", "right", "bottom", "top", "all"):
            combobox.add_item(view_id, view_id, get_command(view_id))

        combobox.update_popup_menu()
        view_id = data["view"]
        combobox.select_item(view_id)

        self.finalize()

    def close(self, answer=""):

        self._checkboxes = None
        self._fields = None

        Dialog.close(self, answer)

    def __reset(self):

        fields = self._fields
        fields["filename"].set_value("filename", "")
        fields["filename"].set_text("filename", "<None>")
        fields["alpha"].set_value("alpha", 1.)
        fields["x"].set_value("x", 0.)
        fields["y"].set_value("y", 0.)
        fields["width"].set_value("width", 1.)
        fields["height"].set_value("height", 1.)
        checkboxes = self._checkboxes
        checkboxes["show"].check()
        checkboxes["in_foreground"].check(False)
        checkboxes["fixed_aspect_ratio"].check()
        checkboxes["flip_h"].check(False)
        checkboxes["flip_v"].check(False)
        data = self._data
        data["filename"] = ""
        data["show"] = True
        data["in_foreground"] = False
        data["alpha"] = 1.
        data["x"] = 0.
        data["y"] = 0.
        data["width"] = 1.
        data["height"] = 1.
        data["fixed_aspect_ratio"] = True
        data["bitmap_aspect_ratio"] = 1.
        data["flip_h"] = False
        data["flip_v"] = False

    def __load_image(self):

        def load(filename):

            config_data = GlobalData["config"]
            texfile_paths = config_data["texfile_paths"]
            path = os.path.dirname(filename)

            if path not in texfile_paths:
                texfile_paths.append(path)

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

            data = self._data
            self._fields["filename"].set_value("filename", filename)
            data["filename"] = filename
            img = PNMImage()
            img.read(Filename.from_os_specific(filename))
            ratio = img.get_y_size() / img.get_x_size()
            data["bitmap_aspect_ratio"] = ratio

            if data["fixed_aspect_ratio"]:
                width = data["width"]
                height = width * ratio
                self._fields["height"].set_value("height", height)
                data["height"] = height

        file_types = ("Bitmap files|bmp;jpg;png", "All types|*")

        FileDialog(title="Load background image",
                   ok_alias="Load",
                   on_yes=load,
                   file_op="read",
                   file_types=file_types)

    def __init_filename_input(self):

        field = self._fields["filename"]
        filename = self._data["filename"]

        if filename:
            field.set_input_text(filename)
        else:
            field.clear(forget=False)

    def __check_filename(self, filename):

        return filename if (not filename or os.path.exists(filename)) else None

    def __parse_filename(self, filename):

        if filename:

            img = PNMImage()
            img.read(Filename.from_os_specific(filename))
            ratio = img.get_y_size() / img.get_x_size()
            self._data["bitmap_aspect_ratio"] = ratio

            if self._data["fixed_aspect_ratio"]:
                width = self._data["width"]
                height = width * ratio
                self._fields["height"].set_value("height", height)
                self._data["height"] = height

        return os.path.basename(filename) if filename else "<None>"

    def __parse_alpha(self, alpha):

        try:
            return min(1., max(0., abs(float(eval(alpha)))))
        except:
            return None

    def __parse_size(self, size):

        try:
            return max(.001, abs(float(eval(size))))
        except:
            return None

    def __handle_value(self, value_id, value):

        data = self._data

        if value_id == "fixed_aspect_ratio" and value:

            ratio = data["bitmap_aspect_ratio"]
            width = data["width"]
            height = width * ratio
            self._fields["height"].set_value("height", height)
            data["height"] = height

        elif data["fixed_aspect_ratio"]:

            ratio = data["bitmap_aspect_ratio"]

            if value_id == "width":
                height = value * ratio
                self._fields["height"].set_value("height", height)
                data["height"] = height
            elif value_id == "height":
                width = value / ratio
                self._fields["width"].set_value("width", width)
                data["width"] = width

        data[value_id] = value

    def __on_yes(self):

        Mgr.update_remotely("view", "background", self._data)


def _request_view_name(command, default_name=None):

    name = "New" if default_name is None else default_name
    InputDialog(title="Name user view",
                message="Please enter a name for this user view:",
                default_input=name,
                choices="okcancel", on_yes=command)

def _init_snapshot():

    def command(name):

        Mgr.update_remotely("view", "take_snapshot", name)

    _request_view_name(command)


class ViewManager(object):

    def __init__(self, menubar):

        self._main_menu = main_menu = menubar.add_menu("view", "View")
        item = main_menu.add("std_views", "Standard views", item_type="submenu")
        self._std_view_menu = menu = item.get_submenu()

        view_ids = ("persp", "ortho", "back", "front", "left", "right", "top")
        names = ("Perspective", "Orthographic", "Back", "Front", "Left", "Right", "Top")
        accelerators = ("p", "o", "b", "f", "l", "r", "t")
        mod_key_codes = GlobalData["mod_key_codes"]
        mod_code = mod_key_codes["shift"]
        hotkeys = [(accel, mod_code) for accel in accelerators]

        get_command = lambda view_id: lambda: Mgr.update_app("view", "set", view_id)

        for view_id, name, accel, hotkey in zip(view_ids, names, accelerators, hotkeys):
            menu.add(view_id, name, get_command(view_id), item_type="radio")
            menu.set_item_hotkey(view_id, hotkey, "Shift+{}".format(accel.upper()))

        mod_code = mod_key_codes["shift"] | mod_key_codes["alt"]
        hotkey = ("b", mod_code)
        menu.add("bottom", "Bottom", get_command("bottom"), item_type="radio", index=6)
        menu.check_radio_item("persp")
        menu.set_item_hotkey("bottom", hotkey, "Shift+Alt+B")
        item = main_menu.add("user_views", "User views", item_type="submenu")
        self._user_view_menu = menu = item.get_submenu()
        item = menu.add("edit_user_views", "Edit", item_type="submenu")
        submenu = item.get_submenu()
        menu.add("sep0", item_type="separator")
        submenu.add("copy_persp", "Create as persp. copy",
                    lambda: Mgr.update_remotely("view", "init_copy", "persp"))
        submenu.add("copy_ortho", "Create as orthogr. copy",
                    lambda: Mgr.update_remotely("view", "init_copy", "ortho"))
        mod_code = mod_key_codes["shift"]
        hotkey = ("u", mod_code)
        submenu.add("snapshot", "Create as snapshot", _init_snapshot)
        submenu.set_item_hotkey("snapshot", hotkey, "Shift+U")
        submenu.add("sep0", item_type="separator")
        submenu.add("toggle_lens_type", "Toggle lens type",
                    lambda: Mgr.update_locally("view", "toggle_lens_type"))
        submenu.add("sep1", item_type="separator")
        hotkey = ("f2", mod_code)
        submenu.add("rename", "Rename", lambda: Mgr.update_remotely("view", "init_rename"))
        submenu.set_item_hotkey("rename", hotkey, "Shift+F2")
        submenu.add("sep2", item_type="separator")
        hotkey = ("delete", mod_code)
        submenu.add("remove", "Remove", lambda: Mgr.update_remotely("view", "init_remove"))
        submenu.set_item_hotkey("remove", hotkey, "Shift+Del")
        submenu.add("clear", "Remove all", lambda: Mgr.update_remotely("view", "init_clear"))
        main_menu.add("sep0", item_type="separator")

        def command():

            task = lambda: BackgroundDialog()
            PendingTasks.add(task, "show_background_dialog")

        main_menu.add("background_image", "Background image...", command)

        def command():

            Mgr.update_remotely("view", "reset_backgrounds")
            GlobalData.reset("view_backgrounds")

        main_menu.add("clear_bg_images", "Clear all backgr. images", command)
        main_menu.add("sep1", item_type="separator")

        def command():

            task = lambda: Mgr.update_remotely("view", "center")
            PendingTasks.add(task, "center_obj_in_view")

        main_menu.add("obj_center", "Center on objects", command)
        hotkey = ("c", 0)
        main_menu.set_item_hotkey("obj_center", hotkey, "C")
        item = main_menu.add("obj_align", "Align to object...",
                             lambda: Mgr.update_remotely("view", "obj_align"))
        disabler = lambda: "uv" in (GlobalData["viewport"][1], GlobalData["viewport"][2])
        item.add_disabler("uv_edit", disabler)
        main_menu.add("sep2", item_type="separator")

        def command():

            task = lambda: Mgr.update_remotely("view", "reset", False, True)
            PendingTasks.add(task, "home")

        main_menu.add("home", "Home", command)
        hotkey = ("home", 0)
        main_menu.set_item_hotkey("home", hotkey, "Home")
        main_menu.add("set_home", "Set current as Home",
                      lambda: Mgr.update_remotely("view", "set_as_home"))
        main_menu.add("reset_home", "Reset Home",
                      lambda: Mgr.update_remotely("view", "reset_home"))
        main_menu.add("sep3", item_type="separator")
        main_menu.add("set_front", "Set current as Front",
                      lambda: Mgr.update_remotely("view", "set_as_front"))

        def command():

            task = lambda: Mgr.update_remotely("view", "reset_front")
            PendingTasks.add(task, "reset_front_view")

        main_menu.add("reset_front", "Reset Front", command)
        main_menu.add("sep4", item_type="separator")

        def command():

            task = lambda: Mgr.update_remotely("view", "reset", True, True)
            PendingTasks.add(task, "reset_view")

        main_menu.add("reset", "Reset", command)
        main_menu.add("reset_all", "Reset all", lambda: Mgr.update_remotely("view", "reset_all"))

        Mgr.add_app_updater("view", self.__update_view)

        ViewTileManager()

    def setup(self):

        def enter_obj_picking_mode(prev_state_id, is_active):

            Mgr.do("set_viewport_border_color", "viewport_frame_pick_objects")
            Mgr.do("enable_gui")

        add_state = Mgr.add_state
        add_state("view_obj_picking_mode", -75, enter_obj_picking_mode)

    def __set_view(self, view_id):

        view_ids = ("persp", "ortho", "back", "front", "left", "right", "bottom", "top")

        if view_id in view_ids:
            self._std_view_menu.check_radio_item(view_id)
            self._user_view_menu.clear_radio_check()
        else:
            self._user_view_menu.check_radio_item(view_id)
            self._std_view_menu.clear_radio_check()

    def __add_user_view(self, view_id, view_name):

        name = view_name.replace("User ", "", 1)
        name = name.replace("ortho - " if name.startswith("o") else "persp - ", "", 1)
        get_handler = lambda view_id: lambda: Mgr.update_app("view", "set", view_id)
        menu = self._user_view_menu
        menu.add(view_id, name, get_handler(view_id), item_type="radio", update=True)
        menu.check_radio_item(view_id)
        self._std_view_menu.clear_radio_check()

    def __confirm_remove_user_view(self, view_id, view_name):

        msg = "You have chosen to remove the following user view:\n\n" + view_name
        msg += "\n\nAre you sure?"
        command = lambda: Mgr.update_app("view", "remove", view_id)
        MessageDialog(title="Confirm user view removal",
                      message=msg,
                      choices="yesno", on_yes=command,
                      icon_id="icon_exclamation")

    def __remove_user_view(self, view_id):

        self._user_view_menu.remove(view_id, update=True, destroy=True)
        Mgr.update_locally("view", "set", "persp")

    def __confirm_clear_user_views(self, view_count):

        if view_count > 1:
            msg = "Are you sure you want to remove all {:d} user views?".format(view_count)
        else:
            msg = "Are you sure you want to remove the user view?"

        command = lambda: Mgr.update_app("view", "clear")
        MessageDialog(title="Confirm user view removal",
                      message=msg,
                      choices="yesno", on_yes=command,
                      icon_id="icon_exclamation")

    def __clear_user_views(self):

        menu = self._user_view_menu

        for item in list(menu.get_items().values()):

            if item.get_widget_type() == "menu_separator":
                continue

            item_id = item.get_id()

            if item_id != "edit_user_views":
                menu.remove(item_id, update=False, destroy=True)

        menu.update()
        view_ids = ("persp", "ortho", "back", "front", "left", "right", "bottom", "top")

        if GlobalData["view"] not in view_ids:
            Mgr.update_locally("view", "set", "persp")

    def __request_view_copy_name(self, lens_type, proposed_name):

        def command(name):

            Mgr.update_remotely("view", "copy", lens_type, name)

        _request_view_name(command, proposed_name)

    def __request_new_view_name(self, current_name):

        def command(name):

            if name != current_name:
                Mgr.update_remotely("view", "rename", name)

        _request_view_name(command, current_name)

    def __rename_user_view(self, lens_type, view_id, view_name):

        self._user_view_menu.set_item_text(view_id, view_name, update=True)

    def __update_view(self, update_type, *args):

        if update_type == "set":
            self.__set_view(*args)
        elif update_type == "add":
            self.__add_user_view(*args)
        elif update_type == "confirm_remove":
            self.__confirm_remove_user_view(*args)
        elif update_type == "remove":
            self.__remove_user_view(*args)
        elif update_type == "confirm_clear":
            self.__confirm_clear_user_views(*args)
        elif update_type == "clear":
            self.__clear_user_views(*args)
        elif update_type == "request_copy_name":
            self.__request_view_copy_name(*args)
        elif update_type == "request_new_name":
            self.__request_new_view_name(*args)
        elif update_type == "rename":
            self.__rename_user_view(*args)
        elif update_type == "enable_obj_align":
            self._main_menu.enable_item("obj_align", *args)


class ViewTileCard(WidgetCard):

    def __init__(self, parent):

        WidgetCard.__init__(self, "view_tile_card", parent, stretch_dir="both")

        self.set_sizer(Sizer("vertical"))

    def get_sort(self):

        return 1

    def update_images(self):

        sizer = self.get_sizer()
        self.get_sizer().update_images()
        w, h = self.get_size()
        l = 0
        r = w
        b = -h
        t = 0
        quad = self.create_quad((l, r, b, t))
        x, y = self.get_pos(from_root=True)
        quad.set_pos(x, 0, -y)
        quad.set_transparency(TransparencyAttrib.M_alpha)

        img = PNMImage(w, h, 4)
        x, y = self.get_pos()

        for widget in sizer.get_widgets(include_children=False):

            x_w, y_w = widget.get_pos(from_root=True)
            x_w -= x
            y_w -= y
            widget_img = widget.get_image()

            if widget_img:
                img.copy_sub_image(widget_img, x_w, y_w, 0, 0)

        tex = self._tex
        tex.load(img)
        quad.set_texture(tex)
        self._image = img


class ViewTileButton(Button):

    _gfx = {
        "normal": (("viewtile_button_normal",),),
        "hilited": (("viewtile_button_hilited",),),
        "pressed": (("viewtile_button_pressed",),),
        "active": (("viewtile_button_active",),)
    }

    def __init__(self, parent):

        command = lambda: self.set_active(Mgr.do("toggle_view_tiles"))

        Button.__init__(self, parent, self._gfx, "", "", "Toggle view tiles", command,
                        button_type="view_tile_button", stretch_dir="")

        self._menu = main_menu = Menu()
        item = main_menu.add("std_views", "Standard views", item_type="submenu")
        self._std_view_menu = menu = item.get_submenu()

        view_ids = ("persp", "ortho", "back", "front", "left", "right", "bottom", "top")
        names = ("Perspective", "Orthographic", "Back", "Front", "Left", "Right", "Bottom", "Top")

        get_command = lambda view_id: lambda: Mgr.update_app("view", "set", view_id)

        for view_id, name in zip(view_ids, names):
            menu.add(view_id, name, get_command(view_id), item_type="radio")

        menu.check_radio_item("persp")
        item = main_menu.add("user_views", "User views", item_type="submenu")
        self._user_view_menu = menu = item.get_submenu()
        main_menu.update()

        Mgr.add_app_updater("view", self.__update_view)

    def __set_view(self, view_id):

        view_ids = ("persp", "ortho", "back", "front", "left", "right", "bottom", "top")

        if view_id in view_ids:
            self._std_view_menu.check_radio_item(view_id)
            self._user_view_menu.clear_radio_check()
        else:
            self._user_view_menu.check_radio_item(view_id)
            self._std_view_menu.clear_radio_check()

    def __add_user_view(self, view_id, view_name):

        name = view_name.replace("User ", "", 1)
        name = name.replace("ortho - " if name.startswith("o") else "persp - ", "", 1)
        get_handler = lambda view_id: lambda: Mgr.update_app("view", "set", view_id)
        menu = self._user_view_menu
        menu.add(view_id, name, get_handler(view_id), item_type="radio", update=True)
        menu.check_radio_item(view_id)
        self._std_view_menu.clear_radio_check()

    def __remove_user_view(self, view_id):

        self._user_view_menu.remove(view_id, update=True, destroy=True)

    def __clear_user_views(self):

        menu = self._user_view_menu

        for item in list(menu.get_items().values()):
            item_id = item.get_id()
            menu.remove(item_id, update=False, destroy=True)

        menu.update()

    def __update_view(self, update_type, *args):

        if update_type == "set":
            self.__set_view(*args)
        elif update_type == "add":
            self.__add_user_view(*args)
        elif update_type == "remove":
            self.__remove_user_view(*args)
        elif update_type == "clear":
            self.__clear_user_views(*args)

    def on_enter(self):

        Button.on_enter(self)

        Mgr.do("restore_active_view")
        Mgr.enter_state("suppressed")

    def on_leave(self):

        if not Button.on_leave(self):
            return

        if not (Menu.is_menu_shown() or Dialog.get_dialogs()):
            Mgr.exit_state("suppressed")

    def on_right_up(self):

        Mgr.exit_state("suppressed")
        self._menu.show_at_mouse_pos()


class ViewLabel(Text):

    def __init__(self, parent, text):

        skin_text = Skin["text"]["view_label"]
        Text.__init__(self, parent, skin_text["font"], skin_text["color"], text)

        self.set_widget_type("view_label")

    def post_process_image(self, image):

        color = Skin["colors"]["view_label_shadow"]
        text_img = self.get_font().create_image(self.get_text(), color)
        offset_x = Skin["options"]["view_label_shadow_offset_x"]
        offset_y = Skin["options"]["view_label_shadow_offset_y"]
        d_w = 1 + max(1, abs(offset_x))
        d_h = 1 + max(1, abs(offset_y))
        img = PNMImage(text_img.get_x_size() + d_w, text_img.get_y_size() + d_h, 4)
        img.copy_sub_image(text_img, max(1, offset_x), max(1, offset_y), 0, 0)
        img.gaussian_filter(1.)
        img.blend_sub_image(image, max(0, 1 - offset_x), max(0, 1 - offset_y), 0, 0)

        return img

    def use_main_text_attribs(self, main=True):

        skin_text = Skin["text"]["view_label" if main else "view_label_hilited"]
        self.set_font(skin_text["font"])
        self.set_color(skin_text["color"])


class ViewTile(Button):

    _gfx = {
        "normal": (("viewtile_normal",),),
        "hilited": (("viewtile_hilited",),),
        "pressed": (("viewtile_pressed",),),
        "active": (("viewtile_active",),)
    }

    def __init__(self, parent, view_type, view_id, view_name, text):

        command = lambda: Mgr.update_app("view", "set", view_id)

        Button.__init__(self, parent, self._gfx, text, "", "", command, button_type="view_tile")

        self._view_type = view_type
        self._view_id = view_id
        self._view_name = view_name
        self.get_node().reparent_to(parent.get_widget_root_node())

    def get_view_type(self):

        return self._view_type

    def set_view_name(self, view_name):

        self._view_name = view_name

    def get_view_name(self):

        return self._view_name

    def on_enter(self):

        Button.on_enter(self)

        Mgr.remove_task("check_view")
        Mgr.do("check_view", self._view_id)

    def on_leave(self):

        if not Button.on_leave(self):
            return

        Mgr.remove_task("check_view")
        Mgr.do("check_view", None)

    def on_right_up(self):

        self.press()

        Mgr.exit_state("suppressed")
        Mgr.do("popup_view_menu", self._view_type)


class ViewScrollThumb(ScrollThumb):

    def __init__(self, *args, **kwargs):

        ScrollThumb.__init__(self, *args, **kwargs)

        self._has_mouse = False

    def on_enter(self):

        ScrollThumb.on_enter(self)

        self._has_mouse = True
        Mgr.do("restore_active_view")
        Mgr.enter_state("suppressed")

    def on_leave(self):

        ScrollThumb.on_leave(self)

        if not self._has_mouse:
            return False

        self._has_mouse = False
        Mgr.exit_state("suppressed")


class ViewScrollBar(ScrollBar):

    def __init__(self, *args, **kwargs):

        ScrollBar.__init__(self, *args, **kwargs)

        self._has_mouse = False

    def _create_thumb(self, pane, thumb_gfx_data, cull_bin, scroll_dir, inner_border_id):

        return ViewScrollThumb(self, pane, thumb_gfx_data, cull_bin, scroll_dir, inner_border_id)

    def on_enter(self):

        ScrollBar.on_enter(self)

        self._has_mouse = True
        Mgr.do("restore_active_view")
        Mgr.enter_state("suppressed")

    def on_leave(self):

        ScrollBar.on_leave(self)

        if not self._has_mouse:
            return False

        self._has_mouse = False
        Mgr.exit_state("suppressed")


class ViewPaneFrame(ScrollPaneFrame):

    def _create_bar(self, pane, bar_gfx_data, thumb_gfx_data, cull_bin, scroll_dir, inner_border_id):

        return ViewScrollBar(self, pane, bar_gfx_data, thumb_gfx_data, cull_bin, scroll_dir,
                             inner_border_id)


class ViewPane(ScrollPane):

    def __init__(self, card):

        pane_id = "viewtile_pane"
        scroll_dir = "vertical"
        cull_bin = "gui"
        frame_gfx_data = {}
        bar_gfx_data = {}
        thumb_gfx_data = {
            "normal": (
                ("viewtile_scrollthumb_normal_topleft", "viewtile_scrollthumb_normal_top",
                 "viewtile_scrollthumb_normal_topright"),
                ("viewtile_scrollthumb_normal_left", "viewtile_scrollthumb_normal_center",
                 "viewtile_scrollthumb_normal_right"),
                ("viewtile_scrollthumb_normal_bottomleft", "viewtile_scrollthumb_normal_bottom",
                 "viewtile_scrollthumb_normal_bottomright")
            ),
            "hilited": (
                ("viewtile_scrollthumb_hilited_topleft", "viewtile_scrollthumb_hilited_top",
                 "viewtile_scrollthumb_hilited_topright"),
                ("viewtile_scrollthumb_hilited_left", "viewtile_scrollthumb_hilited_center",
                 "viewtile_scrollthumb_hilited_right"),
                ("viewtile_scrollthumb_hilited_bottomleft", "viewtile_scrollthumb_hilited_bottom",
                 "viewtile_scrollthumb_hilited_bottomright")
            )
        }
        bar_inner_border_id = "viewtile_scrollbar"
        ScrollPane.__init__(self, card, pane_id, scroll_dir, cull_bin, frame_gfx_data, bar_gfx_data,
             thumb_gfx_data, bar_inner_border_id, frame_has_mouse_region=False, append_scrollbar=False)

        self.get_sizer().ignore_stretch()
        self._tile_sizers = tile_sizers = {}
        sizer = GridSizer(columns=2)
        tile_sizers["std"] = sizer
        borders = (5, 5, 5, 5)
        self.get_sizer().add(sizer, borders=borders)
        sizer = GridSizer(columns=2)
        tile_sizers["user"] = sizer
        borders = (5, 5, 5, 0)
        self.get_sizer().add(sizer, borders=borders)
        self.set_transparent()
        task = self.setup
        task_id = "setup"
        PendingTasks.add(task, task_id)
        self._tiles = []

        # the following mask is added to the mouse watcher of the ViewPane, to prevent the
        # mouse from interacting with the view tiles where they overlap with the auxiliary
        # viewport
        self._mouse_region_mask = mask = MouseWatcherRegion("aux_vp_mask_viewtile_pane", 0., 0., 0., 0.)
        flags = MouseWatcherRegion.SF_mouse_button | MouseWatcherRegion.SF_mouse_position
        mask.set_suppress_flags(flags)
        mask.set_sort(10)
        self.get_mouse_watcher().add_region(mask)

    def _create_frame(self, parent, scroll_dir, cull_bin, gfx_data, bar_gfx_data,
            thumb_gfx_data, bar_inner_border_id, has_mouse_region=True):

        return ViewPaneFrame(parent, self, gfx_data, bar_gfx_data, thumb_gfx_data,
                             cull_bin, scroll_dir, bar_inner_border_id, has_mouse_region)

    def _copy_widget_images(self, pane_image): 

        root_node = self.get_widget_root_node()

        for tile in self._tiles:
            x, y = tile.get_pos(ref_node=root_node)
            offset_x, offset_y = tile.get_image_offset()
            pane_image.copy_sub_image(tile.get_image(), x + offset_x, y + offset_y, 0, 0)

    def _can_scroll(self):

        if (self.get_mouse_watcher().get_over_region() is None
                or Dialog.get_dialogs() or Mgr.get("active_input_field")
                or Menu.is_menu_shown() or not Mgr.get("gui_enabled")):
            return False

        return True

    def _finalize_mouse_watcher_frame_update(self):

        viewport_id = GlobalData["viewport"][2]

        if viewport_id == "main":
            self._mouse_region_mask.set_active(False)
        else:
            x, y, w, h = GlobalData["viewport"]["aux_region"]
            x_offset, y_offset = self.get_pos(from_root=True)
            x -= x_offset
            y -= y_offset - self.get_scrollthumb().get_offset()
            self._mouse_region_mask.set_frame(x, x + w, -y - h, -y)
            self._mouse_region_mask.set_active(True)

    def add_tile(self, tile):

        self._tiles.append(tile)
        self._tile_sizers[tile.get_view_type()].add(tile)
        self.reset_sub_image_index()

    def remove_tile(self, tile):

        self._tiles.remove(tile)
        self._tile_sizers["user"].remove(tile, destroy=True)
        self.reset_sub_image_index()

    def clear_tiles(self):

        del self._tiles[8:]
        self._tile_sizers["user"].clear(destroy_items=True)
        self.reset_sub_image_index()


class ViewTileManager(object):

    def __init__(self):

        self._card = card = ViewTileCard(Mgr.get("window"))
        self._sizer = sizer = Sizer("horizontal")
        sizer.add(card, proportion=1., expand=True)
        self._pane = pane = ViewPane(card)
        card_sizer = card.get_sizer()
        subsizer = Sizer("horizontal")
        card_sizer.add(subsizer)
        btn = ViewTileButton(card)
        borders = (5, 5, 5, 5)
        subsizer.add(btn, borders=borders)
        self._view_label = view_label = ViewLabel(card, "Perspective")
        subsizer.add(view_label, alignment="center_v")
        card_sizer.add(pane.get_frame(), proportion=1.)
        self._space_item = card_sizer.add((0, 20))
        self._view_tiles = {}
        self._user_view_ids = []
        self._view_tile_regions = []
        self._view_tiles_shown = True
        self._active_view_id = "persp"
        self._mouse_prev = None

        # the following mask is added to the main GUI mouse watcher, to prevent the mouse from
        # interacting with the view tile card where it overlaps with the auxiliary viewport
        self._mouse_region_mask = mask = MouseWatcherRegion("aux_vp_mask_viewtile_card", 0., 0., 0., 0.)
        flags = MouseWatcherRegion.SF_mouse_button | MouseWatcherRegion.SF_mouse_position
        mask.set_suppress_flags(flags)
        mask.set_sort(10)
        Mgr.get("mouse_watcher").add_region(mask)

        root = Mgr.get("base").pixel2d
        self._scrollthumb_offset_node = node = root.attach_new_node("scrollthumb_offset")
        pane.get_scrollthumb().get_quad().reparent_to(node)

        menu_std = Menu()
        menu_user = Menu()
        self._popup_menus = {"std": menu_std, "user": menu_user}

        for menu in (menu_std, menu_user):
            command = lambda: Mgr.update_remotely("view", "init_copy", "persp")
            menu.add("copy_to_persp", "Copy to persp. view", command)
            command = lambda: Mgr.update_remotely("view", "init_copy", "ortho")
            menu.add("copy_to_ortho", "Copy to orthogr. view", command)
            menu.add("snapshot", "Take snapshot", _init_snapshot)
            menu.set_item_hotkey("snapshot", None, "Shift+U")

        menu_user.add("sep0", item_type="separator")
        menu_user.add("toggle_lens_type", "Toggle lens type", self.__toggle_lens_type)
        menu_user.add("sep1", item_type="separator")
        command = lambda: Mgr.update_remotely("view", "init_rename")
        menu_user.add("rename", "Rename", command)
        menu_user.set_item_hotkey("rename", None, "Shift+F2")
        command = lambda: Mgr.update_remotely("view", "init_remove")
        menu_user.add("remove", "Remove", command)
        menu_user.set_item_hotkey("remove", None, "Shift+Del")

        menu_std.update()
        menu_user.update()

        self.__create_view_tiles()
        PendingTasks.add(self.__toggle_view_tiles, "hide_view_tiles")

        Mgr.accept("toggle_view_tiles", self.__toggle_view_tiles)
        Mgr.accept("check_view", self.__start_view_check)
        Mgr.accept("restore_active_view", self.__restore_active_view)
        Mgr.accept("popup_view_menu", self.__popup_menu)
        Mgr.add_app_updater("viewport", self.__update_sizer)
        Mgr.add_app_updater("view", self.__update_view)

    def __create_view_tiles(self):

        tiles = self._view_tiles
        regions = self._view_tile_regions
        pane = self._pane
        view_ids = ("persp", "ortho", "back", "front", "left", "right", "bottom", "top")
        names = ("Perspective", "Orthographic", "Back", "Front", "Left", "Right", "Bottom", "Top")
        texts = ["P", "O", "Bk", "F", "L", "R", "B", "T"]

        for view_id, view_name, text in zip(view_ids, names, texts):
            tile = ViewTile(pane, "std", view_id, view_name, text)
            pane.add_tile(tile)
            tiles[view_id] = tile
            region = tile.get_mouse_region()
            regions.append(region)

        tiles["persp"].set_active()

        def task():

            self.__update_sizer()
            sizer = pane.get_sizer()
            sizer.lock_item_size()
            sizer.lock_mouse_regions()

        PendingTasks.add(task, "lock_tiles")

    def __toggle_view_tiles(self):

        tiles = self._view_tiles
        regions = self._view_tile_regions
        pane = self._pane
        pane_mouse_watcher = pane.get_mouse_watcher()
        gui_mouse_watcher = Mgr.get("mouse_watcher")
        scrollthumb = pane.get_scrollthumb()
        scrollbar = scrollthumb.get_parent()
        self._view_tiles_shown = shown = not self._view_tiles_shown

        if shown:

            pane.get_quad().show()
            scrollthumb.get_quad().show()
            gui_mouse_watcher.add_region(scrollbar.get_mouse_region())
            gui_mouse_watcher.add_region(scrollthumb.get_mouse_region())

            for region in regions:
                pane_mouse_watcher.add_region(region)

        else:

            pane.get_quad().hide()
            scrollthumb.get_quad().hide()
            gui_mouse_watcher.remove_region(scrollbar.get_mouse_region())
            gui_mouse_watcher.remove_region(scrollthumb.get_mouse_region())

            for region in regions:
                pane_mouse_watcher.remove_region(region)

        return shown

    def __set_view_name(self, name):

        view_label = self._view_label
        width, height = view_label.get_size()
        img = PNMImage(width, height, 4)
        self._card.copy_sub_image(view_label, img, width, height)
        view_label.set_text(name, force=True)
        img = view_label.get_image()
        width, height = view_label.get_size()
        self._card.copy_sub_image(view_label, img, width, height)

    def __set_active_view(self, view_id):

        if self._active_view_id == view_id:
            return

        if self._active_view_id in self._view_tiles:
            self._view_tiles[self._active_view_id].set_active(False)

        self._active_view_id = view_id
        tile = self._view_tiles[view_id]
        tile.set_active()
        self.__set_view_name(tile.get_view_name())

    def __check_view(self, view_id, task):

        if view_id is None:

            if not (Menu.is_menu_shown() or Dialog.get_dialogs()):
                Mgr.exit_state("suppressed")

            self._view_label.use_main_text_attribs()
            tile = self._view_tiles[self._active_view_id]
            self.__set_view_name(tile.get_view_name())
            Mgr.update_remotely("view", "set", self._active_view_id)

            return

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        pos = (mouse_pointer.get_x(), mouse_pointer.get_y())

        if pos == self._mouse_prev:
            self._view_label.use_main_text_attribs(False)
            tile = self._view_tiles[view_id]
            self.__set_view_name(tile.get_view_name())
            Mgr.update_remotely("view", "preview", view_id)
            self._mouse_prev = None
            return

        self._mouse_prev = pos

        return task.again

    def __start_view_check(self, view_id=None):

        Mgr.enter_state("suppressed")
        Mgr.add_task(.1, self.__check_view, "check_view", extraArgs=[view_id], appendTask=True)

    def __restore_active_view(self):

        Mgr.remove_task("check_view")
        self._view_label.use_main_text_attribs()
        tile = self._view_tiles[self._active_view_id]
        self.__set_view_name(tile.get_view_name())
        Mgr.update_remotely("view", "set", self._active_view_id)

    def __update_sizer(self):

        viewport_id = GlobalData["viewport"][2]
        x, y = pos = GlobalData["viewport"]["pos_aux" if viewport_id == "main" else "pos"]
        w, h = GlobalData["viewport"]["size_aux" if viewport_id == "main" else "size"]
        sizer = self._sizer
        h_min = sizer.update_min_size()[1]
        size = (w, min(h, h_min + self._pane.get_sizer().get_virtual_size()[1]))
        sizer.set_size(size)
        sizer.calculate_positions(pos)
        sizer.update_images()
        sizer.update_mouse_region_frames()
        root = Mgr.get("base").pixel2d
        quad = self._card.get_quad()
        quad.reparent_to(root)
        quad.set_pos(quad, -x, 0., y)
        quad = self._pane.get_quad()
        quad.reparent_to(root)
        quad.set_pos(quad, -x, 0., y)

        if not self._view_tiles_shown:
            quad.hide()

        self._scrollthumb_offset_node.set_pos(-x, 0., y)

        if viewport_id in (None, "main"):
            self._mouse_region_mask.set_active(False)
        else:
            x, y, w, h = GlobalData["viewport"]["aux_region"]
            self._mouse_region_mask.set_frame(x, x + w, -y - h, -y)
            self._mouse_region_mask.set_active(True)

    def __add_user_view(self, view_id, view_name):

        pane = self._pane
        tile = ViewTile(pane, "user", view_id, view_name, "U"+"{:02d}".format(int(view_id))[-2:])
        pane.add_tile(tile)
        self._view_tiles[view_id] = tile
        self._user_view_ids.append(view_id)
        region = tile.get_mouse_region()
        self._view_tile_regions.append(region)
        self.__set_active_view(view_id)
        sizer = pane.get_sizer()
        sizer.lock_item_size(False)
        sizer.lock_mouse_regions(False)
        self.__update_sizer()
        sizer.lock_item_size()
        sizer.lock_mouse_regions()

        if not self._view_tiles_shown:
            pane.get_mouse_watcher().remove_region(region)

    def __remove_user_view(self, view_id):

        tile = self._view_tiles[view_id]
        del self._view_tiles[view_id]
        self._user_view_ids.remove(view_id)
        region = tile.get_mouse_region()
        self._view_tile_regions.remove(region)
        self._pane.remove_tile(tile)
        sizer = self._pane.get_sizer()
        sizer.lock_item_size(False)
        sizer.lock_mouse_regions(False)
        self.__update_sizer()
        sizer.lock_item_size()
        sizer.lock_mouse_regions()

    def __clear_user_views(self):

        for view_id in self._user_view_ids:
            tile = self._view_tiles[view_id]
            region = tile.get_mouse_region()
            self._view_tile_regions.remove(region)
            del self._view_tiles[view_id]

        self._user_view_ids = []
        self._pane.clear_tiles()
        sizer = self._pane.get_sizer()
        sizer.lock_item_size(False)
        sizer.lock_mouse_regions(False)
        self.__update_sizer()
        sizer.lock_item_size()
        sizer.lock_mouse_regions()

    def __rename_user_view(self, lens_type, view_id, view_name):

        name = "User {} - {}".format(lens_type, view_name)
        self._view_tiles[view_id].set_view_name(name)
        self.__set_view_name(name)

    def __toggle_lens_type(self):

        tile = self._view_tiles[self._active_view_id]
        name = tile.get_view_name()

        if name.startswith("User persp"):
            name = name.replace("persp", "ortho", 1)
        elif name.startswith("User ortho"):
            name = name.replace("ortho", "persp", 1)

        tile.set_view_name(name)
        self.__set_view_name(name)
        Mgr.update_remotely("view", "toggle_lens_type")

    def __update_view(self, update_type, *args):

        if update_type == "set":
            self.__set_active_view(*args)
        elif update_type == "add":
            self.__add_user_view(*args)
        elif update_type == "remove":
            self.__remove_user_view(*args)
        elif update_type == "clear":
            self.__clear_user_views(*args)
        elif update_type == "rename":
            self.__rename_user_view(*args)
        elif update_type == "toggle_lens_type":
            self.__toggle_lens_type(*args)

    def __popup_menu(self, menu_id):

        menu = self._popup_menus[menu_id]
        menu.show_at_mouse_pos()
