from ..base import *
from ..button import Button
from ..toggle import ToggleButtonGroup
from ..combobox import ComboBox, EditableComboBox
from ..field import InputField
from ..checkbox import CheckBox
from ..colorctrl import ColorPickerCtrl
from ..radiobtn import RadioButton, RadioButtonGroup


class PanelInputField(InputField):

    def __init__(self, panel, container, sizer, width, text_color=None, back_color=None,
                 sizer_args=None, insertion_index=-1, focus_receiver=None):

        InputField.__init__(self, panel, width, text_color, back_color,
                            parent_type="panel", focus_receiver=focus_receiver)

        container.add_child_control(self)
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, self, *args)
        else:
            sizer.Add(self, *args)


class PanelCheckBox(CheckBox):

    def __init__(self, panel, container, sizer, command, mark_color=None, back_color=None,
                 sizer_args=None, insertion_index=-1, focus_receiver=None):

        CheckBox.__init__(self, panel, command, mark_color, back_color,
                          parent_type="panel", focus_receiver=focus_receiver)

        container.add_child_control(self)
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, self, *args)
        else:
            sizer.Add(self, *args)


class PanelColorPickerCtrl(ColorPickerCtrl):

    def __init__(self, panel, container, sizer, command, sizer_args=None,
                 insertion_index=-1, focus_receiver=None):

        ColorPickerCtrl.__init__(self, panel, command, parent_type="panel",
                                 focus_receiver=focus_receiver)

        container.add_child_control(self)
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, self, *args)
        else:
            sizer.Add(self, *args)


class PanelButton(Button):

    def __init__(self, panel, container, sizer, bitmaps, label="", tooltip_label="",
                 command=None, sizer_args=None, insertion_index=-1, focus_receiver=None):

        Button.__init__(self, panel, bitmaps, label, tooltip_label, command,
                        parent_type="panel", focus_receiver=focus_receiver)

        container.add_child_control(self)
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, self, *args)
        else:
            sizer.Add(self, *args)


class PanelToggleButtonGroup(ToggleButtonGroup):

    def __init__(self):

        ToggleButtonGroup.__init__(self)

    def add_button(self, panel, container, sizer, toggle_id, toggle, bitmaps,
                   tooltip_text, label="", do_before=None, do_after=None,
                   sizer_args=None, insertion_index=-1, focus_receiver=None, pos=None):

        button = ToggleButtonGroup.add_button(self, panel, toggle_id, toggle, bitmaps,
                                              tooltip_text, label, do_before, do_after,
                                              "panel", focus_receiver, pos)

        container.add_child_control(button)
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, button, *args)
        else:
            sizer.Add(button, *args)

        return button


class PanelRadioButtonGroup(RadioButtonGroup):

    def __init__(self, panel, container, group_title="", sizer=None,
                 sizer_args=None, size=None, column_gap=-1, insertion_index=-1,
                 dot_color=None, back_color=None, focus_receiver=None):

        RadioButtonGroup.__init__(self, dot_color, back_color, focus_receiver)

        self._panel = panel

        if size:

            cols, rows = size

            if column_gap > 0:
                self._sizer = wx.FlexGridSizer(
                    rows=rows, cols=cols * 3 - 1, hgap=5)
            else:
                self._sizer = wx.FlexGridSizer(
                    rows=rows, cols=cols * 2, hgap=5)

        else:

            self._sizer = wx.FlexGridSizer(rows=0, cols=2, hgap=5)

        self._column_gap = column_gap
        self._focus_receiver = focus_receiver

        if group_title:
            group = container.add_group(group_title)
            sizer = group.get_client_sizer()
            self._container = group
        else:
            self._container = container

        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, self._sizer, *args)
        else:
            sizer.Add(self._sizer, *args)

    def add_button(self, btn_id, text, sizer_args=None):

        btn = RadioButtonGroup.add_button(self, btn_id, self._panel)

        self._container.add_child_control(btn)
        self._sizer.Add(btn)
        args = sizer_args if sizer_args else (0, wx.ALIGN_CENTER_VERTICAL)
        self._container.add_text(text, self._sizer, args)

        if self._column_gap > 0:

            col_count = (self._sizer.GetCols() + 1) / 3
            item_count = self.get_button_count()

            if item_count % col_count:
                self._sizer.Add(wx.Size(self._column_gap, 0))


class PanelComboBox(ComboBox):

    _field_pos = (4, 4)

    def __init__(self, panel, container, sizer, tooltip, width,
                 active_tint=(1.8, 1.8, 1.8), sizer_args=None,
                 insertion_index=-1, focus_receiver=None):

        bitmap_paths = ComboBox.get_bitmap_paths("panel_button")
        bitmaps = ComboBox.create_button_bitmaps("", bitmap_paths, width)
        btn_data = (panel, bitmaps, "", tooltip, None, "panel", focus_receiver)

        ComboBox.__init__(self, btn_data, active_tint)

        container.add_child_control(self)
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, self, *args)
        else:
            sizer.Add(self, *args)


class EditablePanelComboBox(EditableComboBox):

    _field_pos = (4, 4)

    def __init__(self, panel, container, sizer, tooltip, width, sizer_args=None,
                 insertion_index=-1, focus_receiver=None):

        bitmap_paths = ComboBox.get_bitmap_paths("panel_button")
        bitmaps = ComboBox.create_button_bitmaps("", bitmap_paths, width)
        btn_data = (panel, bitmaps, "", tooltip, None, "panel", focus_receiver)

        EditableComboBox.__init__(self, btn_data)

        container.add_child_control(self)
        args = sizer_args if sizer_args else ()

        if insertion_index > -1:
            sizer.Insert(insertion_index, self, *args)
        else:
            sizer.Add(self, *args)


__all__ = ["PanelInputField", "PanelCheckBox", "PanelColorPickerCtrl",
           "PanelButton", "PanelToggleButtonGroup", "PanelComboBox",
           "EditablePanelComboBox", "PanelRadioButtonGroup"]
