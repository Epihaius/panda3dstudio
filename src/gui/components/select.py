from ..base import *
from ..button import *
from ..toolbar import *
from ..panel import *
from ..dialogs import *


class SelectionToolbar(Toolbar):

    def __init__(self, parent):

        Toolbar.__init__(self, parent, "selection")

        widgets = Skin.layout.create(self, "selection")
        self._btns = btns = widgets["buttons"]
        self._comboboxes = widgets["comboboxes"]

        btn = btns["region_select"]
        btn.command = self.__toggle_region_select
        mod_code = GD["mod_key_codes"]["alt"]
        hotkey = ("s", mod_code)
        btn.set_hotkey(hotkey, "Alt+S")

        btn = btns["enclose"]
        btn.command = self.__toggle_enclose

        self.__setup_region_type_combobox()
        self.__setup_selection_set_combobox()

    def __setup_region_type_combobox(self):

        combobox = self._comboboxes["region_type"]

        def add_region_type_entry(region_type, text):

            def set_region_type():

                GD["region_select"]["type"] = region_type
                combobox.select_item(region_type)

            combobox.add_item(region_type, text, set_region_type)

        for entry_data in (
            ("rect", "Rectangle (from corner)"), ("rect_centered", "Rectangle (from center)"),
            ("square", "Square (from corner)"), ("square_centered", "Square (from center)"),
            ("ellipse", "Ellipse (from corner)"), ("ellipse_centered", "Ellipse (from center)"),
            ("circle", "Circle (from corner)"), ("circle_centered", "Circle (from center)"),
            ("fence", "Fence (point-to-point)"), ("lasso", "Lasso (freehand)"),
            ("paint", "Paint (using circle)")
        ):
            add_region_type_entry(*entry_data)

        combobox.update_popup_menu()

    def __setup_selection_set_combobox(self):

        combobox = self._comboboxes["sets"]

        val_id = "name"
        handler = lambda *args: self.__handle_name(args[1])
        field = combobox.set_input_field(val_id, "string", handler)
        field.set_input_init(self.__init_input)
        field.set_input_parser(self.__parse_name)
        field.set_text("Create selection set")
        field.set_text_color(Skin.text["input_disabled"]["color"])
        field.set_on_accept(self.__accept_name)
        field.set_on_reject(self.__reject_name)
        self._field_text_color = None
        combobox.set_text("")

        self._menus = menus = {"top": combobox.get_popup_menu()}

        for obj_level in ("vert", "normal", "edge", "poly",
                "uv_vert", "uv_edge", "uv_poly", "uv_part"):
            menus[obj_level] = combobox.create_popup_menu()

        Mgr.add_app_updater("selection_set", self.__update)

    def __init_input(self):

        field = self._comboboxes["sets"].input_field
        self._field_text_color = color = field.get_text_color()

        if color == Skin.text["input_disabled"]["color"]:
            field.set_text_color(None)
            field.clear(forget=False)

    def __accept_name(self, valid):

        if not valid:
            self._comboboxes["sets"].input_field.set_text_color(self._field_text_color)

    def __reject_name(self):

        self._comboboxes["sets"].input_field.set_text_color(self._field_text_color)

    def __parse_name(self, input_text):

        name = input_text.strip()
        old_name = self._comboboxes["sets"].input_field.get_text()

        if name != old_name:
            return name if name else None

    def __handle_name(self, name):

        Mgr.update_remotely("object_selection", "add_set", name)

    def __add_set(self, set_id, name, is_copy=False):

        def apply_set():

            combobox = self._comboboxes["sets"]
            combobox.select_item(set_id)
            text = combobox.get_item_text(set_id)
            combobox.input_field.set_value(text)
            combobox.input_field.set_text_color(None)
            Mgr.update_remotely("object_selection", "apply_set", set_id)

        combobox = self._comboboxes["sets"]
        combobox.add_item(set_id, name, apply_set, update=True)

        if not is_copy:
            combobox.select_item(set_id)
            combobox.input_field.set_value(name)
            combobox.input_field.set_text_color(None)

    def __rename_set(self, set_id, name):

        combobox = self._comboboxes["sets"]
        combobox.set_item_text(set_id, name)

        if combobox.get_selected_item() == set_id:
            combobox.input_field.set_value(name)
            combobox.input_field.set_text_color(None)

    def __remove_set(self, set_id):

        combobox = self._comboboxes["sets"]

        if combobox.get_selected_item() == set_id:
            self.__hide_name()

        combobox.remove_item(set_id)

    def __clear_sets(self):

        combobox = self._comboboxes["sets"]
        item_ids = list(combobox.get_popup_menu().items.keys())
        item_id = combobox.get_selected_item()

        if item_id is not None:
            item_ids.append(item_id)
            self.__hide_name()

        for item_id in item_ids:
            combobox.remove_item(item_id)

    def __select_set(self, set_id, name):

        combobox = self._comboboxes["sets"]
        combobox.select_item(set_id)
        combobox.input_field.set_value(name)
        combobox.input_field.set_text_color(None)

    def __hide_set(self, set_id):

        if self._comboboxes["sets"].get_selected_item() == set_id:
            self.__hide_name()

    def __hide_name(self):

        combobox = self._comboboxes["sets"]
        combobox.input_field.clear()
        combobox.input_field.set_text("Create selection set")
        combobox.input_field.set_text_color(Skin.text["input_disabled"]["color"])
        combobox.select_none()

    def __replace_sets(self, obj_level):

        self.__hide_name()
        self._comboboxes["sets"].set_popup_menu(self._menus[obj_level])

    def __reset_sets(self):

        self.__hide_name()
        combobox = self._comboboxes["sets"]

        for menu in self._menus.values():
            combobox.set_popup_menu(menu)
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

    def __toggle_region_select(self):

        is_default = not GD["region_select"]["is_default"]
        GD["region_select"]["is_default"] = is_default
        self._btns["region_select"].active = is_default

    def __toggle_enclose(self):

        enclose = not GD["region_select"]["enclose"]
        GD["region_select"]["enclose"] = enclose
        colors = Skin.colors
        shape_color = colors[f'selection_region_shape_{"enclose" if enclose else "default"}']
        fill_color = colors[f'selection_region_fill_{"enclose" if enclose else "default"}']
        GD["region_select"]["shape_color"] = shape_color
        GD["region_select"]["fill_color"] = fill_color
        Mgr.update_remotely("object_selection", "region_color")
        self._btns["enclose"].active = enclose


