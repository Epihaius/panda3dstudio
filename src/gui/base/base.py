from panda3d.core import *
from ...base import logging, re, cPickle, GlobalData, get_unique_name, DirectObject
import platform
import math
import os
import time
import collections

PLATFORM_ID = platform.system()


TextureAtlas = {
    "image": None,
    "regions": {},
    "inner_borders": {},
    "outer_borders": {}
}
Skin = {
    "text": {},
    "cursors": {},
    "colors": {},
    "options": {}
}


class Font(object):

    def __init__(self, path, pixel_size, height, y, line_spacing):

        self._text_maker = text_maker = PNMTextMaker(Filename.from_os_specific(path), 0)
        text_maker.set_pixel_size(pixel_size)
        text_maker.set_scale_factor(1.)
        self._height = height
        self._y = y
        self._line_spacing = max(height, line_spacing)

    def get_height(self):

        return self._height

    def get_line_spacing(self):

        return self._line_spacing

    def calc_width(self, text):

        return self._text_maker.calc_width(text)

    def create_image(self, text, text_color=(0., 0., 0., 1.), back_color=None):

        text_maker = self._text_maker
        w = text_maker.calc_width(text)
        h = self._height
        image = PNMImage(w, h, 4)

        if back_color is not None:
            r, g, b, a = back_color
            image.fill(r, g, b)
            image.alpha_fill(a)

        text_maker.set_fg(text_color)
        text_maker.generate_into(text, image, 0, self._y)
        image.unpremultiply_alpha()

        return image


def load_skin(skin_id):

    skin_path = os.path.join("skins", skin_id)

    tex_atlas = PNMImage()
    tex_atlas.read(Filename.from_os_specific(os.path.join(skin_path, "atlas.png")))
    TextureAtlas["image"] = tex_atlas
    tex_atlas_regions = TextureAtlas["regions"]
    tex_atlas_inner_borders = TextureAtlas["inner_borders"]
    tex_atlas_outer_borders = TextureAtlas["outer_borders"]

    # Parse texture atlas data

    read_regions = False
    read_inner_borders = False
    read_outer_borders = False

    with open(os.path.join(skin_path, "atlas.txt")) as atlas_txt:

        for line in atlas_txt:

            if line.startswith("#"):
                continue
            elif line.startswith("REGIONS"):
                read_regions = True
                read_inner_borders = False
                read_outer_borders = False
                continue
            elif line.startswith("INNER_BORDERS"):
                read_regions = False
                read_inner_borders = True
                read_outer_borders = False
                continue
            elif line.startswith("OUTER_BORDERS"):
                read_regions = False
                read_inner_borders = False
                read_outer_borders = True
                continue

            if read_regions:
                part_id, x, y, w, h = line.split()
                tex_atlas_regions[part_id] = (int(x), int(y), int(w), int(h))
            elif read_inner_borders:
                widget_id, l, r, b, t = line.split()
                tex_atlas_inner_borders[widget_id] = (int(l), int(r), int(b), int(t))
            elif read_outer_borders:
                widget_id, l, r, b, t = line.split()
                tex_atlas_outer_borders[widget_id] = (int(l), int(r), int(b), int(t))

    # Parse other skin data, like fonts and cursors

    font_path = os.path.join(skin_path, "fonts")
    cursor_path = os.path.join(skin_path, "cursors")
    fonts = {}
    text = {}
    read_fonts = False
    read_text = False
    read_cursors = False
    read_colors = False
    read_options = False

    def typecast(string, data_type):

        if data_type == "string":
            return string
        if data_type == "float":
            return float(string)
        if data_type == "int":
            return int(string)
        if data_type == "bool":
            return bool(int(string))

    with open(os.path.join(skin_path, "skin.txt")) as skin_txt:

        for line in skin_txt:

            if line.startswith("#"):
                continue
            elif line.startswith("FONTS"):
                read_fonts = True
                read_text = False
                read_cursors = False
                read_colors = False
                read_options = False
                continue
            elif line.startswith("TEXT"):
                read_fonts = False
                read_text = True
                read_cursors = False
                read_colors = False
                read_options = False
                continue
            elif line.startswith("CURSORS"):
                read_fonts = False
                read_text = False
                read_cursors = True
                read_colors = False
                read_options = False
                continue
            elif line.startswith("COLORS"):
                read_fonts = False
                read_text = False
                read_cursors = False
                read_colors = True
                read_options = False
                continue
            elif line.startswith("OPTIONS"):
                read_fonts = False
                read_text = False
                read_cursors = False
                read_colors = False
                read_options = True
                continue

            if read_fonts:
                font_id, filename, pixel_size, height, y, line_spacing = line.split()
                path = os.path.join(font_path, *filename.split("/"))
                fonts[font_id] = Font(path, float(pixel_size), int(height), int(y), int(line_spacing))
            elif read_text:
                text_id, font_id, r, g, b, a = line.split()
                text[text_id] = (font_id, (float(r), float(g), float(b), float(a)))
            elif read_cursors:
                cursor_id, filename = line.split()
                path = os.path.join(cursor_path, filename)
                filename = Filename.binary_filename(Filename.from_os_specific(path))
                Skin["cursors"][cursor_id] = filename
            elif read_colors:
                prop_id, r, g, b, a = line.split()
                Skin["colors"][prop_id] = (float(r), float(g), float(b), float(a))
            elif read_options:
                option, data_type, value = line.split()
                Skin["options"][option] = typecast(value, data_type)

            for text_id, text_data in text.iteritems():
                font_id, color = text_data
                Skin["text"][text_id] = {"font": fonts[font_id], "color": color}


