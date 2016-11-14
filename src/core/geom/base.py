from ..base import *


class GeomDataOwner(BaseObject):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_model"] = None
        state["_geom_data_obj"] = None

        return state

    def __init__(self, prop_ids, type_prop_ids, model, geom_data_obj=None):

        self._prop_ids = prop_ids
        self._type_prop_ids = type_prop_ids
        self._model = model
        self._geom_data_obj = geom_data_obj

        if geom_data_obj:
            geom_data_obj.set_owner(self)

    def destroy(self):

        self._geom_data_obj.destroy()
        self._geom_data_obj = None

    def get_geom_data_object(self):

        return self._geom_data_obj

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_toplevel_object(self, get_group=False):

        return self._model.get_toplevel_object(get_group)

    def get_model(self):

        return self._model

    def set_model(self, model):

        self._model = model

    def replace(self, geom_obj):

        geom_data_obj = self._geom_data_obj
        geom_data_obj.set_owner(geom_obj)
        geom_obj.set_geom_data_object(geom_data_obj)

    def get_subobj_selection(self, subobj_lvl):

        return  self._geom_data_obj.get_selection(subobj_lvl)

    def set_wireframe_color(self, color):

        self._geom_data_obj.set_wireframe_color(color)

    def update_selection_state(self, is_selected=True):

        self._geom_data_obj.update_selection_state(is_selected)

    def update_render_mode(self, is_selected):

        self._geom_data_obj.update_render_mode(is_selected)

    def update_tangent_space(self, flip_tangent, flip_bitangent):

        self._geom_data_obj.flip_tangent(flip_tangent)
        self._geom_data_obj.flip_bitangent(flip_bitangent)
        self._geom_data_obj.update_tangent_space()

    def is_tangent_space_initialized(self):

        return self._geom_data_obj.is_tangent_space_initialized()

    def bake_texture(self, texture):

        self._geom_data_obj.bake_texture(texture)

    def reset_vertex_colors(self):

        self._geom_data_obj.reset_vertex_colors()

    def set_two_sided(self, two_sided=True):

        self._geom_data_obj.get_origin().set_two_sided(two_sided)

    def show_subobj_level(self, obj_lvl):

        self._geom_data_obj.show_subobj_level(obj_lvl)

    def show_top_level(self):

        self._geom_data_obj.show_top_level()

    def register(self):
        pass

    def unregister(self):

        self._geom_data_obj.unregister()

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["geom_obj"] = {"main": self}
            prop_ids = self.get_property_ids()

            for prop_id in prop_ids:
                data.update(self.get_property_to_store(prop_id, event_type))

        elif event_type == "prop_change":

            if prop_id == "editable state":
                data["geom_obj"] = {"main": self}
            elif prop_id in self.get_property_ids():
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

            geom_data_obj = Mgr.do("load_last_from_history", obj_id, "geom_data", new_time_id)
            self._geom_data_obj = geom_data_obj
            geom_data_obj.get_origin().reparent_to(self._model.get_origin())
            geom_data_obj.set_owner(self)
            geom_data_obj.restore_data(["self"], restore_type, old_time_id, new_time_id)

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    self.restore_property(prop_id, restore_type, old_time_id, new_time_id)
                    data_ids.remove(prop_id)

            if data_ids:
                self._geom_data_obj.restore_data(data_ids, restore_type, old_time_id, new_time_id)

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):
        """
        Override in derived class.

        """

        pass

    def get_property_ids(self, for_hist=False):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids
