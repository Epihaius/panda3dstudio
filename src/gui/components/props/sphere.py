from .base import *


class SphereProperties:

    def __init__(self, panel, widgets):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}

        prop_ids = ("radius", "segments")
        val_types = ("float", "int")

        for prop_id, val_type in zip(prop_ids, val_types):
            field = widgets["fields"][f"sphere_{prop_id}"]
            field.value_id = prop_id
            field.value_type = val_type
            field.set_value_handler(self.__handle_value)
            self._fields[prop_id] = field

        self._fields["radius"].set_input_parser(self.__parse_radius_input)
        self._fields["segments"].set_input_parser(self.__parse_segments_input)

        checkbox = widgets["checkbuttons"]["sphere_smoothness"]
        checkbox.command = lambda val: self.__handle_value("smoothness", val)
        self._checkbuttons["smoothness"] = checkbox

    def setup(self): pass

    def __handle_value(self, value_id, value, state="done"):

        if GD["active_creation_type"]:
            Mgr.update_app("sphere_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

    def __parse_radius_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None

    def __parse_segments_input(self, input_text):

        try:
            return max(4, abs(int(eval(input_text))))
        except:
            return None

    def get_base_type(self):

        return "primitive"

    def get_section_ids(self):

        return ["sphere_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = Skin.colors["default_value"]

        if prop_id == "smoothness":
            self._checkbuttons["smoothness"].check(value)
            self._checkbuttons["smoothness"].set_checkmark_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "smoothness":
            self._checkbuttons["smoothness"].check(value)
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


ObjectTypes.add_type("sphere", "Sphere")
PropertyPanel.add_properties("sphere", SphereProperties)
