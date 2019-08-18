from ...base import *
from ...panel import *
from ...dialog import FileDialog


class BackgroundPanel(Panel):

    def __init__(self, stack):

        Panel.__init__(self, stack, "background", "Background")

        self._checkbuttons = {}
        self._fields = {}

        self._tex_filename = ""

        top_container = self.get_top_container()

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        borders = (5, 5, 10, 5)
        top_container.add(sizer, expand=True, borders=borders)

        text = "Load"
        tooltip_text = "Load background texture"
        btn = PanelButton(top_container, text, "", tooltip_text, self.__load_tex)
        sizer.add(btn, stretch_h=True, alignment_v="center_v")

        val_id = "tex_filename"
        handler = lambda *args: self.__set_tex(args[1])
        field = PanelInputField(top_container, val_id, "string", handler, 120)
        field.set_input_init(self.__init_tex_filename_input)
        field.set_input_parser(self.__check_texture_filename)
        field.set_value_parser(self.__parse_texture_filename)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "Brightness:"
        sizer.add(PanelText(top_container, text), alignment_v="center_v")
        val_id = "brightness"
        field = PanelSliderField(top_container, val_id, "float", (0., 1.), self.__handle_value, 80)
        field.set_input_parser(self.__parse_brightness_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "Tiling:"
        sizer.add(PanelText(top_container, text), alignment_v="center_v")
        val_id = "tiling"
        field = PanelInputField(top_container, val_id, "int", self.__handle_value, 40)
        field.set_input_parser(self.__parse_tiling_input)
        self._fields[val_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        command = lambda val: self.__handle_value("show_on_models", val)
        text = "Show on models"
        checkbtn = PanelCheckButton(top_container, command, text)
        self._checkbuttons["show_on_models"] = checkbtn
        top_container.add(checkbtn, borders=borders)

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

    def __parse_brightness_input(self, input_text):

        try:
            return min(1., max(0., float(eval(input_text))))
        except:
            return None

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
