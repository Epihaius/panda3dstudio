from .base import *


class CylinderProperties:

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}
        self._segments_default = {"circular": 3, "height": 1, "caps": 0}

        section = panel.add_section("cylinder_props", "Cylinder properties", hidden=True)

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        section.add(sizer, expand=True)

        for prop_id in ("radius", "height"):
            text = f"{prop_id.title()}:"
            sizer.add(PanelText(section, text), alignment_v="center_v")
            field = PanelInputField(section, prop_id, "float", self.__handle_value, 80)
            self._fields[prop_id] = field
            sizer.add(field, proportion_h=1., alignment_v="center_v")

        group = section.add_group("Segments")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)

        for spec in ("circular", "height", "caps"):
            prop_id = f"segments_{spec}"
            text = f"{spec.title()}:"
            sizer.add(PanelText(group, text), alignment_v="center_v")
            field = PanelInputField(group, prop_id, "int", self.__handle_value, 80)
            self._fields[prop_id] = field
            sizer.add(field, proportion_h=1., alignment_v="center_v")

        self._fields["radius"].set_input_parser(self.__parse_radius_input)
        self._fields["height"].set_input_parser(self.__parse_height_input)
        parser = lambda input_text: self.__parse_segments_input(input_text, 3)
        self._fields["segments_circular"].set_input_parser(parser)
        parser = lambda input_text: self.__parse_segments_input(input_text, 1)
        self._fields["segments_height"].set_input_parser(parser)
        parser = lambda input_text: self.__parse_segments_input(input_text, 0)
        self._fields["segments_caps"].set_input_parser(parser)

        section.add((0, 5))

        text = "Smooth"
        checkbtn = PanelCheckButton(section, lambda val:
            self.__handle_value("smoothness", val), text)
        checkbtn.check(True)
        self._checkbuttons["smoothness"] = checkbtn
        section.add(checkbtn)

    def setup(self): pass

    def __handle_value(self, value_id, value, state="done"):

        in_creation_mode = GD["active_creation_type"]

        if "segments" in value_id:
            prop_id, spec = value_id.split("_")
            val = self._segments_default if in_creation_mode else {}
            val[spec] = value
            val = val.copy()
        else:
            prop_id = value_id
            val = value

        if in_creation_mode:
            Mgr.update_app("cylinder_prop_default", prop_id, val)
            return

        Mgr.update_remotely("selected_obj_prop", prop_id, val)

    def __parse_radius_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None

    def __parse_height_input(self, input_text):

        try:
            value = float(eval(input_text))
        except:
            return None

        sign = -1. if value < 0. else 1.

        return max(.001, abs(value)) * sign

    def __parse_segments_input(self, input_text, segs_min):

        try:
            return max(segs_min, abs(int(eval(input_text))))
        except:
            return None

    def get_base_type(self):

        return "primitive"

    def get_section_ids(self):

        return ["cylinder_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = (1., 1., 0., 1.)

        if prop_id == "smoothness":
            self._checkbuttons["smoothness"].check(value)
            self._checkbuttons["smoothness"].set_checkmark_color(color)
        elif prop_id == "segments":
            self._segments_default.update(value)
            for spec in ("circular", "height", "caps"):
                value_id = "segments_" + spec
                field = self._fields[value_id]
                field.show_text()
                field.set_value(value[spec])
                field.set_text_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "smoothness":
            self._checkbuttons["smoothness"].check(value)
        elif prop_id == "segments":
            for spec in ("circular", "height", "caps"):
                value_id = "segments_" + spec
                field = self._fields[value_id]
                field.set_value(value[spec])
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.set_value(value)

    def check_selection_count(self):

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        if multi_sel:
            self._checkbuttons["smoothness"].check(False)

        for field in self._fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkbuttons["smoothness"].set_checkmark_color(color)


ObjectTypes.add_type("cylinder", "Cylinder")
PropertyPanel.add_properties("cylinder", CylinderProperties)
