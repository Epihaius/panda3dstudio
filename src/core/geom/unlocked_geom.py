from ..base import *


class UnlockedGeom:

    def __getstate__(self):

        state = self.__dict__.copy()
        state["model"] = None
        state["geom_data_obj"] = None
        state["_inverted_geometry"] = False

        return state

    def __init__(self, model, has_vert_colors=False):

        self.type = "unlocked_geom"
        self._prop_ids = ["geom_data"]
        self._type_prop_ids = ["inverted_geom"]
        self.model = model
        geom_data_obj = Mgr.do("create_geom_data", self)
        geom_data_obj.owner = self
        self.geom_data_obj = geom_data_obj
        self._geom_data_backup = None
        # the following refers to the vertex colors of imported geometry
        self._has_vert_colors = has_vert_colors
        self._inverted_geometry = False
        model.geom_obj = self

    def create(self, geom_data_obj=None, gradual=False):

        if geom_data_obj:
            self.geom_data_obj = geom_data_obj
            data_obj = geom_data_obj
        else:
            data_obj = self.geom_data_obj

        for _ in data_obj.create_geometry(self.type, gradual=gradual):
            if gradual:
                yield True

        data_obj.finalize_geometry()
        data_obj.update_poly_centers()

        yield False

    def cancel_creation(self):

        Notifiers.geom.debug('UnlockedGeom creation cancelled.')
        self.model = None

        if self.geom_data_obj:
            self.geom_data_obj.cancel_creation()
            self.geom_data_obj = None

    def is_valid(self):

        return False

    def destroy(self, unregister=True):

        self.geom_data_obj.destroy(unregister)
        self.geom_data_obj = None

    def register(self, restore=True):

        self.geom_data_obj.register(restore)

    def unregister(self):

        self.geom_data_obj.unregister()

    def get_geom_data_backup(self):

        return self._geom_data_backup

    def set_geom_data_backup(self, geom_data_obj):

        self._geom_data_backup = geom_data_obj

    def remove_geom_data_backup(self):

        if self._geom_data_backup:
            self._geom_data_backup.destroy(unregister=False)
            self._geom_data_backup = None

    @property
    def origin(self):

        if self.geom_data_obj:
            return self.geom_data_obj.origin

    @origin.setter
    def origin(self, origin):

        self.geom_data_obj.origin = origin

    def get_toplevel_object(self, get_group=False):

        return self.model.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def replace(self, other):

        geom_data_obj = self.geom_data_obj

        if other.type != "unlocked_geom":
            geom_data_obj.destroy()
            other.restore_geom_root()
            other.register()
            other.update_render_mode(self.model.is_selected())
            return

        geom_data_obj.owner = other
        other.geom_data_obj = geom_data_obj
        other.set_inverted_geometry(self._inverted_geometry)

    def get_subobj_selection(self, subobj_lvl):

        return  self.geom_data_obj.get_selection(subobj_lvl)

    def set_wireframe_color(self, color):

        self.geom_data_obj.set_wireframe_color(color)

    def update_selection_state(self, is_selected=True):

        self.geom_data_obj.update_selection_state(is_selected)

    def update_render_mode(self, is_selected):

        self.geom_data_obj.update_render_mode(is_selected)

    def update_tangent_space(self, tangent_flip, bitangent_flip):

        self.geom_data_obj.update_tangent_space(tangent_flip, bitangent_flip)

    def init_tangent_space(self):

        self.geom_data_obj.init_tangent_space()

    @property
    def is_tangent_space_initialized(self):

        return self.geom_data_obj.is_tangent_space_initialized

    def bake_texture(self, texture):

        self.geom_data_obj.bake_texture(texture)

    def get_initial_vertex_colors(self):

        return self.geom_data_obj.get_initial_vertex_colors()

    def has_vertex_colors(self):

        return self._has_vert_colors

    def reset_vertex_colors(self):

        if self._has_vert_colors:
            self.geom_data_obj.set_initial_vertex_colors()
        else:
            self.geom_data_obj.clear_vertex_colors()

    def invert_geometry(self, invert=True, restore=""):

        if self._inverted_geometry == invert:
            return False

        self.geom_data_obj.invert_geometry(invert)
        self._inverted_geometry = invert

        return True

    def set_inverted_geometry(self, inverted=True):

        self._inverted_geometry = inverted

    def has_inverted_geometry(self):

        return self._inverted_geometry

    def make_pickable(self, mask_index, pickable=True):

        render_mode = GD["render_mode"]
        subobj_lvl = "poly" if "shaded" in render_mode else "edge"
        self.geom_data_obj.make_subobjs_pickable(subobj_lvl, mask_index, pickable)

    def show_subobj_level(self, obj_lvl):

        self.geom_data_obj.show_subobj_level(obj_lvl)

    def show_top_level(self):

        self.geom_data_obj.show_top_level()

    def set_normal_length(self, normal_length, state="done"):

        return self.geom_data_obj.set_normal_length(normal_length, state)

    def get_uv_set_names(self):

        return self.geom_data_obj.get_uv_set_names()

    def set_uv_set_names(self, uv_set_names):

        return self.geom_data_obj.set_uv_set_names(uv_set_names)

    def get_subdivision_data(self):

        return self.geom_data_obj.get_subdivision_data()

    def get_property_ids(self, for_hist=False):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        obj_lvl = GD["active_obj_level"]

        return self._type_prop_ids + self.geom_data_obj.get_type_property_ids(obj_lvl)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "inverted_geom":
            return self._inverted_geometry

        obj_lvl = GD["active_obj_level"]

        return self.geom_data_obj.get_property(prop_id, for_remote_update, obj_lvl)

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "geom_data":

            if self.geom_data_obj:

                if value.id == self.geom_data_obj.id:
                    return False

                self.geom_data_obj.destroy()

            self.geom_data_obj = value
            value.origin.reparent_to(self.model.origin)
            value.owner = self

            if self._inverted_geometry:
                value.invert_geometry()

            return True

        elif prop_id == "inverted_geom":

            Mgr.update_remotely("selected_obj_prop", "unlocked_geom", prop_id, value)
            return self.invert_geometry(value, restore)

    def get_property_to_store(self, prop_id, event_type=""):

        data = {prop_id: {"main": self.get_property(prop_id)}}

        return data

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

        data.update(self.geom_data_obj.get_data_to_store(event_type, prop_id))

        return data

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
        self.set_property(prop_id, val, restore_type)

        if prop_id == "geom_data":
            val.restore_data(["self"], restore_type, old_time_id, new_time_id)

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id

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
                self.geom_data_obj.restore_data(data_ids, restore_type, old_time_id, new_time_id)


