from .base import *
from .mgr import GUIManager as Mgr


class SizerItem:

    def __init__(self, sizer, obj, obj_type, proportion=0., expand=False,
                 alignment="", borders=None):

        self._sizer = sizer
        self._obj = obj
        self._type = obj_type
        self.proportion = proportion
        self.expand = expand
        self.alignment = alignment

        if borders is None:
            outer_borders = (0, 0, 0, 0)
        else:
            outer_borders = borders

        if obj_type == "widget":
            widget_borders = obj.outer_borders
            outer_borders = tuple(v1 + v2 for v1, v2 in zip(outer_borders, widget_borders))

        l, r, b, t = self._borders = outer_borders
        self._obj_offset = (l, t)

        if obj_type == "size":
            w, h = obj
        else:
            w, h = obj.min_size

        w += l + r
        h += b + t
        self._size = self._min_size = (w, h)
        self._preserve_obj = False

    def destroy(self):

        self._sizer = None

        if not (self._preserve_obj or self._type == "size"):
            self._obj.destroy()

        self._obj = None
        self._type = ""
        self.proportion = 0
        self.expand = False
        self.alignment = ""
        self._borders = (0, 0, 0, 0)
        self._obj_offset = (0, 0)
        self._size = self._min_size = (0, 0)

    @property
    def type(self):

        return self._type

    @property
    def sizer(self):

        return self._sizer

    @sizer.setter
    def sizer(self, sizer):

        self._sizer = sizer

        if self._type == "sizer":
            self._obj.owner = sizer

    @property
    def object(self):

        return self._obj

    @property
    def object_offset(self):

        return self._obj_offset

    def preserve_object(self, preserve=True):

        self._preserve_obj = preserve

    @property
    def borders(self):

        return self._borders

    @borders.setter
    def borders(self, borders):

        if borders is None:
            outer_borders = (0, 0, 0, 0)
        else:
            outer_borders = borders

        l, r, b, t = self._borders = outer_borders
        self._obj_offset = (l, t)

    @property
    def min_size(self):

        return self._min_size

    def update_min_size(self):

        if self._type == "size":
            w, h = self._obj
        if self._type == "sizer":
            w, h = self._obj.update_min_size()
        if self._type == "widget":
            w, h = self._obj.min_size

        l, r, b, t = self._borders
        w += l + r
        h += b + t
        self._min_size = (w, h)

        return self._min_size

    def get_size(self):

        return self._size

    def set_size(self, size):

        width, height = self._size = size
        x = y = 0
        l, r, b, t = self._borders

        if self._type != "size":

            width -= l + r
            height -= t + b
            x += l
            y += t
            grow_dir = self._sizer.grow_dir
            w, h = self._obj.min_size

            if grow_dir == "horizontal":
                if not self.expand:
                    if self.alignment == "bottom":
                        y += height - h
                    elif self.alignment == "center_v":
                        y += (height - h) // 2
            elif grow_dir == "vertical":
                if not self.expand:
                    if self.alignment == "right":
                        x += width - w
                    elif self.alignment == "center_h":
                        x += (width - w) // 2

            w_new, h_new = w, h

            if grow_dir == "horizontal":
                if self.proportion > 0.:
                    w_new = width
                if self.expand:
                    h_new = height
            elif grow_dir == "vertical":
                if self.proportion > 0.:
                    h_new = height
                if self.expand:
                    w_new = width

            new_size = (w_new, h_new)
            self._obj.set_size(new_size)

        self._obj_offset = (x, y)

    def is_hidden(self):

        return False if self._type == "size" else self._obj.is_hidden(check_ancestors=False)