class SelectionPanel(ControlPanel):

    def __init__(self, pane):

        ControlPanel.__init__(self, pane, "selection")

        widgets = Skin.layout.create(self, "selection")
        self._btns = btns = widgets["buttons"]
        self._comboboxes = widgets["comboboxes"]
        self._fields = widgets["fields"]
        self._radio_btns = widgets["radiobutton_groups"]

        # **************************** Sets section ********************************

        val_id = "name"
        handler = lambda *args: self.__handle_name(args[1])
        combobox1 = self._comboboxes["set1"]
        field = combobox1.set_input_field(val_id, "string", handler)
        field.set_input_parser(self.__parse_name)
        self._fields[val_id] = field

        def select_current():

            self._comboboxes["set1"].select_item("cur_sel")
            self._comboboxes["set1"].show_input_field(False)
            self._fields["name"].clear()
            self._btns["edit_set_name"].active = False

        combobox1.add_item("cur_sel", "<Current selection>", select_current, update=True)
        combobox1.show_input_field(False)

        btn = btns["edit_set_name"]
        btn.command = self.__toggle_set_name_editable

        btn = btns["copy_set"]
        btn.command = self.__copy_set

        btn = btns["create_set"]
        btn.command = self.__create_set

        btn = btns["remove_set"]
        btn.command = self.__remove_set

        btn = btns["clear_sets"]
        btn.command = self.__clear_sets

        btn = btns["apply_set"]
        btn.command = self.__apply_set

        combobox2 = self._comboboxes["set2"]

        def select_current():

            self._comboboxes["set2"].select_item("cur_sel")

        combobox2.add_item("cur_sel", "<Current selection>", select_current, update=True)

        set_menus1 = {"top": combobox1.get_popup_menu()}
        set_menus2 = {"top": combobox2.get_popup_menu()}
        self._menus = {"set1": set_menus1, "set2": set_menus2}

        for obj_level in ("vert", "normal", "edge", "poly",
                "uv_vert", "uv_edge", "uv_poly", "uv_part"):
            set_menus1[obj_level] = combobox1.create_popup_menu()
            set_menus2[obj_level] = combobox2.create_popup_menu()

        for op in ("union", "intersection", "difference", "sym_diff"):
            btn = btns[op]
            btn.command = lambda o=op: self.__combine_sets(o)

        radio_btns = self._radio_btns["result"]
        radio_btns.set_selected_button("in_place")

        # **************************************************************************

        Mgr.add_app_updater("selection_set", self.__update)

    def setup(self):

        self.expand(False)

    def __parse_name(self, input_text):

        name = input_text.strip()
        old_name = self._fields["name"].get_value()

        if name != old_name:
            return name if name else None

    def __handle_name(self, name):

        set_id = self._comboboxes["set1"].get_selected_item()
        Mgr.update_remotely("object_selection", "rename_set", set_id, name)

    def __add_set(self, set_id, name):

        def select_set1():

            self._comboboxes["set1"].select_item(set_id)
            text = self._comboboxes["set1"].get_item_text(set_id)
            self._fields["name"].set_value(text)

        def select_set2():

            self._comboboxes["set2"].select_item(set_id)

        self._comboboxes["set1"].add_item(set_id, name, select_set1, update=True)
        self._comboboxes["set2"].add_item(set_id, name, select_set2, update=True)
        self._comboboxes["set1"].select_item(set_id)
        self._fields["name"].set_value(name)

    def __rename_set(self, set_id, name):

        self._comboboxes["set1"].set_item_text(set_id, name)
        self._comboboxes["set2"].set_item_text(set_id, name)
        self._fields["name"].set_value(name)

    def __hide_name(self):

        self._fields["name"].clear()
        self._btns["edit_set_name"].active = False
        self._comboboxes["set1"].show_input_field(False)
        self._comboboxes["set1"].select_item("cur_sel")
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

        if set_id != "cur_sel":
            Mgr.update_remotely("object_selection", "apply_set", set_id)
            name = self._fields["name"].get_value()
            Mgr.update_locally("selection_set", "select", set_id, name)

    def __toggle_set_name_editable(self):

        set_id = self._comboboxes["set1"].get_selected_item()

        if set_id != "cur_sel":
            combobox = self._comboboxes["set1"]
            show = combobox.is_input_field_hidden()
            combobox.show_input_field(show)
            self._btns["edit_set_name"].active = show

    def __copy_set(self):

        set_id = self._comboboxes["set1"].get_selected_item()

        if set_id != "cur_sel":
            Mgr.update_remotely("object_selection", "copy_set", set_id)

    def __create_set(self):

        Mgr.update_remotely("object_selection", "add_set")

    def __remove_set(self):

        combobox = self._comboboxes["set1"]
        set_id = combobox.get_selected_item()

        if set_id == "cur_sel":
            return

        Mgr.update_remotely("object_selection", "remove_set", set_id)
        item_ids = list(combobox.get_popup_menu().items.keys())
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

        if set_id == "cur_sel":
            self._fields["name"].clear()
            self._comboboxes["set1"].show_input_field(False)
            self._btns["edit_set_name"].active = False
        else:
            text = self._comboboxes["set1"].get_item_text(set_id)
            self._fields["name"].set_value(text)

    def __clear_sets(self, update_remotely=True):

        combobox = self._comboboxes["set1"]
        item_ids = list(combobox.get_popup_menu().items.keys())
        item_id = combobox.get_selected_item()

        if item_id != "cur_sel":
            item_ids.remove("cur_sel")
            item_ids.append(item_id)
            self._fields["name"].clear()
            combobox.show_input_field(False)
            self._btns["edit_set_name"].active = False

        if not item_ids:
            return

        if update_remotely:
            Mgr.update_remotely("object_selection", "clear_sets")

        for combobox_id in ("set1", "set2"):

            combobox = self._comboboxes[combobox_id]
            combobox.select_item("cur_sel")

            for item_id in item_ids:
                combobox.remove_item(item_id)

    def __combine_sets(self, op):

        item_id1 = self._comboboxes["set1"].get_selected_item()
        item_id2 = self._comboboxes["set2"].get_selected_item()
        in_place = self._radio_btns["result"].get_selected_button() == "in_place"
        Mgr.update_remotely("object_selection", "combine_sets", item_id1, item_id2, op, in_place)


class SelectionManager:

    def __init__(self, menubar):

        menu = menubar.add_menu("select", "Select")
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
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

        dialog_item = menu.add("name_select", "Select by name...", self.__show_selection_dialog)
        hotkey = ("n", 0)
        menu.set_item_hotkey("name_select", hotkey, "N")

        region_select = {"is_default": False, "type": "rect", "enclose": False}
        region_select["shape_color"] = Skin.colors["selection_region_shape_default"]
        region_select["fill_color"] = Skin.colors["selection_region_fill_default"]
        GD.set_default("region_select", region_select)

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

        if update_type == "show":
            self.__show_selection_dialog()
        elif update_type == "default":
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