class UnlockedGeomManager(ObjPropDefaultsManager):

    def __init__(self):

        self._id_generator = id_generator()

        Mgr.accept("create_unlocked_geom", self.__create)
        Mgr.add_app_updater("geometry_access", self.__update_geometry_access)

    def __create(self, model, has_vert_colors=False):

        return UnlockedGeom(model, has_vert_colors)

    def __update_geometry_access(self, access):

        if access:
            self.__unlock_geometry()
        else:
            Mgr.do("lock_geometry")

    def __add_to_history(self, models):

        Mgr.do("update_history_time")
        obj_data = {}

        for model in models:
            data = model.geom_obj.get_data_to_store("creation")
            obj_data[model.id] = data

        if len(models) == 1:
            model = models[0]
            event_descr = f'Enable geometry editing of "{model.name}"'
        else:
            event_descr = 'Enable geometry editing of objects:\n'
            event_descr += "".join([f'\n    "{model.name}"' for model in models])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        Mgr.update_remotely("selected_obj_types", ("unlocked_geom",))

    def __unlock_geometry(self):

        selection = Mgr.get("selection_top")
        models = []

        for model in selection:
            models.append(model)
            geom_obj = model.geom_obj
            has_vert_colors = model.geom_type == "locked_geom"
            unlocked_geom = self.__create(model, has_vert_colors=has_vert_colors)
            geom_obj.unlock_geometry(unlocked_geom)

        get_task = lambda models: lambda: self.__add_to_history(models)
        task = get_task(models)
        PendingTasks.add(task, "add_history", "object", 100)

        task = lambda: Mgr.do("update_picking_col_id_ranges", as_task=False)
        PendingTasks.add(task, "update_picking_col_id_ranges", "object", 101)


MainObjects.add_class(UnlockedGeomManager)
