from ..dialog import *
from ..button import Button
from ..menu import Menu
from ..icon import LayeredIcon


class ExpandButton(Button):

    _gfx = {
        "normal": (("expand_button_normal",),),
        "active": (("expand_button_active",),),
        "disabled": (("expand_button_disabled",),)
    }

    def __init__(self, parent):

        Button.__init__(self, parent, self._gfx, "", "", "")

        self.set_widget_type("expand_button")

        self.get_mouse_region().set_sort(parent.get_sort())

    def on_left_up(self):

        if Button.on_left_up(self):
            self.set_active(not self.is_active())
            self.get_parent().expand_description(self.is_active())


class TimelineButton(Button):

    _gfx = {
        "normal": (("timeline_button_normal",),),
        "hilited": (("timeline_button_hilited",),),
        "pressed": (("timeline_button_pressed",),),
        "active": (("timeline_button_active",),)
    }
    _ref_node = NodePath("timeline_btn_ref_node")
    _menu_offsets = {}

    @classmethod
    def set_ref_node_pos(cls, pos):

        cls._ref_node.set_pos(pos)

    def __init__(self, parent, entries, commands):

        Button.__init__(self, parent, self._gfx, "", "", "Choose timeline", self.__show_menu)

        self.set_widget_type("timeline_button")
        self.get_mouse_region().set_sort(parent.get_sort())

        self._menu = menu = Menu(on_hide=self.__on_hide)

        for entry, command in zip(entries, commands):
            event = entry.get_event()
            timestamp = event.get_timestamp()
            descr_start = event.get_description_start()
            text = timestamp + "  |  " + descr_start
            menu.add(entry, text, command, item_type="radio")

        menu.check_radio_item(entries[0])
        menu.update()

        if not self._menu_offsets:
            x, y, w, h = TextureAtlas["regions"]["timeline_button_normal"]
            x = w - 260
            self._menu_offsets["top"] = (x, 0)
            self._menu_offsets["bottom"] = (x, h)

    def destroy(self):

        Button.destroy(self)

        self._menu.destroy()
        self._menu = None

    def get_menu(self):

        return self._menu

    def __on_hide(self):

        if self.is_active():
            self.set_active(False)
            self.on_leave(force=True)

    def __show_menu(self):

        pane = self.get_ancestor("history_pane")
        pane.set_clicked_entry(self.get_parent())
        self.set_active()
        x, y = self.get_pos(ref_node=self._ref_node)
        offset_x, offset_y = self._menu_offsets["bottom"]
        pos = (x + offset_x, y + offset_y)
        offset_x, offset_y = self._menu_offsets["top"]
        w, h = self._menu.get_size()
        alt_pos = (x + offset_x, y + offset_y - h)
        self._menu.show(pos, alt_pos)


