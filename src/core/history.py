from __future__ import with_statement
from .base import *


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

    def __init__(self, time_id, data, prev=None, description=""):

        self._time_id = time_id
        self._data = data  # dict
        self._prev = prev  # HistoryEvent object
        self._next = []  # list of HistoryEvent objects
        self._descr = description
        self._user_descr = ""
        self._is_milestone = False
        self._user_descr_tmp = None
        self._is_milestone_tmp = None
        self._to_be_merged = False

        if self._prev:

            self._prev.add_next_event(self)

            if data["object_ids"] is None:
                self._data["object_ids"] = self._prev.get_last_object_ids()

    def get_time_id(self):

        return self._time_id

    def get_timestamp(self):

        sec, index = self.get_time_id()
        timestamp = time.ctime(sec) + ((" (%s)" % (index + 1)) if index else "")

        return timestamp

    def set_previous_event(self, prev_event):

        self._prev = prev_event

    def get_previous_event(self):

        return self._prev

    def add_next_event(self, event):

        self._next.append(event)

    def remove_next_event(self, event):

        self._next.remove(event)

    def clear_next_events(self):

        self._next = []

    def get_next_event(self):

        return self._next[-1] if self._next else None

    def get_next_events(self):

        return self._next

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

        if self._is_milestone_tmp is not None:
            self._is_milestone = self._is_milestone_tmp

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

    def remove_object_props(self, obj_id):

        if obj_id in self._data["objects"]:
            del self._data["objects"][obj_id]

        if self._prev:
            self._prev.remove_object_props(obj_id)

    def get_changed_object_props(self, obj_id):

        return self._data["objects"].get(obj_id, set())

    def get_last_object_prop_change(self, obj_id, prop_id):

        data = self._data["objects"]

        if obj_id in data and prop_id in data[obj_id]:
            return self._time_id
        else:
            if not self._prev:
                return
            else:
                return self._prev.get_last_object_prop_change(obj_id, prop_id)

    def get_last_object_ids(self):

        return self._data["object_ids"]

    def set_to_be_merged(self, to_be_merged=True):

        self._to_be_merged = to_be_merged

    def is_to_be_merged(self):

        return self._to_be_merged


