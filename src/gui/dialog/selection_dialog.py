from .dialog import *


class NameInputField(DialogInputField):

    _field_borders = ()
    _img_offset = (0, 0)

    @classmethod
    def __set_field_borders(cls):

        l, r, b, t = TextureAtlas["outer_borders"]["dialog_inset1"]
        cls._field_borders = (l, r, b, t)
        cls._img_offset = (-l, -t)

    def __init__(self, parent, value_id, handler, width, dialog=None,
                 font=None, text_color=None, back_color=None,
                 on_key_enter=None, on_key_escape=None):

        if not self._field_borders:
            self.__set_field_borders()

        DialogInputField.__init__(self, parent, value_id, "string", handler, width,
                                  INSET1_BORDER_GFX_DATA, self._img_offset,
                                  dialog, font, text_color, back_color,
                                  on_key_enter=on_key_enter, on_key_escape=on_key_escape)

    def get_outer_borders(self):

        return self._field_borders


class EntryText(Widget):

    def __init__(self, parent, entry, text_list):

        Widget.__init__(self, "entry_text", parent, gfx_data={}, stretch_dir="both")

        self.mouse_region.sort = parent.sort + 1
        self.node.reparent_to(parent.get_widget_root_node())

        sizer = Sizer("horizontal")
        self.set_sizer(sizer)
        self._entry = entry
        self._image = None

        if len(text_list) == 1:

            text_widget = DialogText(self, text_list[0])
            sizer.add((50, 0))
            borders = (0, 5, 2, 2)
            sizer.add(text_widget, borders=borders)

        else:

            borders = (0, 0, 2, 2)
            text1, text2 = text_list
            subsizer = Sizer("horizontal")
            subsizer.set_default_size((20, 0))
            sizer.add(subsizer, borders=borders)

            if text1:
                text_widget = DialogText(self, text1)
                subsizer.add((0, 0), proportion=1.)
                subsizer.add(text_widget)
                subsizer.add((0, 0), proportion=1.)

            text_widget = DialogText(self, text2)
            sizer.add(text_widget, proportion=1., borders=borders)

    def destroy(self):

        if Widget.destroy(self):
            self._entry.destroy()
            self._entry = None

    def update_images(self, recurse=True, size=None):

        w, h = self.get_size()
        self._image = image = PNMImage(w, h, 4)
        color = self._entry.get_color()
        image.fill(*color)
        image.alpha_fill(1.)

        if recurse:
            self.get_sizer().update_images()

    def get_image(self, state=None, composed=True):

        image = PNMImage(self._image)

        if composed:
            image = self.get_sizer().get_composed_image(image)

        return image

    def update(self):

        self.update_images()
        w, h = self.get_size()

        if not self.is_hidden():
            self.get_card().copy_sub_image(self, self.get_image(), w, h, 0, 0)

    def on_left_down(self):

        ctrl_down = Mgr.get("mouse_watcher").is_button_down("control")
        shift_down = Mgr.get("mouse_watcher").is_button_down("shift")

        if ctrl_down and shift_down:
            return

        entry = self._entry

        if ctrl_down:
            self.parent.toggle_selected_entry(entry)
        elif shift_down:
            self.parent.set_selected_entry_range(entry)
        else:
            self.parent.set_selected_entry(entry)


class Entry:

    colors = None

    def __init__(self, parent, obj_data):

        self._is_selected = False
        obj_id, obj_sel_state, obj_name, obj_type = obj_data
        self._obj_id = obj_id
        self._obj_name = obj_name
        self._obj_type = obj_type

        if obj_sel_state:
            text_list = ["*", obj_name]
        else:
            text_list = ["", obj_name]

        self._components = components = []
        component = EntryText(parent, self, text_list)
        components.append(component)
        component = EntryText(parent, self, [obj_type.title()])
        components.append(component)

    def destroy(self):

        if not self._components:
            return

        self._components = []

    def get_object_id(self):

        return self._obj_id

    def get_object_name(self):

        return self._obj_name

    def get_object_type(self):

        return self._obj_type

    def get_components(self):

        return self._components

    def set_selected(self, is_selected=True):

        if self._is_selected == is_selected:
            return

        self._is_selected = is_selected

        for component in self._components:
            component.update()

    def is_selected(self):

        return self._is_selected

    def get_color(self):

        return self.colors["selected" if self._is_selected else "unselected"]

    def hide(self):

        for component in self._components:
            component.hide()

    def show(self):

        for component in self._components:
            component.show()


