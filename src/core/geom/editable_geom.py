from .data import *


class EditableGeomManager(BaseObject, ObjPropDefaultsManager):

    def __init__(self):

        self._id_generator = id_generator()
        self._obj_lvl_before_hist_change = "top"
        self._sel_before_hist_change = set()
        Mgr.accept("create_editable_geom", self.__create)

        Mgr.add_app_updater("active_obj_level", self.__update_object_level)
        Mgr.add_app_updater("history_change", self.__start_selection_check)

    def setup(self):

        sort = PendingTasks.get_sort("update_selection", "object")
        PendingTasks.add_task_id("set_obj_level", "object", sort + 1)

        return True

    def __create(self, model=None, geom_data_obj=None, name="", origin_pos=None):

        if not model:
            pos = Point3() if origin_pos is None else origin_pos
            model_id = ("editable_geom",) + self._id_generator.next()
            model = Mgr.do("create_model", model_id, name, pos)

        obj = EditableGeom(model, geom_data_obj)
        model.set_geom_object(obj)

        return obj

    def __update_object_level(self):

        obj_lvl = Mgr.get_global("active_obj_level")
        obj_root = Mgr.get("object_root")
        picking_mask = Mgr.get("picking_mask")

        models = set([obj for obj in Mgr.get("selection", "top")
                      if obj.get_type() == "model" and obj.get_geom_type() == "editable_geom"])

        if self._sel_before_hist_change:

            for model_id in self._sel_before_hist_change:

                model = Mgr.get("model", model_id)

                if model and model.get_geom_type() == "editable_geom":
                    models.add(model)

        if obj_lvl == "top":

            obj_root.show(picking_mask)

            for model in models:
                geom_data_obj = model.get_geom_object().get_geom_data_object()
                geom_data_obj.show_top_level()

        else:

            obj_root.hide(picking_mask)

            for model in models:
                geom_data_obj = model.get_geom_object().get_geom_data_object()
                geom_data_obj.show_subobj_level(obj_lvl)

    def __check_selection(self):

        obj_lvl = self._obj_lvl_before_hist_change

        if obj_lvl == "top":
            return

        sel_after_hist_change = set([obj.get_id() for obj in Mgr.get("selection", "top")])
        set_sublvl = False

        if sel_after_hist_change == self._sel_before_hist_change:

            set_sublvl = True

            for model_id in sel_after_hist_change:

                model = Mgr.get("model", model_id)

                if model.get_geom_type() != "editable_geom":
                    set_sublvl = False
                    break

        if set_sublvl:
            Mgr.set_global("active_obj_level", obj_lvl)
            Mgr.update_app("active_obj_level", restore=True)

        self._obj_lvl_before_hist_change = "top"
        self._sel_before_hist_change = set()

    def __start_selection_check(self):

        # This is called before undo/redo, to determine whether or not to stay at
        # the current subobject level, depending on the change in toplevel object
        # selection.

        obj_lvl = Mgr.get_global("active_obj_level")

        if obj_lvl == "top":
            return

        self._obj_lvl_before_hist_change = obj_lvl
        self._sel_before_hist_change = set([obj.get_id() for obj in Mgr.get("selection", "top")])
        task = self.__check_selection
        task_id = "set_obj_level"
        PendingTasks.add(task, task_id, "object")
        Mgr.set_global("active_obj_level", "top")
        Mgr.update_app("active_obj_level", restore=True)


class EditableGeom(BaseObject):

    def __getstate__(self):

        # When pickling an EditableGeom, it should not have a model or a geom_data_obj,
        # since these are pickled separately.

        d = self.__dict__.copy()
        d["_model"] = None
        d["_geom_data_obj"] = None

        return d

    def __init__(self, model, geom_data_obj):

        prop_ids = []
        self._prop_ids = prop_ids
        self._type_prop_ids = prop_ids
        self._type = "editable_geom"
        self._model = model
        self._geom_data_obj = geom_data_obj if geom_data_obj else GeomDataObject(self)

        if geom_data_obj:
            geom_data_obj.set_owner(self)

    def create(self, geom_data_obj=None):

        if geom_data_obj:
            self._geom_data_obj = geom_data_obj

        self._geom_data_obj.create_geometry(self._type)
        self._geom_data_obj.finalize_geometry()

    def destroy(self):

        self._geom_data_obj.destroy()
        self._geom_data_obj = None

    def is_valid(self):

        return False

    def get_type(self):

        return self._type

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_geom_data_object(self):

        return self._geom_data_obj

    def set_model(self, model):

        self._model = model

    def get_model(self):

        return self._model

    def get_toplevel_object(self):

        return self._model

    def replace(self, geom_obj):

        geom_data_obj = self._geom_data_obj
        geom_data_obj.set_owner(geom_obj)
        geom_obj.set_geom_data_object(geom_data_obj)

    def get_subobj_selection(self, subobj_lvl):

        return self._geom_data_obj.get_selection(subobj_lvl)

    def update_selection_state(self, is_selected=True):

        self._geom_data_obj.update_selection_state(is_selected)

    def update_render_mode(self):

        self._geom_data_obj.update_render_mode()

    def set_two_sided(self, two_sided=True):

        self._geom_data_obj.get_origin().set_two_sided(two_sided)

    def register(self):
        pass

    def unregister(self):

        self._geom_data_obj.unregister()

    def set_origin(self, origin):

        self._geom_data_obj.set_origin(origin)

    def get_origin(self):

        if self._geom_data_obj:
            return self._geom_data_obj.get_origin()

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["geom_obj"] = {"main": self}
            prop_ids = self.get_property_ids()

            for prop_id in prop_ids:
                data[prop_id] = {"main": self.get_property(prop_id)}

        elif event_type == "prop_change":

            if prop_id == "editable state":
                data["geom_obj"] = {"main": self}
            elif prop_id in self.get_property_ids():
                data[prop_id] = {"main": self.get_property(prop_id)}

        data.update(self._geom_data_obj.get_data_to_store(event_type, prop_id))

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()

        if "self" in data_ids:

            for prop_id in self.get_property_ids():
                val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                self.set_property(prop_id, val, restore_type)

            geom_data_obj = Mgr.do("load_last_from_history", obj_id, "geom_data", new_time_id)
            self._geom_data_obj = geom_data_obj
            self.get_origin().reparent_to(self._model.get_origin())
            geom_data_obj.set_owner(self)
            geom_data_obj.restore_data(["self"], restore_type, old_time_id, new_time_id)

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                    self.set_property(prop_id, val, restore_type)
                    data_ids.remove(prop_id)

            if data_ids:
                self._geom_data_obj.restore_data(data_ids, restore_type, old_time_id, new_time_id)

    def get_property_ids(self, for_hist=False):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids


MainObjects.add_class(EditableGeomManager)