class Sizer:

    def __init__(self, grow_dir="", hidden=False):

        self._type = "sizer"
        self._sizer_type = "sizer"
        self._owner = None
        # the SizerItem this sizer is tracked by, in case it is a subsizer
        self.sizer_item = None
        self.grow_dir = grow_dir
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
        self.item_size_locked = False
        self.mouse_regions_locked = False

    def destroy(self):

        for item in self._items:
            item.destroy()

        self._items = []
        self._owner = None
        self.sizer_item = None

    def clear(self, destroy_items=False):

        if destroy_items:
            for item in self._items:
                item.destroy()

        self._items = []
        self.set_min_size_stale()

    @property
    def type(self):

        return self._type

    @property
    def sizer_type(self):

        return self._sizer_type

    @property
    def owner(self):

        return self._owner

    @owner.setter
    def owner(self, owner):

        self._owner = owner

        if owner and owner.type == "widget":
            self.default_size = owner.gfx_size

    def add(self, obj, proportion=0., expand=False, alignment="", borders=None, index=None):

        obj_type = "size" if type(obj) == tuple else obj.type
        item = SizerItem(self, obj, obj_type, proportion, expand, alignment, borders)

        if index is None:
            self._items.append(item)
        else:
            self._items.insert(index, item)

        self.set_min_size_stale()

        if obj_type == "sizer":
            obj.owner = self

        if obj_type != "size":
            obj.sizer_item = item

        return item

    def add_item(self, item, index=None):

        item.sizer = self

        if index is None:
            self._items.append(item)
        else:
            self._items.insert(index, item)

        self.set_min_size_stale()

    def remove_item(self, item, destroy=False):

        self._items.remove(item)
        item.sizer = None

        if destroy:
            item.destroy()

        self.set_min_size_stale()

    def pop_item(self, index=None):

        item = self._items[-1 if index is None else index]
        self._items.remove(item)
        item.sizer = None
        self.set_min_size_stale()

        return item

    @property
    def items(self):

        return self._items

    def get_widgets(self, include_children=True):

        widgets = []

        for item in self._items:

            if item.type == "widget":

                widget = item.object
                widgets.append(widget)

                if include_children:

                    sizer = widget.sizer

                    if sizer:
                        widgets.extend(sizer.get_widgets())

            elif item.type == "sizer":

                widgets.extend(item.object.get_widgets(include_children))

        return widgets

    def get_pos(self, from_root=False):

        x, y = self._pos

        if from_root:

            owner = self._owner

            while owner:

                if owner.type == "widget":
                    x_o, y_o = owner.get_pos(from_root=True)
                    x += x_o
                    y += y_o
                    break

                owner = owner.owner

        return (x, y)

    def set_pos(self, pos):

        self._pos = pos

    @property
    def default_size(self):

        return self._default_size

    @default_size.setter
    def default_size(self, size):

        w_d, h_d = self._default_size = size
        w_min, h_min = self._min_size
        self._min_size = w_min, h_min = (max(w_d, w_min), max(h_d, h_min))
        w, h = self._size
        self._size = (max(w_min, w), max(h_min, h))

        if self.sizer_item:
            self.sizer_item.update_min_size()

        self.set_min_size_stale()

    def set_min_size_stale(self, stale=True):

        self._is_min_size_stale = stale

        if stale and self._owner:

            if self._owner.type == "sizer":

                self._owner.set_min_size_stale()

            elif self._owner.type == "widget":

                item = self._owner.sizer_item

                if item:

                    item_sizer = item.sizer

                    if item_sizer:
                        item_sizer.set_min_size_stale()

    @property
    def min_size(self):

        return self._min_size

    @min_size.setter
    def min_size(self, size):
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

            if item.type == "widget":

                sizer = item.object.sizer

                if sizer:
                    sizer.update_min_size()

            w, h = item.update_min_size()

            if self.grow_dir == "horizontal":
                if not item.is_hidden():
                    width += w
            else:
                width = max(width, w)

            if self.grow_dir == "vertical":
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

    def __check_proportions(self, items, total_size, sizes, dim):

        proportions = [i.proportion for i in items]
        p_sum = sum(proportions)
        tmp_size = total_size

        for item, proportion in zip(items, proportions):

            s_min = item.min_size[dim]
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
        w_min, h_min = size_min = list(self.min_size)
        self._size = (max(w_min, width), max(h_min, height))
        dim = 0 if self.grow_dir == "horizontal" else 1
        size_min[dim] += sum([i.min_size[dim] for i in self._items if i.is_hidden()])
        w_min, h_min = size_min
        width, height = (max(w_min, width), max(h_min, height))

        if self.item_size_locked:
            return

        widths = heights = None

        if self.grow_dir == "horizontal":

            widths = [0] * len(self._items)
            sizer_items = self._items[:]

            for index, item in enumerate(self._items):

                proportion = item.proportion

                if proportion == 0.:
                    sizer_items.remove(item)
                    w_min = item.min_size[0]
                    width -= w_min
                    widths[index] = w_min

            check_proportions = True

            while check_proportions:
                check_proportions, width = self.__check_proportions(sizer_items, width, widths, 0)

            proportions = [i.proportion for i in sizer_items]
            p_sum = sum(proportions)
            sizer_items = [(i.min_size[0], i) for i in sizer_items]
            last_item = sizer_items.pop() if sizer_items else None

            for w_min, item in sizer_items:

                proportion = item.proportion
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

        elif self.grow_dir == "vertical":

            heights = [0] * len(self._items)
            sizer_items = self._items[:]

            for index, item in enumerate(self._items):

                proportion = item.proportion

                if proportion == 0.:
                    sizer_items.remove(item)
                    h_min = item.min_size[1]
                    height -= h_min
                    heights[index] = h_min

            check_proportions = True

            while check_proportions:
                check_proportions, height = self.__check_proportions(sizer_items, height, heights, 1)

            proportions = [i.proportion for i in sizer_items]
            p_sum = sum(proportions)
            sizer_items = [(i.min_size[1], i) for i in sizer_items]
            last_item = sizer_items.pop() if sizer_items else None

            for h_min, item in sizer_items:

                proportion = item.proportion
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

        if self.item_size_locked:
            return

        x, y = start_x, start_y = start_pos

        for item in self._items:

            obj = item.object
            w, h = item.get_size()
            offset_x, offset_y = item.object_offset
            pos = (x + offset_x, y + offset_y)

            if item.type == "widget":

                obj.set_pos(pos)
                sizer = obj.sizer

                if sizer:
                    sizer.calculate_positions()

            elif item.type == "sizer":

                obj.set_pos(pos)
                obj.calculate_positions(pos)

            if item.is_hidden():
                continue

            if self.grow_dir == "horizontal":
                x += w

            if self.grow_dir == "vertical":
                y += h

    def update(self, size=None):

        self.update_min_size()

        if size:
            self.set_size(size)
            self.calculate_positions()

    def update_images(self):

        if self.item_size_locked:
            return

        for item in self._items:
            if item.type != "size":
                item.object.update_images()

    def get_composed_image(self, image):

        for item in self._items:

            if item.is_hidden():
                continue

            if item.type == "widget":

                widget = item.object
                img = widget.get_image()

                if img:
                    w, h = img.size
                    x, y = widget.get_pos()
                    offset_x, offset_y = widget.image_offset
                    x += offset_x
                    y += offset_y
                    image.blend_sub_image(img, x, y, 0, 0, w, h)

            elif item.type == "sizer":

                sizer = item.object
                sizer.get_composed_image(image)

        return image

    def update_mouse_region_frames(self, exclude=""):

        if self.mouse_regions_locked:
            return

        for item in self._items:
            if item.type != "size":
                item.object.update_mouse_region_frames(exclude)

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

    def __init__(self, scroll_dir="", grow_dir="", hidden=False):

        Sizer.__init__(self, grow_dir, hidden)

        self._sizer_type = "scroll_sizer"
        self.scroll_dir = scroll_dir
        self.grow_dir = grow_dir if grow_dir else scroll_dir
        self.ignore_stretch = False

    @property
    def min_size(self):

        w, h = self._min_size

        if self.scroll_dir == "horizontal":
            w = 0

        if self.scroll_dir == "vertical":
            h = 0

        return (w, h)

    @property
    def virtual_size(self):

        return self._min_size

    @virtual_size.setter
    def virtual_size(self, size):

        self._min_size = size

    def set_size(self, size, force=False):

        Sizer.set_size(self, size, force)

        if self.ignore_stretch:
            w, h = self._size
            w_min, h_min = self._min_size
            self._size = (min(w_min, w), min(h_min, h))


