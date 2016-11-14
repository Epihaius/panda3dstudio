from .base import *


class TorusProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}
        self._segments_default = {"ring": 3, "section": 3}

        section = panel.add_section("torus_props", "Torus properties")
        sizer = section.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        for spec in ("ring", "section"):
            section.add_text("%s radius:" % spec.title(), subsizer, sizer_args)
            field = PanelInputField(panel, section, subsizer, 80)
            prop_id = "radius_%s" % spec
            field.add_value(prop_id, "float", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field

        sizer.Add(wx.Size(0, 4))

        group = section.add_group("Segments")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        grp_sizer.Add(subsizer)

        for spec in ("ring", "section"):
            prop_id = "segments_%s" % spec
            group.add_text("%s:" % spec.title(), subsizer, sizer_args)
            field = PanelInputField(panel, group, subsizer, 80)
            field.add_value(prop_id, "int", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field

        for spec in ("ring", "section"):
            prop_id = "radius_%s" % spec
            self._fields[prop_id].set_input_parser(prop_id, self.__parse_radius)
            prop_id = "segments_%s" % spec
            self._fields[prop_id].set_input_parser(prop_id, self.__parse_segments)

        sizer.Add(wx.Size(0, 4))

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        checkbox = PanelCheckBox(panel, section, subsizer,
                                 lambda val: self.__handle_value("smoothness", val))
        checkbox.check(True)
        self._checkboxes["smoothness"] = checkbox
        section.add_text("Smooth", subsizer, sizer_args)

    def __handle_value(self, value_id, value):

        in_creation_mode = GlobalData["active_creation_type"]

        if "segments" in value_id:
            prop_id, spec = value_id.split("_")
            val = self._segments_default if in_creation_mode else {}
            val[spec] = value
            val = val.copy()
        else:
            prop_id = value_id
            val = value

        if in_creation_mode:
            Mgr.update_app("torus_prop_default", prop_id, val)
            return

        Mgr.update_remotely("selected_obj_prop", prop_id, val)

    def __parse_radius(self, radius):

        try:
            return max(.001, abs(float(eval(radius))))
        except:
            return None

    def __parse_segments(self, segments):

        try:
            return max(3, abs(int(eval(segments))))
        except:
            return None

    def get_base_type(self):

        return "primitive"

    def get_section_ids(self):

        return ["torus_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = wx.Colour(255, 255, 0)

        if prop_id == "smoothness":
            self._checkboxes["smoothness"].check(value)
            self._checkboxes["smoothness"].set_checkmark_color(color.Get())
        elif prop_id == "segments":
            self._segments_default.update(value)
            for spec in ("ring", "section"):
                value_id = "segments_" + spec
                field = self._fields[value_id]
                field.show_text()
                field.set_value(value_id, value[spec])
                field.set_text_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "smoothness":
            self._checkboxes["smoothness"].check(value)
        elif prop_id == "segments":
            for spec in ("ring", "section"):
                value_id = "segments_" + spec
                field = self._fields[value_id]
                field.set_value(value_id, value[spec])
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        if multi_sel:
            self._checkboxes["smoothness"].check(False)

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkboxes["smoothness"].set_checkmark_color(color)


ObjectTypes.add_type("torus", "Torus")
PropertyPanel.add_properties("torus", TorusProperties)
