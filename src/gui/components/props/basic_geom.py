from .base import *


class BasicGeomProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}

        section = panel.add_section("basic_geom_props", "Basic editing")
        sizer = section.get_client_sizer()
        sizer.Add(wx.Size(0, 4))

        def finalize_sections():

            section.expand(False)

        wx.CallAfter(finalize_sections)

    def get_base_type(self):

        return "editable"

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

        if prop_id in self._checkboxes:
            self._checkboxes[prop_id].check(value)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)


PropertyPanel.add_properties("basic_geom", BasicGeomProperties)
