from ..base import *
import random


class Model(TopLevelObject):

    def __getstate__(self):

        state = TopLevelObject.__getstate__(self)

        state["_geom_obj"] = None
        state["_color"] = None
        state["_material"] = None
        del state["geom_obj"]
        state["_bbox"] = state.pop("bbox")

        return state

    def __setstate__(self, state):

        TopLevelObject.__setstate__(self, state)

        state["geom_obj"] = state.pop("_geom_obj")
        state["bbox"] = state.pop("_bbox")
        self.bbox.origin.reparent_to(self.origin)
        self.bbox.origin.hide()

        if GD["two_sided"]:
            self.origin.set_two_sided(True)

    def __init__(self, model_id, name, origin_pos, bbox_color):

        TopLevelObject.__init__(self, "model", model_id, name, origin_pos, has_color=True)

        self.get_property_ids().extend(["color", "material", "tangent_flip", "bitangent_flip"])
        self._color = None
        self._material = None
        self.geom_obj = None
        self._has_tangent_space = False
        self._tangent_flip = False
        self._bitangent_flip = False

        self.bbox = Mgr.do("create_bbox", self, bbox_color)
        self.bbox.hide()

        if GD["two_sided"]:
            self.origin.set_two_sided(True)

        id_str = str(self.id)
        handler = lambda info: self.cancel_creation() if info == "creation" else None
        Mgr.add_notification_handler("long_process_cancelled", id_str, handler, once=True)
        task = lambda: Mgr.remove_notification_handler("long_process_cancelled", id_str)
        task_id = "remove_notification_handler"
        PendingTasks.add(task, task_id, "object", id_prefix=id_str, sort=100)

    def __del__(self):

        Notifiers.obj.info(f'Model "{self.id}" garbage-collected.')

    def cancel_creation(self):

        TopLevelObject.cancel_creation(self)

        if self.geom_obj:
            self.geom_obj.cancel_creation()
            self.geom_obj = None

        self.bbox.destroy(unregister=False)
        self.bbox = None

    def destroy(self, unregister=True, add_to_hist=True):

        if not TopLevelObject.destroy(self, unregister, add_to_hist):
            return

        if self._material:
            self._material.remove(self)

        self.geom_obj.destroy(unregister)
        self.geom_obj.model = None
        self.geom_obj = None
        self.bbox.destroy(unregister)
        self.bbox = None

    def register(self, restore=True):

        TopLevelObject.register(self)

        self.bbox.register(restore)

        if self.geom_obj:
            self.geom_obj.register(restore)

    @property
    def geom_type(self):

        return self.geom_obj.type if self.geom_obj else ""

    def set_color(self, color, update_app=True):

        if self._color == color:
            return False

        self._color = color

        if not self._material:
            self.origin.set_color(color)

        if not self.is_selected() and self.geom_obj:
            self.geom_obj.set_wireframe_color(color)

        if update_app:

            sel_colors = tuple(set(obj.get_color() for obj in Mgr.get("selection")
                                   if obj.has_color()))
            sel_color_count = len(sel_colors)

            if sel_color_count == 1:
                color = sel_colors[0]
                color_values = [x for x in color][:3]
                Mgr.update_remotely("selected_obj_color", color_values)

            GD["sel_color_count"] = sel_color_count
            Mgr.update_app("sel_color_count")

        return True

    def get_color(self):

        return (1., 1., 1., 1.) if self._color is None else self._color

    def set_two_sided(self, two_sided=True):

        if two_sided:
            self.origin.set_two_sided(True)
        else:
            self.origin.clear_two_sided()

    def make_pickable(self, mask_index, pickable=True):

        self.geom_obj.make_pickable(mask_index, pickable)

    def set_material(self, material, restore=""):

        old_material = self._material

        if old_material is material:
            return False

        if old_material:
            old_material.remove(self)

        if not material:
            self._material = material
            return True

        material_id = material.id
        registered_material = Mgr.get("material", material_id)

        if registered_material:
            self._material = registered_material
        else:
            self._material = material
            Mgr.do("register_material", material)

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

    def __restore_geom_object(self, geom_obj, restore_type, old_time_id, new_time_id):

        geom_obj.model = self
        self.geom_obj = geom_obj

        def task():

            selection = Mgr.get("selection_top")
            selection.update_ui()
            selection.update_obj_props(force=True)

        task_id = "update_type_props"
        PendingTasks.add(task, task_id, "ui")

        geom_obj.restore_data(["self"], restore_type, old_time_id, new_time_id)

    def replace_geom_object(self, geom_obj):

        old_geom_obj, self.geom_obj = self.geom_obj, geom_obj
        geom_obj.model = self

        if old_geom_obj.type == "basic_geom":
            old_geom_obj.destroy()
        else:
            old_geom_obj.replace(geom_obj)

        color = (.7, .7, 1., 1.) if geom_obj.type == "basic_geom" else (1., 1., 1., 1.)
        self.bbox.color = color

        if geom_obj.type == "basic_geom":

            if self._has_tangent_space:
                geom_obj.init_tangent_space()

            if self._material:
                self._material.apply(self, force=True)

        def task():

            selection = Mgr.get("selection_top")
            selection.update_ui()
            selection.update_obj_props(force=True)

        task_id = "update_type_props"
        PendingTasks.add(task, task_id, "ui")

    def get_data_to_store(self, event_type, prop_id=""):

        data = TopLevelObject.get_data_to_store(self, event_type, prop_id)
        data.update(self.geom_obj.get_data_to_store(event_type, prop_id))

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        TopLevelObject.restore_data(self, data_ids, restore_type, old_time_id, new_time_id)
        obj_id = self.id

        if "self" in data_ids:

            geom_obj = Mgr.do("load_last_from_history", obj_id, "geom_obj", new_time_id)
            self.__restore_geom_object(geom_obj, restore_type, old_time_id, new_time_id)
            color = (.7, .7, 1., 1.) if geom_obj.type == "basic_geom" else (1., 1., 1., 1.)
            self.bbox.color = color

        else:

            if "geom_obj" in data_ids:

                geom_obj = Mgr.do("load_last_from_history", obj_id, "geom_obj", new_time_id)
                self.replace_geom_object(geom_obj)
                prop_ids = geom_obj.get_property_ids()[:]

                if "geom_data" in prop_ids:
                    prop_ids.remove("geom_data")

                for prop_id in prop_ids[:]:
                    if prop_id in data_ids:
                        prop_ids.remove(prop_id)

                geom_obj.restore_data(prop_ids, restore_type, old_time_id, new_time_id)

            if data_ids:
                self.geom_obj.restore_data(data_ids, restore_type, old_time_id, new_time_id)

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "color":
            update = True if restore else False
            return self.set_color(value, update_app=update)
        elif prop_id == "material":
            if restore:
                task = lambda: self.set_material(value, restore)
                task_id = "set_material"
                PendingTasks.add(task, task_id, "object", id_prefix=self.id)
            else:
                return self.set_material(value, restore)
        elif prop_id == "tangent_flip":
            change = self.set_tangent_flip(value)
            if change:
                if restore:
                    Mgr.update_remotely("selected_obj_prop", self.geom_type, prop_id, value)
                    task = lambda: self.update_tangent_space()
                    task_id = "update_tangent_space"
                    PendingTasks.add(task, task_id, "object", id_prefix=self.id)
                else:
                    self.update_tangent_space()
            return change
        elif prop_id == "bitangent_flip":
            change = self.set_bitangent_flip(value)
            if change:
                if restore:
                    Mgr.update_remotely("selected_obj_prop", self.geom_type, prop_id, value)
                    task = lambda: self.update_tangent_space()
                    task_id = "update_tangent_space"
                    PendingTasks.add(task, task_id, "object", id_prefix=self.id)
                else:
                    self.update_tangent_space()
            return change
        elif prop_id in TopLevelObject.get_property_ids(self):
            return TopLevelObject.set_property(self, prop_id, value, restore)
        elif prop_id in self.geom_obj.get_property_ids():
            return self.geom_obj.set_property(prop_id, value)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "color":
            return self._color
        elif prop_id == "material":
            return self._material
        elif prop_id == "tangent_flip":
            return self._tangent_flip
        elif prop_id == "bitangent_flip":
            return self._bitangent_flip
        elif prop_id in TopLevelObject.get_property_ids(self):
            return TopLevelObject.get_property(self, prop_id, for_remote_update)

        return self.geom_obj.get_property(prop_id, for_remote_update)

    def get_type_property_ids(self):

        return self.geom_obj.get_type_property_ids() + ["tangent_flip", "bitangent_flip"]

    def get_subobj_selection(self, subobj_lvl):

        return self.geom_obj.get_subobj_selection(subobj_lvl)

    def get_center_pos(self, ref_node):

        return self.bbox.get_center_pos(ref_node)

    def update_selection_state(self, is_selected=True):

        TopLevelObject.update_selection_state(self, is_selected)

        if not self.bbox:
            return

        if "shaded" in GD["render_mode"]:
            if is_selected:
                self.bbox.show()
            else:
                self.bbox.hide()
        else:
            self.bbox.hide()

        if self.geom_obj:
            self.geom_obj.update_selection_state(is_selected)

    def update_render_mode(self):

        is_selected = self.is_selected()

        if is_selected:
            if "shaded" in GD["render_mode"]:
                self.bbox.show()
            else:
                self.bbox.hide()

        if self.geom_obj:
            self.geom_obj.update_render_mode(is_selected)

    def clear_tangent_space(self):

        self._has_tangent_space = False

    def has_tangent_space(self):

        return self._has_tangent_space

    def set_tangent_flip(self, flip=True):

        if self._tangent_flip == flip:
            return False

        self._tangent_flip = flip

        return True

    def set_bitangent_flip(self, flip=True):

        if self._bitangent_flip == flip:
            return False

        self._bitangent_flip = flip

        return True

    def get_tangent_space_flip(self):

        return self._tangent_flip, self._bitangent_flip

    def update_tangent_space(self):

        if self.geom_obj:
            self.geom_obj.update_tangent_space(self._tangent_flip, self._bitangent_flip)

        self._has_tangent_space = True

        return True

    def init_tangent_space(self):

        if self.geom_obj:
            self.geom_obj.init_tangent_space()
            self._has_tangent_space = True

    def is_tangent_space_initialized(self):

        if self.geom_obj:
            return self.geom_obj.is_tangent_space_initialized()

        return False

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this model.

        """

        self.bbox.flash()


class ModelManager(ObjectManager):

    def __init__(self):

        ObjectManager.__init__(self, "model", self.__create_model)

        GD.set_default("two_sided", False)
        updater = lambda flip: self.__set_tangent_space_vector_flip("tangent", flip)
        Mgr.add_app_updater("tangent_flip", updater)
        updater = lambda flip: self.__set_tangent_space_vector_flip("bitangent", flip)
        Mgr.add_app_updater("bitangent_flip", updater)

    def __create_model(self, model_id, name, origin_pos, bbox_color=(1., 1., 1., 1.)):

        model = Model(model_id, name, origin_pos, bbox_color)

        return model

    def __set_tangent_space_vector_flip(self, vector_type, flip):

        selection = Mgr.get("selection_top")
        changed_objs = []
        prop_id = f"{vector_type}_flip"

        for obj in selection:
            if obj.set_property(prop_id, flip):
                changed_objs.append(obj)

        if not changed_objs:
            return

        Mgr.do("update_history_time")
        obj_data = {}
        prop_data = {prop_id: {"main": flip}}

        for obj in changed_objs:
            obj_data[obj.id] = prop_data

        if len(changed_objs) == 1:
            obj = changed_objs[0]
            event_descr = f'{"Flip" if flip else "Unflip"} {vector_type} vectors of "{obj.name}"'
        else:
            event_descr = f'{"Flip" if flip else "Unflip"} {vector_type} vectors of objects:\n'
            event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(ModelManager)
