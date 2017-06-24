from ..base import *


class TemporaryPointHelper(object):

    _original_geom = None

    @classmethod
    def init(cls):

        array = GeomVertexArrayFormat()
        array.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)
        array.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)
        array.add_column(InternalName.make("size"), 1, Geom.NT_float32, Geom.C_other)
        vertex_format = GeomVertexFormat()
        vertex_format.add_array(array)
        vertex_format_point = GeomVertexFormat.register_format(vertex_format)
        vertex_data = GeomVertexData("point_data", vertex_format_point, Geom.UH_static)

        prim = GeomPoints(Geom.UH_static)
        geom = Geom(vertex_data)
        geom.add_primitive(prim)
        geom_node = GeomNode("tmp_point_helper_geom")
        geom_node.add_geom(geom)
        tmp_geom = NodePath(geom_node)
        tmp_geom.set_light_off()
        tmp_geom.set_color_off()
        tmp_geom.set_texture_off()
        tmp_geom.set_material_off()
        tmp_geom.set_shader_off()
        tmp_geom.set_transparency(TransparencyAttrib.M_none)
        tmp_geom.hide(Mgr.get("picking_masks")["all"])
        cls._original_geom = tmp_geom

    def __init__(self, pos, color, size, on_top):

        self._size = size
        object_root = Mgr.get("object_root")
        self._temp_geom = tmp_geom = self._original_geom.copy_to(object_root)

        active_grid_plane = Mgr.get(("grid", "plane"))
        grid_origin = Mgr.get(("grid", "origin"))

        if active_grid_plane == "xz":
            tmp_geom.set_pos_hpr(grid_origin, pos, VBase3(0., -90., 0.))
        elif active_grid_plane == "yz":
            tmp_geom.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 90.))
        else:
            tmp_geom.set_pos_hpr(grid_origin, pos, VBase3(0., 0., 0.))

        geom = tmp_geom.node().modify_geom(0)
        vertex_data = geom.modify_vertex_data()
        pos_writer = GeomVertexWriter(vertex_data, "vertex")
        pos_writer.add_data3f(0., 0., 0.)
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.add_data4f(color)
        size_writer = GeomVertexWriter(vertex_data, "size")
        size_writer.add_data1f(size)
        prim = geom.modify_primitive(0)
        prim.add_vertex(0)

        if on_top:
            tmp_geom.set_bin("fixed", 51)
            tmp_geom.set_depth_test(False)
            tmp_geom.set_depth_write(False)

    def __del__(self):

        logging.debug('TemporaryPointHelper garbage-collected.')

    def destroy(self):

        self._temp_geom.remove_node()
        self._temp_geom = None

    def is_valid(self):

        return self._size >= 1

    def finalize(self):

        pos = self._temp_geom.get_pos(Mgr.get(("grid", "origin")))

        for step in Mgr.do("create_point_helper", pos):
            pass

        self.destroy()


class PointHelperViz(BaseObject):

    def __init__(self, point_helper, picking_col_id):

        self._point_helper = point_helper
        self._picking_col_id = picking_col_id

    def __del__(self):

        logging.debug('PointHelperViz garbage-collected.')

    def get_toplevel_object(self, get_group=False):

        return self._point_helper.get_toplevel_object(get_group)

    def get_picking_color_id(self):

        return self._picking_col_id

    def get_point_at_screen_pos(self, screen_pos):

        cam = self.cam()
        normal = self.world.get_relative_vector(cam, Vec3.forward())
        plane = Plane(normal, self._point_helper.get_origin().get_pos(self.world))

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)

        intersection_point = Point3()
        plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point))

        return intersection_point


