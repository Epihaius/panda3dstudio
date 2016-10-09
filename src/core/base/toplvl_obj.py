from .base import *
from .mgr import CoreManager as Mgr


class TopLevelObject(BaseObject):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_name"] = self._name.get_value()
        state["_pivot"] = NodePath(self._pivot.get_name())
        state["_origin"] = NodePath(self._origin.get_name())
        state["_child_ids"] = []
        state["_parent_id"] = None
        state["_group_id"] = None
        del state["_pivot_gizmo"]

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
        self._pivot_gizmo = Mgr.do("create_pivot_gizmo", self)

    def __init__(self, obj_type, obj_id, name, origin_pos, has_color=False):

        self._prop_ids = ["name", "link", "selection_state", "tags",
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
        self._group_id = None
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

        self.set_parent(None)
        self.set_group(None)

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

    def get_toplevel_object(self, get_group=False):

        if get_group:

            group = Mgr.get("group", self._group_id) if self._group_id else None

            if group and not group.is_open():
                return group.get_toplevel_object(get_group)

        return self

    def register(self):

        Mgr.do("register_%s" % self._type, self)

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this one.

        Override in derived class.

        """

        pass

    def set_parent(self, parent_id=None):

        if self._parent_id == parent_id:
            if parent_id is None:
                if self._group_id is None:
                    return False
            else:
                return False

        parent = Mgr.get("object", parent_id) if parent_id else None

        if parent:
            self._pivot.wrt_reparent_to(parent.get_pivot())
            parent.add_child(self._id)
        else:
            self._pivot.wrt_reparent_to(Mgr.get("object_root"))

        if parent:
            Mgr.do("add_obj_link_viz", self, parent)
        elif self._parent_id:
            Mgr.do("remove_obj_link_viz", self._id)

        old_parent = Mgr.get("object", self._parent_id)
        old_group = Mgr.get("group", self._group_id)

        if old_parent:
            old_parent.remove_child(self._id)
        elif old_group:
            old_group.remove_member(self._id)

        self._parent_id = parent_id
        self._group_id = None

        return True

    def set_group(self, group_id=None):

        if self._group_id == group_id:
            if group_id is None:
                if self._parent_id is None:
                    return False
            else:
                return False

        group = Mgr.get("group", group_id) if group_id else None

        if group:
            self._pivot.wrt_reparent_to(group.get_pivot())
            group.add_member(self._id)
        else:
            self._pivot.wrt_reparent_to(Mgr.get("object_root"))

        if self._parent_id:
            Mgr.do("remove_obj_link_viz", self._id)

        old_parent = Mgr.get("object", self._parent_id)
        old_group = Mgr.get("group", self._group_id)

        if old_parent:
            old_parent.remove_child(self._id)
        elif old_group:
            old_group.remove_member(self._id)

        self._parent_id = None
        self._group_id = group_id

        return True

    def restore_link(self, parent_id, group_id):

        old_parent = Mgr.get("object", self._parent_id)
        old_group = Mgr.get("group", self._group_id)
        link_restored = False

        if parent_id is None and group_id is None:
            restore_parent = self._parent_id != parent_id
            restore_group = self._group_id != group_id
        elif parent_id is None:
            restore_parent = False
            restore_group = self._group_id != group_id
        elif group_id is None:
            restore_parent = self._parent_id != parent_id
            restore_group = False

        if restore_parent:

            parent = Mgr.get("object", parent_id) if parent_id else None

            if parent in self.get_descendants():
                parent.restore_link(None, None)

            if parent:
                parent.add_child(self._id)
                self._pivot.reparent_to(parent.get_pivot())
            else:
                self._pivot.reparent_to(Mgr.get("object_root"))

            if parent:
                Mgr.do("add_obj_link_viz", self, parent)
            elif self._parent_id:
                Mgr.do("remove_obj_link_viz", self._id)

            link_restored = True

        if restore_group:

            group = Mgr.get("group", group_id) if group_id else None

            if group in self.get_descendants():
                group.restore_link(None, None)

            if group:
                self._pivot.reparent_to(group.get_pivot())
                group.add_member(self._id)
            else:
                self._pivot.reparent_to(Mgr.get("object_root"))

            if self._parent_id:
                Mgr.do("remove_obj_link_viz", self._id)

            link_restored = True

        self._parent_id = parent_id
        self._group_id = group_id

        if link_restored:
            if old_parent:
                old_parent.remove_child(self._id)
            elif old_group:
                old_group.remove_member(self._id)

    def get_link_target(self):

        return Mgr.get("group", self._group_id) or Mgr.get("object", self._parent_id)

    def get_common_link_target(self, others):

        link_targets = []
        link_target = self.get_link_target()

        while link_target:
            link_targets.append(link_target)
            link_target = link_target.get_link_target()

        common_link_target = None
        link_target_index = -1

        for other in others:

            common_link_target_found = False
            link_target = other.get_link_target()

            while link_target:

                if link_target in link_targets:

                    index = link_targets.index(link_target)

                    if index > link_target_index:
                        common_link_target = link_target
                        link_target_index = index

                    common_link_target_found = True
                    break

                link_target = link_target.get_link_target()

            if not common_link_target_found:
                return None

        return common_link_target

    def get_parent(self):

        return Mgr.get("object", self._parent_id)

    def get_parent_origin(self):

        return self.get_parent().get_origin() if self._parent_id else Mgr.get("object_root")

    def get_parent_pivot(self, accept_group=True):

        pivot = self.get_parent().get_pivot() if self._parent_id else None

        if not pivot and accept_group:
            pivot = self.get_group().get_pivot() if self._group_id else None

        if not pivot:
            pivot = Mgr.get("object_root")

        return pivot

    def get_group(self):

        return Mgr.get("group", self._group_id)

    def get_outer_groups(self):

        outer_groups = []
        group = Mgr.get("group", self._group_id)

        while group:
            outer_groups.append(group)
            group = group.get_group()

        return outer_groups

    def get_outermost_group(self, accept_self=True):

        group = Mgr.get("group", self._group_id)

        if group:
            return group.get_outermost_group()
        elif self._type == "group" and accept_self:
            return self

    def get_common_group(self, others):

        outer_groups = self.get_outer_groups()
        common_group = None
        group_index = -1

        for other in others:

            common_group_found = False
            group = other.get_group()

            while group:

                if group in outer_groups:

                    index = outer_groups.index(group)

                    if index > group_index:
                        common_group = group
                        group_index = index

                    common_group_found = True
                    break

                group = group.get_group()

            if not common_group_found:
                return None

        return common_group

    def update_group_bbox(self):

        group = Mgr.get("group", self._group_id)

        if group:
            Mgr.do("update_group_bboxes", [self._group_id])

    def get_root(self):

        node = self
        parent = self.get_link_target()

        while parent:
            node = parent
            parent = node.get_link_target()

        return node

    def get_ancestors(self):

        ancestors = []
        ancestor = self.get_parent()

        while ancestor:
            ancestors.append(ancestor)
            ancestor = ancestor.get_parent()

        return ancestors

    def get_common_ancestor(self, others):

        ancestors = self.get_ancestors()
        common_ancestor = None
        ancestor_index = -1

        for other in others:

            common_ancestor_found = False
            parent = other.get_parent()

            while parent:

                if parent in ancestors:

                    index = ancestors.index(parent)

                    if index > ancestor_index:
                        common_ancestor = parent
                        ancestor_index = index

                    common_ancestor_found = True
                    break

                parent = parent.get_parent()

            if not common_ancestor_found:
                return None

        return common_ancestor

    def add_child(self, child_id):

        if child_id in self._child_ids:
            return False

        self._child_ids.append(child_id)

        return True

    def remove_child(self, child_id):

        if child_id not in self._child_ids:
            return False

        self._child_ids.remove(child_id)

        return True

    def get_children(self):

        return [Mgr.get("object", child_id) for child_id in self._child_ids]

    def get_child_types(self):

        return [Mgr.get("object", child_id).get_type() for child_id in self._child_ids]

    def get_descendants(self, include_group_members=True):

        descendants = []
        children = self.get_children()[:]

        if include_group_members and self._type == "group":
            children.extend(self.get_members())

        descendants.extend(children)

        for child in children:
            descendants.extend(child.get_descendants(include_group_members))

        return descendants

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

            sel_colors = tuple(set(obj.get_color() for obj in Mgr.get("selection")
                                   if obj.has_color()))
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
            self._pivot_gizmo.show(is_selected)

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

    def set_property(self, prop_id, value, restore=""):

        add_to_hist = not restore

        if prop_id == "name":

            self.set_name(value)

        elif prop_id == "link":

            group_ids = [obj_id for obj_id in value if obj_id]
            group = self.get_group()

            if group:
                group_ids.append(group.get_id())

            Mgr.do("update_group_bboxes", group_ids)

            task = lambda: self.restore_link(*value)
            task_id = "object_linking"
            PendingTasks.add(task, task_id, "object", id_prefix=self._id)

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

            for obj in self.get_descendants():
                if obj.get_type() == "point_helper":
                    obj.update_pos()

            self.update_group_bbox()

        elif prop_id == "origin_transform":

            task = lambda: self._origin.set_mat(self._pivot, value)
            Mgr.do("add_transf_to_restore", "origin", self, task)
            Mgr.do("restore_transforms")
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

            self.update_group_bbox()

            if self._type == "group":
                Mgr.do("update_group_bboxes", [self._id])

        elif prop_id == "tags":

            self.set_tags(value)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "name":
            return self._name.get_value()
        elif prop_id == "link":
            return self._parent_id, self._group_id
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