class EntryPane(DialogScrollPane):

    def __init__(self, dialog, object_types, obj_data):

        DialogScrollPane.__init__(self, dialog, "entry_pane", "vertical", (300, 300), "both")

        if not Entry.colors:
            colors = Skin["colors"]
            Entry.colors = {
                "unselected": colors["list_entry_unselected"][:3],
                "selected": colors["list_entry_selected"][:3]
            }

        sel_dialog_config = GD["config"]["sel_dialog"]
        obj_types = object_types if object_types else sel_dialog_config["obj_types"]
        self._entries_by_name = entries_by_name = {}
        self._entries_by_type = entries_by_type = {}
        self._entries_sorted_by_name = by_name = []
        self._entries_sorted_by_type = by_type = []
        self._entry_list = by_name if sel_dialog_config["sort"] == "name" else by_type
        # when a range is set, the following variable is used to determine the starting entry
        self._sel_start_entry = None
        self._entry_sizer = entry_sizer = GridSizer(columns=2)
        self.get_sizer().add(entry_sizer, proportion=1., expand=True)
        shown_entries = []
        shown_by_type = {}

        for obj_type, value in obj_data.items():
            for data in value:
                obj_id, obj_sel_state, obj_name = data
                data_ext = (obj_id, obj_sel_state, obj_name, obj_type)
                entry = Entry(self, data_ext)
                if obj_type in obj_types:
                    shown_entries.append(entry)
                entries_by_type.setdefault(obj_type, []).append(entry)
                entries_by_name[obj_name] = entry

        for entry in shown_entries:
            by_name.append(entry.get_object_name())
            shown_by_type.setdefault(entry.get_object_type(), []).append(entry.get_object_name())

        sort_case = GD["config"]["sel_dialog"]["sort_case"]

        by_name.sort() if sort_case else by_name.sort(key=str.casefold)
        by_name[:] = [entries_by_name[name] for name in by_name]

        for obj_type in obj_types:
            names = shown_by_type.get(obj_type, [])
            sorted_names = sorted(names) if sort_case else sorted(names, key=str.casefold)
            by_type.extend([entries_by_name[name] for name in sorted_names])

        for entry in self._entry_list:
            component1, component2 = entry.get_components()
            entry_sizer.add(component1, proportion_h=1.)
            entry_sizer.add(component2, stretch_h=True)

    def destroy(self):

        DialogScrollPane.destroy(self)

        self._entries_by_name = {}
        self._entries_by_type = {}
        self._entries_sorted_by_name = []
        self._entries_sorted_by_type = []
        self._entry_list = []
        self._sel_start_entry = None

    def _copy_widget_images(self, pane_image): 

        root_node = self.get_widget_root_node()

        for entry in self._entry_list:
            for component in entry.get_components():
                x, y = component.get_pos(ref_node=root_node)
                pane_image.copy_sub_image(component.get_image(), x, y, 0, 0)

    def __update_selection_start_entry(self, entry_list=None):

        entries = self._entry_list if entry_list is None else entry_list

        for entry in entries:
            if entry.is_selected():
                self._sel_start_entry = entry
                break
        else:
            self._sel_start_entry = None

    def show_object_types(self, obj_types):

        entries_by_name = self._entries_by_name
        entries_by_type = self._entries_by_type
        by_name = self._entries_sorted_by_name
        by_type = self._entries_sorted_by_type
        entry_list = self._entry_list
        old_entries = set(entry_list)
        entry_sizer = self._entry_sizer

        for entry in entry_list:
            for component in entry.get_components():
                entry_sizer.remove(component, rebuild=False)

        entry_sizer.rebuild()
        del by_name[:]
        del by_type[:]

        shown_entries = []
        shown_by_type = {}

        for obj_type in obj_types:
            for entry in entries_by_type.get(obj_type, []):
                shown_entries.append(entry)

        for entry in shown_entries:
            by_name.append(entry.get_object_name())
            shown_by_type.setdefault(entry.get_object_type(), []).append(entry.get_object_name())

        sort_case = GD["config"]["sel_dialog"]["sort_case"]

        by_name.sort() if sort_case else by_name.sort(key=str.casefold)
        by_name[:] = [entries_by_name[name] for name in by_name]

        for obj_type in obj_types:
            names = shown_by_type.get(obj_type, [])
            sorted_names = sorted(names) if sort_case else sorted(names, key=str.casefold)
            by_type.extend([entries_by_name[name] for name in sorted_names])

        for entry in entry_list:
            component1, component2 = entry.get_components()
            entry_sizer.add(component1, proportion_h=1.)
            entry_sizer.add(component2, stretch_h=True)
            entry.show()

        for entry in old_entries.difference(entry_list):
            entry.hide()
            entry.set_selected(False)

        self.get_ancestor("dialog").update_layout()

        if self._sel_start_entry and not self._sel_start_entry.is_selected():
            self.__update_selection_start_entry()

        self.get_ancestor("dialog").hide_set_name()

    def sort_entries(self, sort_by):

        entry_sizer = self._entry_sizer

        for entry in self._entry_list:
            for component in entry.get_components():
                entry_sizer.remove(component, rebuild=False)

        entry_sizer.rebuild()
        entry_list = self._entries_sorted_by_name if sort_by == "name" else self._entries_sorted_by_type
        self._entry_list = entry_list

        for entry in entry_list:
            component1, component2 = entry.get_components()
            entry_sizer.add(component1, proportion_h=1.)
            entry_sizer.add(component2, stretch_h=True)

        self.get_ancestor("dialog").update_layout()

    def search_entries(self, substring, in_selection):

        search_config = GD["config"]["sel_dialog"]["search"]
        match_case = search_config["match_case"]
        part = search_config["part"]

        if in_selection:
            entry_list = [e for e in self._entry_list if e.is_selected()]
        else:
            entry_list = self._entry_list

        for entry in entry_list:

            obj_name = entry.get_object_name()

            if part == "start":
                if match_case:
                    selected = obj_name.startswith(substring)
                else:
                    selected = obj_name.casefold().startswith(substring.casefold())
            elif part == "end":
                if match_case:
                    selected = obj_name.endswith(substring)
                else:
                    selected = obj_name.casefold().endswith(substring.casefold())
            elif part == "sub":
                if match_case:
                    selected = substring in obj_name
                else:
                    selected = substring.casefold() in obj_name.casefold()
            elif part == "whole":
                if match_case:
                    selected = substring == obj_name
                else:
                    selected = substring.casefold() == obj_name.casefold()

            entry.set_selected(selected)

        self.__update_selection_start_entry(entry_list)

        self.get_ancestor("dialog").hide_set_name()

    def set_selected_entry(self, entry):

        for e in self._entry_list:
            e.set_selected(False)

        entry.set_selected()
        self._sel_start_entry = entry

        self.get_ancestor("dialog").hide_set_name()

    def toggle_selected_entry(self, entry):

        entry.set_selected(not entry.is_selected())

        if entry.is_selected():
            self._sel_start_entry = entry
        elif self._sel_start_entry:
            if self._sel_start_entry is entry:
                for e in self._entry_list:
                    if e.is_selected():
                        self._sel_start_entry = e
                        break
                else:
                    self._sel_start_entry = None

        self.get_ancestor("dialog").hide_set_name()

    def set_selected_entry_range(self, end_entry):

        for entry in self._entry_list:
            entry.set_selected(False)

        if not self._sel_start_entry:
            self._sel_start_entry = end_entry

        i1 = self._entry_list.index(self._sel_start_entry)
        i2 = self._entry_list.index(end_entry)
        i1, i2 = min(i1, i2), max(i1, i2)

        for entry in self._entry_list[i1:i2+1]:
            entry.set_selected()

        self.get_ancestor("dialog").hide_set_name()

    def modify_selection(self, mod):

        if mod == "all":
            for entry in self._entry_list:
                entry.set_selected()
        elif mod == "none":
            for entry in self._entry_list:
                entry.set_selected(False)
        elif mod == "invert":
            for entry in self._entry_list:
                entry.set_selected(not entry.is_selected())

        self.__update_selection_start_entry()

    def select_from_set(self, selection_set):

        for entry in self._entry_list:
            entry.set_selected(entry.get_object_id() in selection_set)

        self.__update_selection_start_entry()

    def get_selection(self):

        return [e.get_object_id() for e in self._entry_list if e.is_selected()]


