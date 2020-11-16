from ...base import *
from ...panel import *
from ...dialogs import FileDialog


class BackgroundPanel(ControlPanel):

    def __init__(self, pane):

        ControlPanel.__init__(self, pane, "background")

        widgets = Skin.layout.create(self, "background")
        self._btns = btns = widgets["buttons"]
        self._checkbuttons = checkbuttons = widgets["checkbuttons"]
        self._fields = fields = widgets["fields"]

        self._tex_filename = ""

        btn = btns["load"]
        btn.command =  self.__load_tex

        val_id = "tex_filename"
        handler = lambda *args: self.__set_tex(args[1])
        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "string"
        field.set_value_handler(handler)
        field.set_input_init(self.__init_tex_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)

        val_id = "brightness"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., 1.), False, "float")
        field.set_step(.01)

        val_id = "tiling"
        field = fields[val_id]
        field.value_id = val_id
        field.set_input_parser(self.__parse_tiling_input)
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0, None), False, "int")
        field.set_step(1)

        checkbtn = checkbuttons["show_on_models"]
        checkbtn.command = lambda val: self.__handle_value("show_on_models", val)

    def setup(self): pass

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_background", self.__set_background_property, interface_id="uv")

    def __handle_value(self, value_id, value, state="done"):

        Mgr.update_interface_remotely("uv", "uv_background", value_id, value)

    def __load_tex(self):

        def load(tex_filename):

            config_data = GD["config"]
            texfile_paths = config_data["texfile_paths"]
            path = os.path.dirname(tex_filename)

            if path not in texfile_paths:
                texfile_paths.append(path)

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

            self._fields["tex_filename"].set_value(tex_filename)
            self._tex_filename = tex_filename

            Mgr.update_interface_remotely("uv", "uv_background", "tex_filename", tex_filename)

        file_types = ("Bitmap files|bmp;jpg;png", "All types|*")
        FileDialog(title="Load background texture",
                   ok_alias="Load",
                   on_yes=load,
                   file_op="read",
                   file_types=file_types)

    def __set_tex(self, tex_filename):

        self._tex_filename = tex_filename

        Mgr.update_interface_remotely("uv", "uv_background", "tex_filename", tex_filename)

    def __init_tex_filename_input(self):

        field = self._fields["tex_filename"]

        if self._tex_filename:
            field.set_input_text(self._tex_filename)
        else:
            field.clear(forget=False)

    def __check_texture_filename(self, filename):

        return filename if (not filename or os.path.exists(filename)) else None

    def __parse_texture_filename(self, filename):

        return os.path.basename(filename) if filename else "<None>"

    def __parse_tiling_input(self, input_text):

        try:
            return max(0, abs(int(eval(input_text))))
        except:
            return None

    def __set_background_property(self, prop_id, value):

        if prop_id == "show_on_models":
            self._checkbuttons[prop_id].check(value)
            return

        self._fields[prop_id].set_value(value)

        if prop_id == "tex_filename":
            self._tex_filename = value
