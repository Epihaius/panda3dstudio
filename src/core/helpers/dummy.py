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

        self.set_property_default("size", 1.)

        self._draw_plane = None

        Mgr.accept("inst_create_dummy", self.__create_dummy_instantly)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "dummy helper"
        status_text["phase1"] = "draw out the dummy"

        CreationPhaseManager.setup(self, creation_phases, status_text)

        return True

    def __create_dummy(self, dummy_id, name, origin_pos):

        prop_defaults = self.get_property_defaults()
        dummy = Dummy(dummy_id, name, origin_pos)

        return dummy, dummy_id

    def __create_dummy_instantly(self, origin_pos):

        dummy_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        dummy = Mgr.do("create_dummy", dummy_id, name, origin_pos)
        prop_defaults = self.get_property_defaults()
        dummy.set_size(prop_defaults["size"])
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(dummy)

    def __start_creation_phase1(self):
        """ Start drawing out dummy """

        dummy_id = self.generate_object_id()
        name = Mgr.get("next_obj_name", self.get_object_type())
        origin_pos = self.get_origin_pos()
        dummy = Mgr.do("create_dummy", dummy_id, name, origin_pos)
        self.init_object(dummy)

        # Create the plane parallel to the camera and going through the dummy
        # origin, used to determine the size drawn by the user.

        normal = self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.))
        grid_origin = Mgr.get(("grid", "origin"))
        pos = self.world.get_relative_point(grid_origin, origin_pos)
        self._draw_plane = Plane(normal, pos)

    def __creation_phase1(self):
        """ Draw out dummy """

        mpos = self.mouse_watcher.get_mouse()
        far_point_local = Point3()
        self.cam_lens.extrude(mpos, Point3(), far_point_local)
        far_point = self.world.get_relative_point(self.cam, far_point_local)
        cam_pos = self.cam.get_pos(self.world)
        intersection_point = Point3()
        self._draw_plane.intersects_line(intersection_point, cam_pos, far_point)
        grid_origin = Mgr.get(("grid", "origin"))
        pos = self.world.get_relative_point(grid_origin, self.get_origin_pos())
        size = max(.001, (intersection_point - pos).length())
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

        origin = self._dummy.get_origin()
        corner_pos = self._dummy.get_corner_pos(self._corner_index)
        vec_coords = [0., 0., 0.]
        vec_coords["xyz".index(self._axis)] = 1.
        edge_vec = V3D(self.world.get_relative_vector(origin, Vec3(*vec_coords)))
        cam_vec = V3D(self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.)))
        cross_vec = edge_vec ** cam_vec

        if not cross_vec.normalize():
            return corner_pos

        point1 = corner_pos
        point2 = point1 + edge_vec
        point3 = point1 + cross_vec

        far_point_local = Point3()
        self.cam_lens.extrude(screen_pos, Point3(), far_point_local)
        far_point = self.world.get_relative_point(self.cam, far_point_local)
        cam_pos = self.cam.get_pos(self.world)

        plane = Plane(point1, point2, point3)
        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, cam_pos, far_point):
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

        root = NodePath("dummy")
        root.set_light_off()
        root.set_color_off()
        root.set_bin("fixed", 50)
        root.set_depth_test(False)
        root.set_depth_write(False)

        cls._original = root
        cls.__create_geom(root, "unselected")
        cls.__create_geom(root, "selected")
        cls.__create_geom(root, "pickable")

    @classmethod
    def __create_geom(cls, parent, state):

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
        node = GeomNode("geom_%s" % state)
        node.add_geom(geom)
        np = parent.attach_new_node(node)
        np.hide(Mgr.get("%s_mask" % ("render" if state == "pickable" else "picking")))
        np.hide() if state == "selected" else np.show()

    def __get_corners(self):

        if not self._corners:
            Dummy.__define_corners()

        return self._corners

    corners = property(__get_corners)

    def __get_original(self):

        if not self._original:
            Dummy.__create_original()

        return self._original

    original = property(__get_original)

    def __getstate__(self):

        d = self.__dict__.copy()
        d["_pivot"] = NodePath(self.get_pivot().get_name())
        d["_origin"] = NodePath(self.get_origin().get_name())
        del d["_geoms"]

        return d

    def __setstate__(self, state):

        self.__dict__ = state

        pivot = self.get_pivot()
        pivot.reparent_to(Mgr.get("object_root"))
        origin = self.get_origin()
        origin.reparent_to(pivot)
        self.get_pivot_gizmo().get_origin().set_compass(pivot)
        root = self._root
        root.reparent_to(origin)
        self._geoms = {}
        self._geoms["unselected"] = root.find("**/geom_unselected")
        self._geoms["selected"] = root.find("**/geom_selected")

    def __init__(self, dummy_id, name, origin_pos):

        TopLevelObject.__init__(self, "dummy", dummy_id, name, origin_pos,
                                has_color=False)

        self._type_prop_ids = ["size", "axis_tripod"]
        self._size = 0.

        origin = self.get_origin()
        self._root = root = self.original.copy_to(origin)
        self._geoms = {}
        self._geoms["unselected"] = root.find("**/geom_unselected")
        self._geoms["selected"] = root.find("**/geom_selected")
        pickable_geom = root.find("**/geom_pickable")
        vertex_data = pickable_geom.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)

        self._edges = {}
        pickable_type_id = PickableTypes.get_id("dummy_edge")

        for i, corner in enumerate(self._corners):
            for axis in "xyz":
                edge = Mgr.do("create_dummy_edge", self, axis, i)
                color_id = edge.get_picking_color_id()
                picking_color = get_color_vec(color_id, pickable_type_id)
                col_writer.set_data4f(picking_color)
                col_writer.set_data4f(picking_color)
                self._edges[color_id] = edge

    def destroy(self, add_to_hist=True):

        TopLevelObject.destroy(self, add_to_hist)

        self.unregister()
        self._edges = {}
        self._root.remove_node()
        self._root = None

    def get_corner_pos(self, corner_index):

        corner_pos = Point3(self.corners[corner_index])

        return self.world.get_relative_point(self._root, corner_pos)

    def set_size(self, size):

        if self._size == size:
            return False

        self._size = size
        self._root.set_scale(size)

        return True

    def get_size(self):

        return self._size

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "dummy", prop_id,
                                self.get_property(prop_id, True))

        if prop_id == "size":
            if self.set_size(value):
                update_app()
                return True
        else:
            return TopLevelObject.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "size":
            return self._size

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

        self._geoms["unselected" if is_selected else "selected"].hide()
        self._geoms["selected" if is_selected else "unselected"].show()

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
