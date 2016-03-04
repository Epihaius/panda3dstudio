from .base import *


class HierarchyManager(BaseObject):

    def __init__(self):

        self._obj_link_viz_nps = NodePathCollection()
        self._obj_link_viz = {}

        self._draw_plane = None
        self._link_start_pos = None
        self._link_geom = None
        self._obj_to_link = None
        self._prev_xform_target_type = "all"

        self._pixel_under_mouse = VBase4()

        status_data = Mgr.get_global("status_data")
        mode_text = "Link objects"
        info_text = "LMB-drag over first (child) object and release LMB over" \
                    " second (parent) object; RMB or <Escape> to end"
        status_data["object_linking"] = {"mode": mode_text, "info": info_text}

        Mgr.set_global("object_links_shown", False)
        Mgr.set_global("transform_target_type", "all")
        Mgr.accept("add_obj_link_viz", self.__add_obj_link_viz)
        Mgr.accept("remove_obj_link_viz", self.__remove_obj_link_viz)
        Mgr.accept("update_obj_link_viz", self.__update_obj_link_viz)
        Mgr.add_app_updater("object_link_viz", self.__show_object_links)
        Mgr.add_app_updater("object_unlinking", self.__unlink_objects)
        Mgr.add_app_updater("transform_target_type", self.__update_xform_target_type)
        Mgr.add_app_updater("geom_reset", self.__reset_geoms)
        Mgr.add_app_updater("pivot_reset", self.__reset_pivots)
        Mgr.add_app_updater("history_change", self.__reset_xform_target_type)

    def setup(self):

        sort = PendingTasks.get_sort("obj_transf_info_reset", "object")

        if sort is None:
            return False

        PendingTasks.add_task_id("obj_link_viz_update", "object", sort)
        sort = PendingTasks.get_sort("pivot_transform", "object")
        PendingTasks.add_task_id("object_linking", "object", sort)

        add_state = Mgr.add_state
        add_state("object_linking_mode", -10, self.__enter_linking_mode,
                  self.__exit_linking_mode)
        add_state("object_link_creation", -11)

        cancel_link_creation = lambda: self.__finalize_object_linking(cancel=True)

        bind = Mgr.bind_state
        bind("object_linking_mode", "link objects -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("object_linking_mode", "link objects -> select", "escape",
             lambda: Mgr.exit_state("object_linking_mode"))
        bind("object_linking_mode", "exit object linking mode", "mouse3-up",
             lambda: Mgr.exit_state("object_linking_mode"))
        bind("object_linking_mode", "initialize link creation", "mouse1",
             self.__init_object_linking)
        bind("object_link_creation", "quit link creation", "escape", cancel_link_creation)
        bind("object_link_creation", "cancel link creation", "mouse3-up", cancel_link_creation)
        bind("object_link_creation", "finalize link creation",
             "mouse1-up", self.__finalize_object_linking)

        return True

    def __enter_linking_mode(self, prev_state_id, is_active):

        if prev_state_id == "object_link_creation":
            return

        Mgr.add_task(self.__update_cursor, "update_linking_cursor")
        self.__reset_xform_target_type()

        if Mgr.get_global("active_transform_type"):
            Mgr.set_global("active_transform_type", "")
            Mgr.update_app("active_transform_type", "")

        if Mgr.get_global("active_obj_level") != "top":
            Mgr.set_global("active_obj_level", "top")
            Mgr.update_app("active_obj_level")

        Mgr.update_app("status", "object_linking")

    def __exit_linking_mode(self, next_state_id, is_active):

        if next_state_id == "object_link_creation":
            return

        self._pixel_under_mouse = VBase4() # force an update of the cursor next
                                           # time self.__update_cursor() is
                                           # called
        Mgr.remove_task("update_linking_cursor")
        Mgr.set_cursor("main")

    def __show_object_links(self, show):

        Mgr.set_global("object_links_shown", show)

        if show:
            self._obj_link_viz_nps.show()
        else:
            self._obj_link_viz_nps.hide()

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:

            self._pixel_under_mouse = pixel_under_mouse
            cursor_name = "main"

            if pixel_under_mouse != VBase4():

                obj_to_link = self._obj_to_link

                if obj_to_link:

                    obj = Mgr.get("object", pixel_color=pixel_under_mouse)

                    if obj and obj is not obj_to_link \
                            and obj is not obj_to_link.get_parent() \
                            and obj not in obj_to_link.get_descendants():
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
        link_geom.hide(Mgr.get("picking_mask"))
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
        link_geom.hide(Mgr.get("picking_mask"))
        self._obj_link_viz[child_id] = link_geom
        self._obj_link_viz_nps.add_path(link_geom)

        if not Mgr.get_global("object_links_shown"):
            link_geom.hide()

    def __remove_obj_link_viz(self, child_id):

        if child_id not in self._obj_link_viz:
            return

        link_geom = self._obj_link_viz[child_id]
        self._obj_link_viz_nps.remove_path(link_geom)
        link_geom.remove_node()
        del self._obj_link_viz[child_id]

    def __update_obj_link_viz(self, obj_ids=None, force_update_children=False):

        def update():

            obj_transf_info = obj_ids if obj_ids else Mgr.get("obj_transf_info")
            obj_link_viz = self._obj_link_viz
            update_children = Mgr.get_global("transform_target_type") in ("pivot",
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

        task = update
        task_id = "obj_link_viz_update"
        PendingTasks.add(task, task_id, "object")

    def __draw_obj_link(self, task):

        screen_pos = self.mouse_watcher.get_mouse()
        far_point_local = Point3()
        self.cam_lens.extrude(screen_pos, Point3(), far_point_local)
        far_point = self.world.get_relative_point(self.cam, far_point_local)
        cam_pos = self.cam.get_pos(self.world)
        point = Point3()
        self._draw_plane.intersects_line(point, cam_pos, far_point)
        length = (point - self._link_start_pos).length()
        vertex_data = self._link_geom.node().modify_geom(0).modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.set_row(1)
        pos_writer.set_data3f(point)
        uv_writer = GeomVertexWriter(vertex_data, "texcoord")
        uv_writer.set_row(1)
        uv_writer.set_data2f(length * 5., 1.)

        return task.cont

    def __init_object_linking(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if not obj:
            return

        self._obj_to_link = obj
        normal = self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.))
        point = self.world.get_relative_point(self.cam, Point3(0., 10., 0.))
        self._draw_plane = Plane(normal, point)
        cam_pos = self.cam.get_pos(self.world)
        pivot_pos = obj.get_pivot().get_pos(self.world)
        start_pos = Point3()
        self._draw_plane.intersects_line(start_pos, cam_pos, pivot_pos)
        self.__create_obj_link_geom(start_pos)

        Mgr.enter_state("object_link_creation")
        Mgr.add_task(self.__draw_obj_link, "draw_link", sort=3)
        Mgr.set_cursor("no_link")

    def __link_objects(self):

        obj_to_link = self._obj_to_link

        if not obj_to_link:
            return

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if obj and obj is not obj_to_link and obj is not obj_to_link.get_parent() \
                and obj not in obj_to_link.get_descendants():
            obj_to_link.set_parent(obj.get_id())
            obj.display_link_effect()

    def __finalize_object_linking(self, cancel=False):

        if not cancel:
            self.__link_objects()

        Mgr.remove_task("draw_link")
        Mgr.enter_state("object_linking_mode")
        Mgr.set_cursor("main" if self._pixel_under_mouse == VBase4() else "select")

        self._draw_plane = None
        self._link_start_pos = None
        self._link_geom.remove_node()
        self._link_geom = None
        self._obj_to_link = None

    def __unlink_objects(self):

        for obj in Mgr.get("selection", "top"):
            obj.set_parent()

    def __detach_objects(self):

        obj_root = Mgr.get("object_root")

        def detach_objs(objs):

            for obj in objs:
                detach_objs(obj.get_children())
                obj.get_origin().wrt_reparent_to(obj_root)
                obj.get_pivot().wrt_reparent_to(obj_root)

        objs = set(obj.get_root() for obj in Mgr.get("objects"))
        detach_objs(objs)

    def __reattach_objects(self):

        def reattach_objs(objs, parent_pivot):

            for obj in objs:
                pivot = obj.get_pivot()
                pivot.wrt_reparent_to(parent_pivot)
                obj.get_origin().wrt_reparent_to(pivot)
                reattach_objs(obj.get_children(), pivot)

        objs = set(obj.get_root() for obj in Mgr.get("objects"))
        reattach_objs(objs, Mgr.get("object_root"))

    def __detach_pivots(self):

        obj_root = Mgr.get("object_root")

        def detach_pivots(objs):

            for obj in objs:
                detach_pivots(obj.get_children())
                obj.get_pivot().wrt_reparent_to(obj_root)

        objs = set(obj.get_root() for obj in Mgr.get("objects"))
        detach_pivots(objs)

    def __reattach_pivots(self):

        def reattach_pivots(objs, parent_pivot):

            for obj in objs:
                pivot = obj.get_pivot()
                pivot.wrt_reparent_to(parent_pivot)
                reattach_pivots(obj.get_children(), pivot)

        objs = set(obj.get_root() for obj in Mgr.get("objects"))
        reattach_pivots(objs, Mgr.get("object_root"))

    def __detach_origins(self):

        obj_root = Mgr.get("object_root")

        def detach_origs(objs):

            for obj in objs:
                detach_origs(obj.get_children())
                obj.get_origin().wrt_reparent_to(obj_root)

        objs = set(obj.get_root() for obj in Mgr.get("objects"))
        detach_origs(objs)

    def __reattach_origins(self):

        def reattach_origs(objs):

            for obj in objs:
                obj.get_origin().wrt_reparent_to(obj.get_pivot())
                reattach_origs(obj.get_children())

        objs = set(obj.get_root() for obj in Mgr.get("objects"))
        reattach_origs(objs)

    def __update_xform_target_type(self):

        target_type = Mgr.get_global("transform_target_type")
        prev_target_type = self._prev_xform_target_type
        self._prev_xform_target_type = target_type

        if prev_target_type == "all":

            Mgr.enter_state("selection_mode")

            if Mgr.get_global("active_obj_level") != "top":
                Mgr.set_global("active_obj_level", "top")
                Mgr.update_app("active_obj_level")

        if target_type == "geom":
            if prev_target_type == "pivot":
                self.__reattach_objects()
            elif prev_target_type == "no_children":
                self.__reattach_pivots()
            Mgr.do("show_pivot_gizmos")
        elif target_type == "pivot":
            if prev_target_type == "no_children":
                self.__detach_origins()
            else:
                self.__detach_objects()
            Mgr.do("show_pivot_gizmos")
        elif target_type == "no_children":
            if prev_target_type == "geom":
                self.__detach_pivots()
                Mgr.do("show_pivot_gizmos", False)
            elif prev_target_type == "pivot":
                self.__reattach_origins()
                Mgr.do("show_pivot_gizmos", False)
            else:
                self.__detach_pivots()
        elif prev_target_type == "geom":
            Mgr.do("show_pivot_gizmos", False)
        elif prev_target_type == "pivot":
            self.__reattach_objects()
            Mgr.do("show_pivot_gizmos", False)
        elif prev_target_type == "no_children":
            self.__reattach_pivots()

    def __reset_xform_target_type(self):

        if Mgr.get_global("transform_target_type") != "all":
            Mgr.set_global("transform_target_type", "all")
            Mgr.update_app("transform_target_type")

    def __reset_geoms(self):

        sel = Mgr.get("selection", "top")

        if not sel:
            return

        for obj in sel:
            pivot = obj.get_pivot()
            origin = obj.get_origin()
            origin.set_mat(pivot, Mat4.ident_mat())

        sel.update()

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

        target_type = Mgr.get_global("transform_target_type")

        for obj in sel:

            if target_type in ("all", "links"):

                obj_root = Mgr.get("object_root")

                for child in obj.get_children():
                    child.get_pivot().wrt_reparent_to(obj_root)

            pivot = obj.get_pivot()
            origin = obj.get_origin()
            pivot.set_mat(origin, Mat4.ident_mat())
            origin.set_mat(pivot, Mat4.ident_mat())

            if target_type in ("all", "links"):
                for child in obj.get_children():
                    child.get_pivot().wrt_reparent_to(pivot)

        cs_type = Mgr.get_global("coord_sys_type")
        cs_obj = Mgr.get("coord_sys_obj")
        tc_type = Mgr.get_global("transf_center_type")
        tc_obj = Mgr.get("transf_center_obj")

        if cs_obj in sel:
            Mgr.do("notify_coord_sys_transformed")
            Mgr.do("update_coord_sys")

        if tc_type == "cs_origin":
            if cs_type == "object" and cs_obj in sel:
                Mgr.do("set_transf_gizmo_pos", cs_obj.get_pivot().get_pos())
        elif tc_type == "object" and tc_obj in sel:
            Mgr.do("set_transf_gizmo_pos", tc_obj.get_pivot().get_pos())

        sel.update()
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

        for obj in sel:
            objs.update(obj.get_children())

        for obj in objs:
            obj_data[obj.get_id()] = data = {}
            data.update(obj.get_data_to_store("prop_change", "transform"))

        for obj in sel:
            data = obj_data[obj.get_id()]
            data.update(obj.get_data_to_store("prop_change", "origin_transform"))

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(HierarchyManager)
