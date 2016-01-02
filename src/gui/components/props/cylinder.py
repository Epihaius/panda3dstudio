from .base import *


class CylinderProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}

        section = panel.add_section("cylinder_props", "Cylinder properties")
        sizer = section.get_client_sizer()

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        for prop_id in ("radius", "height"):
            section.add_text("%s:" % prop_id.title(), subsizer, sizer_args)
            field = PanelInputField(panel, section, subsizer, 80)
            field.add_value(prop_id, "float", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field

        sizer.Add(wx.Size(0, 4))

        group = section.add_group("Segments")
        grp_sizer = group.get_client_sizer()
        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        grp_sizer.Add(subsizer)

        for spec in ("lateral", "height", "caps"):
            prop_id = "segments_%s" % spec
            group.add_text("%s:" % spec.title(), subsizer, sizer_args)
            field = PanelInputField(panel, group, subsizer, 80)
            field.add_value(prop_id, "int", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field

        self._fields["radius"].set_input_parser("radius", self.__parse_radius)
        self._fields["height"].set_input_parser("height", self.__parse_height)
        parser = lambda segs: self.__parse_segments(segs, 3)
        self._fields["segments_lateral"].set_input_parser(
            "segments_lateral", parser)
        parser = lambda segs: self.__parse_segments(segs, 1)
        self._fields["segments_height"].set_input_parser(
            "segments_height", parser)
        parser = lambda segs: self.__parse_segments(segs, 0)
        self._fields["segments_caps"].set_input_parser("segments_caps", parser)

        sizer.Add(wx.Size(0, 4))

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        sizer.Add(subsizer)
        checkbox = PanelCheckBox(panel, section, subsizer,
                                 lambda val: self.__handle_value("smoothness", val))
        checkbox.check(True)
        self._checkboxes["smoothness"] = checkbox
        section.add_text("Smooth", subsizer, sizer_args)

    def __handle_value(self, value_id, value):

        if Mgr.get_global("active_creation_type"):
            Mgr.update_app("cylinder_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

    def __parse_radius(self, radius):

        try:
            return max(.001, abs(float(eval(radius))))
        except:
            return None

    def __parse_height(self, height):

        try:
            value = float(eval(height))
        except:
            return None

        sign = -1. if value < 0. else 1.

        return max(.001, abs(value)) * sign

    def __parse_segments(self, segments, segs_min):

        try:
            return max(segs_min, abs(int(eval(segments))))
        except:
            return None

    def get_base_type(self):

        return "primitive"

    def get_section_ids(self):

        return ["cylinder_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = wx.Colour(255, 255, 0)

        if prop_id == "smoothness":
            self._checkboxes["smoothness"].check(value)
            self._checkboxes["smoothness"].set_checkmark_color(color.Get())
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "smoothness":
            self._checkboxes["smoothness"].check(value)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = Mgr.get_global("selection_count")
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        if multi_sel:
            self._checkboxes["smoothness"].check(False)

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkboxes["smoothness"].set_checkmark_color(color)


ObjectTypes.add_type("cylinder", "Cylinder")
PropertyPanel.add_properties("cylinder", CylinderProperties)
