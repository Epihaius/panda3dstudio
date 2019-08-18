from .base import *


class DummyProperties:

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}

        section = panel.add_section("dummy_props", "Dummy helper properties", hidden=True)

        get_handler = lambda geom_type: lambda val: self.__handle_viz(geom_type, val)

        for geom_type in ("box", "cross"):
            text = f"Show {geom_type}"
            checkbtn = PanelCheckButton(section, get_handler(geom_type), text)
            self._checkbuttons[f"{geom_type}_viz"] = checkbtn
            section.add(checkbtn)
            section.add((0, 5))

        sizer = GridSizer(rows=0, columns=3, gap_h=5, gap_v=2)
        section.add(sizer, expand=True)

        text = "Box size:"
        sizer.add(PanelText(section, text), alignment_v="center_v")
        prop_id = "size"
        field = PanelInputField(section, prop_id, "float", self.__handle_value, 80)
        field.set_input_parser(self.__parse_size_input)
        self._fields[prop_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")
        sizer.add((0, 0))

        text = "Cross size:"
        sizer.add(PanelText(section, text), alignment_v="center_v")
        prop_id = "cross_size"
        field = PanelInputField(section, prop_id, "float", self.__handle_value, 80)
        field.set_input_parser(self.__parse_size_input)
        self._fields[prop_id] = field
        sizer.add(field, proportion_h=1., alignment_v="center_v")
        text = "%"
        sizer.add(PanelText(section, text), alignment_v="center_v")

        section.add((0, 5))

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)
        prop_id = "const_size_state"
        get_handler = lambda prop_id: lambda val: self.__handle_value(prop_id, val)
        text = "Const. screen size:"
        checkbtn = PanelCheckButton(section, get_handler(prop_id), text)
        self._checkbuttons[prop_id] = checkbtn
        borders = (0, 5, 0, 0)
        sizer.add(checkbtn, alignment="center_v", borders=borders)
        prop_id = "const_size"
        field = PanelInputField(section, prop_id, "float", self.__handle_value, 40)
        field.set_value_parser(lambda value: f"{value :.1f}")
        field.set_input_parser(self.__parse_size_input)
        self._fields[prop_id] = field
        sizer.add(field, proportion=1., alignment="center_v")

        section.add((0, 5))

        prop_id = "on_top"
        text = "Draw on top"
        checkbtn = PanelCheckButton(section, get_handler(prop_id), text)
        self._checkbuttons[prop_id] = checkbtn
        section.add(checkbtn)

    def setup(self): pass

    def __handle_value(self, value_id, value, state="done"):

        if GD["active_creation_type"]:
            Mgr.update_app("dummy_prop_default", value_id, value)
            return

        Mgr.update_remotely("selected_obj_prop", value_id, value)

    def __handle_viz(self, geom_type, shown):

        other_geom_type = "cross" if geom_type == "box" else "box"
        other_shown = self._checkbuttons[f"{other_geom_type}_viz"].is_checked()

        if not shown and not other_shown:
            self._checkbuttons[f"{other_geom_type}_viz"].check()
            other_shown = True

        viz = set()

        if shown:
            viz.add(geom_type)

        if other_shown:
            viz.add(other_geom_type)

        if GD["active_creation_type"]:
            Mgr.update_app("dummy_prop_default", "viz", viz)
            return

        Mgr.update_remotely("selected_obj_prop", "viz", viz)

    def __parse_size_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None

    def get_base_type(self):

        return "helper"

    def get_section_ids(self):

        return ["dummy_props"]

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = (1., 1., 0., 1.)
        checkbtns = self._checkbuttons

        if prop_id == "viz":
            for geom_type in ("box", "cross"):
                check_id = f"{geom_type}_viz"
                checkbtns[check_id].check(True if geom_type in value else False)
                checkbtns[check_id].set_checkmark_color(color)
        elif prop_id in checkbtns:
            checkbtns[prop_id].check(value)
            checkbtns[prop_id].set_checkmark_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        checkbtns = self._checkbuttons
        fields = self._fields

        if prop_id == "viz":
            for geom_type in ("box", "cross"):
                check_id = f"{geom_type}_viz"
                checkbtns[check_id].check(True if geom_type in value else False)
        elif prop_id in checkbtns:
            checkbtns[prop_id].check(value)
        elif prop_id in fields:
            fields[prop_id].set_value(value)

    def check_selection_count(self):

        checkbtns = self._checkbuttons
        fields = self._fields

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        for checkbtn in checkbtns.values():
            checkbtn.set_checkmark_color(color)

        for field in fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)


ObjectTypes.add_type("dummy", "Dummy Helper")
PropertyPanel.add_properties("dummy", DummyProperties)
