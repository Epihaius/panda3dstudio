# DeepShelf module.

# Implements the shelf content access buttons.

from __future__ import division
from .base import *


class AccessButton(object):

    _bitmaps = {"protected": {}, "unprotected": {}}
    _panel = None
    _rect = None

    @classmethod
    def init(cls, panel, panel_width, panel_height, bitmap_name):

        images = {"normal": {}, "hilited": {}, "down": {}, "flat": {}}

        for state in images:
            for position in ("left", "center", "right"):
                images[state][position] = wx.Image(
                    bitmap_name + position + "_" + state + ".png")

        bitmap_left_name = bitmap_name + "left"
        bitmap_center_name = bitmap_name + "center"
        bitmap_right_name = bitmap_name + "right"
        side_width, height = images["normal"]["left"].GetSize()

        mem_dc = wx.MemoryDC()
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT,
                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        gc = wx.GraphicsContext.Create(mem_dc)
        gc.SetFont(font)
        label = "Show contents"
        text_width, text_height = gc.GetTextExtent(label)
        width = text_width + 2 + 2 * side_width
        cls._panel = panel
        cls._rect = wx.Rect((panel_width - width) / 2,
                            panel_height - height - 2, width, height)

        def create_state_bitmap(state, text_col):

            img_center = images[state]["center"].Scale(text_width + 2, height)
            bitmap_center = img_center.ConvertToBitmap()
            y = (height - text_height) // 2
            label_rect = wx.Rect(0, y, text_width + 1, text_height)
            label_img = img_center.GetSubImage(label_rect)
            label_bg = bitmap_center.GetSubBitmap(label_rect)
            label_bitmap = wx.EmptyBitmap(text_width + 1, text_height)
            mem_dc.SelectObject(label_bitmap)
            mem_dc.DrawBitmap(label_bg, 0, 0)
            gc = wx.GraphicsContext.Create(mem_dc)
            gc.SetFont(font, text_col)
            gc.DrawText(label, 0, 0)
            mem_dc.SelectObject(wx.NullBitmap)
            img = label_bitmap.ConvertToImage()
            img.InitAlpha()
            label_bitmap = img.ConvertToBitmap()
            bitmap = wx.EmptyBitmapRGBA(width, height)
            mem_dc.SelectObject(bitmap)
            mem_dc.DrawBitmap(images[state]["left"].ConvertToBitmap(), 0, 0)
            mem_dc.DrawBitmap(bitmap_center, side_width, 0)
            mem_dc.DrawBitmap(
                images[state]["right"].ConvertToBitmap(), width - side_width, 0)
            mem_dc.DrawBitmap(label_bitmap, side_width + 1, y)
            mem_dc.SelectObject(wx.NullBitmap)

            return bitmap

        for state in images:
            cls._bitmaps["protected"][state] = create_state_bitmap(
                state, wx.Colour(100, 0, 0))
            cls._bitmaps["unprotected"][state] = create_state_bitmap(
                state, wx.Colour(0, 100, 0))

    def __init__(self, shelf):

        self._shelf = shelf
        self._is_down = False
        self._has_mouse = False

    def draw(self, dc, y=0, flat=False):

        if flat:
            state = "flat"
        elif self._is_down:
            state = "down"
        elif self._has_mouse:
            state = "hilited"
        else:
            state = "normal"

        protection = "protected" if self._shelf.has_password() else "unprotected"
        x = self._rect.GetX()
        dc.DrawBitmap(self._bitmaps[protection][state], x, y)

    def check_has_mouse(self, mouse_pos):

        has_mouse = self._rect.Contains(mouse_pos)

        if has_mouse != self._has_mouse:
            self._has_mouse = has_mouse
            self._panel.Refresh()

        if not self._has_mouse:
            self._is_down = False

        return self._has_mouse

    def has_mouse(self):

        return self._has_mouse

    def notify_mouse_leave(self):

        self._is_down = False
        self._has_mouse = False

    def press(self):

        if not self._has_mouse:
            return

        self._is_down = True
        self._panel.Refresh()

    def release(self):

        if not self._has_mouse:
            return

        if self._is_down:
            self._is_down = False
            self._shelf.set_access()
            self._panel.Refresh()
