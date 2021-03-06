from ..dialog import *
from .input_dialog import InputDialog


class ListEntry(Widget):

    colors = None

    def __init__(self, parent):

        Widget.__init__(self, "list_entry", parent, gfx_ids={})

        self.mouse_region.sort = parent.sort + 1
        self.node.reparent_to(parent.widget_root_node)

        self.sizer = Sizer("horizontal")
        self._image = None
        self._is_selected = False
        self._text = {}
        self._text_sizers = {}
        self._min_default_widths = {}

    def set_data(self, data, borders):

        sizer = self.sizer
        min_default_widths = self._min_default_widths

        for text_id, text, alignment, width, proportion in data:

            subsizer = Sizer("horizontal")
            subsizer.set_column_proportion(0, 1.)
            sizer.add(subsizer, proportions=(proportion, 0.), borders=borders)
            self._text_sizers[text_id] = subsizer

            if text:
                subsizer.add(DialogText(self, text), alignments=(alignment, "min"))
            else:
                subsizer.add((0, 0))

            self._text[text_id] = text

            subsizer.default_size = (width, 0)
            min_default_widths[text_id] = width

        sizer.update_min_size()

    def get_text(self, text_id):

        return self._text[text_id]

    def set_text(self, text_id, text):

        self._text[text_id] = text
        sizer = self._text_sizers[text_id]

        for i, cell in enumerate(sizer.cells[:]):
            if cell.type == "widget":
                sizer.remove_cell(cell)
                sizer.add(DialogText(self, text), index=i)

        min_def_w = self._min_default_widths[text_id]
        sizer.default_size = (max(min_def_w, 0), 0)

    def get_widths(self):

        widths = []
        sizer = self.sizer

        for cell in sizer.cells:
            widths.append(cell.object.min_size[0])

        return widths

    def set_widths(self, widths):

        sizer = self.sizer
        min_default_widths = self._min_default_widths.values()

        for cell, width, min_def_w in zip(sizer.cells, widths, min_default_widths):
            cell.object.default_size = (max(min_def_w, width), 0)

        sizer.update_min_size()

    def set_selected(self, is_selected=True):

        if self._is_selected == is_selected:
            return

        self._is_selected = is_selected
        self.update_images()
        w, h = self.get_size()

        if not self.is_hidden():
            self.card.copy_sub_image(self, self.get_image(), w, h, 0, 0)

    def is_selected(self):

        return self._is_selected

    @property
    def color(self):

        return self.colors["selected" if self._is_selected else "unselected"]

    def update_images(self, recurse=True, size=None):

        w, h = self.get_size()
        self._image = image = PNMImage(w, h, 4)
        image.fill(*self.color)
        image.alpha_fill(1.)

        if recurse:
            self.sizer.update_images()

    def get_image(self, state=None, composed=True):

        image = PNMImage(self._image)

        if composed:
            image = self.sizer.get_composed_image(image)

        return image

    def on_left_down(self):

        ctrl_down = Mgr.get("mouse_watcher").is_button_down("control")
        shift_down = Mgr.get("mouse_watcher").is_button_down("shift")

        if ctrl_down and shift_down:
            return

        if ctrl_down:
            self.parent.toggle_selected_entry(self)
        elif shift_down:
            self.parent.set_selected_entry_range(self)
        else:
            self.parent.set_selected_entry(self)


