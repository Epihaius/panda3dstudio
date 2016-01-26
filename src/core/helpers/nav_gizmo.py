from ..base import *
from direct.showbase.ShowBase import DirectObject
from direct.interval.IntervalGlobal import LerpQuatInterval, LerpPosQuatInterval


class NavigationGizmo(BaseObject):

    def __init__(self):

        core = Mgr.get("core")
        win = core.win
        win_props = win.get_properties()
        self._size = self._size_min = size = .05
        self._size_max = .2
        self._size_delta = self._size_max - self._size_min
        size_v = size * win_props.get_x_size() / win_props.get_y_size()
        dr = win.make_display_region(1. - size, 1., 1. - size_v, 1.)
        self._display_region = dr
        dr.set_sort(2)
        gizmo_cam_node = Camera("nav_gizmo_cam")
        self._root = NodePath("nav_gizmo_root")
        self._cam_target = cam_target = self._root.attach_new_node("gizmo_cam_target")
        cam_target.set_hpr(-35., -25., 0.)
        self._gizmo_cam = gizmo_cam = cam_target.attach_new_node(gizmo_cam_node)
        gizmo_cam.set_y(-10.)
        dr.set_camera(gizmo_cam)
        dr.set_clear_color(VBase4(1, 0, 0, 1))
        dr.set_clear_color_active(True)
        dr.set_clear_color_active(False)
        dr.set_clear_depth_active(True)
        Mgr.expose("nav_gizmo_cam", lambda: gizmo_cam)

        frame = (1. - 2. * size, 1., 1. - 2. * size_v, 1.)
        region = MouseWatcherRegion("nav_gizmo_region", *frame)
        self._mouse_region = region
        self.mouse_watcher.add_region(region)
        self.mouse_watcher.set_enter_pattern("region_enter")
        self.mouse_watcher.set_leave_pattern("region_leave")

        input_ctrl = NodePath(self.mouse_watcher).get_parent()
        mouse_watcher_node = MouseWatcher()
        mouse_watcher_node.set_display_region(dr)
        input_ctrl.attach_new_node(mouse_watcher_node)
        self._gizmo_mouse_watcher = mouse_watcher_node

        self._clock = ClockObject.get_global_clock()
        self._time = 0.
        self._has_focus = False
        self._reached_full_size = False
        self._pixel_under_mouse = VBase4()
        self._is_clicked = False
        self._is_orbiting = False
        self._orbit_start_pos = Point2()
        self._lerp_interval = None
        self._dest_view = ""
        self._mouse_start_pos = ()
        self._stop_world_axes_update = False

        self._listener = listener = DirectObject.DirectObject()
        listener.accept("region_enter", self.__on_region_enter)
        listener.accept("region_leave", self.__on_region_leave)

        self._handles_main = {}
        self._handles_aux = {}
        self._handle_ids = {}
        self._handle_normals = {}
        self._handle_quats = {}
        self._hilited_handle_id = ""
        self._hilited_handle_color = {"main": VBase4(), "aux": VBase4()}

        self._handle_root_main = self._root.attach_new_node("handle_root_main")
        self._handle_root_aux = self._root.attach_new_node("handle_root_aux")
        self._handle_root_aux.set_two_sided(True)
        self._handle_root_aux.set_transparency(TransparencyAttrib.M_alpha)
        self.__create_geometry()

        d_light = DirectionalLight("nav_gizmo_light")
        light = gizmo_cam.attach_new_node(d_light)
        light.set_hpr(3., 3., 0.)
        self._handle_root_main.set_light(light)
        tex = Mgr.load_tex(GFX_PATH + "nav_gizmo_sides.png")
        self._handle_root_main.set_texture(tex)

        self._picking_cam = PickingCamera(gizmo_cam, mouse_watcher_node)

        Mgr.accept("update_nav_gizmo", self.__update)
        Mgr.accept("start_updating_nav_gizmo", self.__init_update)
        Mgr.accept("stop_updating_nav_gizmo", self.__end_update)
        Mgr.accept("enable_nav_gizmo", self.__enable)

    def setup(self):

        self._picking_cam.setup()
        self.__update()

        return True

    def __create_geometry(self):

        handle_ids = self._handle_ids
        handle_quats = self._handle_quats
        handle_normals = self._handle_normals
        handles_main = self._handles_main

        # create Home icon

        vertex_format = GeomVertexFormat.get_v3cpt2()

        vertex_data = GeomVertexData("nav_gizmo_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")
        uv_writer = GeomVertexWriter(vertex_data, "texcoord")

        picking_col = get_color_vec(1, 1)

        pos_writer.add_data3f(0., 0., 0.)
        col_writer.add_data4f(picking_col)
        uv_writer.add_data2f(0., 1.)
        pos_writer.add_data3f(.4, 0., 0.)
        col_writer.add_data4f(picking_col)
        uv_writer.add_data2f(1., 1.)
        pos_writer.add_data3f(.4, 0., -.4)
        col_writer.add_data4f(picking_col)
        uv_writer.add_data2f(1., 0.)
        pos_writer.add_data3f(0., 0., -.4)
        col_writer.add_data4f(picking_col)
        uv_writer.add_data2f(0., 0.)

        tris = GeomTriangles(Geom.UH_static)
        tris.add_vertices(0, 2, 1)
        tris.add_vertices(0, 3, 2)

        tris_geom = Geom(vertex_data)
        tris_geom.add_primitive(tris)
        icon_node = GeomNode("nav_home_icon")
        icon_node.add_geom(tris_geom)
        icon = self._gizmo_cam.attach_new_node(icon_node)
        handle_id = "home"
        handles_main[handle_id] = icon
        icon.set_pos(-1.3, 5.5, 1.3)
        icon.set_color(.75, .75, .75)
        icon.set_transparency(TransparencyAttrib.M_alpha)
        tex = Mgr.load_tex(GFX_PATH + "home_icon.png")
        icon.set_texture(tex)
        icon.hide()
        handle_ids[1] = handle_id

        quat = Quat()
        quat.set_hpr(VBase3(-45., -45., 0.))
        handle_quats[handle_id] = quat

        # create main handles

        inset = .4
        coords = {"x": 0., "y": 0., "z": 0.}
        picking_colors = {}
        handle_root_main = self._handle_root_main

        # create side handles

        vertex_format = GeomVertexFormat.get_v3n3cpt2()
        color = VBase4(.75, .75, .75, 1.)

        for i in range(3):

            axis1 = "xyz"[i]
            axis2, axis3 = "".join(sorted("xyz"[i - 2] + "xyz"[i - 1]))

            for sign in (-1, 1):

                vertex_data = GeomVertexData("nav_gizmo_data", vertex_format,
                                             Geom.UH_static)
                pos_writer = GeomVertexWriter(vertex_data, "vertex")
                col_writer = GeomVertexWriter(vertex_data, "color")
                normal_writer = GeomVertexWriter(vertex_data, "normal")
                uv_writer = GeomVertexWriter(vertex_data, "texcoord")

                tris = GeomTriangles(Geom.UH_static)

                picking_col_id = len(handle_ids) + 1
                picking_col = get_color_vec(picking_col_id, 1)
                handle_id = "%s%s" % ("-" if sign < 0 else "+", axis1)
                handle_ids[picking_col_id] = handle_id
                picking_colors[handle_id] = picking_col

                normal = V3D(*map(lambda x: sign * 1. if x == i else 0., range(3)))
                handle_normals[handle_id] = normal
                quat = Quat()
                quat.set_hpr(V3D(normal * -1.).get_hpr())
                handle_quats[handle_id] = quat

                coords[axis1] = sign

                for j in (-1, 1):

                    coords[axis3] = j * (1. - inset)

                    for k in (-1, 1):

                        coords[axis2] = k * (1. - inset)
                        pos = tuple(coords[axis] for axis in "xyz")
                        pos_writer.add_data3f(pos)
                        col_writer.add_data4f(picking_col)
                        normal_writer.add_data3f(normal)

                        a = i / 3.
                        b = (i + 1) / 3.
                        u1, u2 = (a, b) if sign < 0 else (b, a)
                        u = u1 if (k < 0 if axis1 == "y" else k > 0) else u2
                        c, d = (0., .5) if sign < 0 else (.5, 1.)
                        v = c if j < 0 else d
                        uv = (u, v)
                        uv_writer.add_data2f(uv)

                tri_indices = (0, 1, 2) if (sign < 0 if axis1 == "y"
                    else sign > 0) else (0, 2, 1)
                tris.add_vertices(*tri_indices)
                tri_indices = (1, 3, 2) if (sign < 0 if axis1 == "y"
                    else sign > 0) else (1, 2, 3)
                tris.add_vertices(*tri_indices)

                tris_geom = Geom(vertex_data)
                tris_geom.add_primitive(tris)
                handle_node = GeomNode("nav_gizmo_handle_main" + handle_id)
                handle_node.add_geom(tris_geom)
                handle = handle_root_main.attach_new_node(handle_node)
                handle.set_color(color)
                handles_main[handle_id] = handle

        quat = Quat()
        quat.set_hpr(VBase3(180., 90., 0.))
        handle_quats["-z"] = quat
        quat = Quat()
        quat.set_hpr(VBase3(0., -90., 0.))
        handle_quats["+z"] = quat

        # create edge handles

        vertex_format = GeomVertexFormat.get_v3n3cp()

        edge_root = handle_root_main.attach_new_node("edge_root")
        edge_root.set_texture_off()
        color = VBase4(.65, .65, .65, 1.)
        edge_root.set_two_sided(True)
        normal_data = {"x":0., "y":0., "z":0.}

        for i in range(3):

            axis1, axis2, axis3 = "xyz"[i], "xyz"[i - 1], "xyz"[i - 2]

            for j in (-1, 1):

                for k in (-1, 1):

                    vertex_data = GeomVertexData("nav_gizmo_data", vertex_format,
                                                 Geom.UH_static)
                    pos_writer = GeomVertexWriter(vertex_data, "vertex")
                    col_writer = GeomVertexWriter(vertex_data, "color")
                    normal_writer = GeomVertexWriter(vertex_data, "normal")

                    tris = GeomTriangles(Geom.UH_static)

                    picking_col_id = len(handle_ids) + 1
                    picking_col = get_color_vec(picking_col_id, 1)
                    handle_id = "%s%s%s%s" % ("-" if j < 0 else "+", axis2,
                                              "-" if k < 0 else "+", axis3)
                    handle_ids[picking_col_id] = handle_id

                    normal_data[axis1] = 0.
                    normal_data[axis2] = -j
                    normal_data[axis3] = -k
                    dir_vec = V3D(*[normal_data[axis] for axis in "xyz"])
                    quat = Quat()
                    quat.set_hpr(dir_vec.get_hpr())
                    handle_quats[handle_id] = quat

                    for a in (axis2, axis3):

                        normal_data[axis1] = 0.
                        normal_data[axis2] = j if a == axis2 else 0.
                        normal_data[axis3] = k if a == axis3 else 0.
                        normal = Vec3(*[normal_data[axis] for axis in "xyz"])

                        for sign in (-1, 1):

                            coords[axis1] = sign * (1. - inset)

                            coords[axis2] = j
                            coords[axis3] = k
                            pos = tuple(coords[axis] for axis in "xyz")
                            pos_writer.add_data3f(pos)
                            col_writer.add_data4f(picking_col)
                            normal_writer.add_data3f(normal)

                            coords[axis2] = j * (1. - (0. if a == axis2 else inset))
                            coords[axis3] = k * (1. - (0. if a == axis3 else inset))
                            pos = tuple(coords[axis] for axis in "xyz")
                            pos_writer.add_data3f(pos)
                            col_writer.add_data4f(picking_col)
                            normal_writer.add_data3f(normal)

                    tris.add_vertices(0, 1, 2)
                    tris.add_vertices(1, 3, 2)
                    tris.add_vertices(4, 5, 6)
                    tris.add_vertices(5, 7, 6)

                    tris_geom = Geom(vertex_data)
                    tris_geom.add_primitive(tris)
                    handle_node = GeomNode("nav_gizmo_handle_main" + handle_id)
                    handle_node.add_geom(tris_geom)
                    handle = edge_root.attach_new_node(handle_node)
                    handle.set_color(color)
                    handles_main[handle_id] = handle

        # create corner handles

        corner_root = handle_root_main.attach_new_node("corner_root")
        corner_root.set_texture_off()
        color = VBase4(.5, .5, .5, 1.)
        corner_root.set_two_sided(True)

        for sign in (-1, 1):

            for j in (-1, 1):

                for k in (-1, 1):

                    vertex_data = GeomVertexData("nav_gizmo_data", vertex_format,
                                                 Geom.UH_static)
                    pos_writer = GeomVertexWriter(vertex_data, "vertex")
                    col_writer = GeomVertexWriter(vertex_data, "color")
                    normal_writer = GeomVertexWriter(vertex_data, "normal")

                    tris = GeomTriangles(Geom.UH_static)

                    picking_col_id = len(handle_ids) + 1
                    picking_col = get_color_vec(picking_col_id, 1)
                    handle_id = "%s%s%s" % ("-x" if j < 0 else "+x",
                                            "-y" if k < 0 else "+y",
                                            "-z" if sign < 0 else "+z")
                    handle_ids[picking_col_id] = handle_id

                    dir_vec = V3D(-j, -k, -sign)
                    quat = Quat()
                    quat.set_hpr(dir_vec.get_hpr())
                    handle_quats[handle_id] = quat

                    corner = Point3(j, k, sign)
                    vecs = {}
                    vecs["x"] = Vec3(-j * inset, 0., 0.)
                    vecs["y"]  = Vec3(0., -k * inset, 0.)
                    vecs["z"]  = Vec3(0., 0., -sign * inset)

                    for a1 in "xyz":

                        normal_data["x"] = j if a1 == "x" else 0.
                        normal_data["y"] = k if a1 == "y" else 0.
                        normal_data["z"] = sign if a1 == "z" else 0.
                        normal = Vec3(*[normal_data[axis] for axis in "xyz"])

                        a2, a3 = "xyz".replace(a1, "")

                        pos_writer.add_data3f(corner)
                        col_writer.add_data4f(picking_col)
                        normal_writer.add_data3f(normal)

                        pos = corner + vecs[a2]
                        pos_writer.add_data3f(pos)
                        col_writer.add_data4f(picking_col)
                        normal_writer.add_data3f(normal)

                        pos += vecs[a3]
                        pos_writer.add_data3f(pos)
                        col_writer.add_data4f(picking_col)
                        normal_writer.add_data3f(normal)

                        pos = corner + vecs[a3]
                        pos_writer.add_data3f(pos)
                        col_writer.add_data4f(picking_col)
                        normal_writer.add_data3f(normal)

                    tris.add_vertices(0, 1, 2)
                    tris.add_vertices(0, 2, 3)
                    tris.add_vertices(4, 5, 6)
                    tris.add_vertices(4, 6, 7)
                    tris.add_vertices(8, 9, 10)
                    tris.add_vertices(8, 10, 11)

                    tris_geom = Geom(vertex_data)
                    tris_geom.add_primitive(tris)
                    handle_node = GeomNode("nav_gizmo_handle_main" + handle_id)
                    handle_node.add_geom(tris_geom)
                    handle = corner_root.attach_new_node(handle_node)
                    handle.set_color(color)
                    handles_main[handle_id] = handle

        # create auxiliary axis-aligned handles

        handles_aux = self._handles_aux
        handle_root_aux = self._handle_root_aux

        vertex_format = GeomVertexFormat.get_v3cp()

        colors = {"x":VBase4(.75, 0., 0., 1.),
                  "y":VBase4(0., .75, 0., 1.),
                  "z":VBase4(0., 0., .75, 1.)}

        for i in range(3):

            axis1, axis2, axis3 = "xyz"[i], "xyz"[i - 1], "xyz"[i - 2]

            for sign in (-1, 1):

                vertex_data = GeomVertexData("nav_gizmo_data", vertex_format,
                                             Geom.UH_static)
                pos_writer = GeomVertexWriter(vertex_data, "vertex")
                col_writer = GeomVertexWriter(vertex_data, "color")

                tris = GeomTriangles(Geom.UH_static)

                handle_id = "%s%s" % ("-" if sign < 0 else "+", axis1)
                picking_col = picking_colors[handle_id]
                coords[axis1] = -.5

                for j in (-1, 1):

                    coords[axis3] = j * .25

                    for k in (-1, 1):
                        coords[axis2] = k * .25
                        pos = tuple(coords[axis] for axis in "xyz")
                        pos_writer.add_data3f(pos)
                        col_writer.add_data4f(picking_col)

                tris.add_vertices(0, 1, 2)
                tris.add_vertices(1, 3, 2)

                coords[axis1] = .5
                coords[axis2] = 0.
                coords[axis3] = 0.
                pos = tuple(coords[axis] for axis in "xyz")
                pos_writer.add_data3f(pos)
                col_writer.add_data4f(picking_col)

                tris.add_vertices(0, 1, 4)
                tris.add_vertices(1, 2, 4)
                tris.add_vertices(2, 3, 4)
                tris.add_vertices(3, 0, 4)

                tris_geom = Geom(vertex_data)
                tris_geom.add_primitive(tris)
                handle_node = GeomNode("nav_gizmo_handle_aux" + handle_id)
                handle_node.add_geom(tris_geom)
                handle = handle_root_aux.attach_new_node(handle_node)
                offset = {"x": 0., "y": 0., "z": 0.}
                offset[axis1] = -1.7 if sign < 0 else 1.7
                pos = tuple(offset[axis] for axis in "xyz")
                handle.set_pos(pos)
                handle.set_color(colors[axis1])
                handles_aux[handle_id] = handle

    def __on_region_enter(self, *args):

        name = args[0].get_name()

        if name == "nav_gizmo_region":

            Mgr.remove_task("resize_nav_gizmo_region")
            Mgr.add_task(self.__expand_region, "resize_nav_gizmo_region")
            Mgr.get("core").suppress_mouse_events()
            Mgr.get("picking_cam").set_active(False)

            if not self._is_orbiting:
                self._picking_cam.set_active()

    def __on_region_leave(self, *args):

        name = args[0].get_name()

        if name == "nav_gizmo_region":

            self._has_focus = False
            Mgr.remove_task("hilite_handle")

            if not self._is_orbiting:
                self._listener.ignore("mouse1")
                self._listener.ignore("mouse1-up")
                self._picking_cam.set_active(False)
                Mgr.do_next_frame(lambda task: self.__hilite_handle(), "remove_hilite")
                Mgr.remove_task("resize_nav_gizmo_region")
                Mgr.add_task(self.__shrink_region, "resize_nav_gizmo_region")
                Mgr.get("core").suppress_mouse_events(False)
                Mgr.get("picking_cam").set_active()

    def __set_region_size(self):

        factor = self._time ** (.2 if self._reached_full_size else 5.)
        self._size = self._size_min + self._size_delta * factor
        win = Mgr.get("core").win
        win_props = win.get_properties()
        size = self._size
        size_v = size * win_props.get_x_size() / win_props.get_y_size()
        self._display_region.set_dimensions(1. - size, 1., 1. - size_v, 1.)
        self._mouse_region.set_frame(1. - 2. * size, 1., 1. - 2. * size_v, 1.)

    def __expand_region(self, task):

        if self._size >= self._size_max:
            self._time = 1.
            self._has_focus = True
            self._reached_full_size = True
            Mgr.add_task(self.__hilite_handle, "hilite_handle")
            self._listener.accept("mouse1", self.__on_left_down)
            self._listener.accept("mouse1-up", self.__on_left_up)
            return

        self._time = min(1., self._time + 2. * self._clock.get_dt())
        alpha = max(0., self._time - .5) * 2.
        icon = self._handles_main["home"]
        icon.set_alpha_scale(alpha)
        icon.show() if alpha else icon.hide()
        self.__set_region_size()

        return task.cont

    def __shrink_region(self, task):

        if self._size <= self._size_min:
            self._time = 0.
            self._reached_full_size = False
            return

        self._time = max(0., self._time - 2. * self._clock.get_dt())
        alpha = max(0., self._time - .5) * 2.
        icon = self._handles_main["home"]
        icon.set_alpha_scale(alpha)
        icon.show() if alpha else icon.hide()
        self.__set_region_size()

        return task.cont

    def __hilite_handle(self, task=None):

        r, g, b, a = [int(round(c * 255.)) for c in self._picking_cam.get_pixel_under_mouse()]
        color_id = r << 16 | g << 8 | b  # credit to coppertop @ panda3d.org
        handle_ids = self._handle_ids
        handle_id = handle_ids[color_id] if color_id in handle_ids else ""

        if self._hilited_handle_id != handle_id:

            if self._hilited_handle_id:

                handle = self._handles_main[self._hilited_handle_id]
                handle.set_color(self._hilited_handle_color["main"])

                if self._hilited_handle_id in self._handles_aux:
                    handle = self._handles_aux[self._hilited_handle_id]
                    handle.set_color(self._hilited_handle_color["aux"])

            if handle_id:

                handle = self._handles_main[handle_id]
                self._hilited_handle_color["main"] = handle.get_color()
                handle.set_color(2., 2., 0.)

                if handle_id in self._handles_aux:
                    handle = self._handles_aux[handle_id]
                    self._hilited_handle_color["aux"] = handle.get_color()
                    handle.set_color(2., 2., 0.)

            self._hilited_handle_id = handle_id

        return task.cont if task else None

    def __transition_view(self, task):

        main_cam_target = Mgr.get( ("cam", "target") )

        if self._lerp_interval.is_stopped():

            quat = main_cam_target.get_quat()
            pos = main_cam_target.get_pos()

            # prevent the bottom view from flipping 180 degrees when orbiting
            # the view later, due to a negative heading
            if self._dest_view == "-z":
                hpr = Vec3(180., 90., 0.)
            else:
                hpr = quat.get_hpr()

            main_cam_target.set_pos_hpr(pos, hpr)
            self._cam_target.set_hpr(hpr)
            self.__update_aux_handles()
            Mgr.do("update_transf_gizmo")
            Mgr.do("update_coord_sys")

            self._lerp_interval = None
            Mgr.get("core").suppress_key_events(False)
            self.__enable()

            if self._stop_world_axes_update:
                Mgr.do("stop_updating_world_axes")

            if self._gizmo_mouse_watcher.has_mouse():
                self._has_focus = True
                self._listener.accept("mouse1", self.__on_left_down)
                self._listener.accept("mouse1-up", self.__on_left_up)
                self._picking_cam.set_active()
            else:
                Mgr.get("core").suppress_mouse_events(False)
                Mgr.get("picking_cam").set_active()

            self._dest_view = ""

            return

        hpr = main_cam_target.get_hpr()
        pos = main_cam_target.get_pos()
        self._cam_target.set_hpr(hpr)
        self.__update_aux_handles()
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

        return task.cont

    def __on_left_down(self):

        if self._is_orbiting:
            return

        self._is_clicked = True
        mouse_pointer = Mgr.get("mouse_pointer", 0)
        self._mouse_start_pos = (mouse_pointer.get_x(), mouse_pointer.get_y())

        Mgr.add_task(self.__check_mouse_offset, "check_mouse_offset")

    def __on_left_up(self):

        if self._is_orbiting:
            self.__end_orbit()
            return

        Mgr.remove_task("check_mouse_offset")

        if not self._is_clicked:
            return

        self._is_clicked = False
        handle_id = self._hilited_handle_id

        if handle_id:
            self.__enable(False)
            self._has_focus = False
            self._listener.ignore("mouse1")
            self._listener.ignore("mouse1-up")
            self._picking_cam.set_active(False)
            Mgr.get("core").suppress_key_events()
            self._dest_view = handle_id
            main_cam_target = Mgr.get( ("cam", "target") )
            lerp_interval = LerpPosQuatInterval(main_cam_target, .5, Point3(),
                                                self._handle_quats[handle_id],
                                                blendType="easeInOut") \
                            if handle_id == "home" else \
                            LerpQuatInterval(main_cam_target, .5,
                                             self._handle_quats[handle_id],
                                             blendType="easeInOut")
            self._lerp_interval = lerp_interval
            lerp_interval.start()
            Mgr.add_task(self.__transition_view, "transition_view", sort=30)
            self._stop_world_axes_update = Mgr.do("start_updating_world_axes", False)

    def __check_mouse_offset(self, task):
        """
        Delay start of orbiting until user has moved mouse at least 3 pixels
        in any direction, to avoid conflicts with specific view selections.

        """

        mouse_pointer = Mgr.get("mouse_pointer", 0)
        mouse_x = mouse_pointer.get_x()
        mouse_y = mouse_pointer.get_y()
        mouse_start_x, mouse_start_y = self._mouse_start_pos

        if max(abs(mouse_x - mouse_start_x), abs(mouse_y - mouse_start_y)) > 3:
            self.__init_orbit()
            return task.done

        return task.cont

    def __init_orbit(self):

        self._is_clicked = False
        Mgr.remove_task("transform_cam")

        if not self.mouse_watcher.has_mouse():
            return

        self._orbit_start_pos = Point2(self.mouse_watcher.get_mouse())
        Mgr.add_task(self.__orbit, "transform_cam", sort=2)
        self._is_orbiting = True
        self._stop_world_axes_update = Mgr.do("start_updating_world_axes", False)
        self._picking_cam.set_active(False)
        Mgr.get("core").suppress_key_events()

    def __orbit(self, task):

        if not self.mouse_watcher.has_mouse():
            return task.cont

        orbit_pos = self.mouse_watcher.get_mouse()
        d_heading, d_pitch = (orbit_pos - self._orbit_start_pos) * 500.
        self._orbit_start_pos = Point2(orbit_pos)
        target = self._cam_target
        hpr = Vec3(target.get_h() - d_heading, target.get_p() + d_pitch, 0.)
        target.set_hpr(hpr)
        self.__update_aux_handles()
        main_cam_target = Mgr.get( ("cam", "target") )
        main_cam_target.set_hpr(hpr)
        Mgr.do("update_transf_gizmo")
        Mgr.do("update_coord_sys")

        return task.cont

    def __end_orbit(self):

        Mgr.remove_task("transform_cam")
        self._is_orbiting = False
        Mgr.get("core").suppress_key_events(False)

        if self._stop_world_axes_update:
            Mgr.do("stop_updating_world_axes")

        if self._has_focus:
            self._picking_cam.set_active()
        else:
            self._listener.ignore("mouse1")
            self._listener.ignore("mouse1-up")
            Mgr.get("core").suppress_mouse_events(False)
            Mgr.get("picking_cam").set_active()

    def __update_aux_handles(self):

        cam_vec = V3D(self._root.get_relative_vector(self._cam_target, Vec3(0., 1., 0.)))
        handles = self._handles_aux

        # make the auxiliary handles more or less transparent, depending on their
        # direction relative to the camera
        for handle_id, normal in self._handle_normals.iteritems():
            dot_prod = cam_vec * normal
            alpha = 1. + min(0., max(-.4, dot_prod)) * 2.5
            handle = handles[handle_id]
            handle.set_alpha_scale(alpha)
            handle.show() if alpha else handle.hide()

    def __update(self, task=None):

        if not self._is_orbiting and not self._lerp_interval:

            main_cam_target = Mgr.get( ("cam", "target") )
            self._cam_target.set_hpr(main_cam_target.get_hpr())
            self.__update_aux_handles()

        return task.cont if task else None

    def __init_update(self):

        Mgr.add_task(self.__update, "update_nav_gizmo")

    def __end_update(self):

        Mgr.remove_task("update_nav_gizmo")

    def __enable(self, enable=True):

        listener = self._listener

        if enable:
            listener.accept("region_enter", self.__on_region_enter)
            listener.accept("region_leave", self.__on_region_leave)
        else:
            listener.ignore("region_enter")
            listener.ignore("region_leave")


