from .base import *


class DummyProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}

        section = panel.add_section("dummy_props", "Dummy helper properties")
        sizer = section.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        section.add_text("Size:", subsizer, sizer_args)
        field = PanelInputField(panel, section, subsizer, 80)
        field.add_value("size", "float", handler=self.__handle_value)
        field.show_value("size")
        self._fields["size"] = field
        self._fields["size"].set_input_parser("size", self.__parse_size)

    def __handle_value(self, value_id, value):

        if Mgr.get_global("active_creation_type"):
            Mgr.update_app("dummy_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

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

        if prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id in self._fields:
            field = self._fields[prop_id]
            field.set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = Mgr.get_global("selection_count")
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)


ObjectTypes.add_type("dummy", "Dummy Helper")
PropertyPanel.add_properties("dummy", DummyProperties)