class HistoryEntry(Widget):

    def __init__(self, parent, event, index, is_on):

        Widget.__init__(self, "hist_entry", parent, gfx_data={}, stretch_dir="both")

        sort = parent.get_sort() + 1
        self._sort = sort
        self.get_mouse_region().set_sort(sort)

        self._event = event
        self._index = index
        self._is_on = is_on
        self._has_event_to_del = False
        self._has_event_to_merge = False
        self._image = None
        self._is_selected = False
        colors = Skin["colors"]
        self._colors = {
            "unselected": colors["history_entry_unselected{}".format("_alt" if index % 2 else "")][:3],
            "selected": colors["history_entry_selected{}".format("_alt" if index % 2 else "")][:3]
        }
        timestamp = event.get_timestamp()
        sizer = Sizer("horizontal")
        self.set_sizer(sizer)
        self._subsizer = subsizer = Sizer("horizontal")
        subsizer.set_default_size((260, 0))
        sizer.add(subsizer)
        icon_ids = ["icon_hist_entry_off", "icon_hist_entry_on", "icon_hist_entry_merge",
                    "icon_hist_entry_delete"]
        self._icon = icon = LayeredIcon(self, icon_ids)

        if is_on:
            icon.show_icon("icon_hist_entry_on", True)
            icon.show_icon("icon_hist_entry_off", False, update=True)

        borders = (10, 0, 6, 6)
        subsizer.add(icon, alignment="center_v", borders=borders)
        text = DialogText(self, timestamp)
        borders = (10, 0, 6, 6)
        subsizer.add(text, alignment="center_v", borders=borders)
        subsizer.add((0, 0), proportion=1.)
        self._expand_btn = btn = ExpandButton(self)
        btn.enable(event.get_description_line_count() > 1)
        d = max(0, icon.get_size()[1] - btn.get_size()[1]) // 2
        borders = (10, 0, 6 + d, 6 + d)
        sizer.add(btn, borders=borders)
        descr = event.get_description_start()
        self._description = text = DialogText(self, descr)
        milestone_text = Skin["text"]["milestone"]
        self._text_attribs = {
            "dialog": {"font": text.get_font(), "color": text.get_color()},
            "milestone": {"font": milestone_text["font"], "color": milestone_text["color"]}
        }

        if event.is_milestone():
            text_attr = self._text_attribs["milestone"]
            text = self._description
            text.set_font(text_attr["font"], update=False)
            text.set_color(text_attr["color"])

        borders = (10, 10, 6, 6)
        sizer.add(text, alignment="center_v", borders=borders)

    def get_sort(self):

        return self._sort

    def get_event(self):

        return self._event

    def get_expand_button(self):

        return self._expand_btn

    def add_timeline_button(self, entries, commands):

        btn = TimelineButton(self, entries, commands)
        self._subsizer.add(btn, alignment="center_v")

    def add_timeline_item(self, item):

        self._subsizer.add_item(item)
        item.get_object().set_parent(self)

    def pop_timeline_item(self):

        return self._subsizer.pop_item()

    def set_selected(self, is_selected=True):

        if self._is_selected == is_selected:
            return

        self._is_selected = is_selected
        self._is_on = is_on = not self._is_on

        if is_on and self._has_event_to_del:

            self._has_event_to_del = False
            self._icon.show_icon("icon_hist_entry_delete", False)
            menu = self.get_ancestor("dialog").get_rejected_history_button().get_menu()

            if self in menu.get_items():
                menu.remove(self, destroy=True, update=True)

        self._icon.show_icon("icon_hist_entry_on", is_on)
        self._icon.show_icon("icon_hist_entry_off", not is_on, update=True)
        self.update_images()
        w, h = self.get_size()

        if not self.is_hidden():
            self.get_card().copy_sub_image(self, self.get_image(), w, h, 0, 0)

    def is_selected(self):

        return self._is_selected

    def is_on(self):

        return self._is_on

    def reject_event(self, reject=True):

        if (reject and self._is_on) or self._has_event_to_del == reject:
            return False

        if reject and self._has_event_to_merge:
            self._icon.show_icon("icon_hist_entry_merge", False)
            self._has_event_to_merge = False

        self._has_event_to_del = reject
        self._icon.show_icon("icon_hist_entry_delete", reject)
        self._icon.update()
        self.update_images()
        w, h = self.get_size()

        if not self.is_hidden():
            self.get_card().copy_sub_image(self, self.get_image(), w, h, 0, 0)

        return True

    def has_rejected_event(self):

        return self._has_event_to_del

    def set_event_to_merge(self, merge=True):

        if self._has_event_to_merge == merge:
            return False

        self._has_event_to_merge = merge
        self._icon.show_icon("icon_hist_entry_merge", merge, update=True)
        self.update_images()
        w, h = self.get_size()

        if not self.is_hidden():
            self.get_card().copy_sub_image(self, self.get_image(), w, h, 0, 0)

        return True

    def has_event_to_merge(self):

        return self._has_event_to_merge

    def update_description(self):

        event = self._event
        self._expand_btn.enable(event.get_description_line_count() > 1)
        expand = self._expand_btn.is_active()
        text = event.get_full_description() if expand else event.get_description_start()
        descr = self._description

        if descr.set_text(text):

            descr.get_sizer_item().get_sizer().set_min_size_stale()
            self.get_ancestor("dialog").update_layout()
            item = self._subsizer.get_items()[-1]

            if item.get_type() == "widget":
                menu = item.get_object().get_menu()
                timestamp = event.get_timestamp()
                text = timestamp + "  |  " + event.get_description_start()
                menu.set_item_text(self, text, update=True)

    def expand_description(self, expand=True, update=True):

        event = self._event
        text = event.get_full_description() if expand else event.get_description_start()
        descr = self._description

        if descr.set_text(text):

            descr.get_sizer_item().get_sizer().set_min_size_stale()

            if update:
                self.get_ancestor("dialog").update_layout()

    def toggle_milestone(self):

        is_milestone = not self._event.is_milestone()
        self._event.set_as_milestone(is_milestone)
        text_attr = self._text_attribs["milestone" if is_milestone else "dialog"]
        descr = self._description
        descr.set_font(text_attr["font"], update=False)
        descr.set_color(text_attr["color"])
        descr.get_sizer_item().get_sizer().set_min_size_stale()
        self.get_ancestor("dialog").update_layout()

    def update_images(self, recurse=True, size=None):

        w, h = self.get_size()
        self._image = image = PNMImage(w, h, 4)
        image.fill(*self._colors["selected" if self._is_selected else "unselected"])
        image.alpha_fill(1.)
        pane = self.get_ancestor("history_pane")

        if pane.get_current_entry() is self:
            painter = PNMPainter(image)
            pen = PNMBrush.make_pixel((0., 0., 0., 1.))
            fill = PNMBrush.make_transparent()
            painter.set_pen(pen)
            painter.set_fill(fill)
            painter.draw_rectangle(262, 2, w - 3, h - 3)

        if recurse:
            self.get_sizer().update_images()

    def get_image(self, state=None, composed=True):

        image = PNMImage(self._image)

        if composed:
            image = self.get_sizer().get_composed_image(image)

        return image

    def on_left_down(self):

        pane = self.get_ancestor("history_pane")
        pane.set_clicked_entry(self)
        ctrl_down = Mgr.get("mouse_watcher").is_button_down("control")
        shift_down = Mgr.get("mouse_watcher").is_button_down("shift")

        if ctrl_down:
            if shift_down:
                pane.set_range_to_merge()
            else:
                pane.toggle_entry_to_merge()
        else:
            pane.select_entries()

    def on_right_down(self):

        pane = self.get_ancestor("history_pane")
        pane.set_clicked_entry(self)
        pane.show_menu(self)


