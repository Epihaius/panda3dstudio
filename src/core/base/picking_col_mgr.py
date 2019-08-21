from .mgr import CoreManager as Mgr
from .base import Notifiers, PendingTasks
from functools import reduce


# All managers of pickable objects should derive from the following class
class PickingColorIDManager:

    _mgrs = {}
    _id_range_backups_created = False

    @classmethod
    def init(cls):

        Mgr.accept("reset_picking_col_id_ranges", cls.__reset_id_ranges)
        Mgr.accept("update_picking_col_id_ranges", cls.__update_id_ranges)
        Mgr.accept("create_id_range_backups", cls.__create_id_range_backups)
        Mgr.add_notification_handler("long_process_cancelled", "picking_col_mgr",
                                     cls.__restore_id_range_backups)

    @classmethod
    def __reset_id_ranges(cls):

        for mgr in cls._mgrs.values():
            mgr.reset()

    @classmethod
    def __update_id_ranges(cls):

        def task():

            for mgr in cls._mgrs.values():
                mgr.update_picking_color_id_ranges()

        task_id = "update_picking_col_id_ranges"
        PendingTasks.add(task, task_id, "object")

    @classmethod
    def __create_id_range_backups(cls):

        if cls._id_range_backups_created:
            return

        for mgr in cls._mgrs.values():
            mgr.create_id_ranges_backup()

        task = cls.__remove_id_range_backups
        task_id = "remove_id_range_backups"
        PendingTasks.add(task, task_id, "object", sort=100)
        cls._id_range_backups_created = True

    @classmethod
    def __restore_id_range_backups(cls, info=""):

        if not cls._id_range_backups_created:
            return

        Notifiers.reg.info(f'Restoring ID ranges;\ninfo: {info}')

        for mgr in cls._mgrs.values():
            mgr.restore_id_ranges_backup()

        cls.__remove_id_range_backups()

    @classmethod
    def __remove_id_range_backups(cls):

        if not cls._id_range_backups_created:
            return

        for mgr in cls._mgrs.values():
            mgr.remove_id_ranges_backup()

        cls._id_range_backups_created = False

    def __init__(self):

        self._mgrs[self.get_managed_object_type()] = self

        self._id_ranges = [(1, 2 ** 24)]
        self._ids_to_recover = set()
        self._ids_to_discard = set()
        self._id_ranges_backup = None

    def reset(self):

        self._id_ranges = [(1, 2 ** 24)]
        self._ids_to_recover = set()
        self._ids_to_discard = set()
        self._id_ranges_backup = None
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color IDs reset.')

    def __get_ranges(self, lst):

        l = iter([None] + lst[:-1])
        m = iter(lst[1:] + [None])

        return list(zip([i for i in lst if i - 1 != next(l)],
                   [i + 1 for i in [i for i in lst if i + 1 != next(m)]]))

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
        Notifiers.reg.debug(f'****** {self.get_managed_object_type()} picking color IDs '
                            f'recovered:\n{self.__get_ranges(sorted(self._ids_to_recover))}')

    def discard_picking_color_id(self, color_id):
        """ Discard the given color ID, so it can no longer be used """

        self._ids_to_discard.add(color_id)

    def discard_picking_color_ids(self, color_ids):
        """ Discard the given color IDs, so they can no longer be used. """

        self._ids_to_discard.update(color_ids)
        Notifiers.reg.debug(f'****** {self.get_managed_object_type()} picking color IDs '
                            f'discarded:\n{self.__get_ranges(sorted(self._ids_to_discard))}')

    def update_picking_color_id_ranges(self):

        id_ranges = self._id_ranges
        set_to_recover = self._ids_to_recover
        set_to_discard = self._ids_to_discard

        if not (set_to_recover or set_to_discard):
            return

        Notifiers.reg.debug(f'++++++ Updating {self.get_managed_object_type()} '
                            f'picking color IDs ranges, starting with:\n{id_ranges}')

        # remove the common IDs from both sets
        if not set_to_recover.isdisjoint(set_to_discard):
            set_to_recover ^= set_to_discard
            set_to_discard &= set_to_recover
            set_to_recover -= set_to_discard

        if set_to_recover:
            id_ranges_to_recover = self.__get_ranges(sorted(set_to_recover))
            Notifiers.reg.debug(f'++++++ Recovering {self.get_managed_object_type()} '
                                f'picking color IDs:\n{id_ranges_to_recover}')
            id_ranges += id_ranges_to_recover
            id_ranges.sort()
            id_ranges[:] = reduce(self.__merge_ranges, id_ranges[:], [])

        if set_to_discard:
            id_ranges_to_discard = self.__get_ranges(sorted(set_to_discard))
            Notifiers.reg.debug(f'++++++ Discarding {self.get_managed_object_type()} '
                                f'picking color IDs:\n{id_ranges_to_discard}')
            id_ranges += id_ranges_to_discard
            id_ranges.sort()
            id_ranges[:] = reduce(self.__split_ranges, id_ranges[:], [])

        self._ids_to_recover = set()
        self._ids_to_discard = set()
        Notifiers.reg.debug(f'++++++ New {self.get_managed_object_type()} '
                            f'picking color ID ranges:\n{id_ranges}')

        # check integrity
        for rng1, rng2 in zip(id_ranges[:-1], id_ranges[1:]):
            if rng1[1] >= rng2[0]:
                # something went wrong; create scene and log files to submit for debugging
                Notifiers.reg.info('(error): An error occurred with '
                                   f'{self.get_managed_object_type()} '
                                   f'object ID management:\n{id_ranges}')
                import shutil
                shutil.copy("p3ds.log", "corrupt_object_ids.log")
                Mgr.update_locally("scene", "save", "corrupt_object_ids.p3ds", set_saved_state=False)
                msg = "An error occurred with object ID management;\n" \
                      "files 'corrupt_object_ids.p3ds' and 'corrupt_object_ids.log' have\n" \
                      "been created to submit for debugging."
                raise AssertionError(msg)

    def create_id_ranges_backup(self):

        self._id_ranges_backup = self._id_ranges[:]
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color IDs '
                            f'backup created:\n{self._id_ranges_backup}')

    def restore_id_ranges_backup(self):

        self._id_ranges = self._id_ranges_backup
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color '
                            f'IDs backup restored:\n{self._id_ranges}')

    def remove_id_ranges_backup(self):

        self._id_ranges_backup = None
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color IDs backup removed.')
