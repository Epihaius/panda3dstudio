from ..base import *
from panda3d.fx import ProjectionScreen
from math import pi, sin, cos


class TemporaryTexProjector:

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

        tmp_geom = NodePath("tmp_tex_proj_geom")
        tmp_geom.set_color_scale(.1)
        tmp_geom.set_bin("fixed", 50)
        tmp_geom.set_depth_test(False)
        tmp_geom.set_depth_write(False)
        cls._original_geom = tmp_geom

        # Create body.

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("tex_proj_body_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        lines = GeomLines(Geom.UH_static)
        edge_ends = []

        for corner in corners:
            for coord, axis in zip(corner, "xyz"):
                pos_writer.add_data3(corner)
                coord2 = coord + (1. if coord < 0. else -1.)
                pos = Point3(*corner)
                pos["xyz".index(axis)] = coord2
                pos_writer.add_data3(pos)
                lines.add_next_vertices(2)
                edge_ends.append((corner, pos))

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("tex_proj_body")
        node.add_geom(geom)

        body = tmp_geom.attach_new_node(node)
        body.set_scale(1.2, 1.8, 1.2)
        body.set_color(.7, 1., .7)

        # Create lens visualizations.

        def xform_point(point, proj_type):

            if proj_type == "orthographic":

                x, y, z = point
                y = (y + .5) * .5 + .9

            elif proj_type == "perspective":

                x, y, z = point
                y = (y + .5) * .5 + .9
                x *= y * .6666
                z *= y * .6666

            return (x, y, z)

        for proj_type in ("orthographic", "perspective"):

            vertex_data = GeomVertexData(f"tex_proj_lens_{proj_type}_viz_data",
                                         vertex_format, Geom.UH_static)
            pos_writer = GeomVertexWriter(vertex_data, "vertex")

            lines = GeomLines(Geom.UH_static)

            for points in edge_ends:

                for point in points:
                    pos_writer.add_data3(xform_point(point, proj_type))

                lines.add_next_vertices(2)

            geom = Geom(vertex_data)
            geom.add_primitive(lines)
            node = GeomNode(f"tex_proj_lens_{proj_type}_viz")
            node.add_geom(geom)
            lens_viz = tmp_geom.attach_new_node(node)
            lens_viz.hide(Mgr.get("picking_mask"))
            lens_viz.hide()
            lens_viz.set_color(.5, .8, .5)

        # Create tripod.

        angle = 2. * pi / 3.
        positions = [Point3(sin(angle * i), cos(angle * i), -1.5) for i in range(3)]

        vertex_data = GeomVertexData("tex_proj_tripod_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        lines = GeomLines(Geom.UH_static)

        pos_writer.add_data3(0., 0., 0.)

        for i, pos in enumerate(positions):
            pos_writer.add_data3(pos)
            lines.add_vertices(0, i + 1)

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("tex_proj_tripod")
        node.add_geom(geom)

        tripod = tmp_geom.attach_new_node(node)
        tripod.hide(Mgr.get("picking_mask"))
        tripod.set_z(-.6)
        tripod.set_color(.5, .8, .5)

    def __init__(self, pos, projection_type):

        self._size = 0.
        object_root = Mgr.get("object_root")
        self._temp_geom = tmp_geom = self.original_geom.copy_to(object_root)

        grid = Mgr.get("grid")
        active_grid_plane = grid.plane_id
        grid_origin = grid.origin

        if active_grid_plane == "xz":
            tmp_geom.set_pos_hpr(grid_origin, pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            tmp_geom.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 90.))
        else:
            tmp_geom.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 0.))

        lens_viz = tmp_geom.find(f"**/tex_proj_lens_{projection_type}_viz")
        lens_viz.show()

    def __del__(self):

        Notifiers.obj.debug('TemporaryTexProjector garbage-collected.')

    def destroy(self):

        self._temp_geom.remove_node()
        self._temp_geom = None

    @property
    def original_geom(self):

        if not self._original_geom:
            TemporaryTexProjector.__create_original_geom()

        return self._original_geom

    def set_size(self, size):

        s = max(size, .001)

        if self._size == s:
            return

        self._size = s
        self._temp_geom.set_scale(s)

    def is_valid(self):

        return self._size > .001

    def finalize(self):

        pos = self._temp_geom.get_pos(Mgr.get("grid").origin)

        for step in Mgr.do("create_tex_projector", pos, self._size):
            pass

        self.destroy()