class HistoryManager(BaseObject):

    def __init__(self):

        self._restoring_history = False
        self._event_descr_to_store = ""
        self._event_data_to_store = {"objects": {}}
        self._update_time_id = True
        self._hist_events = {}
        self._prev_time_id = self._next_time_id = self._saved_time_id = (0, 0)

        GlobalData.set_default("history_to_undo", False)
        GlobalData.set_default("history_to_redo", False)

        Mgr.accept("reset_history", self.__reset_history)
        Mgr.accept("load_from_history", self.__load_from_history)
        Mgr.accept("load_last_from_history", self.__load_last_value)
        Mgr.accept("update_history_time", self.__update_time_id)
        Mgr.accept("get_prev_history_time", self.__get_previous_time_id)
        Mgr.accept("get_history_time", self.__get_next_time_id)
        Mgr.accept("add_history", self.__add_history)
        Mgr.accept("save_history", self.__save_history)
        Mgr.accept("load_history", self.__load_history)

        Mgr.add_app_updater("history", self.__manage_history)
        Mgr.add_task(self.__store_history, "store_history", sort=49)

    def setup(self):

        self.__reset_history()

        return True

    def __manage_history(self, update_type, *args, **kwargs):

        if update_type in ("undo", "redo", "update"):

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
        elif update_type == "clear":
            self.__clear_history()

    def __reset_history(self):

        event_data = {"objects": {}, "object_ids": TimeIDRef((0, 0))}
        self._hist_events = {(0, 0): HistoryEvent((0, 0), event_data)}
        self._prev_time_id = self._saved_time_id = (0, 0)

        hist_file = Multifile()
        hist_file.open_write("hist.dat")
        time_id_stream = StringStream(cPickle.dumps(self._prev_time_id, -1))
        hist_file.add_subfile("time_id", time_id_stream, 6)
        hist_event_stream = StringStream(cPickle.dumps(self._hist_events, -1))
        hist_file.add_subfile("events", hist_event_stream, 6)
        object_ids_stream = StringStream(cPickle.dumps(set(), -1))
        hist_file.add_subfile("%s/object_ids" % (self._prev_time_id,), object_ids_stream, 6)

        hist_file.repack()
        hist_file.close()

        GlobalData["history_to_undo"] = False
        GlobalData["history_to_redo"] = False
        Mgr.update_app("history", "check")

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

        if self._restoring_history:
            return

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

    def __store_history(self, task):

        if self._restoring_history:
            return task.cont

        event_data = self._event_data_to_store

        if not event_data["objects"]:
            return task.cont

        time_id = self.__update_time_id() if self._update_time_id else self._next_time_id

        if "object_ids" not in event_data:
            event_data["object_ids"] = None

        obj_data = event_data["objects"]
        obj_ids = event_data["object_ids"]

        objects = dict((obj_id, set([("creation" if (k == "object" and v) else k)
                       for k, v in prop_data.iteritems()])) for obj_id, prop_data
                       in obj_data.iteritems())

        data = {"objects": objects,
                "object_ids": None if obj_ids is None else TimeIDRef(time_id)}
        prev_event = self._hist_events[self._prev_time_id]
        event = HistoryEvent(time_id, data, prev_event, self._event_descr_to_store)
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
                hist_file.add_subfile(subfile_name, streams[-1], 6)

                if "extra" in prop_val_data:
                    for data_id, data in prop_val_data["extra"].iteritems():
                        subfile_name = "%s/%s/%s" % (time_id, obj_id, data_id)
                        streams.append(StringStream(cPickle.dumps(data, -1)))
                        hist_file.add_subfile(subfile_name, streams[-1], 6)

        if obj_ids is not None:
            subfile_name = "%s/object_ids" % (time_id,)
            streams.append(StringStream(cPickle.dumps(obj_ids, -1)))
            hist_file.add_subfile(subfile_name, streams[-1], 6)

        if hist_file.needs_repack():
            hist_file.repack()

        hist_file.flush()
        hist_file.close()

        self._event_data_to_store = {"objects": {}}
        self._event_descr_to_store = ""
        self._update_time_id = True
        self._prev_time_id = self._next_time_id = time_id

        GlobalData["history_to_undo"] = True
        GlobalData["history_to_redo"] = False
        Mgr.update_app("history", "check")
        GlobalData["unsaved_scene"] = True
        Mgr.update_app("unsaved_scene")

        return task.cont

    def __load_property_value(self, hist_file, time_id, obj_id, prop_id):

        subfile_name = "%s/%s/%s" % (time_id, obj_id, prop_id)
        prop_val_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))

        return cPickle.loads(prop_val_pickled)

    def __undo_history(self):

        if self._prev_time_id == (0, 0):
            return

        event = self._hist_events[self._prev_time_id]
        obj_data = event.get_object_data()
        prev_event = event.get_previous_event()

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

        for obj, data_ids in props_to_restore.iteritems():
            obj.restore_data(data_ids, restore_type="undo", old_time_id=old_time_id,
                             new_time_id=new_time_id)

        Mgr.do("update_picking_col_id_ranges")

        if not prev_event.get_previous_event():
            GlobalData["history_to_undo"] = False

        self._prev_time_id = new_time_id

        GlobalData["history_to_redo"] = True
        Mgr.update_app("history", "check")
        GlobalData["unsaved_scene"] = self._prev_time_id != self._saved_time_id
        Mgr.update_app("unsaved_scene")

    def __redo_history(self):

        event = self._hist_events[self._prev_time_id]
        next_event = event.get_next_event()

        if not next_event:
            return

        obj_data_to_restore = next_event.get_object_data()

        old_time_id = self._prev_time_id
        new_time_id = next_event.get_time_id()

        self._prev_time_id = new_time_id

        obj_data = {}

        for obj_id, prop_ids in obj_data_to_restore.iteritems():
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
        GlobalData["unsaved_scene"] = self._prev_time_id != self._saved_time_id
        Mgr.update_app("unsaved_scene")

    def __save_history(self, scene_file):

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")
        time_id_stream = StringStream(cPickle.dumps(self._prev_time_id, -1))
        hist_file.add_subfile("time_id", time_id_stream, 6)
        hist_event_stream = StringStream(cPickle.dumps(self._hist_events, -1))
        hist_file.add_subfile("events", hist_event_stream, 6)

        if hist_file.needs_repack():
            hist_file.repack()

        hist_file.flush()
        hist_file.close()

        scene_file.add_subfile("hist.dat", Filename.binary_filename("hist.dat"), 0)

        self._saved_time_id = self._prev_time_id

    def __load_history(self, scene_file):

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
            obj.restore_data(["self"], restore_type="redo", old_time_id=(0, 0),
                             new_time_id=self._prev_time_id)

        Mgr.do("update_picking_col_id_ranges")

        GlobalData["history_to_undo"] = True if event.get_previous_event() else False
        GlobalData["history_to_redo"] = True if event.get_next_event() else False
        Mgr.update_app("history", "check")

    def __edit_history(self):

        if len(self._hist_events) > 1:
            hist_root = self._hist_events[(0, 0)]
            Mgr.update_app("history", "show", hist_root, self._prev_time_id)

    def __merge_history(self, end_event, subfile_names, subfiles_to_remove, hist_file):

        to_merge = [end_event]
        prev_event = end_event.get_previous_event()

        while prev_event.is_to_be_merged():
            to_merge.insert(0, prev_event)
            prev_event = prev_event.get_previous_event()

        start_event = prev_event
        start_event.set_description("MERGED EVENT")
        start_time_id = start_event.get_time_id()
        start_event_data = start_event.get_data()

        obj_ids_time_id = start_event_data["object_ids"].get_time_id()
        subfile_name = "%s/object_ids" % (obj_ids_time_id,)
        data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
        obj_ids_before = cPickle.loads(data_pickled)

        created_obj_ids = obj_ids_before if start_time_id == (0, 0) else set()
        deleted_obj_ids = set()

        for event in to_merge:

            time_id = event.get_last_object_ids().get_time_id()

            if time_id != obj_ids_time_id:
                subfile_name = "%s/object_ids" % (time_id,)
                data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
                obj_ids_after = cPickle.loads(data_pickled)
                deleted_obj_ids |= created_obj_ids - obj_ids_after
                created_obj_ids -= deleted_obj_ids
                created_obj_ids |= obj_ids_after - obj_ids_before
                obj_ids_time_id = time_id
                obj_ids_before = obj_ids_after

        for event in to_merge:

            time_id = event.get_time_id()
            event_data = event.get_data()

            for obj_id, obj_props in event_data["objects"].iteritems():

                if obj_id in deleted_obj_ids:

                    # the object was deleted, so all of its data must be
                    # removed

                    event.remove_object_props(obj_id)

                    obj_id_str = str(obj_id)

                    for subfile_name in subfile_names:
                        if obj_id_str in subfile_name:
                            subfiles_to_remove.add(subfile_name)

                elif "object" not in obj_props:

                    for prop_id in obj_props:

                        subfile_name = "%s/%s/%s" % (time_id, obj_id, "object"
                                                     if prop_id == "creation" else prop_id)
                        data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
                        subfile_name = "%s/%s/%s" % (start_time_id, obj_id, "object"
                                                     if prop_id == "creation" else prop_id)
                        data_stream = StringStream(data_pickled)
                        hist_file.add_subfile(subfile_name, data_stream, 6)
                        hist_file.flush()

            start_event.update_object_data(event_data["objects"])

        event_data = end_event.get_data()
        start_event_data["object_ids"] = event_data["object_ids"]
        start_event.clear_next_events()

        for next_event in end_event.get_next_events():
            next_event.set_previous_event(start_event)
            start_event.add_next_event(next_event)

        time_id_ref = start_event_data["object_ids"]
        time_id = time_id_ref.get_time_id()

        if time_id not in self._hist_events:
            time_id_ref.set_time_id(start_time_id)
            subfile_name = "%s/object_ids" % (time_id,)
            data_pickled = hist_file.read_subfile(hist_file.find_subfile(subfile_name))
            subfile_name = "%s/object_ids" % (start_time_id,)
            data_stream = StringStream(data_pickled)
            hist_file.add_subfile(subfile_name, data_stream, 6)
            hist_file.flush()

    def __update_history(self, to_undo, to_redo, to_delete, to_merge, to_restore):

        if not (to_undo or to_redo or to_delete or to_merge or to_restore):
            return

        time_to_restore = to_restore if to_restore else self._prev_time_id
        event_to_restore = self._hist_events[time_to_restore]

        if event_to_restore in to_merge:

            evt_prev = event_to_restore.get_previous_event()

            while evt_prev.is_to_be_merged():
                evt_prev = evt_prev.get_previous_event()

            time_to_restore = evt_prev.get_time_id()

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

        for obj, data_ids in props_to_restore.iteritems():
            obj.restore_data(data_ids, restore_type="undo_redo", old_time_id=old_time_id,
                             new_time_id=time_to_restore)

        Mgr.do("update_picking_col_id_ranges")

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")

        subfiles_to_remove = set()
        subfile_names = [hist_file.get_subfile_name(i)
                         for i in xrange(hist_file.get_num_subfiles())]
        subfile_names.remove("events")
        subfile_names.remove("time_id")

        def delete_history(event, recursive=True):

            del self._hist_events[event.get_time_id()]
            time_id_str = str(event.get_time_id())

            for subfile_name in subfile_names:
                if subfile_name.startswith(time_id_str):
                    subfiles_to_remove.add(subfile_name)

            if recursive:
                for next_event in event.get_next_events():
                    delete_history(next_event)

        for event in to_delete:

            delete_history(event)
            prev_event = event.get_previous_event()

            if prev_event:
                prev_event.remove_next_event(event)

        for event in to_merge:

            delete_history(event, recursive=False)
            prev_event = event.get_previous_event()

            while prev_event.is_to_be_merged():
                delete_history(prev_event, recursive=False)
                prev_event = prev_event.get_previous_event()

        for event in to_merge:
            self.__merge_history(event, subfile_names, subfiles_to_remove, hist_file)

        for name in subfiles_to_remove:
            hist_file.remove_subfile(hist_file.find_subfile(name))

        if to_delete or to_merge:
            hist_file.repack()

        hist_file.close()

        if time_to_restore != self._prev_time_id:

            event = self._hist_events[time_to_restore]
            prev_event = event.get_previous_event()

            # make the timeline that the restored event belongs to the "active"
            # timeline for self.__undo_history() and self.__redo_history()
            while prev_event and (event.get_time_id() != self._prev_time_id):
                prev_event.remove_next_event(event)
                prev_event.add_next_event(event)
                event = prev_event
                prev_event = event.get_previous_event()

            self._prev_time_id = time_to_restore

        event = self._hist_events[self._prev_time_id]
        GlobalData["history_to_undo"] = True if event.get_previous_event() else False
        GlobalData["history_to_redo"] = True if event.get_next_event() else False
        Mgr.update_app("history", "check")
        GlobalData["unsaved_scene"] = self._prev_time_id != self._saved_time_id
        Mgr.update_app("unsaved_scene")

    def __clear_history(self):

        if len(self._hist_events) == 1:
            return

        time_id = (0, 0)
        time_id_str = str(time_id)
        root_event = self._hist_events[time_id]

        event = self._hist_events[self._prev_time_id]
        prev_event = event.get_previous_event()

        while prev_event is not root_event:
            prev_event.set_to_be_merged()
            prev_event = prev_event.get_previous_event()

        subfiles_to_remove = set()

        hist_file = Multifile()
        hist_file.open_read_write("hist.dat")
        subfile_names = [hist_file.get_subfile_name(i)
                         for i in xrange(hist_file.get_num_subfiles())]
        subfile_names.remove("events")
        subfile_names.remove("time_id")

        self.__merge_history(event, subfile_names, subfiles_to_remove, hist_file)

        for subfile_name in subfile_names:

            if not subfile_name.startswith(time_id_str):
                subfiles_to_remove.add(subfile_name)

        for subfile_name in subfiles_to_remove:
            hist_file.remove_subfile(hist_file.find_subfile(subfile_name))

        hist_file.repack()
        hist_file.close()

        self._prev_time_id = time_id

        root_event.clear_next_events()
        self._hist_events = {time_id: root_event}


MainObjects.add_class(HistoryManager)
