import math
import os
import time
import collections
import wx

GFX_PATH = os.path.join("res", "gui")


class EventDispatcher(object):

    _event_handlers = {}

    @classmethod
    def add_event_handler(cls, interface_id, event_id, obj, event_handler):

        cls._event_handlers.setdefault(interface_id, {}).setdefault(
            event_id, {})[obj] = event_handler

    @classmethod
    def remove_event_handler(cls, interface_id, event_id, obj):

        handlers = cls._event_handlers.get(interface_id, {}).get(event_id, {})

        if obj in handlers:

            del handlers[obj]

            if not handlers:

                del cls._event_handlers[interface_id][event_id]

                if not cls._event_handlers[interface_id]:
                    del cls._event_handlers[interface_id]

    @classmethod
    def remove_interface(cls, interface_id):

        if interface_id in cls._event_handlers:
            del cls._event_handlers[interface_id]

    @classmethod
    def dispatch_event(cls, interface_id, event_id, event, *args, **kwargs):

        handlers = cls._event_handlers.get(interface_id, {}).get(event_id, {})

        for handler in handlers.itervalues():
            handler(event, *args, **kwargs)


class Cache(object):

    _gfx_cache = {
        "bitmap": {"loaded": {}, "created": {}},
        "image": {"loaded": {}, "created": {}}
    }

    @classmethod
    def load(cls, gfx_type, path):

        if path in cls._gfx_cache[gfx_type]["loaded"]:
            return cls._gfx_cache[gfx_type]["loaded"][path]

        gfx = wx.Bitmap(path) if gfx_type == "bitmap" else wx.Image(path)
        cls._gfx_cache[gfx_type]["loaded"][path] = gfx

        return gfx

    @classmethod
    def unload(cls, gfx_type, path):

        if path in cls._gfx_cache[gfx_type]["loaded"]:
            del cls._gfx_cache[gfx_type]["loaded"][path]

    @classmethod
    def create(cls, gfx_type, gfx_id, creation_func):

        h = hash(gfx_id)

        if h in cls._gfx_cache[gfx_type]["created"]:
            return cls._gfx_cache[gfx_type]["created"][h]

        gfx = creation_func()
        cls._gfx_cache[gfx_type]["created"][h] = gfx

        return gfx

    @classmethod
    def destroy(cls, gfx_type, gfx_id):

        if gfx_id in cls._gfx_cache[gfx_type]["created"]:
            del cls._gfx_cache[gfx_type]["created"][gfx_id]


class Cursors(object):

    _cursors = {}

    @classmethod
    def init(cls, cursors):

        cls._cursors = cursors

    @classmethod
    def get(cls, cursor_id):

        return cls._cursors.get(cursor_id)


class Fonts(object):

    _fonts = {}

    @classmethod
    def init(cls, fonts):

        cls._fonts = fonts

    @classmethod
    def get(cls, font_id):

        return cls._fonts.get(font_id)


class BaseObject(object):

    _verbose = False
    _default_data_retriever = lambda *args, **kwargs: None

    @classmethod
    def init(cls, verbose=False):

        cls._verbose = verbose

    def __init__(self, interface_id=""):

        # structure to store callables through which data can be retrieved by
        # id
        self._data_retrievers = {}
        self._interface_id = interface_id

    def setup(self, *args, **kwargs):
        """
        Should be called to setup things that cannot be handled during __init__(),
        e.g. because they depend on objects that were not created yet.

        Override in derived class.

        """

        pass

    def set_interface_id(self, interface_id):

        self._interface_id = interface_id

    def get_interface_id(self):

        return self._interface_id

    def expose(self, data_id, retriever):
        """ Make data publicly available by id through a callable """

        self._data_retrievers[data_id] = retriever

    def get(self, data_id, *args, **kwargs):
        """
        Obtain data by id. The arguments provided will be passed to the callable
        that returns the data.

        """

        if self._verbose and data_id not in self._data_retrievers:
            print 'GUI warning: data "%s" is not defined.' % data_id

        retriever = self._data_retrievers.get(
            data_id, self._default_data_retriever)

        return retriever(*args, **kwargs)

    def bind_event(self, event_id, event_handler):

        EventDispatcher.add_event_handler(
            self._interface_id, event_id, self, event_handler)

    def unbind_event(self, event_id):

        EventDispatcher.remove_event_handler(
            self._interface_id, event_id, self)

    def dispatch_event(self, event_id, event, *args, **kwargs):

        EventDispatcher.dispatch_event(
            self._interface_id, event_id, event, *args, **kwargs)


