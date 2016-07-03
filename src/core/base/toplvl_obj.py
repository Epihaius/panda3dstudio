from .base import *
from .mgr import CoreManager as Mgr


class TopLevelObject(BaseObject):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_name"] = self._name.get_value()
        state["_pivot"] = NodePath(self._pivot.get_name())
        state["_origin"] = NodePath(self._origin.get_name())

        if self._has_color:
            state["_color"] = None

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        self._name = ObjectName(state["_name"])
        self._name.add_updater("global_obj_names", self.__update_obj_names)
        self._name.update("global_obj_names")
        pivot = self._pivot
        pivot.reparent_to(Mgr.get("object_root"))
        origin = self._origin
        origin.reparent_to(pivot)

    def __init__(self, obj_type, obj_id, name, origin_pos, has_color=False):

        self._prop_ids = ["name", "parent", "selection_state", "tags",
                          "transform", "origin_transform"]

        if has_color:
            self._prop_ids.append("color")
            self._color = None

        self._type = obj_type
        self._id = obj_id
        self._name = ObjectName(name)
        self._name.add_updater("global_obj_names", self.__update_obj_names)
        self._name.update("global_obj_names")
        self._parent_id = None
        self._child_ids = []
        obj_root = Mgr.get("object_root")
        pivot = obj_root.attach_new_node("%s_pivot" % str(obj_id))
        self._pivot = pivot
        self._origin = pivot.attach_new_node("%s_origin" % str(obj_id))
        self._has_color = has_color

        active_grid_plane = Mgr.get(("grid", "plane"))
        grid_origin = Mgr.get(("grid", "origin"))

        if active_grid_plane == "xz":
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., 0., 90.))
        else:
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., 0., 0.))

        self._pivot_gizmo = Mgr.do("create_pivot_gizmo", self)
        self._optimize_for_export = False
        self._optimize_children_for_export = False

    def __update_obj_names(self, name=None):

        obj_names = GlobalData["obj_names"]

        if name is None:

            value = self._name.get_value()

            if value in obj_names:
                obj_names.remove(value)

        elif name not in obj_names:
            obj_names.append(name)

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

        self._name.remove_updater("global_obj_names", final_update=True)
        self.set_name("")
        self._pivot_gizmo.destroy()
        self._pivot_gizmo = None
        self._origin.remove_node()
        self._origin = None
        self._pivot.remove_node()
        self._pivot = None

        Mgr.do("unregister_%s" % self._type, self)

        task = lambda: self.__remove_references(add_to_hist)
        task_id = "object_removal"
        PendingTasks.add(task, task_id, "object", id_prefix=self._id)
        task = lambda: self.set_selected(False, False)
        task_id = "update_selection"
        PendingTasks.add(task, task_id, "object", id_prefix=self._id)
        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        return True

    def __remove_references(self, add_to_hist=True):

        cs_type = GlobalData["coord_sys_type"]
        tc_type = GlobalData["transf_center_type"]

        if Mgr.get("coord_sys_obj") is self:
            Mgr.update_app("coord_sys", "world" if cs_type == "object" else cs_type)

        if Mgr.get("transf_center_obj") is self:
            Mgr.update_app("transf_center", "adaptive" if tc_type == "object" else tc_type)

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

                if GlobalData["transform_target_type"] == "all":
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

                if GlobalData["transform_target_type"] == "all":
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

    def get_child_types(self):

        return [Mgr.get("object", child_id).get_type() for child_id in self._child_ids]

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

    def get_type(self):

        return self._type

    def get_id(self):

        return self._id

    def set_name(self, name):

        if self._name.get_value() == name:
            return False

        self._name.set_value(name)

        selection = Mgr.get("selection")

        if len(selection) == 1 and selection[0] is self:
            Mgr.update_remotely("selected_obj_name", name)

        return True

    def get_name(self, as_object=False):

        return self._name if as_object else self._name.get_value()

    def get_origin(self):

        return self._origin

    def get_pivot(self):

        return self._pivot

    def get_pivot_gizmo(self):

        return self._pivot_gizmo

    def set_color(self, color, update_app=True, apply_color=True):

        if not self._has_color or self._color == color:
            return False

        self._color = color

        if apply_color:
            self._origin.set_color(color)

        if update_app:

            sel_colors = tuple(set([obj.get_color() for obj in Mgr.get("selection")
                                    if obj.has_color()]))
            sel_color_count = len(sel_colors)

            if sel_color_count == 1:
                color = sel_colors[0]
                color_values = [x for x in color][:3]
                Mgr.update_remotely("selected_obj_color", color_values)

            GlobalData["sel_color_count"] = sel_color_count
            Mgr.update_app("sel_color_count")

        return True

    def get_color(self):

        return self._color

    def has_color(self):

        return self._has_color

    def set_selected(self, is_selected=True, add_to_hist=True):

        if is_selected:
            return Mgr.get("selection", "top").add([self], add_to_hist)
        else:
            return Mgr.get("selection", "top").remove([self], add_to_hist)

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

        if GlobalData["coord_sys_type"] == "local":
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

    def set_optimization_for_export(self, optimize=True):

        if self._type == "model":
            self._optimize_for_export = optimize

    def get_optimization_for_export(self):

        return self._optimize_for_export if self._type == "model" else False

    def get_children_optimized_for_export(self):

        return [child for child in self.get_children() if child.get_optimization_for_export()]

    def set_child_optimization_for_export(self, optimize=True):

        self._optimize_children_for_export = optimize

    def get_child_optimization_for_export(self):

        if not self.get_children_optimized_for_export():
            return False

        return self._optimize_children_for_export

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
            return self._name.get_value()
        elif prop_id == "parent":
            return self._parent_id
        elif prop_id == "color":
            return self._color
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
        of this object (e.g. "radius" for a sphere or "cross_size" for a dummy
        helper object), as opposed to the basic properties like name, color,
        transform, etc.

        """

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
