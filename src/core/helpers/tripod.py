from ..base import *


class TripodAxisManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "tripod_helper_axis", self.__create_tripod_axis,
                               "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("tripod_helper_axis")

    def __create_tripod_axis(self, tripod, axis):

        picking_col_id = self.get_next_picking_color_id()
        tripod_axis = TripodHelperAxis(tripod, axis, picking_col_id)

        return tripod_axis, picking_col_id


class TripodManager(ObjectManager, CreationPhaseManager, ObjPropDefaultsManager):

    def __init__(self):

        ObjectManager.__init__(self, "tripod_helper", self.__create_tripod)
        CreationPhaseManager.__init__(self, "tripod_helper")
        ObjPropDefaultsManager.__init__(self, "tripod_helper")

        self.set_property_default("size", 1.)
        self.set_property_default("label_size", 1.)
        self.set_property_default("labels", True)

        self._draw_plane = None

        Mgr.accept("inst_create_tripod_helper", self.__create_tripod_instantly)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "axis tripod helper"
        status_text["phase1"] = "draw out the tripod"

        CreationPhaseManager.setup(self, creation_phases, status_text)

        return True

    def __create_tripod_instantly(self, origin_pos):

        tripod_id = self.generate_object_id()
        obj_type = self.get_object_type()
        next_name = Mgr.get("next_obj_name", obj_type)
        tripod = Mgr.do("create_tripod_helper", tripod_id, name, origin_pos)
        prop_defaults = self.get_property_defaults()
        tripod.set_size(prop_defaults["size"])
        tripod.set_label_size(prop_defaults["label_size"])
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(tripod)

    def __create_tripod(self, tripod_id, name, origin_pos):

        prop_defaults = self.get_property_defaults()
        show_labels = prop_defaults["labels"]
        tripod = TripodHelper(tripod_id, name, origin_pos, show_labels)
        tripod.set_label_size(prop_defaults["label_size"])

        return tripod, tripod_id

    def __start_creation_phase1(self):
        """ Start drawing out tripod """

        tripod_id = self.generate_object_id()
        name = Mgr.get("next_obj_name", self.get_object_type())
        origin_pos = self.get_origin_pos()
        tripod = Mgr.do("create_tripod_helper", tripod_id, name, origin_pos)
        self.init_object(tripod)

        # Create the plane parallel to the camera and going through the tripod
        # origin, used to determine the size drawn by the user.

        normal = self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.))
        grid_origin = Mgr.get(("grid", "origin"))
        pos = self.world.get_relative_point(grid_origin, origin_pos)
        self._draw_plane = Plane(normal, pos)

    def __creation_phase1(self):
        """ Draw out tripod """

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


class TripodHelperAxis(BaseObject):

    def __init__(self, tripod, axis, picking_col_id):

        self._tripod = tripod
        self._axis = axis
        self._picking_col_id = picking_col_id

    def get_toplevel_object(self):

        return self._tripod

    def get_picking_color_id(self):

        return self._picking_col_id

    def get_axis(self):

        return self._axis

    def get_point_at_screen_pos(self, screen_pos):

        origin = self._tripod.get_origin()
        vec_coords = [0., 0., 0.]
        vec_coords["XYZ".index(self._axis)] = 1.
        axis_vec = V3D(self.world.get_relative_vector(origin, Vec3(*vec_coords)))
        cam_vec = V3D(self.world.get_relative_vector(self.cam, Vec3(0., 1., 0.)))
        cross_vec = axis_vec ** cam_vec

        point1 = origin.get_pos(self.world)

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


