from .base import *


class PointProperties(object):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkboxes = {}
        self._colorboxes = {}

        section = panel.add_section("point_props", "Point helper properties", hidden=True)

        borders = (0, 5, 0, 0)

        sizer = Sizer("horizontal")
        section.add(sizer)
        text = "Size:"
        sizer.add(PanelText(section, text), alignment="center_v", borders=borders)
        prop_id = "size"
        field = PanelInputField(section, 45)
        field.add_value(prop_id, "int", handler=self.__handle_value)
        field.show_value(prop_id)
        field.set_input_parser("size", self.__parse_size)
        self._fields[prop_id] = field
        sizer.add(field, alignment="center_v")

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer)
        prop_id = "on_top"
        checkbox = PanelCheckBox(section, self.__draw_on_top)
        self._checkboxes[prop_id] = checkbox
        sizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Draw on top"
        sizer.add(PanelText(section, text), alignment="center_v")

        section.add((0, 5))

        group = section.add_group("Color")
        sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
        group.add(sizer, expand=True)
        text = "Unselected:"
        sizer.add(PanelText(section, text), alignment_v="center_v")
        title = "Pick unselected point color"
        colorbox = PanelColorBox(group, lambda col: self.__handle_color("unselected", col),
                                 dialog_title=title)
        self._colorboxes["unselected_color"] = colorbox
        sizer.add(colorbox, alignment_v="center_v")

        text = "Selected:"
        sizer.add(PanelText(section, text), alignment_v="center_v")
        title = "Pick selected point color"
        colorbox = PanelColorBox(group, lambda col: self.__handle_color("selected", col),
                                 dialog_title=title)
        self._colorboxes["selected_color"] = colorbox
        sizer.add(colorbox, alignment_v="center_v")

    def setup(self): pass

    def __handle_value(self, value_id, value):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("point_helper_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

    def __draw_on_top(self, on_top):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("point_helper_prop_default", "on_top", on_top)
            return

        Mgr.update_remotely("selected_obj_prop", "on_top", on_top)

    def __parse_size(self, size):

        try:
            return max(1, abs(int(eval(size))))
        except:
            return None

    def __handle_color(self, sel_state, color):

        r, g, b = color
        prop_id = "{}_color".format(sel_state)

        if GlobalData["active_creation_type"]:
            Mgr.update_remotely("point_helper_prop_default", prop_id, (r, g, b, 1.))
            self.set_object_property_default(prop_id, color)
            return

        Mgr.update_remotely("selected_obj_prop", prop_id, (r, g, b, 1.))

    def get_base_type(self):

        return "helper"

    def get_section_ids(self):

        return ["point_props"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = (1., 1., 0., 1.)
        fields = self._fields
        checkboxes = self._checkboxes
        colorboxes = self._colorboxes

        if prop_id in fields:
            field = fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)
        elif prop_id in checkboxes:
            checkboxes[prop_id].check(value)
            checkboxes[prop_id].set_checkmark_color(color)
        elif prop_id in colorboxes:
            colorboxes[prop_id].set_color(value[:3])

    def set_object_property(self, prop_id, value):

        fields = self._fields
        checkboxes = self._checkboxes
        colorboxes = self._colorboxes

        if prop_id in fields:
            fields[prop_id].set_value(prop_id, value)
        elif prop_id in checkboxes:
            checkboxes[prop_id].check(value)
        elif prop_id in colorboxes:
            colorboxes[prop_id].set_color(value[:3])

    def check_selection_count(self):

        checkboxes = self._checkboxes
        fields = self._fields

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        for checkbox in checkboxes.itervalues():
            checkbox.set_checkmark_color(color)

        for field in fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)


ObjectTypes.add_type("point_helper", "Point Helper")
PropertyPanel.add_properties("point_helper", PointProperties)
