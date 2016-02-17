from ..base import *


class BBoxEdgeManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "bbox_edge", self.__create_bbox_edge, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("bbox_edge")

    def __create_bbox_edge(self, bbox, axis, corner_index):

        picking_col_id = self.get_next_picking_color_id()
        bbox_edge = BBoxEdge(bbox, axis, corner_index, picking_col_id)

        return bbox_edge, picking_col_id


class BBoxEdge(BaseObject):

    def __init__(self, bbox, axis, corner_index, picking_col_id):

        self._bbox = bbox
        self._axis = axis
        self._corner_index = corner_index
        self._picking_col_id = picking_col_id

    def destroy(self):

        Mgr.do("unregister_bbox_edge", self._id)

    def get_toplevel_object(self):

        return self._bbox.get_toplevel_object()

    def get_picking_color_id(self):

        return self._picking_col_id

    def get_point_at_screen_pos(self, screen_pos):

        origin = self._bbox.get_origin()
        corner_pos = self._bbox.get_corner_pos(self._corner_index)
        vec_coords = [0., 0., 0.]
        vec_coords["XYZ".index(self._axis)] = 1.
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


class BoundingBox(BaseObject):

    def __init__(self, toplevel_obj):

        self._toplevel_obj = toplevel_obj

        scalings = {
            "X": (.5, 1., 1.),
            "Y": (1., .5, 1.),
            "Z": (1., 1., .5)
        }

        edge_offset = .52
        minmax = (-edge_offset, edge_offset)
        corners = [(x, y, z) for x in minmax for y in minmax for z in minmax]

        x1, y1, z1 = origin1 = corners.pop()
        edge_origins = [origin1]

        for corner in corners[:]:

            x, y, z = corner

            if (x == x1 and y != y1 and z != z1) \
                    or (y == y1 and x != x1 and z != z1) \
                    or (z == z1 and x != x1 and y != y1):

                edge_origins.append(corner)
                corners.remove(corner)

                if len(corners) == 4:
                    break

        self._corners = edge_origins + corners
        self._edges = {}
        edge_data = []
        pickable_type_id = PickableTypes.get_id("bbox_edge")

        for i, corner1 in enumerate(edge_origins):

            x1, y1, z1 = corner1

            for corner2 in corners:

                x2, y2, z2 = corner2

                if (x1 == x2 and y1 == y2):
                    axis = "Z"
                elif (x1 == x2 and z1 == z2):
                    axis = "Y"
                elif (y1 == y2 and z1 == z2):
                    axis = "X"
                else:
                    continue

                j = self._corners.index(corner2)
                edge = Mgr.do("create_bbox_edge", self, axis, i)
                color_id = edge.get_picking_color_id()
                picking_color = get_color_vec(color_id, pickable_type_id)
                self._edges[color_id] = edge
                edge_data.append(((i, j), axis, picking_color))

        vertex_format = GeomVertexFormat.get_v3cp()
        vertex_data = GeomVertexData("bbox_data", vertex_format, Geom.UH_static)

        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        lines = GeomLines(Geom.UH_static)

        for indices, axis, color in edge_data:

            for index in indices:
                x, y, z = self._corners[index]
                pos_writer.add_data3f(x, y, z)
                col_writer.add_data4f(color)
                scalx, scaly, scalz = scalings[axis]
                pos_writer.add_data3f(scalx * x, scaly * y, scalz * z)
                col_writer.add_data4f(color)
                lines.add_next_vertices(2)

        bbox_geom = Geom(vertex_data)
        bbox_geom.add_primitive(lines)
        bbox_node = GeomNode("bounding_box")
        bbox_node.add_geom(bbox_geom)
        self._origin = toplevel_obj.get_origin().attach_new_node(bbox_node)
        self._origin.set_light_off()
        self._origin.set_texture_off()
        self._origin.set_color(1., 1., 1., 1.)
        self._origin.set_color_scale_off()

    def destroy(self):

        self.unregister()

        self._edges = {}
        self._origin.remove_node()
        self._origin = None

    def get_origin(self):

        return self._origin

    def get_corner_pos(self, corner_index):

        corner_pos = Point3(self._corners[corner_index])

        return self.world.get_relative_point(self._origin, corner_pos)

    def get_toplevel_object(self):

        return self._toplevel_obj

    def register(self):

        obj_type = "bbox_edge"
        Mgr.do("register_%s_objs" % obj_type, self._edges.itervalues())

    def unregister(self):

        obj_type = "bbox_edge"
        Mgr.do("unregister_%s_objs" % obj_type, self._edges.itervalues())

    def update(self, point_min, point_max):

        vec = point_max - point_min
        scale_factors = [max(.0001, abs(factor)) for factor in vec]
        self._origin.set_scale(*scale_factors)
        self._origin.set_pos(point_min + vec * .5)

    def show(self, *args, **kwargs):

        self._origin.show(*args, **kwargs)

    def hide(self, *args, **kwargs):

        self._origin.hide(*args, **kwargs)

    def flash(self):

        orig = self._origin
        hidden = orig.is_hidden()
        data = {"flash_count": 0, "state": ["shown", "hidden"]}

        def do_flash(task):

            state = data["state"][1 if hidden else 0]
            orig.show() if state == "hidden" else orig.hide()
            data["state"].reverse()
            data["flash_count"] += 1

            return task.again if data["flash_count"] < 4 else None

        Mgr.add_task(.2, do_flash, "do_flash")


Mgr.accept("create_bbox", lambda toplevel_obj: BoundingBox(toplevel_obj))
MainObjects.add_class(BBoxEdgeManager)