class ListPane(DialogScrollPane):

    def __init__(self, parent, column_data, borders, frame_client_size, multi_select=True):

        DialogScrollPane.__init__(self, parent, "list_pane", "vertical", frame_client_size)

        if not ListEntry.colors:
            colors = Skin.colors
            ListEntry.colors = {
                "unselected": colors["list_entry_unselected"][:3],
                "selected": colors["list_entry_selected"][:3]
            }

        self.multi_select = multi_select
        self._search_options = ()

        # when a range is set, the following variable is used to determine the starting entry;
        # if multiple selection is disabled, it is simply a reference to the single selected
        # entry, if any
        self._sel_start_entry = None

        self.entry_list = []

        self._column_sizers = column_sizers = {}
        self._entry_sizer = Sizer("vertical")
        self._entry_sizer.set_column_proportion(0, 1.)
        self.sizer.add(self._entry_sizer, (1., 1.))
        self._width_sizer = width_sizer = Sizer("horizontal")
        self.sizer.add(width_sizer)

        for column_id, proportion in column_data:
            column_sizer = Sizer("vertical")
            width_sizer.add(column_sizer, (proportion, 0.), borders=borders)
            column_sizers[column_id] = column_sizer

        self._is_finalized = False

    def finalize(self):

        self.add_entries()
        self._is_finalized = True

    def destroy(self):

        DialogScrollPane.destroy(self)

        self._sel_start_entry = None
        self.entry_list = []
        self._column_sizers = {}
        self._entry_sizer = None
        self._width_sizer = None

    def __update_entry_widths(self):

        sizer = self.get_ancestor("dialog").client_sizer
        sizer.update_min_size()
        widths = [sizer.min_size[0] for sizer in self._column_sizers.values()]

        for entry in self.entry_list:
            entry.set_widths(widths)

    def add_entries(self, entry_list=None):

        for entry in self.entry_list:
            for width, column_sizer in zip(entry.get_widths(), self._column_sizers.values()):
                column_sizer.add((width, 0))

        self.__update_entry_widths()
        entry_sizer = self._entry_sizer

        for entry in self.entry_list:
            entry_sizer.add(entry)

        self.__update_selection_start_entry()

    def edit_selected_entry_text(self, text_id, title, message, ok_alias, validator, command):

        entry = self._sel_start_entry

        if entry is None:
            return

        old_text = entry.get_text(text_id)

        def on_yes(new_text):

            if new_text == old_text or not validator(new_text):
                return

            entry = self._sel_start_entry
            entry.set_text(text_id, new_text)
            index = self.entry_list.index(entry)

            for width, column_sizer in zip(entry.get_widths(), self._column_sizers.values()):
                cell = column_sizer.cells[index]
                column_sizer.remove_cell(cell)
                column_sizer.add((width, 0), index=index)

            self.__update_entry_widths()

            command(new_text)

        InputDialog(title=title,
                    message=message,
                    default_input=old_text,
                    ok_alias=ok_alias,
                    on_yes=on_yes)

    def remove_selected_entry(self):

        if self._sel_start_entry is None:
            return

        index = self.entry_list.index(self._sel_start_entry)
        self._entry_sizer.remove_cell(self._sel_start_entry.sizer_cell)

        for column_sizer in self._column_sizers.values():
            cell = column_sizer.cells[index]
            column_sizer.remove_cell(cell, destroy=True)

        self.entry_list.remove(self._sel_start_entry)
        self._sel_start_entry = None

        self.__update_entry_widths()

    def clear_entries(self, destroy_entries=False):

        if not destroy_entries:

            widths = [0] * len(self._column_sizers)

            for entry in self.entry_list:
                entry.set_widths(widths)

        for column_sizer in self._column_sizers.values():
            column_sizer.clear()

        self._entry_sizer.clear(destroy_cells=destroy_entries)
        self._sel_start_entry = None

        if destroy_entries:
            self.entry_list = []

    def _copy_widget_images(self, pane_image): 

        if not self._is_finalized:
            return

        root_node = self.widget_root_node

        for entry in self.entry_list:
            x, y = entry.get_pos(ref_node=root_node)
            pane_image.copy_sub_image(entry.get_image(), x, y, 0, 0)

    def __update_selection_start_entry(self, entry_list=None):

        entries = self.entry_list if entry_list is None else entry_list

        for entry in entries:
            if entry.is_selected():
                self._sel_start_entry = entry
                break
        else:
            self._sel_start_entry = None

    def check_selection_start_entry(self):

        if self._sel_start_entry and not self._sel_start_entry.is_selected():
            self.__update_selection_start_entry()

    def search_entries(self, text_id, substring, in_selection, match_case, part, find_next=False):

        if in_selection:
            entry_list = [e for e in self.entry_list if e.is_selected()]
        else:
            entry_list = self.entry_list

        if not self.multi_select:
            self._search_options = (text_id, substring, in_selection, match_case, part)

        selected_entries = []

        for entry in entry_list:

            text = entry.get_text(text_id)

            if part == "start":
                if match_case:
                    selected = text.startswith(substring)
                else:
                    selected = text.casefold().startswith(substring.casefold())
            elif part == "end":
                if match_case:
                    selected = text.endswith(substring)
                else:
                    selected = text.casefold().endswith(substring.casefold())
            elif part == "sub":
                if match_case:
                    selected = substring in text
                else:
                    selected = substring.casefold() in text.casefold()
            elif part == "whole":
                if match_case:
                    selected = substring == text
                else:
                    selected = substring.casefold() == text.casefold()

            if not find_next and (not selected or self.multi_select or not selected_entries):
                entry.set_selected(selected)
            elif entry.is_selected():
                entry.set_selected(False)

            if selected:
                selected_entries.append(entry)

        if not find_next:
            self.__update_selection_start_entry(entry_list)

        return selected_entries

    def find_next(self):

        selected_entries = self.search_entries(*self._search_options, find_next=True)

        if not selected_entries:
            return None

        if len(selected_entries) == 1:
            next_entry = selected_entries[0]
        else:
            for i, entry in enumerate(selected_entries):
                if self._sel_start_entry is entry:
                    entry.set_selected(False)
                    if i == len(selected_entries) - 1:
                        next_entry = selected_entries[0]
                    else:
                        next_entry = selected_entries[i + 1]
                    break
            else:
                next_entry = selected_entries[0]

        next_entry.set_selected()
        self._sel_start_entry = next_entry

        return next_entry

    def get_selected_entry(self):

        return self._sel_start_entry

    def set_selected_entry(self, entry):

        for e in self.entry_list:
            e.set_selected(False)

        entry.set_selected()
        self._sel_start_entry = entry

    def toggle_selected_entry(self, entry):

        if not self.multi_select:
            return False

        entry.set_selected(not entry.is_selected())

        if entry.is_selected():
            self._sel_start_entry = entry
        elif self._sel_start_entry:
            if self._sel_start_entry is entry:
                for e in self.entry_list:
                    if e.is_selected():
                        self._sel_start_entry = e
                        break
                else:
                    self._sel_start_entry = None

        return True

    def set_selected_entry_range(self, end_entry):

        if not self.multi_select:
            return False

        for entry in self.entry_list:
            entry.set_selected(False)

        if not self._sel_start_entry:
            self._sel_start_entry = end_entry

        i1 = self.entry_list.index(self._sel_start_entry)
        i2 = self.entry_list.index(end_entry)
        i1, i2 = min(i1, i2), max(i1, i2)

        for entry in self.entry_list[i1:i2+1]:
            entry.set_selected()

        return True

    def modify_selection(self, mod):

        if not self.multi_select:
            return False

        if mod == "all":
            for entry in self.entry_list:
                entry.set_selected()
        elif mod == "none":
            for entry in self.entry_list:
                entry.set_selected(False)
        elif mod == "invert":
            for entry in self.entry_list:
                entry.set_selected(not entry.is_selected())

        self.__update_selection_start_entry()

        return True

    def select(self, entries):

        for entry in self.entry_list:
            entry.set_selected(entry in entries)

        self.__update_selection_start_entry()