class GridDataItem:

    def __init__(self, obj, proportion_h, proportion_v, expand_h, expand_v,
                 alignment_h, alignment_v, borders, sizer_item):

        self._data = [obj, proportion_h, proportion_v, expand_h, expand_v,
                      alignment_h, alignment_v, borders, None, False, sizer_item]

    def set_sizer_item(self, sizer_item):

        self._data[-1] = sizer_item

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
        self._data_items = []
        self._proportions = {"row": {}, "column": {}}

    def destroy(self):

        self._items = []

        Sizer.destroy(self)

        self._sizers["horizontal"].destroy()
        self._sizers["vertical"].destroy()
        self._sizers = {}
        self._data_items = []
        self._proportions = {"row": {}, "column": {}}

    def clear(self, destroy_items=False):

        self._items = []

        Sizer.clear(self, destroy_items)

        self._sizers["horizontal"].clear(destroy_items)
        self._sizers["vertical"].clear(destroy_items)
        self._data_items = []
        self._proportions = {"row": {}, "column": {}}

    def __add_to_horizontal_sizer(self, obj, proportion=0., borders=None, index=None):

        # A horizontal help sizer is used to compute the widths of the columns,
        # especially important when horizontal proportions are needed.
        # The calculated width of a column is then set as the default width of
        # the corresponding outer cell sizers.

        gap = self._gaps["horizontal"]
        sizer = self._sizers["horizontal"]
        column_sizer_items = sizer.items
        column_count = len(column_sizer_items)

        if index is None:
            if column_count == 0:
                column_sizer = Sizer("vertical")
                sizer.add(column_sizer, expand=True)
            else:
                column_sizer = column_sizer_items[-1].object
                if len(column_sizer.items) == self._max_rows * 2 - 1:
                    sizer.add((gap, 0))
                    column_sizer = Sizer("vertical")
                    sizer.add(column_sizer, expand=True)
        elif index < column_count:
            column_sizer = column_sizer_items[index].object
        else:
            if index > 0:
                sizer.add((gap, 0))
            column_sizer = Sizer("vertical")
            sizer.add(column_sizer, expand=True)

        if column_sizer.items:
            column_sizer.add((0, 0))

        column_sizer.add(obj, borders=borders)

        column_sizer_item = column_sizer.sizer_item
        proportions = self._proportions["column"]
        column_index = column_sizer_items[::2].index(column_sizer_item)

        if column_index in proportions:
            column_proportion = proportions[column_index]
        else:
            column_proportion = column_sizer_item.proportion
            # the column sizer should have the largest of the horizontal proportions
            # that were passed for its items; all of its items that should resize
            # proportionately in the horizontal direction will end up with the same
            # width, as if they were all given that same largest proportion
            column_proportion = max(column_proportion, proportion)

        column_sizer_item.proportion = column_proportion

    def __add_to_vertical_sizer(self, obj, proportion_h=0., proportion_v=0.,
                                expand_h=False, expand_v=False,
                                alignment_h="", alignment_v="",
                                borders=None, index=None):

        # Each object added to the vertical help sizer is wrapped in a nested "cell sizer", i.e.
        # a horizontal inner cell sizer inside a vertical outer cell sizer.
        # The outer cell sizer expands within its horizontal row sizer, while the inner cell sizer
        # is added with proportion=1. to the outer cell sizer.
        # No proportion needs to be set for an outer cell sizer, since its default width will be
        # set to the width of the corresponding column sizer of the horizontal help sizer, after
        # that one has been resized.
        # If expand_v is True or proportion_v is non-zero, the added object needs to expand (any
        # proportion applied to the object is the one set on the row sizer).
        # If expand_h is True or proportion_h is non-zero, the added object needs a non-zero
        # proportion (any value will do; the actual proportion applied to the object is the one
        # set on the column sizer), while its inner cell sizer needs to expand.
        # To align the added object vertically, it simply needs to have the desired alignment set.
        # To align the added object horizontally, its inner cell sizer needs to have the desired
        # alignment set.

        gap_v = self._gaps["vertical"]
        gap_h = self._gaps["horizontal"]
        sizer = self._sizers["vertical"]
        row_sizer_items = sizer.items
        row_count = len(row_sizer_items)

        if index is None:
            if row_count == 0:
                row_sizer = Sizer("horizontal")
                sizer.add(row_sizer, expand=True)
            else:
                row_sizer = row_sizer_items[-1].object
                if len(row_sizer.items) == self._max_cols * 2 - 1:
                    sizer.add((0, gap_v))
                    row_sizer = Sizer("horizontal")
                    sizer.add(row_sizer, expand=True)
        elif index < row_count:
            row_sizer = row_sizer_items[index].object
        else:
            if index > 0:
                sizer.add((0, gap_v))
            row_sizer = Sizer("horizontal")
            sizer.add(row_sizer, expand=True)

        row_sizer_item = row_sizer.sizer_item
        proportions = self._proportions["row"]
        row_index = row_sizer_items[::2].index(row_sizer_item)

        if row_index in proportions:
            row_proportion = proportions[row_index]
        else:
            row_proportion = row_sizer_item.proportion
            # the row sizer should have the largest of the vertical proportions
            # that were passed for its items; all of its items that should resize
            # proportionately in the vertical direction will end up with the same
            # height, as if they were all given that same largest proportion
            row_proportion = max(row_proportion, proportion_v)

        row_sizer_item.proportion = row_proportion

        if row_sizer.items:
            row_sizer.add((gap_h, 0))

        outer_cell_sizer = Sizer("vertical")
        row_sizer.add(outer_cell_sizer, expand=True)
        inner_cell_sizer = Sizer("horizontal")
        expand = expand_h or proportion_h > 0.
        outer_cell_sizer.add(inner_cell_sizer, 1., expand, alignment_h)
        proportion = 1. if expand else 0.
        expand = expand_v or proportion_v > 0.

        return inner_cell_sizer.add(obj, proportion, expand, alignment_v, borders)

    def add(self, obj, proportion_h=0., proportion_v=0., expand_h=False,
            expand_v=False, alignment_h="", alignment_v="", borders=None,
            index=None, rebuild=True, _old_item=None):

        grow_dir = "vertical" if self._max_rows == 0 else "horizontal"

        if grow_dir == "vertical":
            item = self.__add_to_vertical_sizer(obj, proportion_h, proportion_v,
                                                expand_h, expand_v,
                                                alignment_h, alignment_v, borders)
        else:
            self.__add_to_horizontal_sizer(obj, proportion_h)

        subsizer_index = len(self._sizers[grow_dir].items[-1].object.items) - 1

        if grow_dir == "vertical":
            self.__add_to_horizontal_sizer(obj, proportion_h, borders, subsizer_index)
        else:
            item = self.__add_to_vertical_sizer(obj, proportion_h, proportion_v,
                                                expand_h, expand_v, alignment_h,
                                                alignment_v, borders, subsizer_index)

        if item.type != "size":
            obj.sizer_item = item

        if _old_item:
            item_index = self._items.index(_old_item)
            self._items[item_index] = item
            self._data_items[item_index].set_sizer_item(item)
        elif index is None:
            self._items.append(item)
            self._data_items.append(GridDataItem(obj, proportion_h, proportion_v,
                                                 expand_h, expand_v, alignment_h,
                                                 alignment_v, borders, item))
        else:
            self._items.insert(index, item)
            self._data_items.insert(index, GridDataItem(obj, proportion_h, proportion_v,
                                                        expand_h, expand_v, alignment_h,
                                                        alignment_v, borders, item))
            if rebuild:
                self.rebuild()

        Sizer.set_min_size_stale(self)

    def rebuild(self):
        """
        Destroy the sub-sizers used for this grid sizer and move its items
        to new sub-sizers. This is necessary after any change that affects
        previously added items (a notable exception is appending - as
        opposed to inserting - items, which does not require a rebuild).

        """

        sizer = self._sizers["horizontal"]

        for column_item in sizer.items[::2]:
            for item in column_item.object.items[::2]:
                item.preserve_object()

        sizer.destroy()

        sizer = self._sizers["vertical"]

        for row_item in sizer.items[::2]:
            for item in row_item.object.items[::2]:
                item.object.items[0].object.items[0].preserve_object()

        sizer.destroy()

        self._sizers = {"horizontal": Sizer("horizontal"), "vertical": Sizer("vertical")}

        for item in self._data_items:
            self.add(*item.get_data())

    def add_item(self, item, index=None): pass

    def remove_item(self, item, destroy=False, rebuild=True):

        Sizer.set_min_size_stale(self)

        index = self._items.index(item)
        self._items.remove(item)
        del self._data_items[index]

        if destroy:
            item.destroy()

        if rebuild:
            self.rebuild()

    def has_row_proportion(self, index):
        """
        Check whether a vertical proportion has been explicitly set for the
        row with the given index.

        """

        return index in self._proportions["row"]

    def get_row_proportion(self, index):
        """
        Return the vertical proportion that has been explicitly set for the
        row with the given index.
        It is an error to call this if has_row_proportion returns False.

        """

        assert self.has_row_proportion(index)
        return self._proportions["row"][index]

    def set_row_proportion(self, index, proportion, rebuild=True):
        """
        Explicitly set a vertical proportion for the row with the given
        index. It will override the vertical proportions set on any item
        added to that row.

        """

        self._proportions["row"][index] = proportion

        if rebuild:
            self.rebuild()

    def clear_row_proportion(self, index, rebuild=True):
        """
        Remove the vertical proportion that has been explicitly set for the
        row with the given index. This undoes the effect of a previous call
        to set_row_proportion for that row; its new vertical proportion
        will be the largest one passed for its items.

        """

        if index not in self._proportions["row"]:
            return

        del self._proportions["row"][index]

        if rebuild:
            self.rebuild()

    def clear_row_proportions(self, rebuild=True):
        """
        Remove the vertical proportions that were explicitly set for any of
        the rows of this sizer.
        See clear_row_proportion.

        """

        self._proportions["row"].clear()

        if rebuild:
            self.rebuild()

    def has_column_proportion(self, index):
        """
        Check whether a horizontal proportion has been explicitly set for the
        column with the given index.

        """

        return index in self._proportions["column"]

    def get_column_proportion(self, index):
        """
        Return the horizontal proportion that has been explicitly set for the
        column with the given index.
        It is an error to call this if has_column_proportion returns False.

        """

        assert self.has_column_proportion(index)
        return self._proportions["column"][index]

    def set_column_proportion(self, index, proportion, rebuild=True):
        """
        Explicitly set a horizontal proportion for the column with the given
        index. It will override the horizontal proportions set on any item
        added to that column.

        """

        self._proportions["column"][index] = proportion

        if rebuild:
            self.rebuild()

    def clear_column_proportion(self, index, rebuild=True):
        """
        Remove the horizontal proportion that has been explicitly set for the
        column with the given index. This undoes the effect of a previous call
        to set_column_proportion for that column; its new horizontal proportion
        will be the largest one passed for its items.

        """

        if index not in self._proportions["column"]:
            return

        del self._proportions["column"][index]

        if rebuild:
            self.rebuild()

    def clear_column_proportions(self, rebuild=True):
        """
        Remove the horizontal proportions that were explicitly set for any of
        the columns of this sizer.
        See clear_column_proportion.

        """

        self._proportions["column"].clear()

        if rebuild:
            self.rebuild()

    def clear_proportions(self, rebuild=True):
        """
        Remove the proportions that were explicitly set for any of the rows
        and columns of this sizer.
        See clear_row_proportion and clear_column_proportion.

        """

        self._proportions["row"].clear()
        self._proportions["column"].clear()

        if rebuild:
            self.rebuild()

    def get_widgets(self, include_children=True):

        return self._sizers["horizontal"].get_widgets(include_children)

    def set_pos(self, pos):

        Sizer.set_pos(self, pos)

        self._sizers["vertical"].set_pos(pos)

    @property
    def default_size(self):

        return Sizer.default_size.fget(self)

    @default_size.setter
    def default_size(self, size):

        Sizer.default_size.fset(self, size)

        self._sizers["horizontal"].default_size = size
        self._sizers["vertical"].default_size = size

    def set_min_size_stale(self, stale=True):

        Sizer.set_min_size_stale(self, stale)

        self._sizers["horizontal"].set_min_size_stale(stale)
        self._sizers["vertical"].set_min_size_stale(stale)

    def update_min_size(self):

        min_w = self._sizers["horizontal"].update_min_size()[0]
        min_h = self._sizers["vertical"].update_min_size()[1]
        min_size = (min_w, min_h)
        self.min_size = min_size

        return min_size

    def set_size(self, size, force=False):

        sizer_h = self._sizers["horizontal"]
        sizer_v = self._sizers["vertical"]

        # compute the widths of the column sizers
        sizer_h.set_size(size, force)

        row_sizers = [i.object for i in sizer_v.items[::2]]
        # retrieve the widths of the column sizers (the slice removes the horizontal gaps)
        widths = [i.get_size()[0] for i in sizer_h.items[::2]]

        for row_sizer in row_sizers:
            for cell_sizer_item, w in zip(row_sizer.items[::2], widths):
                cell_sizer_item.object.default_size = (w, 0)

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
