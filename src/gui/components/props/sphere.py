from .base import *


class SphereProperties:

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}

        section = panel.add_section("sphere_props", "Sphere properties", hidden=True)

        prop_ids = ("radius", "segments")
        val_types = ("float", "int")

        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        section.add(sizer, expand=True)

        for prop_id, val_type in zip(prop_ids, val_types):
            text = "{}:".format(prop_id.title())
            sizer.add(PanelText(section, text), alignment_v="center_v")
            field = PanelInputField(section, prop_id, val_type, self.__handle_value, 80)
            self._fields[prop_id] = field
            sizer.add(field, proportion_h=1., alignment_v="center_v")

        self._fields["radius"].set_input_parser(self.__parse_radius_input)
        self._fields["segments"].set_input_parser(self.__parse_segments_input)

        section.add((0, 5))

        text = "Smooth"
        checkbox = PanelCheckButton(section, lambda val:
            self.__handle_value("smoothness", val), text)
        checkbox.check(True)
        self._checkbuttons["smoothness"] = checkbox
        section.add(checkbox)

    def setup(self): pass

    def __handle_value(self, value_id, value, state):

        if GlobalData["active_creation_type"]:
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

        color = (1., 1., 0., 1.)

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

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        if multi_sel:
            self._checkbuttons["smoothness"].check(False)

        for field in self._fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)

        self._checkbuttons["smoothness"].set_checkmark_color(color)


ObjectTypes.add_type("sphere", "Sphere")
PropertyPanel.add_properties("sphere", SphereProperties)
