# DeepShelf module.

# Base module; needs to be imported by all other modules.

import os
import cPickle
import weakref
import wx
import zlib
import base64

CURSORS = {}


class DeepShelfObject(object):

    _mgr = None


class KeyManager(object):

    def __init__(self):

        self._hotkey_mgr = None
        self._hotkey_prev = None

    def set_hotkey_manager(self, hotkey_mgr):

        self._hotkey_mgr = hotkey_mgr

    def handle_key_down(self, panel, key, mod_code=0):

        hotkey = (key, mod_code)

        if self._hotkey_prev == hotkey:
            hotkey_repeat = True
        else:
            hotkey_repeat = False
            self._hotkey_prev = hotkey

        if panel.IsShown():

            if mod_code == wx.MOD_CONTROL:

                if key in xrange(48, 91):

                    char = chr(key)

                    if char in "AIXVH":

                        if not hotkey_repeat:
                            panel.edit_subobjects(char)

                        return True

                elif key == wx.WXK_BACK:

                    if not hotkey_repeat:
                        panel.edit_subobjects("BACKSPACE")

                    return True

            elif mod_code == 0 and key == wx.WXK_DELETE:

                if not hotkey_repeat:
                    panel.edit_subobjects("DEL")

                return True

        return self._hotkey_mgr.handle_hotkey(hotkey, hotkey_repeat)

    def handle_key_up(self, panel, key):

        self._hotkey_prev = None

        return False


class DeepShelfManager(KeyManager):

    def __init__(self):

        KeyManager.__init__(self)

        self._task_handlers = {}
        self._remote_task_handler = lambda: None

    def set_remote_task_handler(self, remote_task_handler):

        self._remote_task_handler = remote_task_handler

    def do_remotely(self, task_id, *args, **kwargs):

        return self._remote_task_handler(task_id, *args, **kwargs)

    def accept(self, task_id, task_handler):

        self._task_handlers[task_id] = task_handler

    def do(self, task_id, *args, **kwargs):

        if task_id in self._task_handlers:
            task_handler = self._task_handlers[task_id]
            return task_handler(*args, **kwargs)


