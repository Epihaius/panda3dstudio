from .base import *


class PlaneProperties(object):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._segments_default = {"x": 1, "y": 1}

        section = panel.add_section("plane_props", "Plane properties", hidden=True)

        axes = "xy"
        dimensions = ("length", "width")
        prop_types = ("size", "segments")
        val_types = ("float", "int")
        parsers = (self.__parse_dimension, self.__parse_segments)

        for prop_type, val_type, parser in zip(prop_types, val_types, parsers):

            group = section.add_group(prop_type.title())
            sizer = GridSizer(rows=0, columns=2, gap_h=5, gap_v=2)
            group.add(sizer, expand=True)

            for axis, dim in zip(axes, dimensions):
                prop_id = "{}_{}".format(prop_type, axis)
                text = "{} ({}):".format(axis.upper(), dim)
                sizer.add(PanelText(group, text), alignment_v="center_v")
                field = PanelInputField(group, 80)
                field.add_value(prop_id, val_type, handler=self.__handle_value)
                field.show_value(prop_id)
                field.set_input_parser(prop_id, parser)
                self._fields[prop_id] = field
                sizer.add(field, proportion_h=1., alignment_v="center_v")

    def setup(self): pass

    def __handle_value(self, value_id, value):

        in_creation_mode = GlobalData["active_creation_type"]

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

    def __parse_dimension(self, dimension):

        try:
            return max(.001, abs(float(eval(dimension))))
        except:
            return None

    def __parse_segments(self, segments):

        try:
            return max(1, abs(int(eval(segments))))
        except:
            return None

    def get_base_type(self):

        return "primitive"

    def get_section_ids(self):

        return ["plane_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = (1., 1., 0., 1.)

        if prop_id == "segments":
            self._segments_default.update(value)
            for axis in "xy":
                value_id = "segments_" + axis
                field = self._fields[value_id]
                field.show_text()
                field.set_value(value_id, value[axis])
                field.set_text_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(prop_id, value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if not (prop_id == "segments" or prop_id in self._fields):
            return

        if prop_id == "segments":
            for axis in "xy":
                value_id = "segments_" + axis
                field = self._fields[value_id]
                field.set_value(value_id, value[axis])
        else:
            field = self._fields[prop_id]
            field.set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        for field in self._fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)


ObjectTypes.add_type("plane", "Plane")
PropertyPanel.add_properties("plane", PlaneProperties)
