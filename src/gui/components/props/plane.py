from .base import *


class PlaneProperties:

    def __init__(self, panel, widgets):

        self._panel = panel
        self._fields = {}
        self._segments_default = {"x": 1, "y": 1}

        axes = "xy"
        prop_types = ("size", "segments")
        val_types = ("float", "int")
        parsers = (self.__parse_dimension_input, self.__parse_segments_input)

        for prop_type, val_type, parser in zip(prop_types, val_types, parsers):
            for axis in axes:
                prop_id = f"{prop_type}_{axis}"
                field = widgets["fields"][f"plane_{prop_id}"]
                field.value_id = prop_id
                field.value_type = val_type
                field.set_value_handler(self.__handle_value)
                field.set_input_parser(parser)
                self._fields[prop_id] = field

    def setup(self): pass

    def __handle_value(self, value_id, value, state="done"):

        in_creation_mode = GD["active_creation_type"]

        if "segments" in value_id:
            prop_id, axis = value_id.split("_")
            val = self._segments_default if in_creation_mode else {}
            val[axis] = value
            val = val.copy()
        else:
            prop_id = value_id
            val = value

        if in_creation_mode:
            Mgr.update_app("plane_prop_default", prop_id, val)
            return

        Mgr.update_remotely("selected_obj_prop", prop_id, val)

    def __parse_dimension_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None

    def __parse_segments_input(self, input_text):

        try:
            return max(1, abs(int(eval(input_text))))
        except:
            return None

    def get_base_type(self):

        return "primitive"

    def get_section_ids(self):

        return ["plane_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = Skin.colors["default_value"]

        if prop_id == "segments":
            self._segments_default.update(value)
            for axis in "xy":
                value_id = "segments_" + axis
                field = self._fields[value_id]
                field.show_text()
                field.set_value(value[axis])
                field.set_text_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if not (prop_id == "segments" or prop_id in self._fields):
            return

        if prop_id == "segments":
            for axis in "xy":
                value_id = "segments_" + axis
                field = self._fields[value_id]
                field.set_value(value[axis])
        else:
            field = self._fields[prop_id]
            field.set_value(value)

    def check_selection_count(self):

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = Skin.text["input_disabled"]["color"] if multi_sel else None

        for field in self._fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)


ObjectTypes.add_type("plane", "Plane")
PropertyPanel.add_properties("plane", PlaneProperties)
