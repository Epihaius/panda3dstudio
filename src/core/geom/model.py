from ..base import *
import random


class ModelManager(ObjectManager):

    def __init__(self):

        ObjectManager.__init__(self, "model", self.__create_model)
        GlobalData.set_default("two_sided", False)

    def setup(self):

        PendingTasks.add_task_id("set_geom_obj", "object", 0)

        return True

    def __create_model(self, model_id, name, origin_pos, bbox_color=(1., 1., 1.)):

        model = Model(model_id, name, origin_pos, bbox_color)

        return model, model_id


class Model(TopLevelObject):

    def __getstate__(self):

        state = TopLevelObject.__getstate__(self)

        state["_geom_obj"] = None
        state["_material"] = None

        return state

    def __setstate__(self, state):

        TopLevelObject.__setstate__(self, state)

        self._bbox.get_origin().reparent_to(self.get_origin())

    def __init__(self, model_id, name, origin_pos, bbox_color):

        TopLevelObject.__init__(self, "model", model_id, name, origin_pos, has_color=True)

        self.get_property_ids().append("material")
        self._material = None
        self._geom_obj = None

        self._bbox = Mgr.do("create_bbox", self, bbox_color)
        self._bbox.hide()

    def __del__(self):

        print "Model garbage-collected."

    def destroy(self, add_to_hist=True):

        if not TopLevelObject.destroy(self, add_to_hist):
            return

        if self._material:
            self._material.remove(self)

        self._geom_obj.destroy()
        self._geom_obj.set_model(None)
        self._geom_obj = None
        self._bbox.destroy()
        self._bbox = None

    def set_color(self, color, update_app=True):

        return TopLevelObject.set_color(self, color, update_app, not self._material)

    def set_material(self, material, restore=""):

        old_material = self._material

        if old_material is material:
            return False

        if old_material:
            old_material.remove(self)

        if not material:

            self._material = material

            return True

        material_id = material.get_id()
        registered_material = Mgr.get("material", material_id)

        if registered_material:

            self._material = registered_material

        else:

            self._material = material
            Mgr.do("register_material", material)
            owner_ids = material.get_owner_ids()

            for owner_id in owner_ids[:]:

                if owner_id == self._id:
                    continue

                owner = Mgr.get("object", owner_id)

                if not owner:
                    owner_ids.remove(owner_id)
                    continue

                m = owner.get_material()

                if not m or m.get_id() != material_id:
                    owner_ids.remove(owner_id)

        force = True if restore else False
        self._material.apply(self, force=force)

        return True

    def replace_material(self, new_material):

        old_material = self._material

        if old_material:
            old_material.remove(self)

        new_material.apply(self)
        self._material = new_material

        return True

    def get_material(self):

        return self._material

    def set_geom_object(self, geom_obj):

        self._geom_obj = geom_obj

    def get_geom_object(self):

        return self._geom_obj

    def get_geom_type(self):

        return self._geom_obj.get_type() if self._geom_obj else ""

    def __restore_geom_object(self, geom_obj, restore_type, old_time_id, new_time_id):

        geom_obj.set_model(self)
        self._geom_obj = geom_obj

        def task():

            selection = Mgr.get("selection", "top")
            selection.update_ui()
            selection.update_obj_props(force=True)

        task_id = "update_type_props"
        PendingTasks.add(task, task_id, "ui")

        geom_obj.restore_data(["self"], restore_type, old_time_id, new_time_id)

    def replace_geom_object(self, geom_obj):

        self._geom_obj.replace(geom_obj)
        geom_obj.set_model(self)
        self._geom_obj = geom_obj

        def task():

            selection = Mgr.get("selection", "top")
            selection.update_ui()
            selection.update_obj_props(force=True)

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

        if prop_id == "material":
            return self.set_material(value, restore)

        if prop_id in TopLevelObject.get_property_ids(self):
            return TopLevelObject.set_property(self, prop_id, value, restore)

        if prop_id in self._geom_obj.get_property_ids() + ["editable state"]:
            return self._geom_obj.set_property(prop_id, value)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "material":
            return self._material

        if prop_id in TopLevelObject.get_property_ids(self):
            return TopLevelObject.get_property(self, prop_id, for_remote_update)

        if prop_id in self._geom_obj.get_property_ids():
            return self._geom_obj.get_property(prop_id, for_remote_update)

    def get_type_property_ids(self):

        return self._geom_obj.get_type_property_ids()

    def get_subobj_selection(self, subobj_lvl):

        return self._geom_obj.get_subobj_selection(subobj_lvl)

    def register(self):

        TopLevelObject.register(self)

        self._bbox.register()

        if self._geom_obj:
            self._geom_obj.register()

    def get_bbox(self):

        return self._bbox

    def get_center_pos(self, ref_node):

        return self._bbox.get_center_pos(ref_node)

    def update_selection_state(self, is_selected=True):

        TopLevelObject.update_selection_state(self, is_selected)

        if not self._bbox:
            return

        if "shaded" in GlobalData["render_mode"]:
            if is_selected:
                self._bbox.show()
            else:
                self._bbox.hide()

        if self._geom_obj:
            self._geom_obj.update_selection_state(is_selected)

    def update_render_mode(self):

        is_selected = self.is_selected()

        if is_selected:
            if "shaded" in GlobalData["render_mode"]:
                self._bbox.show()
            else:
                self._bbox.hide()

        if self._geom_obj:
            self._geom_obj.update_render_mode(is_selected)

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this model.

        """

        self._bbox.flash()


MainObjects.add_class(ModelManager)
