from ..base import *
from ..button import *
from ..toolbar import *
from ..panel import *
from ..dialog import *


class RegionTypeComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        tooltip_text = "Region type"

        ToolbarComboBox.__init__(self, toolbar, 150, tooltip_text=tooltip_text)

        def add_region_type_entry(region_type, text):

            def set_region_type():

                GlobalData["region_select"]["type"] = region_type
                self.select_item(region_type)

            self.add_item(region_type, text, set_region_type)

        for entry_data in (
            ("rect", "Rectangle (from corner)"), ("rect_centered", "Rectangle (from center)"),
            ("square", "Square (from corner)"), ("square_centered", "Square (from center)"),
            ("ellipse", "Ellipse (from corner)"), ("ellipse_centered", "Ellipse (from center)"),
            ("circle", "Circle (from corner)"), ("circle_centered", "Circle (from center)"),
            ("fence", "Fence (point-to-point)"), ("lasso", "Lasso (freehand)"),
            ("paint", "Paint (using circle)")
        ):
            add_region_type_entry(*entry_data)

        self.update_popup_menu()


class SetsComboBox(ToolbarComboBox):

    def __init__(self, toolbar):

        tooltip_text = "Selection set"

        ToolbarComboBox.__init__(self, toolbar, 150, tooltip_text=tooltip_text, editable=True)

        field = self.get_input_field()
        val_id = "name"
        field.add_value(val_id, "string", handler=self.__handle_name)
        field.set_input_init(val_id, self.__init_input)
        field.set_input_parser(val_id, self.__parse_name)
        field.show_value(val_id)
        field.set_text(val_id, "Create selection set")
        field.set_text_color(Skin["text"]["input_disabled"]["color"])
        field.set_on_accept(self.__accept_name)
        field.set_on_reject(self.__reject_name)
        self._field_text_color = None
        self.set_text("")

        self._menus = menus = {"top": self.get_popup_menu()}

        for obj_level in ("vert", "normal", "edge", "poly", "uv_vert", "uv_edge", "uv_poly"):
            menus[obj_level] = self.create_popup_menu()

        Mgr.add_app_updater("selection_set", self.__update)

    def __init_input(self):

        field = self.get_input_field()
        self._field_text_color = color = field.get_text_color()

        if color == Skin["text"]["input_disabled"]["color"]:
            field.set_text_color(None)
            field.clear(forget=False)

    def __accept_name(self, valid):

        if not valid:
            self.get_input_field().set_text_color(self._field_text_color)

    def __reject_name(self):

        self.get_input_field().set_text_color(self._field_text_color)

    def __parse_name(self, name):

        parsed_name = name.strip()
        old_name = self.get_input_field().get_text("name")

        if parsed_name != old_name:
            return parsed_name if parsed_name else None

    def __handle_name(self, value_id, name):

        Mgr.update_remotely("object_selection", "add_set", name)

    def __add_set(self, set_id, name, is_copy=False):

        def apply_set():

            self.select_item(set_id)
            text = self.get_item_text(set_id)
            self.get_input_field().set_value("name", text)
            self.get_input_field().set_text_color(None)
            Mgr.update_remotely("object_selection", "apply_set", set_id)

        self.add_item(set_id, name, apply_set, update=True)

        if not is_copy:
            self.select_item(set_id)
            self.get_input_field().set_value("name", name)
            self.get_input_field().set_text_color(None)

    def __rename_set(self, set_id, name):

        self.set_item_text(set_id, name)

        if self.get_selected_item() == set_id:
            self.get_input_field().set_value("name", name)
            self.get_input_field().set_text_color(None)

    def __remove_set(self, set_id):

        if self.get_selected_item() == set_id:
            self.__hide_name()

        self.remove_item(set_id)

    def __clear_sets(self):

        item_ids = list(self.get_popup_menu().get_items().keys())
        item_id = self.get_selected_item()

        if item_id is not None:
            item_ids.append(item_id)
            self.__hide_name()

        for item_id in item_ids:
            self.remove_item(item_id)

    def __select_set(self, set_id, name):

        self.select_item(set_id)
        self.get_input_field().set_value("name", name)
        self.get_input_field().set_text_color(None)

    def __hide_set(self, set_id):

        if self.get_selected_item() == set_id:
            self.__hide_name()

    def __hide_name(self):

        self.get_input_field().clear()
        self.get_input_field().set_text("name", "Create selection set")
        self.get_input_field().set_text_color(Skin["text"]["input_disabled"]["color"])
        self.select_none()

    def __replace_sets(self, obj_level):

        self.__hide_name()
        self.set_popup_menu(self._menus[obj_level])

    def __reset_sets(self):

        self.__hide_name()

        for menu in self._menus.values():
            self.set_popup_menu(menu)
            self.__clear_sets()

    def __update(self, update_type="", *args):

        if update_type == "add":
            self.__add_set(*args)
        if update_type == "copy":
            self.__add_set(*args, is_copy=True)
        elif update_type == "rename":
            self.__rename_set(*args)
        elif update_type == "remove":
            self.__remove_set(*args)
        elif update_type == "clear":
            self.__clear_sets(*args)
        elif update_type == "select":
            self.__select_set(*args)
        elif update_type == "hide":
            self.__hide_set(*args)
        elif update_type == "hide_name":
            self.__hide_name(*args)
        elif update_type == "replace":
            self.__replace_sets(*args)
        elif update_type == "reset":
            self.__reset_sets(*args)


class SelectionToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "selection", "Selection")

        self._btns = btns = {}
        btn = ToolbarButton(self, icon_id="icon_region_sel",
                            tooltip_text="Region-select objects by default",
                            command=self.__toggle_region_select)
        mod_code = GlobalData["mod_key_codes"]["alt"]
        hotkey = ("s", mod_code)
        btn.set_hotkey(hotkey, "Alt+S")
        btns["region_select"] = btn
        borders = (0, 5, 0, 0)
        self.add(btn, borders=borders, alignment="center_v")

        self._comboboxes = {}
        combobox = RegionTypeComboBox(self)
        self._comboboxes["region_type"] = combobox
        self.add(combobox, borders=borders, alignment="center_v")

        btn = ToolbarButton(self, icon_id="icon_region_sel_enclose",
                            tooltip_text="Only select fully enclosed objects",
                            command=self.__toggle_enclose)
        btns["enclose"] = btn
        self.add(btn, borders=borders, alignment="center_v")

        self.add(ToolbarSeparator(self), borders=borders)

        combobox = SetsComboBox(self)
        self._comboboxes["sets"] = combobox
        self.add(combobox, borders=borders, alignment="center_v")

    def __toggle_region_select(self):

        is_default = not GlobalData["region_select"]["is_default"]
        GlobalData["region_select"]["is_default"] = is_default
        self._btns["region_select"].set_active(is_default)

    def __toggle_enclose(self):

        enclose = not GlobalData["region_select"]["enclose"]
        GlobalData["region_select"]["enclose"] = enclose
        colors = Skin["colors"]
        shape_color = colors["selection_region_shape_{}".format("enclose" if enclose else "default")]
        fill_color = colors["selection_region_fill_{}".format("enclose" if enclose else "default")]
        GlobalData["region_select"]["shape_color"] = shape_color
        GlobalData["region_select"]["fill_color"] = fill_color
        Mgr.update_remotely("object_selection", "region_color")
        self._btns["enclose"].set_active(enclose)


