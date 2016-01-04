# DeepShelf module.

# Implements the ShelfContentsCreationDialog and ShelfCreationDialog.

from .base import *
import wx.lib.scrolledpanel as scrolled


class ShelfContentsCreationDialog(wx.Dialog):

    def __init__(self):

        wx.Dialog.__init__(
            self, None, -1, "Create shelf contents", size=(400, 150))

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self._contents_type = 0

        radiobox = wx.RadioBox(
            self, -1, "Create...",
            choices=[
                "...one or more shelves.",
                "...a tool button."
            ],
            style=wx.RA_VERTICAL
        )
        self.Bind(wx.EVT_RADIOBOX, self.__on_select_placement, radiobox)
        main_sizer.Add(radiobox, 0, wx.ALL | wx.EXPAND, 8)
        main_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        main_sizer.AddStretchSpacer()
        main_sizer.Add(main_btn_sizer, 0, wx.ALL | wx.EXPAND, 8)
        self.SetSizer(main_sizer)

    def __on_select_placement(self, event):

        self._contents_type = event.GetInt()

    def get_contents_type(self):

        return self._contents_type


class ShelfCreationDialog(wx.Dialog):

    def __init__(self, parent_shelf, btn_count=0, max_btn_count=1, ignore_existing=False):

        self._parent_shelf = parent_shelf
        title = "Create shelves"
        s = (400, 420)

        wx.Dialog.__init__(self, None, -1, title, size=s)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        max_shelf_count = parent_shelf.get_max_button_count("shelf")

        if not ignore_existing:
            max_shelf_count -= len(parent_shelf.get_children())

        min_shelf_count = max(
            1, min(max_shelf_count, (btn_count // max_btn_count) + 1))
        count_staticbox = wx.StaticBox(self, -1, "Number of shelves")
        count_prompt = wx.StaticText(
            self, -1, "Please enter how many shelves should be created:")
        self._spinner = wx.SpinCtrl(self, -1)
        self._spinner.SetRange(min_shelf_count, max_shelf_count)
        self._spinner.SetValue(min_shelf_count)
        self.Bind(wx.EVT_SPINCTRL, self.__on_set_spinner, self._spinner)

        name_staticbox = wx.StaticBox(self, -1, "Shelf name")

        if min_shelf_count > 1:
            prompt_txt = "Please enter a global name for the shelves:"
            prompt_txt += "\n(the name of each shelf will start with this)"
        else:
            prompt_txt = "Please enter a name for the shelf:\n"

        self._name_global_prompt = wx.StaticText(self, -1, prompt_txt)
        self._name_global_field = wx.TextCtrl(self, -1)

        prompt_txt = "Please enter a specific name for each shelf:"
        prompt_txt += "\n(it will be prefixed with the global name, if any)"
        self._name_specific_prompt = wx.StaticText(self, -1, prompt_txt)

        if min_shelf_count == 1:
            self._name_specific_prompt.Disable()

        self._name_specific_fields = []
        self._name_panel = scrolled.ScrolledPanel(
            self, -1, size=(250, 100),
            style=wx.TAB_TRAVERSAL | wx.SUNKEN_BORDER
        )
        name_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._name_panel.SetSizer(name_panel_sizer)
        label_sizer = wx.BoxSizer(wx.VERTICAL)
        field_sizer = wx.BoxSizer(wx.VERTICAL)

        for i in range(20):
            label = wx.StaticText(self._name_panel, -1, str(i + 1) + ":")
            field = wx.TextCtrl(self._name_panel, -1, str(i + 1))
            self._name_specific_fields.append((label, field))
            label_sizer.Add(label, 1, wx.ALIGN_RIGHT | wx.TOP, 5)
            field_sizer.Add(field, 1, wx.ALL | wx.EXPAND, 2)
            label.Disable()
            field.Disable()

        if min_shelf_count > 1:
            for label, field in self._name_specific_fields[:min_shelf_count]:
                label.Enable()
                field.Enable()

        name_panel_sizer.Add(label_sizer, 0, wx.ALL | wx.EXPAND, 8)
        name_panel_sizer.Add(field_sizer, 1, wx.ALL | wx.EXPAND, 8)
        self._name_panel.SetupScrolling()

        count_sizer = wx.StaticBoxSizer(count_staticbox, wx.HORIZONTAL)
        count_sizer.Add(count_prompt, 0, wx.ALL | wx.EXPAND, 8)
        count_sizer.Add(self._spinner, 1, wx.ALL, 8)
        name_sizer = wx.StaticBoxSizer(name_staticbox, wx.VERTICAL)
        name_sizer.Add(self._name_global_prompt, 0, wx.ALL | wx.EXPAND, 8)
        name_sizer.Add(self._name_global_field, 0, wx.ALL | wx.EXPAND, 8)
        name_sizer.Add(self._name_specific_prompt, 0, wx.ALL | wx.EXPAND, 8)
        name_sizer.Add(self._name_panel, 0, wx.ALL | wx.EXPAND, 8)

        main_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        main_sizer.Add(count_sizer, 0, wx.ALL | wx.EXPAND, 8)
        main_sizer.Add(name_sizer, 0, wx.ALL | wx.EXPAND, 8)
        main_sizer.AddStretchSpacer()
        main_sizer.Add(main_btn_sizer, 0, wx.ALL | wx.EXPAND, 8)

        self.SetSizer(main_sizer)
        self._name_global_field.SetFocus()

    def __on_set_spinner(self, event):

        for label, field in self._name_specific_fields:
            label.Disable()
            field.Disable()

        count = self._spinner.GetValue()

        if count == 1:

            prompt_txt = "Please enter a name for the shelf:\n"
            self._name_specific_prompt.Disable()

        else:

            prompt_txt = "Please enter a global name for the shelves:"
            prompt_txt += "\n(the name of each shelf will start with this)"
            self._name_specific_prompt.Enable()

            for label, field in self._name_specific_fields[:count]:
                label.Enable()
                field.Enable()

        self._name_global_prompt.SetLabel(prompt_txt)

    def get_labels(self):

        count = self._spinner.GetValue()
        global_name = self._name_global_field.GetValue()

        if count == 1:

            shelf_labels = [global_name]

        else:

            shelf_labels = []

            for i, field in enumerate([f for l, f in self._name_specific_fields[:count]]):

                specific_name = field.GetValue()
                name = global_name + " " + specific_name if global_name else specific_name

                if not name:
                    name = str(i + 1)

                shelf_labels.append(name)

        return shelf_labels