class SelectionDialog(Dialog):

    def __init__(self, title="Select objects", object_types=None, multi_select=True,
                 ok_alias="Select", handler=None):

        if handler is None:
            on_yes = self.__set_selection
        else:
            on_yes = lambda: handler(self._selection_ids)

        Dialog.__init__(self, title, "okcancel", ok_alias, on_yes)

        self._selection_ids = []
        self._checkbuttons = {}
        self._fields = fields = {}
        self._search_in_selection = False
        self._obj_types = ["model", "helper", "group", "light", "camera"]
        client_sizer = self.get_client_sizer()
        subsizer = Sizer("horizontal")
        client_sizer.add(subsizer)
        column1_sizer = Sizer("vertical")
        borders = (20, 20, 0, 20)
        subsizer.add(column1_sizer, proportion=1., expand=True, borders=borders)

        sel_dialog_config = GD["config"]["sel_dialog"]

        group = DialogWidgetGroup(self, "Find")
        borders = (0, 0, 10, 0)
        column1_sizer.add(group, expand=True, borders=borders)

        grp_subsizer = Sizer("horizontal")
        borders = (0, 0, 2, 0)
        group.add(grp_subsizer, borders=borders)

        checkbtn_sizer = Sizer("vertical")
        borders = (0, 20, 0, 0)
        grp_subsizer.add(checkbtn_sizer, borders=borders)

        text = "In selection"
        checkbtn = DialogCheckButton(group, lambda on:
            self.__set_search_option("in_sel", on), text)
        borders = (0, 0, 2, 0)
        checkbtn_sizer.add(checkbtn, borders=borders)

        text = "Match case"
        checkbtn = DialogCheckButton(group, lambda on:
            self.__set_search_option("match_case", on), text)
        checkbtn.check(sel_dialog_config["search"]["match_case"])
        checkbtn_sizer.add(checkbtn, borders=borders)

        radio_btns = DialogRadioButtonGroup(group, columns=2, gap_h=5)
        btn_ids = ("start", "end", "sub", "whole")
        texts = ("Start of name", "End of name", "Substring", "Whole name")
        get_command = lambda value: lambda: self.__set_search_option("part", value)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            radio_btns.set_button_command(btn_id, get_command(btn_id))

        radio_btns.set_selected_button(sel_dialog_config["search"]["part"])
        grp_subsizer.add(radio_btns.get_sizer(), alignment="center_v")

        name_handler = lambda *args: self.__search_entries(args[1])
        field = NameInputField(group, "name", name_handler, 100)
        field.set_input_parser(self.__parse_substring)
        fields["name"] = field
        group.add(field, expand=True)

        obj_data = {}
        sel_set_data = {}
        Mgr.update_remotely("object_selection", "get_data", obj_data, sel_set_data)
        self._entry_pane = pane = EntryPane(self, object_types, obj_data)
        frame = pane.frame
        borders = (0, 0, 5, 0)
        column1_sizer.add(frame, proportion=1., expand=True, borders=borders)

        btn_sizer = Sizer("horizontal")
        column1_sizer.add(btn_sizer, expand=True)
        btn = DialogButton(self, "All", command=lambda: self.__modify_selection("all"))
        borders = (0, 5, 0, 0)
        btn_sizer.add(btn, proportion=1., borders=borders)
        btn = DialogButton(self, "None", command=lambda: self.__modify_selection("none"))
        btn_sizer.add(btn, proportion=1., borders=borders)
        btn = DialogButton(self, "Invert", command=lambda: self.__modify_selection("invert"))
        btn_sizer.add(btn, proportion=1.)

        column2_sizer = Sizer("vertical")
        borders = (0, 20, 0, 20)
        subsizer.add(column2_sizer, proportion=1., expand=True, borders=borders)

        group = DialogWidgetGroup(self, "Sort by")
        borders = (0, 0, 10, 0)
        column2_sizer.add(group, expand=True, borders=borders)

        grp_subsizer = Sizer("horizontal")
        group.add(grp_subsizer)

        radio_btns = DialogRadioButtonGroup(group, columns=1)
        btn_ids = ("name", "type")
        texts = ("Name", "Type")
        get_command = lambda sort_by: lambda: self.__sort_entries(sort_by)

        for btn_id, text in zip(btn_ids, texts):
            radio_btns.add_button(btn_id, text)
            radio_btns.set_button_command(btn_id, get_command(btn_id))

        radio_btns.set_selected_button(sel_dialog_config["sort"])
        grp_subsizer.add(radio_btns.get_sizer())

        text = "Case-sensitive"
        checkbtn = DialogCheckButton(group, lambda on:
            self.__set_case_sort(on, object_types), text)
        checkbtn.check(sel_dialog_config["sort_case"])
        borders = (20, 0, 0, 0)
        grp_subsizer.add(checkbtn, borders=borders, alignment="center_v")

        group = DialogWidgetGroup(self, "Object types")
        borders = (0, 0, 10, 0)
        column2_sizer.add(group, expand=True, proportion=1., borders=borders)

        borders = (0, 20, 2, 0)
        type_names = ("Models", "Helpers", "Groups", "Lights", "Cameras")
        obj_types = object_types if object_types else sel_dialog_config["obj_types"]
        checkbox_handler = lambda *args: self.__show_object_types(object_types)

        for obj_type, type_name in zip(self._obj_types, type_names):

            checkbtn = DialogCheckButton(group, checkbox_handler, type_name)
            checkbtn.check(obj_type in obj_types)
            group.add(checkbtn, borders=borders)
            self._checkbuttons[obj_type] = checkbtn

            if object_types and obj_type not in obj_types:
                checkbtn.enable(False)

        group.add((0, 10), proportion=1.)

        btn_sizer = Sizer("horizontal")
        group.add(btn_sizer, expand=True)
        btns = []
        btn = DialogButton(group, "All", command=lambda: self.__modify_types("all"))
        btns.append(btn)
        borders = (0, 5, 0, 0)
        btn_sizer.add(btn, proportion=1., borders=borders)
        btn = DialogButton(group, "None", command=lambda: self.__modify_types("none"))
        btns.append(btn)
        btn_sizer.add(btn, proportion=1., borders=borders)
        btn = DialogButton(group, "Invert", command=lambda: self.__modify_types("invert"))
        btns.append(btn)
        btn_sizer.add(btn, proportion=1.)

        if object_types:
            for btn in btns:
                btn.enable(False)

        group = DialogWidgetGroup(self, "Selection set")
        column2_sizer.add(group, expand=True)

        combobox = DialogComboBox(group, 150, tooltip_text="Selection set")
        self._set_combobox = combobox
        group.add(combobox, expand=True)
        sets = sel_set_data["sets"]
        get_command = lambda set_id: lambda: self.__select_from_set(sets, set_id)

        for set_id, set_name in sel_set_data["names"].items():
            combobox.add_item(set_id, set_name, get_command(set_id), select_initial=False)

        combobox.update_popup_menu()

        info = "Shift-click to select range; Ctrl-click to toggle selection state."

        if not multi_select:
            info += "\nIf multiple names are selected, only the top one will be accepted."

        info += "\nNames of currently selected objects are preceded by an asterisk (*)."
        text = DialogText(self, info)
        borders = (20, 20, 20, 20)
        client_sizer.add(text, expand=True, borders=borders)

        self.finalize()

    def close(self, answer=""):

        self._checkbuttons = None
        self._fields = None

        if answer == "yes":
            self._selection_ids = self._entry_pane.get_selection()

        self._entry_pane = None

        Dialog.close(self, answer)

        self._selection_ids = []

    def __show_object_types(self, object_types):

        checkbtns = self._checkbuttons
        obj_types = [o_type for o_type in self._obj_types if checkbtns[o_type].is_checked()]

        if not object_types:

            config_data = GD["config"]
            config_data["sel_dialog"]["obj_types"] = obj_types

            with open("config", "wb") as config_file:
                pickle.dump(config_data, config_file, -1)

        self._entry_pane.show_object_types(obj_types)

    def __modify_types(self, mod):

        checkbtns = self._checkbuttons

        if mod == "all":
            obj_types = self._obj_types[:]
        elif mod == "none":
            obj_types = []
        elif mod == "invert":
            obj_types = [o_type for o_type in self._obj_types
                         if not checkbtns[o_type].is_checked()]

        for obj_type in self._obj_types:
            checkbtns[obj_type].check(obj_type in obj_types)

        config_data = GD["config"]
        config_data["sel_dialog"]["obj_types"] = obj_types

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        self._entry_pane.show_object_types(obj_types)

    def __set_case_sort(self, on, object_types):

        config_data = GD["config"]
        config_data["sel_dialog"]["sort_case"] = on

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        self.__show_object_types(object_types)

    def __sort_entries(self, sort_by):

        config_data = GD["config"]
        config_data["sel_dialog"]["sort"] = sort_by

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

        self._entry_pane.sort_entries(sort_by)

    def __set_search_option(self, option, value):

        if option == "in_sel":
            self._search_in_selection = value
            return

        config_data = GD["config"]
        config_data["sel_dialog"]["search"][option] = value

        with open("config", "wb") as config_file:
            pickle.dump(config_data, config_file, -1)

    def __search_entries(self, name):

        self._entry_pane.search_entries(name, self._search_in_selection)

    def __parse_substring(self, input_text):

        return input_text if input_text else None

    def __modify_selection(self, mod):

        self._entry_pane.modify_selection(mod)

    def __select_from_set(self, sets, set_id):

        selection_set = sets[set_id]
        self._set_combobox.select_item(set_id)
        self._entry_pane.select_from_set(selection_set)

    def __set_selection(self):

        Mgr.update_remotely("object_selection", "replace", *self._selection_ids)

    def hide_set_name(self):

        self._set_combobox.select_none()

    def update_layout(self):

        self._entry_pane.reset_sub_image_index()
        Dialog.update_layout(self)

    def update_widget_positions(self):

        self._entry_pane.update_quad_pos()
        self._entry_pane.update_widget_root_node()