class StartPanel:

    def __init__(self):

        self._next_panel = None
        self._next_panels = []

    def destroy(self):

        self._next_panel = None
        self._next_panels = []

    def get_previous_panel(self):

        return None

    def get_previous_panels(self):

        return []

    def set_next_panel(self, panel):

        self._next_panel = panel

    def get_next_panel(self):

        return self._next_panel

    def get_next_panels(self):

        return self._next_panels

    def get_entries(self):

        return []

    def show(self): pass

    def hide(self): pass


class HistoryPanel(Widget):

    def __init__(self, parent, prev_panel, events, entry_offset, past):

        Widget.__init__(self, "history_panel", parent, gfx_data={}, stretch_dir="both",
                        has_mouse_region=False, hidden=True)

        self.get_node().reparent_to(parent.get_widget_root_node())

        self._prev_panel = prev_panel
        self._prev_panels = prev_panel.get_previous_panels() + [prev_panel] if prev_panel else []
        self._next_panel = None
        self._next_panels = []
        self._entries = entries = []

        sizer = Sizer("vertical")
        self.set_sizer(sizer)

        for i, event in enumerate(events):

            is_current_entry = event.get_time_id() == parent.get_current_time_id()
            is_on = is_current_entry or event in past
            entry = HistoryEntry(self, event, i + entry_offset, is_on)
            entries.append(entry)
            sizer.add(entry, expand=True, index=0)

            if event.is_milestone():
                parent.add_milestone(entry)

            if is_current_entry:
                parent.set_current_entry(entry)

    def destroy(self):

        Widget.destroy(self)

        self._prev_panel = None
        self._prev_panels = []
        self._next_panel = None
        self._next_panels = []
        self._entries = []

    def add_timeline_button(self, entries, commands):

        entry = self.get_sizer().get_items()[-1].get_object()
        entry.add_timeline_button(entries, commands)

    def add_timeline_item(self, item):

        entry = self.get_sizer().get_items()[-1].get_object()
        entry.add_timeline_item(item)

    def pop_timeline_item(self):

        entry = self.get_sizer().get_items()[-1].get_object()
        return entry.pop_timeline_item()

    def get_sort(self):

        return self.get_parent().get_sort()

    def update_images(self, recurse=True, size=None):

        if recurse:
            self.get_sizer().update_images()

    def get_image(self, state=None, composed=True):

        w, h = self.get_size()
        image = PNMImage(w, h, 4)

        if composed:
            image = self.get_sizer().get_composed_image(image)

        return image

    def get_previous_panel(self):

        return self._prev_panel

    def get_previous_panels(self):

        return self._prev_panels

    def set_next_panel(self, panel):

        self._next_panel = panel

    def get_next_panel(self):

        return self._next_panel

    def get_next_panels(self):

        return self._next_panels

    def get_entries(self):

        return self._entries


