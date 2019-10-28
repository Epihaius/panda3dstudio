from .base import *


class BasicGeomProperties:

    def __init__(self, panel):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}

        section = panel.add_section("basic_geom_props", "Basic properties", hidden=True)

        group = section.add_group("UV set names")

        self._uv_set_btns = uv_set_btns = ToggleButtonGroup()

        def set_active_uv_set(uv_set_id):

            self._uv_set_btns.set_active_button(str(uv_set_id))
            Mgr.update_remotely("uv_set_id")

        get_command = lambda i: lambda: set_active_uv_set(i)

        sizer = GridSizer(rows=0, columns=4, gap_h=5, gap_v=5)
        borders = (5, 5, 5, 5)
        group.add(sizer, expand=True, borders=borders)

        for i in range(8):
            text = str(i)
            tooltip_text = f"UV set {i}"
            btn = PanelButton(group, text, "", tooltip_text)
            toggle = (get_command(i), lambda: None)
            uv_set_btns.add_button(btn, str(i), toggle)
            sizer.add(btn, proportion_h=1.)

        uv_set_btns.set_active_button("0")

        borders = (0, 5, 0, 0)

        group.add((0, 10))
        val_id = "uv_set_name"
        field = PanelInputField(group, val_id, "string", self.__handle_uv_name, 140)
        field.clear()
        field.set_input_parser(self.__parse_uv_name)
        self._fields[val_id] = field
        group.add(field, expand=True)

        group = section.add_group("Vertex normals")

        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        command = lambda on: Mgr.update_remotely("normal_viz", on)
        text = "Show"
        checkbtn = PanelCheckButton(group, command, text)
        self._checkbuttons["normal_viz"] = checkbtn
        sizer.add(checkbtn, alignment="center_v")
        sizer.add((0, 0), proportion=1.)
        self._colorbox = colorbox = PanelColorBox(group, self.__handle_color)
        sizer.add(colorbox, alignment="center_v")
        sizer.add((0, 0), proportion=1.)

        sizer = Sizer("horizontal")
        group.add(sizer, expand=True)

        text = "Length:"
        sizer.add(PanelText(group, text), alignment="center_v", borders=borders)
        val_id = "normal_length"
        field = PanelSpinnerField(group, val_id, "float", (.001, None), .01,
                                  self.__handle_value, 80)
        field.set_input_parser(self.__parse_length_input)
        self._fields[val_id] = field
        sizer.add(field, alignment="center_v")

        Mgr.add_app_updater("uv_set_name", self.__set_uv_name)

    def setup(self):

        self._panel.get_section("basic_geom_props").expand(False)

    def get_base_type(self):

        return "basic_geom"

    def get_section_ids(self):

        return ["basic_geom_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = (1., 1., 0., 1.)

        if prop_id in self._checkbuttons:
            self._checkbuttons[prop_id].check(value)
            self._checkbuttons[prop_id].set_checkmark_color(color)
        elif prop_id in self._fields:
            field = self._fields[prop_id]
            field.show_text()
            field.set_value(value)
            field.set_text_color(color)

    def set_object_property(self, prop_id, value):

        if prop_id == "uv_set_names":
            if GD["selection_count"] == 1:
                self.__set_uv_name(value)
        elif prop_id == "normal_color":
            multi_sel = GD["selection_count"] > 1
            gray = (.5, .5, .5)
            color = gray if multi_sel else value[:3]
            self._colorbox.set_color(color)
        elif prop_id in self._checkbuttons:
            self._checkbuttons[prop_id].check(value)
        elif prop_id in self._fields:
            self._fields[prop_id].set_value(value)

    def check_selection_count(self):

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = (.5, .5, .5, 1.) if multi_sel else None

        if multi_sel:

            for checkbtn in self._checkbuttons.values():
                checkbtn.check(False)

            self._colorbox.set_color(color[:3])

        for checkbtn in self._checkbuttons.values():
            checkbtn.set_checkmark_color(color)

        for field in self._fields.values():
            field.set_text_color(color)
            field.show_text(not multi_sel)

    def __handle_uv_name(self, value_id, value, state="done"):

        uv_set_id = int(self._uv_set_btns.get_active_button_id())
        Mgr.update_remotely(value_id, uv_set_id, value)

    def __handle_color(self, color):

        r, g, b = color
        Mgr.update_remotely("normal_color", (r, g, b, 1.))

    def __handle_value(self, value_id, value, state="done"):

        Mgr.update_remotely(value_id, value, state)

    def __parse_uv_name(self, input_text):

        name = input_text.strip().replace(".", "")

        return name

    def __set_uv_name(self, uv_set_names):

        uv_set_id = int(self._uv_set_btns.get_active_button_id())
        uv_set_name = uv_set_names[uv_set_id]
        self._fields["uv_set_name"].set_value(uv_set_name)

    def __parse_length_input(self, input_text):

        try:
            return max(.001, abs(float(eval(input_text))))
        except:
            return None


PropertyPanel.add_properties("basic_geom", BasicGeomProperties)
