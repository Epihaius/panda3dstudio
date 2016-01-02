from .mgr import CoreManager as Mgr


class ObjPropDefaultsManager(object):

    def __init__(self, obj_type):

        self._prop_defaults = {}

        Mgr.add_app_updater("%s_prop_default" %
                            obj_type, self.set_property_default)
        Mgr.expose("%s_prop_defaults" % obj_type, self.get_property_defaults)

    def set_property_default(self, prop_id, value):

        self._prop_defaults[prop_id] = value

    def get_property_defaults(self):

        return self._prop_defaults