class TexProjectorEdge:

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_picking_col_id"] = state.pop("picking_color_id")

        return state

    def __setstate__(self, state):

        state["picking_color_id"] = state.pop("_picking_col_id")
        self.__dict__ = state

    def __init__(self, projector, axis, corner_index, picking_col_id):

        self._projector = projector
        self._axis = axis
        self._corner_index = corner_index
        self.picking_color_id = picking_col_id

    def __del__(self):

        Notifiers.obj.debug('TexProjectorEdge garbage-collected.')

    def get_toplevel_object(self, get_group=False):

        return self._projector.get_toplevel_object(get_group)

    @property
    def toplevel_obj(self):

        return self.get_toplevel_object()

    def get_point_at_screen_pos(self, screen_pos):

        cam = GD.cam()
        body = self._projector.get_body()
        corner_pos = self._projector.get_corner_pos(self._corner_index)
        vec_coords = [0., 0., 0.]
        vec_coords["xyz".index(self._axis)] = 1.
        edge_vec = V3D(GD.world.get_relative_vector(body, Vec3(*vec_coords)))
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


class TexProjector(TopLevelObject):

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

        subobj_root = NodePath("subobj_root")
        lens_node = LensNode("tex_proj_lens")
        lens_np = subobj_root.attach_new_node(lens_node)

        edge_ends = cls.__create_body(subobj_root)
        cls.__create_lens_viz(subobj_root, edge_ends)
        cls.__create_tripod(subobj_root)

        subobj_root.set_color_scale(.1)
        subobj_root.set_bin("fixed", 50)
        subobj_root.set_depth_test(False)
        subobj_root.set_depth_write(False)
        cls._original = subobj_root

    @classmethod
    def __create_body(cls, parent):

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("tex_proj_body_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        lines = GeomLines(Geom.UH_static)
        edge_ends = []

        for corner in cls._corners:
            for coord, axis in zip(corner, "xyz"):
                pos_writer.add_data3(corner)
                coord2 = coord + (1. if coord < 0. else -1.)
                pos = Point3(*corner)
                pos["xyz".index(axis)] = coord2
                pos_writer.add_data3(pos)
                lines.add_next_vertices(2)
                edge_ends.append((corner, pos))

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("tex_proj_body")
        node.add_geom(geom)

        body = parent.attach_new_node(node)
        body.set_scale(1.2, 1.8, 1.2)
        body.set_color(.7, 1., .7)

        return edge_ends

    @classmethod
    def __create_lens_viz(cls, parent, edge_ends):

        def xform_point(point, proj_type):

            if proj_type == "orthographic":

                x, y, z = point
                y = (y + .5) * .5 + .9

            elif proj_type == "perspective":

                x, y, z = point
                y = (y + .5) * .5 + .9
                x *= y * .6666
                z *= y * .6666

            return (x, y, z)

        for proj_type in ("orthographic", "perspective"):

            vertex_format = GeomVertexFormat.get_v3c4()
            vertex_data = GeomVertexData(f"tex_proj_lens_{proj_type}_viz_data",
                                         vertex_format, Geom.UH_static)
            pos_writer = GeomVertexWriter(vertex_data, "vertex")

            lines = GeomLines(Geom.UH_static)

            for points in edge_ends:

                for point in points:
                    pos_writer.add_data3(xform_point(point, proj_type))

                lines.add_next_vertices(2)

            geom = Geom(vertex_data)
            geom.add_primitive(lines)
            node = GeomNode(f"tex_proj_lens_{proj_type}_viz")
            node.add_geom(geom)
            lens_viz = parent.attach_new_node(node)
            lens_viz.hide(Mgr.get("picking_mask"))
            lens_viz.hide()
            lens_viz.set_color(.5, .8, .5)

    @classmethod
    def __create_tripod(cls, parent):

        angle = 2. * pi / 3.
        positions = [Point3(sin(angle * i), cos(angle * i), -1.5) for i in range(3)]

        vertex_format = GeomVertexFormat.get_v3c4()
        vertex_data = GeomVertexData("tex_proj_tripod_data", vertex_format, Geom.UH_static)
        pos_writer = GeomVertexWriter(vertex_data, "vertex")

        lines = GeomLines(Geom.UH_static)

        pos_writer.add_data3(0., 0., 0.)

        for i, pos in enumerate(positions):
            pos_writer.add_data3(pos)
            lines.add_vertices(0, i + 1)

        geom = Geom(vertex_data)
        geom.add_primitive(lines)
        node = GeomNode("tex_proj_tripod")
        node.add_geom(geom)

        tripod = parent.attach_new_node(node)
        tripod.hide(Mgr.get("picking_mask"))
        tripod.set_z(-.6)
        tripod.set_color(.5, .8, .5)

    def __getstate__(self):

        state = TopLevelObject.__getstate__(self)

        state["_subobj_root"] = NodePath("subobj_root")
        state["_size"] = 1.

        return state

    def __setstate__(self, state):

        TopLevelObject.__setstate__(self, state)

        origin = self.origin
        origin.set_light_off()
        origin.set_texture_off()
        origin.set_material_off()
        origin.set_shader_off()
        self._lens_np.reparent_to(origin)
        subobj_root = self._subobj_root
        subobj_root.reparent_to(origin)
        subobj_root.set_color_scale(.1)
        subobj_root.set_bin("fixed", 50)
        subobj_root.set_depth_test(False)
        subobj_root.set_depth_write(False)
        self._body.reparent_to(subobj_root)
        self._tripod.reparent_to(subobj_root)

        for np in self._lens_viz.values():
            np.reparent_to(subobj_root)

        pickable_type_id = PickableTypes.get_id("tex_proj_edge")
        vertex_data = self._body.node().modify_geom(0).modify_vertex_data()
        col_rewriter = GeomVertexRewriter(vertex_data, "color")
        col_rewriter.set_row(0)
        r, g, b, a = col_rewriter.get_data4()

        if int(round(a * 255.)) != pickable_type_id:
            a = pickable_type_id / 255.
            col_rewriter.set_data4(r, g, b, a)
            while not col_rewriter.is_at_end():
                r, g, b, _ = col_rewriter.get_data4()
                col_rewriter.set_data4(r, g, b, a)

    def __init__(self, projector_id, name, origin_pos, on, projection_type,
                 film_w, film_h, film_x, film_y):

        prop_ids = ["on", "size", "film_w", "film_h", "film_x", "film_y",
                    "projection_type", "targets"]

        TopLevelObject.__init__(self, "tex_projector", projector_id, name, origin_pos)

        self._type_prop_ids = prop_ids
        self._is_on = on
        self._size = 0.
        self._film_w = 1.
        self._film_h = 1.
        self._film_x = 0.
        self._film_y = 0.
        self._projection_type = projection_type
        self._targets = {}

        origin = self.origin
        origin.set_light_off()
        origin.set_texture_off()
        origin.set_material_off()
        origin.set_shader_off()

        self._subobj_root = subobj_root = self.original.copy_to(origin)
        self._body = subobj_root.find("**/tex_proj_body")
        self._lens_viz = {proj_type: subobj_root.find(f"**/tex_proj_lens_{proj_type}_viz")
                          for proj_type in ("orthographic", "perspective")}
        self._lens_viz[projection_type].show()
        self._tripod = subobj_root.find("**/tex_proj_tripod")

        self._lenses = {"orthographic": OrthographicLens(),
                        "perspective": PerspectiveLens()}
        self._lens_np = lens_np = subobj_root.find("**/tex_proj_lens")
        lens_np.node().set_lens(self._lenses[projection_type])
        lens_np.reparent_to(origin)

        for lens in self._lenses.values():
            lens.film_size = 1.
            lens.focal_length = 1.5

        self.set_film_width(film_w)
        self.set_film_height(film_h)
        self.set_film_offset_x(film_x)
        self.set_film_offset_y(film_y)

        vertex_data = self._body.node().modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(0)

        self._edges = {}
        pickable_type_id = PickableTypes.get_id("tex_proj_edge")

        for i, corner in enumerate(self._corners):
            for axis in "xyz":
                edge = Mgr.do("create_tex_proj_edge", self, axis, i)
                color_id = edge.picking_color_id
                picking_color = get_color_vec(color_id, pickable_type_id)
                col_writer.set_data4(picking_color)
                col_writer.set_data4(picking_color)
                self._edges[color_id] = edge

    def __del__(self):

        Notifiers.obj.info('TexProjector garbage-collected.')

    def destroy(self, unregister=True, add_to_hist=True):

        if not TopLevelObject.destroy(self, unregister, add_to_hist):
            return

        if self.is_selected():

            for target_id, target_data in self._targets.items():

                model = Mgr.get("model", target_id)

                if model:

                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    geom_obj = model.geom_obj

                    if geom_obj:
                        target = geom_obj.geom_data_obj
                        target.project_uvs(uv_set_ids, False, toplvl=toplvl)

        self.unregister(unregister)
        self._edges = {}

        for np in self._lens_viz.values():
            np.remove_node()

        self._lens_viz = {}
        self._lens_np.remove_node()
        self._lens_np = None
        self._subobj_root.remove_node()
        self._subobj_root = None
        self._body = None
        self._tripod = None

    def register(self, restore=True):

        TopLevelObject.register(self)

        obj_type = "tex_proj_edge"
        Mgr.do(f"register_{obj_type}_objs", iter(self._edges.values()), restore)

        if restore:
            Mgr.notify("pickable_geom_altered", self)

    def unregister(self, unregister=True):

        if unregister:
            obj_type = "tex_proj_edge"
            Mgr.do(f"unregister_{obj_type}_objs", iter(self._edges.values()))

        Mgr.do("unregister_texproj_targets", iter(self._targets.keys()))

    @property
    def corners(self):

        if not self._corners:
            TexProjector.__define_corners()

        return self._corners

    @property
    def original(self):

        if not self._original:
            TexProjector.__create_original()

        return self._original

    def get_subobject_root(self):

        return self._subobj_root

    def get_body(self):

        return self._body

    def get_corner_pos(self, corner_index):

        corner_pos = Point3(self.corners[corner_index])

        return GD.world.get_relative_point(self._body, corner_pos)

    def get_center_pos(self, ref_node):

        return self.origin.get_pos(ref_node)

    def set_on(self, on):

        if self._is_on == on:
            return False

        self._is_on = on

        if not self.is_selected():
            return True

        if on:

            for target_id, target_data in self._targets.items():

                model = Mgr.get("model", target_id)

                if model:
                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    show_poly_sel = target_data["show_poly_sel"]
                    target = model.geom_obj.geom_data_obj
                    target.project_uvs(uv_set_ids, projector=self._lens_np, toplvl=toplvl,
                                       show_poly_sel=show_poly_sel)

        else:

            for target_id, target_data in self._targets.items():

                model = Mgr.get("model", target_id)

                if model:
                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    target = model.geom_obj.geom_data_obj
                    target.project_uvs(uv_set_ids, False, toplvl=toplvl)

        return True

    def is_on(self):

        return self._is_on

    def set_size(self, size):

        if self._size == size:
            return False

        self._size = size
        self._subobj_root.set_scale(size)

        return True

    def get_size(self):

        return self._size

    def set_film_width(self, film_w):

        if self._film_w == film_w:
            return False

        self._film_w = film_w

        for lens in self._lenses.values():
            lens.film_size = (film_w, self._film_h)

        return True

    def get_film_width(self):

        return self._film_w

    def set_film_height(self, film_h):

        if self._film_h == film_h:
            return False

        self._film_h = film_h

        for lens in self._lenses.values():
            lens.film_size = (self._film_w, film_h)

        return True

    def get_film_height(self):

        return self._film_h

    def set_film_offset_x(self, film_x):

        if self._film_x == film_x:
            return False

        self._film_x = film_x

        for lens in self._lenses.values():
            lens.film_offset = (film_x, self._film_y)

        return True

    def get_film_offset_x(self):

        return self._film_x

    def set_film_offset_y(self, film_y):

        if self._film_y == film_y:
            return False

        self._film_y = film_y

        for lens in self._lenses.values():
            lens.film_offset = (self._film_x, film_y)

        return True

    def get_film_offset_y(self):

        return self._film_y

    def set_projection_type(self, projection_type):

        if self._projection_type == projection_type:
            return False

        self._lens_viz[self._projection_type].hide()
        self._lens_viz[projection_type].show()
        self._lens_np.node().set_lens(self._lenses[projection_type])
        self._projection_type = projection_type

        return True

    def get_projection_type(self):

        return self._projection_type

    def set_projection_targets(self, targets, restore=""):

        old_targets = self._targets

        if targets == old_targets:
            return False

        self._targets = targets

        old_target_ids = set(old_targets.keys())
        new_target_ids = set(targets.keys())
        common_target_ids = old_target_ids & new_target_ids

        if restore:
            Mgr.do("unregister_texproj_targets", old_target_ids - new_target_ids)
            Mgr.do("register_texproj_targets", new_target_ids - old_target_ids, self.id, True)

        for target_id in old_target_ids - new_target_ids:
            Mgr.update_locally("remove_texproj_target", target_id, False)

        if self._is_on and self.is_selected():

            for target_id in old_target_ids - new_target_ids:

                model = Mgr.get("model", target_id)

                if model:
                    target_data = old_targets[target_id]
                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    target = model.geom_obj.geom_data_obj
                    target.project_uvs(uv_set_ids, False, toplvl=toplvl)

            for target_id in new_target_ids - old_target_ids:

                model = Mgr.get("model", target_id)

                if model:
                    target_data = targets[target_id]
                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    show_poly_sel = target_data["show_poly_sel"]
                    target = model.geom_obj.geom_data_obj
                    target.project_uvs(uv_set_ids, projector=self._lens_np, toplvl=toplvl,
                                       show_poly_sel=show_poly_sel)

        else:

            for target_id in common_target_ids:

                model = Mgr.get("model", target_id)

                if model:
                    target_data = old_targets[target_id]
                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    target = model.geom_obj.geom_data_obj
                    target.project_uvs(uv_set_ids, False, toplvl=toplvl)

            return True

        for target_id in common_target_ids:

            old_target_data = old_targets[target_id]
            new_target_data = targets[target_id]

            if new_target_data == old_target_data:
                continue

            model = Mgr.get("model", target_id)

            if model:

                old_uv_set_ids = set(old_target_data["uv_set_ids"])
                new_uv_set_ids = set(new_target_data["uv_set_ids"])
                old_uv_set_ids -= new_uv_set_ids
                old_uv_set_ids = tuple(sorted(old_uv_set_ids))
                new_uv_set_ids = new_target_data["uv_set_ids"]
                old_toplvl = old_target_data["toplvl"]
                new_toplvl = new_target_data["toplvl"]
                show_poly_sel = new_target_data["show_poly_sel"]
                target = model.geom_obj.geom_data_obj

                if old_uv_set_ids:
                    target.project_uvs(old_uv_set_ids, False, toplvl=old_toplvl)

                if new_toplvl != old_toplvl:
                    target.project_uvs(new_uv_set_ids, False, toplvl=old_toplvl)

                target.project_uvs(new_uv_set_ids, projector=self._lens_np, toplvl=new_toplvl,
                                   show_poly_sel=show_poly_sel)

        return True

    def set_property(self, prop_id, value, restore=""):

        def update_app():

            if self.is_selected():
                Mgr.update_remotely("selected_obj_prop", "tex_projector", prop_id,
                                    self.get_property(prop_id, True))

        def restore_on(value):

            if self.set_on(value):
                update_app()

        def restore_proj_targets(value):

            if self.set_projection_targets(value, restore):
                update_app()

        if prop_id == "on":
            if restore:
                task = lambda: restore_on(value)
                task_id = "update_texproj"
                PendingTasks.add(task, task_id, "object", id_prefix=f"on_{self.id}")
            elif self.set_on(value):
                update_app()
                return True
        elif prop_id == "size":
            if self.set_size(value):
                update_app()
                return True
        elif prop_id == "film_w":
            if self.set_film_width(value):
                update_app()
                return True
        elif prop_id == "film_h":
            if self.set_film_height(value):
                update_app()
                return True
        elif prop_id == "film_x":
            if self.set_film_offset_x(value):
                update_app()
                return True
        elif prop_id == "film_y":
            if self.set_film_offset_y(value):
                update_app()
                return True
        elif prop_id == "projection_type":
            if self.set_projection_type(value):
                update_app()
                return True
        elif prop_id == "targets":
            if restore:
                task = lambda: restore_proj_targets(value)
                task_id = "update_texproj"
                PendingTasks.add(task, task_id, "object", id_prefix=f"targets_{self.id}")
            elif self.set_projection_targets(value):
                update_app()
                return True
        else:
            return TopLevelObject.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "on":
            return self._is_on
        elif prop_id == "size":
            return self._size
        elif prop_id == "film_w":
            return self._film_w
        elif prop_id == "film_h":
            return self._film_h
        elif prop_id == "film_x":
            return self._film_x
        elif prop_id == "film_y":
            return self._film_y
        elif prop_id == "projection_type":
            return self._projection_type
        elif prop_id == "targets":
            targets = {k: v.copy() for k, v in self._targets.items()}
            if for_remote_update:
                target_names = {k: Mgr.get("model", k).name for k in targets}
                targets = (targets, target_names)
            return targets

        return TopLevelObject.get_property(self, prop_id, for_remote_update)

    def get_property_ids(self):

        return TopLevelObject.get_property_ids(self) + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids

    def add_target(self, target_id):

        uv_set_ids = (0,)
        targets = {k: v.copy() for k, v in self._targets.items()}
        targets[target_id] = {"uv_set_ids": uv_set_ids,
                              "toplvl": True, "show_poly_sel": True}

        if self._is_on:
            target = Mgr.get("model", target_id).geom_obj.geom_data_obj
            target.project_uvs(uv_set_ids, projector=self._lens_np, toplvl=True)

        Mgr.update_locally("texproj_prop", "targets", targets, self.id, True,
                           target_id, "add")

    def remove_target(self, target_id, add_to_hist=True):

        if target_id not in self._targets:
            return

        targets = {k: v.copy() for k, v in self._targets.items()}

        if self._is_on and self.is_selected():

            model = Mgr.get("model", target_id)

            if model:
                target_data = targets[target_id]
                uv_set_ids = target_data["uv_set_ids"]
                toplvl = target_data["toplvl"]
                target = model.geom_obj.geom_data_obj
                target.project_uvs(uv_set_ids, False, toplvl=toplvl)

        del targets[target_id]
        Mgr.update_locally("texproj_prop", "targets", targets, self.id,
                           add_to_hist, target_id, "remove")

    def apply_uvs(self):

        if not (self._is_on and self._targets):
            return

        obj_root = Mgr.get("object_root")
        screen = ProjectionScreen()
        screen_np = GD.world.attach_new_node(screen)
        screen.set_projector(self._lens_np)
        uv_set_ids = set()
        geoms = {}
        targets = self._targets

        for target_id, target_data in targets.items():
            uv_set_ids.update(target_data["uv_set_ids"])
            target = Mgr.get("model", target_id).geom_obj.geom_data_obj
            origin = target.origin
            geom = target.toplevel_geom.copy_to(origin)
            geom.wrt_reparent_to(screen_np)
            geoms[target_id] = geom

        for uv_set_id in uv_set_ids:

            if uv_set_id:
                screen.set_texcoord_name(str(uv_set_id))

            screen.recompute()

        for target_id, target_data in targets.items():
            geom = geoms[target_id]
            vertex_data = geom.node().get_geom(0).get_vertex_data()
            uv_set_ids = target_data["uv_set_ids"]
            toplvl = target_data["toplvl"]
            target = Mgr.get("model", target_id).geom_obj.geom_data_obj
            target.project_uvs(uv_set_ids, False, toplvl=toplvl)
            target.apply_uv_projection(vertex_data, uv_set_ids, toplvl)

        screen_np.remove_node()

        # Add to history

        Mgr.do("update_history_time")
        names = []
        obj_data = {}

        for target_id in targets:
            obj = Mgr.get("model", target_id)
            names.append(obj.name)
            target = obj.geom_obj.geom_data_obj
            obj_data[target_id] = target.get_data_to_store("prop_change", "uvs")

        if len(targets) > 1:
            event_descr = f'Apply projected UVs to "{self.name}" targets:\n'
            event_descr += "".join([f'\n    "{name}"' for name in names])
        else:
            event_descr = f'Apply projected UVs to "{self.name}" target:\n    "{names[0]}"'

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

        Mgr.update_locally("texproj_prop", "on", False, self.id)

    def update_selection_state(self, is_selected=True):

        TopLevelObject.update_selection_state(self, is_selected)

        if not self._subobj_root:
            return

        self._subobj_root.set_color_scale(1. if is_selected else .1)

        if not self._is_on:
            return

        if is_selected:

            for target_id, target_data in self._targets.items():

                model = Mgr.get("model", target_id)

                if model:
                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    show_poly_sel = target_data["show_poly_sel"]
                    target = model.geom_obj.geom_data_obj
                    target.project_uvs(uv_set_ids, projector=self._lens_np, toplvl=toplvl,
                                       show_poly_sel=show_poly_sel)

        else:

            for target_id, target_data in self._targets.items():

                model = Mgr.get("model", target_id)

                if model:
                    uv_set_ids = target_data["uv_set_ids"]
                    toplvl = target_data["toplvl"]
                    target = model.geom_obj.geom_data_obj
                    target.project_uvs(uv_set_ids, False, toplvl=toplvl)

    def show(self, *args, **kwargs):

        self.origin.show(*args, **kwargs)

    def hide(self, *args, **kwargs):

        self.origin.hide(*args, **kwargs)

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this projector.

        """

        is_selected = self.is_selected()
        data = {"flash_count": 0, "state": ["selected", "unselected"]}

        def do_flash(task):

            state = data["state"][0 if is_selected else 1]
            self._subobj_root.set_color_scale(.1 if state == "selected" else 1.)
            data["state"].reverse()
            data["flash_count"] += 1

            return task.again if data["flash_count"] < 4 else None

        Mgr.add_task(.2, do_flash, "do_flash")

    def make_pickable(self, mask_index=0, pickable=True, show_through=True):

        mask = Mgr.get("picking_mask", mask_index)
        body = self._body

        if pickable:
            body.show_through(mask) if show_through else body.show(mask)
        else:
            body.hide(mask)


class TexProjectorEdgeManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "tex_proj_edge", self.__create_proj_edge, "sub",
                               pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("tex_proj_edge")

    def __create_proj_edge(self, projector, axis, corner_index):

        picking_col_id = self.get_next_picking_color_id()
        proj_edge = TexProjectorEdge(projector, axis, corner_index, picking_col_id)

        return proj_edge


class TexProjectorManager(ObjectManager, CreationPhaseManager, ObjPropDefaultsManager):

    def __init__(self):

        ObjectManager.__init__(self, "tex_projector", self.__create_tex_projector)
        CreationPhaseManager.__init__(self, "tex_projector")
        ObjPropDefaultsManager.__init__(self, "tex_projector")

        self.set_property_default("on", True)
        self.set_property_default("size", 1.)
        self.set_property_default("film_w", 1.)
        self.set_property_default("film_h", 1.)
        self.set_property_default("film_x", 0.)
        self.set_property_default("film_y", 0.)
        self.set_property_default("projection_type", "orthographic")

        self._draw_plane = None

        self._pixel_under_mouse = None
        self._target_to_projector_ids = {}

        Mgr.accept("register_texproj_targets", self.__register_projection_targets)
        Mgr.accept("unregister_texproj_targets", self.__unregister_projection_targets)
        Mgr.add_app_updater("texproj_prop", self.__set_projector_property,
                            kwargs=["target_id", "target_prop"])
        Mgr.add_app_updater("uv_projection", self.__apply_uvs)
        Mgr.add_app_updater("remove_texproj_target", self.__remove_projection_target)
        Mgr.add_app_updater("object_removal", self.__remove_projection_target)

    def setup(self):

        creation_phases = []
        creation_phase = (self.__start_creation_phase1, self.__creation_phase1)
        creation_phases.append(creation_phase)

        status_text = {}
        status_text["obj_type"] = "texture projector"
        status_text["phase1"] = "draw out the projector"

        CreationPhaseManager.setup(self, creation_phases, status_text)

        add_state = Mgr.add_state
        add_state("texprojtarget_picking_mode", -10,
                  self.__enter_picking_mode, self.__exit_picking_mode)

        bind = Mgr.bind_state
        bind("texprojtarget_picking_mode", "pick texproj target -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("texprojtarget_picking_mode", "pick texproj target", "mouse1", self.__pick)
        bind("texprojtarget_picking_mode", "exit texproj target picking", "escape",
             lambda: Mgr.exit_state("texprojtarget_picking_mode"))
        bind("texprojtarget_picking_mode", "cancel texproj target picking", "mouse3",
             lambda: Mgr.exit_state("texprojtarget_picking_mode"))
        mod_ctrl = GD["mod_key_codes"]["ctrl"]
        bind("texprojtarget_picking_mode", "texproj ctrl-right-click", f"{mod_ctrl}|mouse3",
             lambda: Mgr.update_remotely("main_context"))

        status_data = GD["status"]
        mode_text = "Pick projector target"
        info_text = "LMB to pick object; RMB to end"
        status_data["pick_texproj_target"] = {"mode": mode_text, "info": info_text}

        return True

    def __enter_picking_mode(self, prev_state_id, active):

        Mgr.add_task(self.__update_cursor, "update_tpt_picking_cursor")
        Mgr.update_app("status", ["pick_texproj_target"])

    def __exit_picking_mode(self, next_state_id, active):

        self._pixel_under_mouse = None  # force an update of the cursor
                                        # next time self.__update_cursor()
                                        # is called
        Mgr.remove_task("update_tpt_picking_cursor")
        Mgr.set_cursor("main")

    def __pick(self):

        target = Mgr.get("object", pixel_color=self._pixel_under_mouse)

        if target and target.type == "model" and target.geom_type != "basic_geom":

            projectors = [obj for obj in Mgr.get("selection_top")
                          if obj.type == "tex_projector"]

            if len(projectors) == 1:
                projector = projectors[0]
                target_id = target.id
                projector.add_target(target_id)
                self.__register_projection_targets([target_id], projector.id)

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __apply_uvs(self):

        projectors = [obj for obj in Mgr.get("selection_top")
                      if obj.type == "tex_projector"]

        if len(projectors) == 1:
            projectors[0].apply_uvs()

    def __register_projection_targets(self, target_ids, projector_id, restore=False):

        target_to_proj_ids = self._target_to_projector_ids

        for target_id in target_ids:

            if not restore:

                if target_id in target_to_proj_ids:

                    old_projector_id = target_to_proj_ids[target_id]

                    if old_projector_id != projector_id:
                        projector = Mgr.get("tex_projector", old_projector_id)
                        projector.remove_target(target_id)

            target_to_proj_ids[target_id] = projector_id

    def __unregister_projection_targets(self, target_ids):

        target_to_proj_ids = self._target_to_projector_ids

        for target_id in target_ids:
            if target_id in target_to_proj_ids:
                del target_to_proj_ids[target_id]

    def __remove_projection_target(self, target_id, add_to_hist=True):

        target_to_proj_ids = self._target_to_projector_ids

        if target_id in target_to_proj_ids:
            projector_id = target_to_proj_ids[target_id]
            projector = Mgr.get("tex_projector", projector_id)
            projector.remove_target(target_id, add_to_hist)
            del target_to_proj_ids[target_id]

    def __create_object(self, projector_id, name, origin_pos):

        prop_defaults = self.get_property_defaults()
        projector = TexProjector(projector_id, name, origin_pos,
                                 prop_defaults["on"],
                                 prop_defaults["projection_type"],
                                 prop_defaults["film_w"],
                                 prop_defaults["film_h"],
                                 prop_defaults["film_x"],
                                 prop_defaults["film_y"])
        projector.register(restore=False)

        return projector

    def __create_tex_projector(self, origin_pos, size=None):

        projector_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        projector = self.__create_object(projector_id, name, origin_pos)
        prop_defaults = self.get_property_defaults()
        projector.set_size(prop_defaults["size"] if size is None else size)
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(projector)

        yield False

    def __start_creation_phase1(self):
        """ start drawing out texture projector """

        origin_pos = self.get_origin_pos()
        projection_type = self.get_property_defaults()["projection_type"]
        tmp_projector = TemporaryTexProjector(origin_pos, projection_type)
        self.init_object(tmp_projector)

        # Create the plane parallel to the camera and going through the projector
        # origin, used to determine the size drawn by the user.

        normal = GD.world.get_relative_vector(GD.cam(), Vec3.forward())
        point = GD.world.get_relative_point(Mgr.get("grid").origin, origin_pos)
        self._draw_plane = Plane(normal, point)

    def __creation_phase1(self):
        """ Draw out texture projector """

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

        start_point = GD.world.get_relative_point(grid_origin, self.get_origin_pos())
        size = (end_point - start_point).length()

        if snap_on and snap_tgt_type == "increment":
            offset_incr = snap_settings["increment"]["creation_phase_1"]
            size = round(size / offset_incr) * offset_incr

        self.get_object().set_size(size)

    def __set_projector_property(self, prop_id, value, projector_id=None,
                                 add_to_hist=True, target_id=None, target_prop=""):

        if projector_id:
            objs = [Mgr.get("tex_projector", projector_id)]
        else:
            objs = Mgr.get("selection")

        if not objs:
            return

        changed_objs = [obj for obj in objs if obj.set_property(prop_id, value)]

        if not changed_objs:
            return

        if not add_to_hist:
            return

        Mgr.do("update_history_time")

        obj_data = {}

        for obj in changed_objs:
            obj_data[obj.id] = obj.get_data_to_store("prop_change", prop_id)

        if prop_id == "on":

            if len(changed_objs) == 1:
                obj = changed_objs[0]
                event_descr = f'Turn {"on" if value else "off"} "{obj.name}"'
            else:
                event_descr = f'Turn {"on" if value else "off"} texture projectors:\n'
                event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])

        elif prop_id == "targets":

            model = Mgr.get("model", target_id)
            target_name = model.name if model else ""

            if target_id in value:
                target_data = value[target_id]

            if target_prop == "add":
                event_descr = f'Add projection target to "{obj.name}":\n'
                event_descr += f'\n    "{target_name}"'
            elif target_prop == "remove":
                if target_name:
                    event_descr = f'Remove projection target from "{obj.name}":\n'
                    event_descr += f'\n    "{target_name}"'
                else:
                    event_descr = f'Remove deleted projection target from "{obj.name}"'
            elif target_prop == "clear":
                event_descr = f'Clear projection targets from "{obj.name}"'
            elif target_prop == "use_poly_sel":
                event_descr = f'Change projection property of "{obj.name}"'
                event_descr += f'\nfor target "{target_name}":\n'
                target_descr = "entire target" if target_data["toplvl"] else "selected polys only"
                event_descr += f"\n    project onto {target_descr}"
            elif target_prop == "show_poly_sel":
                event_descr = f'Change projection property of "{obj.name}"'
                event_descr += f'\nfor target "{target_name}":\n'
                show_or_hide = "show" if target_data["show_poly_sel"] else "hide"
                event_descr += f'\n    {show_or_hide} selection state of affected polys'
            elif target_prop == "uv_set_ids":
                uv_set_id_str = str(target_data["uv_set_ids"]).strip("(),")
                event_descr = f'Change projection property of "{obj.name}"'
                event_descr += f'\nfor target "{target_name}":\n'
                event_descr += f"\n    affect UV sets: {uv_set_id_str}"

        else:

            if prop_id == "projection_type":
                prop_descr = "projection type"
            elif prop_id == "film_w":
                prop_descr = "film width"
            elif prop_id == "film_h":
                prop_descr = "film height"
            elif prop_id == "film_x":
                prop_descr = "film X offset"
            elif prop_id == "film_y":
                prop_descr = "film Y offset"
            else:
                prop_descr = prop_id

            if len(changed_objs) == 1:
                obj = changed_objs[0]
                event_descr = f'Change {prop_descr} of "{obj.name}"\nto {value}'
            else:
                event_descr = f'Change {prop_descr} of texture projectors:\n'
                event_descr += "".join([f'\n    "{obj.name}"' for obj in changed_objs])
                event_descr += f'\n\nto {value}'

        event_data = {"objects": obj_data}

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)


MainObjects.add_class(TexProjectorEdgeManager)
MainObjects.add_class(TexProjectorManager)
