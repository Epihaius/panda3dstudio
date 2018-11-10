from .base import *


class TorusProperties(object):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}
        self._segments_default = {"ring": 3, "section": 3}

        section = panel.add_section("torus_props", "Torus properties", hidden=True)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        section.add(sizer, expand=True)

        for spec in ("ring", "section"):
            text = "{} radius:".format(spec.title())
            sizer.add(PanelText(section, text), alignment_v="center_v")
            prop_id = "radius_{}".format(spec)
            field = PanelInputField(section, 80)
            field.add_value(prop_id, "float", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field
            sizer.add(field, proportion_h=1., alignment_v="center_v")

        group = section.add_group("Segments")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)

        for spec in ("ring", "section"):
            prop_id = "segments_{}".format(spec)
            text = "{}:".format(spec.title())
            sizer.add(PanelText(group, text), alignment_v="center_v")
            field = PanelInputField(group, 80)
            field.add_value(prop_id, "int", handler=self.__handle_value)
            field.show_value(prop_id)
            self._fields[prop_id] = field
            sizer.add(field, proportion_h=1., alignment_v="center_v")

        for spec in ("ring", "section"):
            prop_id = "radius_{}".format(spec)
            self._fields[prop_id].set_input_parser(prop_id, self.__parse_radius)
            prop_id = "segments_{}".format(spec)
            self._fields[prop_id].set_input_parser(prop_id, self.__parse_segments)

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

        color = (1., 1., 0., 1.)

        if prop_id == "smoothness":
            self._checkboxes["smoothness"].check(value)
            self._checkboxes["smoothness"].set_checkmark_color(color)
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
        color = (.5, .5, .5, 1.) if multi_sel else None

        if multi_sel:
            self._checkboxes["smoothness"].check(False)

        for field in self._fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkboxes["smoothness"].set_checkmark_color(color)


ObjectTypes.add_type("torus", "Torus")
PropertyPanel.add_properties("torus", TorusProperties)
