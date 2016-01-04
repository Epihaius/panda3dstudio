# DeepShelf module.

# Implements the ShelfButtonContainer class, a base class of the Shelf class.

from __future__ import division
from .base import *
from .btn_container import ButtonContainer
from .shelf_btn import ShelfButton


class ShelfButtonContainer(ButtonContainer):

    @classmethod
    def init(cls, panel, rect, btn_bitmap_name, btn_gutter):

        ButtonContainer._panel = panel
        ButtonContainer._rect = rect
        ButtonContainer._btn_gutter = btn_gutter
        ButtonContainer._width, height = rect.GetSize()
        ShelfButton.init(panel, btn_bitmap_name, height)
        cls._max_btn_count["shelf"] = ((cls._width - btn_gutter)
                                       // (btn_gutter + ShelfButton.get_minimum_width()))

    def get_unused_shelf_button_room(self):

        min_btn_width = ShelfButton.get_minimum_width()
        btn_room = self._width - self._btn_gutter - (min_btn_width
                                                     + self._btn_gutter) * len(self._btns)

        return btn_room

    def rescale_shelf_buttons(self, btns_to_scale=None, label_widths=None):

        btn_sides_width = ShelfButton.get_side_width() * 2 + 2
        min_btn_width = ShelfButton.get_minimum_width()

        total_scaled_label_width = self._width - self._btn_gutter - (btn_sides_width
                                                                     + self._btn_gutter) * len(self._btns)

        if btns_to_scale:

            total_scaled_label_width -= (min_btn_width - btn_sides_width) \
                * (len(self._btns) - len(btns_to_scale))

        else:

            btns_to_scale = []
            label_widths = []

            for btn in self._btns:
                w = btn.get_width(original=True) - btn_sides_width
                label_widths.append(w)
                label_widths.sort()
                btns_to_scale.insert(label_widths.index(w), btn)

        btns_with_min_width = []

        total_label_width = sum(label_widths)
        label_scale_factor = min(
            1., total_scaled_label_width / total_label_width)

        for label_width, btn in zip(label_widths, btns_to_scale):

            width_scaled = int(
                label_width * label_scale_factor) + btn_sides_width

            if width_scaled < min_btn_width:
                label_widths.remove(label_width)
                btns_to_scale.remove(btn)
                btns_with_min_width.append(btn)

        if btns_with_min_width:
            self.rescale_shelf_buttons(btns_to_scale, label_widths)
            return

        x = self._rect.GetX() + self._btn_gutter
        self._btn_positions = [x]

        for btn in self._btns:

            if btn in btns_to_scale:
                label_width = label_widths[btns_to_scale.index(btn)]
                width_scaled = int(
                    label_width * label_scale_factor) + btn_sides_width
            else:
                width_scaled = min_btn_width

            btn.set_width_scaled(width_scaled)
            btn.set_x(x)
            x += width_scaled + self._btn_gutter
            self._btn_positions.append(x)

    def insert_shelf_buttons(self, index, buttons=None, label_data=None, force_rescale=False):

        if not buttons and not label_data:
            return []

        start_index = index

        shelf_width_exceeded = False

        btns = buttons if buttons else [ShelfButton(
            label, col) for label, col in label_data]

        for btn in btns:

            btn.set_cut(False)
            self._panel.release_cut_button(btn)
            btn_width = btn.get_width(original=True)
            btn_x = self._btn_positions[index]
            self._btn_positions.insert(index, btn_x)
            self._btns.insert(index, btn)

            for i in range(index + 1, len(self._btns) + 1):
                self._btn_positions[i] += btn_width + self._btn_gutter

            index += 1

            if shelf_width_exceeded:
                continue

            if self._btn_positions[-1] + self._btn_gutter > self._width:
                shelf_width_exceeded = True

        for i in range(start_index, len(self._btns)):
            self._btns[i].set_x(self._btn_positions[i])

        if shelf_width_exceeded or force_rescale:
            self.rescale_shelf_buttons()

        self._button_type = "shelf"

        self._update_selected_btn_ids()
        self._update_cut_btn_ids()

        return btns

    def remove_shelf_buttons(self, buttons):

        if self._btn_with_mouse in buttons:
            self._btn_with_mouse = None

        for btn in buttons:

            if btn.is_cut():
                btn.set_cut(False)
                self._panel.release_cut_button(btn)

            self._btns.remove(btn)

        if self._btns:
            self.rescale_shelf_buttons()
        else:
            self._btn_positions = [self._rect.GetX() + self._btn_gutter]
            self._button_type = ""

        self._update_selected_btn_ids()
        self._update_cut_btn_ids()

        return True

    def drop_shelf_buttons(self, x, buttons):

        if self._button_type == "tool":
            return "not"

        if len(set(buttons + self._btns)) > self._max_btn_count["shelf"]:

            btns_to_left, btns_to_right = self.get_buttons_split_at_pos(x)
            buttons = (btns_to_left, buttons + btns_to_right)

            if self._panel.relocate_shelf_contents(buttons, "shelf"):
                return "deeper"
            else:
                return "not"

        btn_at_x = self.get_button_at_pos(x)

        if btn_at_x in buttons:
            return "not"

        if btn_at_x:

            index = self._btns.index(btn_at_x)

            if x not in self._btn_positions:
                btn_rect = btn_at_x.get_rect()
                btn_rect_center = btn_rect.GetX() + btn_rect.GetWidth() // 2
                index = index if x < btn_rect_center else index + 1

        else:

            index = len(self._btns)

        if buttons[0] in self._btns:

            btn_at_index = None if index == len(
                self._btns) else self._btns[index]

            if btn_at_index in buttons:
                return "not"

            for btn in buttons:
                btn.set_cut(False)
                self._panel.release_cut_button(btn)
                self._btns.remove(btn)

            index = self._btns.index(
                btn_at_index) if btn_at_index else len(self._btns)

            for btn in buttons[::-1]:
                self._btns.insert(index, btn)

            x = self._rect.GetX() + self._btn_gutter

            for i in range(len(self._btns)):
                self._btn_positions[i] = x
                self._btns[i].set_x(x)
                x += self._btns[i].get_width() + self._btn_gutter

            self._update_selected_btn_ids()
            self._update_cut_btn_ids()

            return "from_within"

        if self.insert_shelf_buttons(index, buttons, force_rescale=True):
            return "from_outside"
        else:
            return "not"

    def set_shelf_button_label(self, button, label, color=None):

        button.set_label(label, color)
        self.rescale_shelf_buttons()

    def set_shelf_button_labels(self, button_label_data):

        for button, label, color in button_label_data:
            button.set_label(label, color)

        self.rescale_shelf_buttons()
