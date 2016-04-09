from ..base import *
from ..button import Button
from ..toggle import ToggleButtonGroup


class GridToolbar(Toolbar):

    def __init__(self, parent, pos, width):

        Toolbar.__init__(self, parent, pos, width)

        separator_bitmap_path = os.path.join(GFX_PATH, "toolbar_separator.png")
        self.add_separator(separator_bitmap_path)
        separator = self.add_separator(separator_bitmap_path)
        self.GetSizer().Layout()
        sizer = separator.get_sizer()
        x, y = sizer.GetPosition()
        w, h = sizer.GetSize()
        x += w

        bitmap = self.get_bitmap()
        icon = wx.Bitmap(os.path.join(GFX_PATH, "icon_gridspacing.png"))
        borders = {}

        for part in ("left", "right"):
            path = os.path.join(GFX_PATH, "toolbar_border_large_%s.png" % part)
            borders[part] = Cache.load("bitmap", path)

        path = os.path.join(GFX_PATH, "toolbar_border_large_center.png")
        center_img = Cache.load("image", path)

        if not center_img.HasAlpha():
            center_img.InitAlpha()

        w, h_border = borders["left"].GetSize()
        w_icon, h_icon = icon.GetSize()
        icon_offset = (h_border - h_icon) // 2
        w_border = w_icon + icon_offset * 2
        self._border_rect = wx.Rect(x, 0, w_border, h_border)
        self._text_bg_rect = wx.Rect(5, h_border - 18, w_border - 10, 12)
        icon_back_img = bitmap.GetSubBitmap(self._border_rect).ConvertToImage()
        icon_back_img = icon_back_img.AdjustChannels(1.6, 1.6, 1.6)
        icon_back_bitmap = icon_back_img.Mirror(horizontally=False).ConvertToBitmap()
        self._text_bg = icon_back_bitmap.GetSubBitmap(self._text_bg_rect)
        self._text_bg_rect.OffsetXY(x, 0)
        size = (w_border - 2 * w, h_border)
        borders["center"] = center_img.Scale(*size).ConvertToBitmap()
        mem_dc = wx.MemoryDC(bitmap)
        mem_dc.DrawBitmap(icon_back_bitmap, x, 0)
        mem_dc.DrawBitmap(icon, x + icon_offset, icon_offset)
        mem_dc.DrawBitmap(borders["left"], x, 0)
        mem_dc.DrawBitmap(borders["center"], x + w, 0)
        mem_dc.DrawBitmap(borders["right"], x + w_border - w, 0)
        mem_dc.SelectObject(wx.NullBitmap)

        self._plane_btns = GridPlaneButtons(self)

        # TODO: add "Hide/Show Grid" button

        def update_grid_spacing(grid_spacing):

            mem_dc = wx.MemoryDC(self.get_bitmap())
            mem_dc.DrawBitmap(self._text_bg, *self._text_bg_rect.GetPosition())
            mem_dc.SetFont(Fonts.get("default"))
            mem_dc.DrawLabel(grid_spacing, self._text_bg_rect, wx.ALIGN_CENTER)
            mem_dc.SelectObject(wx.NullBitmap)
            self.RefreshRect(self._text_bg_rect)

        Mgr.add_app_updater("gridspacing", update_grid_spacing)

    def enable(self):

        self._plane_btns.enable()

    def disable(self, show=True):

        self._plane_btns.disable(show)


class GridPlaneButtons(ToggleButtonGroup):

    def __init__(self, btn_parent):

        ToggleButtonGroup.__init__(self)

        btn_data = {
            "xz": ("icon_gridplane_xz", "Grid plane XZ"),
            "yz": ("icon_gridplane_yz", "Grid plane YZ")
        }

        sizer = btn_parent.GetSizer()
        separator_bitmap_path = os.path.join(GFX_PATH, "toolbar_separator.png")
        sizer.AddSpacer(50)

        bitmap_paths = Button.get_bitmap_paths("toolbar_button")

        def add_toggle(grid_plane):

            def toggle_on():

                Mgr.update_app("active_grid_plane", grid_plane)

            toggle = (toggle_on, lambda: None)

            if grid_plane == "xy":
                self.set_default_toggle(grid_plane, toggle)
            else:
                icon_name, tooltip_text = btn_data[grid_plane]
                icon_path = os.path.join(GFX_PATH, icon_name + ".png")
                bitmaps = Button.create_button_bitmaps(icon_path, bitmap_paths, flat=True)
                btn = self.add_button(btn_parent, grid_plane, toggle, bitmaps, tooltip_text)
                sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)

        for grid_plane in ("xy", "xz", "yz"):
            add_toggle(grid_plane)

        def set_active_grid_plane(plane):

            if plane == "xy":
                self.deactivate()
            else:
                self.set_active_button(plane)

        Mgr.add_app_updater("active_grid_plane", set_active_grid_plane)

        sizer.AddStretchSpacer()
        btn_parent.add_separator(separator_bitmap_path)
        sizer.Layout()
