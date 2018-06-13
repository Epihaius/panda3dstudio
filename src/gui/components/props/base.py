from ...base import *
from ...panel import *
from ...button import *


class ObjectTypes(object):

    _types = {}

    @classmethod
    def add_type(cls, obj_type_id, obj_type_name):

        cls._types[obj_type_id] = obj_type_name

    @classmethod
    def get_types(cls):

        return cls._types


class PropertyPanel(Panel):

    _property_classes = {}
    _properties = {}

    @classmethod
    def add_properties(cls, obj_type, properties):

        cls._property_classes[obj_type] = properties

    def __init__(self, stack):

        Panel.__init__(self, stack, "obj_props", "Object properties")

        self._obj_types = ()
        self._sel_obj_types = ()
        self._sel_obj_count = 0

        self._colors = {
            "disabled": (.5, .5, .5, 1.),
            "custom": (1., 1., 0., 1.)
        }
        self._checkboxes = {}
        self._radio_btns = {}
        self._comboboxes = {}

        # ************************* Selection section **************************

        section = self.add_section("selection", "Selection")

        group = section.add_group("Choice from name box")
        radio_btns = PanelRadioButtonGroup(group, columns=1)
        radio_btns.add_button("deselect", "Deselect")
        radio_btns.add_button("deselect_others", "Deselect others")
        radio_btns.add_button("center", "Center in view")
        radio_btns.set_selected_button("deselect_others")
        group.add(radio_btns.get_sizer())
        self._radio_btns["selection"] = radio_btns

        # **************************** ID section ******************************

        section = self.add_section("id", "Name and color")

        sizer = Sizer("horizontal")
        section.add(sizer, expand=True)

        combobox = PanelComboBox(section, 120, tooltip_text="Selected object(s)", editable=True)
        combobox.add_disabler("creating", lambda: GlobalData["active_creation_type"])
        combobox.enable(False)
        val_id = "name"
        self._comboboxes[val_id] = combobox
        borders = (5, 10, 0, 0)
        sizer.add(combobox, proportion=1., alignment="center_v", borders=borders)
        field = combobox.get_input_field()
        field.add_value(val_id, "string", handler=self.__handle_value)
        field.set_input_init(val_id, self.__init_input)
        field.show_value(val_id)
        field.show_text(False)
        field.enable(False)
        field.set_input_parser(val_id, self.__parse_object_name)
        self._name_field = field

        title = "Pick object color"
        self._colorbox = colorbox = PanelColorBox(section, self.__handle_color, dialog_title=title)
        colorbox.set_color_type("")
        colorbox.enable(False)
        borders = (0, 5, 0, 0)
        sizer.add(colorbox, alignment="center_v", borders=borders)

        # ************************* Creation section ***************************

        section = self.add_section("create", "Creation", hidden=True)

        group = section.add_group("Position")
        color = (1., 1., 0., 1.)
        radio_btns = PanelRadioButtonGroup(group, bullet_color=color, columns=1)
        radio_btns.add_button("grid_pos", "Coord. system origin")
        radio_btns.add_button("cam_target_pos", "Camera target")
        radio_btns.set_selected_button("grid_pos")
        self._radio_btns["creation"] = radio_btns
        group.add(radio_btns.get_sizer())

        text = "Create object"
        btn = PanelButton(section, text, command=self.__create_object)
        borders = (0, 0, 0, 10)
        section.add(btn, alignment="center_h", borders=borders)

        for obj_type, prop_cls in self._property_classes.items():
            self._properties[obj_type] = prop_cls(self)

        # ********************** Surface properties section ********************

        section = self.add_section("surface_props", "Surface properties", hidden=True)

        subsizer = Sizer("horizontal")
        borders = (0, 0, 0, 4)
        section.add(subsizer, alignment="center_h", borders=borders)

        command = lambda on: Mgr.update_remotely("normal_flip", on)
        checkbox = PanelCheckBox(section, command)
        checkbox.check(False)
        self._checkboxes["normal_flip"] = checkbox
        borders = (2, 2, 2, 2)
        subsizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Invert (render inside-out)"
        subsizer.add(PanelText(section, text), alignment="center_v", borders=borders)

        section.add((0, 8))

        group = section.add_group("Tangent space")
        subsizer = Sizer("horizontal")
        group.add(subsizer)
        command = lambda on: Mgr.update_remotely("tangent_flip", on)
        checkbox = PanelCheckBox(group, command)
        checkbox.check(False)
        self._checkboxes["tangent_flip"] = checkbox
        borders = (0, 5, 0, 0)
        subsizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Flip tangent vectors"
        subsizer.add(PanelText(group, text), alignment="center_v")
        subsizer = Sizer("horizontal")
        group.add(subsizer)
        command = lambda on: Mgr.update_remotely("bitangent_flip", on)
        checkbox = PanelCheckBox(group, command)
        checkbox.check(False)
        self._checkboxes["bitangent_flip"] = checkbox
        borders = (0, 5, 0, 0)
        subsizer.add(checkbox, alignment="center_v", borders=borders)
        text = "Flip bitangent vectors"
        subsizer.add(PanelText(group, text), alignment="center_v")

        # **********************************************************************

        bottom_container = self.get_bottom_container()
        text = "Unlock geometry"
        tooltip_text = "Enable subobject editing"
        command = self.__unlock_geometry
        btn = PanelButton(bottom_container, text, "", tooltip_text, command)
        borders = (10, 10, 10, 10)
        bottom_container.add(btn, alignment="center_h", borders=borders)

        def set_obj_prop(obj_type, prop_id, value):

            if GlobalData["active_creation_type"] != "":
                return

            if prop_id in self._checkboxes:
                self._checkboxes[prop_id].check(value)
            elif obj_type:
                self._properties[obj_type].set_object_property(prop_id, value)

        def set_obj_prop_default(obj_type, prop_id, value):

            if obj_type:
                self._properties[obj_type].set_object_property_default(prop_id, value)

        Mgr.add_app_updater("selected_obj_types", self.__show)
        Mgr.add_app_updater("selected_obj_prop", set_obj_prop)
        Mgr.add_app_updater("obj_prop_default", set_obj_prop_default)
        Mgr.add_app_updater("interactive_creation", self.__update_sections)
        Mgr.add_app_updater("selected_obj_names", self.__set_object_names)
        Mgr.add_app_updater("selected_obj_color", self.__set_object_color)
        Mgr.add_app_updater("selection_count", self.__check_selection_count)
        Mgr.add_app_updater("sel_color_count", self.__check_selection_color_count)
        Mgr.add_app_updater("next_obj_name", self.__set_next_object_name)
        Mgr.accept("display_next_obj_color", self.__set_next_object_color)

    def setup(self):

        for props in self._properties.values():
            props.setup()

        self.get_section("selection").expand(False)
        self.get_section("create").expand(False)
        self.get_section("surface_props").expand(False)
        self.show_container("bottom", False)

    def __unlock_geometry(self):

        Mgr.update_remotely("geometry_access")

    def __update_sections(self, creation_status):

        obj_types = self._sel_obj_types
        obj_type = obj_types[0] if len(obj_types) == 1 else ""
        props = self._properties[obj_type] if obj_type else None
        extra_section_ids = props.get_extra_section_ids() if props else []

        if creation_status == "started":

            self.get_section("create").show()
            self.show_container("bottom", False)
            self.get_section("surface_props").hide()

            for section_id in extra_section_ids:
                self.get_section(section_id).hide()

        elif creation_status == "ended":

            if self._sel_obj_count == 1:
                for section_id in extra_section_ids:
                    self.get_section(section_id).show()

            props = self._properties
            base_types = set(props[o_type].get_base_type() for o_type in obj_types)

            if base_types and not base_types - set(["primitive", "basic_geom"]):
                self.show_container("bottom")

            if base_types and not base_types - set(["primitive", "editable_geom", "basic_geom"]):
                self.get_section("surface_props").show()

            self.get_section("create").hide()

    def __init_input(self):

        if self._name_field.get_text_color() == self._colors["disabled"]:
            self._name_field.clear()

    def __handle_value(self, value_id, value):

        if GlobalData["active_creation_type"]:
            obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""
            Mgr.update_remotely("custom_obj_name", obj_type, value)
        else:
            Mgr.update_remotely("selected_obj_name", value)

    def __parse_object_name(self, name):

        parsed_name = name.strip()

        if GlobalData["active_creation_type"]:
            return parsed_name

        return parsed_name if parsed_name else None

    def __update_selection(self, obj_id):

        radio_btn_id = self._radio_btns["selection"].get_selected_button()

        if radio_btn_id == "deselect":
            Mgr.update_remotely("object_selection", obj_id, "remove")
        elif radio_btn_id == "deselect_others":
            Mgr.update_remotely("object_selection", obj_id, "replace")
        elif radio_btn_id == "center":
            Mgr.update_remotely("view", "center", False, None, obj_id)

    def __set_object_names(self, names):

        if GlobalData["active_creation_type"]:
            return

        combobox = self._comboboxes["name"]
        combobox.clear()

        if not names:
            self._name_field.show_text(False)
            return

        count = len(names)

        if count > 1:
            name = "{:d} Objects selected".format(count)
            combobox.add_item(None, name, lambda: None)

        get_command = lambda obj_id: lambda: self.__update_selection(obj_id)

        for obj_id, name in names.items():
            combobox.add_item(obj_id, name, get_command(obj_id))

        if count == 1:
            name = names.popitem()[1]
        else:
            name = "{:d} Objects selected".format(count)

        combobox.update_popup_menu()
        self._name_field.set_value("name", name, handle_value=False)
        self._name_field.show_text()

    def __set_next_object_name(self, name):

        self._name_field.enable(ignore_parent=True)
        self._name_field.set_text_color(self._colors["custom"])
        self._name_field.set_value("name", name, handle_value=False)
        self._name_field.show_text()

    def __handle_color(self, color):

        r, g, b = color

        if GlobalData["active_creation_type"]:
            obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""
            GlobalData["next_{}_color".format(obj_type)] = color
        else:
            Mgr.update_remotely("selected_obj_color", color)

    def __set_object_color(self, color):

        if GlobalData["active_creation_type"] != "":
            return

        self._colorbox.set_color(color[:3])

    def __set_next_object_color(self):

        obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""

        if not obj_type or obj_type == "editable_geom":
            return

        next_color = GlobalData["next_{}_color".format(obj_type)]
        self._colorbox.enable(True if next_color else False)
        self._colorbox.set_color_type("single" if next_color else "")

        if next_color:
            self._colorbox.set_color(next_color)

    def __check_selection_count(self, on_enable=False):

        if GlobalData["active_creation_type"] != "" or GlobalData["temp_toplevel"]:
            return

        self._sel_obj_count = sel_count = GlobalData["selection_count"]

        if GlobalData["active_obj_level"] == "top":

            multi_sel = sel_count > 1
            color = self._colors["disabled"] if multi_sel else None

            if not on_enable:

                if multi_sel:
                    for checkbox in self._checkboxes.values():
                        checkbox.check(False)

                for checkbox in self._checkboxes.values():
                    checkbox.set_checkmark_color(color)

            self._comboboxes["name"].enable(sel_count > 0)
            self._name_field.enable(sel_count > 0)
            self._name_field.show_text(sel_count > 0)
            self._name_field.set_text_color(color)

        else:

            self._name_field.enable(False)
            self._comboboxes["name"].enable(False)

        obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""

        if obj_type:

            if not on_enable:
                self._properties[obj_type].check_selection_count()

            extra_section_ids = self._properties[obj_type].get_extra_section_ids()

            if extra_section_ids:

                if sel_count > 1:
                    for section_id in extra_section_ids:
                        self.get_section(section_id).hide()
                else:
                    for section_id in extra_section_ids:
                        self.get_section(section_id).show()

    def __check_selection_color_count(self):

        if GlobalData["active_creation_type"] != "":
            return

        if GlobalData["active_obj_level"] == "top":
            count = GlobalData["sel_color_count"]
            self._colorbox.enable(count > 0)
            self._colorbox.set_color_type(("single" if count == 1 else "multi")
                                          if count > 0 else "")
        else:
            self._colorbox.enable(False)

    def __create_object(self):

        pos_id = self._radio_btns["creation"].get_selected_button()
        Mgr.update_app("creation", pos_id)
        self.__set_next_object_color()

    def get_active_object_type(self):

        obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""

        return obj_type

    def enable(self, enable=True):

        if not Panel.enable(self, enable):
            return

        if GlobalData["active_creation_type"]:
            self._name_field.enable()
            self._colorbox.enable()
        else:
            self.__check_selection_count(on_enable=True)
            self.__check_selection_color_count()

    def get_width(self):

        return self._width

    def get_client_width(self):

        return self._width - self.get_client_offset() * 2

    def __show(self, obj_types):

        creation_type = GlobalData["active_creation_type"]
        new_types = set([creation_type]) if creation_type else set(obj_types)

        if creation_type:
            self._comboboxes["name"].enable(False)

        obj_type = obj_types[0] if len(obj_types) == 1 else ""
        props = self._properties

        if (obj_type and obj_type not in props) or set(self._obj_types) == new_types:
            return

        prev_obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""
        prev_section_ids = props[prev_obj_type].get_section_ids() if prev_obj_type else []
        next_section_ids = props[obj_type].get_section_ids() if obj_type else []
        extra_section_ids = props[obj_type].get_extra_section_ids() if obj_type else []

        in_creation_mode = creation_type != ""

        for section_id in next_section_ids:
            self.get_section(section_id).show()

        base_types = set(props[o_type].get_base_type() for o_type in obj_types)

        if base_types and not base_types - set(["primitive", "basic_geom"]):
            self.show_container("bottom")
        else:
            self.show_container("bottom", False)

        if base_types and not base_types - set(["primitive", "editable_geom", "basic_geom"]):
            self.get_section("surface_props").show()
        else:
            self.get_section("surface_props").hide()

        if in_creation_mode:

            self.show_container("bottom", False)
            self.get_section("surface_props").hide()

            for section_id in extra_section_ids:
                self.get_section(section_id).hide()

        for section_id in prev_section_ids:
            self.get_section(section_id).hide()

        self._obj_types = obj_types

        if in_creation_mode:
            self._colorbox.set_color_type("single")
            self.__set_next_object_color()

        self._sel_obj_types = obj_types
