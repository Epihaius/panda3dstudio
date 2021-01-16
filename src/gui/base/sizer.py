from .base import *


class SizerCell:

    def __init__(self, sizer, obj, obj_type, proportions, alignments, borders):

        self._sizer = sizer
        self._obj = obj
        self._type = obj_type
        self.proportions = proportions if proportions else (-1., -1.)
        self.alignments = alignments if alignments else ("expand", "expand")
        outer_borders = borders if borders else (0, 0, 0, 0)

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

    def destroy(self):

        self._sizer = None

        if self._type != "size":
            self._obj.destroy()

        self._obj = None
        self._type = ""
        self.proportions = (-1., -1.)
        self.alignments = ("expand", "expand")
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

    @object.setter
    def object(self, obj):

        prev_obj = self._obj
        prev_type = self._type
        obj_type = "size" if type(obj) == tuple else obj.type
        self._obj = obj
        self._type = obj_type

        if obj_type == "sizer":
            obj.owner = self._sizer

        if obj_type != "size":
            obj.sizer_cell = self

        outer_borders = self._borders

        if prev_type == "widget":
            widget_borders = prev_obj.outer_borders
            outer_borders = tuple(v1 - v2 for v1, v2 in zip(outer_borders, widget_borders))

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

    @property
    def object_offset(self):

        return self._obj_offset

    @property
    def borders(self):

        return self._borders

    @borders.setter
    def borders(self, borders):

        if borders is None:
            outer_borders = (0, 0, 0, 0)
        else:
            outer_borders = borders

        if self._type == "widget":
            widget_borders = self._obj.outer_borders
            outer_borders = tuple(v1 + v2 for v1, v2 in zip(outer_borders, widget_borders))

        l, r, b, t = self._borders = outer_borders
        self._obj_offset = (l, t)

    @property
    def min_size(self):

        return self._min_size

    def update_min_size(self):

        if self._type == "size":
            w, h = self._obj
        elif self._type == "sizer":
            w, h = self._obj.update_min_size()
        elif self._type == "widget":
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
        offset = [0, 0]

        if self._type != "size":

            size = [width, height]
            l, r, b, t = self._borders
            size[0] -= l + r
            size[1] -= t + b
            offset[0] += l
            offset[1] += t
            w, h = self._obj.min_size
            new_size = [w, h]
            prim_dim = self._sizer.prim_dim

            if self.alignments[prim_dim] == "max":
                offset[prim_dim] += size[prim_dim] - new_size[prim_dim]
            elif self.alignments[prim_dim] == "center":
                offset[prim_dim] += (size[prim_dim] - new_size[prim_dim]) // 2

            if self.alignments[1-prim_dim] == "max":
                offset[1-prim_dim] += size[1-prim_dim] - new_size[1-prim_dim]
            elif self.alignments[1-prim_dim] == "center":
                offset[1-prim_dim] += (size[1-prim_dim] - new_size[1-prim_dim]) // 2

            if self.alignments[prim_dim] == "expand":
                new_size[prim_dim] = size[prim_dim]
            if self.alignments[1-prim_dim] == "expand":
                new_size[1-prim_dim] = size[1-prim_dim]

            self._obj.set_size(tuple(new_size))

        self._obj_offset = tuple(offset)

    @property
    def mouse_regions(self):

        regions = set()

        if self._type == "sizer":

            for widget in self._obj.get_widgets():
                regions.add(widget.mouse_region)

        elif self._type == "widget":

            regions.add(self._obj.mouse_region)

            if self._obj.sizer:
                for widget in self._obj.sizer.get_widgets():
                    regions.add(widget.mouse_region)

        regions.discard(None)

        return regions


