from ..base import *
import wx.combo


class ListCtrlComboPopup(wx.VListBox, wx.combo.ComboPopup):

    def __init__(self, combo_text="", combo_color=None, text_offset=0, fit_width=True):

        # Since we are using multiple inheritance, and don't know yet
        # which window is to be the parent, we'll do 2-phase create of
        # the VListBox instead, and call its Create method later in
        # our Create method.  (See Create below.)
        self.PostCreate(wx.PreVListBox())

        # Also init the ComboPopup base class.
        wx.combo.ComboPopup.__init__(self)

        self._combo_text = combo_text
        self._combo_color = combo_color
        self._text_offset = text_offset
        self._fit_width = fit_width

    def add_choice(self, choice):

        self._choices.append(choice)
        choice_count = len(self._choices)
        self.SetItemCount(choice_count)

        if choice_count == 1:
            self.GetCombo().Enable()
            self._cur_choice = choice
            self.SetSelection(0)

    def insert_choice(self, index, choice):

        self._choices.insert(index, choice)
        choice_count = len(self._choices)
        self.SetItemCount(choice_count)

        if choice_count == 1:
            self.GetCombo().Enable()
            self._cur_choice = choice
            self.SetSelection(0)

    def remove_choice(self, choice="", index=None):

        if index is not None:
            if -1 < index < len(self._choices):
                choice = self._choices[index]
            else:
                return False

        if choice in self._choices:

            choice_id = self._choices.index(choice)
            self._choices.remove(choice)
            self.SetItemCount(len(self._choices))

            if not self._choices:
                self.GetCombo().Disable()

            if self._cur_choice == choice:
                self._cur_choice = ""

            return choice_id if index is None else True

        return -1

    def clear_choices(self):

        self._choices = []
        self._cur_choice = ""
        self.SetItemCount(0)
        self.GetCombo().Disable()

    def set_current_choice(self, choice_id):

        if choice_id < len(self._choices):
            self._cur_choice = self._choices[choice_id]
            self.Refresh()

    def __on_motion(self, event):

        choice_id = self.HitTest(event.GetPosition())

        if choice_id >= 0:
            self.SetSelection(choice_id)

    def __on_left_down(self, event):

        cur_choice_id = self.GetSelection()
        self._cur_choice = self._choices[cur_choice_id]
        self.GetCombo().OnPopupDismiss(cur_choice_id)
        self.Dismiss()

    # The following methods are those that are overridable from the
    # VListBox base class.

    def OnDrawItem(self, dc, rect, choice_id):

        x, y = rect.GetPosition()
        x += self._text_offset

        if self.GetSelection() == choice_id:
            color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            color = self.GetForegroundColour()

        dc.SetFont(NodePanel.get_fonts()["normal"])
        dc.SetTextForeground(color)

        if choice_id < len(self._choices):
            timestamp, descr = self._choices[choice_id].split("|", 1)
            dc.DrawText(timestamp, x + 6, y + 2)
            dc.DrawText(descr, x + 246, y + 2)

        pen = wx.Pen(color)
        dc.SetPen(pen)
        dc.DrawLine(x + 199, y, x + 199, y + rect.height)

    def OnDrawBackground(self, dc, rect, choice_id):

        if self.GetSelection() == choice_id:
            color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        else:
            color = self._combo_color if self._combo_color else self.GetBackgroundColour()

        pen = wx.Pen(color, 0)
        dc.SetPen(pen)
        brush = wx.Brush(color)
        dc.SetBrush(brush)
        dc.DrawRectangleRect(rect)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, choice_id):

        return self._text_height + 5

    # The following methods are those that are overridable from the
    # ComboPopup base class.

    def Init(self):
        """
        This is called immediately after construction finishes.  You can
        use self.GetCombo if needed to get to the ComboCtrl instance.

        """

        self.GetCombo().Disable()

        self._choices = []
        self._cur_choice = ""

        self._text_height = self.GetCharHeight()

    def Create(self, parent):
        """ Create the popup child control. Return True on success. """

        wx.VListBox.Create(self, parent, style=wx.LB_SINGLE | wx.SIMPLE_BORDER)

        self.Bind(wx.EVT_MOTION, self.__on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self.__on_left_down)

        return True

    def GetControl(self):
        """ Return the widget that is to be used for the popup. """

        return self

    def GetStringValue(self):
        """ Return the current choice. """

        return self._cur_choice

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):

        if self._fit_width:
            width = self.GetCombo().GetSize()[0]
        else:
            width = self.GetCombo().GetParent().GetSize()[0]

        return width, len(self._choices) * (self._text_height + 5) + 2

    # This is called to custom paint in the combo control itself
    # (ie. not the popup).  Default implementation draws value as
    # string.
    def PaintComboControl(self, dc, rect):

        if self.GetCombo().IsEnabled():
            back_color = self._combo_color if self._combo_color else self.GetBackgroundColour()
            text_color = self.GetForegroundColour()
        else:
            back_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE)
            text_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)

        pen = wx.Pen(back_color)
        dc.SetPen(pen)
        brush = wx.Brush(back_color)
        dc.SetBrush(brush)
        dc.DrawRectangleRect(rect)

        x, y = rect.GetPosition()
        x += self._text_offset
        dc.SetFont(NodePanel.get_fonts()["normal"])
        dc.SetTextForeground(text_color)

        if self._combo_text:
            dc.DrawText(self._combo_text, x + 6, y + 3)
        else:
            timestamp, descr = self._cur_choice.split("|", 1)
            dc.DrawText(timestamp, x + 6, y + 3)

    def OnPopup(self):
        """ Called immediately after the popup is shown. """

        if self._cur_choice in self._choices:
            self.SetSelection(self._choices.index(self._cur_choice))

    def OnDismiss(self):
        """ Called when popup is dismissed. """

        wx.CallAfter(HistoryPanel.set_focus)


class NavigationComboBox(wx.combo.ComboCtrl):

    def __init__(self, parent, choices, panels):

        sizer_width = parent.get_combobox_sizer().GetMinSize()[0]

        wx.combo.ComboCtrl.__init__(self, parent, size=(
            sizer_width, 20), style=wx.CB_READONLY)

        parent.get_combobox_sizer().Add(self, 0, wx.TOP, 3)
        parent.get_combobox_sizer().Layout()
        self._parent = parent
        self._panels = panels

        self._popup = ListCtrlComboPopup(
            combo_color=wx.Colour(226, 223, 247), fit_width=False)
        self.SetPopupControl(self._popup)

        for choice in choices:
            self._popup.add_choice(choice)

        self._popup.set_current_choice(0)

    def OnPopupDismiss(self, index):
        """ Common code to be called on popup hide/dismiss. """

        panel = self._panels[index]
        self.reparent_to_panel(panel)

    def reparent_to_panel(self, panel, update=False):

        if panel is not self._parent:

            self._parent.get_combobox_sizer().Remove(self)
            self._parent.hide()
            self._parent.set_active(False)
            panel.set_active()
            panel.show()
            self.Reparent(panel)
            panel.get_combobox_sizer().Add(self, 0, wx.TOP, 3)
            panel.get_combobox_sizer().Layout()
            self._parent = panel
            panel.GetParent().FitInside()
            panel.GetParent().Refresh()
            HistoryPanel.scroll_to_entry(panel, 0, to_top=False)

            if update:
                index = self._panels.index(panel)
                self._popup.set_current_choice(index)

    def replace_choice(self, panel, choice):

        index = self._panels.index(panel)

        if self._popup.remove_choice(index=index):
            self._popup.insert_choice(index, choice)
            self._popup.set_current_choice(index)
            self._popup.Refresh()


