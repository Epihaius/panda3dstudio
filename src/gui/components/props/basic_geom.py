from .base import *


class BasicGeomProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}

        section = panel.add_section("basic_geom_props", "Basic properties")
        sizer = section.get_client_sizer()

        group = section.add_group("UV set names")
        grp_sizer = group.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=4, hgap=4, vgap=4)
        grp_sizer.Add(subsizer, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        self._uv_set_btns = uv_set_btns = PanelToggleButtonGroup()
        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        def set_active_uv_set(uv_set_id):

            self._uv_set_btns.set_active_button(str(uv_set_id))
            Mgr.update_remotely("uv_set_id")

        for i in range(8):
            bitmaps = PanelButton.create_button_bitmaps("*%d" % i, bitmap_paths)
            get_command = lambda i: lambda: set_active_uv_set(i)
            toggle = (get_command(i), lambda: None)
            btn = uv_set_btns.add_button(panel, group, subsizer, str(i), toggle,
                                         bitmaps, "UV set %d" % i, str(i))

        uv_set_btns.set_active_button("0")

        sizer_args = (0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL, 5)

        field = PanelInputField(panel, group, grp_sizer, 140, sizer_args=sizer_args)
        val_id = "uv_set_name"
        field.add_value(val_id, "string", handler=self.__handle_uv_name)
        field.show_value(val_id)
        field.clear()
        field.set_input_parser(val_id, self.__parse_uv_name)
        self._fields[val_id] = field

        sizer.Add(wx.Size(0, 2))

        group = section.add_group("Vertex normals")
        grp_sizer = group.get_client_sizer()
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer)
        command = lambda on: Mgr.update_remotely("normal_viz", on)
        checkbox = PanelCheckBox(panel, group, subsizer, command, sizer_args=sizer_args)
        checkbox.check(False)
        self._checkboxes["normal_viz"] = checkbox
        group.add_text("Show", subsizer, sizer_args)
        subsizer.Add(wx.Size(10, 0))
        self._color_picker = PanelColorPickerCtrl(panel, group, subsizer, self.__handle_color)

        subsizer = wx.BoxSizer()
        grp_sizer.Add(subsizer, 0, wx.LEFT | wx.TOP, 4)

        group.add_text("Length:", subsizer, sizer_args)
        field = PanelInputField(panel, group, subsizer, 80, sizer_args=sizer_args)
        field.add_value("normal_length", "float", handler=self.__handle_value)
        field.show_value("normal_length")
        field.set_input_parser("normal_length", self.__parse_length)
        self._fields["normal_length"] = field

        def finalize_sections():

            section.expand(False)

        wx.CallAfter(finalize_sections)

        Mgr.add_app_updater("uv_set_name", self.__set_uv_name)

    def get_base_type(self):

        return "basic_geom"

    def get_section_ids(self):

        return ["basic_geom_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = wx.Colour(255, 255, 0)

        if prop_id in self._checkboxes:
            self._checkboxes[prop_id].check(value)
            self._checkboxes[prop_id].set_checkmark_color(color.Get())
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "uv_set_names":
            if GlobalData["selection_count"] == 1:
                self.__set_uv_name(value)
        elif prop_id == "normal_color":
            multi_sel = GlobalData["selection_count"] > 1
            gray_values = Mgr.convert_to_remote_format("color", wx.Colour(127, 127, 127).Get())
            color_values = gray_values if multi_sel else value
            self._color_picker.set_color(color_values)
        elif prop_id in self._checkboxes:
            self._checkboxes[prop_id].check(value)
        elif prop_id in self._fields:
            self._fields[prop_id].set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        if multi_sel:

            for checkbox in self._checkboxes.itervalues():
                checkbox.check(False)

            color_values = Mgr.convert_to_remote_format("color", color.Get())
            self._color_picker.set_color(color_values)

        for checkbox in self._checkboxes.itervalues():
            checkbox.set_checkmark_color(color)

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)

    def __handle_uv_name(self, value_id, value):

        uv_set_id = int(self._uv_set_btns.get_active_button_id())
        Mgr.update_remotely(value_id, uv_set_id, value)

    def __handle_color(self, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get())
        Mgr.update_remotely("normal_color", color_values)

    def __handle_value(self, value_id, value):

        Mgr.update_remotely(value_id, value)

    def __parse_uv_name(self, name):

        parsed_name = name.strip().replace(".", "")

        return parsed_name

    def __set_uv_name(self, uv_set_names):

        uv_set_id = int(self._uv_set_btns.get_active_button_id())
        uv_set_name = uv_set_names[uv_set_id]
        self._fields["uv_set_name"].set_value("uv_set_name", uv_set_name)

    def __parse_length(self, length):

        try:
            return max(.001, abs(float(eval(length))))
        except:
            return None


PropertyPanel.add_properties("basic_geom", BasicGeomProperties)
