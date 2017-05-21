from .base import *


class EditableGeom(GeomDataOwner):

    def __init__(self, model, geom_data_obj, has_vert_colors):

        data_obj = geom_data_obj if geom_data_obj else Mgr.do("create_geom_data", self)
        GeomDataOwner.__init__(self, [], [], model, data_obj, has_vert_colors)
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

        data_obj.finalize_geometry()
        data_obj.update_poly_centers()

        yield False

    def is_valid(self):

        return False

    def get_type(self):

        return self._type

    def get_property_to_store(self, prop_id, event_type=""):

        data = {prop_id: {"main": self.get_property(prop_id)}}

        return data

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
        self.set_property(prop_id, val, restore_type)

        if prop_id == "geom_data":
            val.restore_data(["self"], restore_type, old_time_id, new_time_id)

    def set_normal_length(self, normal_length):

        return self.get_geom_data_object().set_normal_length(normal_length)


class EditableGeomManager(BaseObject, ObjPropDefaultsManager):

    def __init__(self):

        self._id_generator = id_generator()
        Mgr.accept("create_editable_geom", self.__create)
        Mgr.add_app_updater("geometry_access", self.__make_geometry_editable)

    def __create(self, model=None, geom_data_obj=None, name="", origin_pos=None,
                 has_vert_colors=False):

        if not model:
            pos = Point3() if origin_pos is None else origin_pos
            model_id = ("editable_geom",) + self._id_generator.next()
            model = Mgr.do("create_model", model_id, name, pos)

        obj = EditableGeom(model, geom_data_obj, has_vert_colors)

        return obj

    def __make_geometry_editable(self):

        selection = Mgr.get("selection", "top")

        Mgr.do("update_history_time")
        obj_data = {}

        for obj in selection:
            obj.get_geom_object().make_geometry_editable()
            geom_obj = obj.get_geom_object()
            data = {"geom_obj": {"main": geom_obj}}
            geom_data_obj = geom_obj.get_geom_data_object()
            geom_data_obj.init_normal_length()
            data.update(geom_data_obj.get_property_to_store("normal_length"))
            obj_data[obj.get_id()] = data

        if len(selection) == 1:
            obj = selection[0]
            event_descr = 'Access geometry of "%s"' % obj.get_name()
        else:
            event_descr = 'Access geometry of objects:\n'
            event_descr += "".join(['\n    "%s"' % obj.get_name() for obj in selection])

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(EditableGeomManager)