class MilestoneComboBox(wx.combo.ComboCtrl):

    _inst = None
    _milestone_locations = []
    _persistent_milestone = None

    @classmethod
    def reset(cls):

        cls._inst = None
        cls._milestone_locations = []
        cls._persistent_milestone = None

    @classmethod
    def add_milestone(cls, milestone, loc):

        if cls._persistent_milestone == milestone:
            return

        cls._inst.get_popup().add_choice(milestone)
        cls._milestone_locations.append(loc)

    @classmethod
    def set_persistent_milestone(cls, milestone, loc):

        cls.remove_milestone(milestone)
        cls._persistent_milestone = milestone
        cls._inst.get_popup().insert_choice(0, milestone)
        cls._milestone_locations.insert(0, loc)

    @classmethod
    def remove_milestone(cls, milestone):

        if cls._persistent_milestone == milestone:
            return

        i = cls._inst.get_popup().remove_choice(milestone)

        if i > -1:
            del cls._milestone_locations[i]

    @classmethod
    def replace_milestone(cls, old_milestone, new_milestone):

        popup = cls._inst.get_popup()
        i = popup.remove_choice(old_milestone)

        if i > -1:
            popup.insert_choice(i, new_milestone)

    def __init__(self, parent):

        text = "---Choose milestone to jump to---"

        wx.combo.ComboCtrl.__init__(
            self, parent, -1, text, style=wx.CB_READONLY)

        MilestoneComboBox._inst = self

        self._popup = ListCtrlComboPopup(text, text_offset=2)
        self.SetPopupControl(self._popup)

    def get_popup(self):

        return self._popup

    def OnPopupDismiss(self, milestone_id):
        """ Common code to be called on popup hide/dismiss. """

        loc = self._milestone_locations[milestone_id]
        NodePanel.jump_to_entry(loc)


class DeletedHistoryComboBox(wx.combo.ComboCtrl):

    _inst = None
    _starting_locations = []

    @classmethod
    def reset(cls):

        cls._inst = None
        cls._starting_locations = []

    @classmethod
    def set_entries(cls, entry_data):

        cls._inst.get_popup().clear_choices()
        cls._starting_locations = []

        for data_item in entry_data:
            choice, loc = data_item
            cls._inst.get_popup().add_choice(choice)
            cls._starting_locations.append(loc)

    @classmethod
    def replace_choice(cls, old_choice, new_choice):

        popup = cls._inst.get_popup()
        i = popup.remove_choice(old_choice)

        if i > -1:
            popup.insert_choice(i, new_choice)

    def __init__(self, parent):

        text = "---Choose start of history marked for deletion to jump to---"

        wx.combo.ComboCtrl.__init__(
            self, parent, -1, text, style=wx.CB_READONLY)

        DeletedHistoryComboBox._inst = self

        self._popup = ListCtrlComboPopup(text, text_offset=2)
        self.SetPopupControl(self._popup)

    def get_popup(self):

        return self._popup

    def OnPopupDismiss(self, choice_id):
        """ Common code to be called on popup hide/dismiss. """

        loc = self._starting_locations[choice_id]
        NodePanel.jump_to_entry(loc)


class DescriptionDialog(wx.Dialog):

    def __init__(self, parent, description):

        wx.Dialog.__init__(self, parent, -1, "Custom description")

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        message = "Enter a custom description for this event:"
        msg_ctrl = wx.StaticText(self, -1, message)
        style = wx.TE_DONTWRAP | wx.TE_MULTILINE
        self._edit_ctrl = wx.TextCtrl(
            self, -1, description, size=(360, 200), style=style)
        btn_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(msg_ctrl, 0, wx.ALL, 14)
        main_sizer.Add(self._edit_ctrl, 0, wx.ALL, 14)
        main_sizer.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 14)
        self.SetSizer(main_sizer)
        self.Fit()

        self._edit_ctrl.SetFocus()

    def get_new_description(self):

        return self._edit_ctrl.GetValue()