class PickingCamera(BaseObject):

    def __init__(self, parent_cam, mouse_watcher):

        BaseObject.__init__(self)

        self._parent_cam = parent_cam
        self._gizmo_mouse_watcher = mouse_watcher
        self._tex = None
        self._img = None
        self._buffer = None
        self._np = None
        self._pixel_color = VBase4()

    def setup(self):

        core = Mgr.get("core")
        self._tex = Texture("picking_texture")
        self._img = PNMImage(1, 1)
        props = FrameBufferProperties()
        props.set_float_color(True)
        props.set_alpha_bits(32)
        props.set_depth_bits(32)
        self._buffer = bfr = core.win.make_texture_buffer("picking_buffer",
                                                          1, 1,
                                                          self._tex,
                                                          to_ram=True,
                                                          fbp=props)

        bfr.set_clear_color(VBase4())
        bfr.set_clear_color_active(True)
        bfr.set_sort(-100)
        self._np = core.make_camera(bfr)
        self._np.reparent_to(self._parent_cam)
        node = self._np.node()
        lens = node.get_lens()
        lens.set_fov(1.)
        cull_bounds = lens.make_bounds()
        lens.set_fov(.1)
        node.set_cull_bounds(cull_bounds)

        state_np = NodePath("flat_color_state")
        state_np.set_texture_off(1)
        state_np.set_material_off(1)
        state_np.set_shader_off(1)
        state_np.set_light_off(1)
        state_np.set_color_off(1)
        state_np.set_color_scale_off(1)
        state_np.set_transparency(TransparencyAttrib.M_none, 1)
        state = state_np.get_state()
        node.set_initial_state(state)
        node.set_active(False)

    def set_active(self, is_active=True):

        if self._np.node().is_active() == is_active:
            return

        self._np.node().set_active(is_active)

        if is_active:
            Mgr.add_task(self.__check_pixel, "get_pixel_under_mouse", sort=0)
        else:
            Mgr.remove_task("get_pixel_under_mouse")
            self._pixel_color = VBase4()

    def __check_pixel(self, task):

        if not self._gizmo_mouse_watcher.has_mouse():
            return task.cont

        screen_pos = self._gizmo_mouse_watcher.get_mouse()
        far_point = Point3()
        self._parent_cam.node().get_lens().extrude(screen_pos, Point3(), far_point)
        self._np.look_at(far_point)
        self._tex.store(self._img)
        self._pixel_color = self._img.get_xel_a(0, 0)

        return task.cont

    def get_pixel_under_mouse(self):

        return self._pixel_color


MainObjects.add_class(NavigationGizmo)
