from ..base import *
import random


class ModelManager(ObjectManager):

    def __init__(self):

        ObjectManager.__init__(self, "model", self.__create_model)
        Mgr.set_global("two_sided", False)

    def setup(self):

        PendingTasks.add_task_id("set_geom_obj", "object", 0)

        return True

    def __create_model(self, model_id, name, origin_pos):

        model = Model(model_id, name, origin_pos)

        return model, model_id


class Model(TopLevelObject):

    def __getstate__(self):

        d = self.__dict__.copy()
        d["_geom_obj"] = None
        d["_material"] = None
        d["_color"] = VBase4(1., 1., 1., 1.)
        d["_pivot"] = NodePath(self.get_pivot().get_name())
        d["_origin"] = NodePath(self.get_origin().get_name())

        return d

    def __setstate__(self, state):

        self.__dict__ = state

        pivot = self.get_pivot()
        pivot.reparent_to(Mgr.get("object_root"))
        origin = self.get_origin()

        if Mgr.get_global("transform_target_type") == "pivot":
            origin.reparent_to(Mgr.get("object_root"))
        else:
            origin.reparent_to(pivot)

        self._bbox.get_origin().reparent_to(origin)
        self.get_pivot_gizmo().get_origin().set_compass(pivot)

    def __init__(self, model_id, name, origin_pos):

        TopLevelObject.__init__(self, "model", model_id, name, origin_pos)

        self._geom_obj = None

        self._bbox = Mgr.do("create_bbox", self)
        self._bbox.hide()

    def __del__(self):

        print "Model garbage-collected."

    def destroy(self, add_to_hist=True):

        if not TopLevelObject.destroy(self, add_to_hist):
            return

        self._geom_obj.destroy()
        self._geom_obj.set_model(None)
        self._geom_obj = None
        self._bbox.destroy()
        self._bbox = None

    def set_geom_object(self, geom_obj):

        self._geom_obj = geom_obj

    def get_geom_object(self):

        return self._geom_obj

    def get_geom_type(self):

        return self._geom_obj.get_type() if self._geom_obj else ""

    def __restore_geom_object(self, geom_obj, restore_type, old_time_id, new_time_id):

        geom_obj.set_model(self)
        self._geom_obj = geom_obj

        task = lambda: Mgr.get("selection", "top").update_ui(force=True)
        task_id = "update_type_props"
        PendingTasks.add(task, task_id, "ui")

        geom_obj.restore_data(["self"], restore_type, old_time_id, new_time_id)

    def replace_geom_object(self, geom_obj):

        geom_data_obj = self._geom_obj.get_geom_data_object()
        geom_data_obj.set_owner(geom_obj)
        geom_obj.set_geom_data_object(geom_data_obj)
        geom_obj.set_model(self)
        self._geom_obj = geom_obj

        task = lambda: Mgr.get("selection", "top").update_ui(force=True)
        task_id = "update_type_props"
        PendingTasks.add(task, task_id, "ui")

    def get_data_to_store(self, event_type, prop_id=""):

        data = TopLevelObject.get_data_to_store(self, event_type, prop_id)
        data.update(self._geom_obj.get_data_to_store(event_type, prop_id))

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        TopLevelObject.restore_data(self, data_ids, restore_type, old_time_id, new_time_id)
        obj_id = self.get_id()

        if "self" in data_ids:

            geom_obj = Mgr.do("load_last_from_history", obj_id, "geom_obj", new_time_id)
            self.__restore_geom_object(geom_obj, restore_type, old_time_id, new_time_id)

        else:

            if "geom_obj" in data_ids:

                geom_obj = Mgr.do("load_last_from_history", obj_id, "geom_obj", new_time_id)
                self.replace_geom_object(geom_obj)
                prop_ids = geom_obj.get_property_ids()
                geom_obj.restore_data(prop_ids, restore_type, old_time_id, new_time_id)

                for prop_id in prop_ids:
                    if prop_id in data_ids:
                        data_ids.remove(prop_id)

            if data_ids:
                self._geom_obj.restore_data(data_ids, restore_type, old_time_id, new_time_id)

    def set_property(self, prop_id, value, restore=""):

        if prop_id in TopLevelObject.get_property_ids(self):
            return TopLevelObject.set_property(self, prop_id, value, restore)

        if prop_id in self._geom_obj.get_property_ids() + ["editable state"]:
            return self._geom_obj.set_property(prop_id, value)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id in TopLevelObject.get_property_ids(self):
            return TopLevelObject.get_property(self, prop_id, for_remote_update)

        if prop_id in self._geom_obj.get_property_ids():
            return self._geom_obj.get_property(prop_id, for_remote_update)

    def get_type_property_ids(self):

        return self._geom_obj.get_type_property_ids()

    def get_subobj_selection(self, subobj_lvl):

        return self._geom_obj.get_geom_data_object().get_selection(subobj_lvl)

    def register(self):

        TopLevelObject.register(self)

        self._bbox.register()

        if self._geom_obj:
            self._geom_obj.register()

    def get_bbox(self):

        return self._bbox

    def update_selection_state(self, is_selected=True):

        TopLevelObject.update_selection_state(self, is_selected)

        if not self._bbox:
            return

        if "shaded" in Mgr.get_global("render_mode"):
            if is_selected:
                self._bbox.show()
            else:
                self._bbox.hide()

        if self._geom_obj:
            self._geom_obj.get_geom_data_object().update_selection_state(is_selected)

    def update_render_mode(self):

        if self.is_selected():
            if "shaded" in Mgr.get_global("render_mode"):
                self._bbox.show()
            else:
                self._bbox.hide()

        if self._geom_obj:
            self._geom_obj.get_geom_data_object().update_render_mode()

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this model.

        """

        self._bbox.flash()


MainObjects.add_class(ModelManager)
