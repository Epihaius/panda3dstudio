from ..base import *


class PivotAxisManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "pivot_axis", self.__create_pivot_axis,
                               "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("pivot_axis")

    def __create_pivot_axis(self, pivot_gizmo, axis):

        picking_col_id = self.get_next_picking_color_id()
        pivot_axis = PivotAxis(pivot_gizmo, axis, picking_col_id)

        return pivot_axis, picking_col_id


class PivotGizmoManager(BaseObject):

    def __init__(self):

        pivot_gizmo_root = self.cam.attach_new_node("pivot_gizmo_root")
        pivot_gizmo_root.set_bin("fixed", 50)
        pivot_gizmo_root.set_depth_test(False)
        pivot_gizmo_root.set_depth_write(False)
        pivot_gizmo_root.hide()
        self._pivot_gizmo_root = pivot_gizmo_root
        Mgr.expose("pivot_gizmo_root", lambda: self._pivot_gizmo_root)
        Mgr.accept("create_pivot_gizmo", self.__create_pivot_gizmo)
        Mgr.accept("show_pivot_gizmos", self.__show_pivot_gizmos)

    def __create_pivot_gizmo(self, toplevel_obj):

        pivot_gizmo = PivotGizmo(toplevel_obj)

        return pivot_gizmo

    def __update_pivot_gizmos(self, task):

        objs = Mgr.get("objects")

        for obj in objs:
            pivot_gizmo = obj.get_pivot_gizmo()
            pivot_gizmo.get_base().look_at(obj.get_pivot())

        return task.cont

    def __show_pivot_gizmos(self, show=True):

        if show:
            self._pivot_gizmo_root.show()
            Mgr.add_task(self.__update_pivot_gizmos, "update_pivot_gizmos", sort=48)
        else:
            self._pivot_gizmo_root.hide()
            Mgr.remove_task("update_pivot_gizmos")


class PivotAxis(BaseObject):

    def __init__(self, pivot_gizmo, axis, picking_col_id):

        self._pivot_gizmo = pivot_gizmo
        self._axis = axis
        self._picking_col_id = picking_col_id

    def get_toplevel_object(self):

        return self._pivot_gizmo.get_toplevel_object()

    def get_picking_color_id(self):

        return self._picking_col_id

    def get_axis(self):

        return self._axis

    def get_point_at_screen_pos(self, screen_pos):

        pivot = self._pivot_gizmo.get_toplevel_object().get_pivot()
        vec_coords = [0., 0., 0.]
        vec_coords["xyz".index(self._axis)] = 1.
        axis_vec = V3D(self.world.get_relative_vector(pivot, Vec3(*vec_coords)))
        cam_vec = V3D(self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.)))
        cross_vec = axis_vec ** cam_vec

        point1 = pivot.get_pos(self.world)

        if not cross_vec.normalize():
            return point1

        point2 = point1 + axis_vec
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