class HistoryPane(DialogScrollPane):

    def __init__(self, dialog, history, past, current_time_id):

        DialogScrollPane.__init__(self, dialog, "history_pane", "vertical", (700, 300), "both")
        mouse_watcher = self.get_mouse_watcher()
        mouse_watcher.remove_region(DialogInputField.get_mouse_region_mask())

        self._start_time_id = history.get_time_id()
        self._current_time_id = current_time_id
        self._current_entry = None
        self._start_entry = None
        self._clicked_entry = None
        self._selected_entry = None
        self._merge_start_entry = None
        self._entries = entries = {}
        self._misc_change = False

        self._start_panel = start_panel = StartPanel()
        panel_data = [(None, history, 0)]
        self._panels = panels = []

        while panel_data:
            prev_panel, event, event_index = panel_data.pop()
            self.__create_panel(panel_data, prev_panel, event, event_index, past)

        if not panels:
            return

        for panel in panels:
            for entry in panel.get_entries():
                entries[entry.get_event()] = entry

        def get_command(panel):

            def command():

                clicked_panel = self._clicked_entry.get_parent()

                if panel is not clicked_panel:
                    item = clicked_panel.pop_timeline_item()
                    self.__show_panel(clicked_panel, False)
                    prev_panel = panel.get_previous_panel()
                    prev_panel.set_next_panel(panel)
                    self.__show_panel(panel)
                    panel.add_timeline_item(item)
                    scrollthumb = self.get_scrollthumb()
                    h = self.get_sizer().get_virtual_size()[1] - scrollthumb.get_offset()
                    self.get_dialog().update_layout()
                    scrollthumb.set_offset(self.get_sizer().get_virtual_size()[1] - h)

            return command

        for panel in [start_panel] + panels:

            next_panels = panel.get_next_panels()

            if next_panels:

                panel0 = next_panels[0]
                panel.set_next_panel(panel0)

                if len(next_panels) > 1:

                    entries = []
                    commands = []

                    for next_panel in next_panels:
                        start_entry = next_panel.get_entries()[0]
                        entries.append(start_entry)
                        commands.append(get_command(next_panel))

                    panel0.add_timeline_button(entries, commands)

        self.__show_panel(start_panel)

        if not self._start_entry:
            self._start_entry = start_panel.get_next_panel().get_entries()[0]

        self._menu = menu = Menu()
        self._menu_items = menu_items = {}
        command = self.select_entries
        item = menu.add("select", "Select range of events to undo/redo", command, item_type="check")
        menu_items["select"] = item
        command = self.__edit_user_description
        menu_items["edit"] = menu.add("edit", "Edit custom description...", command)
        command = self.__toggle_milestone
        menu_items["milestone"] = menu.add("milestone", "Set as milestone", command, item_type="check")
        menu.add("sep0", item_type="separator")
        text = "Mark event for merging with preceding event"
        command = self.toggle_entry_to_merge
        menu_items["merge"] = menu.add("merge", text, command, item_type="check")
        menu.set_item_hotkey("merge", None, "Ctrl+LMB")
        text = "(Un)mark range of events for merging"
        command = self.set_range_to_merge
        menu_items["merge_range"] = item = menu.add("merge_range", text, command)
        item.enable(False)
        menu.set_item_hotkey("merge_range", None, "Shift+Ctrl+LMB")
        text = "Reject inactive history, starting here"
        command = self.__reject_events
        menu_items["reject"] = menu.add("reject", text, command)
        text = "Accept inactive history, starting here"
        command = lambda: self.__reject_events(False)
        menu_items["accept"] = menu.add("accept", text, command)
        menu.add("sep1", item_type="separator")
        text = "Expand all multiline descriptions"
        command = self.__expand_all_entries
        menu_items["expand_all"] = menu.add("expand_all", text, command)
        text = "Collapse all multiline descriptions"
        command = lambda: self.__expand_all_entries(False)
        menu_items["collapse_all"] = menu.add("collapse_all", text, command)
        menu.update()

    def __create_panel(self, panel_data, prev_panel, event, event_index, past):

        events = [event] if prev_panel else []
        next_events = event.get_next_events()

        while len(next_events) == 1:
            next_event = next_events[0]
            events.append(next_event)
            next_events = next_event.get_next_events()

        event_count = len(events)

        if events and not prev_panel:
            prev_panel = self._start_panel

        if prev_panel:
            panel = HistoryPanel(self, prev_panel, events, event_index % 2, past)
            self._panels.append(panel)
            self.get_sizer().add(panel, expand=True, index=0)
            next_panels = prev_panel.get_next_panels()
            next_panels.append(panel)
        else:
            panel = self._start_panel

        event_index += event_count

        if next_events:
            for next_event in next_events:
                panel_data.append((panel, next_event, event_index))

    def _copy_widget_images(self, pane_image): 

        root_node = self.get_widget_root_node()

        for panel in self._panels:
            if not panel.is_hidden():
                x, y = panel.get_pos(ref_node=root_node)
                offset_x, offset_y = panel.get_image_offset()
                pane_image.copy_sub_image(panel.get_image(), x + offset_x, y + offset_y, 0, 0)

    def destroy(self):

        DialogScrollPane.destroy(self)

        self._current_entry = None
        self._clicked_entry = None
        self._selected_entry = None
        self._merge_start_entry = None
        self._entries = {}
        self._start_panel.destroy()
        self._start_panel = None
        self._panels = []
        self._menu.destroy()
        self._menu = None

    def __jump_to_entry(self, entry):

        self.__show_panel(self._start_panel, False)
        panel = entry.get_parent()
        layout_stale = False

        for prev_panel in reversed(panel.get_previous_panels()):

            if prev_panel.get_next_panel() is not panel:
                item = prev_panel.get_next_panel().pop_timeline_item()
                panel.add_timeline_item(item)
                prev_panel.set_next_panel(panel)
                menu = item.get_object().get_menu()
                menu.check_radio_item(panel.get_entries()[0])
                layout_stale = True

            panel = prev_panel

        self.__show_panel(self._start_panel)

        if layout_stale:
            self.get_dialog().update_layout()

        offset = entry.get_pos(from_root=True)[1]
        self.get_scrollthumb().set_offset(offset)

    def __add_to_menu(self, menu, entry, update=True):

        event = entry.get_event()
        timestamp = event.get_timestamp()
        descr_start = event.get_description_start()
        text = timestamp + "  |  " + descr_start
        command = lambda: self.__jump_to_entry(entry)
        menu.add(entry, text, command, update=update)

    def __show_panel(self, panel, show=True):

        panels = [panel]
        next_panel = panel.get_next_panel()

        while next_panel:
            panels.append(next_panel)
            next_panel = next_panel.get_next_panel()

        for panel in panels:
            panel.show() if show else panel.hide()

    def show_menu(self, entry):

        can_merge = self.__can_merge_event(entry)
        self._menu_items["merge"].enable(can_merge)
        self._menu_items["merge"].check(entry.has_event_to_merge())
        self._menu_items["select"].check(entry is self._selected_entry)
        self._menu_items["milestone"].check(entry.get_event().is_milestone())
        self._menu.show_at_mouse_pos()

    def get_current_time_id(self):

        return self._current_time_id

    def get_start_time_id(self):

        return self._start_time_id

    def get_start_panel(self):

        return self._start_panel

    def jump_to_current_entry(self):

        self.__jump_to_entry(self._start_entry)

    def set_current_entry(self, entry):

        self._current_entry = self._start_entry = entry

    def get_current_entry(self):

        return self._current_entry

    def set_clicked_entry(self, entry):

        self._clicked_entry = entry

    def get_clicked_entry(self):

        return self._clicked_entry

    def __clear_merge_range_start(self):

        self._merge_start_entry = None
        self._menu_items["merge_range"].enable(False)
        text = "(Un)mark range of events for merging"
        self._menu.set_item_text("merge_range", text, update=True)

    def __can_merge_event(self, entry):

        # An event can not be merged if it is rejected, if its entry is off and the preceding entry
        # is on, or if it is the 1st event of a timeline, unless the alternate timelines are rejected.

        can_merge = True

        if entry.has_rejected_event():

            can_merge = False

        else:

            event = entry.get_event()
            prev_entry = self._entries.get(event.get_previous_event())

            if prev_entry and prev_entry.is_on() and not entry.is_on():
                can_merge = False

            if can_merge:

                panel = entry.get_parent()

                if entry is panel.get_entries()[0]:

                    prev_panel = prev_entry.get_parent() if prev_entry else self._start_panel
                    next_panels = prev_panel.get_next_panels()

                    for next_panel in next_panels:

                        if next_panel is panel:
                            continue

                        other_entry = next_panel.get_entries()[0]

                        if not other_entry.has_rejected_event():
                            can_merge = False
                            break

        return can_merge

    def __edit_user_description(self):

        entry = self._clicked_entry
        event = entry.get_event()
        user_descr = event.get_user_description().replace("|", "\\|")
        user_descr = user_descr.replace("\n", "|")

        def command(new_descr):

            if new_descr != user_descr:

                new_descr = new_descr.replace("\\|", chr(13))
                new_descr = new_descr.replace("|", "\n")
                new_descr = new_descr.replace(chr(13), "|")
                event.set_user_description(new_descr)
                entry.update_description()

                timestamp = event.get_timestamp()
                descr_start = event.get_description_start()
                text = timestamp + "  |  " + descr_start

                if entry.get_event().is_milestone():
                    menu = self.get_dialog().get_milestone_button().get_menu()
                    menu.set_item_text(entry, text, update=True)

                menu = self.get_dialog().get_rejected_history_button().get_menu()

                if entry in menu.get_items():
                    menu.set_item_text(entry, text, update=True)

        InputDialog(title="Custom description",
                    message="Enter a custom description for this event"
                            " (type '|' to start a new line;"
                            "\nto include '|' itself, type '\|'):",
                    default_input=user_descr,
                    on_yes=command)

        self._misc_change = True

    def add_milestone(self, entry):

        menu = self.get_dialog().get_milestone_button().get_menu()
        self.__add_to_menu(menu, entry)

    def __toggle_milestone(self):

        entry = self._clicked_entry
        entry.toggle_milestone()
        event = entry.get_event()
        menu = self.get_dialog().get_milestone_button().get_menu()

        if event.is_milestone():
            self.__add_to_menu(menu, entry)
        else:
            menu.remove(entry, update=True, destroy=True)

        self._misc_change = True

    def __get_selected_entries(self):

        cur_entry = self._current_entry
        cur_panel = cur_entry.get_parent() if cur_entry else None
        cur_panel_entries = cur_panel.get_entries() if cur_entry else []
        cur_index = cur_panel_entries.index(cur_entry) if cur_entry else -1
        cur_panel_prev = cur_panel.get_previous_panels() if cur_entry else []
        sel_entry = self._selected_entry
        sel_panel = sel_entry.get_parent()
        sel_panel_entries = sel_panel.get_entries()
        sel_index = sel_panel_entries.index(sel_entry)
        sel_panel_prev = sel_panel.get_previous_panels()

        to_undo = []
        to_redo = []

        if not cur_panel:

            for panel in sel_panel_prev:
                to_redo.extend(panel.get_entries())

            to_redo.extend(sel_panel_entries[:sel_index + 1])

        elif sel_panel is cur_panel:

            if sel_index <= cur_index:
                to_undo = cur_panel_entries[sel_index:cur_index + 1]
            else:
                to_redo = cur_panel_entries[cur_index + 1:sel_index + 1]

        elif sel_panel in cur_panel_prev:

            to_undo = sel_panel_entries[sel_index:]
            sel_panel_index = cur_panel_prev.index(sel_panel)

            for panel in cur_panel_prev[sel_panel_index + 1:]:
                to_undo.extend(panel.get_entries())

            to_undo.extend(cur_panel_entries[:cur_index + 1])

        elif cur_panel in sel_panel_prev:

            to_redo = cur_panel_entries[cur_index + 1:]
            cur_panel_index = sel_panel_prev.index(cur_panel)

            for panel in sel_panel_prev[cur_panel_index + 1:]:
                to_redo.extend(panel.get_entries())

            to_redo.extend(sel_panel_entries[:sel_index + 1])

        else:

            index = 0

            for panel in sel_panel_prev:

                if panel not in cur_panel_prev:
                    break

                index += 1

            for panel in cur_panel_prev[index:]:
                to_undo.extend(panel.get_entries())

            to_undo.extend(cur_panel_entries[:cur_index + 1])

            for panel in sel_panel_prev[index:]:
                to_redo.extend(panel.get_entries())

            to_redo.extend(sel_panel_entries[:sel_index + 1])

        to_undo = to_undo[::-1]

        return to_undo, to_redo

    def select_entries(self):

        # determine old selection of entries
        if self._selected_entry:
            to_undo, to_redo = self.__get_selected_entries()
            old_off_entries = to_undo[::-1]
            old_on_entries = to_redo
            old_selection = set(to_undo + to_redo)
        else:
            old_off_entries = []
            old_on_entries = []
            old_selection = set()

        entry = self._clicked_entry

        # determine new selection of entries
        if self._selected_entry is entry:
            # Deselect all entries.
            self._selected_entry = None
            new_off_entries = []
            new_on_entries = []
            new_selection = set()
        else:
            # Select a new entry range.
            self._selected_entry = entry
            to_undo, to_redo = self.__get_selected_entries()
            new_off_entries = to_undo[::-1]
            new_on_entries = to_redo
            new_selection = set(to_undo + to_redo)

        s = set(old_off_entries)
        s.update(old_on_entries, new_off_entries, new_on_entries)
        s -= old_selection & new_selection

        for entry in s.copy():
            event = entry.get_event()
            s.update(self._entries[next_evt] for next_evt in event.get_next_events())

        for entries in (old_off_entries, old_on_entries, new_off_entries, new_on_entries):
            if entries:
                event = entries[0].get_event().get_previous_event()
                s.update(self._entries[next_evt] for next_evt in event.get_next_events())

        for entry in new_selection - old_selection:
            entry.set_selected()

        for entry in old_selection - new_selection:
            entry.set_selected(False)

        # Accept rejected history that has become selected and update the associated menu.

        menu = self.get_dialog().get_rejected_history_button().get_menu()

        if old_selection and old_off_entries:

            entry = old_off_entries[0]
            event = entry.get_event()

            for entry in old_off_entries:

                if not entry.is_on():
                    break

                event = entry.get_event()
                next_entries = [self._entries[next_evt] for next_evt in event.get_next_events()]

                for next_entry in next_entries:
                    if next_entry.has_rejected_event():
                        self.__add_to_menu(menu, next_entry, update=False)

        if new_selection and new_on_entries:

            entry = new_on_entries[0]
            event = entry.get_event()

            for entry in new_on_entries:

                event = entry.get_event()
                next_entries = [self._entries[next_evt] for next_evt in event.get_next_events()]

                for next_entry in next_entries:
                    if next_entry.has_rejected_event():
                        self.__add_to_menu(menu, next_entry, update=False)

        menu.update()

        # Unmark events to be merged where the new selection no longer allows it.

        for entry in s:
            if entry.has_event_to_merge() and not self.__can_merge_event(entry):
                entry.set_event_to_merge(False)

        self.__clear_merge_range_start()

    def __reject_events(self, reject=True):

        entry = self._clicked_entry
        panel = entry.get_parent()
        entries = panel.get_entries()
        index = entries.index(entry)
        menu = self.get_dialog().get_rejected_history_button().get_menu()
        menu_items = menu.get_items()

        if reject:

            self.__reject_events(False)

            if not entry.is_on():
                self.__add_to_menu(menu, entry, update=False)

            for entry in entries[index:]:

                if entry.has_rejected_event():
                    menu.update()
                    return

                if entry.reject_event():

                    prev_entry = self._entries.get(entry.get_event().get_previous_event())

                    if not prev_entry or prev_entry.is_on():
                        self.__add_to_menu(menu, entry, update=False)

        else:

            for entry in reversed(entries):

                if not entry.has_rejected_event():
                    break

                if entry.reject_event(False):

                    if entry in menu_items:
                        menu.remove(entry, destroy=True, update=False)

                    event = entry.get_event()
                    next_events = event.get_next_events()
                    next_entries = [self._entries[next_evt] for next_evt in next_events]

                    for next_entry in next_entries:
                        if next_entry.has_rejected_event():
                            self.__add_to_menu(menu, next_entry, update=False)

                    if entry is entries[0]:

                        next_events = event.get_previous_event().get_next_events()
                        next_entries = [self._entries[next_evt] for next_evt in next_events]

                        for next_entry in next_entries:
                            if next_entry.has_event_to_merge():
                                next_entry.set_event_to_merge(False)

            else:

                for prev_panel in reversed(panel.get_previous_panels()):

                    entries = prev_panel.get_entries()

                    for entry in reversed(entries):

                        if not entry.has_rejected_event():
                            break

                        if entry.reject_event(False):

                            if entry in menu_items:
                                menu.remove(entry, destroy=True, update=False)

                            event = entry.get_event()
                            next_events = event.get_next_events()
                            next_entries = [self._entries[next_evt] for next_evt in next_events]

                            for next_entry in next_entries:
                                if next_entry.has_rejected_event():
                                    self.__add_to_menu(menu, next_entry, update=False)

                            if entry is entries[0]:

                                next_events = event.get_previous_event().get_next_events()
                                next_entries = [self._entries[next_evt] for next_evt in next_events]

                                for next_entry in next_entries:
                                    if next_entry.has_event_to_merge():
                                        next_entry.set_event_to_merge(False)

                    else:

                        continue

                    break

        panels = panel.get_next_panels()[:]

        while panels:

            panel = panels.pop()
            entries = panel.get_entries()

            for entry in entries:

                if reject and entry.has_rejected_event():
                    break

                entry.reject_event(reject)

                if reject:

                    if entry.has_rejected_event():

                        prev_entry = self._entries.get(entry.get_event().get_previous_event())

                        if not prev_entry or prev_entry.is_on():
                            self.__add_to_menu(menu, entry, update=False)

                elif not entry.has_rejected_event():

                    if entry in menu_items:
                        menu.remove(entry, destroy=True, update=False)

                    if entry is entries[0]:

                        next_events = entry.get_event().get_previous_event().get_next_events()
                        next_entries = [self._entries[next_evt] for next_evt in next_events]

                        for next_entry in next_entries:
                            if next_entry.has_event_to_merge():
                                next_entry.set_event_to_merge(False)

            else:

                panels.extend(panel.get_next_panels())

        menu.update()

        self.__clear_merge_range_start()

    def toggle_entry_to_merge(self):

        self._merge_start_entry = entry = self._clicked_entry
        entry.set_event_to_merge(not entry.has_event_to_merge())
        self._menu_items["merge_range"].enable()
        merge = entry.has_event_to_merge()
        text = "{}ark range of events for merging".format("M" if merge else "Unm")
        self._menu.set_item_text("merge_range", text, update=True)

    def set_range_to_merge(self):

        start_entry = self._merge_start_entry

        if not start_entry:
            return

        start_panel = start_entry.get_parent()
        start_panel_entries = start_panel.get_entries()
        start_index = start_panel_entries.index(start_entry)
        start_panel_prev = start_panel.get_previous_panels()
        end_entry = self._clicked_entry
        end_panel = end_entry.get_parent()
        end_panel_entries = end_panel.get_entries()
        end_index = end_panel_entries.index(end_entry)
        end_panel_prev = end_panel.get_previous_panels()

        entries = []

        if end_panel is start_panel:

            if end_index <= start_index:
                entries = start_panel_entries[end_index:start_index]
            else:
                entries = start_panel_entries[start_index + 1:end_index + 1]

        elif end_panel in start_panel_prev:

            entries = end_panel_entries[end_index:]
            end_panel_index = start_panel_prev.index(end_panel)

            for panel in start_panel_prev[end_panel_index + 1:]:
                entries.extend(panel.get_entries())

            entries.extend(start_panel_entries[:start_index])

        elif start_panel in end_panel_prev:

            entries = start_panel_entries[start_index + 1:]
            start_panel_index = end_panel_prev.index(start_panel)

            for panel in end_panel_prev[start_panel_index + 1:]:
                entries.extend(panel.get_entries())

            entries.extend(end_panel_entries[:end_index + 1])

        else:

            index = 0

            for panel in end_panel_prev:

                if panel not in start_panel_prev:
                    break

                index += 1

            for panel in start_panel_prev[index:]:
                entries.extend(panel.get_entries())

            entries.extend(start_panel_entries[:start_index])

            for panel in end_panel_prev[index:]:
                entries.extend(panel.get_entries())

            entries.extend(end_panel_entries[:end_index + 1])

        merge = start_entry.has_event_to_merge()

        for entry in entries:
            if merge:
                if self.__can_merge_event(entry):
                    entry.set_event_to_merge()
            else:
                entry.set_event_to_merge(False)

        self.__clear_merge_range_start()

    def __expand_all_entries(self, expand=True):

        panel = self._start_panel.get_next_panel()

        while panel:

            for entry in panel.get_entries():
                entry.expand_description(expand, update=False)
                entry.get_expand_button().set_active(expand)

            panel = panel.get_next_panel()

        self.get_dialog().update_layout()

    def get_history_to_undo_redo(self):

        if not self._selected_entry:
            return [], []

        entries_to_undo, entries_to_redo = self.__get_selected_entries()
        to_undo = [entry.get_event() for entry in entries_to_undo]
        to_redo = [entry.get_event() for entry in entries_to_redo]

        return to_undo, to_redo

    def get_history_to_delete(self):

        entries = iter(self.get_dialog().get_rejected_history_button().get_menu().get_items().keys())

        return [entry.get_event() for entry in entries]

    def get_history_to_merge(self):

        # return a list of end-of-range events, with all events in the range having
        # their self._to_be_merged flag set to True through event.set_to_be_merged(),
        # retrievable through event.is_to_be_merged()
        # (the actual range of events set to be merged is shifted down by 1 event, since events
        # are merged up, not down)
        to_merge = []
        panels = self._start_panel.get_next_panels()
        entries = self._entries

        for panel in panels:

            events = [panel.get_entries()[0].get_event()]

            while events:

                event = events.pop()
                entry = entries[event]

                if entry.has_rejected_event():
                    continue

                if entry.has_event_to_merge():

                    event.set_to_be_merged()
                    to_merge.append(event)
                    prev_event = event.get_previous_event()

                    if prev_event.is_to_be_merged():
                        # only end-of-range events must be returned
                        to_merge.remove(prev_event)
                    else:
                        # the first event in a range must have its preceding event merged into it
                        # (since events are actually merged up, not down)
                        prev_event.set_to_be_merged()

                events.extend(event.get_next_events())

        for event in to_merge:
            # the end-of-range events themselves should not be set to be merged into the events
            # that follow them
            event.set_to_be_merged(False)

        return to_merge

    def get_history_to_restore(self):

        if not self._selected_entry:
            return None
        elif self._selected_entry.is_on():
            return self._selected_entry.get_event().get_time_id()
        else:
            prev_event = self._selected_entry.get_event().get_previous_event()
            return prev_event.get_time_id() if prev_event else self._start_time_id

    def get_miscellaneous_change(self):

        return self._misc_change