class TripodHelper(TopLevelObject):

    def __getstate__(self):

        d = self.__dict__.copy()
        d["_pivot"] = NodePath(self.get_pivot().get_name())
        d["_origin"] = NodePath(self.get_origin().get_name())
        d["_axis_root"] = NodePath("tripod_helper")
        d["_axis_label_root"] = NodePath("axis_label_root")
        d["_size"] = 1.

        return d

    def __setstate__(self, state):

        self.__dict__ = state

        pivot = self.get_pivot()
        pivot.reparent_to(Mgr.get("object_root"))
        origin = self.get_origin()
        origin.reparent_to(pivot)
        origin.set_light_off()
        axis_root = self._axis_root
        axis_root.reparent_to(origin)
        axis_root.set_bin("fixed", 50)
        axis_root.set_depth_test(False)
        axis_root.set_depth_write(False)
        axis_label_root = self._axis_label_root
        axis_label_root.reparent_to(axis_root)
        axis_label_root.hide(Mgr.get("picking_mask"))
        axis_nps = self._axis_nps
        axis_labels = self._axis_labels

        for axis in "XYZ":
            axis_nps[axis].reparent_to(axis_root)
            axis_labels[axis].reparent_to(axis_label_root)

    def __init__(self, tripod_id, name, origin_pos, show_labels=True):

        TopLevelObject.__init__(self, "tripod_helper", tripod_id, name, origin_pos,
                                has_color=False)

        self._type_prop_ids = ["size", "label_size", "labels"]
        self._size = 0.
        self._label_size = 1.

        self._axis_colors = {
            "selected": {
                "X": VBase4(.7, 0., 0., 1.),
                "Y": VBase4(0., .7, 0., 1.),
                "Z": VBase4(0., 0., .7, 1.)
            },
            "deselected": {
                "X": VBase4(.3, .2, .2, 1.),
                "Y": VBase4(.2, .3, .2, 1.),
                "Z": VBase4(.2, .2, .3, 1.)
            }
        }
        self._axis_label_colors = {
            "selected": {
                "X": VBase4(1., .6, .6, 1.),
                "Y": VBase4(.6, 1., .6, 1.),
                "Z": VBase4(.6, .6, 1., 1.)
            },
            "deselected": {
                "X": VBase4(.4, 0., 0., 1.),
                "Y": VBase4(0., .2, 0., 1.),
                "Z": VBase4(0., 0., .4, 1.)
            }
        }

        origin = self.get_origin()
        origin.set_light_off()

        self._axis_root = origin.attach_new_node("tripod_helper")
        self._axis_root.set_bin("fixed", 50)
        self._axis_root.set_depth_test(False)
        self._axis_root.set_depth_write(False)

        self._axis_nps = {}
        self._axis_objs = {}
        self._axis_labels = {}
        self._axis_label_root = self._axis_root.attach_new_node("axis_label_root")

        for axis in "XYZ":
            axis_obj = Mgr.do("create_tripod_helper_axis", self, axis)
            self._axis_objs[axis_obj.get_picking_color_id()] = axis_obj

        self.__create_geom()

        points = (
            ((-.1, -.15), (.1, .15)),
            ((-.1, .15), (.1, -.15))
        )
        label = self.__create_axis_label(points)
        label.set_x(1.3)
        self._axis_labels["X"] = label

        points = (
            ((-.1, -.15), (.1, .15)),
            ((-.1, .15), (0., 0.))
        )
        label = self.__create_axis_label(points)
        label.set_y(1.3)
        self._axis_labels["Y"] = label

        points = (
            ((-.1, -.15), (.1, -.15)),
            ((-.1, .15), (.1, .15)),
            ((-.1, -.15), (.1, .15))
        )
        label = self.__create_axis_label(points)
        label.set_z(1.3)
        self._axis_labels["Z"] = label

        picking_mask = Mgr.get("picking_mask")
        self._axis_label_root.hide(picking_mask)

        for axis in "XYZ":
            self._axis_labels[axis].set_color(
                self._axis_label_colors["deselected"][axis])

        self.show_labels(show_labels)

    def __create_geom(self):

        vertex_format = GeomVertexFormat.get_v3n3cpt2()
        vertex_data = GeomVertexData("tripod_helper_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        angle = math.pi * 2. / 3.
        shaft_radius = .035
        head_radius = .1
        pickable_type_id = PickableTypes.get_id("tripod_helper_axis")
        axis_ids = dict((obj.get_axis(), obj.get_picking_color_id())
                        for obj in self._axis_objs.itervalues())

        for i, axis in enumerate("XYZ"):

            lines = GeomLines(Geom.UH_static)
            color = get_color_vec(axis_ids[axis], pickable_type_id)

            for j in range(3):

                pos = VBase3()
                pos_writer.add_data3f(pos)
                col_writer.add_data4f(color)

                pos[i] = .2
                pos[i - 1] = math.cos(angle * j) * shaft_radius
                pos[i - 2] = math.sin(angle * j) * shaft_radius

                pos_writer.add_data3f(pos)
                col_writer.add_data4f(color)

                index = i * 15 + j * 5
                lines.add_vertices(index, index + 1)
                lines.add_vertices(index + 1, index + 2)

                pos[i] = .8

                pos_writer.add_data3f(pos)
                col_writer.add_data4f(color)

                pos[i - 1] = math.cos(angle * j) * head_radius
                pos[i - 2] = math.sin(angle * j) * head_radius

                pos_writer.add_data3f(pos)
                col_writer.add_data4f(color)

                pos[i] = 1.
                pos[i - 1] = 0.
                pos[i - 2] = 0.

                pos_writer.add_data3f(pos)
                col_writer.add_data4f(color)

                lines.add_vertices(index + 3, index + 4)

            index1a = i * 15 + 12
            index1b = i * 15 + 13

            for j in range(3):

                index2a = i * 15 + j * 5 + 2
                lines.add_vertices(index1a, index2a)
                index1a = index2a

                index2b = i * 15 + j * 5 + 3
                lines.add_vertices(index1b, index2b)
                index1b = index2b

            tripod_geom = Geom(vertex_data)
            tripod_geom.add_primitive(lines)
            tripod_node = GeomNode("tripod_helper_axis")
            tripod_node.add_geom(tripod_geom)
            self._axis_nps[axis] = self._axis_root.attach_new_node(tripod_node)
            self._axis_nps[axis].set_color(self._axis_colors["deselected"][axis])

    def __create_axis_label(self, points):

        vertex_format = GeomVertexFormat.get_v3n3cpt2()

        vertex_data = GeomVertexData(
            "axis_label_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        label = GeomLines(Geom.UH_static)

        for point_group in points:

            for point in point_group:

                x, z = point
                pos_writer.add_data3f(x, 0., z)

            label.add_next_vertices(2)

        label_geom = Geom(vertex_data)
        label_geom.add_primitive(label)
        label_node = GeomNode("axis_label")
        label_node.add_geom(label_geom)
        node_path = self._axis_label_root.attach_new_node(label_node)
        node_path.set_billboard_point_eye()

        return node_path

    def destroy(self, add_to_hist=True):

        TopLevelObject.destroy(self, add_to_hist)

        self.unregister()
        self._axis_objs = {}
        self._axis_root.remove_node()
        self._axis_root = None

    def set_size(self, size):

        if self._size == size:
            return False

        self._size = size
        self._axis_root.set_scale(size)

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

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "tripod_helper", prop_id,
                                self.get_property(prop_id, True))

        if prop_id == "size":
            if self.set_size(value):
                update_app()
                return True
        elif prop_id == "label_size":
            if self.set_label_size(value):
                update_app()
                return True
        elif prop_id == "labels":
            if self.show_labels(value):
                update_app()
                return True
        else:
            return TopLevelObject.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "size":
            return self._size
        elif prop_id == "label_size":
            return self._label_size
        elif prop_id == "labels":
            return not self._axis_label_root.is_hidden()

        return TopLevelObject.get_property(self, prop_id, for_remote_update)

    def get_property_ids(self):

        return TopLevelObject.get_property_ids(self) + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids

    def register(self):

        TopLevelObject.register(self)

        obj_type = "tripod_helper_axis"
        Mgr.do("register_%s_objs" % obj_type, self._axis_objs.itervalues())

    def unregister(self):

        obj_type = "tripod_helper_axis"
        Mgr.do("unregister_%s_objs" % obj_type, self._axis_objs.itervalues())

    def update_selection_state(self, is_selected=True):

        key = "selected" if is_selected else "deselected"

        for axis in "XYZ":
            self._axis_nps[axis].set_color(self._axis_colors[key][axis])
            self._axis_labels[axis].set_color(self._axis_label_colors[key][axis])

    def is_valid(self):

        return self._size > .001

    def finalize(self):

        pass


MainObjects.add_class(TripodManager)
MainObjects.add_class(TripodAxisManager)
