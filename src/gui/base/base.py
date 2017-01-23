from ...base import logging, GlobalData
import platform
import math
import os
import time
import collections
import wxversion
wxversion.select('2.8.12')
import wx

PLATFORM_ID = platform.system()
GFX_PATH = os.path.join("res", "gui")


class PendingTasks(object):

    _tasks = {}
    _task_ids = {}
    _is_handling_tasks = False

    @classmethod
    def add(cls, task, task_id, task_type="", sort=None, id_prefix=None):
        """
        Add a task that needs to be handled later - and only once - through a call
        to handle(), optionally with a type and/or sort value.
        Additionally, a prefix for the task ID can be given to make it unique (so
        this task doesn't overwrite a previously added task with the same ID and
        type), while retaining the sort value associated with the given task_id (if
        the given sort value is None).

        """

        if cls._is_handling_tasks:
            return False

        if sort is None:

            task_ids = cls._task_ids.get(task_type, [])

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

        if id_prefix:
            task_id = "%s_%s" % (id_prefix, task_id)

        cls._tasks.setdefault(task_type, {}).setdefault(sort, {})[task_id] = task

        return True

    @classmethod
    def remove(cls, task_id, task_type="", sort=None):
        """
        Remove the task with the given ID (and optionally, type and/or sort value)
        and return it (or None if not found).

        """

        if cls._is_handling_tasks:
            return

        if sort is None:

            task_ids = cls._task_ids.get(task_type, [])

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

        return cls._tasks.get(task_type, {}).get(sort, {}).pop(task_id, None)

    @classmethod
    def clear(cls, task_type=None):
        """
        Clear the tasks of the given type if it is specified, or all tasks if it is
        None.

        """

        if cls._is_handling_tasks:
            return

        (cls._tasks if task_type is None else cls._tasks.get(task_type, {})).clear()

    @classmethod
    def handle(cls, task_types=None, sort_by_type=False):
        """
        Handle tasks that were added through add(), in an order that corresponds to
        their sort values (and optionally, their type).

        If a list of task_types is given, only those types of tasks will be handled.

        If sort_by_type is True, tasks will first be processed in the order that
        their types appear in the list of task_types, and then by sort value.
        Otherwise, task types are ignored and the tasks are handled in the order
        given by their sort values only.

        """

        if cls._is_handling_tasks:
            return

        cls._is_handling_tasks = True

        pending_tasks = cls._tasks

        if task_types is None:
            task_types = pending_tasks.keys()

        if sort_by_type:
            sorted_tasks = [task for task_type in task_types for sort, tasks in
                            sorted(pending_tasks.pop(task_type, {}).iteritems())
                            for task in tasks.itervalues()]
        else:
            sorted_tasks = [task for sort, tasks in sorted([i for task_type in task_types
                            for i in pending_tasks.pop(task_type, {}).iteritems()])
                            for task in tasks.itervalues()]

        for task in sorted_tasks:
            task()

        cls._is_handling_tasks = False

    @classmethod
    def add_task_id(cls, task_id, task_type="", sort=None):
        """
        Add a task ID, optionally associated with a particular task type, and with
        an optional sort value.

        """

        task_ids = cls._task_ids.setdefault(task_type, [])

        if sort is None:
            task_ids.append(task_id)
        else:
            task_ids.insert(sort, task_id)

    @classmethod
    def get_sort(cls, task_id, task_type=""):
        """
        Return the sort value of the task with the given ID, or None if the task ID
        is not defined.

        """

        task_ids = cls._task_ids.get(task_type, [])

        if task_id in task_ids:
            return task_ids.index(task_id)


class EventDispatcher(object):

    _event_handlers = {}

    @classmethod
    def add_event_handler(cls, interface_id, event_id, obj, event_handler):

        cls._event_handlers.setdefault(interface_id, {}).setdefault(event_id, {})[obj] = event_handler

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

        if data_id not in self._data_retrievers:

            logging.warning('GUI: data "%s" is not defined.', data_id)

            if self._verbose:
                print 'GUI warning: data "%s" is not defined.' % data_id

        retriever = self._data_retrievers.get(data_id, self._default_data_retriever)

        return retriever(*args, **kwargs)

    def bind_event(self, event_id, event_handler):

        EventDispatcher.add_event_handler(self._interface_id, event_id, self, event_handler)

    def unbind_event(self, event_id):

        EventDispatcher.remove_event_handler(self._interface_id, event_id, self)

    def dispatch_event(self, event_id, event, *args, **kwargs):

        EventDispatcher.dispatch_event(self._interface_id, event_id, event, *args, **kwargs)


class Text(object):

    def __init__(self, text, font=None):

        self._text = text
        mem_dc = wx.MemoryDC()
        w, h, l = mem_dc.GetMultiLineTextExtent(text, font if font else Fonts.get("default"))
        self._sizer = wx.BoxSizer()
        self._sizer.Add(wx.Size(w, h))

    def get(self):

        return self._text

    def get_sizer(self):

        return self._sizer


