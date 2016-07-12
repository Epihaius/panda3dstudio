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

    def create(self, geom_data_obj=None):

        if geom_data_obj:
            self.set_geom_data_object(geom_data_obj)
            data_obj = geom_data_obj
        else:
            data_obj = self.get_geom_data_object()

        data_obj.create_geometry(self._type)
        data_obj.finalize_geometry()

    def is_valid(self):

        return False

    def get_type(self):

        return self._type


MainObjects.add_class(EditableGeomManager)
