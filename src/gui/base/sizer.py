from .base import *
from .mgr import GUIManager as Mgr


class SizerItem(object):

    def __init__(self, sizer, obj, obj_type, proportion=0., expand=False,
                 alignment="", borders=None):

        self._sizer = sizer
        self._obj = obj
        self._type = obj_type
        self._proportion = proportion
        self._expand = expand
        self._alignment = alignment

        if borders is None:
            outer_borders = (0, 0, 0, 0)
        else:
            outer_borders = borders

        if obj_type == "widget":
            widget_borders = obj.get_outer_borders()
            outer_borders = tuple(v1 + v2 for v1, v2 in zip(outer_borders, widget_borders))

        l, r, b, t = self._borders = outer_borders

        x = y = 0

        if obj_type == "size":
            w, h = obj
        else:
            w, h = obj.get_min_size()

        w += l
        x = l
        w += r
        h += t
        y = t
        h += b

        self._obj_offset = (x, y)
        self._size = self._min_size = (w, h)
        self._preserve_obj = False

    def destroy(self):

        self._sizer = None

        if not (self._preserve_obj or self._type == "size"):
            self._obj.destroy()

        self._obj = None
        self._type = ""
        self._proportion = 0
        self._expand = False
        self._alignment = ""
        self._borders = (0, 0, 0, 0)
        self._obj_offset = (0, 0)
        self._size = self._min_size = (0, 0)

    def set_sizer(self, sizer):

        self._sizer = sizer

        if self._type == "sizer":
            self._obj.set_owner(sizer)

    def get_sizer(self):

        return self._sizer

    def get_type(self):

        return self._type

    def get_object(self):

        return self._obj

    def preserve_object(self, preserve=True):

        self._preserve_obj = preserve

    def set_proportion(self, proportion):

        self._proportion = proportion

    def get_proportion(self):

        return self._proportion

    def set_expand(self, expand):

        self._expand = expand

    def get_expand(self):

        return self._expand

    def get_alignment(self):

        return self._alignment

    def get_borders(self):

        return self._borders

    def get_object_offset(self):

        return self._obj_offset

    def update_min_size(self):

        if self._type == "size":
            w, h = self._obj
        if self._type == "sizer":
            w, h = self._obj.update_min_size()
        if self._type == "widget":
            w, h = self._obj.get_min_size()

        l, r, b, t = self._borders
        w += l + r
        h += b + t
        self._min_size = (w, h)

        return self._min_size

    def get_min_size(self):

        return self._min_size

    def set_size(self, size):

        width, height = self._size = size
        x = y = 0
        l, r, b, t = self._borders

        if self._type != "size":

            width -= l + r
            height -= t + b
            x += l
            y += t
            stretch_dir = self._sizer.get_stretch_dir()
            w, h = self._obj.get_min_size()

            if stretch_dir == "horizontal":
                if not self._expand:
                    if self._alignment == "bottom":
                        y += height - h
                    elif self._alignment == "center_v":
                        y += (height - h) // 2
            elif stretch_dir == "vertical":
                if not self._expand:
                    if self._alignment == "right":
                        x += width - w
                    elif self._alignment == "center_h":
                        x += (width - w) // 2

            w_new, h_new = w, h

            if stretch_dir == "horizontal":
                if self._proportion > 0.:
                    w_new = width
                if self._expand:
                    h_new = height
            elif stretch_dir == "vertical":
                if self._proportion > 0.:
                    h_new = height
                if self._expand:
                    w_new = width

            new_size = (w_new, h_new)
            self._obj.set_size(new_size)

        self._obj_offset = (x, y)

    def get_size(self):

        return self._size

    def is_hidden(self):

        return False if self._type == "size" else self._obj.is_hidden(check_ancestors=False)


