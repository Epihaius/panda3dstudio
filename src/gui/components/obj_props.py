from ..base import *
import wx.lib.scrolledpanel as scrolled


class TagDialog(wx.Dialog):

    def __init__(self, parent, tags):

        title = "Edit object tags"
        size = (500, 400)

        wx.Dialog.__init__(self, parent, -1, title, size=size)

        self._tags = tags

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self._clear_btn = clear_btn = wx.Button(self, -1, "Clear")
        clear_btn.Bind(wx.EVT_BUTTON, self.__clear)
        clear_btn.Enable(True if tags else False)
        main_sizer.Add(clear_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self._tag_key_labels = {}
        self._tag_val_fields = {}
        self._removal_btns = {}

        panel = wx.PyPanel(self, -1, style=wx.SUNKEN_BORDER)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(panel_sizer)
        main_sizer.Add(panel, 1, wx.ALL | wx.EXPAND, 10)

        subsizer = wx.FlexGridSizer(rows=0, cols=3, hgap=10, vgap=5)
        subsizer.AddGrowableCol(0, 1)
        subsizer.AddGrowableCol(1, 1)
        subsizer.SetFlexibleDirection(wx.HORIZONTAL)
        subsizer.Add(wx.StaticText(panel, -1, "Key"), 0, wx.ALIGN_CENTER)
        subsizer.Add(wx.StaticText(panel, -1, "Value"), 0, wx.ALIGN_CENTER)
        subsizer.Add(wx.Size(80, 0))
        panel_sizer.Add(subsizer, 0, wx.ALL | wx.EXPAND, 10)

        tag_panel = scrolled.ScrolledPanel(panel, -1, style=wx.TAB_TRAVERSAL | wx.SUNKEN_BORDER)
        self._tag_panel = tag_panel
        tag_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._tag_panel.SetSizer(tag_panel_sizer)
        panel_sizer.Add(tag_panel, 1, wx.EXPAND)

        self._tag_sizer = tag_sizer = wx.FlexGridSizer(rows=0, cols=3, hgap=10, vgap=5)
        tag_sizer.AddGrowableCol(0, 1)
        tag_sizer.AddGrowableCol(1, 1)
        tag_sizer.SetFlexibleDirection(wx.HORIZONTAL)
        tag_panel_sizer.Add(tag_sizer, 1, wx.ALL | wx.EXPAND, 10)

        get_commit_handler = lambda key: lambda evt: self.__commit(key)
        get_remove_handler = lambda key: lambda evt: self.__remove_tag(key)

        for key, value in tags.iteritems():
            label = wx.PyPanel(tag_panel, -1, style=wx.SIMPLE_BORDER)
            label_sizer = wx.BoxSizer(wx.HORIZONTAL)
            label.SetSizer(label_sizer)
            key_txt = wx.StaticText(label, -1, key)
            label_sizer.Add(key_txt, 0, wx.ALL, 2)
            self._tag_key_labels[key] = label
            tag_sizer.Add(label, 0, wx.EXPAND)
            val_field = wx.TextCtrl(tag_panel, -1, value, style=wx.TE_PROCESS_ENTER)
            handler = get_commit_handler(key)
            val_field.Bind(wx.EVT_TEXT_ENTER, handler)
            val_field.Bind(wx.EVT_KILL_FOCUS, handler)
            self._tag_val_fields[key] = val_field
            tag_sizer.Add(val_field, 0, wx.EXPAND)
            btn = wx.Button(tag_panel, -1, "Remove")
            tag_sizer.Add(btn, 0, wx.EXPAND)
            handler = get_remove_handler(key)
            btn.Bind(wx.EVT_BUTTON, handler)
            self._removal_btns[key] = btn

        self._new_key_field = wx.TextCtrl(tag_panel, -1, style=wx.TE_PROCESS_ENTER)
        self._new_key_field.Bind(wx.EVT_KEY_UP, self.__on_key_up)
        self._new_key_field.Bind(wx.EVT_TEXT_ENTER, self.__on_enter)
        tag_sizer.Add(self._new_key_field, 0, wx.EXPAND)
        self._new_val_field = wx.TextCtrl(tag_panel, -1, style=wx.TE_PROCESS_ENTER)
        self._new_val_field.Bind(wx.EVT_TEXT_ENTER, self.__on_enter)
        tag_sizer.Add(self._new_val_field, 0, wx.EXPAND)
        self._add_btn = wx.Button(tag_panel, -1, "Add")
        self._add_btn.Enable(False)
        self._add_btn.Bind(wx.EVT_BUTTON, self.__add_tag)
        tag_sizer.Add(self._add_btn, 0, wx.EXPAND)

        tag_panel.SetupScrolling()

        main_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.Add(main_btn_sizer, 0, wx.ALL | wx.EXPAND, 8)

        self.SetSizer(main_sizer)
        self._new_key_field.SetFocus()

    def __clear(self, event):

        answer = wx.MessageBox(
                               "All tags will be removed!\nAre you sure?",
                               "Clear tags",
                               wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, self
                              )

        if answer == wx.OK:

            for index in range(len(self._tags)):
                self._tag_sizer.Remove(index)

            for label in self._tag_key_labels.itervalues():
                label.Destroy()

            for field in self._tag_val_fields.itervalues():
                field.Destroy()

            for btn in self._removal_btns.itervalues():
                btn.Destroy()

            self._tags = {}
            self._tag_key_labels = {}
            self._tag_val_fields = {}
            self._removal_btns = {}
            self._tag_panel.SetupScrolling()
            self._tag_sizer.Layout()
            self._new_key_field.SetFocus()
            self._clear_btn.Enable(False)

    def __on_key_up(self, event):

        tag_key = self._new_key_field.GetValue()
        self._add_btn.Enable(True if (tag_key and tag_key not in self._tags) else False)

        event.Skip()

    def __on_enter(self, event):

        self._tag_panel.SetFocusIgnoringChildren()

    def __commit(self, key):

        field = self._tag_val_fields[key]
        self._tags[key] = field.GetValue()
        self._tag_panel.SetFocusIgnoringChildren()

    def __add_tag(self, event):

        key = self._new_key_field.GetValue()
        value = self._new_val_field.GetValue()
        self._new_key_field.Clear()
        self._new_val_field.Clear()
        self._add_btn.Enable(False)
        index = len(self._tags) * 3
        self._tags[key] = value
        handler = lambda evt: self.__remove_tag(key)
        btn = wx.Button(self._tag_panel, -1, "Remove")
        btn.Bind(wx.EVT_BUTTON, handler)
        self._removal_btns[key] = btn
        self._tag_sizer.Insert(index, btn, 0, wx.EXPAND)
        val_field = wx.TextCtrl(self._tag_panel, -1, value, style=wx.TE_PROCESS_ENTER)
        handler = lambda evt: self.__commit(key)
        val_field.Bind(wx.EVT_TEXT_ENTER, handler)
        val_field.Bind(wx.EVT_KILL_FOCUS, handler)
        self._tag_val_fields[key] = val_field
        self._tag_sizer.Insert(index, val_field, 0, wx.EXPAND)
        label = wx.PyPanel(self._tag_panel, -1, style=wx.SIMPLE_BORDER)
        label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        label.SetSizer(label_sizer)
        key_txt = wx.StaticText(label, -1, key)
        label_sizer.Add(key_txt, 0, wx.ALL, 2)
        self._tag_sizer.Insert(index, label, 0, wx.EXPAND)
        self._tag_key_labels[key] = label
        self._tag_panel.SetupScrolling()
        self._tag_sizer.Layout()
        self._new_key_field.SetFocus()
        self._clear_btn.Enable(True)

    def __remove_tag(self, key):

        label = self._tag_key_labels[key]
        field = self._tag_val_fields[key]
        btn = self._removal_btns[key]
        del self._tag_key_labels[key]
        del self._tag_val_fields[key]
        del self._removal_btns[key]
        del self._tags[key]
        self._tag_sizer.Remove(btn)
        self._tag_sizer.Remove(field)
        self._tag_sizer.Remove(label)
        label.Destroy()
        field.Destroy()
        btn.Destroy()
        self._tag_panel.SetupScrolling()
        self._tag_sizer.Layout()
        self._new_key_field.SetFocus()

        if not self._tags:
            self._clear_btn.Enable(False)

    def get_tags(self):

        return self._tags


class ObjectPropertiesMenu(object):

    def __init__(self, parent):

        self._parent = parent
        self._menu = menu = wx.Menu()
        item = menu.Append(-1, "Edit tags")
        parent.Bind(wx.EVT_MENU, lambda event: self.__edit_object_tags(), item)
        self._obj_id = None

        Mgr.add_app_updater("obj_props_access", self.__show_menu)
        Mgr.add_app_updater("obj_tags", self.__update_object_tags)

    def __show_menu(self, obj_id):

        self._obj_id = obj_id
        wx.CallLater(100., lambda: self._parent.PopupMenuXY(self._menu))

    def __edit_object_tags(self):

        Mgr.update_remotely("obj_tags", self._obj_id)

    def __update_object_tags(self, tags):

        dialog = TagDialog(self._parent, tags)
        answer = dialog.ShowModal()

        if answer == wx.ID_OK:
            new_tags = dialog.get_tags()
            Mgr.update_remotely("obj_tags", self._obj_id, new_tags)

        dialog.Destroy()
