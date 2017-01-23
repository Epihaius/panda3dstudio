from __future__ import with_statement
from .base import *

COMPRESSION = 9


class TimeIDRef(object):

    def __init__(self, time_id):

        self._time_id = time_id

    def set_time_id(self, time_id):

        self._time_id = time_id

    def get_time_id(self):

        return self._time_id


class HistoryEvent(object):

    _edited_events = set()

    @classmethod
    def update_user_data(cls):

        for event in cls._edited_events:
            event.update_user_description()
            event.update_milestone()

    @classmethod
    def reset_temp_user_data(cls):

        for event in cls._edited_events:
            event.reset_temp_user_description()
            event.reset_temp_milestone()

        cls._edited_events = set()

    def __init__(self, time_id, data, prev_time_id=None, description=""):

        self._time_id = time_id
        self._data = data  # dict
        self._prev = prev_time_id  # HistoryEvent time ID
        self._next = []  # list of HistoryEvent time IDs
        self._descr = description
        self._user_descr = ""
        self._is_milestone = False
        self._milestone_count = 0
        self._user_descr_tmp = None
        self._is_milestone_tmp = None
        self._to_be_merged = False

        previous_event = Mgr.get("history_event", prev_time_id)

        if previous_event:

            previous_event.add_next_event(time_id)

            if data["object_ids"] is None:
                self._data["object_ids"] = previous_event.get_last_object_ids()

    def get_time_id(self):

        return self._time_id

    def get_timestamp(self):

        sec, index = self._time_id
        timestamp = time.ctime(sec) + ((" (%s)" % (index + 1)) if index else "")

        return timestamp

    def set_previous_event(self, prev_time_id):

        self._prev = prev_time_id

    def get_previous_event(self):

        return Mgr.get("history_event", self._prev)

    def add_next_event(self, time_id):

        if time_id not in self._next:
            self._next.append(time_id)

    def remove_next_event(self, time_id, update_milestone_count=False):

        if time_id in self._next:
            self._next.remove(time_id)

        if update_milestone_count:
            self.update_milestone_count()

    def replace_next_event(self, time_id_old, time_id_new):

        if time_id_old in self._next:
            index = self._next.index(time_id_old)
            self._next.remove(time_id_old)
            self._next.insert(index, time_id_new)

    def clear_next_events(self):

        self._next = []
        self._milestone_count = 1 if self.is_milestone() else 0

    def get_next_event(self):

        time_id = self._next[-1] if self._next else None

        return Mgr.get("history_event", time_id)

    def get_next_events(self):

        return [evt for evt in (Mgr.get("history_event", time_id) for time_id in self._next) if evt]

    def set_description(self, description):

        self._descr = description

    def get_description(self):

        return self._descr

    def set_user_description(self, description):

        self._user_descr_tmp = description
        self._edited_events.add(self)

    def get_user_description(self):

        return self._user_descr if self._user_descr_tmp is None else self._user_descr_tmp

    def get_full_description(self):

        user_descr = self.get_user_description()

        if user_descr:
            return user_descr + "\n\n" + self._descr
        else:
            return self._descr

    def get_description_line_count(self):

        return self.get_full_description().count("\n") + 1

    def get_description_start(self):

        return self.get_full_description().split("\n", 1)[0]

    def set_as_milestone(self, is_milestone=True):

        self._is_milestone_tmp = is_milestone
        self._edited_events.add(self)

    def is_milestone(self):

        return self._is_milestone if self._is_milestone_tmp is None else self._is_milestone_tmp

    def update_user_description(self):

        if self._user_descr_tmp is not None:
            self._user_descr = self._user_descr_tmp

    def update_milestone(self):

        if self._is_milestone_tmp is not self._is_milestone:
            self._is_milestone = self._is_milestone_tmp
            self.modify_milestone_count(self._is_milestone)

    def update_milestone_count(self, process_previous=True):

        self._milestone_count = 1 if self.is_milestone() else 0

        for event in self.get_next_events():
            self._milestone_count += event.get_milestone_count()

        if process_previous:

            event = self.get_previous_event()

            while event:
                event.update_milestone_count(process_previous=False)
                event = event.get_previous_event()

    def modify_milestone_count(self, increment=True, process_previous=True):

        self._milestone_count += 1 if increment else -1

        if process_previous:

            event = self.get_previous_event()

            while event:
                event.modify_milestone_count(increment, process_previous=False)
                event = event.get_previous_event()

    def get_milestone_count(self):
        """ Return the number of *future* milestone events """

        return self._milestone_count

    def reset_temp_user_description(self):

        self._user_descr_tmp = None

    def reset_temp_milestone(self):

        self._is_milestone_tmp = None

    def get_data(self):

        return self._data

    def get_object_data(self):

        return self._data["objects"]

    def update_object_data(self, obj_data):

        data = obj_data.copy()

        for obj_id, prop_ids in self._data["objects"].iteritems():
            if obj_id in data:
                prop_ids.update(data[obj_id])
                del data[obj_id]

        self._data["objects"].update(data)

    def remove_object_props(self, obj_id, process_previous=True):

        if obj_id in self._data["objects"]:
            del self._data["objects"][obj_id]

        if process_previous:

            event = self.get_previous_event()

            while event:
                event.remove_object_props(obj_id, process_previous=False)
                event = event.get_previous_event()

    def get_changed_object_props(self, obj_id):

        return self._data["objects"].get(obj_id, set())

    def get_last_object_prop_change(self, obj_id, prop_id, process_previous=True):

        data = self._data["objects"]

        if obj_id in data and prop_id in data[obj_id]:
            return self._time_id

        if process_previous:

            event = self.get_previous_event()

            while event:

                time_id = event.get_last_object_prop_change(obj_id, prop_id,
                                                            process_previous=False)

                if time_id:
                    return time_id

                event = event.get_previous_event()

    def get_last_object_ids(self):

        return self._data["object_ids"]

    def set_last_object_ids(self, time_id_ref):

        self._data["object_ids"] = time_id_ref

    def set_to_be_merged(self, to_be_merged=True):

        self._to_be_merged = to_be_merged

    def is_to_be_merged(self):

        return self._to_be_merged


