from ..dialog import *
from ..dialogs import *


class ViewBackgroundDialog(Dialog):

    def __init__(self):

        extra_button_data = (("Apply", "", self.__on_yes, None, 1.),)

        Dialog.__init__(self, "View background", "okcancel", on_yes=self.__on_yes,
                        extra_button_data=extra_button_data)

        widgets = Skin.layout.create(self, "view_background")
        btns = widgets["buttons"]
        self._checkbuttons = checkbtns = widgets["checkbuttons"]
        self._fields = fields = widgets["fields"]
        comboboxes = widgets["comboboxes"]

        self._data = data = {}
        current_view_id = GD["view"]
        view_ids = ("front", "back", "left", "right", "bottom", "top")
        view_id = current_view_id if current_view_id in view_ids else "front"
        data.update(GD["view_backgrounds"][view_id])
        data["view"] = view_id

        btn = btns["load"]
        btn.command = self.__load_image

        val_id = "filename"
        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "string"
        field.set_value_handler(self.__handle_value)
        filename = data[val_id]
        field.set_text(os.path.basename(filename) if filename else "<None>")
        field.set_input_init(self.__init_filename_input)
        field.set_input_parser(self.__check_filename)
        field.set_value_parser(self.__parse_filename)

        for val_id in ("show", "in_foreground", "fixed_aspect_ratio", "flip_h", "flip_v"):
            checkbtn = checkbtns[val_id]
            checkbtn.command = lambda val, i=val_id: self.__handle_value(i, val)
            checkbtn.check(data[val_id])

        val_id = "alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., 1.), False, "float")
        field.set_step(.001)
        field.set_value(data[val_id])

        for val_id in "xy":
            field = fields[val_id]
            field.value_id = val_id
            field.set_value_handler(self.__handle_value)
            field.set_value_range(None, False, "float")
            field.set_step(.01)
            field.set_value(data[val_id])

        for val_id in ("width", "height"):
            field = fields[val_id]
            field.value_id = val_id
            field.set_value_handler(self.__handle_value)
            field.set_value_range((.001, None), False, "float")
            field.set_step(.001)
            field.set_value(data[val_id])
            field.set_input_parser(self.__parse_size_input)

        btn = btns["reset"]
        btn.command = self.__reset

        self._combobox = combobox = comboboxes["target_view"]

        def set_view(view_id):

            self._combobox.select_item(view_id)
            self.__handle_value("view", view_id)

        for view_id in ("front", "back", "left", "right", "bottom", "top", "all"):
            command = lambda v=view_id: set_view(v)
            combobox.add_item(view_id, view_id, command)

        combobox.update_popup_menu()
        combobox.select_item(data["view"])

        self.finalize()

    def close(self, answer=""):

        self._checkbuttons = None
        self._fields = None
        self._combobox = None

        Dialog.close(self, answer)

    def __reset(self):

        fields = self._fields
        fields["filename"].set_value("")
        fields["filename"].set_text("<None>")
        fields["alpha"].set_value(1.)
        fields["x"].set_value(0.)
        fields["y"].set_value(0.)
        fields["width"].set_value(1.)
        fields["height"].set_value(1.)
        checkbtns = self._checkbuttons
        checkbtns["show"].check()
        checkbtns["in_foreground"].check(False)
        checkbtns["fixed_aspect_ratio"].check()
        checkbtns["flip_h"].check(False)
        checkbtns["flip_v"].check(False)
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

            config_data = GD["config"]
            texfile_paths = config_data["texfile_paths"]
            path = os.path.dirname(filename)

            if path not in texfile_paths:
                texfile_paths.append(path)

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

            data = self._data
            self._fields["filename"].set_value(filename)
            data["filename"] = filename
            img = PNMImage()
            img.read(Filename.from_os_specific(filename))
            w, h = img.size
            ratio = h / w
            data["bitmap_aspect_ratio"] = ratio

            if data["fixed_aspect_ratio"]:
                width = data["width"]
                height = width * ratio
                self._fields["height"].set_value(height)
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
            w, h = img.size
            ratio = h / w
            self._data["bitmap_aspect_ratio"] = ratio

            if self._data["fixed_aspect_ratio"]:
                width = self._data["width"]
                height = width * ratio
                self._fields["height"].set_value(height)
                self._data["height"] = height

        return os.path.basename(filename) if filename else "<None>"

    def __parse_size_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None

    def __handle_value(self, value_id, value, state="done"):

        data = self._data

        if value_id == "fixed_aspect_ratio" and value:

            ratio = data["bitmap_aspect_ratio"]
            width = data["width"]
            height = width * ratio
            self._fields["height"].set_value(height)
            data["height"] = height

        elif data["fixed_aspect_ratio"]:

            ratio = data["bitmap_aspect_ratio"]

            if value_id == "width":
                height = value * ratio
                self._fields["height"].set_value(height)
                data["height"] = height
            elif value_id == "height":
                width = value / ratio
                self._fields["width"].set_value(width)
                data["width"] = width

        data[value_id] = value

    def __on_yes(self):

        Mgr.update_remotely("view", "background", self._data)
