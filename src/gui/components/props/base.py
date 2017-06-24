from ...base import *
from ...panel import *


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

    def __init__(self, parent):

        Panel.__init__(self, parent, "Object properties")

        self._obj_types = ()
        self._sel_obj_types = ()
        self._sel_obj_count = 0
        self._parent = parent
        self._width = parent.get_width()

        self._colors = {
            "disabled": wx.Colour(127, 127, 127),
            "custom": wx.Colour(255, 255, 0)
        }
        self._checkboxes = {}
        self._radio_btns = {}
        self._comboboxes = {}

        self.GetSizer().SetMinSize(wx.Size(self._width, 1))
        self._parent.GetSizer().Add(self)

        # ************************* Selection section **************************

        sel_section = section = self.add_section("selection", "Selection")

        radio_btns = PanelRadioButtonGroup(self, section, "Choice from name box")
        radio_btns.add_button("deselect", "Deselect")
        radio_btns.add_button("deselect_others", "Deselect others")
        radio_btns.add_button("center", "Center in view")
        radio_btns.set_selected_button("deselect_others")
        self._radio_btns["selection"] = radio_btns

        # **************************** ID section ******************************

        id_section = section = self.add_section("id", "Name and color")
        section_sizer = section.get_client_sizer()
        sizer = wx.BoxSizer()
        section_sizer.Add(sizer)

        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)
        combobox = EditablePanelComboBox(self, section, sizer, "Selected object(s)", 130,
                                         sizer_args=sizer_args)
        combobox.add_disabler("creating", lambda: GlobalData["active_creation_type"])
        combobox.enable(False)
        val_id = "name"
        self._comboboxes[val_id] = combobox
        field = combobox.get_input_field()
        field.add_value(val_id, "string", handler=self.__handle_value)
        field.set_input_init(val_id, self.__init_input)
        field.show_value(val_id)
        field.show_text(False)
        field.enable(False)
        field.set_input_parser(val_id, self.__parse_object_name)
        self._name_field = field
        sizer.Add((5, 0))
        self._color_picker = PanelColorPickerCtrl(self, section, sizer, self.__handle_color,
                                                  sizer_args=sizer_args)
        self._color_picker.show_color("none")
        self._color_picker.Enable(False)

        # ************************* Creation section ***************************

        create_section = section = self.add_section("create", "Creation")

        yellow = wx.Colour(255, 255, 0)
        radio_btns = PanelRadioButtonGroup(self, section, "Position", dot_color=yellow)
        radio_btns.add_button("grid_pos", "Coord. system origin")
        radio_btns.add_button("cam_target_pos", "Camera target")
        radio_btns.set_selected_button("grid_pos")
        self._radio_btns["creation"] = radio_btns

        sizer = section.get_client_sizer()

        bitmap_paths = PanelButton.get_bitmap_paths("panel_button")

        label = "Create object"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        sizer_args = (0, wx.ALIGN_CENTER_HORIZONTAL)
        btn = PanelButton(self, section, sizer, bitmaps, label, "",
                          self.__create_object, sizer_args)

        for obj_type, prop_cls in self._property_classes.iteritems():
            self._properties[obj_type] = prop_cls(self)

        # ********************** Surface properties section ********************

        surface_section = section = self.add_section("surface_props", "Surface properties")
        sizer = section.get_client_sizer()

        sizer.Add(wx.Size(0, 4))

        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        subsizer = wx.BoxSizer()
        sizer.Add(subsizer, 0, wx.ALIGN_CENTER_HORIZONTAL)
        command = lambda on: Mgr.update_remotely("normal_flip", on)
        checkbox = PanelCheckBox(self, self, subsizer, command, sizer_args=sizer_args)
        checkbox.check(False)
        self._checkboxes["normal_flip"] = checkbox
        section.add_text("Invert (render inside-out)", subsizer, sizer_args)

        sizer.Add(wx.Size(0, 8))

        group = section.add_group("Tangent space")
        grp_sizer = group.get_client_sizer()
        sizer_args = (0, wx.ALIGN_CENTER_VERTICAL)

        subsizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)
        grp_sizer.Add(subsizer)
        command = lambda on: Mgr.update_remotely("tangent_flip", on)
        checkbox = PanelCheckBox(self, group, subsizer, command)
        checkbox.check(False)
        self._checkboxes["tangent_flip"] = checkbox
        group.add_text("Flip tangent vectors", subsizer, sizer_args)
        command = lambda on: Mgr.update_remotely("bitangent_flip", on)
        checkbox = PanelCheckBox(self, group, subsizer, command)
        checkbox.check(False)
        self._checkboxes["bitangent_flip"] = checkbox
        group.add_text("Flip bitangent vectors", subsizer, sizer_args)

        # **********************************************************************

        sizer = self.get_bottom_ctrl_sizer()
        sizer_args = (0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        label = "Make geometry editable"
        bitmaps = PanelButton.create_button_bitmaps("*%s" % label, bitmap_paths)
        PanelButton(self, self, sizer, bitmaps, label, "Turn into editable geometry",
                    self.__make_editable, sizer_args)

        parent.add_panel(self)
        self.update()
        self.finalize()

        def finalize_sections():

            sel_section.expand(False)
            create_section.set_title_hilite_color((1., 1., .5, .65))
            create_section.set_title_hilited()
            create_section.expand(False)
            surface_section.expand(False)
            self.show_section("create", False, update=False)
            self.show_section("surface_props", False, update=False)
            self.show_bottom_controls(False, update=False)

            for props in self._properties.itervalues():
                for section_id in props.get_section_ids():
                    self.show_section(section_id, False, update=False)

            self.update_parent()

        wx.CallAfter(finalize_sections)

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

        Mgr.add_app_updater("selected_obj_types", self.show)
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

        for props in self._properties.itervalues():
            props.setup()

    def get_clipping_rect(self):

        panel_rect = self.GetRect()
        width, height = panel_rect.size
        y_orig = self.GetParent().GetPosition()[1] + panel_rect.y
        clipping_rect = wx.Rect(0, -y_orig, *self.GetGrandParent().GetSize())

        return clipping_rect

    def update_layout(self):

        def task():

            self._parent.Refresh()
            self.GetSizer().Layout()
            self.update_parent()

        task_id = "update_props_panel"
        PendingTasks.add(task, task_id, sort=100)

    def __make_editable(self):

        Mgr.update_remotely("geometry_access")

    def __update_sections(self, creation_status):

        obj_types = self._sel_obj_types
        obj_type = obj_types[0] if len(obj_types) == 1 else ""
        props = self._properties[obj_type] if obj_type else None
        extra_section_ids = props.get_extra_section_ids() if props else []

        if creation_status == "started":

            self.show_section("create", update=False)
            self.show_bottom_controls(False, update=False)
            self.show_section("surface_props", False, update=False)

            for section_id in extra_section_ids:
                self.show_section(section_id, False, update=False)

        elif creation_status == "ended":

            if self._sel_obj_count == 1:
                for section_id in extra_section_ids:
                    self.show_section(section_id, update=False)

            props = self._properties
            base_types = set(props[o_type].get_base_type() for o_type in obj_types)

            if base_types == set(["primitive"]):
                self.show_bottom_controls(update=False)

            if base_types and not base_types - set(["primitive", "editable_geom", "basic_geom"]):
                self.show_section("surface_props", update=False)

            self.show_section("create", False, update=False)

        self.update_layout()

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
            name = "%s Objects selected" % count
            combobox.add_item(None, name, lambda: None)

        get_command = lambda obj_id: lambda: self.__update_selection(obj_id)

        for obj_id, name in names.iteritems():
            combobox.add_item(obj_id, name, get_command(obj_id))

        if count == 1:
            name = names.popitem()[1]
        else:
            name = "%s Objects selected" % count

        self._name_field.set_value("name", name)
        self._name_field.show_text()

    def __set_next_object_name(self, name):

        self._name_field.enable()
        self._name_field.set_text_color(self._colors["custom"])
        self._name_field.set_value("name", name)
        self._name_field.show_text()

    def __handle_color(self, color):

        color_values = Mgr.convert_to_remote_format("color", color.Get())

        if GlobalData["active_creation_type"]:
            obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""
            GlobalData["next_%s_color" % obj_type] = color_values
            self._color_picker.set_color(color_values)
        else:
            Mgr.update_remotely("selected_obj_color", color_values)

    def __set_object_color(self, color_values):

        if GlobalData["active_creation_type"] != "":
            return

        self._color_picker.set_color(color_values)

    def __set_next_object_color(self):

        obj_type = self._obj_types[0] if len(self._obj_types) == 1 else ""

        if not obj_type or obj_type == "editable_geom":
            return

        next_color = GlobalData["next_%s_color" % obj_type]
        self._color_picker.Enable(True if next_color else False)
        self._color_picker.show_color("single" if next_color else "none")

        if next_color:
            self._color_picker.set_color(next_color)

    def __check_selection_count(self, on_enable=False):

        if GlobalData["active_creation_type"] != "" or GlobalData["temp_toplevel"]:
            return

        self._sel_obj_count = sel_count = GlobalData["selection_count"]

        if GlobalData["active_obj_level"] == "top":

            multi_sel = sel_count > 1
            color = self._colors["disabled"] if multi_sel else None

            if not on_enable:

                if multi_sel:
                    for checkbox in self._checkboxes.itervalues():
                        checkbox.check(False)

                for checkbox in self._checkboxes.itervalues():
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
                        self.show_section(section_id, False, update=False)
                else:
                    for section_id in extra_section_ids:
                        self.show_section(section_id, True, update=False)

                self.update_layout()

    def __check_selection_color_count(self):

        if GlobalData["active_creation_type"] != "":
            return

        if GlobalData["active_obj_level"] == "top":
            count = GlobalData["sel_color_count"]
            self._color_picker.Enable(count > 0)
            self._color_picker.show_color(("single" if count == 1 else "multiple")
                                          if count > 0 else "none")
        else:
            self._color_picker.Enable(False)

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
            self._color_picker.enable()
        else:
            self.__check_selection_count(on_enable=True)
            self.__check_selection_color_count()

    def disable(self, show=True):

        if not Panel.disable(self, show):
            return

        self._name_field.enable(False)
        self._color_picker.disable()

    def get_width(self):

        return self._width

    def get_client_width(self):

        return self._width - self.get_client_offset() * 2

    def show(self, obj_types):

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
            self.show_section(section_id, update=False)

        base_types = set(props[o_type].get_base_type() for o_type in obj_types)

        if base_types == set(["primitive"]):
            self.show_bottom_controls(update=False)
        else:
            self.show_bottom_controls(False, update=False)

        if base_types and not base_types - set(["primitive", "editable_geom", "basic_geom"]):
            self.show_section("surface_props", update=False)
        else:
            self.show_section("surface_props", False, update=False)

        if in_creation_mode:

            self.show_bottom_controls(False, update=False)
            self.show_section("surface_props", False, update=False)

            for section_id in extra_section_ids:
                self.show_section(section_id, False, update=False)

        for section_id in prev_section_ids:
            self.show_section(section_id, False, update=False)

        self._obj_types = obj_types

        if in_creation_mode:
            self._color_picker.show_color("single")
            self.__set_next_object_color()
        else:
            self._sel_obj_types = obj_types

        self.update_layout()
