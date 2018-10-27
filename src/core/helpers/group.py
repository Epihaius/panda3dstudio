from ..base import *


class Group(TopLevelObject):

    # the following maps group member types to the actual object types
    # compatible with those member types; e.g. "collision" includes "model",
    # but this might be extended with line geometry like "ray" etc. in the
    # future
    _compatible_types = {"model": ["model"], "collision": ["model"], "dummy": ["dummy"],
                         "point": ["point_helper"], "tex_projector": ["tex_projector"],
                         "helper": ["dummy", "point_helper", "tex_projector"]}

    def __getstate__(self):

        state = TopLevelObject.__getstate__(self)

        state["_member_ids"] = []
        state["_collision_geoms"] = {}

        return state

    def __setstate__(self, state):

        TopLevelObject.__setstate__(self, state)

        self._bbox.get_origin().reparent_to(self.get_origin())
        self._bbox.set_color(self._color_unsel)
        self._bbox.hide()
        Mgr.do("update_group_bboxes", [self.get_id()])

        if self._bbox_is_const_size:
            Mgr.do("make_group_const_size", self._bbox)
            self._bbox.get_origin().detach_node()

    def __init__(self, member_types, member_types_id, group_id, name, color_unsel):

        TopLevelObject.__init__(self, "group", group_id, name, Point3())

        self._type_prop_ids = ["member_types", "open"]
        self._member_types = member_types
        self._member_types_id = member_types_id
        self._member_ids = []
        self._is_open = False
        self._color_unsel = color_unsel
        self._bbox = Mgr.do("create_bbox", self, color_unsel)
        self._bbox.hide()
        self._bbox_is_const_size = False
        self._collision_geoms = {}

    def __del__(self):

        logging.info('Group garbage-collected.')

    def destroy(self, unregister=True, add_to_hist=True):

        if not TopLevelObject.destroy(self, unregister, add_to_hist):
            return

        if self._member_types_id == "collision" and not self._is_open:
            self.__destroy_collision_geoms()

        if add_to_hist:

            obj_data = {}
            event_data = {"objects": obj_data}

            for member_id in self._member_ids[:]:
                member = Mgr.get("object", member_id)
                obj_data[member_id] = member.get_data_to_store("deletion")
                member.destroy(unregister, add_to_hist)

            if obj_data:
                Mgr.do("add_history", "", event_data, update_time_id=False)

        if self._bbox_is_const_size:
            Mgr.do("make_group_const_size", self._bbox, False)

        self._bbox.destroy(unregister)
        self._bbox = None

    def register(self, restore=True):

        TopLevelObject.register(self)

        self._bbox.register(restore)

    def __create_collision_geoms(self):

        members = self.get_members()

        if not members:
            return

        collision_geoms = self._collision_geoms
        group_pivot = self.get_pivot()
        group_pivot.node().set_final(True)
        compass_props = CompassEffect.P_all

        for member in members:

            member_id = member.get_id()

            if member.get_type() == "model" and member_id not in collision_geoms:

                if member.get_geom_type() == "basic_geom":
                    geom = member.get_geom_object().get_geom()
                else:
                    geom = member.get_geom_object().get_geom_data_object().get_toplevel_geom()

                coll_geom = geom.instance_under_node(group_pivot, "collision_geom")
                coll_geom.set_material_off()
                coll_geom.set_texture_off()
                coll_geom.set_shader_off()
                coll_geom.set_light_off()
                coll_geom.set_transparency(TransparencyAttrib.M_alpha)
                coll_geom.set_color((1., 1., 1., .5))
                compass_effect = CompassEffect.make(member.get_pivot(), compass_props)
                coll_geom.set_effect(compass_effect)
                collision_geoms[member_id] = coll_geom
                geom.detach_node()

    def __destroy_collision_geoms(self):

        for coll_geom in self._collision_geoms.values():
            coll_geom.remove_node()

        for member in self.get_members():
            if member.get_type() == "model":
                if member.get_geom_type() == "basic_geom":
                    geom = member.get_geom_object().get_geom()
                    geom.reparent_to(member.get_origin())
                else:
                    geom_data_obj = member.get_geom_object().get_geom_data_object()
                    geom = geom_data_obj.get_toplevel_geom()
                    geom.reparent_to(geom_data_obj.get_origin())

        self._collision_geoms.clear()
        pivot = self.get_pivot()

        if pivot:
            pivot.node().set_final(False)

    def set_member_types(self, member_types, member_types_id, check_outer_group=True,
                         removed_members=None):

        if self._member_types_id == member_types_id:
            return False

        if check_outer_group:

            group = self.get_group()

            if group and not group.can_contain(member_types=member_types):
                return False

        old_member_types = self._member_types
        old_member_types_id = self._member_types_id
        self._member_types = member_types
        members_to_remove = []

        for member in self.get_members():
            if not self.can_contain(member):
                members_to_remove.append(member)

        if members_to_remove and len(members_to_remove) == len(self._member_ids):
            self._member_types = old_member_types
            return False

        self._member_types_id = member_types_id

        if members_to_remove:

            outer_group = self.get_group()

            if outer_group:

                outer_group_id = outer_group.get_id()

                for member in members_to_remove:
                    member.set_group(outer_group_id)

            else:

                parent = self.get_parent()
                parent_id = parent.get_id() if parent else None

                for member in members_to_remove:
                    member.set_parent(parent_id)

            if removed_members is not None:
                removed_members.update(members_to_remove)

        if member_types_id == "collision" and not self._is_open:
            self.__create_collision_geoms()
        elif old_member_types_id == "collision":
            self.__destroy_collision_geoms()

        return True

    def __restore_member_types(self, member_types, member_types_id):

        old_member_types = self._member_types
        old_member_types_id = self._member_types_id
        self._member_types = member_types
        self._member_types_id = member_types_id

        if member_types_id == "collision" and not self._is_open:
            self.__create_collision_geoms()
        elif old_member_types_id == "collision":
            self.__destroy_collision_geoms()

    def get_member_types(self):

        return self._member_types

    def get_member_types_id(self):

        return self._member_types_id

    def can_contain(self, obj=None, member_types=None):

        if not self._member_types:
            return True

        if obj is None:

            if not member_types:
                return False

            return member_types.issubset(self._member_types)

        if obj.get_type() == "group":

            other_types = obj.get_member_types()

            if not other_types:
                return False

            return other_types.issubset(self._member_types)

        obj_types = sum([self._compatible_types[member_type]
                        for member_type in self._member_types], [])

        return obj.get_type() in obj_types

    def get_bbox(self):

        return self._bbox

    def get_center_pos(self, ref_node):

        if self._bbox_is_const_size:
            return self.get_origin().get_pos(ref_node)

        return self._bbox.get_center_pos(ref_node)

    def update_selection_state(self, is_selected=True):

        TopLevelObject.update_selection_state(self, is_selected)

        if self._bbox_is_const_size:

            bbox_origins = Mgr.get("const_sized_group_bbox", self.get_id())

            if not bbox_origins:
                return

            for origin in bbox_origins:

                if is_selected:
                    origin.set_color((1., 1., 0., 1.) if self._is_open else (1., 1., 1., 1.))
                else:
                    origin.set_color(self._color_unsel)

                if not self._is_open:
                    if is_selected:
                        origin.show()
                    else:
                        origin.hide()

        bbox = self._bbox

        if not bbox:
            return

        if is_selected:
            bbox.set_color((1., 1., 0., 1.) if self._is_open else (1., 1., 1., 1.))
        else:
            bbox.set_color(self._color_unsel)

        if not self._is_open:
            if is_selected:
                bbox.show()
            else:
                bbox.hide()

    def update_bbox(self):

        if not self._bbox:
            return

        members = self.get_members()

        if not members:
            return

        group_orig = self.get_origin()
        group_pivot = self.get_pivot()
        parents = {}

        for member in members:
            member_orig = member.get_origin()
            parents[member_orig] = member_orig.get_parent()
            member_orig.wrt_reparent_to(group_orig)

        bbox_orig = self._bbox.get_origin()
        bbox_orig.detach_node()
        transform = group_orig.get_transform()
        group_orig.clear_transform()
        bounds = group_orig.get_tight_bounds()

        member = members[0]
        x_min, y_min, z_min = x_max, y_max, z_max = member.get_center_pos(group_orig)

        for member in members[1:]:
            x, y, z = member.get_center_pos(group_orig)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            z_min = min(z_min, z)
            x_max = max(x_max, x)
            y_max = max(y_max, y)
            z_max = max(z_max, z)

        bbox_orig.reparent_to(group_orig)
        group_orig.set_transform(transform)

        for member, parent in parents.items():
            member.wrt_reparent_to(parent)

        if bounds:

            for point in bounds:
                x, y, z = point
                x_min = min(x_min, x)
                y_min = min(y_min, y)
                z_min = min(z_min, z)
                x_max = max(x_max, x)
                y_max = max(y_max, y)
                z_max = max(z_max, z)

        epsilon = 1.e-010

        if max(x_max - x_min, y_max - y_min, z_max - z_min) > epsilon:

            if self._bbox_is_const_size:
                Mgr.do("make_group_const_size", self._bbox, False)
                bbox_orig.reparent_to(group_orig)
                self._bbox_is_const_size = False

            point_min = Point3(x_min, y_min, z_min)
            point_max = Point3(x_max, y_max, z_max)
            vec = (point_max - point_min) * .5
            center_pos = point_min + vec
            center_pos = group_pivot.get_relative_point(group_orig, center_pos)
            group_orig.set_pos(center_pos)
            self._bbox.update(Point3(-vec), Point3(vec))

        else:

            pos = Point3(x_min, y_min, z_min)
            center_pos = group_pivot.get_relative_point(group_orig, pos)
            group_orig.set_pos(center_pos)
            bbox_orig.clear_transform()
            bbox_orig.detach_node()

            if not self._bbox_is_const_size:
                Mgr.do("make_group_const_size", self._bbox)
                self._bbox_is_const_size = True

    def center_pivot(self):

        pivot = self.get_pivot()
        obj_root = Mgr.get("object_root")
        objs = self.get_members() + self.get_children()

        for obj in objs:
            obj.get_pivot().wrt_reparent_to(obj_root)

        origin = self.get_origin()
        origin.set_hpr(self.get_parent_pivot(), 0., 0., 0.)
        self.update_bbox()
        pivot.clear_transform(origin)
        origin.clear_transform()

        for obj in objs:
            obj.get_pivot().wrt_reparent_to(pivot)

        obj_data = {}
        event_data = {"objects": obj_data}

        data = self.get_data_to_store("prop_change", "transform")
        obj_data[self.get_id()] = data

        for obj in objs:
            data = obj.get_data_to_store("prop_change", "transform")
            obj_data[obj.get_id()] = data

        Mgr.do("add_history", "", event_data, update_time_id=False)

    def add_member(self, member_id):

        if member_id in self._member_ids:
            return False

        self._member_ids.append(member_id)
        Mgr.do("update_group_bboxes", [self.get_id()])

        if self._member_types_id == "collision" and not self._is_open:

            member = Mgr.get("object", member_id)

            if member.get_type() == "model" and member_id not in self._collision_geoms:

                group_pivot = self.get_pivot()

                if member.get_geom_type() == "basic_geom":
                    geom = member.get_geom_object().get_geom()
                else:
                    geom = member.get_geom_object().get_geom_data_object().get_toplevel_geom()

                coll_geom = geom.instance_under_node(group_pivot, "collision_geom")
                coll_geom.set_material_off()
                coll_geom.set_texture_off()
                coll_geom.set_shader_off()
                coll_geom.set_light_off()
                coll_geom.set_transparency(TransparencyAttrib.M_alpha)
                coll_geom.set_color((1., 1., 1., .5))
                compass_props = CompassEffect.P_pos | CompassEffect.P_rot
                compass_effect = CompassEffect.make(member.get_pivot(), compass_props)
                coll_geom.set_effect(compass_effect)
                self._collision_geoms[member_id] = coll_geom
                geom.detach_node()

        return True

    def remove_member(self, member_id):

        if member_id not in self._member_ids:
            return False

        self._member_ids.remove(member_id)
        Mgr.do("update_group_bboxes", [self.get_id()])

        if member_id in self._collision_geoms:

            coll_geom = self._collision_geoms[member_id]
            coll_geom.remove_node()
            del self._collision_geoms[member_id]
            member = Mgr.get("object", member_id)

            if member:
                if member.get_geom_type() == "basic_geom":
                    geom = member.get_geom_object().get_geom()
                    geom.reparent_to(member.get_origin())
                else:
                    geom_data_obj = member.get_geom_object().get_geom_data_object()
                    geom = geom_data_obj.get_toplevel_geom()
                    geom.reparent_to(geom_data_obj.get_origin())

        return True

    def get_members(self):

        objs = (Mgr.get("object", member_id) for member_id in self._member_ids)

        return [obj for obj in objs if obj]

    def open(self, is_open=True):

        if self._is_open == is_open:
            return False

        if self._bbox_is_const_size:

            bbox_origins = Mgr.get("const_sized_group_bbox", self.get_id())

            for origin in bbox_origins:

                if self.is_selected():
                    origin.set_color((1., 1., 0., 1.) if is_open else (1., 1., 1., 1.))
                else:
                    if is_open:
                        origin.show()
                    else:
                        origin.hide()

        if self.is_selected():
            self._bbox.set_color((1., 1., 0., 1.) if is_open else (1., 1., 1., 1.))
        else:
            if is_open:
                self._bbox.show()
            else:
                self._bbox.hide()

        self._is_open = is_open

        if self._member_types_id == "collision":
            if is_open:
                self.__destroy_collision_geoms()
            else:
                self.__create_collision_geoms()

        return True

    def is_open(self):

        return self._is_open

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "member_types":
            Mgr.update_remotely("selected_obj_prop", "group", "member_types", value[1])
            if restore:
                task = lambda: self.__restore_member_types(*value)
                task_id = "set_group_member_types"
                PendingTasks.add(task, task_id, "object", id_prefix=self.get_id())
            else:
                return self.set_member_types(*value)
        elif prop_id == "open":
            return self.open(value)
        else:
            return TopLevelObject.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "member_types":
            return self._member_types_id if for_remote_update else (self._member_types,
                                                                    self._member_types_id)
        elif prop_id == "open":
            return self._is_open

        return TopLevelObject.get_property(self, prop_id, for_remote_update)

    def get_property_ids(self):

        return TopLevelObject.get_property_ids(self) + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this group.

        """

        self._bbox.flash()


class GroupManager(ObjectManager):

    def __init__(self):

        ObjectManager.__init__(self, "group", self.__create_group)

        self._id_generator = id_generator()
        self._obj_ids_to_check = set()

        main_options = {"recursive_open": False, "recursive_dissolve": False,
                        "recursive_member_selection": False, "subgroup_selection": False}
        link_options = {"allowed": True, "open_groups_only": True, "unlink_only": True}
        group_options = {"main": main_options, "member_linking": link_options}
        copier = lambda d: dict((k, dict.copy(v)) for k, v in d.items())
        GlobalData.set_default("group_options", group_options, copier)

        self._bbox_roots = {}
        self._bbox_bases = {}
        self._bbox_origins = {"persp": {}, "ortho": {}}
        self._compass_props = CompassEffect.P_pos | CompassEffect.P_rot

        self._pixel_under_mouse = None

        status_data = GlobalData["status_data"]
        mode_text = "Add selection to group"
        info_text = "LMB to pick group; RMB or <Escape> to end"
        status_data["sel_grouping_mode"] = {"mode": mode_text, "info": info_text}

        Mgr.add_app_updater("group", self.__update_groups)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)
        Mgr.add_app_updater("region_picking", self.__make_region_pickable)
        Mgr.add_app_updater("lens_type", self.__show_root)
        Mgr.expose("const_sized_group_bbox", self.__get_const_sized_bbox_origins)
        Mgr.accept("make_group_const_size", self.__make_bbox_const_size)
        Mgr.accept("update_group_bboxes", self.__update_group_bboxes)
        Mgr.accept("add_group_member", self.__add_member)
        Mgr.accept("add_group_members", self.__add_members)
        Mgr.accept("close_groups", self.__close_groups)
        Mgr.accept("prune_empty_groups", self.__prune_empty_groups)

        self._bbox_root = bbox_root = self.cam().attach_new_node("group_bbox_root")
        bbox_root.set_light_off()
        bbox_root.set_shader_off()
        bbox_root.set_bin("fixed", 52)
        bbox_root.set_depth_test(False)
        bbox_root.set_depth_write(False)
        bbox_root.node().set_bounds(OmniBoundingVolume())
        bbox_root.node().set_final(True)
        masks = Mgr.get("render_mask") | Mgr.get("picking_mask")
        root_persp = bbox_root.attach_new_node("group_bbox_root_persp")
        root_persp.show(masks)
        root_ortho = bbox_root.attach_new_node("group_bbox_root_ortho")
        root_ortho.set_scale(20.)
        root_ortho.hide(masks)
        self._bbox_roots["persp"] = root_persp
        self._bbox_roots["ortho"] = root_ortho

        add_state = Mgr.add_state
        add_state("grouping_mode", -10, self.__enter_grouping_mode, self.__exit_grouping_mode)

        exit_mode = lambda: Mgr.exit_state("grouping_mode")

        bind = Mgr.bind_state
        bind("grouping_mode", "grouping mode -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("grouping_mode", "grouping mode -> select", "escape", exit_mode)
        bind("grouping_mode", "exit grouping mode", "mouse3-up", exit_mode)
        bind("grouping_mode", "add members", "mouse1", self.__add_members)

    def __handle_viewport_resize(self):

        w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
        scale = 800. / max(w, h)
        bbox_origins = self._bbox_origins

        for group_id in self._bbox_bases:
            for origins in bbox_origins.values():
                origins[group_id].set_scale(.5 * scale)

    def __make_region_pickable(self, pickable):

        if pickable:
            self._bbox_root.wrt_reparent_to(Mgr.get("object_root"))
            bbox_origins = self._bbox_origins
            bbox_origins_persp = bbox_origins["persp"]
            bbox_origins_ortho = bbox_origins["ortho"]
            for group_id in self._bbox_bases:
                group = Mgr.get("group", group_id)
                index = int(group.get_pivot().get_shader_input("index").get_vector().x)
                bbox_origins_persp[group_id].set_shader_input("index", index)
                bbox_origins_ortho[group_id].set_shader_input("index", index)
        else:
            self._bbox_root.reparent_to(self.cam())
            self._bbox_root.clear_transform()

    def __show_root(self, lens_type):

        masks = Mgr.get("render_mask") | Mgr.get("picking_mask")

        if lens_type == "persp":
            self._bbox_roots["persp"].show(masks)
            self._bbox_roots["ortho"].hide(masks)
        else:
            self._bbox_roots["persp"].hide(masks)
            self._bbox_roots["ortho"].show(masks)

    def __create_group(self, name, member_types=None, member_types_id="any", transform=None,
                       color_unsel=(1., .5, .25, 1.)):

        member_type = ("multi" if len(member_types) > 1 else member_types[0]) if member_types else ""
        group_type = "{}_group".format(member_type) if member_type else "group"
        group_id = (group_type,) + next(self._id_generator)
        group = Group(set(member_types if member_types else []), member_types_id, group_id,
                      name, color_unsel)
        group.register(restore=False)

        if transform:
            group.get_pivot().set_transform(transform)

        return group

    def __make_bbox_const_size(self, bbox, const_size_state=True):

        group = bbox.get_toplevel_object()
        group_id = group.get_id()
        group_origin = group.get_origin()
        bbox_bases = self._bbox_bases
        bbox_origins = self._bbox_origins

        if const_size_state:
            if group_id not in bbox_bases:
                bbox_roots = self._bbox_roots
                bbox_base = bbox_roots["persp"].attach_new_node("group_bbox_base")
                origin = bbox.get_origin()
                bbox_base.set_billboard_point_world(group_origin, 2000.)
                pivot = bbox_base.attach_new_node("group_bbox_pivot")
                pivot.set_scale(100.)
                w, h = GlobalData["viewport"]["size_aux" if GlobalData["viewport"][2] == "main" else "size"]
                scale = 800. / max(w, h)
                origin_persp = origin.copy_to(pivot)
                origin_persp.set_name("group_bbox_origin_persp")
                origin_persp.set_scale(.5 * scale)
                bbox_origins["persp"][group_id] = origin_persp
                origin_ortho = origin.copy_to(bbox_roots["ortho"])
                origin_ortho.set_name("group_bbox_origin_ortho")
                origin_ortho.set_scale(.5 * scale)
                bbox_origins["ortho"][group_id] = origin_ortho
                origin_persp.set_compass(group_origin)
                bbox_bases[group_id] = bbox_base
                compass_effect = CompassEffect.make(group_origin, self._compass_props)
                origin_ortho.set_effect(compass_effect)
        else:
            if group_id in bbox_bases:
                origin_persp = bbox_origins["persp"][group_id]
                origin_persp.remove_node()
                del bbox_origins["persp"][group_id]
                origin_ortho = bbox_origins["ortho"][group_id]
                origin_ortho.remove_node()
                del bbox_origins["ortho"][group_id]
                bbox_base = bbox_bases[group_id]
                bbox_base.remove_node()
                del bbox_bases[group_id]

    def __get_const_sized_bbox_origins(self, group_id):

        if group_id in self._bbox_bases:

            bbox_origins = self._bbox_origins
            origin_persp = bbox_origins["persp"][group_id]
            origin_ortho = bbox_origins["ortho"][group_id]

            return origin_persp, origin_ortho

    def __update_group_bboxes_task(self):

        groups = set()
        sorted_groups = []

        for group_id in self._obj_ids_to_check:

            group = Mgr.get("group", group_id)

            if group:
                groups.add(group)
                groups.update(group.get_outer_groups())

        for group in groups:

            for i, grp in enumerate(sorted_groups):
                if grp in group.get_outer_groups():
                    sorted_groups.insert(i, group)
                    break

            if group not in sorted_groups:
                sorted_groups.append(group)

        for group in sorted_groups:
            group.update_bbox()

        self._obj_ids_to_check = set()

    def __update_group_bboxes(self, obj_ids):

        self._obj_ids_to_check.update(obj_ids)

        task = self.__update_group_bboxes_task
        task_id = "update_group_bboxes"
        PendingTasks.add(task, task_id, "object")

    def __close_groups(self, objs, closed_groups, deselected_members):

        for obj in objs:

            if obj.get_type() == "group" and obj.open(False):

                closed_groups.append(obj)
                members = obj.get_members()

                for member in members:
                    if member.set_selected(False, add_to_hist=False):
                        deselected_members.append(member)

                self.__close_groups(members, closed_groups, deselected_members)

    def __prune_empty_groups(self, groups, obj_data):

        empty_groups = [group for group in groups if not group.get_members()]

        if not empty_groups:
            return False

        def get_new_parent(group):

            outer_group = group.get_outermost_group(accept_self=False)

            if outer_group:
                return outer_group

            parent = group.get_parent()

            if parent and parent.get_type() == "group" and not parent.get_members():
                parent = get_new_parent(parent)

            return parent

        def dissolve_group(group, obj_data):

            data = group.get_data_to_store("deletion")
            obj_data.setdefault(group.get_id(), {}).update(data)
            new_parent = get_new_parent(group)
            new_parent_id = new_parent.get_id() if new_parent else None

            for child in group.get_children():
                child.set_parent(new_parent_id)
                data = child.get_data_to_store("prop_change", "link")
                data.update(child.get_data_to_store("prop_change", "transform"))
                obj_data.setdefault(child.get_id(), {}).update(data)

            outer_group = group.get_group()

            group.destroy(add_to_hist=False)

            if outer_group and not outer_group.get_members():
                dissolve_group(outer_group, obj_data)

        for group in empty_groups:
            dissolve_group(group, obj_data)

        return True

    def __add_member(self, obj_to_add, new_group, restore=""):

        old_group = obj_to_add.get_group()
        group_id = new_group.get_id()

        if restore:
            obj_to_add.restore_link(None, group_id)
        else:
            obj_to_add.set_group(group_id)

        children = obj_to_add.get_children()
        parent_id = new_group.get_outermost_group().get_id()

        for child in children:
            child.set_parent(parent_id)

        if not new_group.is_open():

            closed_groups = []
            deselected_members = []
            self.__close_groups([obj_to_add], closed_groups, deselected_members)

            if closed_groups:

                # make undo/redoable

                obj_data = {}
                event_data = {"objects": obj_data}

                for group in closed_groups:
                    obj_data[group.get_id()] = group.get_data_to_store("prop_change", "open")

                for member in deselected_members:
                    data = member.get_data_to_store("prop_change", "selection_state")
                    obj_data.setdefault(member.get_id(), {}).update(data)

                Mgr.do("add_history", "", event_data, update_time_id=False)

            obj_to_add_deselected = obj_to_add.set_selected(False, add_to_hist=False)

            if obj_to_add_deselected or deselected_members:

                # make undo/redoable

                obj_data = {}
                event_data = {"objects": obj_data}

                if obj_to_add_deselected:
                    data = obj_to_add.get_data_to_store("prop_change", "selection_state")
                    obj_data.setdefault(obj_to_add.get_id(), {}).update(data)

                if new_group.set_selected(add_to_hist=False):
                    data = new_group.get_data_to_store("prop_change", "selection_state")
                    obj_data[group_id] = data

                Mgr.do("add_history", "", event_data, update_time_id=False)

        if children:

            # make undo/redoable

            obj_data = {}
            event_data = {"objects": obj_data}

            for child in children:
                data = child.get_data_to_store("prop_change", "link")
                data.update(child.get_data_to_store("prop_change", "transform"))
                obj_data[child.get_id()] = data

            Mgr.do("add_history", "", event_data, update_time_id=False)

        if old_group:

            obj_data = {}

            if self.__prune_empty_groups([old_group], obj_data):
                # make undo/redoable
                event_data = {"objects": obj_data, "object_ids": set(Mgr.get("object_ids"))}
                Mgr.do("add_history", "", event_data, update_time_id=False)

    def __add_members(self, objs=None, new_group=None, add_to_hist=True, restore=""):

        if objs is None:
            objs = Mgr.get("selection_top")

        if new_group is None:
            obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)
            new_group = obj if obj and obj.get_type() == "group" else None

        if not (objs and new_group):
            return [], []

        members = []
        groups = []
        group_children = {}

        for obj in objs:

            if obj is new_group or not new_group.can_contain(obj):
                continue

            old_group = obj.get_group()

            if old_group is not new_group and new_group not in obj.get_descendants():

                members.append(obj)

                if obj.get_type() == "group":
                    groups.append(obj)
                    group_children[obj] = obj.get_children()

        if not members:
            return [], []

        if add_to_hist:
            Mgr.do("update_history_time")

        member_children = []

        for member in members:
            member_children.extend(member.get_children())

        for member in members:
            if member not in groups:
                self.__add_member(member, new_group, restore)

        for group in groups:
            if group.get_members():
                del group_children[group]
                self.__add_member(group, new_group, restore)
            else:
                members.remove(group)

        group_children = [child for g, c in group_children.items() for child in c]
        new_group_id = new_group.get_id()

        for child in group_children:
            child.set_parent(new_group_id)

        if add_to_hist:

            if len(members) == 1:

                names = (new_group.get_name(), members[0].get_name())
                event_descr = 'Add to group "{}":\n    "{}"'.format(*names)

            else:

                event_descr = 'Add to group "{}":\n'.format(new_group.get_name())

                for member in members:
                    event_descr += '\n    "{}"'.format(member.get_name())

        else:

            event_descr = ''

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}

        for member in members:
            data = member.get_data_to_store("prop_change", "link")
            data.update(member.get_data_to_store("prop_change", "transform"))
            obj_data[member.get_id()] = data

        for child in group_children:
            data = child.get_data_to_store("prop_change", "link")
            data.update(child.get_data_to_store("prop_change", "transform"))
            obj_data.setdefault(child.get_id(), {}).update(data)

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        return members, member_children

    def __enter_grouping_mode(self, prev_state_id, is_active):

        Mgr.add_task(self.__update_cursor, "update_grouping_cursor")

        if GlobalData["active_transform_type"]:
            GlobalData["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")

        Mgr.update_app("status", ["sel_grouping_mode"])

        if not is_active:

            def handler(obj_ids):

                if obj_ids:
                    group = Mgr.get("object", obj_ids[0])
                    self.__add_members(new_group=group)

            Mgr.update_remotely("selection_by_name", "", "Pick group",
                                ["group"], False, "Pick", handler)

    def __exit_grouping_mode(self, next_state_id, is_active):

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_grouping_cursor")
        Mgr.set_cursor("main")

        if not is_active:
            Mgr.update_remotely("selection_by_name", "default")

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __update_groups(self, update_type, value=None):

        group_options = GlobalData["group_options"]["main"]

        if update_type == "create":

            if GlobalData["active_obj_level"] != "top":
                return

            selection = Mgr.get("selection_top")

            if not selection:
                return

            group = Mgr.do("create_group", "")

            if len(selection) == 1:

                common_group = selection[0].get_group()

                if not common_group:
                    common_ancestor = selection[0].get_parent()

            else:

                common_group = selection[0].get_common_group(selection[1:])

                if not common_group:
                    common_ancestor = selection[0].get_common_link_target(selection[1:])

            if common_group:
                group.set_group(common_group.get_id())
                group.set_member_types(*common_group.get_property("member_types"))
            elif common_ancestor:
                group.set_parent(common_ancestor.get_id())

            Mgr.do("update_history_time")
            members, member_children = self.__add_members(selection, group, add_to_hist=False)

            task = group.center_pivot # stores member & child transform data
            task_id = "center_group_pivot"
            PendingTasks.add(task, task_id, "object")
            obj_ids = [child.get_id() for child in member_children]
            obj_ids.append(group.get_id())
            Mgr.do("update_obj_link_viz", obj_ids)

            namelist = GlobalData["obj_names"]
            search_pattern = r"^group\s*(\d+)$"
            naming_pattern = "group {:04d}"
            name = get_unique_name("", namelist, search_pattern, naming_pattern)
            group.set_name(name)

            # make undo/redoable

            event_descr = 'Create group "{}":\n'.format(name)

            for member in members:
                event_descr += '\n    "{}"'.format(member.get_name())

            obj_data = {}
            event_data = {"objects": obj_data}
            obj_data[group.get_id()] = group.get_data_to_store("creation")

            objs = selection[:]
            objs.append(group)
            selection.replace([group], add_to_hist=False)

            for obj in objs:
                data = obj.get_data_to_store("prop_change", "selection_state")
                obj_data.setdefault(obj.get_id(), {}).update(data)

            event_data["object_ids"] = set(Mgr.get("object_ids"))
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        elif update_type == "set_member_types":

            groups = Mgr.get("selection_top")[:]
            member_types = set()

            if value != "any":

                for type_id in value.split("+"):
                    member_types.add(type_id)

            def check_compatibility(group, groups, incompatible_groups):

                if group in incompatible_groups:
                    return False

                outer_group = group.get_group()

                if outer_group:
                    if outer_group in groups:
                        if not check_compatibility(outer_group, groups, incompatible_groups):
                            incompatible_groups.append(group)
                            return False
                    elif not outer_group.can_contain(member_types=member_types):
                        incompatible_groups.append(group)
                        return False

                return True

            incompatible_groups = []

            for group in groups:
                check_compatibility(group, groups, incompatible_groups)

            for group in incompatible_groups:
                groups.remove(group)

            sorted_groups = []
            removed_members = set()

            for group in groups:

                for i, grp in enumerate(sorted_groups):
                    if grp in group.get_outer_groups():
                        sorted_groups.insert(i, group)
                        break

                if group not in sorted_groups:
                    sorted_groups.append(group)

            for group in sorted_groups:
                if not group.set_member_types(member_types, value, False, removed_members):
                    groups.remove(group)

            if not groups:
                return

            Mgr.update_remotely("selected_obj_prop", "group", "member_types", value)

            # make undo/redoable

            Mgr.do("update_history_time")
            obj_data = {}
            event_data = {"objects": obj_data}
            event_descr = 'Change member type of groups:\n'

            for group in groups:
                event_descr += '\n    "{}"'.format(group.get_name())
                data = group.get_data_to_store("prop_change", "member_types")
                obj_data.setdefault(group.get_id(), {}).update(data)

            for member in removed_members:
                data = member.get_data_to_store("prop_change", "link")
                data.update(member.get_data_to_store("prop_change", "transform"))
                obj_data.setdefault(member.get_id(), {}).update(data)

            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        elif update_type == "open":

            groups = Mgr.get("selection_top")
            changed_groups = []
            deselected_members = []

            recursive_group_open = group_options["recursive_open"]

            if recursive_group_open:

                def open_subgroups(group, changed_groups):

                    for member in group.get_members():
                        if member.get_type() == "group" and member.open():
                            changed_groups.append(member)
                            open_subgroups(member, changed_groups)

            def close_subgroups(group, changed_groups, deselected_members):

                for member in group.get_members():
                    if member.set_selected(False, add_to_hist=False):
                        deselected_members.append(member)
                    if member.get_type() == "group" and member.open(False):
                        changed_groups.append(member)
                        close_subgroups(member, changed_groups, deselected_members)

            for group in groups:

                if group.open(value):

                    changed_groups.append(group)

                    if not value:
                        close_subgroups(group, changed_groups, deselected_members)
                    elif recursive_group_open:
                        open_subgroups(group, changed_groups)

            if not changed_groups:
                return

            # make undo/redoable

            Mgr.do("update_history_time")
            val_descr = "Open" if value else "Close"
            grp_count = len(changed_groups)

            if grp_count == 1:

                event_descr = '{} group "{}"'.format(val_descr, changed_groups[0].get_name())

            else:

                event_descr = '{} {:d} groups:\n'.format(val_descr, grp_count)

                for group in changed_groups:
                    event_descr += '\n    "{}"'.format(group.get_name())

            obj_data = {}
            event_data = {"objects": obj_data}

            for group in changed_groups:
                obj_data[group.get_id()] = group.get_data_to_store("prop_change", "open")

            for member in deselected_members:
                data = member.get_data_to_store("prop_change", "selection_state")
                obj_data.setdefault(member.get_id(), {}).update(data)

            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        elif update_type == "select_members":

            groups = Mgr.get("selection_top")[:]
            selected_members = []
            groups_to_open = []
            groups_to_deselect = groups[:]

            recursive_selection = group_options["recursive_member_selection"]
            subgroup_selection = group_options["subgroup_selection"]

            if recursive_selection:

                def select_subgroup_members(members, selected_members, groups_to_open,
                                            groups_to_deselect):

                    for member in members:

                        if member.get_type() == "group":

                            subgroup_members = member.get_members()

                            for subgr_member in subgroup_members:
                                if subgr_member in groups_to_deselect:
                                    if subgroup_selection:
                                        groups_to_deselect.remove(subgr_member)
                                elif not (subgr_member.get_type() == "group" and not subgroup_selection) \
                                        and subgr_member.set_selected(add_to_hist=False):
                                    selected_members.append(subgr_member)

                            if not member.is_open():
                                groups_to_open.append(member)

                            select_subgroup_members(subgroup_members, selected_members,
                                                    groups_to_open, groups_to_deselect)

            for group in groups:

                members = group.get_members()

                for member in members:
                    if member in groups_to_deselect:
                        if subgroup_selection:
                            groups_to_deselect.remove(member)
                    elif not (member.get_type() == "group" and not subgroup_selection) \
                            and member.set_selected(add_to_hist=False):
                        selected_members.append(member)

                if not group.is_open():
                    groups_to_open.append(group)

                if recursive_selection:
                    select_subgroup_members(members, selected_members, groups_to_open,
                                            groups_to_deselect)

            if not selected_members:
                return

            for group in groups_to_open:
                group.open()

            for group in groups_to_deselect:
                group.set_selected(False, add_to_hist=False)

            # make undo/redoable

            Mgr.do("update_history_time")
            member_count = len(selected_members)

            if member_count == 1:

                event_descr = 'Select "{}"'.format(selected_members[0].get_name())

            else:

                event_descr = 'Select {:d} group members:\n'.format(member_count)

                for member in selected_members:
                    event_descr += '\n    "{}"'.format(member.get_name())

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in selected_members + groups_to_deselect:
                data = obj.get_data_to_store("prop_change", "selection_state")
                obj_data[obj.get_id()] = data

            for group in groups_to_open:
                data = group.get_data_to_store("prop_change", "open")
                obj_data.setdefault(group.get_id(), {}).update(data)

            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        elif update_type == "dissolve":

            def get_outer_group(group, groups_to_dissolve):

                outer_group = group.get_group()

                if outer_group and outer_group in groups_to_dissolve:
                    outer_group = get_outer_group(outer_group, groups_to_dissolve)

                return outer_group

            def get_new_parent(group, groups_to_dissolve):

                outer_group = get_outer_group(group, groups_to_dissolve)

                if outer_group:
                    return outer_group

                parent = group.get_parent()

                if parent in groups_to_dissolve:
                    parent = get_new_parent(parent, groups_to_dissolve)

                return parent

            groups = Mgr.get("selection_top")[:]

            if not groups:
                return

            if group_options["recursive_dissolve"]:

                def get_subgroups(group, groups_to_dissolve):

                    for member in group.get_members():
                        if member.get_type() == "group":
                            groups_to_dissolve.add(member)
                            get_subgroups(member, groups_to_dissolve)

                groups_to_dissolve = set(groups)

                for group in groups:
                    get_subgroups(group, groups_to_dissolve)

                groups = list(groups_to_dissolve)

            members = []
            selected_members = []
            children = []

            for group in groups:

                c = group.get_children()
                children.extend(c)
                new_parent = get_new_parent(group, groups)
                new_parent_id = new_parent.get_id() if new_parent else None

                for child in c:
                    child.set_parent(new_parent_id)

                m = group.get_members()
                members.extend(m)
                new_group = get_outer_group(group, groups)
                new_group_id = new_group.get_id() if new_group else None

                if new_group:
                    for member in m:
                        member.set_group(new_group_id)
                else:
                    for member in m:
                        member.set_parent(new_parent_id)

            for member in members:
                # select all ungrouped objects for convenience
                if member.set_selected(add_to_hist=False):
                    selected_members.append(member)

            # make undo/redoable

            Mgr.do("update_history_time")
            grp_count = len(groups)

            if grp_count == 1:

                event_descr = 'Dissolve group "{}"'.format(groups[0].get_name())

            else:

                event_descr = 'Dissolve {:d} groups:\n'.format(grp_count)

                for group in groups:
                    event_descr += '\n    "{}"'.format(group.get_name())

            obj_data = {}
            event_data = {"objects": obj_data}

            for obj in children + members:
                data = obj.get_data_to_store("prop_change", "link")
                data.update(obj.get_data_to_store("prop_change", "transform"))
                obj_data.setdefault(obj.get_id(), {}).update(data)

            for member in selected_members:
                data = member.get_data_to_store("prop_change", "selection_state")
                obj_data.setdefault(member.get_id(), {}).update(data)

            for group in groups:
                data = group.get_data_to_store("deletion")
                obj_data.setdefault(group.get_id(), {}).update(data)
                group.destroy(add_to_hist=False)

            event_data["object_ids"] = set(Mgr.get("object_ids"))
            Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        elif update_type == "remove_members":

            if GlobalData["active_obj_level"] != "top":
                return

            selection = Mgr.get("selection_top")

            if not selection:
                return

            groups = set()
            ungrouped_members = []

            for obj in selection:

                group = obj.get_group()

                if group:
                    groups.add(group)
                    obj.set_group(None)
                    ungrouped_members.append(obj)

            if not ungrouped_members:
                return

            # make undo/redoable

            Mgr.do("update_history_time")
            obj_data = {}
            event_data = {"objects": obj_data}

            if len(ungrouped_members) == 1:

                event_descr = 'Ungroup "{}"'.format(ungrouped_members[0].get_name())

            else:

                event_descr = 'Ungroup objects:\n'

                for obj in ungrouped_members:
                    event_descr += '\n    "{}"'.format(obj.get_name())

            for obj in ungrouped_members:
                data = obj.get_data_to_store("prop_change", "link")
                data.update(obj.get_data_to_store("prop_change", "transform"))
                obj_data[obj.get_id()] = data

            if self.__prune_empty_groups(groups, obj_data):
                event_data["object_ids"] = set(Mgr.get("object_ids"))

            Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(GroupManager)