class Text(object):

    def __init__(self, text, font=None):

        self._text = text
        mem_dc = wx.MemoryDC()
        w, h, l = mem_dc.GetMultiLineTextExtent(
            text, font if font else Fonts.get("default"))
        self._sizer = wx.BoxSizer()
        self._sizer.Add(wx.Size(w, h))

    def get(self):

        return self._text

    def get_sizer(self):

        return self._sizer


def create_border(bitmap_paths, size, background_type="toolbar"):

    bitmaps = {}

    if background_type == "toolbar":

        for side in ("left", "right"):
            bitmaps[side] = Cache.load("bitmap", bitmap_paths[side])

        bitmaps["center"] = Cache.load("image", bitmap_paths["center"])

    else:

        for part in ("left", "right", "top", "bottom"):

            image = Cache.load("image", bitmap_paths[part])

            if not image.HasAlpha():
                image.InitAlpha()

            bitmaps[part] = image

        for part in ("topleft", "topright", "bottomright", "bottomleft"):

            image = Cache.load("image", bitmap_paths[part])

            if not image.HasAlpha():
                image.InitAlpha()

            bitmaps[part] = image.ConvertToBitmap()

    width, height = size
    border_bitmap = wx.EmptyBitmapRGBA(width, height)
    mem_dc = wx.MemoryDC(border_bitmap)

    if background_type == "toolbar":
        w = bitmaps["left"].GetWidth()
        bitmap_center = bitmaps["center"].Scale(
            width - 2 * w, height).ConvertToBitmap()
        mem_dc.DrawBitmap(bitmaps["left"], 0, 0)
        mem_dc.DrawBitmap(bitmap_center, w, 0)
        mem_dc.DrawBitmap(bitmaps["right"], width - w, 0)
        mem_dc.SelectObject(wx.NullBitmap)
        return border_bitmap

    corner = bitmaps["topleft"].GetSize()
    hor_thickness = bitmaps["left"].GetWidth()
    vert_thickness = bitmaps["top"].GetHeight()

    x = width - corner[0]
    y = height - corner[1]
    mem_dc.DrawBitmap(bitmaps["topleft"], 0, 0)
    mem_dc.DrawBitmap(bitmaps["bottomleft"], 0, y)
    mem_dc.DrawBitmap(bitmaps["topright"], x, 0)
    mem_dc.DrawBitmap(bitmaps["bottomright"], x, y)
    s = height - corner[1] * 2
    img = bitmaps["left"]
    bitmap = img.Scale(hor_thickness, s).ConvertToBitmap()
    mem_dc.DrawBitmap(bitmap, 0, corner[1])
    img = bitmaps["right"]
    bitmap = img.Scale(hor_thickness, s).ConvertToBitmap()
    mem_dc.DrawBitmap(bitmap, width - hor_thickness, corner[1])
    s = width - corner[0] * 2
    img = bitmaps["top"]
    bitmap = img.Scale(s, vert_thickness).ConvertToBitmap()
    mem_dc.DrawBitmap(bitmap, corner[0], 0)
    img = bitmaps["bottom"]
    bitmap = img.Scale(s, vert_thickness).ConvertToBitmap()
    mem_dc.DrawBitmap(bitmap, corner[0], height - vert_thickness)
    mem_dc.SelectObject(wx.NullBitmap)

    return border_bitmap
