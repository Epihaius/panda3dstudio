from ..base import *


class WorldAxesTripod(BaseObject):

    def __init__(self):

        pos = Point3(-1.22, 0., -.89)
        self._root = self.screen.attach_new_node("world_axes")
        self._root.set_pos(pos)
        self._axis_tripod = None
        self._nav_indic = None
        self._axis_labels = {}
        self._axis_label_colors = {
            "inactive": {
                "X": VBase4(.4, 0., 0., 1.),
                "Y": VBase4(0., .2, 0., 1.),
                "Z": VBase4(0., 0., .4, 1.)
            },
            "active": {
                "X": VBase4(1., .6, .6, 1.),
                "Y": VBase4(.6, 1., .6, 1.),
                "Z": VBase4(.6, .6, 1., 1.)
            }
        }

        Mgr.accept("update_world_axes", self.__update)
        Mgr.accept("start_updating_world_axes", self.__init_update)
        Mgr.accept("stop_updating_world_axes", self.__end_update)

    def setup(self):

        self.__create_axis_tripod()
        self.__create_navigation_indicator()

        points = (
            ((-.01, -.015), (.01, .015)),
            ((-.01, .015), (.01, -.015))
        )
        label = self.__create_axis_label(points)
        label.set_pos(.08, 0., .02)
        self._axis_labels["X"] = label

        points = (
            ((-.01, -.015), (.01, .015)),
            ((-.01, .015), (0., 0.))
        )
        label = self.__create_axis_label(points)
        label.set_pos(0., .08, .02)
        self._axis_labels["Y"] = label

        points = (
            ((-.01, -.015), (.01, -.015)),
            ((-.01, .015), (.01, .015)),
            ((-.01, -.015), (.01, .015))
        )
        label = self.__create_axis_label(points)
        label.set_pos(.02, 0., .08)
        self._axis_labels["Z"] = label

        for axis in "XYZ":
            self._axis_labels[axis].set_color(
                self._axis_label_colors["inactive"][axis])

        return True

    def __create_axis_tripod(self):

        vertex_format = GeomVertexFormat.get_v3n3cpt2()

        vertex_data = GeomVertexData(
            "axis_tripod_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        col_writer = GeomVertexWriter(vertex_data, "color")

        tripod = GeomLines(Geom.UH_static)

        for i in range(3):
            v_pos = VBase3()
            pos_writer.add_data3f(v_pos)
            v_pos[i] = .1
            pos_writer.add_data3f(v_pos)
            color = VBase4(0., 0., 0., 1.)
            color[i] = 1.
            col_writer.add_data4f(color)
            col_writer.add_data4f(color)
            tripod.add_vertices(i * 2, i * 2 + 1)

        tripod_geom = Geom(vertex_data)
        tripod_geom.add_primitive(tripod)
        tripod_node = GeomNode("axis_tripod")
        tripod_node.add_geom(tripod_geom)
        self._axis_tripod = self._root.attach_new_node(tripod_node)
        self._axis_tripod.set_hpr(self.world.get_hpr(self.cam))

    def __create_navigation_indicator(self):

        vertex_format = GeomVertexFormat.get_v3n3cpt2()

        vertex_data = GeomVertexData(
            "circle_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        circle = GeomLines(Geom.UH_static)

        segments = 20
        radius = .11
        angle = 2. * math.pi / segments

        pos_writer.add_data3f(radius, 0., 0.)

        for i in xrange(1, segments):

            x = math.cos(angle * i) * radius
            z = math.sin(angle * i) * radius
            pos_writer.add_data3f(x, 0., z)

            circle.add_vertices(i - 1, i)

        circle.add_vertices(i, 0)

        circle_geom = Geom(vertex_data)
        circle_geom.add_primitive(circle)
        circle_node = GeomNode("navigation_indicator_circle")
        circle_node.add_geom(circle_geom)
        self._nav_indic = self._root.attach_new_node(circle_node)
        self._nav_indic.hide()

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
        label_node = GeomNode("world_axis_label")
        label_node.add_geom(label_geom)
        node_path = self._axis_tripod.attach_new_node(label_node)
        node_path.set_billboard_point_eye()

        return node_path

    def __update(self, task=None):

        self._axis_tripod.set_hpr(self.world.get_hpr(self.cam))

        return task.cont if task else None

    def __init_update(self):

        Mgr.add_task(self.__update, "update_world_axes")
        self._nav_indic.show()

        for axis in "XYZ":
            self._axis_labels[axis].set_color(
                self._axis_label_colors["active"][axis])

    def __end_update(self):

        Mgr.remove_task("update_world_axes")
        self._nav_indic.hide()

        for axis in "XYZ":
            self._axis_labels[axis].set_color(
                self._axis_label_colors["inactive"][axis])


MainObjects.add_class(WorldAxesTripod)
