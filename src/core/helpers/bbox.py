from ..base import *


class BBoxEdge:

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_picking_col_id"] = state.pop("picking_color_id")

        return state

    def __setstate__(self, state):

        state["picking_color_id"] = state.pop("_picking_col_id")
        self.__dict__ = state

    def __init__(self, bbox, axis, corner_index, picking_col_id):

        self._bbox = bbox
        self._axis = axis
        self._corner_index = corner_index
        self.picking_color_id = picking_col_id

    def __del__(self):

        Notifiers.obj.debug('BBoxEdge garbage-collected.')

    def get_toplevel_object(self, get_group=False):

        return self._bbox.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        origin = self._bbox.origin
        corner_pos = self._bbox.get_corner_pos(self._corner_index)
        vec_coords = [0., 0., 0.]
        vec_coords["xyz".index(self._axis)] = 1.
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


class BoundingBox:

    _corners = []
    _original = None

    @classmethod
    def __define_corners(cls):

        edge_offset = .52
        minmax = (-edge_offset, edge_offset)
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

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("bbox_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        lines = GeomLines(Geom.UH_static)

        for corner in cls._corners:

            for coord, axis in zip(corner, "xyz"):

                pos_writer.add_data3(corner)
                sign = 1. if coord < 0. else -1.
                index = "xyz".index(axis)
                coord2 = coord + .26 * sign
                pos = Point3(*corner)
                pos[index] = coord2
                pos_writer.add_data3(pos)
                lines.add_next_vertices(2)

                coord2 = coord + .78 * sign
                pos = Point3(*corner)
                pos[index] = coord2
                pos_writer.add_data3(pos)
                coord2 = coord + 1.04 * sign
                pos = Point3(*corner)
                pos[index] = coord2
                pos_writer.add_data3(pos)
                lines.add_next_vertices(2)

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("bounding_box")
        node.add_geom(geom)

        origin = NodePath(node)
        origin.set_light_off()
        origin.set_texture_off()
        origin.set_material_off()
        origin.set_color_scale_off()
        cls._original = origin

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_is_registered"] = False
        state["_origin"] = state.pop("origin")

        return state

    def __setstate__(self, state):

        state["origin"] = state.pop("_origin")
        self.__dict__ = state
        pickable_type_id = PickableTypes.get_id("bbox_edge")
        vertex_data = self.origin.node().modify_geom(0).modify_vertex_data()
        col_rewriter = GeomVertexRewriter(vertex_data, "color")
        col_rewriter.set_row(0)
        r, g, b, a = col_rewriter.get_data4()

        if int(round(a * 255.)) != pickable_type_id:
            a = pickable_type_id / 255.
            col_rewriter.set_data4(r, g, b, a)
            while not col_rewriter.is_at_end():
                r, g, b, _ = col_rewriter.get_data4()
                col_rewriter.set_data4(r, g, b, a)

    def __init__(self, owner, color):

        self._owner = owner
        self.origin = origin = self.original.copy_to(owner.origin)
        origin.set_color(color)
        vertex_data = origin.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)

        self._edges = {}
        pickable_type_id = PickableTypes.get_id("bbox_edge")

        for i, corner in enumerate(self._corners):

            for axis in "xyz":

                edge = Mgr.do("create_bbox_edge", self, axis, i)
                color_id = edge.picking_color_id
                picking_color = get_color_vec(color_id, pickable_type_id)

                for j in range(4):
                    col_writer.set_data4(picking_color)

                self._edges[color_id] = edge

        self._is_registered = False

    def __del__(self):

        Notifiers.obj.info('BoundingBox garbage-collected.')

    def destroy(self, unregister=True):

        if unregister:
            self.unregister()

        self._edges = {}
        self.origin.remove_node()
        self.origin = None

    def register(self, restore=True):

        if not self._is_registered:
            obj_type = "bbox_edge"
            Mgr.do(f"register_{obj_type}_objs", iter(self._edges.values()), restore)
            self._is_registered = True

    def unregister(self):

        if self._is_registered:
            obj_type = "bbox_edge"
            Mgr.do(f"unregister_{obj_type}_objs", iter(self._edges.values()))
            self._is_registered = False

    @property
    def corners(self):

        if not self._corners:
            BoundingBox.__define_corners()

        return self._corners

    @property
    def original(self):

        if not self._original:
            BoundingBox.__create_original()

        return self._original

    @property
    def color(self):

        return self.origin.get_color()

    @color.setter
    def color(self, color):

        self.origin.set_color(color)

    def get_corner_pos(self, corner_index):

        corner_pos = Point3(self.corners[corner_index])

        return GD.world.get_relative_point(self.origin, corner_pos)

    def get_center_pos(self, ref_node):

        return self.origin.get_pos(ref_node)

    def get_toplevel_object(self, get_group=False):

        return self._owner.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def update(self, point_min, point_max):

        vec = point_max - point_min
        scale_factors = [max(.0001, abs(factor)) for factor in vec]
        self.origin.set_scale(*scale_factors)
        self.origin.set_pos(point_min + vec * .5)
        self._owner.update_group_bbox()

    def show(self, *args, **kwargs):

        self.origin.show(*args, **kwargs)

    def hide(self, *args, **kwargs):

        self.origin.hide(*args, **kwargs)

    def flash(self):

        orig = self.origin
        hidden = orig.is_hidden()
        data = {"flash_count": 0, "state": ["shown", "hidden"]}

        def do_flash(task):

            state = data["state"][1 if hidden else 0]
            orig.show() if state == "hidden" else orig.hide()
            data["state"].reverse()
            data["flash_count"] += 1

            return task.again if data["flash_count"] < 4 else None

        Mgr.add_task(.2, do_flash, "do_flash")


class BBoxEdgeManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "bbox_edge", self.__create_bbox_edge, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("bbox_edge")

    def __create_bbox_edge(self, bbox, axis, corner_index):

        picking_col_id = self.get_next_picking_color_id()
        bbox_edge = BBoxEdge(bbox, axis, corner_index, picking_col_id)

        return bbox_edge


Mgr.accept("create_bbox", lambda owner, color: BoundingBox(owner, color))
MainObjects.add_class(BBoxEdgeManager)
