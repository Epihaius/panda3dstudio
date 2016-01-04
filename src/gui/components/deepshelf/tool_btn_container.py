# DeepShelf module.

# Implements the ToolButtonContainer class, a base class of the Shelf class.

from __future__ import division
from .base import *
from .btn_container import ButtonContainer
from .tool_btn import ToolButton


class ToolButtonContainer(ButtonContainer):

    _toggle_btns = {}
    _btn_data = {}

    @classmethod
    def init(cls, btn_bitmap_name):

        ToolButton.init(btn_bitmap_name)
        ButtonContainer._tool_btn_space = cls._btn_gutter + ToolButton.get_size()
        cls._max_btn_count["tool"] = (
            cls._width - cls._btn_gutter) // cls._tool_btn_space

        cls._mgr.accept("add_tool_button_props", cls.__add_button_props)
        cls._mgr.accept("get_tool_button_data", cls.__get_button_data)
        cls._mgr.accept("toggle_tool_button", cls.__toggle_button)

    @classmethod
    def __add_button_props(cls, btn_id, btn_props):

        cls._btn_data[btn_id] = btn_props

    @classmethod
    def __get_button_data(cls):

        return cls._btn_data

    @classmethod
    def __toggle_button(cls, btn_id):

        if btn_id in cls._toggle_btns:
            for btn in cls._toggle_btns[btn_id]:
                btn.toggle()

    @classmethod
    def remove_toggle_button(cls, button):

        btn_id = button.get_id()

        if btn_id in cls._toggle_btns:

            if button in cls._toggle_btns[btn_id]:

                cls._toggle_btns[btn_id].remove(button)

                if not cls._toggle_btns[btn_id]:
                    del cls._toggle_btns[btn_id]

    @classmethod
    def clear_toggle_buttons(cls):

        cls._toggle_btns = {}

    def insert_tool_buttons(self, btn_data, x=100000):

        for btn_props in btn_data:
            self.insert_tool_button(x, props=btn_props)
            x += self._tool_btn_space

    def insert_tool_button(self, mouse_x, button=None, props=None):

        margin = self._rect.GetX() + self._btn_gutter
        index = max(0, min(len(self._btns) - 1,
                           (mouse_x - margin) // self._tool_btn_space))
        x = margin + index * self._tool_btn_space

        if mouse_x > x + 20 and index < len(self._btns):
            index += 1
            x += self._tool_btn_space

        if button:

            if button in self._btns:

                old_index = self._btns.index(button)

                if old_index < index:
                    index -= 1
                    x -= self._tool_btn_space

                if old_index == index:
                    return

            button.get_shelf().remove_tool_button(button, destroy=False)
            button.set_shelf(self._proxy)
            button.set_x(x)

            data = self._panel.get_shelf_data_value(self._id, "tools")
            data.insert(index, button.get_props())

        else:

            icon_path = decode_string(props["icon"])
            Icons.add(wx.Bitmap(icon_path), icon_path)
            btn_id = decode_string(props["id"])
            hotkey_string = decode_string(props["hotkey"])
            hotkey = ToolButton.get_hotkey_from_string(hotkey_string)
            ToolButton.set_hotkey(hotkey, btn_id)

            button = ToolButton(self._proxy, x, props)

            if btn_id in self._toggle_btns:

                self._toggle_btns[btn_id].append(button)

                if self._toggle_btns[btn_id][0].is_toggled_on():
                    button.toggle()

            else:

                self._toggle_btns[btn_id] = [button]

        for btn in self._btns[index:]:
            btn.move(self._tool_btn_space)
            btn.notify_mouse_leave()

        self._btns.insert(index, button)

        self._button_type = "tool"

        self._update_selected_btn_ids()
        self._update_cut_btn_ids()

        self._panel.Refresh()

        return button

    def remove_tool_button(self, button, destroy=True):

        if button not in self._btns:
            return

        index = self._btns.index(button)
        self._btns.remove(button)
        button.notify_mouse_leave()

        if not self._btns:
            self._button_type = ""

        for btn in self._btns[index:]:
            btn.move(-self._tool_btn_space)

        if self._btn_with_mouse:
            ToolTip.hide()
            self._btn_with_mouse = None

        btn_data = self._panel.get_shelf_data_value(self._id, "tools")
        btn_props = button.get_props()
        btn_data.remove(btn_props)
        button.set_cut(False)
        self._panel.release_cut_button(button)

        if destroy:
            self.remove_toggle_button(button)

        self._update_selected_btn_ids()
        self._update_cut_btn_ids()

        self._panel.Refresh()

    def drop_tool_buttons(self, x, buttons):

        if self._button_type == "shelf":
            return False

        if len(set(buttons + self._btns)) > self._max_btn_count["tool"]:
            btns_to_left, btns_to_right = self.get_buttons_split_at_pos(x)
            buttons = (btns_to_left, buttons + btns_to_right)
            return self._panel.relocate_shelf_contents(buttons, "tool")

        if len(buttons) > 1 and buttons[0] in self._btns:

            btn_at_x = self.get_button_at_pos(x)

            if btn_at_x in buttons:
                return False

            if btn_at_x:
                old_index = self._btns.index(btn_at_x)

            for button in buttons:
                self.remove_tool_button(button, destroy=False)

            if btn_at_x:
                x -= (old_index - self._btns.index(btn_at_x)) * \
                    self._tool_btn_space

        for button in buttons:
            if self.insert_tool_button(x, button):
                x += self._tool_btn_space

        return True
