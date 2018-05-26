from .base import *


class ConeProperties(object):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}
        self._segments_default = {"circular": 3, "height": 1, "caps": 0}

        section = panel.add_section("cone_props", "Cone properties", hidden=True)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        section.add(sizer, expand=True)

        for spec in ("bottom", "top"):
            text = "{} radius:".format(spec.title())
            sizer.add(PanelText(section, text), alignment_v="center_v")
            prop_id = "radius_{}".format(spec)
            field = PanelInputField(section, 80)
            field.add_value(prop_id, "float", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field
            sizer.add(field, proportion_h=1., alignment_v="center_v")

        text = "Height:"
        sizer.add(PanelText(section, text), alignment_v="center_v")
        prop_id = "height"
        field = PanelInputField(section, 80)
        field.add_value(prop_id, "float", handler=self.__handle_value)
        field.show_value(prop_id)
        self._fields[prop_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")

        group = section.add_group("Segments")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)

        for spec in ("circular", "height", "caps"):
            prop_id = "segments_{}".format(spec)
            text = "{}:".format(spec.title())
            sizer.add(PanelText(group, text), alignment_v="center_v")
            field = PanelInputField(group, 80)
            field.add_value(prop_id, "int", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field
            sizer.add(field, proportion_h=1., alignment_v="center_v")

        get_parser = lambda radius_min: lambda radius: self.__parse_radius(radius, radius_min)

        for spec, val_min in (("bottom", .001), ("top", 0.)):
            prop_id = "radius_{}".format(spec)
            self._fields[prop_id].set_input_parser(prop_id, get_parser(val_min))

        self._fields["height"].set_input_parser("height", self.__parse_height)
        parser = lambda segs: self.__parse_segments(segs, 3)
        self._fields["segments_circular"].set_input_parser("segments_circular", parser)
        parser = lambda segs: self.__parse_segments(segs, 1)
        self._fields["segments_height"].set_input_parser("segments_height", parser)
        parser = lambda segs: self.__parse_segments(segs, 0)
        self._fields["segments_caps"].set_input_parser("segments_caps", parser)

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer)
        checkbox = PanelCheckBox(section, lambda val: self.__handle_value("smoothness", val))
        checkbox.check(True)
        self._checkboxes["smoothness"] = checkbox
        borders = (0, 5, 0, 0)
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Smooth"
        sizer.add(PanelText(section, text), alignment="center_v")

    def setup(self): pass

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
            Mgr.update_app("cone_prop_default", prop_id, val)
            return

        Mgr.update_remotely("selected_obj_prop", prop_id, val)

    def __parse_radius(self, radius, radius_min):

        try:
            return max(radius_min, abs(float(eval(radius))))
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

        return ["cone_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = (1., 1., 0., 1.)

        if prop_id == "smoothness":
            self._checkboxes["smoothness"].check(value)
            self._checkboxes["smoothness"].set_checkmark_color(color)
        elif prop_id == "segments":
            self._segments_default.update(value)
            for spec in ("circular", "height", "caps"):
                value_id = "segments_" + spec
                field = self._fields[value_id]
                field.show_text()
                field.set_value(value_id, value[spec], handle_value=False)
                field.set_text_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value, handle_value=False)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "smoothness":
            self._checkboxes["smoothness"].check(value)
        elif prop_id == "segments":
            for spec in ("circular", "height", "caps"):
                value_id = "segments_" + spec
                field = self._fields[value_id]
                field.set_value(value_id, value[spec], handle_value=False)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.set_value(prop_id, value, handle_value=False)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        if multi_sel:
            self._checkboxes["smoothness"].check(False)

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkboxes["smoothness"].set_checkmark_color(color)


ObjectTypes.add_type("cone", "Cone")
PropertyPanel.add_properties("cone", ConeProperties)
