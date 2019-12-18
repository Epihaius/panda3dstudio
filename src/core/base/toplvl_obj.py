from .base import *
from .mgr import CoreManager as Mgr


class TopLevelObject:

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_name"] = self._name.get_value()
        state["_pivot"] = NodePath(self.pivot.name)
        state["_origin"] = NodePath(self.origin.name)
        state["_child_ids"] = []
        state["_parent_id"] = None
        state["_group_id"] = None
        del state["pivot_gizmo"]
        del state["pivot"]
        del state["origin"]
        state["_type"] = state.pop("type")
        state["_id"] = state.pop("id")

        return state

    def __setstate__(self, state):

        state["type"] = state.pop("_type")
        state["id"] = state.pop("_id")
        state["pivot"] = state.pop("_pivot")
        state["origin"] = state.pop("_origin")
        self.__dict__ = state

        self._name = ObjectName(state["_name"])
        self._name.add_updater("global_obj_names", self.__update_obj_names)
        self._name.update("global_obj_names")
        pivot = self.pivot
        pivot.reparent_to(Mgr.get("object_root"))
        origin = self.origin
        origin.reparent_to(pivot)
        self.pivot_gizmo = Mgr.do("create_pivot_gizmo", self)

    def __init__(self, obj_type, obj_id, name, origin_pos, has_color=False):

        self._prop_ids = ["name", "link", "selection_state", "tags",
                          "transform", "origin_transform"]

        self.type = obj_type
        self.id = obj_id
        self._name = ObjectName(name)
        self._name.add_updater("global_obj_names", self.__update_obj_names)
        self._name.update("global_obj_names")
        self._parent_id = None
        self._group_id = None
        self._child_ids = []
        obj_root = Mgr.get("object_root")
        pivot = obj_root.attach_new_node(f"{obj_id}pivot")
        self.pivot = pivot
        self.origin = pivot.attach_new_node(f"{obj_id}origin")
        self._has_color = has_color

        grid = Mgr.get("grid")
        active_grid_plane = grid.plane_id
        grid_origin = grid.origin

        if active_grid_plane == "xz":
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., 0., 90.))
        else:
            pivot.set_pos_hpr(grid_origin, origin_pos, VBase3(0., 0., 0.))

        self.pivot_gizmo = Mgr.do("create_pivot_gizmo", self)

    def cancel_creation(self):

        Notifiers.obj.info(f'Creation of object "{self.name}" has been cancelled.')

        self._name.remove_updater("global_obj_names", final_update=True)
        self.name = ""
        self.pivot_gizmo.destroy(unregister=False)
        self.pivot_gizmo = None
        self.origin.detach_node()
        self.origin = None
        self.pivot.detach_node()
        self.pivot = None

    def destroy(self, unregister=True, add_to_hist=True):

        if not self.origin:
            return False

        if add_to_hist:

            obj_data = {}
            event_data = {"objects": obj_data}

            for child_id in self._child_ids[:]:
                child = Mgr.get("object", child_id)
                obj_data[child_id] = child.get_data_to_store("deletion")
                child.destroy(unregister, add_to_hist)

            if obj_data:
                Mgr.do("add_history", "", event_data, update_time_id=False)

        self.parent = None
        self.group = None

        self._name.remove_updater("global_obj_names", final_update=True)
        self.name = ""
        self.pivot_gizmo.destroy(unregister)
        self.pivot_gizmo = None
        self.origin.detach_node()
        self.origin = None
        self.pivot.detach_node()
        self.pivot = None

        if unregister:
            Mgr.do(f"unregister_{self.type}", self)

        task = lambda: self.__remove_references(add_to_hist)
        task_id = "object_removal"
        PendingTasks.add(task, task_id, "object", id_prefix=self.id)
        task = lambda: self.set_selected(False, False)
        task_id = "update_selection"
        PendingTasks.add(task, task_id, "object", id_prefix=self.id)
        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        return True

    def __remove_references(self, add_to_hist=True):

        cs_type = GD["coord_sys_type"]
        tc_type = GD["transf_center_type"]

        if Mgr.get("coord_sys_obj") is self:
            Mgr.update_app("coord_sys", "world" if cs_type == "object" else cs_type)

        if Mgr.get("transf_center_obj") is self:
            Mgr.update_app("transf_center", "adaptive" if tc_type == "object" else tc_type)

        Mgr.update_app("object_removal", self.id, add_to_hist)
        Mgr.do("update_obj_transf_info", self.id)

    def register(self):

        Mgr.do(f"register_{self.type}", self)
        self.pivot_gizmo.register()

    def recreate(self):
        """
        Recreate the object geometry and ID after unpickling during merge.

        Override in derived class.

        """

        pass

    @property
    def name(self):

        return self._name.get_value()

    @name.setter
    def name(self, name):

        if self._name.get_value() == name:
            return

        self._name.set_value(name)

        selection = Mgr.get("selection")

        if self in selection:
            names = {obj.id: obj.name for obj in selection if obj.name}
            Mgr.update_remotely("selected_obj_names", names)

    @property
    def name_obj(self):

        return self._name

    def __update_obj_names(self, name=None):

        obj_names = GD["obj_names"]

        if name is None:

            value = self._name.get_value()

            if value in obj_names:
                obj_names.remove(value)

        elif name not in obj_names:
            obj_names.append(name)

    def has_color(self):

        return self._has_color

    def get_toplevel_object(self, get_group=False):

        if get_group:

            group = Mgr.get("group", self._group_id) if self._group_id else None

            if group and not group.is_open():
                return group.get_toplevel_object(get_group)

        return self

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    @property
    def root(self):

        node = self
        parent = self.link_target

        while parent:
            node = parent
            parent = node.link_target

        return node

    def get_common_ancestor(self, others):

        ancestors = self.ancestors
        common_ancestor = None
        ancestor_index = -1

        for other in others:

            common_ancestor_found = False
            parent = other.parent

            while parent:

                if parent in ancestors:

                    index = ancestors.index(parent)

                    if index > ancestor_index:
                        common_ancestor = parent
                        ancestor_index = index

                    common_ancestor_found = True
                    break

                parent = parent.parent

            if not common_ancestor_found:
                return None

        return common_ancestor

    @property
    def ancestors(self):

        ancestors = []
        ancestor = self.parent

        while ancestor:
            ancestors.append(ancestor)
            ancestor = ancestor.parent

        return ancestors

    @property
    def parent(self):

        return Mgr.get("object", self._parent_id)

    @parent.setter
    def parent(self, parent_id):

        self.set_parent(parent_id)

    def set_parent(self, parent_id):

        if self._parent_id == parent_id:
            if parent_id is None:
                if self._group_id is None:
                    return False
            else:
                return False

        parent = Mgr.get("object", parent_id) if parent_id else None

        if parent:
            self.pivot.wrt_reparent_to(parent.pivot)
            parent.add_child(self.id)
        else:
            self.pivot.wrt_reparent_to(Mgr.get("object_root"))

        if parent:
            Mgr.do("add_obj_link_viz", self, parent)
        elif self._parent_id:
            Mgr.do("remove_obj_link_viz", self.id)

        old_parent = Mgr.get("object", self._parent_id)
        old_group = Mgr.get("group", self._group_id)

        if old_parent:
            old_parent.remove_child(self.id)
        elif old_group:
            old_group.remove_member(self.id)

        self._parent_id = parent_id
        self._group_id = None

        return True

    @property
    def parent_origin(self):

        return self.parent.origin if self._parent_id else Mgr.get("object_root")

    def get_parent_pivot(self, accept_group=True):

        pivot = self.parent.pivot if self._parent_id else None

        if not pivot and accept_group:
            pivot = self.group.pivot if self._group_id else None

        if not pivot:
            pivot = Mgr.get("object_root")

        return pivot

    @property
    def parent_pivot(self):

        return self.get_parent_pivot()

    @property
    def group(self):

        return Mgr.get("group", self._group_id)

    @group.setter
    def group(self, group_id):

        self.set_group(group_id)

    def set_group(self, group_id):

        if self._group_id == group_id:
            if group_id is None:
                if self._parent_id is None:
                    return False
            else:
                return False

        group = Mgr.get("group", group_id) if group_id else None

        if group:
            self.pivot.wrt_reparent_to(group.pivot)
            group.add_member(self.id)
        else:
            self.pivot.wrt_reparent_to(Mgr.get("object_root"))

        if self._parent_id:
            Mgr.do("remove_obj_link_viz", self.id)

        old_parent = Mgr.get("object", self._parent_id)
        old_group = Mgr.get("group", self._group_id)

        if old_parent:
            old_parent.remove_child(self.id)
        elif old_group:
            old_group.remove_member(self.id)

        self._parent_id = None
        self._group_id = group_id

        return True

    @property
    def outer_groups(self):

        outer_groups = []
        group = Mgr.get("group", self._group_id)

        while group:
            outer_groups.append(group)
            group = group.group

        return outer_groups

    def get_outermost_group(self, accept_self=True):

        group = Mgr.get("group", self._group_id)

        if group:
            return group.outermost_group
        elif self.type == "group" and accept_self:
            return self

    @property
    def outermost_group(self):

        return self.get_outermost_group()

    def get_common_group(self, others):

        outer_groups = self.outer_groups
        common_group = None
        group_index = -1

        for other in others:

            common_group_found = False
            group = other.group

            while group:

                if group in outer_groups:

                    index = outer_groups.index(group)

                    if index > group_index:
                        common_group = group
                        group_index = index

                    common_group_found = True
                    break

                group = group.group

            if not common_group_found:
                return None

        return common_group

    def update_group_bbox(self):

        group = Mgr.get("group", self._group_id)

        if group:
            Mgr.do("update_group_bboxes", [self._group_id])

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this one.

        Override in derived class.

        """

        pass

    def restore_link(self, parent_id, group_id):

        Notifiers.obj.debug(f'Restoring link for "{self.name}"...\n'
                            f'Old parent ID: {self._parent_id}\n'
                            f'Old group ID: {self._group_id}\n'
                            f'New parent ID: {parent_id}\n'
                            f'New group ID: {group_id}')

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

            if parent in self.descendants:
                parent.restore_link(None, None)

            if parent:
                parent.add_child(self.id)
                self.pivot.reparent_to(parent.pivot)
            else:
                self.pivot.reparent_to(Mgr.get("object_root"))

            if parent:
                Mgr.do("add_obj_link_viz", self, parent)
            elif self._parent_id:
                Mgr.do("remove_obj_link_viz", self.id)

            link_restored = True
            Notifiers.obj.debug(f'New parent for "{self.name}": "{parent_id}"')

        if restore_group:

            group = Mgr.get("group", group_id) if group_id else None

            if group in self.descendants:
                group.restore_link(None, None)

            if group:
                self.pivot.reparent_to(group.pivot)
                group.add_member(self.id)
            else:
                self.pivot.reparent_to(Mgr.get("object_root"))

            if self._parent_id:
                Mgr.do("remove_obj_link_viz", self.id)

            link_restored = True
            Notifiers.obj.debug(f'New group for "{self.name}": "{group_id}"')

        self._parent_id = parent_id
        self._group_id = group_id

        if link_restored:

            Notifiers.obj.debug(f'Reparented "{self.name}"')

            if old_parent:
                old_parent.remove_child(self.id)
            elif old_group:
                old_group.remove_member(self.id)

    @property
    def link_target(self):

        return Mgr.get("group", self._group_id) or Mgr.get("object", self._parent_id)

    def get_common_link_target(self, others):

        link_targets = []
        link_target = self.link_target

        while link_target:
            link_targets.append(link_target)
            link_target = link_target.link_target

        common_link_target = None
        link_target_index = -1

        for other in others:

            common_link_target_found = False
            link_target = other.link_target

            while link_target:

                if link_target in link_targets:

                    index = link_targets.index(link_target)

                    if index > link_target_index:
                        common_link_target = link_target
                        link_target_index = index

                    common_link_target_found = True
                    break

                link_target = link_target.link_target

            if not common_link_target_found:
                return None

        return common_link_target

    @property
    def child_types(self):

        return [Mgr.get("object", child_id).type for child_id in self._child_ids]

    @property
    def children(self):

        return [Mgr.get("object", child_id) for child_id in self._child_ids]

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

    def get_descendants(self, include_group_members=True):

        descendants = []
        children = self.children[:]

        if include_group_members and self.type == "group":
            children.extend(self.get_members())

        descendants.extend(children)

        for child in children:
            descendants.extend(child.get_descendants(include_group_members))

        return descendants

    @property
    def descendants(self):

        return self.get_descendants()

    @property
    def transform_values(self):

        transform = {}

        if GD["coord_sys_type"] == "local":
            transform["translate"] = (0., 0., 0.)
            transform["rotate"] = (0., 0., 0.)
            transform["scale"] = (1., 1., 1.)
        else:
            grid_origin = Mgr.get("grid").origin
            node = self.origin if GD["transform_target_type"] == "geom" else self.pivot
            x, y, z = node.get_pos(grid_origin)
            h, p, r = node.get_hpr(grid_origin)
            sx, sy, sz = node.get_scale(grid_origin)
            transform["translate"] = (x, y, z)
            transform["rotate"] = (p, r, h)
            transform["scale"] = (sx, sy, sz)

        return transform

    @property
    def tags(self):

        orig = self.origin
        tags = {key: orig.get_tag(key) for key in orig.get_tag_keys()}

        return tags

    @tags.setter
    def tags(self, tags):

        orig = self.origin

        for key in orig.get_tag_keys():
            orig.clear_tag(key)

        for key, val in tags.items():
            orig.set_tag(key, val)

    def set_selected(self, is_selected=True, add_to_hist=True):

        task = lambda: Mgr.update_remotely("selection_set", "hide_name")
        task_id = "clear_selection_set_display"
        PendingTasks.add(task, task_id, "ui")

        if is_selected:
            return Mgr.get("selection_top").add([self], add_to_hist)
        else:
            return Mgr.get("selection_top").remove([self], add_to_hist)

    def is_selected(self):

        return self in Mgr.get("selection_top")

    def update_selection_state(self, is_selected=True):
        """
        Visually indicate that this object has been (de)selected.

        """

        if self.pivot_gizmo:
            self.pivot_gizmo.show(is_selected)

    def set_property(self, prop_id, value, restore=""):

        add_to_hist = not restore

        if prop_id == "name":

            self.name = value

        elif prop_id == "link":

            group_ids = [obj_id for obj_id in value if obj_id]
            group = self.group

            if group:
                group_ids.append(group.id)

            Mgr.do("update_group_bboxes", group_ids)

            task = lambda: self.restore_link(*value)
            task_id = "object_linking"
            PendingTasks.add(task, task_id, "object", id_prefix=self.id)

        elif prop_id == "selection_state":

            if restore:
                task = lambda: self.set_selected(value, False)
                task_id = "update_selection"
                PendingTasks.add(task, task_id, "object", id_prefix=self.id)
                task = lambda: Mgr.get("selection").update(hide_sets=True)
                PendingTasks.add(task, task_id, "ui")
            else:
                self.set_selected(value, True)

        elif prop_id == "transform":

            task = lambda: self.pivot.set_mat(self.parent_pivot, value)
            Mgr.do("add_transf_to_restore", "pivot", self, task)
            Mgr.do("restore_transforms")
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

            transform_types = ["translate", "rotate", "scale"]
            Mgr.do("update_obj_transf_info", self.id, transform_types)
            Mgr.do("update_obj_link_viz")
            Mgr.do("reset_obj_transf_info")

            if Mgr.get("coord_sys_obj") is self:

                def update_coord_sys():

                    Mgr.do("notify_coord_sys_transformed")
                    Mgr.do("update_coord_sys")

                task_id = "coord_sys_update"
                PendingTasks.add(update_coord_sys, task_id, "ui")

            if Mgr.get("transf_center_obj") is self:
                task = lambda: Mgr.get("transf_gizmo").set_pos(self.pivot.get_pos(GD.world))
                task_id = "transf_center_update"
                PendingTasks.add(task, task_id, "ui")

            for obj in self.descendants:
                if obj.type == "point_helper":
                    obj.update_pos()

            self.update_group_bbox()

        elif prop_id == "origin_transform":

            task = lambda: self.origin.set_mat(self.pivot, value)
            Mgr.do("add_transf_to_restore", "origin", self, task)
            Mgr.do("restore_transforms")
            task = lambda: Mgr.get("selection").update()
            PendingTasks.add(task, "update_selection", "ui")

            self.update_group_bbox()

            if self.type == "group":
                Mgr.do("update_group_bboxes", [self.id])

        elif prop_id == "tags":

            self.tags = value

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "name":
            return self._name.get_value()
        elif prop_id == "link":
            return self._parent_id, self._group_id
        elif prop_id == "selection_state":
            return self.is_selected()
        elif prop_id == "transform":
            return self.pivot.get_mat(self.parent_pivot)
        elif prop_id == "origin_transform":
            return self.origin.get_mat(self.pivot)
        elif prop_id == "tags":
            return self.tags

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

        obj_id = self.id

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
