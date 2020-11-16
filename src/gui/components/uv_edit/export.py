from ...base import *
from ...panel import *
from ...dialogs import FileDialog


class ExportPanel(ControlPanel):

    def __init__(self, pane):

        ControlPanel.__init__(self, pane, "export")

        widgets = Skin.layout.create(self, "export")
        self._btns = btns = widgets["buttons"]
        self._colorboxes = colorboxes = widgets["colorboxes"]
        self._fields = fields = widgets["fields"]

        # ************************* Options section ***************************

        val_id = "size"
        field = fields[val_id]
        field.value_id = val_id
        field.value_type = "int"
        field.set_value_handler(self.__handle_value)
        field.set_input_parser(self.__parse_size_input)

        colorbox = colorboxes["edge_rgb"]
        colorbox.command = lambda col: self.__handle_subobj_rgb("edge", col)
        colorbox.dialog_title = "Pick edge color"

        val_id = "edge_alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., 1.), False, "float")

        colorbox = colorboxes["poly_rgb"]
        colorbox.command = lambda col: self.__handle_subobj_rgb("poly", col)
        colorbox.dialog_title = "Pick polygon / primitive part color"

        val_id = "poly_alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., 1.), False, "float")

        colorbox = colorboxes["seam_rgb"]
        colorbox.command = lambda col: self.__handle_subobj_rgb("seam", col)
        colorbox.dialog_title = "Pick seam color"

        val_id = "seam_alpha"
        field = fields[val_id]
        field.value_id = val_id
        field.set_value_handler(self.__handle_value)
        field.set_value_range((0., 1.), False, "float")

        # **************************************************************************

        btn = btns["export"]
        btn.command = self.__export

    def setup(self): pass

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_template", self.__set_template_property, interface_id="uv")

    def __handle_value(self, value_id, value, state="done"):

        Mgr.update_interface_remotely("uv", "uv_template", value_id, value)

    def __parse_size_input(self, input_text):

        try:
            return max(1, abs(int(eval(input_text))))
        except:
            return None

    def __handle_subobj_rgb(self, subobj_type, color):

        r, g, b = color
        Mgr.update_interface_remotely("uv", "uv_template", f"{subobj_type}_rgb", (r, g, b, 1.))

    def __export(self):

        def save(filename):

            config_data = GD["config"]
            texfile_paths = config_data["texfile_paths"]
            path = os.path.dirname(filename)

            if path not in texfile_paths:
                texfile_paths.append(path)

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

            Mgr.update_interface_remotely("uv", "uv_template", "save", filename)

        file_types = ("PNG files|png", "All types|*")
        FileDialog(title="Save UV template",
                   ok_alias="Save",
                   on_yes=save,
                   file_op="write",
                   incr_filename=True,
                   file_types=file_types)

    def __set_template_property(self, prop_id, value):

        if prop_id in ("size", "edge_alpha", "poly_alpha", "seam_alpha"):
            self._fields[prop_id].set_value(value)
        else:
            self._colorboxes[prop_id].color = value[:3]