class Sizer:

    _global_default_proportions = (0., 0.)

    def __init__(self, prim_dir, prim_limit=0, gaps=(0, 0)):

        self.name = ""
        self._type = "sizer"
        self._owner = None
        # the SizerCell this sizer is inside of, in case it is a subsizer
        self.sizer_cell = None
        # prim_dir: the primary direction in which cells are added to this sizer
        self.prim_dim = 0 if prim_dir == "horizontal" else 1
        # max. number of cells in each row (horizontal growth) or column (vertical growth)
        self.prim_limit = prim_limit
        self._gaps = [gaps[0], gaps[1]]
        self._default_proportions = (-1., -1.)
        self._proportions = [{}, {}]
        self._pos = (0, 0)
        # minimum size without any contents
        self._default_size = (0, 0)
        # minimum size needed to accommodate current contents, bigger than or equal to default size
        self._min_size = (0, 0)
        self._is_min_size_stale = True
        # current size, bigger than or equal to minimum size needed for current contents
        self._size = (0, 0)
        self._cells = []
        self.cell_size_locked = False
        self.mouse_regions_locked = False

    def destroy(self):

        for cell in self._cells:
            cell.destroy()

        self._cells = []
        self._owner = None
        self.sizer_cell = None

    def clear(self, destroy_cells=False):

        if destroy_cells:
            for cell in self._cells:
                cell.destroy()

        self._cells = []
        self.set_min_size_stale()

    @property
    def type(self):

        return self._type

    @property
    def prim_dir(self):

        return "horizontal" if self.prim_dim == 0 else "vertical"

    @prim_dir.setter
    def prim_dir(self, prim_dir):

        self.prim_dim = 0 if prim_dir == "horizontal" else 1
        self.set_min_size_stale()

    @property
    def gaps(self):

        return tuple(self._gaps)

    @gaps.setter
    def gaps(self, gaps):

        self._gaps = [gaps[0], gaps[1]]

    @property
    def owner(self):

        return self._owner

    @owner.setter
    def owner(self, owner):

        self._owner = owner

        if owner and owner.type == "widget":
            l, r, b, t = owner.sizer_borders
            w, h = owner.gfx_size
            self._pos = (l, t)
            self.default_size = (w - l - r, h - b - t)

    @property
    def owner_widget(self):

        owner = self._owner

        if not owner:
            return

        if owner.type == "widget":
            return owner

        return owner.owner_widget

    def add(self, obj, proportions=None, alignments=None, borders=None, index=None):

        obj_type = "size" if type(obj) == tuple else obj.type
        cell = SizerCell(self, obj, obj_type, proportions, alignments, borders)

        if index is None:
            self._cells.append(cell)
        else:
            self._cells.insert(index, cell)

        self.set_min_size_stale()

        if obj_type == "sizer":
            obj.owner = self

        if obj_type != "size":
            obj.sizer_cell = cell

        return cell

    def add_cell(self, cell, index=None):

        cell.sizer = self

        if index is None:
            self._cells.append(cell)
        else:
            self._cells.insert(index, cell)

        self.set_min_size_stale()

    def remove_cell(self, cell, destroy=False):

        self._cells.remove(cell)
        cell.sizer = None

        if destroy:
            cell.destroy()

        self.set_min_size_stale()

        return cell

    def pop_cell(self, index=None):

        cell = self._cells[-1 if index is None else index]
        self._cells.remove(cell)
        cell.sizer = None
        self.set_min_size_stale()

        return cell

    @property
    def cells(self):

        return self._cells

    def get_widgets(self, include_children=True):

        widgets = []

        for cell in self._cells:

            if cell.type == "widget":

                widget = cell.object
                widgets.append(widget)

                if include_children:

                    sizer = widget.sizer

                    if sizer:
                        widgets.extend(sizer.get_widgets())

            elif cell.type == "sizer":

                widgets.extend(cell.object.get_widgets(include_children))

        return widgets

    @property
    def default_size(self):

        return self._default_size

    @default_size.setter
    def default_size(self, size):

        self.set_default_size(size)

    def set_default_size(self, size, set_min_size_stale=True):

        w_d, h_d = self._default_size = size
        w_min, h_min = self._min_size
        self._min_size = w_min, h_min = (max(w_d, w_min), max(h_d, h_min))
        w, h = self._size
        self._size = (max(w_min, w), max(h_min, h))

        if self.sizer_cell:
            self.sizer_cell.update_min_size()

        if set_min_size_stale:
            self.set_min_size_stale()

    def set_min_size_stale(self, stale=True):

        if self._is_min_size_stale == stale:
            return

        self._is_min_size_stale = stale

        if stale and self._owner:

            if self._owner.type == "sizer":

                self._owner.set_min_size_stale()

            elif self._owner.type == "widget":

                cell = self._owner.sizer_cell

                if cell:

                    cell_sizer = cell.sizer

                    if cell_sizer:
                        cell_sizer.set_min_size_stale()

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

    def __get_col_row_min_sizes(self):

        prim_dim = self.prim_dim
        prim_limit = len(self._cells) if self.prim_limit == 0 else self.prim_limit
        min_sizes = [None, None]
        min_sizes[prim_dim] = prim_min_sizes = [0] * len(self._cells[:prim_limit])
        min_sizes[1-prim_dim] = sec_min_sizes = []
        cells = self._cells[:]

        while cells:

            sec_min_size = 0

            for i, cell in enumerate(cells[:prim_limit]):
                min_size = cell.min_size
                prim_min_sizes[i] = max(prim_min_sizes[i], min_size[prim_dim])
                sec_min_size = max(sec_min_size, min_size[1-prim_dim])

            sec_min_sizes.append(sec_min_size)
            del cells[:prim_limit]

        return min_sizes

    def update_min_size(self):

        if not self._is_min_size_stale:
            return self._min_size

        for cell in self._cells:

            if cell.type == "widget":

                sizer = cell.object.sizer

                if sizer:
                    sizer.update_min_size()

        for cell in self._cells:
            cell.update_min_size()

        min_sizes = self.__get_col_row_min_sizes()
        min_w = sum(min_sizes[0])
        min_h = sum(min_sizes[1])
        prim_dim = self.prim_dim
        prim_limit = len(self._cells) if self.prim_limit == 0 else self.prim_limit
        w_d, h_d = self._default_size
        min_size = [max(w_d, min_w), max(h_d, min_h)]
        gap_counts = [0, 0]
        gap_counts[prim_dim] = max(0, len(self._cells[:prim_limit]) - 1)
        gap_counts[1-prim_dim] = max(0, (len(self._cells) - 1) // max(1, prim_limit))
        min_size[prim_dim] += self._gaps[prim_dim] * gap_counts[prim_dim]
        min_size[1-prim_dim] += self._gaps[1-prim_dim] * gap_counts[1-prim_dim]
        self._min_size = width, height = tuple(min_size)
        self._is_min_size_stale = False
        w, h = self._size
        self._size = (max(width, w), max(height, h))

        return self._min_size

    @staticmethod
    def get_global_default_proportions():

        return Sizer._global_default_proportions

    @staticmethod
    def set_global_default_proportions(column_proportion=0., row_proportion=0.):
        """
        Set the proportions to be applied to *any* sizer's columns and rows when
        there is no explicitly set proportion and no proportions associated
        with any cells for those columns and/or rows.

        """

        Sizer._global_default_proportions = (max(0., column_proportion),
                                             max(0., row_proportion))

    def get_default_proportions(self):

        return self._default_proportions

    def set_default_proportions(self, column_proportion=-1., row_proportion=-1.):
        """
        Set the proportions to be applied to *this* sizer's columns and rows
        when there is no explicitly set proportion and no proportions associated
        with any cells for those columns and/or rows.

        """

        self._default_proportions = (column_proportion, row_proportion)

    def __get_cell_proportions(self):
        """
        Return the largest horizontal and vertical proportions associated with
        the cells in this sizer.

        Each time an object was added to this sizer, proportions were associated
        with the object's cell. The largest of the horizontal proportions will
        be considered for the cell's column, while the largest of the vertical
        proportions will be considered for the cell's row.
        They will be applied only in the absence of an explicitly set proportion.

        """

        prim_dim = self.prim_dim
        prim_limit = len(self._cells) if self.prim_limit == 0 else self.prim_limit
        proportions = [None, None]
        proportions[prim_dim] = prim_proportions = [-1.] * len(self._cells[:prim_limit])
        proportions[1-prim_dim] = sec_proportions = []
        cells = self._cells[:]

        while cells:

            sec_proportion = -1.

            for i, cell in enumerate(cells[:prim_limit]):
                min_size = cell.update_min_size()
                prim_proportions[i] = max(prim_proportions[i], cell.proportions[prim_dim])
                sec_proportion = max(sec_proportion, cell.proportions[1-prim_dim])

            sec_proportions.append(sec_proportion)
            del cells[:prim_limit]

        default_proportions = [p1 if p2 < 0. else p2 for p1, p2 in
            zip(self._global_default_proportions, self._default_proportions)]
        default_prim_p = default_proportions[prim_dim]
        default_sec_p = default_proportions[1-prim_dim]
        prim_proportions[:] = [default_prim_p if p < 0. else p for p in prim_proportions]
        sec_proportions[:] = [default_sec_p if p < 0. else p for p in sec_proportions]

        return proportions

    def has_row_proportion(self, index):
        """
        Check whether a vertical proportion has been explicitly set for the
        row with the given index.

        """

        return index in self._proportions[1]

    def get_row_proportion(self, index):
        """
        Return the vertical proportion that has been explicitly set for the
        row with the given index.
        It is an error to call this if has_row_proportion(index) returns False.

        """

        assert self.has_row_proportion(index)
        return self._proportions[1][index]

    def set_row_proportion(self, index, proportion):
        """
        Explicitly set a vertical proportion for the row with the given
        index. It will override the vertical proportions associated with
        any cell added to that row.

        """

        if not (self.has_row_proportion(index)
                and proportion == self.get_row_proportion(index)):
            self._proportions[1][index] = proportion

    def clear_row_proportion(self, index):
        """
        Remove the vertical proportion that has been explicitly set for the
        row with the given index. This undoes the effect of a previous call
        to set_row_proportion for that row; its new vertical proportion
        will be the largest one of those associated with its cells.

        """

        if index in self._proportions[1]:
            del self._proportions[1][index]

    def clear_row_proportions(self):
        """
        Remove the vertical proportions that were explicitly set for any of
        the rows of this sizer.
        See clear_row_proportion.

        """

        self._proportions[1].clear()

    def has_column_proportion(self, index):
        """
        Check whether a horizontal proportion has been explicitly set for the
        column with the given index.

        """

        return index in self._proportions[0]

    def get_column_proportion(self, index):
        """
        Return the horizontal proportion that has been explicitly set for the
        column with the given index.
        It is an error to call this if has_column_proportion(index) returns False.

        """

        assert self.has_column_proportion(index)
        return self._proportions[0][index]

    def set_column_proportion(self, index, proportion):
        """
        Explicitly set a horizontal proportion for the column with the given
        index. It will override the horizontal proportions associated with
        any cell added to that column.

        """

        if not (self.has_column_proportion(index)
                and proportion == self.get_column_proportion(index)):
            self._proportions[0][index] = proportion

    def clear_column_proportion(self, index):
        """
        Remove the horizontal proportion that has been explicitly set for the
        column with the given index. This undoes the effect of a previous call
        to set_column_proportion for that column; its new horizontal proportion
        will be the largest one of those associated with its cells.

        """

        if index in self._proportions[0]:
            del self._proportions[0][index]

    def clear_column_proportions(self):
        """
        Remove the horizontal proportions that were explicitly set for any of
        the columns of this sizer.
        See clear_column_proportion.

        """

        self._proportions[0].clear()

    def clear_proportions(self):
        """
        Remove the proportions that were explicitly set for any of the rows
        and columns of this sizer.
        See clear_row_proportion and clear_column_proportion.

        """

        self._proportions = [{}, {}]

    def __apply_proportions(self, proportions, min_sizes, sizes, total_size, indices=None):

        indices_to_check = list(range(len(sizes))) if indices is None else indices
        p_sum = sum(p for i, p in enumerate(proportions) if i in indices_to_check)
        tmp_size = total_size

        for i in indices_to_check:

            proportion = proportions[i]
            min_size = min_sizes[i]

            if p_sum == 0.:
                p_sum = 1.

            new_size = int(round(tmp_size * min(1., proportion / p_sum)))

            if new_size < min_size:
                total_size -= min_size
                sizes[i] = min_size
                indices_to_check.remove(i)
                self.__apply_proportions(proportions, min_sizes, sizes, total_size, indices_to_check)
                break

            sizes[i] = new_size
            tmp_size -= new_size
            p_sum -= proportion

    def get_size(self):

        return self._size

    def set_size(self, size, force=False):

        if force:
            self._size = size
            return

        width, height = size
        w_min, h_min = self.min_size
        self._size = (max(w_min, width), max(h_min, height))

        if not self._cells or self.cell_size_locked:
            return

        prim_dim = self.prim_dim
        prim_limit = len(self._cells) if self.prim_limit == 0 else self.prim_limit
        size = list(self._size)

        counts = [0, 0]
        counts[prim_dim] = len(self._cells[:prim_limit])
        counts[1-prim_dim] = (len(self._cells) - 1) // prim_limit + 1
        size[prim_dim] -= self._gaps[prim_dim] * max(0, counts[prim_dim] - 1)
        size[1-prim_dim] -= self._gaps[1-prim_dim] * max(0, counts[1-prim_dim] - 1)
        dim_sizes = [None, None]
        dim_sizes[prim_dim] = prim_sizes = [0] * counts[prim_dim]
        dim_sizes[1-prim_dim] = sec_sizes = [0] * counts[1-prim_dim]
        min_sizes_by_dim = self.__get_col_row_min_sizes()
        proportions_by_dim = self.__get_cell_proportions()

        for dim, sizes in ((prim_dim, prim_sizes), (1-prim_dim, sec_sizes)):
            min_sizes = min_sizes_by_dim[dim]
            cell_proportions = proportions_by_dim[dim]
            proportions = [self._proportions[dim].get(i, cell_proportions[i])
                for i in range(counts[dim])]
            self.__apply_proportions(proportions, min_sizes, sizes, size[dim])

        cells = self._cells[:]
        sec_index = 0
        cell_size = [0, 0]

        while cells:

            cell_size[1-prim_dim] = sec_sizes[sec_index]

            for cell, prim_size in zip(cells[:prim_limit], prim_sizes):
                cell_size[prim_dim] = prim_size
                cell.set_size(tuple(cell_size))

            sec_index += 1
            del cells[:prim_limit]

    def get_pos(self, net=False):

        x, y = self._pos

        if net:

            owner = self._owner

            while owner:

                if owner.type == "widget":
                    x_o, y_o = owner.get_pos(net=True)
                    x += x_o
                    y += y_o
                    break

                owner = owner.owner

        return (x, y)

    def set_pos(self, pos):

        self._pos = pos

    def update_positions(self, start_pos=None):

        if self.cell_size_locked:
            return

        prim_dim = self.prim_dim
        prim_limit = len(self._cells) if self.prim_limit == 0 else self.prim_limit
        start_pos = list(start_pos) if start_pos else list(self._pos)
        start_coord = start_pos[prim_dim]

        cells = self._cells[:]
        gaps = self._gaps

        while cells:

            start_pos[prim_dim] = start_coord

            for cell in cells[:prim_limit]:

                obj = cell.object
                size = cell.get_size()
                offset_x, offset_y = cell.object_offset
                pos = (start_pos[0] + offset_x, start_pos[1] + offset_y)

                if cell.type == "widget":

                    obj.set_pos(pos)
                    sizer = obj.sizer

                    if sizer:
                        sizer.update_positions()

                elif cell.type == "sizer":

                    obj.set_pos(pos)
                    obj.update_positions()

                start_pos[prim_dim] += size[prim_dim] + gaps[prim_dim]

            start_pos[1-prim_dim] += size[1-prim_dim] + gaps[1-prim_dim]

            del cells[:prim_limit]

    def update(self, size=None):

        w, h = size if size else (0, 0)
        w_min, h_min = self.update_min_size()
        new_size = (max(w, w_min), max(h, h_min))
        self.set_size(new_size)
        self.update_positions()

    def update_images(self):

        if self.cell_size_locked:
            return

        for cell in self._cells:
            if cell.type != "size":
                cell.object.update_images()

    def get_composed_image(self, image):

        for cell in self._cells:

            if cell.type == "widget":

                widget = cell.object
                img = widget.get_image()

                if img:
                    w, h = img.size
                    x, y = widget.get_pos()
                    offset_x, offset_y = widget.image_offset
                    x += offset_x
                    y += offset_y
                    image.blend_sub_image(img, x, y, 0, 0, w, h)

            elif cell.type == "sizer":

                sizer = cell.object
                sizer.get_composed_image(image)

        return image

    def update_mouse_region_frames(self, exclude=""):

        if self.mouse_regions_locked:
            return

        for cell in self._cells:
            if cell.type != "size":
                cell.object.update_mouse_region_frames(exclude)
