from .base import *


class EditableGeom(GeomDataOwner):

    def __getstate__(self):

        state = GeomDataOwner.__getstate__(self)

        state["_type"] = state.pop("type")

        return state

    def __setstate__(self, state):

        GeomDataOwner.__setstate__(self, state)

        state["type"] = state.pop("_type")

    def __init__(self, model, geom_data_obj, has_vert_colors):

        data_obj = geom_data_obj if geom_data_obj else Mgr.do("create_geom_data", self)
        GeomDataOwner.__init__(self, [], [], model, data_obj, has_vert_colors)
        model.geom_obj = self

        self.type = "editable_geom"

    def create(self, geom_data_obj=None, gradual=False):

        if geom_data_obj:
            self.geom_data_obj = geom_data_obj
            data_obj = geom_data_obj
        else:
            data_obj = self.geom_data_obj

        for step in data_obj.create_geometry(self.type, gradual=gradual):
            if gradual:
                yield True

        data_obj.finalize_geometry()
        data_obj.update_poly_centers()

        yield False

    def is_valid(self):

        return False

    def get_property_to_store(self, prop_id, event_type=""):

        data = {prop_id: {"main": self.get_property(prop_id)}}

        return data

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.toplevel_obj.id
        val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
        self.set_property(prop_id, val, restore_type)

        if prop_id == "geom_data":
            val.restore_data(["self"], restore_type, old_time_id, new_time_id)

    def set_normal_length(self, normal_length, state="done"):

        return self.geom_data_obj.set_normal_length(normal_length, state)

    def get_initial_vertex_colors(self):

        return self.geom_data_obj.get_initial_vertex_colors()


class EditableGeomManager(ObjPropDefaultsManager):

    def __init__(self):

        self._id_generator = id_generator()
        Mgr.accept("create_editable_geom", self.__create)
        Mgr.add_app_updater("geometry_access", self.__unlock_geometry)

    def __create(self, model, geom_data_obj=None, has_vert_colors=False):

        return EditableGeom(model, geom_data_obj, has_vert_colors)

    def __unlock_primitive_geometry(self, models):

        for model in models:
            geom_obj = model.geom_obj
            geom_data_obj = geom_obj.geom_data_obj
            editable_geom = self.__create(model, geom_data_obj)
            editable_geom.set_flipped_normals(geom_obj.has_flipped_normals())
            geom_data_obj.init_normal_length()

        Mgr.update_remotely("selected_obj_types", ("editable_geom",))

    def __add_to_history(self, models1, models2):

        Mgr.do("update_history_time")
        obj_data = {}

        for model in models1:
            data = model.geom_obj.get_data_to_store("creation")
            obj_data[model.id] = data

        for model in models2:
            geom_obj = model.geom_obj
            data = {"geom_obj": {"main": geom_obj}}
            geom_data_obj = geom_obj.geom_data_obj
            data.update(geom_data_obj.get_property_to_store("normal_length"))
            obj_data[model.id] = data

        models = models1 + models2

        if len(models) == 1:
            model = models[0]
            event_descr = f'Access geometry of "{model.name}"'
        else:
            event_descr = 'Access geometry of objects:\n'
            event_descr += "".join([f'\n    "{model.name}"' for model in models])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __unlock_geometry(self):

        selection = Mgr.get("selection_top")
        models1 = []
        models2 = []

        for model in selection:
            models = models1 if model.geom_type == "basic_geom" else models2
            models.append(model)

        for model in models1:
            geom_obj = model.geom_obj
            editable_geom = self.__create(model, has_vert_colors=True)
            geom_obj.unlock_geometry(editable_geom)

        get_task = lambda models: lambda: self.__unlock_primitive_geometry(models)
        task = get_task(models2)
        PendingTasks.add(task, "unlock_prim_geometry", "object", 99)

        get_task = lambda models1, models2: lambda: self.__add_to_history(models1, models2)
        task = get_task(models1, models2)
        PendingTasks.add(task, "add_history", "object", 100)


MainObjects.add_class(EditableGeomManager)
