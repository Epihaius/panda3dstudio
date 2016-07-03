from ..base import *


class DummyEdgeManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "dummy_edge", self.__create_dummy_edge,
                               "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("dummy_edge")

    def __create_dummy_edge(self, dummy, axis, corner_index):

        picking_col_id = self.get_next_picking_color_id()
        dummy_edge = DummyEdge(dummy, axis, corner_index, picking_col_id)

        return dummy_edge, picking_col_id


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

        self._dummy_roots = {}
        self._dummy_bases = {}
        self._dummy_origins = {"persp": {}, "ortho": {}}
        self._compass_props = CompassEffect.P_pos | CompassEffect.P_rot

        Mgr.accept("make_dummy_const_size", self.__make_dummy_const_size)
        Mgr.accept("set_dummy_const_size", self.__set_dummy_const_size)
        Mgr.accept("inst_create_dummy", self.__create_dummy_instantly)
        Mgr.accept("create_custom_dummy", self.__create_custom_dummy)

    def setup(self):

        dummy_root = self.cam().attach_new_node("dummy_helper_root")
        dummy_root.set_bin("fixed", 50)
        dummy_root.set_depth_test(False)
        dummy_root.set_depth_write(False)
        dummy_root.node().set_bounds(OmniBoundingVolume())
        dummy_root.node().set_final(True)
        render_masks = Mgr.get("render_masks")
        picking_masks = Mgr.get("picking_masks")
        root_persp = dummy_root.attach_new_node("dummy_helper_root_persp")
        root_persp.hide(render_masks["ortho"] | picking_masks["ortho"])
        root_ortho = dummy_root.attach_new_node("dummy_helper_root_ortho")
        root_ortho.set_scale(20.)
        root_ortho.hide(render_masks["persp"] | picking_masks["persp"])
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

    def __make_dummy_const_size(self, dummy, const_size_state=True):

        dummy_id = dummy.get_id()
        dummy_bases = self._dummy_bases
        dummy_origins = self._dummy_origins

        if const_size_state:
            if dummy_id not in dummy_bases:
                dummy_roots = self._dummy_roots
                dummy_base = dummy_roots["persp"].attach_new_node("dummy_base")
                dummy_base.set_billboard_point_world(dummy.get_origin(), 2000.)
                pivot = dummy_base.attach_new_node("dummy_pivot")
                pivot.set_scale(100.)
                origin_persp = pivot.attach_new_node("dummy_origin_persp")
                dummy_origins["persp"][dummy_id] = origin_persp
                dummy.get_geom_root().get_children().reparent_to(origin_persp)
                origin_persp.set_scale(dummy.get_const_size())
                origin_ortho = origin_persp.copy_to(dummy_roots["ortho"])
                dummy_origins["ortho"][dummy_id] = origin_ortho
                origin_persp.set_compass(dummy.get_origin())
                dummy_bases[dummy_id] = dummy_base
                compass_effect = CompassEffect.make(dummy.get_origin(), self._compass_props)
                origin_ortho.set_effect(compass_effect)
                dummy.set_geoms_for_ortho_lens(origin_ortho)
        else:
            if dummy_id in dummy_bases:
                origin_persp = dummy_origins["persp"][dummy_id]
                origin_persp.get_children().reparent_to(dummy.get_geom_root())
                origin_persp.remove_node()
                del dummy_origins["persp"][dummy_id]
                origin_ortho = dummy_origins["ortho"][dummy_id]
                origin_ortho.remove_node()
                del dummy_origins["ortho"][dummy_id]
                dummy_base = dummy_bases[dummy_id]
                dummy_base.remove_node()
                del dummy_bases[dummy_id]
                dummy.set_geoms_for_ortho_lens()

    def __set_dummy_const_size(self, dummy, const_size):

        dummy_id = dummy.get_id()

        if dummy_id in self._dummy_bases:
            for origins in self._dummy_origins.itervalues():
                origins[dummy_id].set_scale(const_size)

    def __create_dummy(self, dummy_id, name, origin_pos):

        prop_defaults = self.get_property_defaults()
        dummy = Dummy(dummy_id, name, origin_pos)
        dummy.set_viz(prop_defaults["viz"])
        dummy.set_cross_size(prop_defaults["cross_size"])
        dummy.make_const_size(prop_defaults["const_size_state"])
        dummy.set_const_size(prop_defaults["const_size"])
        dummy.draw_on_top(prop_defaults["on_top"])

        return dummy, dummy_id

    def __create_dummy_instantly(self, origin_pos):

        dummy_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        dummy = Mgr.do("create_dummy", dummy_id, name, origin_pos)
        prop_defaults = self.get_property_defaults()
        dummy.set_viz(prop_defaults["viz"])
        dummy.set_size(prop_defaults["size"])
        dummy.set_cross_size(prop_defaults["cross_size"])
        dummy.make_const_size(prop_defaults["const_size_state"])
        dummy.set_const_size(prop_defaults["const_size"])
        dummy.draw_on_top(prop_defaults["on_top"])
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(dummy)

    def __create_custom_dummy(self, name, viz, size, cross_size, is_const_size,
                              const_size, on_top, transform=None):

        dummy_id = self.generate_object_id()
        dummy = Mgr.do("create_dummy", dummy_id, name, Point3())
        dummy.set_viz(viz)
        dummy.set_size(size)
        dummy.set_cross_size(cross_size)
        dummy.make_const_size(is_const_size)
        dummy.set_const_size(const_size)
        dummy.draw_on_top(on_top)

        if transform:
            dummy.get_pivot().set_transform(transform)

        return dummy

    def __start_creation_phase1(self):
        """ Start drawing out dummy """

        dummy_id = self.generate_object_id()
        name = Mgr.get("next_obj_name", self.get_object_type())
        origin_pos = self.get_origin_pos()
        dummy = Mgr.do("create_dummy", dummy_id, name, origin_pos)
        self.init_object(dummy)

        # Create the plane parallel to the camera and going through the dummy
        # origin, used to determine the size drawn by the user.

        normal = self.world.get_relative_vector(self.cam(), Vec3.forward())
        grid_origin = Mgr.get(("grid", "origin"))
        point = self.world.get_relative_point(grid_origin, origin_pos)
        self._draw_plane = Plane(normal, point)

    def __creation_phase1(self):
        """ Draw out dummy """

        screen_pos = self.mouse_watcher.get_mouse()
        cam = self.cam()
        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)
        near_point = rel_pt(near_point)
        far_point = rel_pt(far_point)
        intersection_point = Point3()
        self._draw_plane.intersects_line(intersection_point, near_point, far_point)
        grid_origin = Mgr.get(("grid", "origin"))
        point = self.world.get_relative_point(grid_origin, self.get_origin_pos())
        size = max(.001, (intersection_point - point).length())
        self.get_object().set_size(size)