def get_alpha(img, alpha_map):

    for y in xrange(img.GetHeight()):

        row = []
        alpha_map.append(row)

        for x in xrange(img.GetWidth()):
            row.append(img.GetAlpha(x, y))


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

    if PLATFORM_ID == "Linux":
        border_bitmap = wx.EmptyBitmap(width, height)
    else:
        border_bitmap = wx.EmptyBitmapRGBA(width, height)

    mem_dc = wx.MemoryDC(border_bitmap)

    if background_type == "toolbar":

        if PLATFORM_ID == "Linux":
            parts = ("left", "center", "right")
            alpha_maps = dict((part, []) for part in parts)

        bitmap_left = bitmaps["left"]
        bitmap_right = bitmaps["right"]
        w = bitmap_left.GetWidth()
        image_center = bitmaps["center"].Scale(width - 2 * w, height)
        bitmap_center = image_center.ConvertToBitmap()

        mem_dc.DrawBitmap(bitmap_left, 0, 0)
        mem_dc.DrawBitmap(bitmap_center, w, 0)
        mem_dc.DrawBitmap(bitmap_right, width - w, 0)
        mem_dc.SelectObject(wx.NullBitmap)

        if PLATFORM_ID == "Linux":

            if not image_center.HasAlpha():
                image_center.InitAlpha()

            get_alpha(image_center, alpha_maps["center"])

            for part in ("left", "right"):

                image = bitmaps[part].ConvertToImage()

                if not image.HasAlpha():
                    image.InitAlpha()

                get_alpha(image, alpha_maps[part])

            image = border_bitmap.ConvertToImage()
            image.InitAlpha()

            for part, offset_x in zip(parts, (0, w, width - w)):

                alpha_map = alpha_maps[part]

                for y, row in enumerate(alpha_map):
                    for x, alpha in enumerate(row):
                        image.SetAlpha(x + offset_x, y, alpha)

            border_bitmap = image.ConvertToBitmap()

        return border_bitmap

    corner = bitmaps["topleft"].GetSize()
    hor_thickness = bitmaps["left"].GetWidth()
    vert_thickness = bitmaps["top"].GetHeight()

    imgs = {}
    pos = {}
    x = width - corner[0]
    y = height - corner[1]

    if PLATFORM_ID == "Linux":
        for part in ("topleft", "bottomleft", "topright", "bottomright"):
            imgs[part] = bitmaps[part].ConvertToImage()

    pos["topleft"] = p = (0, 0)
    mem_dc.DrawBitmap(bitmaps["topleft"], *p)
    pos["bottomleft"] = p = (0, y)
    mem_dc.DrawBitmap(bitmaps["bottomleft"], *p)
    pos["topright"] = p = (x, 0)
    mem_dc.DrawBitmap(bitmaps["topright"], *p)
    pos["bottomright"] = p = (x, y)
    mem_dc.DrawBitmap(bitmaps["bottomright"], *p)
    s = height - corner[1] * 2
    img = bitmaps["left"]
    imgs["left"] = img = img.Scale(hor_thickness, s)
    bitmap = img.ConvertToBitmap()
    pos["left"] = p = (0, corner[1])
    mem_dc.DrawBitmap(bitmap, *p)
    img = bitmaps["right"]
    imgs["right"] = img = img.Scale(hor_thickness, s)
    bitmap = img.ConvertToBitmap()
    pos["right"] = p = (width - hor_thickness, corner[1])
    mem_dc.DrawBitmap(bitmap, *p)
    s = width - corner[0] * 2
    img = bitmaps["top"]
    imgs["top"] = img = img.Scale(s, vert_thickness)
    bitmap = img.ConvertToBitmap()
    pos["top"] = p = (corner[0], 0)
    mem_dc.DrawBitmap(bitmap, *p)
    img = bitmaps["bottom"]
    imgs["bottom"] = img = img.Scale(s, vert_thickness)
    bitmap = img.ConvertToBitmap()
    pos["bottom"] = p = (corner[0], height - vert_thickness)
    mem_dc.DrawBitmap(bitmap, *p)
    mem_dc.SelectObject(wx.NullBitmap)

    if PLATFORM_ID == "Linux":
        parts = ("left", "right", "top", "bottom", "topleft", "bottomleft",
                 "topright", "bottomright")
        alpha_maps = dict((part, []) for part in parts)

        image = border_bitmap.ConvertToImage()
        image.InitAlpha()

        for part in parts:

            img = imgs[part]
            offset_x, offset_y = pos[part]

            if not img.HasAlpha():
                img.InitAlpha()

            alpha_map = []
            get_alpha(img, alpha_map)

            for y, row in enumerate(alpha_map):
                for x, alpha in enumerate(row):
                    image.SetAlpha(x + offset_x, y + offset_y, alpha)

        for y in xrange(corner[1], height - corner[1]):
            for x in xrange(hor_thickness, width - hor_thickness):
                image.SetAlpha(x, y, 0)

        for y in xrange(vert_thickness, corner[1]):
            for x in xrange(corner[0], width - corner[0]):
                image.SetAlpha(x, y, 0)

        for y in xrange(height - corner[1], height - vert_thickness):
            for x in xrange(corner[0], width - corner[0]):
                image.SetAlpha(x, y, 0)

        border_bitmap = image.ConvertToBitmap()

    return border_bitmap