def get_relative_region_frame(x, y, width, height, ref_width, ref_height):

    l = 1. * x / ref_width
    r = 1. * (x + width) / ref_width
    b = 1. - 1. * (y + height) / ref_height
    t = 1. - 1. * y / ref_height

    if b * t < 0.:
        b -= 1. / ref_height

    return l, r, b, t


class PendingTaskBatch(object):

    def __init__(self, sort=0):

        self._tasks = {}
        self._task_ids = {}
        self._is_handling_tasks = False
        self._sort = sort

    def is_empty(self):

        return not self._tasks

    def add(self, task, task_id, task_type="", sort=None, id_prefix=None):
        """
        Add a task that needs to be handled later - and only once - through a call
        to handle(), optionally with a type and/or sort value.
        Additionally, a prefix for the task ID can be given to make it unique (so
        this task doesn't overwrite a previously added task with the same ID and
        type), while retaining the sort value associated with the given task_id (if
        the given sort value is None).

        """

        if self._is_handling_tasks:
            return False

        if sort is None:

            task_ids = self._task_ids.get(task_type, [])

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

        if id_prefix:
            task_id = "{}_{}".format(id_prefix, task_id)

        self._tasks.setdefault(task_type, {}).setdefault(sort, {})[task_id] = task

        return True

    def remove(self, task_id, task_type="", sort=None):
        """
        Remove the task with the given ID (and optionally, type and/or sort value)
        and return it (or None if not found).

        """

        if self._is_handling_tasks:
            return

        if sort is None:

            task_ids = self._task_ids.get(task_type, [])

            if task_id in task_ids:
                sort = task_ids.index(task_id)
            else:
                sort = 0

            task = self._tasks.get(task_type, {}).get(sort, {}).pop(task_id, None)

            if task and not self._tasks[task_type][sort]:

                del self._tasks[task_type][sort]

                if not self._tasks[task_type]:
                    del self._tasks[task_type]

        return task

    def clear(self, task_type=None):
        """
        Clear the tasks of the given type if it is specified, or all tasks if it is
        None.

        """

        if self._is_handling_tasks:
            return

        (self._tasks if task_type is None else self._tasks.get(task_type, {})).clear()

        if task_type in self._tasks and not self._tasks[task_type]:
            del self._tasks[task_type]

    def handle(self, task_types=None, sort_by_type=False):
        """
        Handle tasks that were added through add(), in an order that corresponds to
        their sort values (and optionally, their type).

        If a list of task_types is given, only those types of tasks will be handled.

        If sort_by_type is True, tasks will first be processed in the order that
        their types appear in the list of task_types, and then by sort value.
        Otherwise, task types are ignored and the tasks are handled in the order
        given by their sort values only.

        """

        if self._is_handling_tasks:
            return

        self._is_handling_tasks = True

        pending_tasks = self._tasks

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

        self._is_handling_tasks = False

    def get_sort(self, task_id, task_type=""):
        """
        Return the sort value of the task with the given ID, or None if the task ID
        is not defined.

        """

        task_ids = self._task_ids.get(task_type, [])

        if task_id in task_ids:
            return task_ids.index(task_id)

    def get_batch_sort(self):

        return self._sort


class PendingTasks(object):

    _batches = {"": PendingTaskBatch()}
    _batch_sort = {0: ""}
    _is_handling_tasks = False
    _handled_batch_sort = None

    @classmethod
    def add_batch(cls, batch_id, batch_sort):

        cls._batches[batch_id] = PendingTaskBatch(batch_sort)
        cls._batch_sort[batch_sort] = batch_id

    @classmethod
    def add(cls, task, task_id, task_type="", sort=None, id_prefix=None, batch_id=""):

        batch = cls._batches[batch_id]

        if cls._is_handling_tasks and batch.get_batch_sort() <= cls._handled_batch_sort:
            return False

        return batch.add(task, task_id, task_type, sort, id_prefix)

    @classmethod
    def remove(cls, task_id, task_type="", sort=None, batch_id=""):

        return cls._batches[batch_id].remove(cls, task_id, task_type, sort)

    @classmethod
    def clear(cls, task_type=None, batch_id=""):

        cls._batches[batch_id].clear(task_type)

    @classmethod
    def handle(cls, task_types=None, sort_by_type=False):

        if cls._is_handling_tasks:
            return

        cls._is_handling_tasks = True

        for i in sorted(cls._batch_sort):
            cls._handled_batch_sort = i
            batch_id = cls._batch_sort[i]
            batch = cls._batches[batch_id]
            batch.handle(task_types, sort_by_type)

        cls._is_handling_tasks = False
        cls._handled_batch_sort = None

    @classmethod
    def get_sort(cls, task_id, task_type="", batch_id=""):

        return cls._batches[batch_id].get_sort(task_id, task_type)
