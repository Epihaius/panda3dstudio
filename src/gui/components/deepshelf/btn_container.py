# DeepShelf module.

# Implements the ButtonContainer class, a base class of the Shelf class.

from __future__ import division
from .base import *
from .access_btn import AccessButton


class IndexGroup(object):

    def __init__(self):

        self._ranges = []

    def __len__(self):

        return len(self._ranges)

    def update(self, indices):

        self._ranges = []

        def set_ranges(index_list):

            index = index_list.pop(0)
            index_range = [index, index + 1]
            self._ranges.append(index_range)

            for index in index_list[:]:
                if index == index_range[1]:
                    index_list.remove(index)
                    index_range[1] = index + 1
                else:
                    set_ranges(index_list)
                    break

        if indices:
            set_ranges(indices)

    def clear(self):

        self._ranges = []

    def get_ranges(self):

        return self._ranges

    def get_indices(self):

        return sum([range(*r) for r in self._ranges], [])


class ButtonContainer(DeepShelfObject):

    _btn_gutter = 0
    _tool_btn_space = 0

    _width = 0
    _max_btn_count = {}

    _panel = None
    _rect = None

    @classmethod
    def get_tool_button_space(cls):

        return cls._tool_btn_space

    @classmethod
    def get_max_button_count(cls, btn_type):

        return cls._max_btn_count[btn_type]

    def __init__(self):

        self._button_type = ""
        self._btns = []
        self._btn_positions = [self._btn_gutter + self._rect.GetX()]
        self._sel_btn_ids = IndexGroup()
        self._cut_btn_ids = IndexGroup()
        self._btn_with_mouse = None
        self._btn_pressed = None
        self._access_btn = None
        self._has_mouse = False
        self._is_candidate = False

    def _update_selected_btn_ids(self):

        btn_indices = [i for i, btn in enumerate(
            self._btns) if btn.is_selected()]
        self._sel_btn_ids.update(btn_indices)

    def _update_cut_btn_ids(self):

        btn_indices = [i for i, btn in enumerate(self._btns) if btn.is_cut()]
        self._cut_btn_ids.update(btn_indices)

    def set_button_type(self, button_type):

        self._button_type = button_type

    def get_button_type(self):

        return self._button_type

    def get_buttons(self):

        return self._btns

    def get_button_positions(self):

        return self._btn_positions

    def get_selected_button_ids(self):

        return self._sel_btn_ids

    def get_cut_button_ids(self):

        return self._cut_btn_ids

    def clear_cut_button_ids(self):

        self._cut_btn_ids.clear()

    def get_button_with_mouse(self):

        return self._btn_with_mouse

    def get_button_at_pos(self, x):

        if self._button_type == "tool":
            margin = self._rect.GetX() + self._btn_gutter
            index = max(
                0, min(len(self._btns), (x - margin) // self._tool_btn_space))
        else:
            btn_positions = sorted(self._btn_positions + [x + 1])
            index = max(0, btn_positions.index(x + 1) - 1)

        return self._btns[index] if index < len(self._btns) else None

    def get_buttons_split_at_pos(self, x):

        if self._button_type == "tool":

            margin = self._rect.GetX() + self._btn_gutter
            index = max(0, min(len(self._btns) - 1,
                               (x - margin) // self._tool_btn_space))

            if (index < len(self._btns) and (x > margin + 20 + index * self._tool_btn_space)):
                index += 1

        else:

            btn_positions = sorted(self._btn_positions + [x + 1])
            index = max(0, btn_positions.index(x + 1) - 1)

            if index < len(self._btns):

                x1 = self._btn_positions[index]
                x2 = self._btn_positions[index + 1]

                if x > (x1 + x2 - self._btn_gutter) // 2:
                    index += 1

        return self._btns[:index], self._btns[index:]

    def select_buttons(self, mode):

        if mode == "none":

            for btn in self._btns:
                btn.set_selected(False)

        elif mode == "all":

            for btn in self._btns:
                btn.set_selected()

        elif mode == "invert":

            for btn in self._btns:
                btn.set_selected(not btn.is_selected())

        self._update_selected_btn_ids()

    def get_selected_buttons(self):

        return [self._btns[i] for i in self._sel_btn_ids.get_indices()]

    def toggle_button_selection(self):

        if self._btn_with_mouse:
            self._btn_with_mouse.set_selected(
                not self._btn_with_mouse.is_selected())
            self._update_selected_btn_ids()

    def cut_buttons(self, selected):

        if selected:

            sel_btns = [self._btns[i] for i in self._sel_btn_ids.get_indices()]

            for btn in sel_btns:
                btn.set_cut()

        else:

            self._btn_with_mouse.set_cut()

        self._update_cut_btn_ids()

        return [self._btns[i] for i in self._cut_btn_ids.get_indices()]

    def get_cut_buttons(self):

        return [self._btns[i] for i in self._cut_btn_ids.get_indices()]

    def create_access_button(self):

        self._access_btn = AccessButton(self._proxy)

    def destroy_access_button(self):

        self._access_btn = None

    def notify_mouse_hover(self):

        if self._btn_with_mouse:
            self._btn_with_mouse.notify_mouse_hover()

    def notify_left_down(self):

        if self._access_btn:

            self._access_btn.press()

        elif self._btn_with_mouse:

            self._btn_with_mouse.press()
            bitmap = self._btn_with_mouse.get_bitmap()
            sel_btns = self.get_selected_buttons()

            if self._btn_with_mouse in sel_btns:
                DraggedContents.set_candidate(
                    sel_btns, self._button_type, bitmap)
            else:
                DraggedContents.set_candidate(
                    [self._btn_with_mouse], self._button_type, bitmap)

    def notify_left_up(self):

        contents_dragged = DraggedContents.drop()

        if self._access_btn:
            self._access_btn.release()
        elif self._btn_with_mouse:
            self._btn_with_mouse.release(disabled=contents_dragged)

    def draw(self, dc, y, flat=False):

        if self._access_btn:
            self._access_btn.draw(dc, y, flat)
            return
        else:
            for btn in self._btns:
                btn.draw(dc, y, flat)

        if flat:
            return

        if self._sel_btn_ids or self._cut_btn_ids:

            brush = wx.Brush(wx.Colour(0, 0, 0), wx.TRANSPARENT)
            dc.SetBrush(brush)

            pen = wx.Pen(wx.Colour(0, 255, 255), 1)
            dc.SetPen(pen)

            for id_range in self._sel_btn_ids.get_ranges():

                if self._button_type == "tool":
                    start = id_range[0] * \
                        self._tool_btn_space + self._btn_gutter
                    end = id_range[1] * self._tool_btn_space
                    margin = self._rect.GetX()
                    height = 44
                else:
                    start = self._btn_positions[id_range[0]]
                    end = self._btn_positions[id_range[1]] - self._btn_gutter
                    margin = 0
                    height = 32

                dc.DrawRectangle(margin + start - 2, y - 2,
                                 end - start + 4, height)

            pen = wx.Pen(wx.Colour(255, 255, 255), 1, wx.DOT)
            pen.SetCap(wx.CAP_BUTT)
            dc.SetPen(pen)

            for id_range in self._cut_btn_ids.get_ranges():

                if self._button_type == "tool":
                    start = id_range[0] * \
                        self._tool_btn_space + self._btn_gutter
                    end = id_range[-1] * self._tool_btn_space
                    margin = self._rect.GetX()
                    height = 42
                else:
                    start = self._btn_positions[id_range[0]]
                    end = self._btn_positions[id_range[1]] - self._btn_gutter
                    margin = 0
                    height = 30

                dc.DrawRectangle(margin + start - 1, y - 1,
                                 end - start + 2, height)

        InsertionMarker.draw(dc)

    def check_dragged_contents(self):

        dragged_contents_type = DraggedContents.get_type()

        if dragged_contents_type:
            InsertionMarker.show()
        else:
            return

        if dragged_contents_type == "shelf" and len(DraggedContents.get_items()) == 1:
            if DraggedContents.get_items()[0].get_shelf() in self._ancestors + [self._proxy]:
                dragged_contents_type = "not_allowed"

        if dragged_contents_type == "not_allowed":

            self._panel.SetCursor(CURSORS["no_access"])
            InsertionMarker.hide()

        elif dragged_contents_type == "shelf":

            if not self.is_accessible() or self._button_type == "tool":
                self._panel.SetCursor(CURSORS["no_access"])
                InsertionMarker.hide()
            else:
                self._panel.SetCursor(CURSORS["move"])
                InsertionMarker.set_y(43)

        elif dragged_contents_type == "tool":

            if not self.is_accessible() or self._button_type == "shelf":
                self._panel.SetCursor(CURSORS["no_access"])
                InsertionMarker.hide()
            else:
                self._panel.SetCursor(CURSORS["move"])
                InsertionMarker.set_y(37)

    def check_has_mouse(self, mouse_pos):

        mouse_x, mouse_y = mouse_pos
        has_mouse = self._rect.Contains(mouse_pos)

        old_btn_with_mouse = self._btn_with_mouse
        self._btn_with_mouse = None

        if old_btn_with_mouse:
            old_btn_with_mouse.check_has_mouse(mouse_pos)

        if self._access_btn:
            return self._access_btn.check_has_mouse(mouse_pos)
        elif has_mouse:
            for btn in self._btns:
                if btn.check_has_mouse(mouse_pos):
                    self._btn_with_mouse = btn
                    break

        if self._btn_with_mouse is not old_btn_with_mouse:

            if self._btn_with_mouse:

                if wx.GetKeyState(wx.WXK_CONTROL):

                    if self._btn_with_mouse.is_selected():
                        self._btn_with_mouse.set_selected(False)
                    else:
                        self._btn_with_mouse.set_selected()

                    self._update_selected_btn_ids()

            self._panel.Refresh()

        if not InsertionMarker.is_hidden():

            if self._button_type == "tool":

                if self._btns:

                    margin = self._rect.GetX() + self._btn_gutter
                    index = max(0, min(len(self._btns) - 1,
                                       (mouse_x - margin) // self._tool_btn_space))
                    x = margin + index * self._tool_btn_space

                    if mouse_x > x + 20:
                        InsertionMarker.set_x(x + 40 + self._btn_gutter // 2)
                    else:
                        InsertionMarker.set_x(
                            x - self._btn_gutter + self._btn_gutter // 2)

                else:

                    InsertionMarker.set_x(margin)

            else:

                btn_positions = self._btn_positions[:]

                if mouse_x in btn_positions:

                    InsertionMarker.set_x(mouse_x - self._btn_gutter // 2)

                else:

                    btn_positions.append(mouse_x)
                    btn_positions.sort()

                    if btn_positions[-1] == mouse_x:

                        InsertionMarker.set_x(
                            btn_positions[-2] - self._btn_gutter // 2)

                    elif btn_positions[0] == mouse_x:

                        InsertionMarker.set_x(
                            btn_positions[1] - self._btn_gutter // 2)

                    else:

                        index = btn_positions.index(mouse_x)
                        x1 = btn_positions[index - 1]
                        x2 = btn_positions[index + 1]

                        if mouse_x < (x1 + x2 - self._btn_gutter) // 2:
                            InsertionMarker.set_x(x1 - self._btn_gutter // 2)
                        else:
                            InsertionMarker.set_x(x2 - self._btn_gutter // 2)

        self._has_mouse = has_mouse

        return self._btn_with_mouse is not None

    def has_mouse(self):

        if self._access_btn:
            return self._access_btn.has_mouse()

        return self._btn_with_mouse is not None

    def set_as_candidate(self, is_candidate=True):

        self._is_candidate = is_candidate

    def is_candidate(self):

        return self._is_candidate

    def notify_mouse_leave(self):

        self._has_mouse = False

        if self._access_btn:
            self._access_btn.notify_mouse_leave()
        elif self._btn_with_mouse:
            self._btn_with_mouse.notify_mouse_leave()
            self._btn_with_mouse = None

    def notify_ctrl_down(self):

        if self._btn_with_mouse:

            if self._btn_with_mouse.is_selected():
                self._btn_with_mouse.set_selected(False)
            else:
                self._btn_with_mouse.set_selected()

            self._update_selected_btn_ids()

        self._panel.Refresh()
