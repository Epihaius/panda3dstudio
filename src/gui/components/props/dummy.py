from .base import *


class DummyProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}

        section = panel.add_section("dummy_props", "Dummy helper properties")
        sizer = section.get_client_sizer()

        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5, vgap=2)
        sizer.Add(subsizer)
        get_handler = lambda geom_type: lambda val: self.__handle_viz(geom_type, val)

        for geom_type in ("box", "cross"):
            checkbox = PanelCheckBox(panel, section, subsizer, get_handler(geom_type),
                                     sizer_args=sizer_args)
            self._checkboxes["%s_viz" % geom_type] = checkbox
            section.add_text("Show %s" % geom_type, subsizer, sizer_args)

        subsizer = wx.FlexGridSizer(rows=0, cols=3, hgap=5, vgap=2)
        sizer.Add(subsizer)
        section.add_text("Box size:", subsizer, sizer_args)
        prop_id = "size"
        field = PanelInputField(panel, section, subsizer, 80)
        field.add_value(prop_id, "float", handler=self.__handle_value)
        field.show_value(prop_id)
        self._fields[prop_id] = field
        self._fields[prop_id].set_input_parser("size", self.__parse_size)

        subsizer.AddStretchSpacer()

        section.add_text("Cross size:", subsizer, sizer_args)
        prop_id = "cross_size"
        field = PanelInputField(panel, section, subsizer, 80)
        field.add_value(prop_id, "float", handler=self.__handle_value)
        field.show_value(prop_id)
        self._fields[prop_id] = field
        self._fields[prop_id].set_input_parser("size", self.__parse_size)
        section.add_text("%", subsizer, sizer_args)

        sizer.Add(wx.Size(0, 4))

        subsizer = wx.FlexGridSizer(rows=0, cols=3, hgap=5)
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        prop_id = "const_size_state"
        get_handler = lambda prop_id: lambda val: self.__handle_value(prop_id, val)
        checkbox = PanelCheckBox(panel, section, subsizer, get_handler(prop_id),
                                 sizer_args=sizer_args)
        self._checkboxes[prop_id] = checkbox
        section.add_text("Const. screen size:", subsizer, sizer_args)
        prop_id = "const_size"
        field = PanelInputField(panel, section, subsizer, 40)
        field.set_value_parser(prop_id, lambda value: "%.1f" % value)
        field.add_value(prop_id, "float", handler=self.__handle_value)
        field.show_value(prop_id)
        self._fields[prop_id] = field
        self._fields[prop_id].set_input_parser(prop_id, self.__parse_size)

        sizer.Add(wx.Size(0, 4))

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        prop_id = "on_top"
        checkbox = PanelCheckBox(panel, section, subsizer, get_handler(prop_id),
                                 sizer_args=sizer_args)
        self._checkboxes[prop_id] = checkbox
        section.add_text("Draw on top", subsizer, sizer_args)

    def __handle_value(self, value_id, value):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("dummy_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

    def __handle_viz(self, geom_type, shown):

        other_geom_type = "cross" if geom_type == "box" else "box"
        other_shown = self._checkboxes["%s_viz" % other_geom_type].is_checked()

        if not shown and not other_shown:
            self._checkboxes["%s_viz" % other_geom_type].check()
            other_shown = True

        viz = set()

        if shown:
            viz.add(geom_type)

        if other_shown:
            viz.add(other_geom_type)

        if GlobalData["active_creation_type"]:
            Mgr.update_app("dummy_prop_default", "viz", viz)
            return

        Mgr.update_remotely("selected_obj_prop", "viz", viz)

    def __parse_size(self, size):

        try:
            return max(.001, abs(float(eval(size))))
        except:
            return None

    def get_base_type(self):

        return "helper"

    def get_section_ids(self):

        return ["dummy_props"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = wx.Colour(255, 255, 0)
        checkboxes = self._checkboxes

        if prop_id == "viz":
            for geom_type in ("box", "cross"):
                check_id = "%s_viz" % geom_type
                checkboxes[check_id].check(True if geom_type in value else False)
                checkboxes[check_id].set_checkmark_color(color)
        elif prop_id in checkboxes:
            checkboxes[prop_id].check(value)
            checkboxes[prop_id].set_checkmark_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        checkboxes = self._checkboxes
        fields = self._fields

        if prop_id == "viz":
            for geom_type in ("box", "cross"):
                check_id = "%s_viz" % geom_type
                checkboxes[check_id].check(True if geom_type in value else False)
        elif prop_id in checkboxes:
            checkboxes[prop_id].check(value)
        elif prop_id in fields:
            fields[prop_id].set_value(prop_id, value)

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


ObjectTypes.add_type("dummy", "Dummy Helper")
PropertyPanel.add_properties("dummy", DummyProperties)
