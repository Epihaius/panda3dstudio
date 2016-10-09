from .mgr import CoreManager as Mgr
from .base import PendingTasks


# All managers of pickable objects should derive from the following class
class PickingColorIDManager(object):

    _mgrs = {}

    @classmethod
    def init(cls):

        sort = PendingTasks.get_sort("register_subobjs", "object")
        PendingTasks.add_task_id("update_picking_col_id_ranges", "object", sort + 1)
        Mgr.accept("update_picking_col_id_ranges", cls.__update_id_ranges)

    @classmethod
    def __update_id_ranges(cls):

        def task():

            for mgr in cls._mgrs.itervalues():
                mgr.update_picking_color_id_ranges()

        task_id = "update_picking_col_id_ranges"
        PendingTasks.add(task, task_id, "object")

    def __init__(self):

        self._mgrs[self.get_managed_object_type()] = self

        self._id_ranges = [(1, 2 ** 24)]
        self._ids_to_recover = set()
        self._ids_to_discard = set()

    def __get_ranges(self, lst):

        l = iter([None] + lst[:-1])
        m = iter(lst[1:] + [None])

        return zip(filter(lambda i: i - 1 != next(l), lst),
                   map(lambda i: i + 1, filter(lambda i: i + 1 != next(m), lst)))

    def __merge_ranges(self, range_list, next_range):

        if range_list:

            prev_range_start, prev_range_end = range_list[-1]
            next_range_start, next_range_end = next_range

            if prev_range_end == next_range_start:
                del range_list[-1]
                range_list.append((prev_range_start, next_range_end))
                return range_list

        return range_list + [next_range]

    def __split_ranges(self, range_list, next_range):

        if range_list:

            prev_range_start, prev_range_end = range_list[-1]
            next_range_start, next_range_end = next_range

            if next_range_start < prev_range_end:

                del range_list[-1]

                if prev_range_start != next_range_start:
                    range_list.append((prev_range_start, next_range_start))

                if prev_range_end != next_range_end:
                    min_range_end = min(prev_range_end, next_range_end)
                    max_range_end = max(prev_range_end, next_range_end)
                    range_list.append((min_range_end, max_range_end))

                return range_list

        return range_list + [next_range]

    def get_next_picking_color_id(self):

        if not self._id_ranges:
            # TODO: pop up a message notifying the user that no more objects
            # can be created
            return

        next_id, range_end = self._id_ranges.pop(0)

        if next_id + 1 < range_end:
            self._id_ranges.insert(0, (next_id + 1, range_end))

        return next_id

    def recover_picking_color_id(self, color_id):
        """ Recover the given color ID, so it can be used again """

        self._ids_to_recover.add(color_id)

    def recover_picking_color_ids(self, color_ids):
        """ Recover the given color IDs, so they can be used again. """

        self._ids_to_recover.update(color_ids)

    def discard_picking_color_id(self, color_id):
        """ Discard the given color ID, so it can no longer be used """

        self._ids_to_discard.add(color_id)

    def discard_picking_color_ids(self, color_ids):
        """ Discard the given color IDs, so they can no longer be used. """

        self._ids_to_discard.update(color_ids)

    def update_picking_color_id_ranges(self):

        id_ranges = self._id_ranges
        set_to_recover = self._ids_to_recover
        set_to_discard = self._ids_to_discard

        if not (set_to_recover or set_to_discard):
            return

        # remove the common IDs from both sets
        if not set_to_recover.isdisjoint(set_to_discard):
            set_to_recover ^= set_to_discard
            set_to_discard &= set_to_recover
            set_to_recover -= set_to_discard

        if set_to_recover:
            ids_to_recover = sorted(set_to_recover)
            id_ranges += self.__get_ranges(ids_to_recover)
            id_ranges.sort()
            id_ranges[:] = reduce(self.__merge_ranges, id_ranges[:], [])

        if set_to_discard:
            ids_to_discard = sorted(set_to_discard)
            id_ranges += self.__get_ranges(ids_to_discard)
            id_ranges.sort()
            id_ranges[:] = reduce(self.__split_ranges, id_ranges[:], [])

        self._ids_to_recover = set()
        self._ids_to_discard = set()