class DummyEdge(BaseObject):

    def __init__(self, dummy, axis, corner_index, picking_col_id):

        self._dummy = dummy
        self._axis = axis
        self._corner_index = corner_index
        self._picking_col_id = picking_col_id

    def get_toplevel_object(self):

        return self._dummy

    def get_picking_color_id(self):

        return self._picking_col_id

    def get_axis(self):

        return self._axis

    def get_point_at_screen_pos(self, screen_pos):

        cam = self.cam()
        origin = self._dummy.get_origin()
        corner_pos = self._dummy.get_corner_pos(self._corner_index)
        vec_coords = [0., 0., 0.]
        vec_coords["xyz".index(self._axis)] = 1.
        edge_vec = V3D(self.world.get_relative_vector(origin, Vec3(*vec_coords)))
        cam_vec = V3D(self.world.get_relative_vector(cam, Vec3.forward()))
        cross_vec = edge_vec ** cam_vec

        if not cross_vec.normalize():
            return corner_pos

        point1 = corner_pos
        point2 = point1 + edge_vec
        point3 = point1 + cross_vec
        plane = Plane(point1, point2, point3)

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point


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

        vertex_format = GeomVertexFormat.get_v3cp()
        vertex_data = GeomVertexData("dummy_helper_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        if state != "pickable":
            col_writer = GeomVertexWriter(vertex_data, "color")

        lines = GeomLines(Geom.UH_static)
        vert_index = 0

        for corner in cls._corners:

            for coord, axis in zip(corner, "xyz"):

                pos_writer.add_data3f(corner)
                sign = 1. if coord < 0. else -1.
                index = "xyz".index(axis)

                if state == "unselected":
                    col_writer.add_data4f(0., .15, .15, 1.)
                elif state == "selected":
                    col_writer.add_data4f(.2, 1., 1., 1.)

                vert_index += 1

                if state != "pickable":

                    coord2 = coord + .5 * sign
                    pos = Point3(*corner)
                    pos[index] = coord2
                    pos_writer.add_data3f(pos)

                    # create a gray center vertex
                    if state == "unselected":
                        col_writer.add_data4f(.5, .5, .5, 1.)
                    elif state == "selected":
                        col_writer.add_data4f(.2, .2, .2, 1.)

                    lines.add_vertices(vert_index - 1, vert_index)
                    vert_index += 1

                coord2 = coord + 1. * sign
                pos = Point3(*corner)
                pos[index] = coord2
                pos_writer.add_data3f(pos)

                if state == "unselected":
                    col_writer.add_data4f(0., .15, .15, 1.)
                elif state == "selected":
                    col_writer.add_data4f(.2, 1., 1., 1.)

                lines.add_vertices(vert_index - 1, vert_index)
                vert_index += 1

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("box_geom_%s" % state)
        node.add_geom(geom)
        np = parent.attach_new_node(node)
        np.hide(Mgr.get("%s_masks" % ("render" if state == "pickable" else "picking"))["all"])
        np.hide() if state == "selected" else np.show()

    @classmethod
    def __create_cross_geom(cls, parent, state):

        vertex_format = GeomVertexFormat.get_v3cp()
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
            pos_writer.add_data3f(pos)

            if state == "unselected":
                col_writer.add_data4f(.5, .5, .5, 1.)
            elif state == "selected":
                col_writer.add_data4f(.2, .2, .2, 1.)

            vert_index += 1

            if state != "pickable":

                pos_writer.add_data3f(0., 0., 0.)

                if state == "unselected":
                    col_writer.add_data4f(0., .15, .15, 1.)
                elif state == "selected":
                    col_writer.add_data4f(.2, 1., 1., 1.)

                lines.add_vertices(vert_index - 1, vert_index)
                vert_index += 1

            pos = Point3()
            pos[index] = .5
            pos_writer.add_data3f(pos)

            if state == "unselected":
                col_writer.add_data4f(.5, .5, .5, 1.)
            elif state == "selected":
                col_writer.add_data4f(.2, .2, .2, 1.)

            lines.add_vertices(vert_index - 1, vert_index)
            vert_index += 1

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("cross_geom_%s" % state)
        node.add_geom(geom)
        np = parent.attach_new_node(node)
        np.hide(Mgr.get("%s_masks" % ("render" if state == "pickable" else "picking"))["all"])
        np.hide() if state == "selected" else np.show()

    def __get_corners(self):

        if not self._corners:
            Dummy.__define_corners()

        return self._corners + [(0., 0., 0.)]

    corners = property(__get_corners)

    def __get_original(self):

        if not self._original:
            Dummy.__create_original()

        return self._original

    original = property(__get_original)

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
        root.reparent_to(self.get_origin())
        self._geom_roots = {}
        self._geoms = {"box": {}, "cross": {}}

        for geom_type, geoms in self._geoms.iteritems():
            self._geom_roots[geom_type] = root.find("**/%s_root" % geom_type)
            geoms["unselected"] = root.find("**/%s_geom_unselected" % geom_type)
            geoms["selected"] = root.find("**/%s_geom_selected" % geom_type)

    def __init__(self, dummy_id, name, origin_pos):

        TopLevelObject.__init__(self, "dummy", dummy_id, name, origin_pos)

        self._type_prop_ids = ["viz", "size", "cross_size", "const_size_state",
                               "const_size", "on_top"]
        self._viz = set(["box", "cross"])
        self._size = 0.
        self._cross_size = 100. # percentage of main/box size
        self._is_const_size = False
        self._const_size = 0.
        self._drawn_on_top = True

        origin = self.get_origin()
        self._root = root = self.original.copy_to(origin)
        self._geom_roots = {}
        self._geoms = {"box": {}, "cross": {}}
        self._geoms_ortho = {}

        for geom_type, geoms in self._geoms.iteritems():
            self._geom_roots[geom_type] = root.find("**/%s_root" % geom_type)
            geoms["unselected"] = root.find("**/%s_geom_unselected" % geom_type)
            geoms["selected"] = root.find("**/%s_geom_selected" % geom_type)

        self._edges = {}
        pickable_type_id = PickableTypes.get_id("dummy_edge")

        pickable_geom = root.find("**/box_geom_pickable")
        vertex_data = pickable_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)

        for i, corner in enumerate(self._corners):
            for axis in "xyz":
                edge = Mgr.do("create_dummy_edge", self, axis, i)
                color_id = edge.get_picking_color_id()
                picking_color = get_color_vec(color_id, pickable_type_id)
                col_writer.set_data4f(picking_color)
                col_writer.set_data4f(picking_color)
                self._edges[color_id] = edge

        pickable_geom = root.find("**/cross_geom_pickable")
        vertex_data = pickable_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)

        for axis in "xyz":
            edge = Mgr.do("create_dummy_edge", self, axis, 4)
            color_id = edge.get_picking_color_id()
            picking_color = get_color_vec(color_id, pickable_type_id)
            col_writer.set_data4f(picking_color)
            col_writer.set_data4f(picking_color)
            self._edges[color_id] = edge

    def destroy(self, add_to_hist=True):

        if self._is_const_size:
            Mgr.do("make_dummy_const_size", self, False)

        if not TopLevelObject.destroy(self, add_to_hist):
            return

        self.unregister()
        self._edges = {}
        self._root.remove_node()
        self._root = None

    def set_geoms_for_ortho_lens(self, root=None):
        """
        Set the un/selected geometry to be rendered by the orthographic lens
        when set up to have a constant screen size.

        """

        if root is None:
            self._geoms_ortho = {}
            return

        self._geoms_ortho = {"box": {}, "cross": {}}

        for geom_type, geoms in self._geoms_ortho.iteritems():
            geoms["unselected"] = root.find("**/%s_geom_unselected" % geom_type)
            geoms["selected"] = root.find("**/%s_geom_selected" % geom_type)

    def get_geom_root(self):

        return self._root

    def get_corner_pos(self, corner_index):

        corner_pos = Point3(self.corners[corner_index])

        return self.world.get_relative_point(self._root, corner_pos)

    def get_center_pos(self, ref_node):

        return self.get_origin().get_pos(ref_node)

    def set_viz(self, viz):

        if self._viz == viz:
            return False

        for geom_type in self._viz - viz:
            self._geom_roots[geom_type].hide()

        for geom_type in viz - self._viz:
            self._geom_roots[geom_type].show()

        self._viz = viz

        return True

    def get_viz(self):

        return self._viz

    def set_size(self, size):

        if self._size == size:
            return False

        self._size = size
        self._root.set_scale(size)

        return True

    def get_size(self):

        return self._size

    def set_cross_size(self, size):

        if self._cross_size == size:
            return False

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

    def register(self):

        TopLevelObject.register(self)

        obj_type = "dummy_edge"
        Mgr.do("register_%s_objs" % obj_type, self._edges.itervalues())

    def unregister(self):

        obj_type = "dummy_edge"
        Mgr.do("unregister_%s_objs" % obj_type, self._edges.itervalues())

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

    def is_valid(self):

        return self._size > .001

    def finalize(self):

        pass

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


MainObjects.add_class(DummyManager)
MainObjects.add_class(DummyEdgeManager)
