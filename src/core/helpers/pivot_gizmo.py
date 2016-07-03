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

        self._pivot_gizmo_root = None
        self._pivot_gizmo_roots = {}
        self._compass_props = CompassEffect.P_pos | CompassEffect.P_rot
        Mgr.expose("pivot_gizmo_roots", lambda: self._pivot_gizmo_roots)
        Mgr.accept("create_pivot_gizmo", self.__create_pivot_gizmo)
        Mgr.accept("show_pivot_gizmos", self.__show_pivot_gizmos)

    def setup(self):

        pivot_gizmo_root = self.cam().attach_new_node("pivot_gizmo_root")
        pivot_gizmo_root.set_bin("fixed", 50)
        pivot_gizmo_root.set_depth_test(False)
        pivot_gizmo_root.set_depth_write(False)
        pivot_gizmo_root.node().set_bounds(OmniBoundingVolume())
        pivot_gizmo_root.node().set_final(True)
        pivot_gizmo_root.hide()
        self._pivot_gizmo_root = pivot_gizmo_root
        render_masks = Mgr.get("render_masks")
        picking_masks = Mgr.get("picking_masks")
        root_persp = pivot_gizmo_root.attach_new_node("pivot_gizmo_root_persp")
        root_persp.hide(render_masks["ortho"] | picking_masks["ortho"])
        root_ortho = pivot_gizmo_root.attach_new_node("pivot_gizmo_root_ortho")
        root_ortho.set_scale(50.)
        root_ortho.hide(render_masks["persp"] | picking_masks["persp"])
        self._pivot_gizmo_roots["persp"] = root_persp
        self._pivot_gizmo_roots["ortho"] = root_ortho

        return True

    def __create_pivot_gizmo(self, toplevel_obj):

        pivot_gizmo = PivotGizmo(toplevel_obj)

        return pivot_gizmo

    def __show_pivot_gizmos(self, show=True):

        objs = Mgr.get("objects")

        if show:

            for obj in objs:
                pivot_gizmo = obj.get_pivot_gizmo()
                pivot_gizmo.get_base().set_billboard_point_world(obj.get_pivot(), 8.)
                pivot_gizmo.get_origin().set_compass(obj.get_pivot())
                compass_effect = CompassEffect.make(obj.get_pivot(), self._compass_props)
                pivot_gizmo.get_origin("ortho").set_effect(compass_effect)

            self._pivot_gizmo_root.show()

        else:

            self._pivot_gizmo_root.hide()

            for obj in objs:
                pivot_gizmo = obj.get_pivot_gizmo()
                pivot_gizmo.get_base().clear_billboard()
                pivot_gizmo.get_origin().clear_compass()
                pivot_gizmo.get_origin("ortho").clear_effect(CompassEffect.get_class_type())


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

        cam = self.cam()
        pivot = self._pivot_gizmo.get_toplevel_object().get_pivot()
        vec_coords = [0., 0., 0.]
        vec_coords["xyz".index(self._axis)] = 1.
        axis_vec = V3D(self.world.get_relative_vector(pivot, Vec3(*vec_coords)))
        cam_vec = V3D(self.world.get_relative_vector(cam, Vec3.forward()))
        cross_vec = axis_vec ** cam_vec

        point1 = pivot.get_pos(self.world)

        if not cross_vec.normalize():
            return point1

        point2 = point1 + axis_vec
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
        origin = node.attach_new_node("pivot_gizmo")
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

        picking_masks = Mgr.get("picking_masks")
        axis_label_root.hide(picking_masks["all"])

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

        state = self.__dict__.copy()
        state["_base"] = NodePath("pivot_gizmo_base")
        origin_persp = NodePath("pivot_gizmo")
        state["_origins"] = {"persp": origin_persp}
        label_root_persp = NodePath("axis_label_root")
        state["_axis_label_roots"] = {"persp": label_root_persp}

        for axis in "xyz":
            state["_axis_nps"] = state["_axis_nps"].copy()
            state["_axis_labels"] = state["_axis_labels"].copy()
            del state["_axis_nps"][axis]
            del state["_axis_labels"][axis]

        del state["_axis_nps"]["ortho"]
        del state["_axis_labels"]["ortho"]

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        gizmo_root = Mgr.get("pivot_gizmo_roots")["persp"]
        node = self._base
        node.reparent_to(gizmo_root)
        origin = self._origins["persp"]
        origin.reparent_to(node)

        label_root = self._axis_label_roots["persp"]
        label_root.reparent_to(origin)
        label_root.hide(Mgr.get("picking_masks")["all"])

        axis_nps = self._axis_nps
        axis_labels = self._axis_labels

        for axis in "xyz":
            axis_nps[axis] = NodePathCollection()
            axis_labels[axis] = NodePathCollection()

        for axis in "xyz":
            np = axis_nps["persp"][axis]
            axis_nps[axis].add_path(np)
            np.reparent_to(origin)
            label = axis_labels["persp"][axis]
            axis_labels[axis].add_path(label)
            label.reparent_to(label_root)

        self.__create_geoms_for_ortho_lens()

    def __init__(self, toplevel_obj):

        self._toplevel_obj = toplevel_obj
        gizmo_roots = Mgr.get("pivot_gizmo_roots")
        self._base = self.original.copy_to(gizmo_roots["persp"])
        origin = self._base.get_child(0)
        self._origins = {"persp": origin}

        self._axis_objs = {}
        self._axis_nps = {"persp": {}}
        self._axis_labels = {"persp": {}}
        label_root = origin.find("**/axis_label_root")
        self._axis_label_roots = {"persp": label_root}

        pickable_type_id = PickableTypes.get_id("pivot_axis")

        for axis in "xyz":
            axis_label = label_root.find_all_matches("**/%s_axis_label" % axis)
            self._axis_labels[axis] = axis_label
            self._axis_labels["persp"][axis] = axis_label.get_path(0)
            axis_obj = Mgr.do("create_pivot_axis", self, axis)
            picking_col_id = axis_obj.get_picking_color_id()
            self._axis_objs[picking_col_id] = axis_obj
            axis_np = origin.find_all_matches("**/pivot_%s_axis" % axis)
            self._axis_nps[axis] = axis_np
            self._axis_nps["persp"][axis] = axis_np.get_path(0)
            geom = axis_np[0].node().modify_geom(0)
            vertex_data = geom.modify_vertex_data()
            color = get_color_vec(picking_col_id, pickable_type_id)
            geom.set_vertex_data(vertex_data.set_color(color))

        self.__create_geoms_for_ortho_lens()

    def destroy(self):

        self.unregister()

        self._axis_objs = None

        for origin in self._origins.itervalues():
            origin.remove_node()

        self._origins = None
        self._base.remove_node()
        self._base = None
        self._axis_nps = None
        self._axis_label_roots = None
        self._axis_labels = None

    def __create_geoms_for_ortho_lens(self):

        gizmo_root = Mgr.get("pivot_gizmo_roots")["ortho"]
        origin_ortho = self._origins["persp"].copy_to(gizmo_root)
        origin_ortho.set_name("pivot_gizmo_ortho")
        self._origins["ortho"] = origin_ortho
        label_root_ortho = origin_ortho.find("**/axis_label_root")
        self._axis_label_roots["ortho"] = label_root_ortho
        self._axis_nps["ortho"] = {}
        self._axis_labels["ortho"] = {}

        for axis in "xyz":
            axis_np = origin_ortho.find("**/pivot_%s_axis" % axis)
            self._axis_nps[axis].add_path(axis_np)
            self._axis_nps["ortho"][axis] = axis_np
            axis_label = label_root_ortho.find("**/%s_axis_label" % axis)
            self._axis_labels[axis].add_path(axis_label)
            self._axis_labels["ortho"][axis] = axis_label

    def get_base(self):

        return self._base

    def get_origin(self, lens_type="persp"):

        return self._origins[lens_type]

    def get_toplevel_object(self):

        return self._toplevel_obj

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