class ListDialog(Dialog):

    def __init__(self, title, choices, ok_alias, on_yes, multi_select):

        Dialog.__init__(self, title, choices, ok_alias, on_yes)

        self.pane = None
        self.multi_select = multi_select

    def __parse_substring(self, input_text):

        return input_text if input_text else None

    def __modify_selection(self, mod):

        self.pane.modify_selection(mod)

    def setup_search_interface(self, widgets, search_handler, search_option_handler,
            match_case, part):

        checkbtns = widgets["checkbuttons"]
        radiobtn_grps = widgets["radiobutton_groups"]

        checkbtn = checkbtns["in_sel"]
        checkbtn.command = lambda checked: search_option_handler("in_sel", checked)
        checkbtn.enable(self.multi_select)

        checkbtn = checkbtns["match_case"]
        checkbtn.command = lambda checked: search_option_handler("match_case", checked)
        checkbtn.check(match_case)

        radio_btns = radiobtn_grps["name_part"]
        btn_ids = ("start", "end", "sub", "whole")

        for btn_id in btn_ids:
            command = lambda value=btn_id: search_option_handler("part", value)
            radio_btns.set_button_command(btn_id, command)

        radio_btns.set_selected_button(part)

        if not self.multi_select:
            next_btn = widgets["buttons"]["find_next"]
            next_btn.command = lambda: self.pane.find_next()
            next_btn.enable(False)

        def name_handler(*args):

            search_handler(args[1])

            if not self.multi_select:
                next_btn.enable()

        field = widgets["fields"]["search"]
        field.value_id = "search"
        field.value_type = "string"
        field.set_value_handler(name_handler)
        field.set_input_parser(self.__parse_substring)

    def setup_selection_buttons(self, buttons):

        btn = buttons["select_all"]
        btn.command = lambda: self.__modify_selection("all")
        btn = buttons["select_none"]
        btn.command = lambda: self.__modify_selection("none")
        btn = buttons["select_inverse"]
        btn.command = lambda: self.__modify_selection("invert")

    def update_layout(self):

        if self.pane:
            self.pane.reset_sub_image_index()

        Dialog.update_layout(self)

    def update_widget_positions(self):

        if self.pane:
            self.pane.update_quad_pos()
            self.pane.update_widget_root_node()
