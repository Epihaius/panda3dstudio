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
        del state["has_zero_size_owner"]

        return state

    def __setstate__(self, state):

        state["origin"] = state.pop("_origin")
        self.__dict__ = state
        self.has_zero_size_owner = False
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
        self.has_zero_size_owner = False  # indicates whether owner has no visible geometry
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
        self.origin.detach_node()
        self.origin = None

        if self.has_zero_size_owner:
            Mgr.do("make_bbox_const_size", self, False)

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

    def update(self, min_max):

        if min_max:
            point_max, point_min = min_max
            vec = point_max - point_min

        if not min_max or vec.length() < .0001:
            vec = None

        if vec:
            scale_factors = [max(.0001, abs(factor)) for factor in vec]
            self.origin.set_scale(*scale_factors)
            self.origin.set_pos(point_min + vec * .5)
            if self.has_zero_size_owner:
                Mgr.do("make_bbox_const_size", self, False)
                self.origin.reparent_to(self._owner.origin)
                self.has_zero_size_owner = False
        elif self.has_zero_size_owner:
            return
        else:
            origin_backup = self.origin
            self.origin.detach_node()
            self.origin = self.origin.copy_to(self._owner.origin)
            self.origin.detach_node()
            color = (1., .5, .5, 1.) if self._owner.is_selected() else (1., 0., 0., 1.)
            self.origin.set_color(color)
            self.origin.clear_transform()
            self.origin.show()
            mat = Mat4.scale_mat(.85)
            self.origin.node().modify_geom(0).modify_vertex_data().transform_vertices(mat)
            Mgr.do("make_bbox_const_size", self)
            self.origin = origin_backup
            self.has_zero_size_owner = True

        self._owner.update_group_bbox()

    def show(self, *args):

        self.origin.show(*args)

        if self.has_zero_size_owner:
            for origin in Mgr.get("const_size_bbox_origins", self._owner.id):
                origin.set_color((1., .5, .5, 1.))

    def hide(self, *args):

        self.origin.hide(*args)

        if self.has_zero_size_owner:
            for origin in Mgr.get("const_size_bbox_origins", self._owner.id):
                origin.set_color((1., 0., 0., 1.))

    def flash(self):

        orig = self.origin
        hidden = orig.is_hidden()
        data = {"flash_count": 0, "state": ["shown", "hidden"]}

        def do_flash(task):

            state = data["state"][1 if hidden else 0]
            self.show() if state == "hidden" else self.hide()
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


