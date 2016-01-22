from .base import *
from .mgr import CoreManager as Mgr


class TopLevelObject(BaseObject):

    def __init__(self, obj_type, obj_id, name, origin_pos, has_color=True):

        self._prop_ids = ["name", "selection_state", "transform", "tags"]

        if has_color:
            self._prop_ids += ["color", "material"]

        self._type = obj_type
        self._id = obj_id
        self._name = name
        self._origin = Mgr.get("object_root").attach_new_node(
            "%s_origin" % str(obj_id))
        self._has_color = has_color
        self._color = None
        self._material = None

        active_grid_plane = Mgr.get_global("active_grid_plane")
        grid_origin = Mgr.get(("grid", "origin"))

        if active_grid_plane == "XZ":
            self._origin.set_pos_hpr(
                grid_origin, origin_pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "YZ":
            self._origin.set_pos_hpr(
                grid_origin, origin_pos, VBase3(0., 0., 90.))
        else:
            self._origin.set_pos_hpr(
                grid_origin, origin_pos, VBase3(0., 0., 0.))

    def destroy(self, add_to_hist=True):

        if self._material:
            self._material.remove(self)

        self.set_name("")
        self._origin.remove_node()
        self._origin = None

        Mgr.do("unregister_%s" % self._type, self)

        task = lambda: self.__update_app(add_to_hist)
        task_id = "object_removal"
        PendingTasks.add(task, task_id, "object", id_prefix=self._id)
        task = lambda: self.set_selected(False, False)
        task_id = "update_selection"
        PendingTasks.add(task, task_id, "object", id_prefix=self._id)
        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

    def __update_app(self, add_to_hist=True):

        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        if cs_type == "object" and self is Mgr.get("coord_sys_obj"):
            Mgr.update_app("coord_sys", "world")

        if tc_type == "object" and self is Mgr.get("transf_center_obj"):
            Mgr.update_app("transf_center", "sel_center")

        Mgr.update_app("object_removal", self._id, add_to_hist)

    def recreate(self):
        """
        Recreate the object geometry and ID after unpickling during merge.

        Override in derived class.

        """

        pass

    def get_toplevel_object(self):

        return self

    def register(self):

        Mgr.do("register_%s" % self._type, self)

    def get_geom_object(self):

        return None

    def get_type(self):

        return self._type

    def get_id(self):

        return self._id

    def set_name(self, name):

        if self._name == name:
            return False

        self._name = name

        selection = Mgr.get("selection")

        if len(selection) == 1 and selection[0] is self:
            Mgr.update_remotely("selected_obj_name", name)

        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        if cs_type == "object":
            if self is Mgr.get("coord_sys_obj"):
                Mgr.update_remotely("coord_sys", "object", name)

        if tc_type == "object":
            if self is Mgr.get("transf_center_obj"):
                Mgr.update_remotely("transf_center", "object", name)

        return True

    def get_name(self):

        return self._name

    def get_origin(self):

        return self._origin

    def set_color(self, color, update_app=True):

        if not self._has_color or self._color == color:
            return False

        self._color = color
        self._origin.set_color(color)

        if update_app:

            sel_colors = tuple(set([obj.get_color() for obj in Mgr.get("selection")
                                    if obj.has_color()]))
            sel_color_count = len(sel_colors)

            if sel_color_count == 1:
                color = sel_colors[0]
                color_values = [x for x in color][:3]
                Mgr.update_remotely("selected_obj_color", color_values)

            Mgr.set_global("sel_color_count", sel_color_count)
            Mgr.update_app("sel_color_count")

        return True

    def get_color(self):

        return self._color

    def has_color(self):

        return self._has_color

    def set_material(self, material, restore=""):

        old_material = self._material

        if not self._has_color or old_material is material:
            return False

        if old_material:
            old_material.remove(self)

        if not material:

            self._material = material

            return True

        material_id = material.get_id()
        registered_material = Mgr.get("material", material_id)

        if registered_material:

            self._material = registered_material

        else:

            self._material = material
            Mgr.do("register_material", material)
            owner_ids = material.get_owner_ids()

            for owner_id in owner_ids[:]:

                if owner_id == self._id:
                    continue

                owner = Mgr.get("object", owner_id)

                if not owner:
                    owner_ids.remove(owner_id)
                    continue

                m = owner.get_material()

                if not m or m.get_id() != material_id:
                    owner_ids.remove(owner_id)

        force = True if restore else False
        self._material.apply(self, force=force)

        return True

    def replace_material(self, new_material):

        if not self._has_color:
            return False

        old_material = self._material

        if old_material:
            old_material.remove(self)

        new_material.apply(self)
        self._material = new_material

        return True

    def get_material(self):

        return self._material

    def set_selected(self, is_selected=True, add_to_hist=True):

        if is_selected:
            return Mgr.get("selection", "top").add(self, add_to_hist)
        else:
            return Mgr.get("selection", "top").remove(self, add_to_hist)

    def is_selected(self):

        return self in Mgr.get("selection", "top")

    def get_transform_values(self):

        transform = {}

        if Mgr.get_global("coord_sys_type") == "local":
            transform["translate"] = (0., 0., 0.)
            transform["rotate"] = (0., 0., 0.)
            transform["scale"] = (1., 1., 1.)
        else:
            grid_origin = Mgr.get(("grid", "origin"))
            origin = self._origin
            x, y, z = origin.get_pos(grid_origin)
            h, p, r = origin.get_hpr(grid_origin)
            sx, sy, sz = origin.get_scale(grid_origin)
            transform["translate"] = (x, y, z)
            transform["rotate"] = (p, r, h)
            transform["scale"] = (sx, sy, sz)

        return transform

    def set_tags(self, tags):

        orig = self._origin

        for key in orig.get_tag_keys():
            orig.clear_tag(key)

        for key, val in tags.iteritems():
            orig.set_tag(key, val)

    def get_tags(self):

        orig = self._origin
        tags = dict((key, orig.get_tag(key)) for key in orig.get_tag_keys())

        return tags

    def set_property(self, prop_id, value, restore=""):

        add_to_hist = not restore

        if prop_id == "name":

            self.set_name(value)

        elif prop_id == "color":

            update = True if restore else False
            self.set_color(value, update_app=update)

        elif prop_id == "material":

            return self.set_material(value, restore)

        elif prop_id == "selection_state":

            if restore:
                task = lambda: self.set_selected(value, False)
                task_id = "update_selection"
                PendingTasks.add(task, task_id, "object", id_prefix=self._id)
                task = lambda: Mgr.get("selection").update()
                PendingTasks.add(task, "update_selection", "ui")
            else:
                self.set_selected(value, True)

        elif prop_id == "transform":

            self._origin.set_mat(value)
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

            if Mgr.get("coord_sys_obj") is self:
                Mgr.do("notify_coord_sys_transformed")
                Mgr.do("update_coord_sys")

            if Mgr.get("transf_center_obj") is self:
                Mgr.do("set_transf_gizmo_pos",
                       self._origin.get_pos(self.world))

        elif prop_id == "tags":

            self.set_tags(value)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "name":
            return self._name
        elif prop_id == "color":
            return self._color
        elif prop_id == "material":
            return self._material
        elif prop_id == "selection_state":
            return self.is_selected()
        elif prop_id == "transform":
            return self._origin.get_mat()
        elif prop_id == "tags":
            return self.get_tags()

    def get_property_ids(self):

        return self._prop_ids

    def get_type_property_ids(self):
        """
        Retrieve the IDs of the properties that are specific to the particular type
        of this object (e.g. "radius" for a sphere or "labels" for an axis tripod
        helper object), as opposed to the general properties like name, color,
        transform, etc.

        """

        return []

    def get_subobj_selection(self, subobj_lvl):

        return []

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["object"] = {"main": self}
            prop_ids = self.get_property_ids()

            for prop_id in prop_ids:
                data[prop_id] = {"main": self.get_property(prop_id)}

        elif event_type == "deletion":

            data["object"] = None

        elif event_type == "prop_change" and prop_id in self.get_property_ids():

            data[prop_id] = {"main": self.get_property(prop_id)}

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.get_id()

        if "self" in data_ids:

            self.register()

            for prop_id in self.get_property_ids():
                val = Mgr.do("load_last_from_history",
                             obj_id, prop_id, new_time_id)
                self.set_property(prop_id, val, restore_type)

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    val = Mgr.do("load_last_from_history",
                                 obj_id, prop_id, new_time_id)
                    self.set_property(prop_id, val, restore_type)
                    data_ids.remove(prop_id)