class Sizer(object):

    def __init__(self, stretch_dir="", hidden=False):

        self._type = "sizer"
        self._sizer_type = "sizer"
        self._owner = None
        self._sizer_item = None
        self._stretch_dir = stretch_dir
        self._is_hidden = hidden
        self._pos = (0, 0)
        # minimum size without any contents
        self._default_size = (0, 0)
        # minimum size needed to accommodate current contents, bigger than or equal to default size
        self._min_size = (0, 0)
        self._is_min_size_stale = True
        # current size, bigger than or equal to minimum size needed for current contents
        self._size = (0, 0)
        self._items = []
        self._item_size_locked = False
        self._mouse_regions_locked = False

    def destroy(self):

        for item in self._items:
            item.destroy()

        self._items = []
        self._owner = None
        self._sizer_item = None

    def clear(self, destroy_items=False):

        if destroy_items:
            for item in self._items:
                item.destroy()

        self._items = []
        self.set_min_size_stale()

    def get_type(self):

        return self._type

    def get_sizer_type(self):

        return self._sizer_type

    def set_owner(self, owner):

        self._owner = owner

        if owner and owner.get_type() == "widget":
            self.set_default_size(owner.get_gfx_size())

    def get_owner(self):

        return self._owner

    def set_sizer_item(self, sizer_item):
        """ Create a reference to the SizerItem this subsizer is tracked by """

        self._sizer_item = sizer_item

    def get_sizer_item(self):
        """ Return the SizerItem this sizer is tracked by, in case it is a subsizer """

        return self._sizer_item

    def add(self, obj, proportion=0., expand=False, alignment="", borders=None, index=None):

        obj_type = "size" if type(obj) == tuple else obj.get_type()
        item = SizerItem(self, obj, obj_type, proportion, expand, alignment, borders)

        if index is None:
            self._items.append(item)
        else:
            self._items.insert(index, item)

        self.set_min_size_stale()

        if obj_type == "sizer":
            obj.set_owner(self)

        if obj_type != "size":
            obj.set_sizer_item(item)

        return item

    def add_item(self, item, index=None):

        item.set_sizer(self)

        if index is None:
            self._items.append(item)
        else:
            self._items.insert(index, item)

        self.set_min_size_stale()

    def remove_item(self, item, destroy=False):

        self._items.remove(item)
        item.set_sizer(None)

        if destroy:
            item.destroy()

        self.set_min_size_stale()

    def pop_item(self, index=None):

        item = self._items[-1 if index is None else index]
        self._items.remove(item)
        item.set_sizer(None)
        self.set_min_size_stale()

        return item

    def get_item_index(self, item):

        return self._items.index(item)

    def get_item(self, index):

        return self._items[index]

    def get_items(self):

        return self._items

    def get_item_count(self):

        return len(self._items)

    def get_widgets(self, include_children=True):

        widgets = []

        for item in self._items:

            if item.get_type() == "widget":

                widget = item.get_object()
                widgets.append(widget)

                if include_children:

                    sizer = widget.get_sizer()

                    if sizer:
                        widgets.extend(sizer.get_widgets())

            elif item.get_type() == "sizer":

                widgets.extend(item.get_object().get_widgets(include_children))

        return widgets

    def set_pos(self, pos):

        self._pos = pos

    def get_pos(self, from_root=False):

        x, y = self._pos

        if from_root:

            owner = self._owner

            while owner:

                if owner.get_type() == "widget":
                    x_o, y_o = owner.get_pos(from_root=True)
                    x += x_o
                    y += y_o
                    break

                owner = owner.get_owner()

        return (x, y)

    def get_stretch_dir(self):

        return self._stretch_dir

    def set_default_size(self, size):

        w_d, h_d = self._default_size = size
        w_min, h_min = self._min_size
        self._min_size = w_min, h_min = (max(w_d, w_min), max(h_d, h_min))
        w, h = self._size
        self._size = (max(w_min, w), max(h_min, h))

        if self._sizer_item:
            self._sizer_item.update_min_size()

        self.set_min_size_stale()

    def get_default_size(self):

        return self._default_size

    def set_min_size_stale(self, stale=True):

        self._is_min_size_stale = stale

        if stale and self._owner:

            if self._owner.get_type() == "sizer":

                self._owner.set_min_size_stale()

            elif self._owner.get_type() == "widget":

                item = self._owner.get_sizer_item()

                if item:

                    item_sizer = item.get_sizer()

                    if item_sizer:
                        item_sizer.set_min_size_stale()

    def set_min_size(self, size):
        """
        Force the minimum size, ignoring default and actual sizes.
        Only use in very specific cases where the size is not supposed to change.

        """

        self._min_size = size
        self._is_min_size_stale = False

    def update_min_size(self):

        if not self._is_min_size_stale:
            return self._min_size

        width = height = 0

        for item in self._items:

            if item.get_type() == "widget":

                sizer = item.get_object().get_sizer()

                if sizer:
                    sizer.update_min_size()

            w, h = item.update_min_size()

            if self._stretch_dir == "horizontal":
                if not item.is_hidden():
                    width += w
            else:
                width = max(width, w)

            if self._stretch_dir == "vertical":
                if not item.is_hidden():
                    height += h
            else:
                height = max(height, h)

        w_d, h_d = self._default_size
        self._min_size = width, height = (max(w_d, width), max(h_d, height))
        self._is_min_size_stale = False
        w, h = self._size
        self._size = (max(width, w), max(height, h))

        return self._min_size

    def get_min_size(self):

        return self._min_size

    def __check_proportions(self, items, total_size, sizes, dim):

        proportions = [i.get_proportion() for i in items]
        p_sum = sum(proportions)
        tmp_size = total_size

        for item, proportion in zip(items, proportions):

            s_min = item.get_min_size()[dim]
            s_new = int(round(tmp_size * proportion / p_sum))

            if s_new < s_min:
                items.remove(item)
                index = self._items.index(item)
                sizes[index] = s_min
                total_size -= s_min
                return True, total_size

            p_sum -= proportion
            tmp_size -= s_new

        return False, total_size

    def set_size(self, size, force=False):

        if force:
            self._size = size
            return

        width, height = size
        w_min, h_min = size_min = list(self.get_min_size())
        self._size = (max(w_min, width), max(h_min, height))
        dim = 0 if self._stretch_dir == "horizontal" else 1
        size_min[dim] += sum([i.get_min_size()[dim] for i in self._items if i.is_hidden()])
        w_min, h_min = size_min
        width, height = (max(w_min, width), max(h_min, height))

        if self._item_size_locked:
            return

        widths = heights = None

        if self._stretch_dir == "horizontal":

            widths = [0] * len(self._items)
            sizer_items = self._items[:]

            for index, item in enumerate(self._items):

                proportion = item.get_proportion()

                if proportion == 0.:
                    sizer_items.remove(item)
                    w_min = item.get_min_size()[0]
                    width -= w_min
                    widths[index] = w_min

            check_proportions = True

            while check_proportions:
                check_proportions, width = self.__check_proportions(sizer_items, width, widths, 0)

            proportions = [i.get_proportion() for i in sizer_items]
            p_sum = sum(proportions)
            sizer_items = [(i.get_min_size()[0], i) for i in sizer_items]
            last_item = sizer_items.pop() if sizer_items else None

            for w_min, item in sizer_items:

                proportion = item.get_proportion()
                index = self._items.index(item)
                w_new = int(round(width * proportion / p_sum))

                if w_new < w_min:
                    w_new = w_min

                p_sum -= proportion
                width -= w_new
                widths[index] = w_new

            if last_item:
                w_min, item = last_item
                index = self._items.index(item)
                widths[index] = width

        elif self._stretch_dir == "vertical":

            heights = [0] * len(self._items)
            sizer_items = self._items[:]

            for index, item in enumerate(self._items):

                proportion = item.get_proportion()

                if proportion == 0.:
                    sizer_items.remove(item)
                    h_min = item.get_min_size()[1]
                    height -= h_min
                    heights[index] = h_min

            check_proportions = True

            while check_proportions:
                check_proportions, height = self.__check_proportions(sizer_items, height, heights, 1)

            proportions = [i.get_proportion() for i in sizer_items]
            p_sum = sum(proportions)
            sizer_items = [(i.get_min_size()[1], i) for i in sizer_items]
            last_item = sizer_items.pop() if sizer_items else None

            for h_min, item in sizer_items:

                proportion = item.get_proportion()
                index = self._items.index(item)
                h_new = int(round(height * proportion / p_sum))

                if h_new < h_min:
                    h_new = h_min

                p_sum -= proportion
                height -= h_new
                heights[index] = h_new

            if last_item:
                h_min, item = last_item
                index = self._items.index(item)
                heights[index] = height

        if not (widths or heights):
            return

        if not widths:
            widths = [width] * len(self._items)

        if not heights:
            heights = [height] * len(self._items)

        for item, w, h in zip(self._items, widths, heights):
            item.set_size((w, h))

    def get_size(self):

        return self._size

    def calculate_positions(self, start_pos=(0, 0)):

        if self._item_size_locked:
            return

        x, y = start_x, start_y = start_pos

        for item in self._items:

            obj = item.get_object()
            w, h = item.get_size()
            offset_x, offset_y = item.get_object_offset()
            pos = (x + offset_x, y + offset_y)

            if item.get_type() == "widget":

                obj.set_pos(pos)
                sizer = obj.get_sizer()

                if sizer:
                    sizer.calculate_positions()

            elif item.get_type() == "sizer":

                obj.set_pos(pos)
                obj.calculate_positions(pos)

            if item.is_hidden():
                continue

            if self._stretch_dir == "horizontal":
                x += w

            if self._stretch_dir == "vertical":
                y += h

    def update(self, size=None):

        self.update_min_size()

        if size:
            self.set_size(size)
            self.calculate_positions()

    def update_images(self):

        if self._item_size_locked:
            return

        for item in self._items:
            if item.get_type() != "size":
                item.get_object().update_images()

    def get_composed_image(self, image):

        for item in self._items:

            if item.is_hidden():
                continue

            if item.get_type() == "widget":

                widget = item.get_object()
                img = widget.get_image()

                if img:
                    w = img.get_x_size()
                    h = img.get_y_size()
                    x, y = widget.get_pos()
                    offset_x, offset_y = widget.get_image_offset()
                    x += offset_x
                    y += offset_y
                    image.blend_sub_image(img, x, y, 0, 0, w, h)

            elif item.get_type() == "sizer":

                sizer = item.get_object()
                sizer.get_composed_image(image)

        return image

    def update_mouse_region_frames(self, exclude=""):

        if self._mouse_regions_locked:
            return

        for item in self._items:
            if item.get_type() != "size":
                item.get_object().update_mouse_region_frames(exclude)

    def lock_item_size(self, locked=True):

        self._item_size_locked = locked

    def item_size_locked(self):

        return self._item_size_locked

    def lock_mouse_regions(self, locked=True):

        self._mouse_regions_locked = locked

    def mouse_regions_locked(self):

        return self._mouse_regions_locked

    def hide(self):

        if self._is_hidden:
            return False

        self._is_hidden = True

        return True

    def show(self):

        if not self._is_hidden:
            return False

        self._is_hidden = False

        return True

    def is_hidden(self, check_ancestors=False):

        return self._is_hidden


