from ..base import *


class DummyEdge:

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_axis"] = state.pop("axis")
        state["_picking_col_id"] = state.pop("picking_color_id")

        return state

    def __setstate__(self, state):

        state["axis"] = state.pop("_axis")
        state["picking_color_id"] = state.pop("_picking_col_id")
        self.__dict__ = state

    def __init__(self, dummy, axis, corner_index, picking_col_id):

        self._dummy = dummy
        self.axis = axis
        self._corner_index = corner_index
        self.picking_color_id = picking_col_id

    def __del__(self):

        Notifiers.obj.debug('DummyEdge garbage-collected.')

    def get_toplevel_object(self, get_group=False):

        return self._dummy.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        origin = self._dummy.origin
        corner_pos = self._dummy.get_corner_pos(self._corner_index)
        vec_coords = [0., 0., 0.]
        vec_coords["xyz".index(self.axis)] = 1.
        edge_vec = V3D(GD.world.get_relative_vector(origin, Vec3(*vec_coords)))
        cam_vec = V3D(GD.world.get_relative_vector(cam, Vec3.forward()))
        cross_vec = edge_vec ** cam_vec

        if not cross_vec.normalize():
            return corner_pos

        point1 = corner_pos
        point2 = point1 + edge_vec
        point3 = point1 + cross_vec
        plane = Plane(point1, point2, point3)

        near_point = Point3()
        far_point = Point3()
        GD.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: GD.world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point


class TemporaryDummy:

    _original_geom = None

    @classmethod
    def __create_original_geom(cls):

        minmax = (-.5, .5)
        corners = [(x, y, z) for x in minmax for y in minmax for z in minmax]

        x1, y1, z1 = corners.pop()

        for corner in corners[:]:

            x, y, z = corner

            if (x == x1 and y != y1 and z != z1) \
                    or (y == y1 and x != x1 and z != z1) \
                    or (z == z1 and x != x1 and y != y1):

                corners.remove(corner)

                if len(corners) == 4:
                    break

        tmp_geom = NodePath("tmp_dummy_geom")
        tmp_geom.set_light_off()
        tmp_geom.set_color_off()
        cls._original_geom = tmp_geom

        # Create box.

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("dummy_helper_box_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        lines = GeomLines(Geom.UH_static)
        vert_index = 0

        for corner in corners:

            for coord, axis in zip(corner, "xyz"):

                pos_writer.add_data3(corner)
                sign = 1. if coord < 0. else -1.
                index = "xyz".index(axis)
                col_writer.add_data4(0., .15, .15, 1.)

                vert_index += 1

                coord2 = coord + .5 * sign
                pos = Point3(*corner)
                pos[index] = coord2
                pos_writer.add_data3(pos)
                # create a gray center vertex
                col_writer.add_data4(.5, .5, .5, 1.)
                lines.add_vertices(vert_index - 1, vert_index)

                vert_index += 1

                coord2 = coord + sign
                pos = Point3(*corner)
                pos[index] = coord2
                pos_writer.add_data3(pos)
                col_writer.add_data4(0., .15, .15, 1.)
                lines.add_vertices(vert_index - 1, vert_index)

                vert_index += 1

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("box_geom")
        node.add_geom(geom)
        np = tmp_geom.attach_new_node(node)
        np.hide(Mgr.get("picking_mask"))
        np.hide()

        # Create cross.

        vertex_data = GeomVertexData("dummy_helper_cross_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        lines = GeomLines(Geom.UH_static)
        vert_index = 0

        for axis in "xyz":

            pos = Point3()
            index = "xyz".index(axis)
            pos[index] = -.5
            pos_writer.add_data3(pos)
            col_writer.add_data4(.5, .5, .5, 1.)

            vert_index += 1

            pos_writer.add_data3(0., 0., 0.)
            col_writer.add_data4(0., .15, .15, 1.)
            lines.add_vertices(vert_index - 1, vert_index)

            vert_index += 1

            pos = Point3()
            pos[index] = .5
            pos_writer.add_data3(pos)
            col_writer.add_data4(.5, .5, .5, 1.)
            lines.add_vertices(vert_index - 1, vert_index)

            vert_index += 1

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("cross_geom")
        node.add_geom(geom)
        np = tmp_geom.attach_new_node(node)
        np.hide(Mgr.get("picking_mask"))
        np.hide()

    def __init__(self, pos, viz, cross_size, is_const_size, const_size, on_top):

        self._size = 0.
        self._is_const_size = is_const_size
        self._drawn_on_top = on_top
        object_root = Mgr.get("object_root")
        self.geom = geom = self.original_geom.copy_to(object_root)

        grid = Mgr.get("grid")
        active_grid_plane = grid.plane_id
        grid_origin = grid.origin

        if active_grid_plane == "xz":
            geom.set_pos_hpr(grid_origin, pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            geom.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 90.))
        else:
            geom.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 0.))

        geoms = {"box": geom.find("**/box_geom"), "cross": geom.find("**/cross_geom")}

        for geom_type in viz:
            geoms[geom_type].show()

        if "cross" in viz:
            geoms["cross"].set_scale(cross_size * .01)

        if is_const_size:

            root = GD.cam().attach_new_node("dummy_helper_root")
            root.set_bin("fixed", 50)
            root.set_depth_test(False)
            root.set_depth_write(False)
            root.node().set_bounds(OmniBoundingVolume())
            root.node().final = True
            root.hide(Mgr.get("picking_mask"))
            self._root = root
            origin = NodePath("dummy_origin")
            geom.children.reparent_to(origin)
            w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
            scale = 800. / max(w, h)
            origin.set_scale(const_size * scale)

            if GD.cam.lens_type == "persp":
                dummy_base = root.attach_new_node("dummy_base")
                dummy_base.set_billboard_point_world(geom, 2000.)
                pivot = dummy_base.attach_new_node("dummy_pivot")
                pivot.set_scale(100.)
                origin.reparent_to(pivot)
                origin.set_compass(geom)
            else:
                root.set_scale(20.)
                origin.reparent_to(root)
                compass_props = CompassEffect.P_pos | CompassEffect.P_rot
                compass_effect = CompassEffect.make(geom, compass_props)
                origin.set_effect(compass_effect)

        if on_top:
            geom.set_bin("fixed", 50)
            geom.set_depth_test(False)
            geom.set_depth_write(False)

    def __del__(self):

        Notifiers.obj.debug('TemporaryDummy garbage-collected.')

    def destroy(self):

        self.geom.remove_node()
        self.geom = None

        if self._is_const_size:
            self._root.remove_node()
            self._root = None

    @property
    def original_geom(self):

        if not self._original_geom:
            TemporaryDummy.__create_original_geom()

        return self._original_geom

    def set_size(self, size):

        s = max(size, .001)

        if self._size == s:
            return

        self._size = s
        self.geom.set_scale(s)

    def is_valid(self):

        return self._size > .001

    def finalize(self):

        pos = self.geom.get_pos(Mgr.get("grid").origin)

        for step in Mgr.do("create_dummy", pos, self._size):
            pass

        self.destroy()