class ToolTip(object):

    _inst = None
    _font = None
    _bitmap = None
    _timer = None

    @classmethod
    def init(cls, panel):

        cls._inst = wx.PopupWindow(panel)
        cls._font = wx.Font(8, wx.FONTFAMILY_DEFAULT,
                            wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        cls._inst.Disable()
        cls._inst.Hide()
        cls._timer = wx.Timer(cls._inst)
        cls._inst.Bind(wx.EVT_TIMER, cls.__on_timer, cls._timer)
        cls._inst.Bind(wx.EVT_PAINT, cls.__draw)

    @classmethod
    def create_bitmap(cls, label):

        mem_dc = wx.MemoryDC()
        mem_dc.SetFont(cls._font)
        w, h = mem_dc.GetTextExtent(label)
        bitmap = wx.EmptyBitmap(w + 6, h + 6)
        mem_dc.SelectObject(bitmap)
        pen = wx.Pen(wx.Colour(153, 76, 229), 2)
        mem_dc.SetPen(pen)
        brush = wx.Brush(wx.Colour(51, 38, 76))
        mem_dc.SetBrush(brush)
        rect = wx.Rect(0, 0, w + 7, h + 7)
        mem_dc.DrawRectangleRect(rect)
        mem_dc.SetTextForeground(wx.Colour(127, 178, 229))
        rect.SetHeight(h + 5)
        mem_dc.DrawLabel(label, rect, alignment=wx.ALIGN_CENTER)
        mem_dc.SelectObject(wx.NullBitmap)

        return bitmap

    @classmethod
    def set_bitmap(cls, bitmap):

        cls._bitmap = bitmap
        cls._inst.SetClientSize(bitmap.GetSize())

    @classmethod
    def __draw(cls, event):

        dc = wx.PaintDC(cls._inst)
        dc.DrawBitmap(cls._bitmap, 0, 0)

    @classmethod
    def __on_timer(cls, event):

        x, y = wx.GetMousePosition()
        w, h = cls._bitmap.GetSize()
        w_d, h_d = wx.GetDisplaySize()
        x = max(0, min(x, w_d - w))
        y = max(0, min(y, h_d - h))
        cls._inst.SetPosition(wx.Point(x, y - 21))
        cls._inst.Show()

    @classmethod
    def show(cls, bitmap, delay=500):

        cls.set_bitmap(bitmap)
        cls._timer.Start(delay, oneShot=True)

    @classmethod
    def hide(cls):

        cls._inst.Hide()
        cls._timer.Stop()


class ImageFrame(wx.PopupWindow):

    def __init__(self, parent):

        wx.PopupWindow.__init__(self, parent)

        self.Disable()
        self.Hide()

        self._bitmap = wx.EmptyBitmap(32, 32)

        wx.EVT_PAINT(self, self.__on_paint)

    def __on_paint(self, event):

        dc = wx.PaintDC(self)
        dc.DrawBitmap(self._bitmap, 0, 0)

    def set_bitmap(self, bitmap):

        self._bitmap = bitmap
        self.SetClientSize(bitmap.GetSize())


class DraggedContents(object):

    _candidate = None
    _items = []
    _type = ""
    _start_pos = None
    _panel = None
    _image = None
    _is_dragged = False
    _in_favs = False

    @classmethod
    def init(cls, panel):

        cls._panel = panel
        cls._image = ImageFrame(panel)

    @classmethod
    def set_candidate(cls, items, item_type, bitmap):

        cls._candidate = items
        cls._type = item_type
        cls._image.set_bitmap(bitmap)
        cls._start_pos = wx.GetMousePosition()
        cls._panel.CaptureMouse()

    @classmethod
    def get_candidate(cls):

        return cls._candidate

    @classmethod
    def clear(cls):

        cls._candidate = None
        cls._items = []
        cls._type = ""
        cls._in_favs = False
        cls._start_pos = None
        cls._image.Hide()
        cls._is_dragged = False
        cls._panel.SetCursor(wx.NullCursor)
        InsertionMarker.hide()

    @classmethod
    def get_items(cls):

        return cls._items

    @classmethod
    def get_type(cls):

        return cls._type if cls._is_dragged else ""

    @classmethod
    def is_in_favs(cls):

        return cls._in_favs

    @classmethod
    def on_drag(cls):

        mouse_pos = wx.GetMousePosition()
        img_pos = mouse_pos + wx.Point(0, 12)

        if cls._is_dragged:

            cls._image.SetPosition(img_pos)

        else:

            dx, dy = mouse_pos - cls._start_pos

            if max(abs(dx), abs(dy)) > 5:

                cls._is_dragged = True
                cls._items = cls._candidate
                current_shelf = cls._panel.get_current_shelf()
                cls._in_favs = current_shelf is cls._panel.get_favorites_shelf()

                if cls._in_favs:
                    cls._panel.set_candidate_shelf(None)

                current_shelf.check_dragged_contents()
                cls._panel.Refresh()
                cls._image.SetPosition(img_pos)
                cls._image.Show()

    @classmethod
    def drop(cls):

        items = cls._items
        item_type = cls._type
        items_were_dragged = cls._is_dragged

        if cls._panel.HasCapture():
            cls._panel.ReleaseMouse()  # <-- clear() gets called here

        if not items_were_dragged:
            return False

        if cls._panel.is_shelf_path_ready():
            return True

        shelf = cls._panel.get_current_shelf()
        btn_type = shelf.get_button_type()

        if shelf is cls._panel.get_history_shelf():
            return True

        if item_type == "shelf":

            if shelf.is_accessible() and btn_type != "tool":

                ancestors = shelf.get_ancestors() + [shelf]
                ancestor = None
                ancestor_btn = None
                allow_drop = True

                for btn in items:
                    if btn.get_shelf() in ancestors:
                        ancestor_btn = btn
                        ancestor = btn.get_shelf()
                        break

                if ancestor:

                    items = items[:]
                    items.remove(ancestor_btn)

                    if items:

                        answer = wx.MessageBox(
                            "A shelf cannot be moved into itself!\n\n"
                            + "The following shelf cannot be dropped here:\n\n"
                            + ancestor.get_label()
                            + "\n\nOnly the remaining shelves will be moved.",
                            "Invalid relocation",
                            wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION, cls._panel
                        )

                        if answer != wx.OK:
                            allow_drop = False

                    else:

                        wx.MessageBox(
                            "A shelf cannot be moved into itself!\n\n"
                            + "The following shelf cannot be dropped here:\n\n"
                            + ancestor.get_label(),
                            "Invalid relocation",
                            wx.OK | wx.ICON_EXCLAMATION, cls._panel
                        )

                        allow_drop = False

                if allow_drop:

                    mouse_x = cls._panel.ScreenToClient(
                        wx.GetMousePosition())[0]

                    if shelf.drop_children(mouse_x, items):
                        cls._panel.Refresh()
                        cls._panel.save_shelf_data()

        else:

            if shelf.is_accessible():

                mouse_x = cls._panel.ScreenToClient(wx.GetMousePosition())[0]
                if shelf.drop_tool_buttons(mouse_x, items):
                    cls._panel.Refresh()
                    cls._panel.save_shelf_data()

        return True


class InsertionMarker(object):

    _panel = None
    _bitmap = None
    _hidden = True
    _x_offset = 0
    _x = 0
    _y = 0

    @classmethod
    def init(cls, panel, path):

        cls._panel = panel

        img_path = os.path.join(path, "insertion_marker.png")
        img = wx.Image(img_path, wx.BITMAP_TYPE_PNG)

        if not img.HasAlpha():
            img.InitAlpha()

        cls._bitmap = img.ConvertToBitmap()
        cls._x_offset = img.GetWidth() // 2

    @classmethod
    def draw(cls, dc):

        if not cls._hidden:
            dc.DrawBitmap(cls._bitmap, cls._x, cls._y)

    @classmethod
    def set_x(cls, x):

        old_x = cls._x
        cls._x = x - cls._x_offset

        if cls._x != old_x:
            cls._panel.Refresh()

    @classmethod
    def set_y(cls, y):

        old_y = cls._y
        cls._y = y

        if cls._y != old_y:
            cls._panel.Refresh()

    @classmethod
    def show(cls):

        cls._hidden = False

    @classmethod
    def hide(cls):

        cls._hidden = True

    @classmethod
    def is_hidden(cls):

        return cls._hidden


class Icons(object):

    _bitmaps = {}

    @classmethod
    def add(cls, icon, path):

        if path in cls._bitmaps:

            cls._bitmaps[path][1] += 1

        else:

            img = icon.ConvertToImage()

            if img.HasAlpha():
                bitmap = wx.EmptyBitmapRGBA(32, 32)
                mem_dc = wx.MemoryDC(bitmap)
                mem_dc.DrawBitmap(icon, 0, 0)
                mem_dc.SelectObject(wx.NullBitmap)
            else:
                img.InitAlpha()
                bitmap = img.ConvertToBitmap()

            cls._bitmaps[path] = [bitmap, 1]

    @classmethod
    def get_path(cls, bitmap):

        paths = dict((v[0], k) for k, v in cls._bitmaps.iteritems())

        if bitmap in paths:
            return paths[bitmap]
        else:
            return ""

    @classmethod
    def get(cls, path):

        if path in cls._bitmaps:
            return cls._bitmaps[path][0]

    @classmethod
    def remove(cls, path=None, bitmap=None):

        if bitmap:
            paths = dict((v[0], k) for k, v in cls._bitmaps.iteritems())
            path = paths[bitmap]

        if path in cls._bitmaps:

            cls._bitmaps[path][1] -= 1

            if not cls._bitmaps[path][1]:
                del cls._bitmaps[path]

    @classmethod
    def clear(cls):

        cls._bitmaps = {}


def encode_string(data_str):

    return base64.b64encode(zlib.compress(data_str.encode("unicode-escape"), 1))


def decode_string(data_str):

    return zlib.decompress(base64.b64decode(data_str)).decode("unicode-escape")


__all__ = ("os", "cPickle", "weakref", "wx", "CURSORS", "DeepShelfObject",
           "DeepShelfManager", "ToolTip", "DraggedContents",
           "InsertionMarker", "Icons", "encode_string", "decode_string")