class ScrollSizer(Sizer):

    def __init__(self, scroll_dir="", stretch_dir="", hidden=False):

        Sizer.__init__(self, stretch_dir, hidden)

        self._sizer_type = "scroll_sizer"
        self._scroll_dir = scroll_dir
        self._stretch_dir = stretch_dir if stretch_dir else scroll_dir
        self._ignore_stretch = False

    def get_min_size(self):

        w, h = self._min_size

        if self._stretch_dir in ("both", "horizontal"):
            w = 0

        if self._stretch_dir in ("both", "vertical"):
            h = 0

        return (w, h)

    def set_virtual_size(self, size):

        self._min_size = size

    def get_virtual_size(self):

        return self._min_size

    def ignore_stretch(self, ignore=True):

        self._ignore_stretch = ignore

    def set_size(self, size, force=False):

        Sizer.set_size(self, size, force)

        if self._ignore_stretch:
            w, h = self._size
            w_min, h_min = self._min_size
            self._size = (min(w_min, w), min(h_min, h))


class GridDataItem(object):

    def __init__(self, obj, proportion_h, proportion_v, stretch_h, stretch_v,
                 alignment_h, alignment_v, borders):

        self._data = (obj, proportion_h, proportion_v, stretch_h, stretch_v,
                      alignment_h, alignment_v, borders)

    def get_data(self):

        return self._data