class Dummy(TopLevelObject):

    _corners = []
    _original = None

    @classmethod
    def __define_corners(cls):

        minmax = (-.5, .5)
        corners = [(x, y, z) for x in minmax for y in minmax for z in minmax]

        x1, y1, z1 = corners.pop()

        for corner in corners[:]:

            x, y, z = corner

            if (x == x1 and y != y1 and z != z1) \
                    or (y == y1 and x != x1 and z != z1) \
                    or (z == z1 and x != x1 and y != y1):

                corners.remove(corner)

                if len(corners) == 4:
                    break

        cls._corners = corners

    @classmethod
    def __create_original(cls):

        if not cls._corners:
            cls.__define_corners()

        dummy = NodePath("dummy")
        dummy.set_light_off()
        dummy.set_color_off()
        dummy.set_bin("fixed", 50)
        dummy.set_depth_test(False)
        dummy.set_depth_write(False)

        cls._original = dummy

        root = dummy.attach_new_node("box_root")
        cls.__create_box_geom(root, "unselected")
        cls.__create_box_geom(root, "selected")
        cls.__create_box_geom(root, "pickable")

        root = dummy.attach_new_node("cross_root")
        cls.__create_cross_geom(root, "unselected")
        cls.__create_cross_geom(root, "selected")
        cls.__create_cross_geom(root, "pickable")

    @classmethod
    def __create_box_geom(cls, parent, state):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("dummy_helper_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        if state != "pickable":
            col_writer = GeomVertexWriter(vertex_data, "color")

        lines = GeomLines(Geom.UH_static)
        vert_index = 0

        for corner in cls._corners:

            for coord, axis in zip(corner, "xyz"):

                pos_writer.add_data3(corner)
                sign = 1. if coord < 0. else -1.
                index = "xyz".index(axis)

                if state == "unselected":
                    col_writer.add_data4(0., .15, .15, 1.)
                elif state == "selected":
                    col_writer.add_data4(.2, 1., 1., 1.)

                vert_index += 1

                if state != "pickable":

                    coord2 = coord + .5 * sign
                    pos = Point3(*corner)
                    pos[index] = coord2
                    pos_writer.add_data3(pos)

                    # create a gray center vertex
                    if state == "unselected":
                        col_writer.add_data4(.5, .5, .5, 1.)
                    elif state == "selected":
                        col_writer.add_data4(.2, .2, .2, 1.)

                    lines.add_vertices(vert_index - 1, vert_index)
                    vert_index += 1

                coord2 = coord + sign
                pos = Point3(*corner)
                pos[index] = coord2
                pos_writer.add_data3(pos)

                if state == "unselected":
                    col_writer.add_data4(0., .15, .15, 1.)
                elif state == "selected":
                    col_writer.add_data4(.2, 1., 1., 1.)

                lines.add_vertices(vert_index - 1, vert_index)
                vert_index += 1

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode(f"box_geom_{state}")
        node.add_geom(geom)
        np = parent.attach_new_node(node)
        np.hide(Mgr.get(f'{"render" if state == "pickable" else "picking"}_mask'))
        np.hide() if state == "selected" else np.show()

    @classmethod
    def __create_cross_geom(cls, parent, state):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("dummy_helper_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        if state != "pickable":
            col_writer = GeomVertexWriter(vertex_data, "color")

        lines = GeomLines(Geom.UH_static)
        vert_index = 0

        for axis in "xyz":

            pos = Point3()
            index = "xyz".index(axis)
            pos[index] = -.5
            pos_writer.add_data3(pos)

            if state == "unselected":
                col_writer.add_data4(.5, .5, .5, 1.)
            elif state == "selected":
                col_writer.add_data4(.2, .2, .2, 1.)

            vert_index += 1

            if state != "pickable":

                pos_writer.add_data3(0., 0., 0.)

                if state == "unselected":
                    col_writer.add_data4(0., .15, .15, 1.)
                elif state == "selected":
                    col_writer.add_data4(.2, 1., 1., 1.)

                lines.add_vertices(vert_index - 1, vert_index)
                vert_index += 1

            pos = Point3()
            pos[index] = .5
            pos_writer.add_data3(pos)

            if state == "unselected":
                col_writer.add_data4(.5, .5, .5, 1.)
            elif state == "selected":
                col_writer.add_data4(.2, .2, .2, 1.)

            lines.add_vertices(vert_index - 1, vert_index)
            vert_index += 1

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode(f"cross_geom_{state}")
        node.add_geom(geom)
        np = parent.attach_new_node(node)
        np.hide(Mgr.get(f'{"render" if state == "pickable" else "picking"}_mask'))
        np.hide() if state == "selected" else np.show()

    def __getstate__(self):

        state = TopLevelObject.__getstate__(self)

        del state["_geom_roots"]
        del state["_geoms"]

        if self._is_const_size:
            Mgr.do("make_dummy_const_size", self, False)
            root = self._root.copy_to(Mgr.get("object_root"))
            root.detach_node()
            state["_root"] = root
            Mgr.do("make_dummy_const_size", self)

        return state

    def __setstate__(self, state):

        TopLevelObject.__setstate__(self, state)

        root = self._root
        root.reparent_to(self.origin)
        self._geom_roots = {}
        self._geoms = {"box": {}, "cross": {}}
        self._pickable_geoms = pickable_geoms = {}

        for geom_type, geoms in self._geoms.items():
            self._geom_roots[geom_type] = root.find(f"**/{geom_type}_root")
            geoms["unselected"] = root.find(f"**/{geom_type}_geom_unselected")
            geoms["selected"] = root.find(f"**/{geom_type}_geom_selected")

        pickable_type_id = PickableTypes.get_id("dummy_edge")

        for geom_type in ("box", "cross"):

            pickable_geom = root.find(f"**/{geom_type}_geom_pickable")
            pickable_geoms[geom_type] = pickable_geom
            vertex_data = pickable_geom.node().modify_geom(0).modify_vertex_data()
            col_rewriter = GeomVertexRewriter(vertex_data, "color")
            col_rewriter.set_row(0)
            r, g, b, a = col_rewriter.get_data4()

            if int(round(a * 255.)) != pickable_type_id:
                a = pickable_type_id / 255.
                col_rewriter.set_data4(r, g, b, a)
                while not col_rewriter.is_at_end():
                    r, g, b, _ = col_rewriter.get_data4()
                    col_rewriter.set_data4(r, g, b, a)

    def __init__(self, dummy_id, name, origin_pos):

        TopLevelObject.__init__(self, "dummy", dummy_id, name, origin_pos)

        self._type_prop_ids = ["viz", "size", "cross_size", "const_size_state",
                               "const_size", "on_top"]
        self._viz = set(["box", "cross"])
        self._size = 0.
        self._cross_size = 100.  # percentage of main (box) size
        self._is_const_size = False
        self._const_size = 0.
        self._drawn_on_top = True

        origin = self.origin
        self._root = root = self.original.copy_to(origin)
        self._geom_roots = {}
        self._geoms = {"box": {}, "cross": {}}
        self._geoms_ortho = {}
        self._pickable_geoms = pickable_geoms = {}

        for geom_type, geoms in self._geoms.items():
            self._geom_roots[geom_type] = root.find(f"**/{geom_type}_root")
            geoms["unselected"] = root.find(f"**/{geom_type}_geom_unselected")
            geoms["selected"] = root.find(f"**/{geom_type}_geom_selected")

        self._edges = {}
        pickable_type_id = PickableTypes.get_id("dummy_edge")

        pickable_geom = root.find("**/box_geom_pickable")
        pickable_geoms["box"] = pickable_geom
        vertex_data = pickable_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)

        for i, corner in enumerate(self._corners):
            for axis in "xyz":
                edge = Mgr.do("create_dummy_edge", self, axis, i)
                color_id = edge.picking_color_id
                picking_color = get_color_vec(color_id, pickable_type_id)
                col_writer.set_data4(picking_color)
                col_writer.set_data4(picking_color)
                self._edges[color_id] = edge

        pickable_geom = root.find("**/cross_geom_pickable")
        pickable_geoms["cross"] = pickable_geom
        vertex_data = pickable_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)

        for axis in "xyz":
            edge = Mgr.do("create_dummy_edge", self, axis, 4)
            color_id = edge.picking_color_id
            picking_color = get_color_vec(color_id, pickable_type_id)
            col_writer.set_data4(picking_color)
            col_writer.set_data4(picking_color)
            self._edges[color_id] = edge

    def __del__(self):

        Notifiers.obj.info('Dummy garbage-collected.')

    def destroy(self, unregister=True, add_to_hist=True):

        if self._is_const_size:
            Mgr.do("make_dummy_const_size", self, False)

        if not TopLevelObject.destroy(self, unregister, add_to_hist):
            return

        if unregister:
            self.unregister()

        self._edges = {}
        self._root.remove_node()
        self._root = None

    def register(self, restore=True):

        TopLevelObject.register(self)

        obj_type = "dummy_edge"
        Mgr.do(f"register_{obj_type}_objs", iter(self._edges.values()), restore)

        if restore:
            Mgr.notify("pickable_geom_altered", self)

    def unregister(self):

        obj_type = "dummy_edge"
        Mgr.do(f"unregister_{obj_type}_objs", iter(self._edges.values()))

    @property
    def corners(self):

        if not self._corners:
            Dummy.__define_corners()

        return self._corners + [(0., 0., 0.)]

    @property
    def original(self):

        if not self._original:
            Dummy.__create_original()

        return self._original

    def set_geoms_for_ortho_lens(self, root=None):
        """
        Set the un/selected geometry to be rendered by the orthographic lens
        when set up to have a constant screen size.

        """

        if root is None:
            self._geoms_ortho = {}
            return

        self._geoms_ortho = {"box": {}, "cross": {}}

        for geom_type, geoms in self._geoms_ortho.items():
            geoms["unselected"] = root.find(f"**/{geom_type}_geom_unselected")
            geoms["selected"] = root.find(f"**/{geom_type}_geom_selected")

    def get_geom_root(self):

        return self._root

    def get_corner_pos(self, corner_index):

        corner_pos = Point3(self.corners[corner_index])

        return GD.world.get_relative_point(self._root, corner_pos)

    def get_center_pos(self, ref_node):

        return self.origin.get_pos(ref_node)

    def set_viz(self, viz):

        if self._viz == viz:
            return False

        for geom_type in self._viz - viz:
            self._geom_roots[geom_type].hide()

        for geom_type in viz - self._viz:
            self._geom_roots[geom_type].show()

        group = self.group

        if group:

            sizes = {"box": self._size, "cross": self._size * self._cross_size * .01}
            viz_size_old = max(sizes[geom_type] for geom_type in self._viz)
            viz_size_new = max(sizes[geom_type] for geom_type in viz)

            if viz_size_new != viz_size_old:
                Mgr.do("update_group_bboxes", [group.id])

        self._viz = viz

        return True

    def get_viz(self):

        return self._viz

    def set_size(self, size):

        if self._size == size:
            return False

        self._size = size
        self._root.set_scale(size)

        self.update_group_bbox()

        return True

    def get_size(self):

        return self._size

    def set_cross_size(self, size):

        if self._cross_size == size:
            return False

        if "cross" in self._viz:

            group = self.group

            if group:

                sizes = {"box": self._size, "cross": self._size * self._cross_size * .01}
                viz = [sizes[geom_type] for geom_type in self._viz]
                viz_size_old = max(sizes[geom_type] for geom_type in self._viz)
                sizes["cross"] = self._size * size * .01
                viz_size_new = max(sizes[geom_type] for geom_type in self._viz)

                if viz_size_new != viz_size_old:
                    Mgr.do("update_group_bboxes", [group.id])

        self._cross_size = size
        self._geom_roots["cross"].set_scale(size * .01)

        return True

    def get_cross_size(self):

        return self._cross_size

    def make_const_size(self, is_const_size=True, restore=False):

        if not restore and self._is_const_size == is_const_size:
            return False

        self._is_const_size = is_const_size
        Mgr.do("make_dummy_const_size", self, is_const_size)
        Mgr.notify("pickable_geom_altered", self)

        return True

    def set_const_size(self, const_size):

        if self._const_size == const_size:
            return False

        self._const_size = const_size
        Mgr.do("set_dummy_const_size", self, const_size)

        return True

    def get_const_size(self):

        return self._const_size

    def draw_on_top(self, on_top=True):

        if self._drawn_on_top == on_top:
            return False

        self._drawn_on_top = on_top
        root = self._root

        if on_top:
            root.set_bin("fixed", 50)
            root.set_depth_test(False)
            root.set_depth_write(False)
        else:
            root.clear_bin()
            root.clear_depth_test()
            root.clear_depth_write()

        return True

    def is_drawn_on_top(self):

        return self._drawn_on_top

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "dummy", prop_id,
                                self.get_property(prop_id, True))

        if prop_id == "viz":
            if self.set_viz(value):
                update_app()
                return True
        elif prop_id == "size":
            if self.set_size(value):
                update_app()
                return True
        elif prop_id == "cross_size":
            if self.set_cross_size(value):
                update_app()
                return True
        elif prop_id == "const_size_state":
            if self.make_const_size(value, restore):
                update_app()
                return True
        elif prop_id == "const_size":
            if self.set_const_size(value):
                update_app()
                return True
        elif prop_id == "on_top":
            if self.draw_on_top(value):
                update_app()
                return True
        else:
            return TopLevelObject.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "viz":
            return self._viz
        elif prop_id == "size":
            return self._size
        elif prop_id == "cross_size":
            return self._cross_size
        elif prop_id == "const_size_state":
            return self._is_const_size
        elif prop_id == "const_size":
            return self._const_size
        elif prop_id == "on_top":
            return self._drawn_on_top

        return TopLevelObject.get_property(self, prop_id, for_remote_update)

    def get_property_ids(self):

        return TopLevelObject.get_property_ids(self) + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids

    def update_selection_state(self, is_selected=True):

        TopLevelObject.update_selection_state(self, is_selected)

        geoms = self._geoms

        for geom_type in ("box", "cross"):
            geoms[geom_type]["unselected" if is_selected else "selected"].hide()
            geoms[geom_type]["selected" if is_selected else "unselected"].show()

        geoms = self._geoms_ortho

        if geoms:
            for geom_type in ("box", "cross"):
                geoms[geom_type]["unselected" if is_selected else "selected"].hide()
                geoms[geom_type]["selected" if is_selected else "unselected"].show()

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this dummy helper.

        """

        is_selected = self.is_selected()
        data = {"flash_count": 0, "state": ["selected", "unselected"]}

        def do_flash(task):

            state = data["state"][0 if is_selected else 1]
            self.update_selection_state(False if state == "selected" else True)
            data["state"].reverse()
            data["flash_count"] += 1

            return task.again if data["flash_count"] < 4 else None

        Mgr.add_task(.2, do_flash, "do_flash")

    def make_pickable(self, mask_index=0, pickable=True, show_through=True):

        if self._is_const_size:
            Mgr.do("show_pickable_dummy_geoms", self, mask_index, pickable, show_through)
            return

        picking_mask = Mgr.get("picking_mask", mask_index)
        pickable_geoms = self._pickable_geoms

        if pickable:
            if show_through:
                for geom_type in ("box", "cross"):
                    pickable_geoms[geom_type].show_through(picking_mask)
            else:
                for geom_type in ("box", "cross"):
                    pickable_geoms[geom_type].show(picking_mask)
        else:
            for geom_type in ("box", "cross"):
                pickable_geoms[geom_type].hide(picking_mask)


class DummyEdgeManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "dummy_edge", self.__create_dummy_edge,
                               "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("dummy_edge")

    def __create_dummy_edge(self, dummy, axis, corner_index):

        picking_col_id = self.get_next_picking_color_id()
        dummy_edge = DummyEdge(dummy, axis, corner_index, picking_col_id)

        return dummy_edge


class DummyManager(ObjectManager, CreationPhaseManager, ObjPropDefaultsManager):

    def __init__(self):

        ObjectManager.__init__(self, "dummy", self.__create_dummy)
        CreationPhaseManager.__init__(self, "dummy")
        ObjPropDefaultsManager.__init__(self, "dummy")

        self.set_property_default("viz", set(["box", "cross"]))
        self.set_property_default("size", 1.)
        self.set_property_default("cross_size", 100.)
        self.set_property_default("const_size_state", False)
        self.set_property_default("const_size", 1.)
        self.set_property_default("on_top", True)

        self._draw_plane = None

        self._const_sizes = {}
        self._dummy_roots = {}
        self._dummy_bases = {}
        self._dummy_origins = {"persp": {}, "ortho": {}}
        self._compass_props = CompassEffect.P_pos | CompassEffect.P_rot

        Mgr.accept("show_pickable_dummy_geoms", self.__show_pickable_dummy_geoms)
        Mgr.accept("make_dummy_const_size", self.__make_dummy_const_size)
        Mgr.accept("set_dummy_const_size", self.__set_dummy_const_size)
        Mgr.accept("create_custom_dummy", self.__create_custom_dummy)
        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)
        Mgr.add_app_updater("region_picking", self.__make_region_pickable)
        Mgr.add_app_updater("lens_type", self.__show_root)

    def setup(self):

        self._dummy_root = dummy_root = GD.cam().attach_new_node("dummy_helper_root")
        dummy_root.set_light_off()
        dummy_root.set_shader_off()
        dummy_root.set_bin("fixed", 50)
        dummy_root.set_depth_test(False)
        dummy_root.set_depth_write(False)
        dummy_root.node().set_bounds(OmniBoundingVolume())
        dummy_root.node().final = True
        root_persp = dummy_root.attach_new_node("dummy_helper_root_persp")
        root_ortho = dummy_root.attach_new_node("dummy_helper_root_ortho")
        root_ortho.set_scale(20.)
        self._dummy_roots["persp"] = root_persp
        self._dummy_roots["ortho"] = root_ortho

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "dummy helper"
        status_text["phase1"] = "draw out the dummy"

        CreationPhaseManager.setup(self, creation_phases, status_text)

        return True

    def __handle_viewport_resize(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        scale = 800. / max(w, h)
        const_sizes = self._const_sizes
        dummy_origins = self._dummy_origins

        for dummy_id in self._dummy_bases:

            const_size = const_sizes[dummy_id]

            for origins in dummy_origins.values():
                origins[dummy_id].set_scale(const_size * scale)

    def __make_region_pickable(self, pickable):

        if pickable:
            self._dummy_root.wrt_reparent_to(Mgr.get("object_root"))
            dummy_origins = self._dummy_origins
            dummy_origins_persp = dummy_origins["persp"]
            dummy_origins_ortho = dummy_origins["ortho"]
            for dummy_id in self._dummy_bases:
                dummy = Mgr.get("dummy", dummy_id)
                index = int(dummy.pivot.get_shader_input("index").get_vector().x)
                dummy_origins_persp[dummy_id].set_shader_input("index", index)
                dummy_origins_ortho[dummy_id].set_shader_input("index", index)
        else:
            self._dummy_root.reparent_to(GD.cam())
            self._dummy_root.clear_transform()

    def __show_root(self, lens_type):

        masks = Mgr.get("render_mask") | Mgr.get("picking_mask")

        if lens_type == "persp":
            self._dummy_roots["persp"].show(masks)
            self._dummy_roots["ortho"].hide(masks)
        else:
            self._dummy_roots["persp"].hide(masks)
            self._dummy_roots["ortho"].show(masks)

    def __show_pickable_dummy_geoms(self, dummy, mask_index=0, show=True, show_through=False):

        dummy_id = dummy.id
        dummy_origins = self._dummy_origins

        if dummy_id not in dummy_origins["persp"]:
            return

        origin_persp = dummy_origins["persp"][dummy_id]
        origin_ortho = dummy_origins["ortho"][dummy_id]
        geoms_persp = [origin_persp.find("**/box_geom_pickable"),
                       origin_persp.find("**/cross_geom_pickable")]
        geoms_ortho = [origin_ortho.find("**/box_geom_pickable"),
                       origin_ortho.find("**/cross_geom_pickable")]

        mask = Mgr.get("picking_mask", mask_index)

        if show:
            if GD.cam.lens_type == "persp":
                for geom in geoms_persp:
                    geom.show_through(mask) if show_through else geom.show(mask)
                for geom in geoms_ortho:
                    geom.hide(mask)
            else:
                for geom in geoms_persp:
                    geom.hide(mask)
                for geom in geoms_ortho:
                    geom.show_through(mask) if show_through else geom.show(mask)
        else:
            for geom in geoms_persp + geoms_ortho:
                geom.hide(mask)

    def __make_dummy_const_size(self, dummy, const_size_state=True):

        dummy_id = dummy.id
        dummy_bases = self._dummy_bases
        dummy_origins = self._dummy_origins
        const_sizes = self._const_sizes
        change = False

        if const_size_state:
            if dummy_id not in dummy_bases:
                dummy_roots = self._dummy_roots
                dummy_base = dummy_roots["persp"].attach_new_node("dummy_base")
                dummy_base.set_billboard_point_world(dummy.origin, 2000.)
                pivot = dummy_base.attach_new_node("dummy_pivot")
                pivot.set_scale(100.)
                origin_persp = pivot.attach_new_node("dummy_origin_persp")
                dummy_origins["persp"][dummy_id] = origin_persp
                dummy.get_geom_root().children.reparent_to(origin_persp)
                const_size = dummy.get_const_size()
                const_sizes[dummy_id] = const_size
                w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
                scale = 800. / max(w, h)
                origin_persp.set_scale(const_size * scale)
                origin_ortho = origin_persp.copy_to(dummy_roots["ortho"])
                dummy_origins["ortho"][dummy_id] = origin_ortho
                origin_persp.set_compass(dummy.origin)
                dummy_bases[dummy_id] = dummy_base
                compass_effect = CompassEffect.make(dummy.origin, self._compass_props)
                origin_ortho.set_effect(compass_effect)
                dummy.set_geoms_for_ortho_lens(origin_ortho)
                change = True
        else:
            if dummy_id in dummy_bases:
                del const_sizes[dummy_id]
                origin_persp = dummy_origins["persp"][dummy_id]
                origin_persp.children.reparent_to(dummy.get_geom_root())
                origin_persp.remove_node()
                del dummy_origins["persp"][dummy_id]
                origin_ortho = dummy_origins["ortho"][dummy_id]
                origin_ortho.remove_node()
                del dummy_origins["ortho"][dummy_id]
                dummy_base = dummy_bases[dummy_id]
                dummy_base.remove_node()
                del dummy_bases[dummy_id]
                dummy.set_geoms_for_ortho_lens()
                change = True

        if change:
            dummy.update_group_bbox()

    def __set_dummy_const_size(self, dummy, const_size):

        dummy_id = dummy.id

        if dummy_id in self._dummy_bases:

            w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
            scale = 800. / max(w, h)
            self._const_sizes[dummy_id] = const_size

            for origins in self._dummy_origins.values():
                origins[dummy_id].set_scale(const_size * scale)

    def __create_object(self, dummy_id, name, origin_pos):

        prop_defaults = self.get_property_defaults()
        dummy = Dummy(dummy_id, name, origin_pos)
        dummy.set_viz(prop_defaults["viz"])
        dummy.set_cross_size(prop_defaults["cross_size"])
        dummy.make_const_size(prop_defaults["const_size_state"])
        dummy.set_const_size(prop_defaults["const_size"])
        dummy.draw_on_top(prop_defaults["on_top"])
        dummy.register(restore=False)

        return dummy

    def __create_dummy(self, origin_pos, size=None, cross_size=None, const_size=None):

        dummy_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        dummy = self.__create_object(dummy_id, name, origin_pos)
        prop_defaults = self.get_property_defaults()
        dummy.set_viz(prop_defaults["viz"])
        dummy.set_size(prop_defaults["size"] if size is None else size)
        dummy.set_cross_size(prop_defaults["cross_size"] if cross_size is None else cross_size)
        dummy.make_const_size(prop_defaults["const_size_state"])
        dummy.set_const_size(prop_defaults["const_size"] if const_size is None else const_size)
        dummy.draw_on_top(prop_defaults["on_top"])

        if self.get_object():
            dummy.pivot.set_hpr(self.get_object().geom.get_hpr())

        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(dummy)

        yield False

    def __create_custom_dummy(self, name, viz, size, cross_size, is_const_size,
                              const_size, on_top, transform=None):

        dummy_id = self.generate_object_id()
        dummy = self.__create_object(dummy_id, name, Point3())
        dummy.set_viz(viz)
        dummy.set_size(size)
        dummy.set_cross_size(cross_size)
        dummy.make_const_size(is_const_size)
        dummy.set_const_size(const_size)
        dummy.draw_on_top(on_top)

        if transform:
            dummy.pivot.set_transform(transform)

        return dummy

    def __start_creation_phase1(self):
        """ Start drawing out dummy """

        grid_origin = Mgr.get("grid").origin
        pos = grid_origin.get_relative_point(GD.world, self.get_origin_pos())

        if not self.get_object():
            prop_defaults = self.get_property_defaults()
            viz = prop_defaults["viz"]
            cross_size = prop_defaults["cross_size"]
            is_const_size = prop_defaults["const_size_state"]
            const_size = prop_defaults["const_size"]
            on_top = prop_defaults["on_top"]
            tmp_dummy = TemporaryDummy(pos, viz, cross_size, is_const_size, const_size, on_top)
            self.init_object(tmp_dummy)

        # Create the plane parallel to the camera and going through the dummy
        # origin, used to determine the size drawn by the user.

        normal = GD.world.get_relative_vector(GD.cam(), Vec3.forward())
        point = GD.world.get_relative_point(Mgr.get("grid").origin, pos)
        self._draw_plane = Plane(normal, point)

    def __creation_phase1(self):
        """ Draw out dummy """

        end_point = None
        grid_origin = Mgr.get("grid").origin
        snap_settings = GD["snap"]
        snap_on = snap_settings["on"]["creation"] and snap_settings["on"]["creation_phase_1"]
        snap_tgt_type = snap_settings["tgt_type"]["creation_phase_1"]

        if snap_on and snap_tgt_type != "increment":
            end_point = Mgr.get("snap_target_point")

        if end_point is None:

            if not GD.mouse_watcher.has_mouse():
                return

            screen_pos = GD.mouse_watcher.get_mouse()
            cam = GD.cam()
            near_point = Point3()
            far_point = Point3()
            GD.cam.lens.extrude(screen_pos, near_point, far_point)
            rel_pt = lambda point: GD.world.get_relative_point(cam, point)
            near_point = rel_pt(near_point)
            far_point = rel_pt(far_point)
            end_point = Point3()
            self._draw_plane.intersects_line(end_point, near_point, far_point)

        else:

            end_point = GD.world.get_relative_point(grid_origin, end_point)

        size = (end_point - self.get_origin_pos()).length()

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_1"]
            size = round(size / offset_incr) * offset_incr

        self.get_object().set_size(size)


MainObjects.add_class(DummyEdgeManager)
MainObjects.add_class(DummyManager)
