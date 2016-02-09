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

        status_data = Mgr.get_global("status_data")
        mode_text = "Link objects"
        info_text = "LMB-drag over first (child) object and release LMB over" \
                    " second (parent) object; RMB or <Escape> to end"
        status_data["object_linking"] = {"mode": mode_text, "info": info_text}

        Mgr.set_global("object_links_shown", False)
        Mgr.accept("add_obj_link_viz", self.__add_obj_link_viz)
        Mgr.accept("remove_obj_link_viz", self.__remove_obj_link_viz)
        Mgr.accept("update_obj_link_viz", self.__update_obj_link_viz)
        Mgr.add_app_updater("object_link_viz", self.__show_object_links)
        Mgr.add_app_updater("object_unlinking", self.__unlink_objects)

    def setup(self):

        sort = PendingTasks.get_sort("obj_transf_info_reset", "object")

        if sort is None:
            return False

        PendingTasks.add_task_id("obj_link_viz_update", "object", sort)
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
        pos_writer.add_data3f(child.get_pivot().get_pos())
        col_writer.add_data4f(.25, .25, .25, 1.)

        lines = GeomLines(Geom.UH_static)
        lines.add_next_vertices(2)

        lines_geom = Geom(vertex_data)
        lines_geom.add_primitive(lines)
        node = GeomNode("object_link")
        node.add_geom(lines_geom)
        link_geom = parent.get_pivot().attach_new_node(node)
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

    def __update_obj_link_viz(self):

        def update():

            obj_transf_info = Mgr.get("obj_transf_info")

            for child_id, link_viz in self._obj_link_viz.iteritems():
                if child_id in obj_transf_info:
                    child = Mgr.get("object", child_id)
                    parent = child.get_parent()
                    vertex_data = link_viz.node().modify_geom(0).modify_vertex_data()
                    pos_writer = GeomVertexWriter(vertex_data, "vertex")
                    pos_writer.set_row(1)
                    pos_writer.set_data3f(child.get_pivot().get_pos(parent.get_pivot()))

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


MainObjects.add_class(HierarchyManager)