class HistoryDialog(Dialog):

    def __init__(self, history, time_id, past):

        def update_history():

            Mgr.update_app("history", "update", self._to_undo, self._to_redo, self._to_delete,
                           self._to_merge, self._to_restore, self._set_unsaved)

        extra_button_data = (("Archive", "Merge all history", self.__archive_history, None, 4.),)
        Dialog.__init__(self, "History", choices="okcancel", on_yes=update_history,
                        extra_button_data=extra_button_data)

        self._history = history
        self._history_root = history["root"]
        Mgr.expose("history_event", lambda time_id: self._history.get(time_id))

        client_sizer = self.get_client_sizer()

        text = DialogText(self,
                          "Left-click an entry to select a range of events to"
                          " be undone and/or redone"
                          " (left-click it again to select none).\n"
                          "Right-click an entry for more options."
                          "\nNOTE: rejected events will be permanently deleted."
                         )
        borders = (15, 15, 15, 15)
        client_sizer.add(text, borders=borders)

        subsizer = Sizer("horizontal")
        client_sizer.add(subsizer, borders=borders)
        self._milestone_btn = btn = DialogDropdownButton(self, "To milestone...")
        subsizer.add(btn)
        subsizer.add((20, 0))
        self._rejected_hist_btn = btn = DialogDropdownButton(self, "To rejected history...")
        subsizer.add(btn)
        subsizer.add((20, 0))
        self._hist_pane = pane = HistoryPane(self, self._history_root, past, time_id)
        frame = pane.get_frame()
        client_sizer.add(frame, proportion=1., expand=True, borders=borders)
        btn = DialogButton(self, "To current event", command=pane.jump_to_current_entry)
        subsizer.add(btn)

        self.finalize()

        pane.jump_to_current_entry()

    def __archive_history(self):

        def on_yes():

            self.close()
            Mgr.update_app("history", "archive")

        MessageDialog(title="Confirm archive history",
                      message=("You are about to archive the entire history!"
                      "\n\nAll inactive history will be deleted and the remaining"
                      "\nevents will be merged, making it impossible to undo or"
                      "\nredo any of these events."
                      "\n\nAlso, all edits made in the history dialog will be discarded."),
                      choices="okcancel", on_yes=on_yes,
                      icon_id="icon_exclamation")

    def close(self, answer=""):

        if answer == "yes":
            pane = self._hist_pane
            self._to_undo, self._to_redo = pane.get_history_to_undo_redo()
            self._to_delete = pane.get_history_to_delete()
            self._to_merge = pane.get_history_to_merge()
            self._to_restore = pane.get_history_to_restore()
            self._set_unsaved = self._to_delete or self._to_merge or pane.get_miscellaneous_change()
            self._history_root.update_user_data()

        self._history_root.reset_temp_user_data()
        self._history_root = None

        Dialog.close(self, answer)

        if answer == "yes":
            self._on_yes()
            self._to_undo = []
            self._to_redo = []
            self._to_delete = []
            self._to_merge = []
            self._to_restore = None
            self._set_unsaved = False

    def get_milestone_button(self):

        return self._milestone_btn

    def get_rejected_history_button(self):

        return self._rejected_hist_btn

    def update_layout(self):

        self._hist_pane.reset_sub_image_index()
        Dialog.update_layout(self)

    def update_widget_positions(self):

        pane = self._hist_pane
        pane.update_quad_pos()
        pane.update_widget_root_node()
        x, y = pane.get_pos(from_root=True)
        TimelineButton.set_ref_node_pos((-x, 0, y))
