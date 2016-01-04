# DeepShelf module.

# Implements the shelf buttons.

from __future__ import division
from .base import *


class ShelfButton(object):

    _images = {"normal": {}, "hilited": {}, "down": {}, "flat": {}}
    _bitmap_names = ()
    _min_width = 0
    _max_width = 0
    _side_width = 0
    _height = 0
    _panel = None
    _panel_height = 0
    _y = 0

    @classmethod
    def init(cls, panel, bitmap_name, panel_height):

        for state in cls._images:
            for position in ("left", "center", "right"):
                cls._images[state][position] = wx.Image(
                    bitmap_name + position + "_" + state + ".png")

        bitmap_left_name = bitmap_name + "left"
        bitmap_center_name = bitmap_name + "center"
        bitmap_right_name = bitmap_name + "right"
        cls._bitmap_names = (
            bitmap_left_name, bitmap_center_name, bitmap_right_name)
        cls._side_width, cls._height = cls._images["normal"]["left"].GetSize()
        cls._min_width = cls._side_width * 2 + 40  # 1
        cls._max_width = cls._side_width * 2 + 200
        cls._panel = panel
        cls._panel_height = panel_height
        cls._y = panel_height - cls._height - 2

    @classmethod
    def get_side_width(cls):

        return cls._side_width

    @classmethod
    def get_minimum_width(cls):

        return cls._min_width

    @classmethod
    def get_height(cls):

        return cls._height

    @classmethod
    def get_y(cls):

        return cls._y

    def __init__(self, label, label_color=None):

        self._shelf = None
        self._shelf_data = None
        self._label = ""
        self._label_color = None
        self._label_changed = True
        self._label_width = 0
        self._label_offset = 0
        self._width = 0
        self._width_scaled = self._min_width

        self.set_label(label, label_color)

        self._has_mouse = False
        self._is_ready = False
        self._is_down = False
        self._is_selected = False
        self._is_cut = False

        self.create_bitmaps()
        self._rect = wx.Rect(0, self._y, self._width_scaled, self._height)
        self._path_rect = wx.Rect(0, self._y, self._width_scaled, self._height)
        self._in_path = False

    def copy(self):

        copy = ShelfButton(self._label, self._label_color)
        copy.set_shelf(self._shelf, self._shelf_data)
        copy.set_selected(self._is_selected)

        return copy

    def create_bitmaps(self):

        mem_dc = wx.MemoryDC()
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        gc = wx.GraphicsContext.Create(mem_dc)
        gc.SetFont(font)
        text_width, text_height = gc.GetTextExtent(self._label)

        bitmap_left_name, bitmap_center_name, bitmap_right_name = self._bitmap_names
        self._bitmaps = {}

        center_width = self._width_scaled - 2 * self._side_width
        label_width = center_width - 2

        def create_state_bitmap(state):

            img_center = self._images[state][
                "center"].Scale(center_width, self._height)
            bitmap_center = img_center.ConvertToBitmap()
            y = (self._height - text_height) // 2
            label_rect = wx.Rect(0, y, label_width, text_height)
            label_bg = bitmap_center.GetSubBitmap(label_rect)
            label_bitmap = wx.EmptyBitmap(label_width, text_height)
            mem_dc.SelectObject(label_bitmap)
            mem_dc.DrawBitmap(label_bg, 0, 0)
            gc = wx.GraphicsContext.Create(mem_dc)
            scale_x = 1. if self._label_offset else label_width / \
                (text_width + 2)
            gc.Scale(scale_x, (text_height / (text_height + 1)))

            if self._label_color:
                gc.SetFont(font, wx.Colour(*self._label_color))
            else:
                gc.SetFont(font)

            gc.DrawText(self._label, self._label_offset, 0)
            mem_dc.SelectObject(wx.NullBitmap)
            img = label_bitmap.ConvertToImage()
            img.InitAlpha()
            label_bitmap = img.ConvertToBitmap()
            bitmap = wx.EmptyBitmapRGBA(self._width_scaled, self._height)
            mem_dc.SelectObject(bitmap)
            mem_dc.DrawBitmap(self._images[state][
                              "left"].ConvertToBitmap(), 0, 0)
            mem_dc.DrawBitmap(bitmap_center, self._side_width, 0)
            mem_dc.DrawBitmap(self._images[state]["right"].ConvertToBitmap(),
                              self._width_scaled - self._side_width, 0)
            mem_dc.DrawBitmap(label_bitmap, self._side_width + 1, y)
            mem_dc.SelectObject(wx.NullBitmap)

            return bitmap

        for state in self._images:
            self._bitmaps[state] = create_state_bitmap(state)

        img = self._bitmaps["hilited"].ConvertToImage()
        w = img.GetWidth()
        w -= self._side_width * 2
        h = self._height - 8
        img = img.GetSubImage(wx.Rect(self._side_width, 4, w, h))
        self._bitmap = img.Scale(
            w * .5, h * .5, wx.IMAGE_QUALITY_HIGH).ConvertToBitmap()
        self._label_changed = False

    def set_width_scaled(self, width_scaled):

        if self._width_scaled == width_scaled and not self._label_changed:
            return

        self._width_scaled = width_scaled
        self.create_bitmaps()
        self._rect.SetWidth(width_scaled)
        self._path_rect.SetWidth(width_scaled)

    def get_width(self, original=False):

        if original:
            return self._width
        else:
            return self._width_scaled

    def set_label(self, label, color=None):

        new_col = self._label_color if color is False else color

        if self._label == label and self._label_color == new_col:
            return

        self._label = label
        self._label_color = new_col
        self._label_changed = True
        mem_dc = wx.MemoryDC()
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        gc = wx.GraphicsContext.Create(mem_dc)
        gc.SetFont(font)
        self._label_width, h = gc.GetTextExtent(label)
        self._width = self._width_scaled = max(self._min_width, min(self._max_width,
                                                                    self._label_width // 2 * 2
                                                                    + self._side_width * 2 + 2))
        self._label_offset = max(
            0, (self._width - self._side_width * 2 - 2 - self._label_width) // 2)
        self._tooltip_bitmap = ToolTip.create_bitmap(label)

    def get_label(self):

        return self._label

    def get_label_width(self):

        return self._label_width

    def get_bitmap(self):

        return self._bitmap

    def set_shelf(self, shelf, data=None):

        self._shelf = shelf

        if data:
            self._shelf_data = data

    def get_shelf(self):

        return self._shelf

    def set_shelf_data(self, data):

        self._shelf_data = data

    def get_shelf_data(self):

        return self._shelf_data

    def get_rect(self):

        return self._rect

    def get_path_rect(self):

        return self._path_rect

    def set_x(self, x):

        self._rect.SetX(x)

    def get_x(self):

        return self._rect.GetX()

    def move_to_path(self, x):

        self._path_rect.SetX(x)
        self._in_path = True

    def move_from_path(self):

        self._in_path = False
        self._has_mouse = False
        self._is_ready = False
        self._is_down = False

    def check_has_mouse(self, mouse_pos):

        mouse_x, mouse_y = mouse_pos
        rect = self._path_rect if self._in_path else self._rect
        has_mouse = rect.Contains(mouse_pos)

        if has_mouse != self._has_mouse:

            if has_mouse:

                self.__show_tooltip()

            else:

                self._is_ready = False
                self._is_down = False
                ToolTip.hide()

            self._panel.Refresh()
            self._has_mouse = has_mouse

        return has_mouse

    def notify_mouse_hover(self):

        if not self._shelf:
            return

        if self._is_ready:
            return

        if self._has_mouse and not DraggedContents.is_in_favs():
            self._is_ready = True
            self._panel.set_candidate_shelf(self._shelf)

    def notify_mouse_leave(self):

        self._has_mouse = False
        self._is_ready = False
        self._is_down = False
        ToolTip.hide()
        self._panel.set_candidate_shelf(None)

    def has_mouse(self):

        return self._has_mouse

    def press(self):

        self._is_down = True
        self._panel.Refresh()
        ToolTip.hide()

    def release(self, disabled=False):

        if self._is_down:

            self._is_down = False
            self._panel.Refresh()

            if not disabled:
                self._panel.set_current_shelf(self._shelf)
                return True
            else:
                return False

        return False

    def set_selected(self, is_selected=True):

        self._is_selected = is_selected

    def is_selected(self):

        return self._is_selected

    def set_cut(self, is_cut=True):

        self._is_cut = is_cut

    def is_cut(self):

        return self._is_cut

    def draw(self, dc, y=None, flat=False, in_path=False):

        if flat:
            state = "flat"
        elif self._is_down:
            state = "down"
        elif self._has_mouse:
            state = "hilited"
        else:
            state = "normal"

        rect = self._path_rect if self._in_path else self._rect
        x = self._path_rect.GetX() if in_path else self._rect.GetX()

        if self._shelf and self._shelf.is_candidate():

            dc.SetPen(wx.Pen(wx.Colour(196, 192, 222)))
            dc.SetBrush(wx.Brush(wx.Colour(131, 125, 172)))
            rect = wx.Rect(*rect).Inflate(2, 2)
            dc.DrawRectangleRect(rect)

            x_, y_, w, h = rect
            dc.SetPen(wx.Pen(wx.Colour(131, 125, 172)))
            dc.DrawLine(x_ + 1, y_, x_ + w - 1, y_)

        dc.DrawBitmap(self._bitmaps[state], x, self._y if y is None else y)

    def __show_tooltip(self):

        sides_width = self._side_width * 2

        if self._width_scaled - sides_width > self._label_width * .7:
            return

        x, y = self._panel.GetScreenPosition()
        rect = self._path_rect if self._in_path else self._rect
        x += rect.GetX() + rect.GetWidth() // 2
        ToolTip.show(self._tooltip_bitmap, wx.Point(x, y))
