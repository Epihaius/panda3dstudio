from .base import *


class HierarchyManager(BaseObject):

    def __init__(self):

        self._obj_link_viz_nps = NodePathCollection()
        self._obj_link_viz = {}

        self._draw_plane = None
        self._link_start_pos = None
        self._link_geom = None
        self._obj_to_link = None

        self._pixel_under_mouse = VBase4()

        status_data = GlobalData["status_data"]
        mode_text = "Link selection"
        info_text = "LMB to pick parent object; RMB or <Escape> to end"
        status_data["sel_linking_mode"] = {"mode": mode_text, "info": info_text}
        mode_text = "Link object"
        info_text = "LMB-drag over first (child) object and release LMB over" \
                    " second (parent) object; RMB or <Escape> to end"
        status_data["obj_linking_mode"] = {"mode": mode_text, "info": info_text}
        mode_text = "Unlink object"
        info_text = "LMB to pick child object; RMB or <Escape> to end"
        status_data["obj_unlinking_mode"] = {"mode": mode_text, "info": info_text}

        GlobalData.set_default("object_links_shown", False)
        GlobalData.set_default("object_linking_mode", "")
        GlobalData.set_default("transform_target_type", "all")
        Mgr.accept("add_obj_link_viz", self.__add_obj_link_viz)
        Mgr.accept("remove_obj_link_viz", self.__remove_obj_link_viz)
        Mgr.accept("update_obj_link_viz", self.__update_obj_link_viz)
        Mgr.accept("update_xform_target_type", self.__update_xform_target_type)
        Mgr.add_app_updater("object_link_viz", self.__show_object_links)
        Mgr.add_app_updater("selection_unlinking", self.__unlink_selection)
        Mgr.add_app_updater("transform_target_type", self.__update_pivot_viz)
        Mgr.add_app_updater("geom_reset", self.__reset_geoms)
        Mgr.add_app_updater("pivot_reset", self.__reset_pivots)

    def setup(self):

        add_state = Mgr.add_state
        add_state("object_linking_mode", -10, self.__enter_linking_mode,
                  self.__exit_linking_mode)
        add_state("object_link_creation", -11)

        cancel_link_creation = lambda: self.__finalize_object_linking(cancel=True)

        def exit_mode():

            Mgr.exit_state("object_linking_mode")
            GlobalData["object_linking_mode"] = ""

        bind = Mgr.bind_state
        bind("object_linking_mode", "link objects -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("object_linking_mode", "link objects -> select", "escape", exit_mode)
        bind("object_linking_mode", "exit object linking mode", "mouse3-up", exit_mode)
        bind("object_linking_mode", "handle linking", "mouse1", self.__handle_linking)
        bind("object_link_creation", "quit link creation", "escape", cancel_link_creation)
        bind("object_link_creation", "cancel link creation", "mouse3-up", cancel_link_creation)
        bind("object_link_creation", "finalize link creation",
             "mouse1-up", self.__finalize_object_linking)

        return True

    def __enter_linking_mode(self, prev_state_id, is_active):

        if prev_state_id == "object_link_creation":
            return

        Mgr.add_task(self.__update_cursor, "update_linking_cursor")

        if GlobalData["active_transform_type"]:
            GlobalData["active_transform_type"] = ""
            Mgr.update_app("active_transform_type", "")

        if GlobalData["active_obj_level"] != "top":
            GlobalData["active_obj_level"] = "top"
            Mgr.update_app("active_obj_level")

        Mgr.update_app("status", GlobalData["object_linking_mode"])

    def __exit_linking_mode(self, next_state_id, is_active):

        if next_state_id == "object_link_creation":
            return

        self._pixel_under_mouse = VBase4() # force an update of the cursor next
                                           # time self.__update_cursor() is
                                           # called
        Mgr.remove_task("update_linking_cursor")
        Mgr.set_cursor("main")

    def __show_object_links(self):

        show_links = GlobalData["object_links_shown"]

        if show_links:
            self._obj_link_viz_nps.show()
        else:
            self._obj_link_viz_nps.hide()

    def __get_linkability(self, obj_to_link, target_obj):

        target_is_group = target_obj and target_obj.get_type() == "group"
        objs = obj_to_link.get_descendants() + [obj_to_link]
        member_linking = GlobalData["group_options"]["member_linking"]

        if (target_is_group and member_linking["allowed"]
                and not member_linking["unlink_only"]
                and (target_obj.is_open() or not member_linking["open_groups_only"])):
            objs += [obj_to_link.get_group()]
            linkable = target_obj.can_contain(obj_to_link) and target_obj not in objs
            link_type = "member"
        else:
            objs += [obj_to_link.get_parent()]
            group = target_obj.get_group() if target_obj else None
            linkable = not (group or target_obj in objs)
            link_type = "child"

        return linkable, link_type

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            self._pixel_under_mouse = pixel_under_mouse
            cursor_name = "main"

            if pixel_under_mouse != VBase4():

                obj_to_link = self._obj_to_link

                if obj_to_link:

                    target_obj = Mgr.get("object", pixel_color=pixel_under_mouse)
                    linkable, link_type = self.__get_linkability(obj_to_link, target_obj)

                    if target_obj and linkable:
                        cursor_name = "link"
                    else:
                        cursor_name = "no_link"

                else:

                    cursor_name = "select"

            Mgr.set_cursor(cursor_name)

        return task.cont

    def __create_obj_link_geom(self, start_pos):

        self._link_start_pos = start_pos

        vertex_format = GeomVertexFormat.get_v3cpt2()

        vertex_data = GeomVertexData("link_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")
        uv_writer = GeomVertexWriter(vertex_data, "texcoord")

        for i in range(2):
            pos_writer.add_data3f(start_pos)
            uv_writer.add_data2f(0., 0.)

        col_writer.add_data4f(.25, .25, .25, 1.)
        col_writer.add_data4f(1., 1., 1., 1.)

        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(2)

        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node = GeomNode("object_link")
        node.add_geom(lines_geom)
        link_geom = self.world.attach_new_node(node)
        link_geom.set_bin("fixed", 100)
        link_geom.set_depth_test(False)
        link_geom.set_depth_write(False)
        tex = Mgr.load_tex(GFX_PATH + "marquee.png")
        link_geom.set_texture(tex)
        link_geom.hide(Mgr.get("picking_masks")["all"])
        self._link_geom = link_geom

    def __add_obj_link_viz(self, child, parent):

        child_id = child.get_id()
        parent_pivot = parent.get_pivot()

        if child_id in self._obj_link_viz:
            link_geom = self._obj_link_viz[child_id]
            self._obj_link_viz_nps.remove_path(link_geom)
            link_geom.remove_node()

        vertex_format = GeomVertexFormat.get_v3cp()

        vertex_data = GeomVertexData("link_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        pos_writer.add_data3f(0., 0., 0.)
        col_writer.add_data4f(1., 1., 1., 1.)
        pos_writer.add_data3f(child.get_pivot().get_pos(parent_pivot))
        col_writer.add_data4f(.25, .25, .25, 1.)

        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(2)

        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node = GeomNode("object_link")
        node.add_geom(lines_geom)
        link_geom = parent_pivot.attach_new_node(node)
        link_geom.set_light_off()
        link_geom.set_shader_off()
        link_geom.set_bin("fixed", 100)
        link_geom.set_depth_test(False)
        link_geom.set_depth_write(False)
        link_geom.hide(Mgr.get("picking_masks")["all"])
        self._obj_link_viz[child_id] = link_geom
        self._obj_link_viz_nps.add_path(link_geom)

        if not GlobalData["object_links_shown"]:
            link_geom.hide()

    def __remove_obj_link_viz(self, child_id):

        if child_id not in self._obj_link_viz:
            return

        link_geom = self._obj_link_viz[child_id]
        self._obj_link_viz_nps.remove_path(link_geom)
        link_geom.remove_node()
        del self._obj_link_viz[child_id]

    def __update_obj_link_viz(self, obj_ids=None, force_update_children=False):

        def task():

            obj_transf_info = obj_ids if obj_ids else Mgr.get("obj_transf_info")
            obj_link_viz = self._obj_link_viz
            update_children = GlobalData["transform_target_type"] in ("pivot",
                              "no_children") or force_update_children

            for obj_id in obj_transf_info:

                if obj_id in obj_link_viz:

                    link_viz = obj_link_viz[obj_id]
                    obj = Mgr.get("object", obj_id)
                    parent = obj.get_parent()
                    vertex_data = link_viz.node().modify_geom(0).modify_vertex_data()
                    pos_writer = GeomVertexWriter(vertex_data, "vertex")
                    pos_writer.set_row(1)
                    pivot = obj.get_pivot()
                    pos_writer.set_data3f(pivot.get_pos(parent.get_pivot()))

                    if update_children:
                        for child in obj.get_children():
                            child_link_viz = obj_link_viz[child.get_id()]
                            vertex_data = child_link_viz.node().modify_geom(0).modify_vertex_data()
                            pos_writer = GeomVertexWriter(vertex_data, "vertex")
                            pos_writer.set_row(1)
                            pos_writer.set_data3f(child.get_pivot().get_pos(pivot))

                elif update_children:

                    obj = Mgr.get("object", obj_id)
                    pivot = obj.get_pivot()

                    for child in obj.get_children():
                        child_link_viz = obj_link_viz[child.get_id()]
                        vertex_data = child_link_viz.node().modify_geom(0).modify_vertex_data()
                        pos_writer = GeomVertexWriter(vertex_data, "vertex")
                        pos_writer.set_row(1)
                        pos_writer.set_data3f(child.get_pivot().get_pos(pivot))

        task_id = "obj_link_viz_update"
        PendingTasks.add(task, task_id, "object")

    def __draw_obj_link(self, task):

        screen_pos = self.mouse_watcher.get_mouse()
        cam = self.cam()
        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)
        point = Point3()
        self._draw_plane.intersects_line(point, near_point, far_point)
        length = (point - self._link_start_pos).length()

        if self.cam.lens_type == "ortho":
            length /= 40. * self.cam.zoom

        vertex_data = self._link_geom.node().modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.set_row(1)
        pos_writer.set_data3f(point)
        uv_writer = GeomVertexWriter(vertex_data, "texcoord")
        uv_writer.set_row(1)
        uv_writer.set_data2f(length * 5., 1.)

        return task.cont

    def __handle_linking(self):

        linking_mode = GlobalData["object_linking_mode"]

        if linking_mode == "sel_linking_mode":
            self.__link_selection()
        elif linking_mode == "obj_linking_mode":
            self.__init_object_linking()
        elif linking_mode == "obj_unlinking_mode":
            self.__unlink_object()

    def __init_object_linking(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not obj:
            return

        cam = self.cam()
        lens_type = self.cam.lens_type
        self._obj_to_link = obj
        normal = self.world.get_relative_vector(cam, Vec3.forward())
        point = self.world.get_relative_point(cam, Point3(0., 10., 0.))
        self._draw_plane = Plane(normal, point)
        pivot_pos = obj.get_pivot().get_pos(self.world)

        if lens_type == "persp":
            line_start = cam.get_pos(self.world)
        else:
            line_start = pivot_pos + self.world.get_relative_vector(cam, Vec3(0., -100., 0.))

        start_pos = Point3()
        self._draw_plane.intersects_line(start_pos, line_start, pivot_pos)
        self.__create_obj_link_geom(start_pos)

        Mgr.do("enable_view_tiles", False)
        Mgr.enter_state("object_link_creation")
        Mgr.add_task(self.__draw_obj_link, "draw_link", sort=3)
        Mgr.set_cursor("no_link")

    def __finalize_object_linking(self, cancel=False):

        if not cancel:
            self.__link_picked_object()

        Mgr.remove_task("draw_link")
        Mgr.enter_state("object_linking_mode")
        Mgr.set_cursor("main" if self._pixel_under_mouse == VBase4() else "select")
        Mgr.do("enable_view_tiles")

        self._draw_plane = None
        self._link_start_pos = None
        self._link_geom.remove_node()
        self._link_geom = None
        self._obj_to_link = None

    def __link_object(self, obj_to_link, new_target, link_type):

        old_target = obj_to_link.get_link_target()
        old_target_is_group = old_target and old_target.get_type() == "group"
        target_id = new_target.get_id()

        if link_type == "child":

            obj_to_link.set_parent(target_id)

        else:

            obj_to_link.set_group(target_id)
            children = obj_to_link.get_children()
            parent_id = new_target.get_outermost_group().get_id()

            for child in children:
                child.set_parent(parent_id)

        if link_type == "member" and not new_target.is_open():

            closed_groups = []
            deselected_members = []
            Mgr.do("close_groups", [obj_to_link], closed_groups, deselected_members)

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

            obj_to_link_deselected = obj_to_link.set_selected(False, add_to_hist=False)

            if obj_to_link_deselected or deselected_members:

                # make undo/redoable

                obj_data = {}
                event_data = {"objects": obj_data}

                if obj_to_link_deselected:
                    data = obj_to_link.get_data_to_store("prop_change", "selection_state")
                    obj_data.setdefault(obj_to_link.get_id(), {}).update(data)

                if new_target.set_selected(add_to_hist=False):
                    data = new_target.get_data_to_store("prop_change", "selection_state")
                    obj_data[target_id] = data

                Mgr.do("add_history", "", event_data, update_time_id=False)

        if link_type == "member" and children:

            # make undo/redoable

            obj_data = {}
            event_data = {"objects": obj_data}

            for child in children:
                data = child.get_data_to_store("prop_change", "link")
                data.update(child.get_data_to_store("prop_change", "transform"))
                obj_data[child.get_id()] = data

            Mgr.do("add_history", "", event_data, update_time_id=False)

        if old_target_is_group:

            obj_data = {}

            if Mgr.do("prune_empty_groups", [old_target], obj_data):
                # make undo/redoable
                event_data = {"objects": obj_data, "object_ids": set(Mgr.get("object_ids"))}
                Mgr.do("add_history", "", event_data, update_time_id=False)

    def __link_picked_object(self):

        obj_to_link = self._obj_to_link

        if not obj_to_link:
            return

        new_target = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not new_target:
            return

        linkable, link_type = self.__get_linkability(obj_to_link, new_target)

        if not linkable:
            return

        Mgr.do("update_history_time")

        self.__link_object(obj_to_link, new_target, link_type)

        # make undo/redoable
        data = obj_to_link.get_data_to_store("prop_change", "link")
        data.update(obj_to_link.get_data_to_store("prop_change", "transform"))
        obj_data = {obj_to_link.get_id(): data}
        names = (obj_to_link.get_name(), new_target.get_name())

        if link_type == "child":
            event_descr = 'Link "%s"\nto "%s"' % names
        else:
            event_descr = 'Add to group "%s":\n    "%s"' % names[::-1]

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        new_target_is_group = new_target.get_type() == "group"

        if link_type == "child" and not (new_target_is_group and not new_target.get_members()):
            new_target.display_link_effect()

    def __link_selection(self):

        new_target = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not new_target:
            return

        selection = Mgr.get("selection", "top")

        if not selection:
            return

        children = []
        members = []
        groups = []
        group_children = {}

        for obj in selection:

            linkable, link_type = self.__get_linkability(obj, new_target)

            if not linkable:
                continue

            if obj.get_type() == "group":
                groups.append(obj)
                group_children[obj] = obj.get_children()

            if link_type == "child":
                children.append(obj)
            else:
                members.append(obj)

        if not (children or members):
            return

        Mgr.do("update_history_time")

        for child in children:
            if child not in groups:
                self.__link_object(child, new_target, "child")

        for member in members:
            if member not in groups:
                self.__link_object(member, new_target, "member")

        for group in groups:
            if group in children:
                if group.get_members():
                    del group_children[group]
                    self.__link_object(group, new_target, "child")
                else:
                    children.remove(group)
            else:
                if group.get_members():
                    del group_children[group]
                    self.__link_object(group, new_target, "member")
                else:
                    members.remove(group)

        group_children = [child for group, c in group_children.iteritems() for child in c]
        new_target_id = new_target.get_id()

        for child in group_children:
            child.set_parent(new_target_id)

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}

        for obj in children + members:
            data = obj.get_data_to_store("prop_change", "link")
            data.update(obj.get_data_to_store("prop_change", "transform"))
            obj_data[obj.get_id()] = data

        for child in group_children:
            data = child.get_data_to_store("prop_change", "link")
            data.update(child.get_data_to_store("prop_change", "transform"))
            obj_data.setdefault(child.get_id(), {}).update(data)

        if children:

            if len(children) == 1:

                names = (children[0].get_name(), new_target.get_name())
                event_descr = 'Link "%s"\nto "%s"' % names

            else:

                event_descr = 'Link objects to "%s":\n' % new_target.get_name()

                for child in children:
                    event_descr += '\n    "%s"' % child.get_name()

        elif members:

            if len(members) == 1:

                names = (new_target.get_name(), members[0].get_name())
                event_descr = 'Add to group "%s":\n    "%s"' % names

            else:

                event_descr = 'Add to group "%s":\n' % new_target.get_name()

                for member in members:
                    event_descr += '\n    "%s"' % member.get_name()

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        new_target_is_group = new_target.get_type() == "group"

        if children and not (new_target_is_group and not new_target.get_members()):
            new_target.display_link_effect()

    def __unlink_object(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not obj:
            return

        affect_group_members = GlobalData["group_options"]["member_linking"]["allowed"]
        ungrouped = False
        unlinked = False

        group = obj.get_group()
        groups = [group] if group else []

        if group:
            if affect_group_members and obj.set_group(None):
                ungrouped = True
        elif obj.set_parent(None):
            unlinked = True

        change = ungrouped or unlinked

        if not change:
            return

        # make undo/redoable

        Mgr.do("update_history_time")
        obj_data = {}
        event_data = {"objects": obj_data}

        if unlinked:
            event_descr = 'Unlink "%s"' % obj.get_name()
        elif ungrouped:
            event_descr = 'Ungroup "%s"' % obj.get_name()

        data = obj.get_data_to_store("prop_change", "link")
        data.update(obj.get_data_to_store("prop_change", "transform"))
        obj_data[obj.get_id()] = data

        if Mgr.do("prune_empty_groups", groups, obj_data):
            event_data["object_ids"] = set(Mgr.get("object_ids"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __unlink_selection(self):

        if GlobalData["active_obj_level"] != "top":
            return

        groups = set()
        affect_group_members = GlobalData["group_options"]["member_linking"]["allowed"]
        ungrouped_members = []
        unlinked_children = []

        for obj in Mgr.get("selection", "top"):

            group = obj.get_group()

            if group:

                groups.add(group)

                if affect_group_members and obj.set_group(None):
                    ungrouped_members.append(obj)

            elif obj.set_parent(None):

                unlinked_children.append(obj)

        changed_objs = ungrouped_members + unlinked_children

        if not changed_objs:
            return

        # make undo/redoable

        Mgr.do("update_history_time")
        obj_data = {}
        event_data = {"objects": obj_data}

        if len(unlinked_children) == 1:

            event_descr = 'Unlink "%s"' % unlinked_children[0].get_name()

        elif unlinked_children:

            event_descr = 'Unlink objects:\n'

            for obj in unlinked_children:
                event_descr += '\n    "%s"' % obj.get_name()

        if ungrouped_members:

            if unlinked_children:
                event_descr += '\n\n'
            else:
                event_descr = ''

            if len(ungrouped_members) == 1:

                event_descr += 'Ungroup "%s"' % ungrouped_members[0].get_name()

            else:

                event_descr += 'Ungroup objects:\n'

                for obj in ungrouped_members:
                    event_descr += '\n    "%s"' % obj.get_name()

        for obj in changed_objs:
            data = obj.get_data_to_store("prop_change", "link")
            data.update(obj.get_data_to_store("prop_change", "transform"))
            obj_data[obj.get_id()] = data

        if Mgr.do("prune_empty_groups", groups, obj_data):
            event_data["object_ids"] = set(Mgr.get("object_ids"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __update_pivot_viz(self):

        target_type = GlobalData["transform_target_type"]
        Mgr.do("show_pivot_gizmos", target_type in ("geom", "pivot"))

    def __update_xform_target_type(self, objs, reset=False):

        new_target_type = "all" if reset else GlobalData["transform_target_type"]
        old_target_type = GlobalData["transform_target_type"] if reset else "all"

        if new_target_type == old_target_type:
            return

        obj_root = Mgr.get("object_root")

        if new_target_type == "pivot":

            for obj in objs:

                obj.get_origin().wrt_reparent_to(obj_root)

                for child in obj.get_children():
                    child.get_pivot().wrt_reparent_to(obj_root)

                if obj.get_type() == "group":
                    for member in obj.get_members():
                        member.get_pivot().wrt_reparent_to(obj_root)

        elif new_target_type == "no_children":

            for obj in objs:

                for child in obj.get_children():
                    child.get_pivot().wrt_reparent_to(obj_root)

                if obj.get_group() in objs:
                    obj.get_pivot().wrt_reparent_to(obj_root)

        elif old_target_type == "pivot":

            for obj in objs:

                pivot = obj.get_pivot()
                obj.get_origin().wrt_reparent_to(pivot)

                for child in obj.get_children():
                    child.get_pivot().wrt_reparent_to(pivot)

                if obj.get_type() == "group":
                    for member in obj.get_members():
                        member.get_pivot().wrt_reparent_to(pivot)

        elif old_target_type == "no_children":

            for obj in objs:

                if obj.get_group() in objs:
                    obj.get_pivot().wrt_reparent_to(obj.get_parent_pivot())

                pivot = obj.get_pivot()

                for child in obj.get_children():
                    child.get_pivot().wrt_reparent_to(pivot)

    def __reset_geoms(self):

        sel = Mgr.get("selection", "top")

        if not sel:
            return

        for obj in sel:

            obj.get_origin().clear_transform(obj.get_pivot())
            obj.update_group_bbox()

            if obj.get_type() == "group":
                Mgr.do("update_group_bboxes", [obj.get_id()])

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")
        obj_count = len(sel)

        if obj_count > 1:

            event_descr = "Reset %d objects' geometry:\n" % obj_count

            for obj in sel:
                event_descr += '\n    "%s"' % obj.get_name()

        else:

            event_descr = 'Reset "%s" geometry' % sel[0].get_name()

        for obj in sel:
            data = obj.get_data_to_store("prop_change", "origin_transform")
            obj_data[obj.get_id()] = data

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __reset_pivots(self):

        sel = Mgr.get("selection", "top")

        if not sel:
            return

        members = []

        for obj in sel:

            obj_root = Mgr.get("object_root")

            for child in obj.get_children():
                child.get_pivot().wrt_reparent_to(obj_root)

            if obj.get_type() == "group":

                m = obj.get_members()
                members.extend(m)

                for member in m:
                    member.get_pivot().wrt_reparent_to(obj_root)

            pivot = obj.get_pivot()
            origin = obj.get_origin()
            pivot.clear_transform(origin)
            origin.clear_transform(pivot)

            for child in obj.get_children():
                child.get_pivot().wrt_reparent_to(pivot)

            if obj.get_type() == "group":
                for member in m:
                    member.get_pivot().wrt_reparent_to(pivot)

        cs_type = GlobalData["coord_sys_type"]
        cs_obj = Mgr.get("coord_sys_obj")
        tc_type = GlobalData["transf_center_type"]
        tc_obj = Mgr.get("transf_center_obj")

        if cs_obj in sel:
            Mgr.do("notify_coord_sys_transformed")
            Mgr.do("update_coord_sys")

        if GlobalData["active_obj_level"] == "top":

            if tc_type == "cs_origin":
                if cs_type == "object" and cs_obj in sel:
                    Mgr.do("set_transf_gizmo_pos", cs_obj.get_pivot().get_pos())
            elif tc_type == "object" and tc_obj in sel:
                Mgr.do("set_transf_gizmo_pos", tc_obj.get_pivot().get_pos())

        task = lambda: Mgr.get("selection").update()
        PendingTasks.add(task, "update_selection", "ui")
        self.__update_obj_link_viz([obj.get_id() for obj in sel], True)

        # make undo/redoable

        obj_data = {}
        event_data = {"objects": obj_data}
        Mgr.do("update_history_time")
        obj_count = len(sel)

        if obj_count > 1:

            event_descr = "Reset %d objects' pivots:\n" % obj_count

            for obj in sel:
                event_descr += '\n    "%s"' % obj.get_name()

        else:

            event_descr = 'Reset "%s" pivot' % sel[0].get_name()

        objs = set(sel)
        objs.update(members)

        for obj in sel:
            objs.update(obj.get_children())

        for obj in objs:
            data = obj.get_data_to_store("prop_change", "transform")
            obj_data[obj.get_id()] = data

        for obj in sel:
            data = obj_data[obj.get_id()]
            data.update(obj.get_data_to_store("prop_change", "origin_transform"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(HierarchyManager)
