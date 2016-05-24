from .base import *


class BoxProperties(BaseObject):

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}

        section = panel.add_section("box_props", "Box properties")

        axes = "xyz"
        dimensions = ("width", "depth", "height")
        prop_types = ("size", "segments")
        val_types = ("float", "int")
        parsers = (self.__parse_dimension, self.__parse_segments)
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        for prop_type, val_type, parser in zip(prop_types, val_types, parsers):

            group = section.add_group(prop_type.title())
            sizer = group.get_client_sizer()
            subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
            sizer.Add(subsizer)

            for axis, dim in zip(axes, dimensions):
                prop_id = "%s_%s" % (prop_type, axis)
                group.add_text("%s (%s):" % (axis.upper(), dim), subsizer, sizer_args)
                field = PanelInputField(panel, group, subsizer, 80)
                field.add_value(prop_id, val_type, handler=self.__handle_value)
                field.show_value(prop_id)
                self._fields[prop_id] = field
                field.set_input_parser(prop_id, parser)

        self._fields["size_z"].set_input_parser("size_z", self.__parse_height)

    def __handle_value(self, value_id, value):

        if GlobalData["active_creation_type"]:
            Mgr.update_app("box_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

    def __parse_dimension(self, dimension):

        try:
            return max(.001, abs(float(eval(dimension))))
        except:
            return None

    def __parse_height(self, height):

        try:
            value = float(eval(height))
        except:
            return None

        sign = -1. if value < 0. else 1.

        return max(.001, abs(value)) * sign

    def __parse_segments(self, segments):

        try:
            return max(1, abs(int(eval(segments))))
        except:
            return None

    def get_base_type(self):

        return "primitive"

    def get_section_ids(self):

        return ["box_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        field = self._fields[prop_id]
        field.show_text()
        field.set_value(prop_id, value)
        field.set_text_color(wx.Colour(255, 255, 0))

    def set_object_property(self, prop_id, value):

        if prop_id not in self._fields:
            return

        field = self._fields[prop_id]
        field.set_value(prop_id, value)

    def check_selection_count(self):

        sel_count = GlobalData["selection_count"]
        multi_sel = sel_count > 1
        color = wx.Colour(127, 127, 127) if multi_sel else None

        for field in self._fields.itervalues():
            field.set_text_color(color)
            field.show_text(not multi_sel)


ObjectTypes.add_type("box", "Box")
PropertyPanel.add_properties("box", BoxProperties)
