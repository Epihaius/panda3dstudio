from panda3d.core import SparseArray
from .mgr import CoreManager as Mgr
from .base import Notifiers, PendingTasks


# All managers of pickable objects should derive from the following class
class PickingColorIDManager:

    _mgrs = {}
    _id_range_backups_created = set()

    @classmethod
    def init(cls):

        Mgr.accept("reset_picking_col_id_ranges", cls.__reset_id_ranges)
        Mgr.accept("update_picking_col_id_ranges", cls.__update_id_ranges)
        Mgr.accept("create_id_range_backups", cls.__create_id_range_backups)
        Mgr.accept("restore_id_range_backups", cls.__restore_id_range_backups)
        Mgr.add_notification_handler("long_process_cancelled", "picking_col_mgr",
                                     cls.__restore_id_range_backups)

    @classmethod
    def __reset_id_ranges(cls, obj_types=None):

        types = cls._mgrs if obj_types is None else obj_types

        for obj_type in types:
            cls._mgrs[obj_type].reset()

    @classmethod
    def __update_id_ranges(cls, as_task=True):

        def task():

            for mgr in cls._mgrs.values():
                mgr.update_picking_color_id_ranges()

        if as_task:
            task_id = "update_picking_col_id_ranges"
            PendingTasks.add(task, task_id, "object")
        else:
            task()

    @classmethod
    def __create_id_range_backups(cls, obj_types=None):

        types = set(cls._mgrs) if obj_types is None else set(obj_types)
        types -= cls._id_range_backups_created

        if not types:
            return

        for obj_type in types:
            cls._mgrs[obj_type].create_id_ranges_backup()

        task = cls.__remove_id_range_backups
        task_id = "remove_id_range_backups"
        PendingTasks.add(task, task_id, "object", sort=100)
        cls._id_range_backups_created.update(types)

    @classmethod
    def __restore_id_range_backups(cls, info=""):

        if not cls._id_range_backups_created:
            return

        Notifiers.reg.info(f'Restoring ID ranges;\ninfo: {info}')

        for obj_type in cls._id_range_backups_created:
            cls._mgrs[obj_type].restore_id_ranges_backup()

        cls.__remove_id_range_backups()

    @classmethod
    def __remove_id_range_backups(cls):

        if not cls._id_range_backups_created:
            return

        for obj_type in cls._id_range_backups_created:
            cls._mgrs[obj_type].remove_id_ranges_backup()

        cls._id_range_backups_created.clear()

    def __init__(self):

        self._mgrs[self.get_managed_object_type()] = self

        self._id_ranges = SparseArray.range(1, 2 ** 24)
        self._ids_to_recover = SparseArray()
        self._ids_to_discard = SparseArray()
        self._id_ranges_backup = None

    def reset(self):

        self._id_ranges = SparseArray.range(1, 2 ** 24)
        self._ids_to_recover = SparseArray()
        self._ids_to_discard = SparseArray()
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color IDs reset.')

    def get_next_picking_color_id(self):

        if not self._id_ranges:
            # TODO: pop up a message notifying the user that no more objects
            # can be created
            return

        next_id = self._id_ranges.get_lowest_on_bit()
        self._id_ranges.clear_bit(next_id)

        return next_id

    def recover_picking_color_id(self, color_id):
        """ Recover the given color ID, so it can be used again """

        if self._ids_to_recover.get_bit(color_id):
            Notifiers.reg.warning(f'!!!!!! {self.get_managed_object_type()} picking color ID '
                                  f'already recovered!')

        self._ids_to_recover.set_bit(color_id)

    def recover_picking_color_ids(self, color_ids):
        """ Recover the given color IDs, so they can be used again. """

        s = SparseArray()
        [s.set_bit(i) for i in color_ids]

        if self._ids_to_recover & s:
            Notifiers.reg.warning(f'!!!!!! {self.get_managed_object_type()} picking color IDs '
                                  f'already recovered!')

        self._ids_to_recover |= s
        Notifiers.reg.debug(f'****** {self.get_managed_object_type()} picking color IDs '
                            f'to be recovered:\n{self._ids_to_recover}')

    def discard_picking_color_id(self, color_id):
        """ Discard the given color ID, so it can no longer be used """

        if self._ids_to_discard.get_bit(color_id):
            Notifiers.reg.warning(f'!!!!!! {self.get_managed_object_type()} picking color ID '
                                  f'already discarded!')

        self._ids_to_discard.set_bit(color_id)

    def discard_picking_color_ids(self, color_ids):
        """ Discard the given color IDs, so they can no longer be used. """

        s = SparseArray()
        [s.set_bit(i) for i in color_ids]

        if self._ids_to_discard & s:
            Notifiers.reg.warning(f'!!!!!! {self.get_managed_object_type()} picking color IDs '
                                  f'already discarded!')

        self._ids_to_discard |= s
        Notifiers.reg.debug(f'****** {self.get_managed_object_type()} picking color IDs '
                            f'to be discarded:\n{self._ids_to_discard}')

    def update_picking_color_id_ranges(self):

        id_ranges = self._id_ranges
        ids_to_recover = self._ids_to_recover
        ids_to_discard = self._ids_to_discard

        if not (ids_to_recover or ids_to_discard):
            return

        Notifiers.reg.debug(f'++++++ Updating {self.get_managed_object_type()} '
                            f'picking color IDs ranges, starting with:\n{id_ranges}')

        # remove the common IDs from both arrays
        if ids_to_recover.has_bits_in_common(ids_to_discard):
            ids_to_recover ^= ids_to_discard
            ids_to_discard &= ids_to_recover
            ids_to_recover &= ~ids_to_discard

        if ids_to_recover:
            Notifiers.reg.debug(f'++++++ Recovering {self.get_managed_object_type()} '
                                f'picking color IDs:\n{ids_to_recover}')
            id_ranges |= ids_to_recover

        if ids_to_discard:
            Notifiers.reg.debug(f'++++++ Discarding {self.get_managed_object_type()} '
                                f'picking color IDs:\n{ids_to_discard}')
            id_ranges &= ~ids_to_discard

        ids_to_recover.clear()
        ids_to_discard.clear()
        Notifiers.reg.debug(f'++++++ New {self.get_managed_object_type()} '
                            f'picking color ID ranges:\n{id_ranges}')

    def create_id_ranges_backup(self):

        self._id_ranges_backup = SparseArray(self._id_ranges)
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color IDs '
                            f'backup created:\n{self._id_ranges_backup}')

    def restore_id_ranges_backup(self):

        self._id_ranges = self._id_ranges_backup
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color '
                            f'IDs backup restored:\n{self._id_ranges}')

    def remove_id_ranges_backup(self):

        self._id_ranges_backup = None
        Notifiers.reg.debug(f'"{self.get_managed_object_type()}" picking color IDs backup removed.')
