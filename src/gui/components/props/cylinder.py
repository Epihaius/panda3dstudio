from .base import *


class CylinderProperties:

    def __init__(self, panel, widgets):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}
        self._segments_default = {"circular": 3, "height": 1, "caps": 0}

        for prop_id in ("radius", "height"):
            field = widgets["fields"][f"cylinder_{prop_id}"]
            field.value_id = prop_id
            field.value_type = "float"
            field.set_value_handler(self.__handle_value)
            self._fields[prop_id] = field

        for prop_id in ("segments_circular", "segments_height", "segments_caps"):
            field = widgets["fields"][f"cylinder_{prop_id}"]
            field.value_id = prop_id
            field.value_type = "int"
            field.set_value_handler(self.__handle_value)
            self._fields[prop_id] = field

        self._fields["radius"].set_input_parser(self.__parse_radius_input)
        self._fields["height"].set_input_parser(self.__parse_height_input)
        parser = lambda input_text: self.__parse_segments_input(input_text, 3)
        self._fields["segments_circular"].set_input_parser(parser)
        parser = lambda input_text: self.__parse_segments_input(input_text, 1)
        self._fields["segments_height"].set_input_parser(parser)
        parser = lambda input_text: self.__parse_segments_input(input_text, 0)
        self._fields["segments_caps"].set_input_parser(parser)

        checkbtn = widgets["checkbuttons"]["cylinder_smoothness"]
        checkbtn.command = lambda val: self.__handle_value("smoothness", val)
        self._checkbuttons["smoothness"] = checkbtn

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

        color = Skin.colors["default_value"]

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
        color = Skin.text["input_disabled"]["color"] if multi_sel else None

        if multi_sel:
            self._checkbuttons["smoothness"].check(False)

        for field in self._fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkbuttons["smoothness"].set_checkmark_color(color)


ObjectTypes.add_type("cylinder", "Cylinder")
PropertyPanel.add_properties("cylinder", CylinderProperties)