class GridSizer(Sizer):

    def __init__(self, rows=0, columns=0, gap_h=0, gap_v=0, hidden=False):

        Sizer.__init__(self, "both", hidden)

        self._sizer_type = "grid_sizer"
        self._max_rows = rows
        self._max_cols = columns
        self._gaps = {"horizontal": gap_h, "vertical": gap_v}
        self._sizers = {"horizontal": Sizer("horizontal"), "vertical": Sizer("vertical")}
        self._objs = []
        self._data_items = []

    def destroy(self):

        Sizer.destroy(self)

        self._sizers["horizontal"].destroy()
        self._sizers["vertical"].destroy()
        self._sizers = {}
        self._objs = []
        self._data_items = []

    def clear(self, destroy_items=False):

        Sizer.clear(self, destroy_items)

        self._sizers["horizontal"].clear(destroy_items)
        self._sizers["vertical"].clear(destroy_items)
        self._objs = []
        self._data_items = []

    def __add_to_horizontal_sizer(self, obj, proportion=0., borders=None, index=None):

        # This is a help sizer used to compute the widths of the columns, especially important
        # when horizontal proportions are needed.
        # The calculated width of a column is then set as the default width of the corresponding
        # outer cell sizers.

        gap = self._gaps["horizontal"]
        sizer = self._sizers["horizontal"]
        column_sizer_items = sizer.get_items()
        column_count = len(column_sizer_items)

        if index is None:
            if column_count == 0:
                column_sizer = Sizer("vertical")
                sizer.add(column_sizer, expand=True)
            else:
                column_sizer = column_sizer_items[-1].get_object()
                if column_sizer.get_item_count() == self._max_rows * 2 - 1:
                    sizer.add((gap, 0))
                    column_sizer = Sizer("vertical")
                    sizer.add(column_sizer, expand=True)
        elif index < column_count:
            column_sizer = column_sizer_items[index].get_object()
        else:
            if index > 0:
                sizer.add((gap, 0))
            column_sizer = Sizer("vertical")
            sizer.add(column_sizer, expand=True)

        if column_sizer.get_items():
            column_sizer.add((0, 0))

        column_sizer.add(obj, borders=borders)

        column_sizer_item = column_sizer.get_sizer_item()
        column_proportion = column_sizer_item.get_proportion()
        # the column sizer should have the largest of the horizontal proportions that were passed
        # for its items; all of its items that should resize proportionally in the horizontal
        # direction will end up with the same width, as if they were all given that same largest
        # proportion
        column_proportion = max(column_proportion, proportion)
        column_sizer_item.set_proportion(column_proportion)

    def __add_to_vertical_sizer(self, obj, proportion_h=0., proportion_v=0.,
                                stretch_h=False, stretch_v=False,
                                alignment_h="", alignment_v="",
                                borders=None, index=None):

        # Each object added to the vertical help sizer is wrapped in a nested "cell sizer", i.e.
        # a horizontal inner cell sizer inside a vertical outer cell sizer.
        # The outer cell sizer expands within its horizontal row sizer, while the inner cell sizer
        # is added with proportion=1. to the outer cell sizer.
        # No proportion needs to be set for an outer cell sizer, since its default width will be
        # set to the width of the corresponding column sizer of the horizontal help sizer, after
        # that one has been resized.
        # To stretch or size the added object proportionally in the vertical direction, it needs
        # to expand (the actual proportion applied to the object is the one set on the row sizer).
        # To stretch or size the added object proportionally in the horizontal direction, it needs
        # a non-zero proportion (any value will do; the actual proportion applied to the object is
        # the one set on the column sizer), while its inner cell sizer needs to expand.
        # To align the added object vertically, it simply needs to have the desired alignment set.
        # To align the added object horizontally, its inner cell sizer needs to have the desired
        # alignment set.

        gap_v = self._gaps["vertical"]
        gap_h = self._gaps["horizontal"]
        sizer = self._sizers["vertical"]
        row_sizer_items = sizer.get_items()
        row_count = len(row_sizer_items)

        if index is None:
            if row_count == 0:
                row_sizer = Sizer("horizontal")
                sizer.add(row_sizer, expand=True)
            else:
                row_sizer = row_sizer_items[-1].get_object()
                if row_sizer.get_item_count() == self._max_cols * 2 - 1:
                    sizer.add((0, gap_v))
                    row_sizer = Sizer("horizontal")
                    sizer.add(row_sizer, expand=True)
        elif index < row_count:
            row_sizer = row_sizer_items[index].get_object()
        else:
            if index > 0:
                sizer.add((0, gap_v))
            row_sizer = Sizer("horizontal")
            sizer.add(row_sizer, expand=True)

        row_sizer_item = row_sizer.get_sizer_item()
        row_proportion = row_sizer_item.get_proportion()
        # the row sizer should have the largest of the vertical proportions that were passed for
        # its items; all of its items that should resize proportionally in the vertical direction
        # will end up with the same height, as if they were all given that same largest proportion
        row_proportion = max(row_proportion, proportion_v)
        row_sizer_item.set_proportion(row_proportion)

        if row_sizer.get_items():
            row_sizer.add((gap_h, 0))

        outer_cell_sizer = Sizer("vertical")
        row_sizer.add(outer_cell_sizer, expand=True)
        inner_cell_sizer = Sizer("horizontal")
        expand = stretch_h or proportion_h > 0.
        outer_cell_sizer.add(inner_cell_sizer, 1., expand, alignment_h)
        proportion = 1. if expand else 0.
        expand = stretch_v or proportion_v > 0.

        return inner_cell_sizer.add(obj, proportion, expand, alignment_v, borders)

    def add(self, obj, proportion_h=0., proportion_v=0., stretch_h=False, stretch_v=False,
            alignment_h="", alignment_v="", borders=None, rebuilding=False):

        grow_dir = "vertical" if self._max_rows == 0 else "horizontal"

        if grow_dir == "vertical":
            item = self.__add_to_vertical_sizer(obj, proportion_h, proportion_v,
                                                stretch_h, stretch_v,
                                                alignment_h, alignment_v, borders)
        else:
            self.__add_to_horizontal_sizer(obj, proportion_h)

        index = self._sizers[grow_dir].get_items()[-1].get_object().get_item_count() - 1

        if grow_dir == "vertical":
            self.__add_to_horizontal_sizer(obj, proportion_h, borders, index)
        else:
            item = self.__add_to_vertical_sizer(obj, proportion_h, proportion_v,
                                                stretch_h, stretch_v,
                                                alignment_h, alignment_v, borders, index)

        if item.get_type() != "size":
            obj.set_sizer_item(item)

        if not rebuilding:
            self._objs.append(obj)
            self._data_items.append(GridDataItem(obj, proportion_h, proportion_v,
                                                 stretch_h, stretch_v,
                                                 alignment_h, alignment_v, borders))

        Sizer.set_min_size_stale(self)

    def rebuild(self):

        sizer = self._sizers["horizontal"]

        for column_item in sizer.get_items()[::2]:
            for item in column_item.get_object().get_items()[::2]:
                item.preserve_object()

        sizer.destroy()

        sizer = self._sizers["vertical"]

        for row_item in sizer.get_items()[::2]:
            for item in row_item.get_object().get_items()[::2]:
                item.get_object().get_item(0).get_object().get_item(0).preserve_object()

        sizer.destroy()

        self._sizers = {"horizontal": Sizer("horizontal"), "vertical": Sizer("vertical")}

        for item in self._data_items:
            self.add(*item.get_data(), rebuilding=True)

    def remove(self, obj, destroy=False, rebuild=True):

        Sizer.set_min_size_stale(self)

        index = self._objs.index(obj)
        self._objs.remove(obj)
        del self._data_items[index]

        if destroy:
            obj.destroy()

        if rebuild:
            self.rebuild()

    def get_widgets(self, include_children=True):

        return self._sizers["horizontal"].get_widgets(include_children)

    def set_pos(self, pos):

        Sizer.set_pos(self, pos)

        self._sizers["vertical"].set_pos(pos)

    def set_default_size(self, size):

        Sizer.set_default_size(self, size)

        self._sizers["horizontal"].set_default_size(size)
        self._sizers["vertical"].set_default_size(size)

    def set_min_size_stale(self, stale=True):

        Sizer.set_min_size_stale(self, stale)

        self._sizers["horizontal"].set_min_size_stale(stale)
        self._sizers["vertical"].set_min_size_stale(stale)

    def update_min_size(self):

        self._sizers["horizontal"].update_min_size()
        min_size = self._sizers["vertical"].update_min_size()
        self.set_min_size(min_size)

        return min_size

    def set_size(self, size, force=False):

        sizer_h = self._sizers["horizontal"]
        sizer_v = self._sizers["vertical"]

        # compute the widths of the column sizers
        sizer_h.set_size(size, force)

        row_sizers = [i.get_object() for i in sizer_v.get_items()[::2]]
        # retrieve the widths of the column sizers (the slice removes the horizontal gaps)
        widths = [i.get_size()[0] for i in sizer_h.get_items()[::2]]

        for row_sizer in row_sizers:
            for cell_sizer_item, w in zip(row_sizer.get_items()[::2], widths):
                cell_sizer_item.get_object().set_default_size((w, 0))

        sizer_v.set_size(size, force)

        new_size = sizer_v.get_size()
        Sizer.set_size(self, new_size, force=True)

    def calculate_positions(self, start_pos=(0, 0)):

        self._sizers["vertical"].calculate_positions(start_pos)

    def update_images(self):

        self._sizers["vertical"].update_images()

    def get_composed_image(self, image):

        self._sizers["vertical"].get_composed_image(image)

        return image

    def update_mouse_region_frames(self, exclude=""):

        self._sizers["vertical"].update_mouse_region_frames(exclude)

    def hide(self):

        if not Sizer.hide(self):
            return False

        self._sizers["vertical"].hide()

        return True

    def show(self):

        if not Sizer.show(self):
            return False

        self._sizers["vertical"].show()

        return True