class NodePanel(wx.Panel):

    _old_time_id = (0, 0)
    _old_entry_id = _new_entry_id = _sel_entry_id = -1
    _old_node_panel = _new_node_panel = _sel_node_panel = None
    _root_node_panel = None

    _menu_items = {}
    _menu = None

    _icons = {}

    _merge_range_start = None
    _unmark_merge_range = False

    _bg_colors = {}
    _fonts = {}
    _is_init = False

    @classmethod
    def init(cls):

        if cls._is_init:
            return

        cls._icons["off"] = wx.Bitmap(os.path.join(GFX_PATH, "icon_off.png"))
        cls._icons["on"] = wx.Bitmap(os.path.join(GFX_PATH, "icon_on.png"))
        cls._icons["del"] = wx.Bitmap(os.path.join(GFX_PATH, "icon_del.png"))
        cls._icons["merge"] = wx.Bitmap(
            os.path.join(GFX_PATH, "icon_merge.png"))

        cls._menu = wx.Menu()
        cls._menu_items[
            "select"] = cls._menu.AppendCheckItem(-1, "Select range of events to undo/redo")
        cls._menu_items[
            "edit"] = cls._menu.Append(-1, "Edit custom description...")
        cls._menu_items[
            "milestone"] = cls._menu.AppendCheckItem(-1, "Set as milestone")
        cls._menu.AppendSeparator()
        cls._menu_items["merge"] = cls._menu.AppendCheckItem(
            -1, "Mark event for merging with preceding event\tCtrl+LMB")
        cls._menu_items["merge_range"] = cls._menu.Append(
            -1, "Mark range of events for merging\tShift+Ctrl+LMB")
        cls._menu_items[
            "del"] = cls._menu.Append(-1, "Mark undone history for deletion, starting here")
        cls._menu_items[
            "undel"] = cls._menu.Append(-1, "Unmark undone history for deletion, starting here")
        cls._menu.AppendSeparator()
        cls._menu_items[
            "expand_all"] = cls._menu.Append(-1, "Expand all multiline entries")
        cls._menu_items[
            "collapse_all"] = cls._menu.Append(-1, "Collapse all multiline entries")

        cls._bg_colors = {
            "normal": (wx.Colour(206, 203, 227), wx.Colour(195, 195, 222)),
            "selected": (wx.Colour(236, 243, 255), wx.Colour(225, 235, 252))
        }
        font_normal = wx.Font(8, wx.FONTFAMILY_DEFAULT,
                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        font_bold = wx.Font(8, wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        cls._fonts = {"normal": font_normal, "bold": font_bold}

        cls._is_init = True

    @classmethod
    def set_time_id(cls, time_id):

        cls._old_time_id = time_id

    @classmethod
    def get_fonts(cls):

        return cls._fonts

    @classmethod
    def reset(cls):

        cls._old_entry_id = cls._new_entry_id = cls._sel_entry_id = -1
        cls._old_node_panel = cls._new_node_panel = cls._sel_node_panel = None
        cls._root_node_panel = None

    @classmethod
    def expand_all(cls):

        cls._root_node_panel.expand_all_entries()

    @classmethod
    def collapse_all(cls):

        cls._root_node_panel.collapse_all_entries()

    @classmethod
    def get_old_entry_location(cls):

        return (cls._old_node_panel, cls._old_entry_id) if cls._old_node_panel else None

    @classmethod
    def set_root_node_panel(cls, node_panel):

        cls._root_node_panel = node_panel

    @classmethod
    def get_root_node_panel(cls):

        return cls._root_node_panel

    @staticmethod
    def jump_to_entry(entry_location):

        def activate_parent_node_panel(node_panel):

            parent_node_panel = node_panel.get_parent_node_panel()

            if parent_node_panel:
                activate_parent_node_panel(parent_node_panel)
                combobox = parent_node_panel.get_combobox()
                combobox.reparent_to_panel(node_panel, update=True)

        panel, entry_id = entry_location
        activate_parent_node_panel(panel)
        HistoryPanel.scroll_to_entry(panel, entry_id)

    def __init__(self, parent_window, parent_node_panel, child_node_panels, events, entry_offset=0):

        self._parent_node_panel = parent_node_panel
        self._ancestor_node_panels = [parent_node_panel] + parent_node_panel.get_ancestor_node_panels() \
            if parent_node_panel else []
        self._child_node_panels = child_node_panels

        self._timestamps = []
        self._events = events
        self._entry_count = len(events)
        self._milestone_ids = []
        self._entries_to_merge = set()
        self._entry_to_del_from = self._entry_count
        self._multiline_entry_ids = set()
        self._is_active = False
        self._combobox = None

        for i, event in enumerate(events):

            time_id = event.get_time_id()
            timestamp = event.get_timestamp()
            self._timestamps.append(timestamp)
            is_milestone = event.is_milestone()

            if self._old_time_id == time_id:
                NodePanel._old_node_panel = NodePanel._new_node_panel = self
                NodePanel._old_entry_id = NodePanel._new_entry_id = i

            if is_milestone:
                choice = timestamp + "|" + event.get_description_start()
                entry_loc = (self, i)
                MilestoneComboBox.add_milestone(choice, entry_loc)
                self._milestone_ids.append(i)

        if self._entry_count:
            self.__init_panel(parent_window, entry_offset)

    def __init_panel(self, parent_window, entry_offset):

        wx.Panel.__init__(self, parent_window)

        self._entry_offset = entry_offset
        self._expanded_entry_ids = []
        self._clicked_entry_id = -1
        main_sizer = wx.BoxSizer()
        time_sizer = wx.BoxSizer(wx.VERTICAL)
        descr_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(time_sizer)
        main_sizer.Add(descr_sizer, 1, wx.EXPAND)
        self._sizers = {"time": [], "descr": []}
        self._expand_boxes = []
        self._prev_undone_hist = []

        self.SetFocusIgnoringChildren()

        for i, event in enumerate(self._events):

            sizer = wx.BoxSizer()
            sizer.SetMinSize((200, 28))
            self._sizers["time"].append(time_sizer.Insert(0, sizer))

            sizer = wx.BoxSizer()
            sizer.SetMinSize((1, 28))

            if event.get_description_line_count() > 1:
                self._multiline_entry_ids.add(i)

            expand_box = wx.BoxSizer()
            expand_box.SetMinSize((13, 13))
            expand_sizer = wx.BoxSizer()
            expand_sizer.SetMinSize((13, 28))
            self._expand_boxes.append(expand_sizer.Add(
                expand_box, 0, wx.ALIGN_CENTER_VERTICAL))
            sizer.Add(expand_sizer, 0, wx.LEFT, 25)
            self._sizers["descr"].append(
                descr_sizer.Insert(0, sizer, 0, wx.EXPAND))

        self._combobox_sizer = self._sizers["time"][0].GetSizer()

        self.SetSizer(main_sizer)

        item = self._menu_items["select"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.__select_entry(
            self._clicked_entry_id), item)
        item = self._menu_items["edit"]
        self.Bind(
            wx.EVT_MENU, lambda wx_event: self.__edit_user_description(), item)
        item = self._menu_items["milestone"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.__set_milestone(), item)
        item = self._menu_items["merge"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.__toggle_entry_to_merge(
            self._clicked_entry_id), item)
        item = self._menu_items["merge_range"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.__set_range_to_merge(
            self._clicked_entry_id), item)
        item = self._menu_items["del"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.__delete_from(), item)
        item = self._menu_items["undel"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.__undelete_from(), item)
        item = self._menu_items["expand_all"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.expand_all(), item)
        item = self._menu_items["collapse_all"]
        self.Bind(wx.EVT_MENU, lambda wx_event: self.collapse_all(), item)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_SET_FOCUS, self.__on_gain_focus)
        self.Bind(wx.EVT_LEFT_DOWN, self.__on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self.__on_left_doubleclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.__on_right_down)

    def __draw(self, wx_event):

        panel_rect = self.GetRect()
        y_orig = panel_rect.y
        parent_rect = wx.Rect(0, -y_orig, *self.GetParent().GetSize())
        dc = wx.AutoBufferedPaintDC(self)
        dc.ClippingRect = parent_rect
        pen = wx.Pen(wx.Colour(), style=wx.TRANSPARENT)
        brushes = dict(
            (k, map(wx.Brush, self._bg_colors[k])) for k in self._bg_colors)
        dc.SetPen(pen)
        dc.SetFont(self._fonts["normal"])
        entry_id_min, entry_id_max, event_state = self.__get_selection_range()

        for i, sizer in enumerate(self._sizers["time"]):

            rect = sizer.GetRect()

            if not parent_rect.Intersects(rect):
                continue

            selected = entry_id_min <= i <= entry_id_max
            j = i + self._entry_offset
            dc.SetBrush(brushes["selected" if selected else "normal"][j % 2])
            dc.DrawRectangleRect(rect)
            x, y = rect.GetPosition()
            rect.OffsetXY(7, 7)

            dc.DrawLabel(self._timestamps[i], rect)

        for i, sizer in enumerate(self._sizers["descr"]):

            rect = sizer.GetRect()

            if not parent_rect.Intersects(rect):
                continue

            selected = entry_id_min <= i <= entry_id_max
            j = i + self._entry_offset
            dc.SetBrush(brushes["selected" if selected else "normal"][j % 2])
            dc.DrawRectangleRect(rect)
            x, y = rect.GetPosition()
            rect.OffsetXY(47, 7)

            dc.SetFont(
                self._fonts["bold" if i in self._milestone_ids else "normal"])

            if selected:
                dc.DrawBitmap(self._icons[event_state], x + 2, y + 3)
            elif i in self._prev_undone_hist:
                dc.DrawBitmap(self._icons["off"], x + 2, y + 3)
            else:
                dc.DrawBitmap(self._icons["on"], x + 2, y + 3)

            if i in self._entries_to_merge:
                dc.DrawBitmap(self._icons["merge"], x + 2, y + 3)

            if i >= self._entry_to_del_from:
                dc.DrawBitmap(self._icons["del"], x + 2, y + 3)

            if i in self._expanded_entry_ids:
                dc.DrawLabel(self._events[i].get_full_description(), rect)
            else:
                dc.DrawLabel(self._events[i].get_description_start(), rect)

        dc.SetPen(wx.NullPen)
        brush = wx.Brush(wx.Colour(), style=wx.TRANSPARENT)
        dc.SetBrush(brush)

        if self is self._old_node_panel:

            rect = self._sizers["descr"][
                self._old_entry_id].GetRect().Deflate(2, 1)

            if parent_rect.Intersects(rect):
                dc.DrawRectangleRect(rect)

        for index in self._multiline_entry_ids:

            rect = self._expand_boxes[index].GetRect()

            if not parent_rect.Intersects(rect):
                continue

            dc.DrawRectangleRect(rect)
            x, y, w, h = rect
            dc.DrawLine(x + 2, y + h // 2, x + w - 2, y + h // 2)

            if index not in self._expanded_entry_ids:
                dc.DrawLine(x + w // 2, y + 2, x + w // 2, y + h - 2)

        c = 100
        color = wx.Colour(c, c, c)
        panel_rect.x = panel_rect.y = 0
        h = parent_rect.Intersect(panel_rect).height
        y = max(0, -y_orig)

        if h:
            pen = wx.Pen(color)
            dc.SetPen(pen)
            dc.DrawLine(200, y, 200, y + h)

    def __on_gain_focus(self, wx_event):

        self.GetParent().SetFocusIgnoringChildren()

    def __get_selection_range(self):

        event_state = None

        if not self._old_node_panel:
            index_1 = -1
            event_state = "on"
        elif self is self._old_node_panel:
            index_1 = self._old_entry_id
        elif self in self._old_node_panel.get_ancestor_node_panels():
            index_1 = self._entry_count
        else:
            index_1 = -1

        if not self._sel_node_panel:
            index_1 = index_2 = -1
            event_state = ""
        elif self is self._sel_node_panel:
            index_2 = self._sel_entry_id
        elif self in self._sel_node_panel.get_ancestor_node_panels():
            index_2 = self._entry_count
        else:
            index_2 = -1

        if event_state is None:
            if index_1 < index_2:
                event_state = "on"
            else:
                event_state = "off"

        return min(index_1 + 1, index_2), max(index_1, index_2), event_state

    def __get_entry_id_at_pos(self, pos):

        for i, sizer in enumerate(self._sizers["descr"]):

            rect = sizer.GetRect()

            if rect.Contains(pos):

                return i

        return -1

    def __on_left_down(self, wx_event):

        self.GetParent().SetFocusIgnoringChildren()

        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()

        for entry_id in self._multiline_entry_ids:

            rect = self._expand_boxes[entry_id].GetRect()

            if rect.Contains(mouse_pos):
                self.__expand_entry(entry_id)
                return True

        if wx_event.ControlDown():

            if wx_event.ShiftDown():
                self.__set_range_to_merge()
            else:
                self.__toggle_entry_to_merge()

            return True

        return False

    def __on_left_doubleclick(self, wx_event):

        if self.__on_left_down(wx_event):
            return

        self.__select_entry()

    def __on_right_down(self, wx_event):

        self.GetParent().SetFocusIgnoringChildren()
        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
        index = self.__get_entry_id_at_pos(mouse_pos)

        if index > -1:

            self._clicked_entry_id = index
            item = self._menu_items["select"]
            is_sel_entry = self is self._sel_node_panel and index == self._sel_entry_id
            item.Check(is_sel_entry)
            item = self._menu_items["milestone"]
            item.Check(index in self._milestone_ids)
            item = self._menu_items["merge"]
            item.Check(index in self._entries_to_merge)
            enable = self.__entry_can_be_merged(index)
            item.Enable(enable)
            item = self._menu_items["merge_range"]

            if not self._merge_range_start:

                item.SetItemLabel(
                    "(Un)mark event for merging as start of range")
                item.Enable(False)

            else:

                if self._unmark_merge_range:
                    item.SetItemLabel(
                        "Unmark range of events for merging\tShift+Ctrl+LMB")
                else:
                    item.SetItemLabel(
                        "Mark range of events for merging\tShift+Ctrl+LMB")

                enable = enable and self._merge_range_start is not None
                item.Enable(enable)

            self.PopupMenu(self._menu)

    def __select_entry(self, entry_id=-1):

        def refresh():

            panel = self._old_node_panel
            old_node_path = [panel] + \
                panel.get_ancestor_node_panels() if panel else []
            panel = self._sel_node_panel
            sel_node_path = [panel] + \
                panel.get_ancestor_node_panels() if panel else []

            for panel in sel_node_path:

                if panel.get_entry_count():
                    panel.Refresh()

                if panel in old_node_path:
                    break

            for panel in old_node_path:

                if panel.get_entry_count():
                    panel.Refresh()

                if panel in sel_node_path:
                    break

        if entry_id > -1:
            index = entry_id
        else:
            mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
            index = self.__get_entry_id_at_pos(mouse_pos)

        if index == -1:
            return

        panel = self._new_node_panel
        path_before = [panel] + \
            panel.get_ancestor_node_panels() if panel else []

        if (self._sel_entry_id == index and self._sel_node_panel is self):

            NodePanel._sel_entry_id = -1
            NodePanel._new_entry_id = self._old_entry_id
            refresh()
            NodePanel._sel_node_panel = None
            NodePanel._new_node_panel = self._old_node_panel
            refresh()

        else:

            NodePanel._sel_entry_id = index
            refresh()
            NodePanel._sel_node_panel = self
            refresh()

            if (self is self._old_node_panel and index <= self._old_entry_id) \
                    or (self._old_node_panel and self in self._old_node_panel.get_ancestor_node_panels()):

                new_entry_id = index - 1
                new_node_panel = self

                if new_entry_id == -1:

                    new_node_panel = self._parent_node_panel

                    if new_node_panel and not new_node_panel.get_entry_count():
                        new_node_panel = None

                    if new_node_panel:
                        new_entry_id = new_node_panel.get_entry_count() - 1

                NodePanel._new_entry_id = new_entry_id
                NodePanel._new_node_panel = new_node_panel

            else:

                NodePanel._new_entry_id = index
                NodePanel._new_node_panel = self

        panel = self._new_node_panel
        path_after = [panel] + \
            panel.get_ancestor_node_panels() if panel else []

        for node_panel in path_after:

            entry_to_del_from = self._new_entry_id if node_panel is panel else None
            node_panel.update_entry_to_delete_from(entry_to_del_from)

            if node_panel in path_before:
                break

        self._root_node_panel.check_entries_to_merge()

    def __entry_can_be_merged(self, entry_id=0):

        if entry_id >= self._entry_to_del_from:
            return False

        event = self._events[entry_id]
        panel = self._new_node_panel
        time_id = panel.get_events()[
            self._new_entry_id].get_time_id() if panel else (0, 0)

        if event.get_previous_event().get_time_id() == time_id:
            return False

        if entry_id > 0:
            return True

        if self._parent_node_panel:

            sibling_node_panels = self._parent_node_panel.get_child_node_panels()[
                :]
            sibling_node_panels.remove(self)

            for sibling_node_panel in sibling_node_panels:
                if not sibling_node_panel.is_marked_for_deletion():
                    return False

        return True

    def __toggle_entry_to_merge(self, entry_id=-1):

        if entry_id > -1:

            index = entry_id

        else:

            mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
            index = self.__get_entry_id_at_pos(mouse_pos)

            if not self.__entry_can_be_merged(index):
                return

        if index == -1:
            return

        if index in self._entries_to_merge:
            self._entries_to_merge.remove(index)
            NodePanel._unmark_merge_range = True
        else:
            self._entries_to_merge.add(index)
            NodePanel._unmark_merge_range = False

        NodePanel._merge_range_start = (self, index)

        rect = self._sizers["descr"][index].GetRect()
        rect.SetWidth(30)
        self.RefreshRect(rect)

    def __set_range_to_merge(self, entry_id=-1):

        if not self._merge_range_start:
            return

        if entry_id > -1:

            index = entry_id

        else:

            mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
            index = self.__get_entry_id_at_pos(mouse_pos)

            if not self.__entry_can_be_merged(index):
                return

        if index == -1:
            return

        start_node_panel, start_entry_id = self._merge_range_start

        if start_node_panel is self:

            entry_id_min = min(index, start_entry_id)
            entry_id_max = max(index, start_entry_id)

        else:

            start_ancestors = start_node_panel.get_ancestor_node_panels()
            end_ancestors = self.get_ancestor_node_panels()
            path = set(start_ancestors).symmetric_difference(
                set(end_ancestors))
            path.difference_update(set([self, start_node_panel]))

            i = start_node_panel.get_entry_count() - 1 if start_node_panel in end_ancestors else 0
            start_node_panel.set_range_to_merge(i)

            for panel in path:
                panel.set_range_to_merge()

            i = self._entry_count - 1 if self in start_ancestors else 0
            entry_id_min = min(index, i)
            entry_id_max = max(index, i)

        id_range = xrange(entry_id_min, entry_id_max + 1)

        if self._unmark_merge_range:
            self._entries_to_merge.difference_update(
                set([i for i in id_range]))
        else:
            self._entries_to_merge.update(
                set([i for i in id_range if self.__entry_can_be_merged(i)]))

        NodePanel._merge_range_start = None

        rect = self._sizers["descr"][-1].GetRect()
        rect.SetSize(wx.Size(30, self.GetSize()[1]))
        self.RefreshRect(rect)

    def set_range_to_merge(self, end_entry_id=None):

        start_node_panel, start_entry_id = self._merge_range_start

        if end_entry_id is None:
            id_range = xrange(self._entry_count)
        else:
            entry_id_min = min(start_entry_id, end_entry_id)
            entry_id_max = max(start_entry_id, end_entry_id)
            id_range = xrange(entry_id_min, entry_id_max + 1)

        if self._unmark_merge_range:
            for i in id_range:
                if i in self._entries_to_merge:
                    self._entries_to_merge.remove(i)
        else:
            for i in id_range:
                if self.__entry_can_be_merged(i):
                    self._entries_to_merge.add(i)

        rect = self._sizers["descr"][-1].GetRect()
        rect.SetSize(wx.Size(30, self.GetSize()[1]))
        self.RefreshRect(rect)

    def check_entries_to_merge(self):

        if self.is_marked_for_deletion():

            self._entries_to_merge = set()

            if self._merge_range_start and self._merge_range_start[0] is self:
                NodePanel._merge_range_start = None

        else:

            for i in self._entries_to_merge.copy():

                if not self.__entry_can_be_merged(i):

                    self._entries_to_merge.remove(i)

                    if self._merge_range_start == (self, i):
                        NodePanel._merge_range_start = None

            for child_node_panel in self._child_node_panels:
                child_node_panel.check_entries_to_merge()

        if self._entry_count:
            rect = self._sizers["descr"][-1].GetRect()
            rect.SetSize(wx.Size(30, self.GetSize()[1]))
            self.RefreshRect(rect)

    def set_entry_to_delete_from(self, entry_id=None, recurse=True):

        _entry_id = self._entry_count if entry_id is None else entry_id

        if self is self._new_node_panel:

            self._entry_to_del_from = max(_entry_id, self._new_entry_id + 1)

        else:

            panel = self._new_node_panel
            panels = panel.get_ancestor_node_panels() if panel else []

            if self not in panels:
                self._entry_to_del_from = _entry_id

        if self._entry_to_del_from == 0:

            if self._merge_range_start and self._merge_range_start[0] is self:
                NodePanel._merge_range_start = None

            self._entries_to_merge = set()

        elif self._entry_to_del_from < self._entry_count:

            if self._merge_range_start and self._merge_range_start[0] is self \
                    and self._merge_range_start[1] >= self._entry_to_del_from:
                NodePanel._merge_range_start = None

            self._entries_to_merge = set(i for i in self._entries_to_merge
                                         if i < self._entry_to_del_from)

        if recurse:
            for child_node_panel in self._child_node_panels:
                child_node_panel.set_entry_to_delete_from(entry_id)

        if self._entry_count:
            rect = self._sizers["descr"][-1].GetRect()
            rect.SetSize(wx.Size(30, self.GetSize()[1]))
            self.RefreshRect(rect)

    def get_entries_to_delete_from(self):

        entry_data = []

        if self._entry_to_del_from < self._entry_count:
            timestamp = self._timestamps[self._entry_to_del_from]
            descr_start = self._events[
                self._entry_to_del_from].get_description_start()
            choice = timestamp + "|" + descr_start
            entry_location = (self, self._entry_to_del_from)
            data = (choice, entry_location)
            entry_data.append(data)
        else:
            for child_node_panel in self._child_node_panels:
                entry_data += child_node_panel.get_entries_to_delete_from()

        return entry_data

    def __delete_from(self):

        if self is self._new_node_panel:

            self._entry_to_del_from = max(
                self._clicked_entry_id, self._new_entry_id + 1)

        else:

            panel = self._new_node_panel
            panels = panel.get_ancestor_node_panels() if panel else []

            if self not in panels:
                self._entry_to_del_from = self._clicked_entry_id

        for child_node_panel in self._child_node_panels:
            child_node_panel.set_entry_to_delete_from(0)

        for ancestor_node_panel in self._ancestor_node_panels:
            ancestor_node_panel.set_entry_to_delete_from(recurse=False)

        DeletedHistoryComboBox.set_entries(
            self._root_node_panel.get_entries_to_delete_from())

        if self._merge_range_start and self._merge_range_start[0] is self \
                and self._merge_range_start[1] >= self._entry_to_del_from:
            NodePanel._merge_range_start = None

        self._entries_to_merge = set(i for i in self._entries_to_merge
                                     if i < self._entry_to_del_from)

        rect = self._sizers["descr"][-1].GetRect()
        rect.SetSize(wx.Size(30, self.GetSize()[1]))
        self.RefreshRect(rect)

    def __undelete_from(self):

        self._entry_to_del_from = self._entry_count

        for child_node_panel in self._child_node_panels:
            child_node_panel.set_entry_to_delete_from()

        for ancestor_node_panel in self._ancestor_node_panels:
            ancestor_node_panel.set_entry_to_delete_from(recurse=False)

        DeletedHistoryComboBox.set_entries(
            self._root_node_panel.get_entries_to_delete_from())

        self._root_node_panel.check_entries_to_merge()

        rect = self._sizers["descr"][-1].GetRect()
        rect.SetSize(wx.Size(30, self.GetSize()[1]))
        self.RefreshRect(rect)

    def update_entry_to_delete_from(self, entry_id):

        if self._entry_to_del_from == self._entry_count:
            return

        _entry_id = self._entry_count if entry_id is None else entry_id + 1

        self._entry_to_del_from = max(self._entry_to_del_from, _entry_id)

        DeletedHistoryComboBox.set_entries(
            self._root_node_panel.get_entries_to_delete_from())

        rect = self._sizers["descr"][-1].GetRect()
        rect.SetSize(wx.Size(30, self.GetSize()[1]))
        self.RefreshRect(rect)

    def is_marked_for_deletion(self):

        return self._entry_to_del_from == 0

    def __edit_user_description(self):

        timestamp = self._timestamps[self._clicked_entry_id]
        event = self._events[self._clicked_entry_id]
        descr_start = event.get_description_start()
        user_descr = event.get_user_description()

        dlg = DescriptionDialog(self.GetGrandParent(), user_descr)
        answer = dlg.ShowModal()

        if answer == wx.ID_OK:
            new_descr = dlg.get_new_description()
        else:
            new_descr = None

        dlg.Destroy()

        if new_descr is None:
            return

        if new_descr != user_descr:

            old_choice = timestamp + "|" + descr_start

            event.set_user_description(new_descr)
            descr_start = event.get_description_start()

            new_choice = timestamp + "|" + descr_start

            if self._clicked_entry_id in self._milestone_ids \
                    or (self is self._old_node_panel and self._clicked_entry_id == self._old_entry_id):
                MilestoneComboBox.replace_milestone(old_choice, new_choice)

            combobox = self._parent_node_panel.get_combobox(
            ) if self._parent_node_panel else None

            if self._clicked_entry_id == 0 and combobox:
                combobox.replace_choice(self, new_choice)

            if self._clicked_entry_id == self._entry_to_del_from:
                DeletedHistoryComboBox.replace_choice(old_choice, new_choice)

            if new_descr:

                self._multiline_entry_ids.add(self._clicked_entry_id)

                if self._clicked_entry_id in self._expanded_entry_ids:
                    self._expanded_entry_ids.remove(self._clicked_entry_id)
                    self.__expand_entry(self._clicked_entry_id)

            else:

                line_count = event.get_description_line_count()

                if self._clicked_entry_id in self._multiline_entry_ids and line_count == 1:
                    self._multiline_entry_ids.remove(self._clicked_entry_id)

                if self._clicked_entry_id in self._expanded_entry_ids:

                    if self._clicked_entry_id in self._multiline_entry_ids:
                        self._expanded_entry_ids.remove(self._clicked_entry_id)

                    self.__expand_entry(self._clicked_entry_id)

        rect = self._sizers["descr"][self._clicked_entry_id].GetRect()
        self.RefreshRect(rect)

    def __set_milestone(self):

        timestamp = self._timestamps[self._clicked_entry_id]
        event = self._events[self._clicked_entry_id]
        descr_start = event.get_description_start()
        choice = timestamp + "|" + descr_start

        if self._clicked_entry_id in self._milestone_ids:
            self._milestone_ids.remove(self._clicked_entry_id)
            MilestoneComboBox.remove_milestone(choice)
            event.set_as_milestone(False)
        else:
            self._milestone_ids.append(self._clicked_entry_id)
            MilestoneComboBox.add_milestone(
                choice, (self, self._clicked_entry_id))
            event.set_as_milestone()

        rect = self._sizers["descr"][self._clicked_entry_id].GetRect()
        self.RefreshRect(rect)

    def __expand_entry(self, entry_id):

        time_sizer = self._sizers["time"][entry_id].GetSizer()
        descr_sizer = self._sizers["descr"][entry_id].GetSizer()

        if entry_id not in self._expanded_entry_ids:
            self._expanded_entry_ids.append(entry_id)
            mem_dc = wx.MemoryDC()
            mem_dc.SetFont(self._fonts["normal"])
            line_count = self._events[entry_id].get_description_line_count()
            height = mem_dc.GetMultiLineTextExtent("\n" * (line_count - 1))[1]
            height += 14
        else:
            self._expanded_entry_ids.remove(entry_id)
            height = 28

        time_sizer.SetMinSize((200, height))
        descr_sizer.SetMinSize((1, height))
        self.GetParent().FitInside()
        self.GetParent().Refresh()

    def expand_all_entries(self):

        for entry_id in self._multiline_entry_ids:
            if entry_id not in self._expanded_entry_ids:
                self.__expand_entry(entry_id)

        for child_node_panel in self._child_node_panels:
            child_node_panel.expand_all_entries()

    def collapse_all_entries(self):

        for entry_id in self._multiline_entry_ids:
            if entry_id in self._expanded_entry_ids:
                self.__expand_entry(entry_id)

        for child_node_panel in self._child_node_panels:
            child_node_panel.collapse_all_entries()

    def check_prev_undone_history(self):

        if self._entry_count:
            if self is self._old_node_panel:
                self._prev_undone_hist = xrange(
                    self._old_entry_id + 1, self._entry_count)
            elif self._old_node_panel and self in self._old_node_panel.get_ancestor_node_panels():
                self._prev_undone_hist = []
            else:
                self._prev_undone_hist = xrange(self._entry_count)

        for child_node_panel in self._child_node_panels:
            child_node_panel.check_prev_undone_history()

    def get_parent_node_panel(self):

        return self._parent_node_panel

    def get_ancestor_node_panels(self):

        return self._ancestor_node_panels

    def get_child_node_panels(self):

        return self._child_node_panels

    def get_events(self):

        return self._events

    def get_entry_count(self):

        return self._entry_count

    def get_entry_rect(self, entry_id):

        return self._sizers["descr"][entry_id].GetRect()

    def get_undoable_history(self):

        if self is self._old_node_panel:
            return [self._events[i] for i in xrange(self._old_entry_id + 1)][::-1]
        elif self._old_node_panel and self in self._old_node_panel.get_ancestor_node_panels():
            return [self._events[i] for i in xrange(self._entry_count)][::-1]

        return []

    def get_redoable_history(self):

        if self is self._old_node_panel:
            id_range = xrange(self._old_entry_id + 1, self._entry_count)
            return [self._events[i] for i in id_range]
        elif self._old_node_panel and self in self._old_node_panel.get_ancestor_node_panels():
            return []

        return [self._events[i] for i in xrange(self._entry_count)]

    @classmethod
    def get_history_to_undo_redo(cls, to_undo, to_redo):

        if not cls._sel_node_panel:
            return

        if cls._old_node_panel:
            old_node_panel = cls._old_node_panel
        else:
            old_node_panel = cls._root_node_panel

        if old_node_panel is cls._sel_node_panel:

            if cls._sel_entry_id > cls._old_entry_id:
                count = cls._sel_entry_id - cls._old_entry_id
                to_redo += old_node_panel.get_redoable_history()[:count]
            else:
                count = cls._old_entry_id + 1 - cls._sel_entry_id
                to_undo += old_node_panel.get_undoable_history()[:count]

            return

        old_node_ancestors = old_node_panel.get_ancestor_node_panels()
        sel_node_ancestors = cls._sel_node_panel.get_ancestor_node_panels()
        old_node_path = [old_node_panel] + old_node_ancestors
        sel_node_path = [cls._sel_node_panel] + sel_node_ancestors

        for panel in sel_node_ancestors:
            if panel in old_node_path:
                break
            else:
                to_redo[:0] = panel.get_redoable_history()

        if old_node_panel in sel_node_ancestors:
            to_redo[:0] = old_node_panel.get_redoable_history()
        else:
            to_undo += old_node_panel.get_undoable_history()

        for panel in old_node_ancestors:
            if panel in sel_node_path:
                break
            else:
                to_undo += panel.get_undoable_history()

        if cls._sel_node_panel in old_node_ancestors:
            to_undo += cls._sel_node_panel.get_undoable_history()[::-1][
                cls._sel_entry_id:][::-1]
        else:
            to_redo += cls._sel_node_panel.get_redoable_history()[
                :cls._sel_entry_id + 1]

    def get_history_to_delete(self, to_delete):

        if self._entry_to_del_from < self._entry_count:
            to_delete.append(self._events[self._entry_to_del_from])
            return

        for child_node_panel in self._child_node_panels:
            child_node_panel.get_history_to_delete(to_delete)

    def get_history_to_merge(self, to_merge):

        if self.is_marked_for_deletion():
            return

        if self._entries_to_merge:

            if 0 in self._entries_to_merge:

                prev_event = self._events[0].get_previous_event()

                if prev_event in to_merge:
                    to_merge.remove(prev_event)

            # return a list of end-of-range events, with all marked events having
            # their self._to_be_merged flag set through event.set_to_be_merged(bool),
            # retrievable through event.is_to_be_merged()
            l = list(self._entries_to_merge)
            l.sort()
            m = iter(l[1:] + [None])
            # given l == [1, 2, 3, 5, 6, 8, 9, 10, 11, 17], l filtered = [3, 6,
            # 11, 17]
            to_merge += [self._events[i]
                         for i in filter(lambda j: j + 1 != next(m), l)]

            for i in self._entries_to_merge:
                self._events[i].set_to_be_merged()

        for child_node_panel in self._child_node_panels:
            child_node_panel.get_history_to_merge(to_merge)

    @classmethod
    def get_history_to_restore(cls):

        if (cls._new_node_panel is cls._old_node_panel
                and cls._new_entry_id == cls._old_entry_id):
            return None
        elif cls._new_node_panel:
            return cls._new_node_panel.get_events()[cls._new_entry_id].get_time_id()
        else:
            return (0, 0)

    def get_combobox_sizer(self):

        return self._combobox_sizer

    def set_combobox(self, combobox):

        self._combobox = combobox

    def get_combobox(self):

        return self._combobox

    def set_active(self, is_active=True):

        self._is_active = is_active

    def is_active(self):

        return self._is_active

    def show(self):

        if not self._is_active:
            return

        if self._entry_count:
            sizer = self.GetContainingSizer()
            self.GetParent().GetSizer().Show(sizer)

        for panel in self._child_node_panels:
            panel.show()

    def hide(self):

        if not self._is_active:
            return

        if self._entry_count:
            sizer = self.GetContainingSizer()
            self.GetParent().GetSizer().Hide(sizer)

        for panel in self._child_node_panels:
            panel.hide()


class HistoryPanel(wx.ScrolledWindow):

    _inst = None

    @classmethod
    def set_focus(cls):

        cls._inst.SetFocusIgnoringChildren()

    @classmethod
    def scroll_to_entry(cls, panel, entry_id, to_top=True):

        step = cls._inst.GetScrollPixelsPerUnit()[1]

        if not step:
            return

        entry_rect = panel.get_entry_rect(entry_id)
        panel_pos = panel.GetScreenPosition()
        offset = panel_pos - cls._inst.GetScreenPosition()
        entry_rect.Offset(offset)

        start_y = cls._inst.GetViewStart()[1]
        entry_top = entry_rect.GetTop()
        entry_bottom = entry_rect.GetBottom()
        height = cls._inst.GetClientSize()[1]
        y = -1

        if entry_top < 0:
            y = start_y + (entry_top // step)

        if to_top:

            y = start_y + (entry_top // step)

        elif entry_bottom > height:

            step_count = int(
                math.ceil(1.0 * (entry_bottom - height + 1) / step))

            if entry_top - step_count * step > 0:
                y = start_y + step_count
            else:
                y = start_y + (entry_top // step)

        if y != -1:
            cls._inst.Scroll(-1, y)

    def __create_node_panel(self, to_create, node_panels, parent_node_panel, event,
                            event_index):

        events = [event] if parent_node_panel else []
        next_events = event.get_next_events()

        while len(next_events) == 1:
            next_event = next_events[0]
            events.append(next_event)
            next_events = next_event.get_next_events()

        event_count = len(events)
        node_panel = NodePanel(self, parent_node_panel,
                               [], events, event_index % 2)
        node_panels.append(node_panel)

        if parent_node_panel:
            sibling_node_panels = parent_node_panel.get_child_node_panels()
            sibling_node_panels.append(node_panel)

        event_index += event_count

        if next_events:
            for next_event in next_events:
                child_data = {"parent_node_panel": node_panel, "event": next_event,
                              "event_index": event_index}
                to_create.append(child_data)

    def __init__(self, parent, history):
        # sys.setrecursionlimit(50000)

        wx.ScrolledWindow.__init__(self, parent, style=wx.SUNKEN_BORDER)

        HistoryPanel._inst = self

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        data = {"parent_node_panel": None, "event": history, "event_index": 0}
        to_create = [data]
        node_panels = []

        while to_create:
            data = to_create.pop()
            self.__create_node_panel(to_create, node_panels, **data)

        if not node_panels:
            return

        for node_panel in node_panels:

            child_node_panels = node_panel.get_child_node_panels()

            if child_node_panels:

                child_cb_choices = []

                for child_node_panel in child_node_panels:
                    start_event = child_node_panel.get_events()[0]
                    timestamp = start_event.get_timestamp()
                    descr_start = start_event.get_description_start()
                    combobox_choice = timestamp + "|" + descr_start
                    child_cb_choices.append(combobox_choice)
                    separator = wx.Panel(self, size=(1, 5))
                    separator.SetBackgroundColour(wx.Colour(100, 100, 100))
                    sizer = wx.BoxSizer(wx.VERTICAL)
                    sizer.Add(child_node_panel, 0, wx.EXPAND)
                    sizer.Add(separator, 0, wx.EXPAND)
                    main_sizer.Insert(0, sizer, 0, wx.EXPAND)
                    main_sizer.Hide(sizer)

                panel = child_node_panels[0]
                panel.set_active()
                combobox = NavigationComboBox(
                    panel, child_cb_choices, child_node_panels)
                wx.CallAfter(combobox.Refresh)
                node_panel.set_combobox(combobox)

        root_node_panel = node_panels[0]

        if root_node_panel.get_entry_count():
            main_sizer.Add(root_node_panel, 0, wx.EXPAND)

        root_node_panel.set_active()
        root_node_panel.show()
        NodePanel.set_root_node_panel(root_node_panel)
        root_node_panel.check_prev_undone_history()

# ****************** Recursively create NodePanels ***************************
##
# def createNodePanel(parent_node_panel, event, event_index):
##
##      child_node_panels = []
##      events = [event] if parent_node_panel else []
##      next_events = event.get_next_events()
##
# while len(next_events) == 1:
##        next_event = next_events[0]
# events.append(next_event)
##        next_events = next_event.get_next_events()
##
##      event_count = len(events)
# node_panel = NodePanel(self, parent_node_panel, child_node_panels,
# events, event_index % 2)
##
##      event_index += event_count
##
# if next_events:
##
##        child_cb_choices = []
##
# for next_event in next_events:
# child_node_panel, cb_choice = createNodePanel(node_panel, next_event,
# event_index)
##          child_node_panels.insert(0, child_node_panel)
##          child_cb_choices.insert(0, cb_choice)
##          separator = wx.Panel(self, size=(1, 5))
##          separator.SetBackgroundColour(wx.Colour(100, 100, 100))
##          sizer = wx.BoxSizer(wx.VERTICAL)
##          sizer.Add(child_node_panel, 0, wx.EXPAND)
##          sizer.Add(separator, 0, wx.EXPAND)
##          main_sizer.Add(sizer, 0, wx.EXPAND)
# main_sizer.Hide(sizer)
##
##        child_node_panel = child_node_panels[0]
# child_node_panel.set_active()
##        combobox = NavigationComboBox(child_node_panel, child_cb_choices, child_node_panels)
# node_panel.set_combobox(combobox)
##
# if events:
##        start_event = events[0]
##        timestamp = start_event.get_timestamp()
##        descr_start = start_event.get_description_start()
##        combobox_choice = timestamp  + "|" + descr_start
# else:
##        combobox_choice = ""
##
# return node_panel, combobox_choice
##
##    event_index = 0
##    root_node_panel, cb_choice = createNodePanel(None, history, event_index)
##
# if root_node_panel.get_entry_count():
##      main_sizer.Add(root_node_panel, 0, wx.EXPAND)
##
# root_node_panel.set_active()
# root_node_panel.show()
# NodePanel.set_root_node_panel(root_node_panel)
# root_node_panel.check_prev_undone_history()
##
# ***************************************************************************

        main_sizer.Layout()
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)
        self.SetAutoLayout(True)
        self.SetScrollRate(0, 10)


class Button(wx.Button):

    def __init__(self, *args, **kwargs):

        wx.Button.__init__(self, *args, **kwargs)

        self._clicked = False

        self.Bind(wx.EVT_SET_FOCUS, self.__on_gain_focus)
        self.Bind(wx.EVT_KILL_FOCUS, self.__on_lose_focus)
        self.Bind(wx.EVT_LEFT_DOWN, self.__on_left_down)
        self.Bind(wx.EVT_MOUSEWHEEL, self.__on_mouse_wheel)

    def __on_gain_focus(self, wx_event):

        if self._clicked:
            wx_event.Skip()
        else:
            HistoryPanel.set_focus()

    def __on_lose_focus(self, wx_event):

        self._clicked = False
        wx_event.Skip()

    def __on_mouse_wheel(self, wx_event):

        HistoryPanel.set_focus()
        self._clicked = False
        wx_event.Skip()

    def __on_left_down(self, wx_event):

        self._clicked = True
        wx_event.Skip()


class HistoryWindow(wx.Frame):

    def __init__(self, parent, history, time_id):

        style = wx.CAPTION | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT
        wx.Frame.__init__(self, parent, -1, "History", style=style)

        self._history = history

        NodePanel.init()
        NodePanel.set_time_id(time_id)

        w = 700
        h = 500

        main_panel = wx.Panel(self)

        self.MakeModal()
        self.Show()

        sizer = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(main_panel, -1,
                             "Doubleclick an event description to select a range of events to"
                             " be undone and/or redone.\n"
                             "(Doubleclick it again to select none.)\n"
                             "Rightclick an event description for more options."
                             )
        sizer.Add(info, 0, wx.ALL, 14)

        combobox = MilestoneComboBox(main_panel)
        sizer.Add(combobox, 0, wx.ALL | wx.EXPAND, 14)
        combobox = DeletedHistoryComboBox(main_panel)
        sizer.Add(combobox, 0, wx.ALL | wx.EXPAND, 14)
        hist_panel = HistoryPanel(main_panel, history)
        sizer.Add(hist_panel, 1, wx.ALL | wx.EXPAND, 14)

        def close():

            self.__on_close()
            self.Destroy()

        def clear_history():

            answer = wx.MessageBox("WARNING! You are about to clear the entire history!"
                                   "\n\nAll undone history will be deleted and the remaining"
                                   "\nevents will be merged."
                                   "\n\nAlso, all edits made in this dialog will be discarded.",
                                   "Confirm clear history",
                                   wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, main_panel)

            if answer == wx.OK:
                close()
                Mgr.update_app("history", "clear")

        def update_history():

            to_undo = []
            to_redo = []
            to_delete = []
            to_merge = []
            root_node = NodePanel.get_root_node_panel()
            NodePanel.get_history_to_undo_redo(to_undo, to_redo)
            root_node.get_history_to_delete(to_delete)
            root_node.get_history_to_merge(to_merge)
            to_restore = NodePanel.get_history_to_restore()
            self._history.update_user_data()
            close()
            Mgr.update_app("history", "update", to_undo, to_redo, to_delete,
                           to_merge, to_restore)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        clear_button = Button(main_panel, -1, "Clear")
        clear_button.Bind(wx.EVT_BUTTON, lambda event: clear_history())
        btn_sizer.Add(clear_button, 0, wx.ALL, 3)
        btn_sizer.Add(wx.Size(150, 1), 1, wx.EXPAND)
        ok_button = Button(main_panel, -1, "OK")
        ok_button.Bind(wx.EVT_BUTTON, lambda event: update_history())
        btn_sizer.Add(ok_button, 0, wx.ALL, 3)
        cancel_button = Button(main_panel, -1, "Cancel")
        cancel_button.Bind(wx.EVT_BUTTON, lambda event: close())
        btn_sizer.Add(cancel_button, 0, wx.ALL, 3)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        sizer.AddSpacer(20)

        main_panel.SetSizer(sizer)

        main_panel.SetSize((w, h))
        self.SetClientSize((w, h))
        HistoryPanel.set_focus()

        main_panel.Bind(wx.EVT_SET_FOCUS, self.__on_gain_focus)
        self.Bind(wx.EVT_CLOSE, self.__on_close)

        old_entry_loc = NodePanel.get_old_entry_location()

        if old_entry_loc:
            old_entry_panel, old_entry_id = old_entry_loc
            event = old_entry_panel.get_events()[old_entry_id]
            timestamp = event.get_timestamp()
            descr_start = event.get_description_start()
            choice = timestamp + "|" + descr_start
            MilestoneComboBox.set_persistent_milestone(choice, old_entry_loc)
            NodePanel.jump_to_entry(old_entry_loc)
            HistoryPanel.scroll_to_entry(old_entry_panel, old_entry_id)

    def __on_gain_focus(self, wx_event):

        HistoryPanel.set_focus()

    def __on_close(self, wx_event=None):

        MilestoneComboBox.reset()
        DeletedHistoryComboBox.reset()
        NodePanel.reset()
        self.MakeModal(False)
        self._history.reset_temp_user_data()

        if wx_event:
            wx_event.Skip()
