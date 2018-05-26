from ...base import *
from ...panel import *
from ...dialog import FileDialog


class ExportPanel(Panel):

    def __init__(self, stack):

        Panel.__init__(self, stack, "export", "Template export")

        self._btns = {}
        self._colorboxes = {}
        self._fields = {}

        # ************************* Options section ***************************

        section = self.add_section("export_options", "Export options")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        text = "Width, height:"
        sizer.add(PanelText(section, text), alignment="center_v")
        sizer.add((5, 0))

        field = PanelInputField(section, 80)
        field.add_value("size", "int", handler=self.__handle_value)
        field.show_value("size")
        field.set_input_parser("size", self.__parse_size)
        self._fields["size"] = field
        sizer.add(field, proportion=1., alignment="center_v")

        group = section.add_group("Edge color")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "RGB:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))

        dialog_title = "Pick edge color"
        command = lambda col: self.__handle_subobj_rgb("edge", col)
        colorbox = PanelColorBox(group, command, dialog_title=dialog_title)
        self._colorboxes["edge_rgb"] = colorbox
        sizer.add(colorbox, alignment="center_v")
        sizer.add((5, 0))

        text = "Alpha:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))
        field = PanelInputField(group, 45)
        val_id = "edge_alpha"
        field.set_input_parser(val_id, self.__parse_alpha)
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        sizer.add(field, proportion=1., alignment="center_v")

        group = section.add_group("Polygon color")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "RGB:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))

        dialog_title = "Pick polygon color"
        command = lambda col: self.__handle_subobj_rgb("poly", col)
        colorbox = PanelColorBox(group, command, dialog_title=dialog_title)
        self._colorboxes["poly_rgb"] = colorbox
        sizer.add(colorbox, alignment="center_v")
        sizer.add((5, 0))

        text = "Alpha:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))
        field = PanelInputField(group, 45)
        val_id = "poly_alpha"
        field.set_input_parser(val_id, self.__parse_alpha)
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        sizer.add(field, proportion=1., alignment="center_v")

        group = section.add_group("Seam color")
        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "RGB:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))

        dialog_title = "Pick seam color"
        command = lambda col: self.__handle_subobj_rgb("seam", col)
        colorbox = PanelColorBox(group, command, dialog_title=dialog_title)
        self._colorboxes["seam_rgb"] = colorbox
        sizer.add(colorbox, alignment="center_v")
        sizer.add((5, 0))

        text = "Alpha:"
        sizer.add(PanelText(group, text), alignment="center_v")
        sizer.add((5, 0))
        field = PanelInputField(group, 45)
        val_id = "seam_alpha"
        field.set_input_parser(val_id, self.__parse_alpha)
        field.add_value(val_id, "float", handler=self.__handle_value)
        field.show_value(val_id)
        self._fields[val_id] = field
        sizer.add(field, proportion=1., alignment="center_v")

        # **************************************************************************

        bottom_container = self.get_bottom_container()

        text = "Export"
        tooltip_text = "Export UV template"
        btn = PanelButton(bottom_container, text, "", tooltip_text, self.__export)
        self._btns["export"] = btn
        borders = (0, 0, 10, 10)
        bottom_container.add(btn, alignment="center_h", borders=borders)

    def setup(self): pass

    def add_interface_updaters(self):

        Mgr.add_app_updater("uv_template", self.__set_template_property, interface_id="uv")

    def __handle_value(self, value_id, value):

        Mgr.update_interface_remotely("uv", "uv_template", value_id, value)

    def __parse_size(self, size):

        try:
            return max(1, abs(int(eval(size))))
        except:
            return None

    def __parse_alpha(self, alpha):

        try:
            return min(1., max(0., float(eval(alpha))))
        except:
            return None

    def __handle_subobj_rgb(self, subobj_type, color):

        r, g, b = color
        Mgr.update_interface_remotely("uv", "uv_template", "{}_rgb".format(subobj_type), (r, g, b, 1.))

    def __export(self):

        def save(filename):

            config_data = GlobalData["config"]
            texfile_paths = config_data["texfile_paths"]
            path = os.path.dirname(filename)

            if path not in texfile_paths:
                texfile_paths.append(path)

            with open("config", "wb") as config_file:
                cPickle.dump(config_data, config_file, -1)

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
            self._fields[prop_id].set_value(prop_id, value, handle_value=False)
        else:
            self._colorboxes[prop_id].set_color(value[:3])