class ConstSizeBBoxManager:

    def __init__(self):

        self._bbox_roots = {}
        self._bbox_bases = {}
        self._bbox_origins = {"persp": {}, "ortho": {}}
        self._compass_props = CompassEffect.P_pos | CompassEffect.P_rot
        bbox_root = GD.cam.const_size_obj_root.attach_new_node("const_size_bbox_root")
        self._bbox_root = bbox_root

        Mgr.add_app_updater("viewport", self.__handle_viewport_resize)
        Mgr.add_app_updater("region_picking", self.__make_region_pickable)
        Mgr.add_app_updater("lens_type", self.__show_root)
        Mgr.accept("make_bbox_const_size", self.__make_bbox_const_size)
        Mgr.accept("show_const_size_bboxes", self.__show_const_size_bboxes)
        Mgr.expose("const_size_bbox_origins", self.__get_const_size_bbox_origins)
        Mgr.expose("const_size_bbox_root", lambda: self._bbox_root)

        masks = Mgr.get("render_mask") | Mgr.get("picking_mask")
        root_persp = bbox_root.attach_new_node("group_bbox_root_persp")
        root_persp.show(masks)
        root_ortho = bbox_root.attach_new_node("group_bbox_root_ortho")
        root_ortho.set_scale(20.)
        root_ortho.hide(masks)
        self._bbox_roots["persp"] = root_persp
        self._bbox_roots["ortho"] = root_ortho

    def __handle_viewport_resize(self):

        w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
        scale = 800. / max(w, h) * .6
        bbox_origins = self._bbox_origins

        for owner_id in self._bbox_bases:
            for origins in bbox_origins.values():
                origins[owner_id].set_scale(scale)

    def __make_region_pickable(self, pickable):

        if pickable:
            self._bbox_root.wrt_reparent_to(Mgr.get("object_root"))
            bbox_origins = self._bbox_origins
            bbox_origins_persp = bbox_origins["persp"]
            bbox_origins_ortho = bbox_origins["ortho"]
            for owner_id in self._bbox_bases:
                owner = Mgr.get("object", owner_id)
                index = int(owner.pivot.get_shader_input("index").get_vector().x)
                bbox_origins_persp[owner_id].set_shader_input("index", index)
                bbox_origins_ortho[owner_id].set_shader_input("index", index)
        else:
            self._bbox_root.reparent_to(GD.cam())
            self._bbox_root.clear_transform()

    def __show_root(self, lens_type):

        masks = Mgr.get("render_mask") | Mgr.get("picking_mask")

        if lens_type == "persp":
            self._bbox_roots["persp"].show(masks)
            self._bbox_roots["ortho"].hide(masks)
        else:
            self._bbox_roots["persp"].hide(masks)
            self._bbox_roots["ortho"].show(masks)

    def __make_bbox_const_size(self, bbox, const_size_state=True):

        owner = bbox.toplevel_obj
        owner_id = owner.id
        owner_origin = owner.origin
        bbox_bases = self._bbox_bases
        bbox_origins = self._bbox_origins

        if const_size_state:
            if owner_id not in bbox_bases:
                bbox_roots = self._bbox_roots
                bbox_base = bbox_roots["persp"].attach_new_node("bbox_base")
                origin = bbox.origin
                bbox_base.set_billboard_point_world(owner_origin, 2000.)
                pivot = bbox_base.attach_new_node("bbox_pivot")
                pivot.set_scale(100.)
                w, h = GD["viewport"]["size_aux" if GD["viewport"][2] == "main" else "size"]
                scale = 800. / max(w, h) * .6
                origin_persp = origin.copy_to(pivot)
                origin_persp.name = "bbox_origin_persp"
                origin_persp.set_scale(scale)
                bbox_origins["persp"][owner_id] = origin_persp
                origin_ortho = origin.copy_to(bbox_roots["ortho"])
                origin_ortho.name = "bbox_origin_ortho"
                origin_ortho.set_scale(scale)
                bbox_origins["ortho"][owner_id] = origin_ortho
                origin_persp.set_compass(owner_origin)
                bbox_bases[owner_id] = bbox_base
                compass_effect = CompassEffect.make(owner_origin, self._compass_props)
                origin_ortho.set_effect(compass_effect)
        else:
            if owner_id in bbox_bases:
                origin_persp = bbox_origins["persp"][owner_id]
                origin_persp.detach_node()
                del bbox_origins["persp"][owner_id]
                origin_ortho = bbox_origins["ortho"][owner_id]
                origin_ortho.detach_node()
                del bbox_origins["ortho"][owner_id]
                bbox_base = bbox_bases[owner_id]
                bbox_base.detach_node()
                del bbox_bases[owner_id]

    def __show_const_size_bboxes(self, bbox, mask_index=0, show=True, show_through=False):

        owner = bbox.toplevel_obj
        owner_id = owner.id
        bbox_origins = self._bbox_origins

        if owner_id not in bbox_origins["persp"]:
            return

        origin_persp = bbox_origins["persp"][owner_id]
        origin_ortho = bbox_origins["ortho"][owner_id]

        mask = Mgr.get("picking_mask", mask_index)

        if show:
            if GD.cam.lens_type == "persp":
                origin_persp.show_through(mask) if show_through else origin_persp.show(mask)
                origin_ortho.hide(mask)
            else:
                origin_persp.hide(mask)
                origin_ortho.show_through(mask) if show_through else origin_ortho.show(mask)
        else:
            origin_persp.hide(mask)
            origin_ortho.hide(mask)

    def __get_const_size_bbox_origins(self, owner_id):

        if owner_id in self._bbox_bases:

            bbox_origins = self._bbox_origins
            origin_persp = bbox_origins["persp"][owner_id]
            origin_ortho = bbox_origins["ortho"][owner_id]

            return origin_persp, origin_ortho


Mgr.accept("create_bbox", lambda owner, color: BoundingBox(owner, color))
MainObjects.add_class(BBoxEdgeManager)
MainObjects.add_class(ConstSizeBBoxManager)