class HistoryManager(BaseObject):

    def __init__(self):

        self._event_descr_to_store = ""
        self._event_data_to_store = {"objects": {}}
        self._update_time_id = True
        self._hist_events = {}
        self._prev_time_id = self._next_time_id = self._saved_time_id = (0, 0)
        self._backup_file_index = 1

        self._clocks = {"automerge": ClockObject(), "autobackup": ClockObject()}

        GlobalData.set_default("history_to_undo", False)
        GlobalData.set_default("history_to_redo", False)
        automerge_defaults = {"max_event_count": 50, "interval": 120.}
        autobackup_defaults = {"max_file_count": 5, "interval": 300.}
        copier = dict.copy
        GlobalData.set_default("automerge_defaults", automerge_defaults, copier)
        GlobalData.set_default("autobackup_defaults", autobackup_defaults, copier)

        Mgr.expose("history_event", lambda time_id: self._hist_events.get(time_id))
        Mgr.accept("reset_history", self.__reset_history)
        Mgr.accept("load_from_history", self.__load_from_history)
        Mgr.accept("load_last_from_history", self.__load_last_value)
        Mgr.accept("update_history_time", self.__update_time_id)
        Mgr.accept("get_prev_history_time", self.__get_previous_time_id)
        Mgr.accept("get_history_time", self.__get_next_time_id)
        Mgr.accept("add_history", self.__add_history)
        Mgr.accept("clear_added_history", self.__clear_added_history)
        Mgr.accept("save_history", self.__save_history)
        Mgr.accept("load_history", self.__load_history)

        Mgr.add_app_updater("history", self.__manage_history)
        Mgr.add_task(self.__store_history, "store_history", sort=49)

    def setup(self):

        self.__reset_history()

        return True

    def __manage_history(self, update_type, *args, **kwargs):

        if update_type in ("undo", "redo", "update"):

            Mgr.show_screenshot()

            state_id = Mgr.get_state_id()
            Mgr.update_app("history_change")

            if state_id == "navigation_mode":
                Mgr.enter_state("navigation_mode")

        if update_type == "undo":
            self.__undo_history()
        elif update_type == "redo":
            self.__redo_history()
        elif update_type == "edit":
            self.__edit_history()
        elif update_type == "update":
            self.__update_history(*args, **kwargs)
        elif update_type == "archive":
            self.__archive_history()

    def __reset_history(self):

        event_data = {"objects": {}, "object_ids": TimeIDRef((0, 0))}
        root_event = HistoryEvent((0, 0), event_data)
        self._hist_events = {(0, 0): root_event, "root": root_event}
        self._prev_time_id = self._saved_time_id = (0, 0)

        hist_file = Multifile()
        hist_file.open_write("hist.dat")
        time_id_stream = StringStream(cPickle.dumps(self._prev_time_id, -1))
        hist_file.add_subfile("time_id", time_id_stream, COMPRESSION)
        hist_event_stream = StringStream(cPickle.dumps(self._hist_events, -1))
        hist_file.add_subfile("events", hist_event_stream, COMPRESSION)
        object_ids_stream = StringStream(cPickle.dumps(set(), -1))
        hist_file.add_subfile("%s/object_ids" % (self._prev_time_id,), object_ids_stream, COMPRESSION)

        hist_file.repack()
        hist_file.close()

        GlobalData["history_to_undo"] = False
        GlobalData["history_to_redo"] = False
        Mgr.update_app("history", "check")
        self._clocks["automerge"].reset()
        self._clocks["autobackup"].reset()
        self._backup_file_index = 1

    def __load_from_history(self, obj_id, data_id, time_id=None):

        if not time_id:
            time_id = self._prev_time_id

        hist_file = Multifile()
        hist_file.open_read("hist.dat")

        subfile_name = "%s/%s/%s" % (time_id, obj_id, data_id)
        data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))

        hist_file.close()

        return cPickle.loads(data_pickled)

    def __get_last_time_id(self, obj_id, prop_id, time_id=None):

        if not time_id:
            time_id = self._prev_time_id

        event = self._hist_events[time_id]

        return event.get_last_object_prop_change(obj_id, prop_id)

    def __load_last_value(self, obj_id, prop_id, time_id=None, return_last_time_id=False):

        if not time_id:
            time_id = self._prev_time_id

        if time_id not in self._hist_events:
            return

        event = self._hist_events[time_id]
        last_time_id = event.get_last_object_prop_change(obj_id, prop_id)

        if last_time_id is None:
            return

        hist_file = Multifile()
        hist_file.open_read("hist.dat")

        value = self.__load_property_value(hist_file, last_time_id, obj_id, prop_id)

        hist_file.close()

        if return_last_time_id:
            return value, last_time_id

        return value

    def __update_time_id(self):

        # Keep track of the last time an undoable event occurred, using a tuple
        # containing the time in seconds, followed by an index indicating the
        # number of events that have occurred previously within the same
        # second.

        if not self._update_time_id:
            return self._next_time_id

        cur_time = int(time.time())

        if cur_time == self._next_time_id[0]:
            time_id = (cur_time, self._next_time_id[1] + 1)
