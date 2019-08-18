from .mgr import CoreManager as Mgr


class ObjPropDefaultsManager:

    def __init__(self, obj_type):

        self._prop_defaults = {}

        Mgr.add_app_updater(f"{obj_type}_prop_default", self.set_property_default)
        Mgr.expose(f"{obj_type}_prop_defaults", self.get_property_defaults)

    def set_property_default(self, prop_id, value):

        self._prop_defaults[prop_id] = value

    def get_property_defaults(self):

        return self._prop_defaults
