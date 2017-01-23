from .base import *


class EditableGeomManager(BaseObject, ObjPropDefaultsManager):

    def __init__(self):

        self._id_generator = id_generator()
        Mgr.accept("create_editable_geom", self.__create)

    def __create(self, model=None, geom_data_obj=None, name="", origin_pos=None):

        if not model:
            pos = Point3() if origin_pos is None else origin_pos
            model_id = ("editable_geom",) + self._id_generator.next()
            model = Mgr.do("create_model", model_id, name, pos)

        obj = EditableGeom(model, geom_data_obj)

        return obj


class EditableGeom(GeomDataOwner):

    def __init__(self, model, geom_data_obj):

        data_obj = geom_data_obj if geom_data_obj else Mgr.do("create_geom_data", self)
        GeomDataOwner.__init__(self, [], [], model, data_obj)
        model.set_geom_object(self)

        self._type = "editable_geom"

    def create(self, geom_data_obj=None, gradual=False):

        if geom_data_obj:
            self.set_geom_data_object(geom_data_obj)
            data_obj = geom_data_obj
        else:
            data_obj = self.get_geom_data_object()

        for step in data_obj.create_geometry(self._type, gradual=gradual):
            if gradual:
                yield True

        for step in data_obj.finalize_geometry():
            if gradual:
                yield True

        yield False

    def is_valid(self):

        return False

    def get_type(self):

        return self._type

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
        self.set_property(prop_id, val, restore_type)

        if prop_id == "geom_data":
            val.restore_data(["self"], restore_type, old_time_id, new_time_id)


MainObjects.add_class(EditableGeomManager)