##        if cur_time == self._prev_time_id[0]:
##            time_id = (cur_time, self._prev_time_id[1] + 1)
        else:
            time_id = (cur_time, 0)

        self._next_time_id = time_id

        return time_id

    def __get_previous_time_id(self):

        return self._prev_time_id

    def __get_next_time_id(self):

        return self._next_time_id

    def __add_history(self, event_descr, event_data, update_time_id=True):

        logging.debug("Adding history:\n%s", event_descr)

        if self._event_descr_to_store:
            if event_descr:
                self._event_descr_to_store += "\n\n" + event_descr
        else:
            self._event_descr_to_store = event_descr

        evt_data_to_store = self._event_data_to_store
        obj_data = evt_data_to_store["objects"]

        for obj_id, data in event_data["objects"].iteritems():
            obj_data.setdefault(obj_id, {}).update(data)

        if "object_ids" in event_data:
            evt_data_to_store["object_ids"] = event_data["object_ids"]

        if not update_time_id:
            self._update_time_id = False

    def __clear_added_history(self):

        self._event_data_to_store = {"objects": {}}
        self._event_descr_to_store = ""
        self._update_time_id = True
        logging.debug("Cleared previously added history.")

    def __store_history(self, task):

        if GlobalData["long_process_running"]:
            return task.cont

        event_data = self._event_data_to_store

        if not event_data["objects"]:
            return task.cont

        time_id = self.__update_time_id() if self._update_time_id else self._next_time_id
        logging.debug("Storing history:\n%s\n... for time ID %s",
                      self._event_descr_to_store, str(time_id))

        if "object_ids" not in event_data:
            event_data["object_ids"] = None

        obj_data = event_data["objects"]
        obj_ids = event_data["object_ids"]

        objects = dict((obj_id, set([("creation" if (k == "object" and v) else k)
                       for k, v in prop_data.iteritems()])) for obj_id, prop_data
                       in obj_data.iteritems())

        data = {"objects": objects,
                "object_ids": None if obj_ids is None else TimeIDRef(time_id)}
        event = HistoryEvent(time_id, data, self._prev_time_id, self._event_descr_to_store)
        self._hist_events[time_id] = event

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")

        streams = []

        for obj_id in obj_data:

            if "object" in obj_data[obj_id] and obj_data[obj_id]["object"] is None:
                del obj_data[obj_id]["object"]

            for prop_id, prop_val_data in obj_data[obj_id].iteritems():

                subfile_name = "%s/%s/%s" % (time_id, obj_id, prop_id)
                prop_val = prop_val_data["main"]
                streams.append(StringStream(cPickle.dumps(prop_val, -1)))
                hist_file.add_subfile(subfile_name, streams[-1], COMPRESSION)

                if "extra" in prop_val_data:
                    for data_id, data in prop_val_data["extra"].iteritems():
                        subfile_name = "%s/%s/%s" % (time_id, obj_id, data_id)
                        streams.append(StringStream(cPickle.dumps(data, -1)))
                        hist_file.add_subfile(subfile_name, streams[-1], COMPRESSION)

        if obj_ids is not None:
            subfile_name = "%s/object_ids" % (time_id,)
            streams.append(StringStream(cPickle.dumps(obj_ids, -1)))
            hist_file.add_subfile(subfile_name, streams[-1], COMPRESSION)

        hist_file.flush()
        hist_file.close()

        self._event_data_to_store = {"objects": {}}
        self._event_descr_to_store = ""
        self._update_time_id = True
        self._prev_time_id = self._next_time_id = time_id

        GlobalData["history_to_undo"] = True
        GlobalData["history_to_redo"] = False
        Mgr.update_app("history", "check")
        undo_descr = self.__get_undo_description()
        redo_descr = self.__get_redo_description()
        Mgr.update_remotely("history", "set_descriptions", undo_descr, redo_descr)
        self._saved_time_id = (-1, 0)
        GlobalData["unsaved_scene"] = True
        Mgr.update_app("unsaved_scene")

        clock = self._clocks["automerge"]

        if clock.get_real_time() >= GlobalData["automerge_defaults"]["interval"]:
            self.__automerge(event)
            clock.reset()

        clock = self._clocks["autobackup"]
        backup_defaults = GlobalData["autobackup_defaults"]

        if clock.get_real_time() >= backup_defaults["interval"]:
            index = self._backup_file_index
            Mgr.do("make_backup", index)
            index = 1 if index == backup_defaults["max_file_count"] else index + 1
            self._backup_file_index = index
            clock.reset()

        return task.cont

    def __automerge(self, last_event):

        last_milestone_count = -1
        event_ranges = []
        root_event = self._hist_events["root"]
        event = last_event

        while event is not root_event:

            milestone_count = event.get_milestone_count()

            if milestone_count > last_milestone_count:
                last_milestone_count = milestone_count
                event_range = [event]
                event_ranges.append(event_range)
                event = event.get_previous_event()
                continue

            event_range.append(event)
            event = event.get_previous_event()

        count = len(sum(event_ranges, []))
        max_event_count = GlobalData["automerge_defaults"]["max_event_count"]
        num_events_to_merge = max(0, count - max_event_count)

        if num_events_to_merge == 0:
            return

        def process_event_ranges(event_ranges, end_events, events_to_delete):

            merge_count = 0

            for event_range in reversed(event_ranges):

                event_range.reverse()
                del event_range[1 + num_events_to_merge - merge_count:]
                end_event = event_range.pop()

                if event_range:

                    end_events.append(end_event)
                    start_event = event_range[0]

                    for event in event_range:

                        if event is not start_event:
                            prev_event = event.get_previous_event()
                            sibling_events = prev_event.get_next_events()[:]
                            sibling_events.remove(event)
                            events_to_delete.extend(sibling_events)

                        event.set_to_be_merged()
                        merge_count += 1

                        if merge_count == num_events_to_merge:
                            return

        end_events = []
        events_to_delete = []
        process_event_ranges(event_ranges, end_events, events_to_delete)

        if end_events:
            self.__update_history(None, None, events_to_delete, end_events, None, False, True)

    def __load_property_value(self, hist_file, time_id, obj_id, prop_id):

        subfile_name = "%s/%s/%s" % (time_id, obj_id, prop_id)
        subfile_index = hist_file.find_subfile(subfile_name)

        if subfile_index == -1:
            msg = "Couldn't load '%s' property of '%s' for time ID %s" % (prop_id, obj_id, time_id)
            logging.critical(msg)
            raise RuntimeError(msg)

        prop_val_pickled = hist_file.read_subfile(subfile_index)

        return cPickle.loads(prop_val_pickled)

    def __get_undo_description(self):

        event = self._hist_events[self._prev_time_id]

        if event is self._hist_events["root"]:
            return ""

        return event.get_description_start()

    def __get_redo_description(self):

        event = self._hist_events[self._prev_time_id]
        next_event = event.get_next_event()

        if next_event:
            return next_event.get_description_start()

        return ""

    def __undo_history(self):

        if self._prev_time_id == self._hist_events["root"].get_time_id():
            return

        event = self._hist_events[self._prev_time_id]
        obj_data = event.get_object_data()
        prev_event = event.get_previous_event()

        logging.debug('\n\n==================== Undoing event:\n%s\n... and restoring event:\n%s\n\n',
                      event.get_description_start(), prev_event.get_description_start())

        time_ids = {}

        for obj_id, prop_ids in obj_data.iteritems():
            if "creation" in prop_ids:
                # the object was created, so it must now be destroyed
                obj = Mgr.get("object", obj_id)
                obj.destroy(add_to_hist=False)
            else:
                time_ids[obj_id] = dict((prop_id, prev_event.get_last_object_prop_change(obj_id,
                                        "creation" if prop_id == "object" else prop_id))
                                        for prop_id in prop_ids)

        props_to_restore = {}

        hist_file = Multifile()
        hist_file.open_read("hist.dat")

        for obj_id in time_ids:

            obj_time_ids = time_ids[obj_id]

            # if "object" is in obj_time_ids, it means that the object was deleted;
            # to undo this, it has to be restored by unpickling it
            if "object" in obj_time_ids:
                time_id = obj_time_ids["object"]
                obj = self.__load_property_value(hist_file, time_id, obj_id, "object")
                # the entire object will be restored
                obj_time_ids = {"self": None}
            else:
                obj = Mgr.get("object", obj_id)

            props_to_restore[obj] = obj_time_ids.keys()

        hist_file.close()

        old_time_id = self._prev_time_id
        new_time_id = prev_event.get_time_id()
        logging.debug('Undoing event with time ID %s and restoring event with time ID %s',
                      old_time_id, new_time_id)

        for obj, data_ids in props_to_restore.iteritems():
            obj.restore_data(data_ids, restore_type="undo", old_time_id=old_time_id,
                             new_time_id=new_time_id)

        Mgr.do("update_picking_col_id_ranges")

        if not prev_event.get_previous_event():
            GlobalData["history_to_undo"] = False

        self._prev_time_id = new_time_id

        GlobalData["history_to_redo"] = True
        Mgr.update_app("history", "check")
        undo_descr = self.__get_undo_description()
        redo_descr = self.__get_redo_description()
        Mgr.update_remotely("history", "set_descriptions", undo_descr, redo_descr)
        GlobalData["unsaved_scene"] = self._prev_time_id != self._saved_time_id
        Mgr.update_app("unsaved_scene")

    def __redo_history(self):

        event = self._hist_events[self._prev_time_id]
        next_event = event.get_next_event()

        if not next_event:
            return

        old_time_id = self._prev_time_id
        new_time_id = next_event.get_time_id()
        logging.debug('\n\n==================== Redoing event with time ID %s:\n%s\n\n',
                      new_time_id, next_event.get_description_start())

        self._prev_time_id = new_time_id

        obj_data = {}

        for obj_id, prop_ids in next_event.get_object_data().iteritems():
            if "object" in prop_ids:
                # the object must be destroyed
                obj = Mgr.get("object", obj_id)
                obj.destroy(add_to_hist=False)
            else:
                obj_data[obj_id] = [("object" if prop_id == "creation" else prop_id)
                                    for prop_id in prop_ids]

        props_to_restore = {}

        hist_file = Multifile()
        hist_file.open_read("hist.dat")

        for obj_id, prop_ids in obj_data.iteritems():

            # if "object" is in prop_ids, it means that the object was created;
            # to redo this, it has to be restored by unpickling it
            if "object" in prop_ids:
                obj = self.__load_property_value(hist_file, new_time_id, obj_id, "object")
                prop_ids = ["self"]
            else:
                obj = Mgr.get("object", obj_id)

            props_to_restore[obj] = prop_ids

        hist_file.close()

        for obj, data_ids in props_to_restore.iteritems():
            obj.restore_data(data_ids, restore_type="redo", old_time_id=old_time_id,
                             new_time_id=new_time_id)

        Mgr.do("update_picking_col_id_ranges")

        if not next_event.get_next_event():
            GlobalData["history_to_redo"] = False

        GlobalData["history_to_undo"] = True
        Mgr.update_app("history", "check")
        undo_descr = self.__get_undo_description()
        redo_descr = self.__get_redo_description()
        Mgr.update_remotely("history", "set_descriptions", undo_descr, redo_descr)
        GlobalData["unsaved_scene"] = self._prev_time_id != self._saved_time_id
        Mgr.update_app("unsaved_scene")

    def __save_history(self, scene_file, set_saved_state=True):

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")
        time_id_stream = StringStream(cPickle.dumps(self._prev_time_id, -1))
        hist_file.add_subfile("time_id", time_id_stream, COMPRESSION)
        hist_event_stream = StringStream(cPickle.dumps(self._hist_events, -1))
        hist_file.add_subfile("events", hist_event_stream, COMPRESSION)

        if hist_file.needs_repack():
            hist_file.repack()

        hist_file.flush()
        hist_file.close()

        scene_file.add_subfile("hist.dat", Filename.binary_filename("hist.dat"), 0)

        if set_saved_state:
            self._saved_time_id = self._prev_time_id

        self._clocks["autobackup"].reset()
        self._backup_file_index = 1

    def __load_history(self, scene_file):

        Mgr.show_screenshot()

        scene_file.extract_subfile(scene_file.find_subfile("hist.dat"), Filename("hist.dat"))

        hist_file = Multifile()
        hist_file.open_read("hist.dat")

        time_id_pickled = hist_file.read_subfile(hist_file.find_subfile("time_id"))
        self._prev_time_id = self._next_time_id = self._saved_time_id = cPickle.loads(time_id_pickled)
        events_pickled = hist_file.read_subfile(hist_file.find_subfile("events"))
        self._hist_events = cPickle.loads(events_pickled)
        event = self._hist_events[self._prev_time_id]

        obj_ids_time_id = event.get_last_object_ids().get_time_id()
        subfile_name = "%s/object_ids" % (obj_ids_time_id,)
        obj_ids_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
        obj_ids = cPickle.loads(obj_ids_pickled)

        objs_to_restore = []

        for obj_id in obj_ids:

            time_id = event.get_last_object_prop_change(obj_id, "creation")
            obj = self.__load_property_value(hist_file, time_id, obj_id, "object")
            objs_to_restore.append(obj)

        hist_file.close()

        for obj in objs_to_restore:
            obj.restore_data(["self"], restore_type="redo", old_time_id=(-1, 0),
                             new_time_id=self._prev_time_id)

        Mgr.do("update_picking_col_id_ranges")

        GlobalData["history_to_undo"] = True if event.get_previous_event() else False
        GlobalData["history_to_redo"] = True if event.get_next_event() else False
        Mgr.update_app("history", "check")
        undo_descr = self.__get_undo_description()
        redo_descr = self.__get_redo_description()
        Mgr.update_remotely("history", "set_descriptions", undo_descr, redo_descr)

    def __edit_history(self):

        if len(self._hist_events) > 2:
            Mgr.update_app("history", "show", self._hist_events, self._prev_time_id)

    def __merge_history(self, end_event, subfile_names, subfiles_to_remove, hist_file, comment=""):

        to_merge = [end_event]
        prev_event = end_event.get_previous_event()

        while prev_event and prev_event.is_to_be_merged():
            to_merge.insert(0, prev_event)
            prev_event = prev_event.get_previous_event()

        start_event = to_merge[0]

        if start_event is self._hist_events["root"]:
            self._hist_events["root"] = end_event

        end_descr = end_event.get_description()

        if "\n\n(Merged)" in end_descr:
            end_descr = end_descr.replace("\n\n(Merged)", "")
        elif "\n\n(Automerged)" in end_descr:
            end_descr = end_descr.replace("\n\n(Automerged)", "")

        description = "%s\n\n(%s)" % (end_descr, comment)
        end_event.set_description(description)

        start_time_id = start_event.get_time_id()
        start_obj_ids = start_event.get_last_object_ids()
        start_obj_ids_time_id = start_obj_ids.get_time_id()

        prev_event = start_event.get_previous_event()

        if prev_event:
            prev_time_id = prev_event.get_time_id()
            prev_obj_ids_time_id = prev_event.get_last_object_ids().get_time_id()
            subfile_name = "%s/object_ids" % (prev_obj_ids_time_id,)
            data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
            obj_ids_before = cPickle.loads(data_pickled)
        else:
            prev_time_id = None
            prev_obj_ids_time_id = None
            obj_ids_before = set()

        end_time_id = end_event.get_time_id()
        end_obj_ids = end_event.get_last_object_ids()
        end_obj_ids_time_id = end_obj_ids.get_time_id()
        subfile_name = "%s/object_ids" % (end_obj_ids_time_id,)
        data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
        obj_ids_after = cPickle.loads(data_pickled)
        obsolete_obj_ids = set()
        obj_ids_time_id = prev_obj_ids_time_id

        for event in to_merge:

            time_id = event.get_last_object_ids().get_time_id()

            if time_id != obj_ids_time_id:
                subfile_name = "%s/object_ids" % (time_id,)
                data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
                obsolete_obj_ids.update(cPickle.loads(data_pickled))
                obj_ids_time_id = time_id

        obsolete_obj_ids -= obj_ids_before | obj_ids_after

        for obj_id in obsolete_obj_ids:

            # the object only exists during the events to be merged, so
            # all of its data is obsolete and must be removed

            obj_id_str = str(obj_id)

            for subfile_name in subfile_names:
                if obj_id_str in subfile_name:
                    subfiles_to_remove.add(subfile_name)

        to_merge.remove(end_event)
        obj_ids_subfile_to_move = ""
        end_data = end_event.get_data()["objects"]

        for event in to_merge:

            time_id = event.get_time_id()
            obj_data = event.get_data()["objects"]

            if time_id == end_obj_ids_time_id:
                obj_ids_subfile_to_move = "%s/object_ids" % (time_id,)

            for obj_id, obj_props in obj_data.iteritems():

                if obj_id not in obsolete_obj_ids:

                    for prop_id in obj_props:

                        if prop_id == "object":
                            continue

                        if prop_id in end_data.get(obj_id, {}):
                            continue

                        subfile_name = "%s/%s/%s" % (time_id, obj_id, "object"
                                                     if prop_id == "creation" else prop_id)
                        data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
                        subfile_name = "%s/%s/%s" % (end_time_id, obj_id, "object"
                                                     if prop_id == "creation" else prop_id)
                        data_stream = StringStream(data_pickled)
                        hist_file.add_subfile(subfile_name, data_stream, COMPRESSION)
                        hist_file.flush()

            start_event.update_object_data(obj_data)

        end_event.update_object_data(start_event.get_data()["objects"])
        end_event.set_previous_event(prev_time_id)

        for obj_id in obsolete_obj_ids:
            end_event.remove_object_props(obj_id)

        if prev_event:
            prev_event.replace_next_event(start_time_id, end_time_id)

        if obj_ids_subfile_to_move:
            end_obj_ids.set_time_id(end_time_id)
            data_pickled = hist_file.read_subfile(hist_file.find_subfile(obj_ids_subfile_to_move))
            subfile_name = "%s/object_ids" % (end_time_id,)
            data_stream = StringStream(data_pickled)
            hist_file.add_subfile(subfile_name, data_stream, COMPRESSION)
            hist_file.flush()

    def __update_history(self, to_undo, to_redo, to_delete, to_merge, to_restore,
                         set_unsaved, automerge=False):

        if set_unsaved:
            self._saved_time_id = (-1, 0)

        if not (to_undo or to_redo or to_delete or to_merge or to_restore):

            if set_unsaved:
                undo_descr = self.__get_undo_description()
                redo_descr = self.__get_redo_description()
                Mgr.update_remotely("history", "set_descriptions", undo_descr, redo_descr)
                GlobalData["unsaved_scene"] = True
                Mgr.update_app("unsaved_scene")

            return

        time_to_restore = to_restore if to_restore else self._prev_time_id
        event_to_restore = self._hist_events[time_to_restore]

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")

        if to_undo or to_redo:

            obj_ids_before = set(Mgr.get("object_ids"))
            obj_ids_time_id = event_to_restore.get_last_object_ids().get_time_id()
            subfile_name = "%s/object_ids" % (obj_ids_time_id,)
            obj_ids_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
            obj_ids_after = cPickle.loads(obj_ids_pickled)
            objects_to_destroy = [Mgr.get("object", obj_id) for obj_id in
                                  obj_ids_before - obj_ids_after]
            objects_to_create = obj_ids_after - obj_ids_before
            objects_to_update = obj_ids_after & obj_ids_before

            for obj in objects_to_destroy:
                obj.destroy(add_to_hist=False)

            props_to_restore = {}

            for obj_id in objects_to_create:

                time_id = event_to_restore.get_last_object_prop_change(obj_id, "creation")
                obj = self.__load_property_value(hist_file, time_id, obj_id, "object")
                props_to_restore[obj] = ["self"]

            for obj_id in objects_to_update:

                prop_ids = set()

                for event in to_undo + to_redo:
                    prop_ids |= event.get_changed_object_props(obj_id)

                obj = Mgr.get("object", obj_id)
                props_to_restore[obj] = prop_ids

        hist_file.close()

        old_time_id = self._prev_time_id

        if to_undo or to_redo:

            logging.debug('\n\n==================== Restoring event with time ID %s'
                          + ' (current event time ID: %s).\n\n',
                          time_to_restore, old_time_id)

            for obj, data_ids in props_to_restore.iteritems():
                obj.restore_data(data_ids, restore_type="undo_redo", old_time_id=old_time_id,
                                 new_time_id=time_to_restore)

        Mgr.do("update_picking_col_id_ranges")

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")

        def get_future_events(event):

            future_events = []
            next_events = event.get_next_events()

            while next_events:

                future_events.extend(next_events)
                events = []

                for next_event in next_events:
                    events.extend(next_event.get_next_events())

                next_events = events

            return future_events

        def add_subfiles_to_remove(event, subfile_names, subfiles_to_remove,
                                   include_extra_data=True):

            time_id_str = str(event.get_time_id())

            for subfile_name in subfile_names:
                if subfile_name.startswith(time_id_str):
                    if include_extra_data or "__extra__" not in subfile_name:
                        subfiles_to_remove.add(subfile_name)

        events_to_remove = set(to_delete)
        events_to_merge = set()
        subfiles_to_remove = set()
        subfile_names = [hist_file.get_subfile_name(i)
                         for i in xrange(hist_file.get_num_subfiles())]
        subfile_names.remove("events")
        subfile_names.remove("time_id")

        for event in to_delete:
            events_to_remove.update(get_future_events(event))

        for event in to_merge:

            prev_event = event.get_previous_event()

            while prev_event and prev_event.is_to_be_merged():
                events_to_merge.add(prev_event)
                prev_event = prev_event.get_previous_event()

        comment = "Automerged" if automerge else "Merged"

        for event in to_merge:
            self.__merge_history(event, subfile_names, subfiles_to_remove,
                                 hist_file, comment=comment)

        for event in events_to_merge:
            add_subfiles_to_remove(event, subfile_names, subfiles_to_remove,
                                   include_extra_data=False)

        for event in events_to_remove:
            add_subfiles_to_remove(event, subfile_names, subfiles_to_remove)

        events_to_remove.update(events_to_merge)

        for event in events_to_remove:
            del self._hist_events[event.get_time_id()]

        for event in events_to_remove:

            prev_event = event.get_previous_event()

            if prev_event:
                prev_event.remove_next_event(event.get_time_id(), update_milestone_count=True)

        for name in subfiles_to_remove:
            hist_file.remove_subfile(hist_file.find_subfile(name))

        if to_delete or to_merge:
            hist_file.repack()

        hist_file.close()

        if automerge:

            if time_to_restore != self._prev_time_id:
                self._prev_time_id = time_to_restore

            return

        if time_to_restore != self._prev_time_id:

            event = self._hist_events[time_to_restore]
            prev_event = event.get_previous_event()

            # make the timeline that the restored event belongs to the "active"
            # timeline for self.__undo_history() and self.__redo_history()
            while prev_event and (event.get_time_id() != self._prev_time_id):
                time_id = event.get_time_id()
                prev_event.remove_next_event(time_id)
                prev_event.add_next_event(time_id)
                event = prev_event
                prev_event = event.get_previous_event()

            self._prev_time_id = time_to_restore

        event = self._hist_events[self._prev_time_id]
        GlobalData["history_to_undo"] = True if event.get_previous_event() else False
        GlobalData["history_to_redo"] = True if event.get_next_event() else False
        Mgr.update_app("history", "check")
        undo_descr = self.__get_undo_description()
        redo_descr = self.__get_redo_description()
        Mgr.update_remotely("history", "set_descriptions", undo_descr, redo_descr)
        GlobalData["unsaved_scene"] = self._prev_time_id != self._saved_time_id
        Mgr.update_app("unsaved_scene")

    def __archive_history(self):

        if len(self._hist_events) == 2:
            return

        event = self._hist_events[self._prev_time_id]
        merge_time_ids = set([str(self._prev_time_id)])
        prev_event = event.get_previous_event()

        while prev_event:
            prev_event.set_to_be_merged()
            merge_time_ids.add(str(prev_event.get_time_id()))
            prev_event = prev_event.get_previous_event()

        merge_time_ids = tuple(merge_time_ids)
        subfiles_to_remove = set()

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")
        subfile_names = [hist_file.get_subfile_name(i)
                         for i in xrange(hist_file.get_num_subfiles())]
        subfile_names.remove("events")
        subfile_names.remove("time_id")

        self.__merge_history(event, subfile_names, subfiles_to_remove, hist_file)

        root_event = self._hist_events["root"]
        time_id = root_event.get_time_id()
        time_id_str = str(time_id)

        for subfile_name in subfile_names:
            if not subfile_name.startswith(time_id_str):
                if not (subfile_name.startswith(merge_time_ids) and "__extra__" in subfile_name):
                    subfiles_to_remove.add(subfile_name)

        for subfile_name in subfiles_to_remove:
            hist_file.remove_subfile(hist_file.find_subfile(subfile_name))

        hist_file.repack()
        hist_file.close()

        self._prev_time_id = time_id

        root_event.clear_next_events()
        self._hist_events = {time_id: root_event, "root": root_event}

        self._saved_time_id = (-1, 0)
        GlobalData["unsaved_scene"] = True
        Mgr.update_app("unsaved_scene")


MainObjects.add_class(HistoryManager)
