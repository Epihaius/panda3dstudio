from ..data import *


class PrimitiveManager(BaseObject, CreationPhaseManager, ObjPropDefaultsManager):

    def __init__(self, prim_type):

        CreationPhaseManager.__init__(self, prim_type, has_color=True)
        ObjPropDefaultsManager.__init__(self, prim_type)

    def setup(self, creation_phases, status_text):

        sort = PendingTasks.get_sort("clear_geom_data", "object")

        if sort is None:
            PendingTasks.add_task_id("clear_geom_data", "object", 1)
            PendingTasks.add_task_id("set_geom_data", "object", 2)
            PendingTasks.add_task_id("make_editable", "object", 3)

        phase_starter, phase_handler = creation_phases.pop(0)
        creation_starter = self.__get_prim_creation_starter(phase_starter)
        creation_phases.insert(0, (creation_starter, phase_handler))

        return CreationPhaseManager.setup(self, creation_phases, status_text)

    def __get_prim_creation_starter(self, main_creation_func):

        def start_primitive_creation():

            model_id = self.generate_object_id()
            name = Mgr.get("next_obj_name", self.get_object_type())
            model = Mgr.do("create_model", model_id, name, self.get_origin_pos())
            next_color = self.get_next_object_color()
            model.set_color(next_color, update_app=False)
            prim = self.init_primitive(model)
            self.init_object(prim)
            model.set_geom_object(prim)

            main_creation_func()

        return start_primitive_creation

    def get_primitive(self):

        return self.get_object()

    def init_primitive(self, model):
        """ Override in derived class """

        return None

    def apply_default_size(self, prim):
        """ Override in derived class """

        pass

    def create_instantly(self, origin_pos):

        model_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        model = Mgr.do("create_model", model_id, name, origin_pos)
        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        prim = self.init_primitive(model)
        self.apply_default_size(prim)
        prim.get_geom_data_object().finalize_geometry()
        model.set_geom_object(prim)
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        self.set_next_object_color()
        # make undo/redoable
        self.add_history(model)


class Primitive(BaseObject):

    def __getstate__(self):

        # When pickling a Primitive, it should not have a model or a geom_data_obj,
        # since these are pickled separately.

        d = self.__dict__.copy()
        d["_model"] = None
        d["_geom_data_obj"] = None

        return d

    def __init__(self, prim_type, model, type_prop_ids):

        self._type = prim_type
        self._type_prop_ids = type_prop_ids
        self._prop_ids = []
        self._model = model
        self._geom_data_obj = None
        # the following "initial position data" corresponds to the vertex positions
        # at the time the geometry is created or recreated; it is kept around to
        # facilitate resizing of the primitive, when "baking" the transform of the
        # origin into the vertices
        # (the alternative would be to first apply an inverse transformation to get
        # the original positions back, but this could lead to math errors)
        self._init_pos_data = None

    def define_geom_data(self):
        """
        Define the geometry of the primitive; the vertex properties and how those
        vertices are combined into triangles and polygons.

        Override in derived class.

        """

        pass

    def update(self, data):
        """
        Update the primitive with the given data.

        Override in derived class.

        """

        pass

    def create(self):

        self._geom_data_obj = geom_data_obj = GeomDataObject(self)
        geom_data = self.define_geom_data()
        data = geom_data_obj.process_geom_data(geom_data)
        self.update(data)
        geom_data_obj.create_geometry(self._type)

    def destroy(self):

        self._geom_data_obj.destroy()
        self._geom_data_obj = None

    def clear_geometry(self):

        self._geom_data_obj.clear_subobjects()

    def recreate_geometry(self):

        Mgr.do("update_picking_col_id_ranges")
        geom_data_obj = self._geom_data_obj
        geom_data = self.define_geom_data()
        data = geom_data_obj.process_geom_data(geom_data)
        self.update(data)
        geom_data_obj.create_subobjects(rebuild=True)
        self.update_init_pos_data()
        self.finalize()

    def is_valid(self):

        return False

    def get_type(self):

        return self._type

    def set_geom_data_object(self, geom_data_obj):

        self._geom_data_obj = geom_data_obj

    def get_geom_data_object(self):

        return self._geom_data_obj

    def update_init_pos_data(self):

        self._init_pos_data = self._geom_data_obj.get_position_data()

    def reset_init_pos_data(self):

        self._geom_data_obj.set_position_data(self._init_pos_data)

    def restore_init_pos_data(self, pos_data):

        self._init_pos_data = pos_data

    def get_init_pos_data(self):

        return self._init_pos_data

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

    def finalize(self, update_poly_centers=True):

        self._geom_data_obj.finalize_geometry(update_poly_centers)

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["geom_obj"] = {"main": self}
            prop_ids = self.get_property_ids()

            for prop_id in prop_ids:
                data[prop_id] = {"main": self.get_property(prop_id)}

        elif event_type == "prop_change" and prop_id in self.get_property_ids():

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

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "editable state":

            obj_type = "editable_geom"
            Mgr.do("create_%s" % obj_type, self._model, self._geom_data_obj)
            Mgr.update_remotely("selected_obj_type", obj_type)

            return True

        else:

            return self._geom_data_obj.set_property(prop_id, value, restore)

    def get_property_ids(self):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids
