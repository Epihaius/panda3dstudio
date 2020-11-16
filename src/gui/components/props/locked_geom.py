from .base import *


class LockedGeomProperties:

    def __init__(self, panel, widgets):

        self._panel = panel
        self._fields = {}
        self._checkbuttons = {}

        checkbtn = widgets["checkbuttons"]["normal_viz"]
        checkbtn.command = lambda on: Mgr.update_remotely("normal_viz", on)
        self._checkbuttons["normal_viz"] = checkbtn

        colorbox = widgets["colorboxes"]["locked_geom_normal"]
        colorbox.command = self.__handle_color
        self._colorbox = colorbox

        val_id = "normal_length"
        field = widgets["fields"]["locked_geom_normal_length"]
        field.value_id = val_id
        field.set_input_parser(self.__parse_length_input)
        field.set_value_handler(self.__handle_value)
        field.set_value_range((.001, None), False, "float")
        field.set_step(.01)
        self._fields[val_id] = field

        self._uv_set_btns = uv_set_btns = ToggleButtonGroup()

        def set_active_uv_set(uv_set_id):

            self._uv_set_btns.set_active_button(str(uv_set_id))
            Mgr.update_remotely("uv_set_id")

        for i in range(8):
            btn = widgets["buttons"][f"locked_geom_uv_set_{i}"]
            command = lambda set_id=i: set_active_uv_set(set_id)
            toggle = (command, lambda: None)
            uv_set_btns.add_button(btn, str(i), toggle)

        uv_set_btns.set_active_button("0")

        val_id = "uv_set_name"
        field = widgets["fields"]["locked_geom_uv_set_name"]
        field.value_id = val_id
        field.value_type = "string"
        field.set_value_handler(self.__handle_uv_name)
        field.clear()
        field.set_input_parser(self.__parse_uv_name)
        self._fields[val_id] = field

        Mgr.add_app_updater("uv_set_name", self.__set_uv_name)

    def setup(self):

        self._panel.get_section("locked_geom_props").expand(False)

    def get_base_type(self):

        return "locked_geom"

    def get_section_ids(self):

        return ["locked_geom_props"] + self.get_extra_section_ids()

    def get_extra_section_ids(self):

        return []

    def set_object_property_default(self, prop_id, value):

        color = Skin.colors["default_value"]

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
            color = Skin.text["input_disabled"]["color"] if multi_sel else value
            self._colorbox.color = color[:3]
        elif prop_id in self._checkbuttons:
            self._checkbuttons[prop_id].check(value)
        elif prop_id in self._fields:
            self._fields[prop_id].set_value(value)

    def check_selection_count(self):

        sel_count = GD["selection_count"]
        multi_sel = sel_count > 1
        color = Skin.text["input_disabled"]["color"] if multi_sel else None

        if multi_sel:

            for checkbtn in self._checkbuttons.values():
                checkbtn.check(False)

            self._colorbox.color = color[:3]

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


PropertyPanel.add_properties("locked_geom", LockedGeomProperties)
