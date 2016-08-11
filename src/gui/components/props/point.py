from .base import *


class PointProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}
        self._color_pickers = {}

        section = panel.add_section("point_props", "Point helper properties")
        sizer = section.get_client_sizer()

        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        section.add_text("Size:", subsizer, sizer_args)
        prop_id = "size"
        field = PanelInputField(panel, section, subsizer, 45)
        field.add_value(prop_id, "int", handler=self.__handle_value)
        field.show_value(prop_id)
        self._fields[prop_id] = field
        self._fields[prop_id].set_input_parser("size", self.__parse_size)

        sizer.Add(wx.Size(0, 4))

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        prop_id = "on_top"
        checkbox = PanelCheckBox(panel, section, subsizer, self.__draw_on_top,
                                 sizer_args=sizer_args)
        self._checkboxes[prop_id] = checkbox
        section.add_text("Draw on top", subsizer, sizer_args)

        sizer.Add(wx.Size(0, 5))

        group = section.add_group("Color")
        grp_sizer = group.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        grp_sizer.Add(subsizer)
        group.add_text("Unselected:", subsizer, sizer_args)
        color_picker = PanelColorPickerCtrl(panel, group, subsizer,
                                            lambda col: self.__handle_color("unselected", col))
        self._color_pickers["unselected_color"] = color_picker

        group.add_text("Selected:", subsizer, sizer_args)
        color_picker = PanelColorPickerCtrl(panel, group, subsizer,
                                            lambda col: self.__handle_color("selected", col))
        self._color_pickers["selected_color"] = color_picker

    def __handle_value(self, value_id, value):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("point_helper_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

    def __draw_on_top(self, on_top):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("point_helper_prop_default", "on_top", on_top)
            return

        Mgr.update_remotely("selected_obj_prop", "on_top", on_top)

    def __parse_size(self, size):

        try:
            return max(1, abs(int(eval(size))))
        except:
            return None

    def __handle_color(self, sel_state, color):

        r, g, b = color.Get()
        color_values = Mgr.convert_to_remote_format("color", (r, g, b, 255))
        prop_id = "%s_color" % sel_state

        if GlobalData["active_creation_type"]:
            Mgr.update_remotely("point_helper_prop_default", prop_id, color_values)
            self.set_object_property_default(prop_id, color_values)
            return

        Mgr.update_remotely("selected_obj_prop", prop_id, color_values)

    def get_base_type(self):

        return "helper"

    def get_section_ids(self):

        return ["point_props"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = wx.Colour(255, 255, 0)
        fields = self._fields
        checkboxes = self._checkboxes
        color_pickers = self._color_pickers

        if prop_id in fields:
            field = fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)
        elif prop_id in checkboxes:
            checkboxes[prop_id].check(value)
            checkboxes[prop_id].set_checkmark_color(color)
        elif prop_id in color_pickers:
            color_pickers[prop_id].set_color(value)

    def set_object_property(self, prop_id, value):

        fields = self._fields
        checkboxes = self._checkboxes
        color_pickers = self._color_pickers

        if prop_id in fields:
            fields[prop_id].set_value(prop_id, value)
        elif prop_id in checkboxes:
            checkboxes[prop_id].check(value)
        elif prop_id in color_pickers:
            color_pickers[prop_id].set_color(value)

    def check_selection_count(self):

        checkboxes = self._checkboxes
        fields = self._fields

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        for checkbox in checkboxes.itervalues():
            checkbox.set_checkmark_color(color)

        for field in fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)


ObjectTypes.add_type("point_helper", "Point Helper")
PropertyPanel.add_properties("point_helper", PointProperties)
