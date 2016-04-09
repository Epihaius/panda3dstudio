from .base import *
from .mgr import CoreManager as Mgr


class TopLevelObject(BaseObject):

    def __init__(self, obj_type, obj_id, name, origin_pos, has_color=True):

        self._prop_ids = ["name", "parent", "selection_state", "tags",
                          "transform", "origin_transform"]

        if has_color:
            self._prop_ids += ["color", "material"]

        self._type = obj_type
        self._id = obj_id
        self._name = name
        self._parent_id = None
        self._child_ids = []
        obj_root = Mgr.get("object_root")
        pivot = obj_root.attach_new_node("%s_pivot" % str(obj_id))
        self._pivot = pivot
        self._origin = pivot.attach_new_node("%s_origin" % str(obj_id))
        self._has_color = has_color
        self._vert_colors_shown = False
        self._color = None
        self._material = None

        active_grid_plane = Mgr.get(("grid", "plane"))
        grid_origin = Mgr.get(("grid", "origin"))

        if active_grid_plane == "xz":
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., 0., 90.))
        else:
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., 0., 0.))

        self._pivot_gizmo = Mgr.do("create_pivot_gizmo", self)

    def destroy(self, add_to_hist=True):

        if not self._origin:
            return False

        if add_to_hist:

            obj_data = {}
            event_data = {"objects": obj_data}

            for child_id in self._child_ids[:]:
                child = Mgr.get("object", child_id)
                obj_data[child_id] = child.get_data_to_store("deletion")
                child.destroy(add_to_hist)

            if obj_data:
                Mgr.do("add_history", "", event_data, update_time_id=False)

        self.set_parent(add_to_hist=False)

        if self._material:
            self._material.remove(self)

        self.set_name("")
        self._pivot_gizmo.destroy()
        self._pivot_gizmo = None
        self._origin.remove_node()
        self._origin = None
        self._pivot.remove_node()
        self._pivot = None

        Mgr.do("unregister_%s" % self._type, self)

        task = lambda: self.__update_app(add_to_hist)
        task_id = "object_removal"
        PendingTasks.add(task, task_id, "object", id_prefix=self._id)
        task = lambda: self.set_selected(False, False)
        task_id = "update_selection"
        PendingTasks.add(task, task_id, "object", id_prefix=self._id)
        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        return True

    def __update_app(self, add_to_hist=True):

        cs_type = Mgr.get_global("coord_sys_type")
        tc_type = Mgr.get_global("transf_center_type")

        if cs_type == "object" and self is Mgr.get("coord_sys_obj"):
            Mgr.update_app("coord_sys", "world")

        if tc_type == "object" and self is Mgr.get("transf_center_obj"):
            Mgr.update_app("transf_center", "sel_center")

        Mgr.update_app("object_removal", self._id, add_to_hist)
        Mgr.do("update_obj_transf_info", self._id)

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
        self._pivot_gizmo.register()

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this one.

        Override in derived class.

        """

        pass

    def set_parent(self, parent_id=None, add_to_hist=True):

        parent = Mgr.get("object", parent_id) if parent_id else None

        if add_to_hist:

            if self._parent_id == parent_id or parent in self.get_descendants():
                return False

            if parent:

                if Mgr.get_global("transform_target_type") == "all":
                    self._pivot.wrt_reparent_to(parent.get_pivot())

                parent.add_child(self._id)

            else:

                self._pivot.wrt_reparent_to(Mgr.get("object_root"))

        else:

            if parent in self.get_descendants():
                if parent:
                    parent.set_parent(add_to_hist=False)

            if parent:

                parent.add_child(self._id)

                if Mgr.get_global("transform_target_type") == "all":
                    self._pivot.reparent_to(parent.get_pivot())
                else:
                    self._pivot.reparent_to(Mgr.get("object_root"))

            else:

                self._pivot.reparent_to(Mgr.get("object_root"))

        if parent:
            Mgr.do("add_obj_link_viz", self, parent)
        elif self._parent_id:
            Mgr.do("remove_obj_link_viz", self._id)

        if self._parent_id and self._parent_id != parent_id:

            prev_parent = Mgr.get("object", self._parent_id)

            if prev_parent:
                prev_parent.remove_child(self._id)

        self._parent_id = parent_id

        if add_to_hist:

            Mgr.do("update_history_time")
            data = self.get_data_to_store("prop_change", "parent")
            data.update(self.get_data_to_store("prop_change", "transform"))
            obj_data = {self._id: data}

            if parent:
                event_descr = 'Link "%s"\nto "%s"' % (self.get_name(), parent.get_name())
            else:
                event_descr = 'Unlink "%s"' % self.get_name()

            event_data = {"objects": obj_data}
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        return True

    def get_parent(self):

        return Mgr.get("object", self._parent_id)

    def get_parent_origin(self):

        return self.get_parent().get_origin() if self._parent_id else Mgr.get("object_root")

    def get_parent_pivot(self):

        return self.get_parent().get_pivot() if self._parent_id else Mgr.get("object_root")

    def get_root(self):

        node = self
        parent = self.get_parent()

        while parent:
            node = parent
            parent = node.get_parent()

        return node

    def get_ancestors(self):

        ancestors = []
        ancestor = self.get_parent()

        while ancestor:
            ancestors.append(ancestor)
            ancestor = ancestor.get_parent()

        return ancestors

    def add_child(self, child_id):

        if child_id not in self._child_ids:
            self._child_ids.append(child_id)

    def get_children(self):

        return [Mgr.get("object", child_id) for child_id in self._child_ids]

    def get_descendants(self):

        descendants = []
        children = self.get_children()
        descendants.extend(children)

        for child in children:
            descendants.extend(child.get_descendants())

        return descendants

    def remove_child(self, child_id):

        if child_id in self._child_ids:
            self._child_ids.remove(child_id)

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

    def get_pivot(self):

        return self._pivot

    def get_pivot_gizmo(self):

        return self._pivot_gizmo

    def set_color(self, color, update_app=True):

        if not self._has_color or self._color == color:
            return False

        self._color = color

        if not self._vert_colors_shown:
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

    def update_selection_state(self, is_selected=True):
        """
        Visually indicate that this object has been (de)selected.

        """

        if self._pivot_gizmo:
            self._pivot_gizmo.update_selection_state(is_selected)

    def get_transform_values(self):

        transform = {}

        if Mgr.get_global("coord_sys_type") == "local":
            transform["translate"] = (0., 0., 0.)
            transform["rotate"] = (0., 0., 0.)
            transform["scale"] = (1., 1., 1.)
        else:
            grid_origin = Mgr.get(("grid", "origin"))
            pivot = self._pivot
            x, y, z = pivot.get_pos(grid_origin)
            h, p, r = pivot.get_hpr(grid_origin)
            sx, sy, sz = pivot.get_scale(grid_origin)
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

        elif prop_id == "parent":

            if restore:
                task = lambda: self.set_parent(value, add_to_hist)
                task_id = "object_linking"
                PendingTasks.add(task, task_id, "object", id_prefix=self._id)
            else:
                self.set_parent(value)

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

            task = lambda: self._pivot.set_mat(self.get_parent_pivot(), value)
            Mgr.do("add_transf_to_restore", "pivot", self, task)
            Mgr.do("restore_transforms")
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

            transform_types = ["translate", "rotate", "scale"]
            Mgr.do("update_obj_transf_info", self._id, transform_types)
            Mgr.do("update_obj_link_viz")
            Mgr.do("reset_obj_transf_info")

            if Mgr.get("coord_sys_obj") is self:

                def update_coord_sys():

                    Mgr.do("notify_coord_sys_transformed")
                    Mgr.do("update_coord_sys")

                task_id = "coord_sys_update"
                PendingTasks.add(update_coord_sys, task_id, "ui")

            if Mgr.get("transf_center_obj") is self:
                task = lambda: Mgr.do("set_transf_gizmo_pos", self._pivot.get_pos(self.world))
                task_id = "transf_center_update"
                PendingTasks.add(task, task_id, "ui")

        elif prop_id == "origin_transform":

            task = lambda: self._origin.set_mat(self._pivot, value)
            Mgr.do("add_transf_to_restore", "origin", self, task)
            Mgr.do("restore_transforms")
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

        elif prop_id == "tags":

            self.set_tags(value)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "name":
            return self._name
        elif prop_id == "parent":
            return self._parent_id
        elif prop_id == "color":
            return self._color
        elif prop_id == "material":
            return self._material
        elif prop_id == "selection_state":
            return self.is_selected()
        elif prop_id == "transform":
            return self._pivot.get_mat(self.get_parent_pivot())
        elif prop_id == "origin_transform":
            return self._origin.get_mat(self._pivot)
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

        obj_id = self._id

        if "self" in data_ids:

            self.register()

            for prop_id in self.get_property_ids():
                val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                self.set_property(prop_id, val, restore_type)

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                    self.set_property(prop_id, val, restore_type)
                    data_ids.remove(prop_id)