class SelectionPanel(Panel):

    def __init__(self, stack):

        Panel.__init__(self, stack, "selection", "Selection")

        self._comboboxes = {}
        self._fields = {}
        self._btns = {}
        self._radio_btns = {}

        # **************************** Sets section ********************************

        section = self.add_section("sets", "Sets")

        combobox1 = PanelComboBox(section, 100, tooltip_text="Primary set", editable=True)
        self._comboboxes["set1"] = combobox1
        section.add(combobox1, expand=True)

        field = combobox1.get_input_field()
        val_id = "name"
        field.add_value(val_id, "string", handler=self.__handle_name)
        field.set_input_parser(val_id, self.__parse_name)
        field.show_value(val_id)
        self._fields[val_id] = field
        combobox1.show_input_field(False)

        section.add((0, 5))
        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        icon_id = "icon_caret"
        tooltip_text = "Edit primary set name"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__toggle_set_name_editable)
        self._btns["edit_set_name"] = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_copy"
        tooltip_text = "Create copy of primary set"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__copy_set)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_add"
        tooltip_text = "Create new set from current selection"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__create_set)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_remove"
        tooltip_text = "Delete primary set"
        btn = PanelButton(section, "", icon_id, tooltip_text, self.__remove_set)
        btn_sizer.add(btn, proportion=1.)

        section.add((0, 5))
        btn_sizer = Sizer("horizontal")
        section.add(btn_sizer, expand=True)

        text = "Clear"
        tooltip_text = "Delete all sets"
        btn = PanelButton(section, text, "", tooltip_text, self.__clear_sets)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        text = "Apply"
        tooltip_text = "Select objects in primary set"
        btn = PanelButton(section, text, "", tooltip_text, self.__apply_set)
        btn_sizer.add(btn, proportion=1.)

        group = section.add_group("Combine with")

        combobox2 = PanelComboBox(group, 100, tooltip_text="Secondary set")

        def select_current():

            self._comboboxes["set2"].select_item("cur_sel")

        combobox2.add_item("cur_sel", "<Current selection>", select_current, update=True)
        self._comboboxes["set2"] = combobox2
        group.add(combobox2, expand=True)

        set_menus1 = {"top": combobox1.get_popup_menu()}
        set_menus2 = {"top": combobox2.get_popup_menu()}
        self._menus = menus = {"set1": set_menus1, "set2": set_menus2}

        for obj_level in ("vert", "normal", "edge", "poly", "uv_vert", "uv_edge", "uv_poly"):
            set_menus1[obj_level] = combobox1.create_popup_menu()
            set_menus2[obj_level] = combobox2.create_popup_menu()

        group.add((0, 5))
        btn_sizer = Sizer("horizontal")
        group.add(btn_sizer, expand=True)

        icon_id = "icon_union"
        tooltip_text = "Union"
        command = lambda: self.__combine_sets("union")
        btn = PanelButton(group, "", icon_id, tooltip_text, command)
        self._edit_mat_name_btn = btn
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_intersection"
        tooltip_text = "Intersection"
        command = lambda: self.__combine_sets("intersection")
        btn = PanelButton(group, "", icon_id, tooltip_text, command)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_difference"
        tooltip_text = "Difference"
        command = lambda: self.__combine_sets("difference")
        btn = PanelButton(group, "", icon_id, tooltip_text, command)
        btn_sizer.add(btn, proportion=1.)

        btn_sizer.add((5, 0))

        icon_id = "icon_sym_diff"
        tooltip_text = "Symmetric difference"
        command = lambda: self.__combine_sets("sym_diff")
        btn = PanelButton(group, "", icon_id, tooltip_text, command)
        btn_sizer.add(btn, proportion=1.)

        group.add((0, 5))

        radio_btns = PanelRadioButtonGroup(group, columns=1, gap_h=10)
        btn_data = (("in_place", "Modify primary set"), ("new", "Create new set"))

        for btn_id, text in btn_data:
            radio_btns.add_button(btn_id, text)

        self._radio_btns["result"] = radio_btns
        group.add(radio_btns.get_sizer())
        radio_btns.set_selected_button("in_place")

        # **************************************************************************

        Mgr.add_app_updater("selection_set", self.__update)

    def setup(self):

        self.expand(False)

    def __parse_name(self, name):

        parsed_name = name.strip()
        old_name = self._fields["name"].get_text("name")

        if parsed_name != old_name:
            return parsed_name if parsed_name else None

    def __handle_name(self, value_id, name):

        set_id = self._comboboxes["set1"].get_selected_item()
        Mgr.update_remotely("object_selection", "rename_set", set_id, name)

    def __add_set(self, set_id, name):

        def select_set1():

            self._comboboxes["set1"].select_item(set_id)
            text = self._comboboxes["set1"].get_item_text(set_id)
            self._fields["name"].set_value("name", text)

        def select_set2():

            self._comboboxes["set2"].select_item(set_id)

        self._comboboxes["set1"].add_item(set_id, name, select_set1, update=True)
        self._comboboxes["set2"].add_item(set_id, name, select_set2, update=True)
        self._comboboxes["set1"].select_item(set_id)
        self._fields["name"].set_value("name", name)

    def __rename_set(self, set_id, name):

        self._comboboxes["set1"].set_item_text(set_id, name)
        self._comboboxes["set2"].set_item_text(set_id, name)
        self._fields["name"].set_value("name", name)

    def __hide_name(self):

        self._fields["name"].clear()
        self._btns["edit_set_name"].set_active(False)
        self._comboboxes["set1"].show_input_field(False)
        self._comboboxes["set1"].select_none()
        self._comboboxes["set2"].select_item("cur_sel")

    def __replace_sets(self, obj_level):

        self.__hide_name()
        self._comboboxes["set1"].set_popup_menu(self._menus["set1"][obj_level])
        self._comboboxes["set2"].set_popup_menu(self._menus["set2"][obj_level])

    def __reset_sets(self):

        self.__hide_name()
        menus = self._menus
        combobox1 = self._comboboxes["set1"]
        combobox2 = self._comboboxes["set2"]

        for menu1, menu2 in zip(list(menus["set1"].values()), list(menus["set2"].values())):
            combobox1.set_popup_menu(menu1)
            combobox2.set_popup_menu(menu2)
            self.__clear_sets(update_remotely=False)

    def __update(self, update_type="", *args):

        if update_type in ("add", "copy"):
            self.__add_set(*args)
        elif update_type == "rename":
            self.__rename_set(*args)
        elif update_type == "replace":
            self.__replace_sets(*args)
        elif update_type == "reset":
            self.__reset_sets(*args)

    def __apply_set(self):

        set_id = self._comboboxes["set1"].get_selected_item()

        if set_id is not None:
            Mgr.update_remotely("object_selection", "apply_set", set_id)
            name = self._fields["name"].get_text("name")
            Mgr.update_locally("selection_set", "select", set_id, name)

    def __toggle_set_name_editable(self):

        set_id = self._comboboxes["set1"].get_selected_item()

        if set_id is not None:
            combobox = self._comboboxes["set1"]
            show = combobox.is_input_field_hidden()
            combobox.show_input_field(show)
            self._btns["edit_set_name"].set_active(show)

    def __copy_set(self):

        set_id = self._comboboxes["set1"].get_selected_item()

        if set_id is not None:
            Mgr.update_remotely("object_selection", "copy_set", set_id)

    def __create_set(self):

        Mgr.update_remotely("object_selection", "add_set")

    def __remove_set(self):

        combobox = self._comboboxes["set1"]
        set_id = combobox.get_selected_item()

        if set_id is None:
            return

        Mgr.update_remotely("object_selection", "remove_set", set_id)
        item_ids = list(combobox.get_popup_menu().get_items().keys())
        item_ids.append(set_id)

        for combobox_id in ("set1", "set2"):

            combobox = self._comboboxes[combobox_id]
            all_item_ids = combobox.get_item_ids()
            other_item_ids = []

            for item_id in all_item_ids[:]:
                if item_id not in item_ids:
                    all_item_ids.remove(item_id)
                    other_item_ids.append(item_id)

            combobox.remove_item(set_id)
            all_item_ids[:] = item_ids + other_item_ids
            all_item_ids.remove(set_id)

        if self._comboboxes["set2"].get_selected_item() is None:
            self._comboboxes["set2"].select_item("cur_sel")

        set_id = self._comboboxes["set1"].get_selected_item()

        if set_id is None:
            self._fields["name"].clear()
            self._comboboxes["set1"].show_input_field(False)
            self._btns["edit_set_name"].set_active(False)
        else:
            text = self._comboboxes["set1"].get_item_text(set_id)
            self._fields["name"].set_value("name", text)

    def __clear_sets(self, update_remotely=True):

        combobox = self._comboboxes["set1"]
        item_ids = list(combobox.get_popup_menu().get_items().keys())
        item_id = combobox.get_selected_item()

        if item_id is not None:
            item_ids.append(item_id)
            self._fields["name"].clear()
            combobox.show_input_field(False)
            self._btns["edit_set_name"].set_active(False)

        if not item_ids:
            return

        if update_remotely:
            Mgr.update_remotely("object_selection", "clear_sets")

        for combobox_id in ("set1", "set2"):

            combobox = self._comboboxes[combobox_id]
            combobox.select_none()

            for item_id in item_ids:
                combobox.remove_item(item_id)

        self._comboboxes["set2"].select_item("cur_sel")

    def __combine_sets(self, op):

        item_id1 = self._comboboxes["set1"].get_selected_item()

        if item_id1 is None:
            return

        item_id2 = self._comboboxes["set2"].get_selected_item()
        in_place = self._radio_btns["result"].get_selected_button() == "in_place"
        Mgr.update_remotely("object_selection", "combine_sets", item_id1, item_id2, op, in_place)