class PointHelper(TopLevelObject):

    def __init__(self, point_id, name, origin_pos, on_top):

        TopLevelObject.__init__(self, "point_helper", point_id, name, origin_pos)

        self._type_prop_ids = ["size", "on_top", "unselected_color", "selected_color"]
        self._size = 0
        self._drawn_on_top = on_top
        self._colors = {"unselected": None, "selected": None}
        self._viz = Mgr.do("create_point_helper_viz", self)

    def __del__(self):

        logging.info('PointHelper garbage-collected.')

    def destroy(self, unregister=True, add_to_hist=True):

        if not TopLevelObject.destroy(self, unregister, add_to_hist):
            return

        self.unregister(unregister)
        self._viz = None

    def register(self, restore=True):

        TopLevelObject.register(self)

        obj_type = "point_helper_viz"
        Mgr.do("register_%s" % obj_type, self._viz, restore)

        if restore:
            Mgr.do("add_point_helper", self)

    def unregister(self, unregister=True):

        if unregister:
            obj_type = "point_helper_viz"
            Mgr.do("unregister_%s" % obj_type, self._viz)

        Mgr.do("remove_point_helper", self)

    def get_viz(self):

        return self._viz

    def get_center_pos(self, ref_node):

        return self.get_origin().get_pos(ref_node)

    def set_size(self, size):

        if self._size == size:
            return False

        self._size = size
        Mgr.do("set_point_helper_size", self, size)

        return True

    def get_size(self):

        return self._size

    def draw_on_top(self, on_top):

        if self._drawn_on_top == on_top:
            return False

        self._drawn_on_top = on_top
        Mgr.do("set_point_helper_on_top", self)

        return True

    def is_drawn_on_top(self):

        return self._drawn_on_top

    def set_color(self, selection_state, color):

        if self._colors[selection_state] == color:
            return False

        self._colors[selection_state] = color
        Mgr.do("set_point_helper_color", self)

        return True

    def get_color(self, selection_state):

        return self._colors[selection_state]

    def update_pos(self):

        task = lambda: Mgr.do("set_point_helper_pos", self)
        task_id = "transform_point_helper"
        sort = PendingTasks.get_sort("origin_transform", "object") + 1
        PendingTasks.add(task, task_id, "object", sort, id_prefix=self.get_id())

    def set_property(self, prop_id, value, restore=""):

        if prop_id in ("transform", "origin_transform"):
            task = lambda: Mgr.do("set_point_helper_pos", self)
            task_id = "transform_point_helper"
            sort = PendingTasks.get_sort("origin_transform", "object") + 1
            PendingTasks.add(task, task_id, "object", sort, id_prefix=self.get_id())

        def update_app():

            Mgr.update_remotely("selected_obj_prop", "point_helper", prop_id,
                                self.get_property(prop_id, True))

        if prop_id == "size":
            if self.set_size(value):
                update_app()
                return True
        elif prop_id == "on_top":
            if self.draw_on_top(value):
                update_app()
                return True
        elif prop_id == "unselected_color":
            if self.set_color("unselected", value):
                update_app()
                return True
        elif prop_id == "selected_color":
            if self.set_color("selected", value):
                update_app()
                return True
        else:
            return TopLevelObject.set_property(self, prop_id, value, restore)

    def get_property(self, prop_id, for_remote_update=False):

        if prop_id == "size":
            return self._size
        elif prop_id == "on_top":
            return self._drawn_on_top
        elif prop_id == "unselected_color":
            return self._colors["unselected"]
        elif prop_id == "selected_color":
            return self._colors["selected"]

        return TopLevelObject.get_property(self, prop_id, for_remote_update)

    def get_property_ids(self):

        return TopLevelObject.get_property_ids(self) + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids

    def update_selection_state(self, is_selected=True):

        TopLevelObject.update_selection_state(self, is_selected)
        Mgr.do("set_point_helper_sel_state", self, is_selected)

    def display_link_effect(self):
        """
        Visually indicate that another object has been successfully reparented
        to this point helper.

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


class PointHelperVizManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "point_helper_viz", self.__create_point_helper_viz,
                               "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("point_helper_viz")

        self._geoms = {"pickable": None, "viz": None}

    def __create_point_helper_viz(self, point_helper):

        picking_col_id = self.get_next_picking_color_id()
        point_helper_viz = PointHelperViz(point_helper, picking_col_id)

        return point_helper_viz


class PointHelperManager(ObjectManager, CreationPhaseManager, ObjPropDefaultsManager):

    def __init__(self):

        ObjectManager.__init__(self, "point_helper", self.__create_point_helper)
        CreationPhaseManager.__init__(self, "point_helper")
        ObjPropDefaultsManager.__init__(self, "point_helper")

        self.set_property_default("size", 10)
        self.set_property_default("on_top", True)
        self.set_property_default("unselected_color", (.7, .5, 1., 1.))
        self.set_property_default("selected_color", (1., 1., 1., 1.))

        self._geoms = {}
        self._point_helpers = {"normal": [], "on_top": []}
        self._point_helpers_to_transf = {"normal": [], "on_top": []}
        self._transf_start_arrays = {"normal": None, "on_top": None}

        Mgr.accept("create_custom_point_helper", self.__create_custom_point_helper)
        Mgr.accept("add_point_helper", self.__add_point_helper)
        Mgr.accept("remove_point_helper", self.__remove_point_helper)
        Mgr.accept("set_point_helper_sel_state", self.__set_point_helper_sel_state)
        Mgr.accept("set_point_helper_size", self.__set_point_helper_size)
        Mgr.accept("set_point_helper_color", self.__set_point_helper_color)
        Mgr.accept("set_point_helper_on_top", self.__set_point_helper_on_top)
        Mgr.accept("init_point_helper_transform", self.__init_point_helper_transform)
        Mgr.accept("transform_point_helpers", self.__transform_point_helpers)
        Mgr.accept("finalize_point_helper_transform", self.__finalize_point_helper_transform)
        Mgr.accept("set_point_helper_pos", self.__set_point_helper_pos)

    def setup(self):

        render_masks = Mgr.get("render_masks")["all"]
        picking_masks = Mgr.get("picking_masks")["all"]

        array1 = GeomVertexArrayFormat()
        array1.add_column(InternalName.make("vertex"), 3, Geom.NT_float32, Geom.C_point)

        array2 = GeomVertexArrayFormat()
        array2.add_column(InternalName.make("size"), 1, Geom.NT_float32, Geom.C_other)
        array2.add_column(InternalName.make("color"), 4, Geom.NT_float32, Geom.C_color)

        vertex_format = GeomVertexFormat()
        vertex_format.add_array(array1)
        vertex_format.add_array(array2)
        vertex_format_points = GeomVertexFormat.register_format(vertex_format)
        vertex_data = GeomVertexData("point_data", vertex_format_points, Geom.UH_dynamic)

        prim = GeomPoints(Geom.UH_static)
        geom = Geom(vertex_data)
        geom.add_primitive(prim)
        geom_node = GeomNode("point_helper_geom")
        geom_node.add_geom(geom)
        geom_node.set_bounds(OmniBoundingVolume())
        geom_node.set_final(True)

        object_root = Mgr.get("object_root")
        pickable_geom = object_root.attach_new_node(geom_node)
        pickable_geom.set_light_off()
        pickable_geom.set_color_off()
        pickable_geom.set_texture_off()
        pickable_geom.set_material_off()
        pickable_geom.set_shader_off()
        pickable_geom.set_transparency(TransparencyAttrib.M_none)
        pickable_geom.show(picking_masks)
        pickable_geom.hide(render_masks)
        viz_geom = pickable_geom.copy_to(object_root)
        viz_geom.show(render_masks)
        viz_geom.hide(picking_masks)
        geoms_normal = {"pickable": pickable_geom, "viz": viz_geom}
        pickable_geom = pickable_geom.copy_to(object_root)
        pickable_geom.set_bin("fixed", 51)
        pickable_geom.set_depth_test(False)
        pickable_geom.set_depth_write(False)
        viz_geom = pickable_geom.copy_to(object_root)
        viz_geom.show(render_masks)
        viz_geom.hide(picking_masks)
        geoms_on_top = {"pickable": pickable_geom, "viz": viz_geom}
        self._geoms = {"normal": geoms_normal, "on_top": geoms_on_top}

        creation_phases = [(self.__start_creation_phase, lambda: None)]

        status_text = {}
        status_text["obj_type"] = "point helper"
        status_text["phase1"] = "create the point helper"

        CreationPhaseManager.setup(self, creation_phases, status_text)
        TemporaryPointHelper.init()

        return True

    def __create_object(self, name, origin_pos):

        point_id = self.generate_object_id()
        prop_defaults = self.get_property_defaults()
        size = prop_defaults["size"]
        sizes = {"pickable": size * .5, "viz": size}
        unselected_color = prop_defaults["unselected_color"]
        selected_color = prop_defaults["selected_color"]
        on_top = prop_defaults["on_top"]
        draw_mode = "on_top" if on_top else "normal"
        point_helper = PointHelper(point_id, name, origin_pos, on_top)
        point_helper.set_size(size)
        point_helper.set_color("unselected", unselected_color)
        point_helper.set_color("selected", selected_color)
        point_helpers = self._point_helpers[draw_mode]
        count = len(point_helpers)
        point_helpers.append(point_helper)
        picking_col_id = point_helper.get_viz().get_picking_color_id()
        pickable_type_id = PickableTypes.get_id("point_helper_viz")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        colors = {"pickable": picking_color, "viz": unselected_color}
        geoms = self._geoms[draw_mode]
        pos = point_helper.get_origin().get_pos(self.world)

        for geom_type in ("pickable", "viz"):
            geom_node = geoms[geom_type].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()
            vertex_data.set_num_rows(count + 1)
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(count)
            pos_writer.add_data3f(pos)
            col_writer = GeomVertexWriter(vertex_data, "color")
            col_writer.set_row(count)
            col_writer.add_data4f(colors[geom_type])
            size_writer = GeomVertexWriter(vertex_data, "size")
            size_writer.set_row(count)
            size_writer.add_data1f(sizes[geom_type])
            prim = geom_node.modify_geom(0).modify_primitive(0)
            prim.clear_vertices()
            prim.reserve_num_vertices(count + 1)
            prim.add_next_vertices(count + 1)

        point_helper.register(restore=False)

        return point_helper

    def __create_point_helper(self, origin_pos):

        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        point_helper = self.__create_object(name, origin_pos)
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        # make undo/redoable
        self.add_history(point_helper)

        yield False

    def __create_custom_point_helper(self, name, size, on_top, colors, transform=None):

        point_helper = self.__create_object(name, Point3())
        point_helper.set_size(size)
        point_helper.draw_on_top(on_top)

        for selection_state in ("unselected", "selected"):
            point_helper.set_color(selection_state, colors[selection_state])

        if transform:
            point_helper.get_pivot().set_transform(transform)
            self.__set_point_helper_pos(point_helper)

        return point_helper

    def __start_creation_phase(self):

        origin_pos = self.get_origin_pos()
        prop_defaults = self.get_property_defaults()
        color = prop_defaults["unselected_color"]
        size = prop_defaults["size"]
        on_top = prop_defaults["on_top"]
        tmp_point_helper = TemporaryPointHelper(origin_pos, color, size, on_top)
        self.init_object(tmp_point_helper)

    def __rebuild_geoms(self):

        for draw_mode in ("normal", "on_top"):

            geoms = self._geoms[draw_mode]
            count = len(self._point_helpers[draw_mode])

            for geom_type in ("pickable", "viz"):

                geom_node = geoms[geom_type].node()
                prim = geom_node.modify_geom(0).modify_primitive(0)
                prim.clear_vertices()

                if count:
                    prim.reserve_num_vertices(count)
                    prim.add_next_vertices(count)

    def __init_point_helper_transform(self):

        helpers_to_transf = self._point_helpers_to_transf
        point_helpers = self._point_helpers
        selection = Mgr.get("selection_top")
        objs = set(selection)

        for obj in selection:
            objs.update(obj.get_descendants())

        for obj in objs:
            if obj.get_type() == "point_helper":
                draw_mode = "on_top" if obj.is_drawn_on_top() else "normal"
                helpers_to_transf[draw_mode].append(obj)

        for draw_mode in ("normal", "on_top"):
            if helpers_to_transf[draw_mode]:
                geom_node = self._geoms[draw_mode]["pickable"].node()
                pos_array = geom_node.get_geom(0).get_vertex_data().get_array(0)
                self._transf_start_arrays[draw_mode] = GeomVertexArrayData(pos_array)

    def __transform_point_helpers(self):

        for draw_mode in ("normal", "on_top"):

            helpers_to_transf = self._point_helpers_to_transf[draw_mode]

            if not helpers_to_transf:
                continue

            geoms = self._geoms[draw_mode]
            geom_node = geoms["pickable"].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            point_helpers = self._point_helpers[draw_mode]

            for point_helper in helpers_to_transf:
                row_index = point_helpers.index(point_helper)
                pos_writer.set_row(row_index)
                pos_writer.set_data3f(point_helper.get_origin().get_pos(self.world))

            pos_array = geom_node.get_geom(0).get_vertex_data().get_array(0)
            geom_node = geoms["viz"].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()
            vertex_data.set_array(0, pos_array)

    def __finalize_point_helper_transform(self, cancelled=False):

        for draw_mode in ("normal", "on_top"):

            helpers_to_transf = self._point_helpers_to_transf[draw_mode]

            if not helpers_to_transf:
                continue

            if cancelled:

                geoms = self._geoms[draw_mode]
                pos_array = self._transf_start_arrays[draw_mode]

                for geom_type in ("pickable", "viz"):
                    geom_node = geoms[geom_type].node()
                    vertex_data = geom_node.modify_geom(0).modify_vertex_data()
                    vertex_data.set_array(0, pos_array)

            self._point_helpers_to_transf[draw_mode] = []
            self._transf_start_arrays[draw_mode] = None

    def __set_point_helper_pos(self, point_helper):

        draw_mode = "on_top" if point_helper.is_drawn_on_top() else "normal"
        geoms = self._geoms[draw_mode]
        row_index = self._point_helpers[draw_mode].index(point_helper)
        pos = point_helper.get_origin().get_pos(self.world)

        for geom_type in ("pickable", "viz"):
            geom_node = geoms[geom_type].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(row_index)
            pos_writer.set_data3f(pos)

    def __add_point_helper(self, point_helper):

        draw_mode = "on_top" if point_helper.is_drawn_on_top() else "normal"
        geoms = self._geoms[draw_mode]
        point_helpers = self._point_helpers[draw_mode]
        count = len(point_helpers)
        point_helpers.append(point_helper)
        pos = point_helper.get_origin().get_pos(self.world)
        picking_col_id = point_helper.get_viz().get_picking_color_id()
        pickable_type_id = PickableTypes.get_id("point_helper_viz")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        unselected_color = point_helper.get_color("unselected")
        colors = {"pickable": picking_color, "viz": unselected_color}
        size = point_helper.get_size()
        sizes = {"pickable": size * .5, "viz": size}

        for geom_type in ("pickable", "viz"):
            geom_node = geoms[geom_type].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(count)
            pos_writer.add_data3f(pos)
            col_writer = GeomVertexWriter(vertex_data, "color")
            col_writer.set_row(count)
            col_writer.add_data4f(colors[geom_type])
            size_writer = GeomVertexWriter(vertex_data, "size")
            size_writer.set_row(count)
            size_writer.add_data1f(sizes[geom_type])

        task = self.__rebuild_geoms
        task_id = "rebuild_point_geoms"
        sort = PendingTasks.get_sort("update_selection", "object") - 1
        PendingTasks.add(task, task_id, "object", sort)

    def __remove_point_helper(self, point_helper):

        draw_mode = "on_top" if point_helper.is_drawn_on_top() else "normal"
        geoms = self._geoms[draw_mode]
        point_helpers = self._point_helpers[draw_mode]
        row_index = point_helpers.index(point_helper)
        point_helpers.remove(point_helper)

        for geom_type in ("pickable", "viz"):

            geom_node = geoms[geom_type].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()

            for i in range(2):
                array = vertex_data.modify_array(i)
                handle = array.modify_handle()
                stride = array.get_array_format().get_stride()
                handle.set_subdata(row_index * stride, stride, "")

        task = self.__rebuild_geoms
        task_id = "rebuild_point_geoms"
        sort = PendingTasks.get_sort("update_selection", "object") - 1
        PendingTasks.add(task, task_id, "object", sort)

    def __set_point_helper_sel_state(self, point_helper, is_selected):

        draw_mode = "on_top" if point_helper.is_drawn_on_top() else "normal"
        point_helpers = self._point_helpers[draw_mode]

        if point_helper not in point_helpers:
            return

        row_index = point_helpers.index(point_helper)
        selection_state = "selected" if is_selected else "unselected"
        color = point_helper.get_color(selection_state)
        geom_node = self._geoms[draw_mode]["viz"].node()
        vertex_data = geom_node.modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(row_index)
        col_writer.add_data4f(color)

    def __set_point_helper_size(self, point_helper, size):

        draw_mode = "on_top" if point_helper.is_drawn_on_top() else "normal"
        point_helpers = self._point_helpers[draw_mode]

        if point_helper not in point_helpers:
            return

        row_index = point_helpers.index(point_helper)
        geoms = self._geoms[draw_mode]
        sizes = {"pickable": size * .5, "viz": size}

        for geom_type in ("pickable", "viz"):
            geom_node = geoms[geom_type].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()
            size_writer = GeomVertexWriter(vertex_data, "size")
            size_writer.set_row(row_index)
            size_writer.add_data1f(sizes[geom_type])

    def __set_point_helper_color(self, point_helper):

        draw_mode = "on_top" if point_helper.is_drawn_on_top() else "normal"
        point_helpers = self._point_helpers[draw_mode]

        if point_helper not in point_helpers:
            return

        row_index = point_helpers.index(point_helper)
        selection_state = "selected" if point_helper.is_selected() else "unselected"
        color = point_helper.get_color(selection_state)
        geom_node = self._geoms[draw_mode]["viz"].node()
        vertex_data = geom_node.modify_geom(0).modify_vertex_data()
        col_writer = GeomVertexWriter(vertex_data, "color")
        col_writer.set_row(row_index)
        col_writer.add_data4f(color)

    def __set_point_helper_on_top(self, point_helper):

        draw_mode = "on_top" if point_helper.is_drawn_on_top() else "normal"
        point_helpers = self._point_helpers[draw_mode]

        if point_helper in point_helpers:
            return

        other_draw_mode = "on_top" if draw_mode == "normal" else "normal"
        other_point_helpers = self._point_helpers[other_draw_mode]

        if point_helper in other_point_helpers:

            geoms = self._geoms[other_draw_mode]
            row_index = other_point_helpers.index(point_helper)
            other_point_helpers.remove(point_helper)

            for geom_type in ("pickable", "viz"):

                geom_node = geoms[geom_type].node()
                vertex_data = geom_node.modify_geom(0).modify_vertex_data()

                for i in range(2):
                    array = vertex_data.modify_array(i)
                    handle = array.modify_handle()
                    stride = array.get_array_format().get_stride()
                    handle.set_subdata(row_index * stride, stride, "")

        count = len(point_helpers)
        point_helpers.append(point_helper)
        pos = point_helper.get_origin().get_pos(self.world)
        picking_col_id = point_helper.get_viz().get_picking_color_id()
        pickable_type_id = PickableTypes.get_id("point_helper_viz")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        selection_state = "selected" if point_helper.is_selected() else "unselected"
        color = point_helper.get_color(selection_state)
        colors = {"pickable": picking_color, "viz": color}
        size = point_helper.get_size()
        sizes = {"pickable": size * .5, "viz": size}
        geoms = self._geoms[draw_mode]

        for geom_type in ("pickable", "viz"):
            geom_node = geoms[geom_type].node()
            vertex_data = geom_node.modify_geom(0).modify_vertex_data()
            pos_writer = GeomVertexWriter(vertex_data, "vertex")
            pos_writer.set_row(count)
            pos_writer.add_data3f(pos)
            col_writer = GeomVertexWriter(vertex_data, "color")
            col_writer.set_row(count)
            col_writer.add_data4f(colors[geom_type])
            size_writer = GeomVertexWriter(vertex_data, "size")
            size_writer.set_row(count)
            size_writer.add_data1f(sizes[geom_type])

        task = self.__rebuild_geoms
        task_id = "rebuild_point_geoms"
        sort = PendingTasks.get_sort("update_selection", "object") - 1
        PendingTasks.add(task, task_id, "object", sort)


MainObjects.add_class(PointHelperVizManager)
MainObjects.add_class(PointHelperManager)