class PivotGizmo(object):

    _original = None

    _size = 1.
    _label_size = .5

    _axis_colors = {
        "selected": {
            "x": VBase4(.7, 0., 0., 1.),
            "y": VBase4(0., .7, 0., 1.),
            "z": VBase4(0., 0., .7, 1.)
        },
        "deselected": {
            "x": VBase4(.3, .2, .2, 1.),
            "y": VBase4(.2, .3, .2, 1.),
            "z": VBase4(.2, .2, .3, 1.)
        }
    }
    _axis_label_colors = {
        "selected": {
            "x": VBase4(1., .6, .6, 1.),
            "y": VBase4(.6, 1., .6, 1.),
            "z": VBase4(.6, .6, 1., 1.)
        },
        "deselected": {
            "x": VBase4(.4, 0., 0., 1.),
            "y": VBase4(0., .2, 0., 1.),
            "z": VBase4(0., 0., .4, 1.)
        }
    }

    @classmethod
    def __create_original(cls):

        node = NodePath("pivot_gizmo_base")
        cls._original = node
        pivot = node.attach_new_node("pivot_gizmo_pivot")
        pivot.set_y(8.)
        bounds = BoundingSphere(Point3(), 1.1)
        pivot.node().set_bounds(bounds)
        pivot.node().set_final(True)
        origin = pivot.attach_new_node("pivot_gizmo")
        axis_label_root = origin.attach_new_node("axis_label_root")

        cls.__create_geom(origin)

        points = (
            ((-.1, -.15), (.1, .15)),
            ((-.1, .15), (.1, -.15))
        )
        label = cls.__create_axis_label(axis_label_root, "x", points)
        label.set_x(1.3)

        points = (
            ((-.1, -.15), (.1, .15)),
            ((-.1, .15), (0., 0.))
        )
        label = cls.__create_axis_label(axis_label_root, "y", points)
        label.set_y(1.3)

        points = (
            ((-.1, -.15), (.1, -.15)),
            ((-.1, .15), (.1, .15)),
            ((-.1, -.15), (.1, .15))
        )
        label = cls.__create_axis_label(axis_label_root, "z", points)
        label.set_z(1.3)

        picking_mask = Mgr.get("picking_mask")
        axis_label_root.hide(picking_mask)

    @classmethod
    def __create_geom(cls, origin):

        vertex_format = GeomVertexFormat.get_v3cp()

        angle = math.pi * 2. / 3.
        shaft_radius = .035
        head_radius = .1
        axis_colors = cls._axis_colors["deselected"]

        for i, axis in enumerate("xyz"):

            vertex_data = GeomVertexData("pivot_axis_data", vertex_format, Geom.UH_static)
            pos_writer = GeomVertexWriter(vertex_data, "vertex")

            lines = GeomLines(Geom.UH_static)

            for j in range(3):

                pos = VBase3()
                pos_writer.add_data3f(pos)

                pos[i] = .2
                pos[i - 1] = math.cos(angle * j) * shaft_radius
                pos[i - 2] = math.sin(angle * j) * shaft_radius
                pos_writer.add_data3f(pos)

                index = j * 5
                lines.add_vertices(index, index + 1)
                lines.add_vertices(index + 1, index + 2)

                pos[i] = .8
                pos_writer.add_data3f(pos)

                pos[i - 1] = math.cos(angle * j) * head_radius
                pos[i - 2] = math.sin(angle * j) * head_radius
                pos_writer.add_data3f(pos)

                pos[i] = 1.
                pos[i - 1] = 0.
                pos[i - 2] = 0.
                pos_writer.add_data3f(pos)

                lines.add_vertices(index + 3, index + 4)

            index1a = 12
            index1b = 13

            for j in range(3):

                index2a = j * 5 + 2
                lines.add_vertices(index1a, index2a)
                index1a = index2a

                index2b = j * 5 + 3
                lines.add_vertices(index1b, index2b)
                index1b = index2b

            axis_geom = Geom(vertex_data)
            axis_geom.add_primitive(lines)
            axis_node = GeomNode("pivot_%s_axis" % axis)
            axis_node.add_geom(axis_geom)
            np = origin.attach_new_node(axis_node)
            np.set_color(axis_colors[axis])

    @classmethod
    def __create_axis_label(cls, root, axis, points):

        vertex_format = GeomVertexFormat.get_v3()

        vertex_data = GeomVertexData("axis_label_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        label = GeomLines(Geom.UH_static)

        for point_group in points:

            for point in point_group:
                x, z = point
                pos_writer.add_data3f(x, 0., z)

            label.add_next_vertices(2)

        label_geom = Geom(vertex_data)
        label_geom.add_primitive(label)
        label_node = GeomNode("%s_axis_label" % axis)
        label_node.add_geom(label_geom)
        node_path = root.attach_new_node(label_node)
        node_path.set_billboard_point_eye()
        node_path.set_scale(cls._label_size)
        node_path.set_color(cls._axis_label_colors["deselected"][axis])

        return node_path

    def __get_original(self):

        if not self._original:
            PivotGizmo.__create_original()

        return self._original

    original = property(__get_original)

    def __getstate__(self):

        d = self.__dict__.copy()
        d["_base"] = NodePath("pivot_gizmo_base")
        d["_origin"] = NodePath("pivot_gizmo")
        d["_axis_label_root"] = NodePath("axis_label_root")

        return d

    def __setstate__(self, state):

        self.__dict__ = state

        node = self._base
        node.reparent_to(Mgr.get("pivot_gizmo_root"))
        pivot = node.attach_new_node("pivot_gizmo_pivot")
        pivot.set_y(8.)
        bounds = BoundingSphere(Point3(), 1.1)
        pivot.node().set_bounds(bounds)
        pivot.node().set_final(True)
        origin = self._origin
        origin.reparent_to(pivot)
        axis_label_root = self._axis_label_root
        axis_label_root.reparent_to(origin)
        axis_label_root.hide(Mgr.get("picking_mask"))
        axis_nps = self._axis_nps
        axis_labels = self._axis_labels

        for axis in "xyz":
            axis_nps[axis].reparent_to(origin)
            axis_labels[axis].reparent_to(axis_label_root)

    def __init__(self, toplevel_obj):

        self._toplevel_obj = toplevel_obj
        self._base = self.original.copy_to(Mgr.get("pivot_gizmo_root"))
        origin = self._base.get_child(0).get_child(0)
        origin.set_compass(toplevel_obj.get_pivot())
        self._origin = origin

        self._axis_nps = {}
        self._axis_objs = {}
        self._axis_labels = {}
        self._axis_label_root = label_root = origin.find("**/axis_label_root")

        pickable_type_id = PickableTypes.get_id("pivot_axis")

        for axis in "xyz":
            axis_label = label_root.find("**/%s_axis_label" % axis)
            self._axis_labels[axis] = axis_label
            axis_obj = Mgr.do("create_pivot_axis", self, axis)
            picking_col_id = axis_obj.get_picking_color_id()
            self._axis_objs[picking_col_id] = axis_obj
            axis_np = origin.find("**/pivot_%s_axis" % axis)
            self._axis_nps[axis] = axis_np
            geom = axis_np.node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            color = get_color_vec(picking_col_id, pickable_type_id)
            geom.set_vertex_data(vertex_data.set_color(color))

    def destroy(self):

        self.unregister()

        self._axis_objs = {}
        self._origin.remove_node()
        self._origin = None
        self._base.remove_node()
        self._base = None

    def get_origin(self):

        return self._origin

    def get_base(self):

        return self._base

    def get_toplevel_object(self):

        return self._toplevel_obj

    def set_size(self, size):

        if self._size == size:
            return False

        self._size = size
        self._origin.set_scale(size)

        return True

    def get_size(self):

        return self._size

    def set_label_size(self, size):

        if self._label_size == size:
            return False

        self._label_size = size

        for label in self._axis_labels.itervalues():
            label.set_scale(size)

        return True

    def get_label_size(self):

        return self._label_size

    def show_labels(self, show=True):

        if self._axis_label_root.is_hidden() != show:
            return False

        if show:
            self._axis_label_root.show()
        else:
            self._axis_label_root.hide()

        return True

    def register(self):

        obj_type = "pivot_axis"
        Mgr.do("register_%s_objs" % obj_type, self._axis_objs.itervalues())

    def unregister(self):

        obj_type = "pivot_axis"
        Mgr.do("unregister_%s_objs" % obj_type, self._axis_objs.itervalues())

    def update_selection_state(self, is_selected=True):

        key = "selected" if is_selected else "deselected"

        for axis in "xyz":
            self._axis_nps[axis].set_color(self._axis_colors[key][axis])
            self._axis_labels[axis].set_color(self._axis_label_colors[key][axis])


MainObjects.add_class(PivotAxisManager)
MainObjects.add_class(PivotGizmoManager)