class SelectionManager(object):

    def __init__(self, menubar):

        menu = menubar.add_menu("select", "Select")
        mod_ctrl = GlobalData["mod_key_codes"]["ctrl"]
        handler = lambda: Mgr.update_remotely("object_selection", "all")
        menu.add("select_all", "Select all", handler)
        hotkey = ("a", mod_ctrl)
        menu.set_item_hotkey("select_all", hotkey, "Ctrl+A")
        handler = lambda: Mgr.update_remotely("object_selection", "invert")
        menu.add("invert_sel", "Invert selection", handler)
        hotkey = ("i", mod_ctrl)
        menu.set_item_hotkey("invert_sel", hotkey, "Ctrl+I")
        handler = lambda: Mgr.update_remotely("object_selection", "clear")
        menu.add("clear_sel", "Select none", handler)
        hotkey = ("backspace", mod_ctrl)
        menu.set_item_hotkey("clear_sel", hotkey, "Ctrl+Backspace")

        menu.add("sep0", item_type="separator")

        dialog_item = menu.add("name_select", "Select by name", self.__show_selection_dialog)
        hotkey = ("n", 0)
        menu.set_item_hotkey("name_select", hotkey, "N")

        region_select = {"is_default": False, "type": "rect", "enclose": False}
        region_select["shape_color"] = Skin["colors"]["selection_region_shape_default"]
        region_select["fill_color"] = Skin["colors"]["selection_region_fill_default"]
        GlobalData.set_default("region_select", region_select)

        def disable_selection_dialog(disabler_id=None, disabler=None):

            dialog_item.enable(False)

            if disabler_id is not None:
                dialog_item.add_disabler(disabler_id, disabler)

        def enable_selection_dialog(disabler_id=None):

            if disabler_id is not None:
                dialog_item.remove_disabler(disabler_id)

            dialog_item.enable()

        self._selection_dialog_kwargs = {}

        Mgr.accept("disable_selection_dialog", disable_selection_dialog)
        Mgr.accept("enable_selection_dialog", enable_selection_dialog)
        Mgr.add_app_updater("selection_by_name", self.__update_selection_by_name)

    def __update_selection_by_name(self, update_type, *args):

        if update_type == "default":
            self._selection_dialog_kwargs = {}
        else:
            title, object_types, multi_select, ok_alias, handler = args
            self._selection_dialog_kwargs = {
                "title": title,
                "object_types": object_types,
                "multi_select": multi_select,
                "ok_alias": ok_alias,
                "handler": handler
            }

    def __show_selection_dialog(self):

        SelectionDialog(**self._selection_dialog_kwargs)
