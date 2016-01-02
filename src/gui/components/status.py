from ..base import *


class StatusBar(BasicToolbar):

    def __init__(self, parent, pos, width):

        back_img = wx.Image(os.path.join(GFX_PATH, "statusbar_bg.png"))
        borders = {}

        for part in ("left", "right"):
            path = os.path.join(GFX_PATH, "statusbar_border_%s.png" % part)
            borders[part] = wx.Bitmap(path)

        center_img = wx.Image(os.path.join(
            GFX_PATH, "statusbar_border_center.png"))

        if not center_img.HasAlpha():
            center_img.InitAlpha()

        w, h = borders["left"].GetSize()
        margin = 9
        x = 160
        self._mode_text_rect = wx.Rect(margin, 5, x - margin * 2, h - 10)
        self._info_text_rect = wx.Rect(
            x + margin, 5, width - x - margin * 2, h - 10)

        bitmap = back_img.AdjustChannels(
            1.6, 1.6, 1.6).Scale(width, h).ConvertToBitmap()
        mem_dc = wx.MemoryDC(bitmap)
        mem_dc.DrawBitmap(borders["left"], 0, 0)
        size = (x - 2 * w, h)
        borders["center"] = center_img.Scale(*size).ConvertToBitmap()
        mem_dc.DrawBitmap(borders["center"], w, 0)
        mem_dc.DrawBitmap(borders["right"], x - w, 0)
        mem_dc.DrawBitmap(borders["left"], x, 0)
        size = (width - x - 2 * w, h)
        borders["center"] = center_img.Scale(*size).ConvertToBitmap()
        mem_dc.DrawBitmap(borders["center"], x + w, 0)
        mem_dc.DrawBitmap(borders["right"], width - w, 0)
        mem_dc.SelectObject(wx.NullBitmap)

        BasicToolbar.__init__(self, parent, pos, bitmap)

        self._mode_text = ""
        self._info_text = ""

        self.Bind(wx.EVT_PAINT, self.__draw)

        Mgr.add_app_updater("status", self.__update_status)

    def __update_status(self, *status_specs):

        data = Mgr.get_global("status_data")[status_specs[0]]

        for spec in status_specs[1:]:
            data = data[spec]

        mode_text = data["mode"]

        if mode_text and mode_text != self._mode_text:
            self.__set_mode_text(mode_text)

        info_text = data["info"]

        if info_text != self._info_text:
            self.__set_info_text(info_text)

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.DrawBitmap(self.get_bitmap(), 0, 0)
        dc.SetFont(Fonts.get("default"))
        dc.DrawLabel(self._mode_text, self._mode_text_rect,
                     wx.ALIGN_CENTER_VERTICAL)
        dc.DrawLabel(self._info_text, self._info_text_rect,
                     wx.ALIGN_CENTER_VERTICAL)

    def __set_mode_text(self, text):

        self._mode_text = text
        self.RefreshRect(self._mode_text_rect)

    def __set_info_text(self, text):

        self._info_text = text
        self.RefreshRect(self._info_text_rect)
