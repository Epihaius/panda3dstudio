from ..base import *


class GeomDataOwner(BaseObject):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_model"] = None
        state["_geom_data_obj"] = None
        state["_normals_flipped"] = False

        return state

    def __init__(self, prop_ids, type_prop_ids, model, geom_data_obj=None, has_vert_colors=False):

        self._prop_ids = prop_ids + ["geom_data"]
        self._type_prop_ids = type_prop_ids + ["normal_flip"]
        self._model = model
        self._geom_data_obj = geom_data_obj
        self._geom_data_backup = None
        # the following refers to the vertex colors of imported geometry
        self._has_vert_colors = has_vert_colors
        self._normals_flipped = False
        model.set_geom_object(self)

        if geom_data_obj:
            geom_data_obj.set_owner(self)

    def cancel_creation(self):

        logging.debug('GeomDataOwner creation cancelled.')
        self._model = None

        if self._geom_data_obj:
            self._geom_data_obj.cancel_creation()
            self._geom_data_obj = None

    def destroy(self, unregister=True):

        self._geom_data_obj.destroy(unregister)
        self._geom_data_obj = None

    def register(self, restore=True):

        self._geom_data_obj.register(restore)

    def unregister(self):

        self._geom_data_obj.unregister()

    def get_geom_data_object(self):

        return self._geom_data_obj

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_geom_data_backup(self):

        return self._geom_data_backup

    def set_geom_data_backup(self, geom_data_obj):

        self._geom_data_backup = geom_data_obj

    def remove_geom_data_backup(self):

        if self._geom_data_backup:
            self._geom_data_backup.destroy(unregister=False)
            self._geom_data_backup = None

    def get_toplevel_object(self, get_group=False):

        return self._model.get_toplevel_object(get_group)

    def get_model(self):

        return self._model

    def set_model(self, model):

        self._model = model

    def get_origin(self):

        if self._geom_data_obj:
            return self._geom_data_obj.get_origin()

    def set_origin(self, origin):

        self._geom_data_obj.set_origin(origin)

    def replace(self, other):

        geom_data_obj = self._geom_data_obj

        if other.get_type() == "basic_geom":
            geom_data_obj.destroy()
            other.get_geom().reparent_to(self._model.get_origin())
            other.register()
            other.update_render_mode(self._model.is_selected())
            return

        geom_data_obj.set_owner(other)
        other.set_geom_data_object(geom_data_obj)
        other.set_flipped_normals(self._normals_flipped)

    def get_subobj_selection(self, subobj_lvl):

        return  self._geom_data_obj.get_selection(subobj_lvl)

    def set_wireframe_color(self, color):

        self._geom_data_obj.set_wireframe_color(color)

    def update_selection_state(self, is_selected=True):

        self._geom_data_obj.update_selection_state(is_selected)

    def update_render_mode(self, is_selected):

        self._geom_data_obj.update_render_mode(is_selected)

    def update_tangent_space(self, tangent_flip, bitangent_flip):

        self._geom_data_obj.update_tangent_space(tangent_flip, bitangent_flip)

    def init_tangent_space(self):

        self._geom_data_obj.init_tangent_space()

    def is_tangent_space_initialized(self):

        return self._geom_data_obj.is_tangent_space_initialized()

    def bake_texture(self, texture):

        self._geom_data_obj.bake_texture(texture)

    def has_vertex_colors(self):

        return self._has_vert_colors

    def reset_vertex_colors(self):

        if self._has_vert_colors:
            self._geom_data_obj.set_initial_vertex_colors()
        else:
            self._geom_data_obj.clear_vertex_colors()

    def flip_normals(self, flip=True, restore=""):

        if self._normals_flipped == flip:
            return False

        self._geom_data_obj.flip_normals(flip)
        self._normals_flipped = flip

        return True

    def set_flipped_normals(self, flipped=True):

        self._normals_flipped = flipped

    def has_flipped_normals(self):

        return self._normals_flipped

    def set_two_sided(self, two_sided=True):

        origin = self._model.get_origin()

        if two_sided:
            origin.set_two_sided(True)
        else:
            origin.clear_two_sided()

    def show_subobj_level(self, obj_lvl):

        self._geom_data_obj.show_subobj_level(obj_lvl)

    def show_top_level(self):

        self._geom_data_obj.show_top_level()

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["geom_obj"] = {"main": self}
            prop_ids = self.get_property_ids()
            prop_ids.remove("geom_data")

            for prop_id in prop_ids:
                data.update(self.get_property_to_store(prop_id, event_type))

        elif event_type == "prop_change":

            if prop_id in self.get_property_ids():
                data.update(self.get_property_to_store(prop_id, event_type))

        data.update(self._geom_data_obj.get_data_to_store(event_type, prop_id))

        return data

    def get_property_to_store(self, prop_id, event_type=""):
        """
        Override in derived class.

        """

        data = {}

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()

        if "self" in data_ids:

            for prop_id in self.get_property_ids():
                self.restore_property(prop_id, restore_type, old_time_id, new_time_id)

        else:

            if "geom_data" in data_ids:
                self.restore_property("geom_data", restore_type, old_time_id, new_time_id)

            prop_ids = self.get_property_ids()
            prop_ids.remove("geom_data")

            for prop_id in prop_ids:
                if prop_id in data_ids:
                    self.restore_property(prop_id, restore_type, old_time_id, new_time_id)
                    data_ids.remove(prop_id)

            if data_ids and "geom_data" not in data_ids:
                self._geom_data_obj.restore_data(data_ids, restore_type, old_time_id, new_time_id)

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):
        """
        Override in derived class.

        """

        pass

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "geom_data":

            if self._geom_data_obj:

                if value.get_id() == self._geom_data_obj.get_id():
                    return False

                self._geom_data_obj.destroy()

            self._geom_data_obj = value
            value.get_origin().reparent_to(self._model.get_origin())
            value.set_owner(self)

            if self._normals_flipped:
                value.flip_normals()

            return True

        elif prop_id == "normal_flip":

            Mgr.update_remotely("selected_obj_prop", "basic_geom", prop_id, value)
            return self.flip_normals(value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "normal_flip":
            return self._normals_flipped

        obj_lvl = GlobalData["active_obj_level"]

        return self._geom_data_obj.get_property(prop_id, for_remote_update, obj_lvl)

    def get_property_ids(self, for_hist=False):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        obj_lvl = GlobalData["active_obj_level"]

        return self._type_prop_ids + self._geom_data_obj.get_type_property_ids(obj_lvl)
