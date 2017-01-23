from ..base import *
from .material import render_state_to_material


class BasicGeomManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "basic_geom", self.__create, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("basic_geom")

        self._id_generator = id_generator()

    def setup(self):

        BasicGeom.init_render_states()

        return True

    def __create(self, geom, name):

        model_id = ("basic_geom",) + self._id_generator.next()
        model = Mgr.do("create_model", model_id, name, Point3(), (.7, .7, 1., 1.))
        picking_col_id = self.get_next_picking_color_id()
        basic_geom = BasicGeom(model, geom, picking_col_id)

        return basic_geom


class BasicGeom(BaseObject):

    _render_state_ids = {}
    _render_states = {}

    @classmethod
    def init_render_states(cls):

        state_empty = RenderState.make_empty()
        np = NodePath("render_state")
        np.set_light_off(1)
        np.set_texture_off(1)
        np.set_material_off(1)
        np.set_shader_off(1)
        state_flat = np.get_state()
        np.set_color((1., 1., 1., 1.), 1)
        state_flat_white = np.get_state()
        attrib = RenderModeAttrib.make(RenderModeAttrib.M_wireframe)
        state_wire_white = state_flat_white.add_attrib(attrib)
        attrib = RenderModeAttrib.make(RenderModeAttrib.M_filled_wireframe, 1.,
                                       False, (1., 1., 1., 1.))
        state_filled_wire_white = state_empty.add_attrib(attrib)
        render_state_ids = cls._render_state_ids
        render_state_ids["shaded"] = {}
        render_state_ids["shaded"]["unselected"] = "filled_unselected"
        render_state_ids["shaded"]["selected"] = "filled_selected"
        render_state_ids["flat"] = "flat"
        render_state_ids["wire"] = {}
        render_state_ids["wire"]["unselected"] = "wire_unselected"
        render_state_ids["wire"]["selected"] = "wire_selected"
        render_state_ids["shaded+wire"] = {}
        render_state_ids["shaded+wire"]["unselected"] = "filled_wire_unselected"
        render_state_ids["shaded+wire"]["selected"] = "filled_wire_selected"
        render_states = cls._render_states
        render_states["filled_unselected"] = state_empty
        render_states["filled_selected"] = state_empty
        render_states["flat"] = state_flat
        render_states["wire_selected"] = state_wire_white
        render_states["filled_wire_selected"] = state_filled_wire_white

    def __make_wireframe_render_state(self, render_state_id, color):

        if render_state_id == "wire_unselected":
            render_state = self._render_states["flat"]
            attrib = ColorAttrib.make_flat(color)
            render_state = render_state.add_attrib(attrib)
            attrib = RenderModeAttrib.make(RenderModeAttrib.M_wireframe)
            render_state = render_state.add_attrib(attrib)
        elif render_state_id == "filled_wire_unselected":
            render_state = RenderState.make_empty()
            attrib = RenderModeAttrib.make(RenderModeAttrib.M_filled_wireframe,
                                           1., False, color)
            render_state = render_state.add_attrib(attrib)

        return render_state

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_geom"] = geom = NodePath(self._geom.node().make_copy())
        geom.set_state(RenderState.make_empty())
        del state["_model"]
        del state["_picking_states"]
        del state["_initial_vertex_colors"]

        return state

    def __setstate__(self, state):

        self.__dict__ = state

        picking_col_id = self._picking_col_id
        pickable_type_id = PickableTypes.get_id("basic_geom")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        np = NodePath("picking_color_state")
        np.set_color(picking_color, 1)
        picking_states = {"filled": np.get_state()}
        np.set_render_mode_wireframe(1)
        np.set_render_mode_thickness(5, 1)
        picking_states["wire"] = np.get_state()
        self._picking_states = picking_states
        vertex_data = self._geom.node().get_geom(0).get_vertex_data()
        array = GeomVertexArrayData(vertex_data.get_array(2))
        self._initial_vertex_colors = array

    def __init__(self, model, geom, picking_col_id):

        self._prop_ids = []
        self._type_prop_ids = []
        self._type = "basic_geom"
        self._model = model
        self._geom = geom
        self._picking_col_id = picking_col_id
        self._is_tangent_space_initialized = False

        model.set_geom_object(self)
        model.get_pivot().set_transform(geom.get_transform())
        geom.clear_transform()
        model_orig = model.get_origin()
        render_state = geom.get_state()
        geom.set_state(RenderState.make_empty())

        material, uv_set_names = render_state_to_material(render_state)

        src_vert_data = geom.node().get_geom(0).get_vertex_data()
        src_format = src_vert_data.get_format()
        dest_format = Mgr.get("vertex_format_full")
        dest_vert_data = src_vert_data.convert_to(dest_format)
        self._initial_vertex_colors = dest_vert_data.get_array(2)
        geom.node().modify_geom(0).set_vertex_data(dest_vert_data)
        dest_vert_data = geom.node().modify_geom(0).modify_vertex_data()
        num_rows = src_vert_data.get_num_rows()

        for src_uv_set, dest_uv_set in uv_set_names.iteritems():

            uv_reader = GeomVertexReader(src_vert_data, src_uv_set)
            uv_writer = GeomVertexWriter(dest_vert_data, dest_uv_set)

            for i in xrange(num_rows):
                uv = uv_reader.get_data2f()
                uv_writer.set_data2f(uv)

        if material:
            model.set_material(material)

        color = tuple([random.random() * .4 + .5 for i in range(3)] + [1.])
        model.set_color(color, update_app=False)
        geom.reparent_to(model_orig)

        pickable_type_id = PickableTypes.get_id("basic_geom")
        picking_color = get_color_vec(picking_col_id, pickable_type_id)
        np = NodePath("picking_color_state")
        np.set_color(picking_color, 1)
        state = np.get_state()
        picking_col_id_str = str(picking_col_id)
        geom.set_tag("picking_color", picking_col_id_str)
        Mgr.do("set_basic_geom_picking_color", picking_col_id_str, state)
        picking_states = {"filled": state}
        np.set_render_mode_wireframe(1)
        np.set_render_mode_thickness(5, 1)
        state = np.get_state()
        picking_states["wire"] = state
        self._picking_states = picking_states

        def update_render_mode():

            self.update_render_mode(False)
            self.set_two_sided(GlobalData["two_sided"])

        obj_id = model.get_id()
        PendingTasks.add(update_render_mode, "update_render_mode", "object", 0, obj_id)

    def __del__(self):

        logging.debug('BasicGeom garbage-collected.')

    def destroy(self, unregister=True):

        self._geom.remove_node()
        self._geom = None

        if unregister:
            Mgr.do("unregister_basic_geom", self)

        Mgr.do("clear_basic_geom_picking_color", str(self._picking_col_id))

    def register(self, restore=True):

        Mgr.do("register_basic_geom", self, restore)

    def unregister(self):

        Mgr.do("unregister_basic_geom", self)

    def get_type(self):

        return self._type

    def get_geom(self):

        return self._geom

    def set_model(self, model):

        self._model = model

    def get_model(self):

        return self._model

    def get_toplevel_object(self, get_group=False):

        return self._model.get_toplevel_object(get_group)

    def get_picking_color_id(self):

        return self._picking_col_id

    def get_point_at_screen_pos(self, screen_pos):

        cam = self.cam()
        normal = V3D(self.world.get_relative_vector(cam, Vec3.forward()))
        point = self._geom.get_pos(self.world)
        plane = Plane(normal, point)

        near_point = Point3()
        far_point = Point3()
        self.cam.lens.extrude(screen_pos, near_point, far_point)
        rel_pt = lambda point: self.world.get_relative_point(cam, point)

        intersection_point = Point3()

        if not plane.intersects_line(intersection_point, rel_pt(near_point), rel_pt(far_point)):
            return

        return intersection_point

    def update_tangent_space(self, flip_tangent, flip_bitangent):

        vertex_data = self._geom.node().modify_geom(0).modify_vertex_data()
        vert_indices = self._geom.node().get_geom(0).get_primitive(0).get_vertex_list()

        pos_reader = GeomVertexReader(vertex_data, "vertex")
        normal_reader = GeomVertexReader(vertex_data, "normal")
        uv_reader = GeomVertexReader(vertex_data, "texcoord")
        tan_writer = GeomVertexWriter(vertex_data, "tangent")
        bitan_writer = GeomVertexWriter(vertex_data, "binormal")
        vert_handlers = (pos_reader, normal_reader, uv_reader, tan_writer, bitan_writer)

        processed_rows = []
        epsilon = 1.e-010

        for rows in (vert_indices[i:i + 3] for i in xrange(0, len(vert_indices), 3)):

            for row in rows:

                if row in processed_rows:
                    continue

                other_rows = list(rows)
                other_rows.remove(row)
                row1, row2 = other_rows

                for handler in vert_handlers:
                    handler.set_row(row)

                pos = pos_reader.get_data3f()
                normal = normal_reader.get_data3f()
                uv = uv_reader.get_data2f()

                pos_reader.set_row(row1)
                pos1 = pos_reader.get_data3f()
                pos_reader.set_row(row2)
                pos2 = pos_reader.get_data3f()
                pos_vec1 = pos1 - pos
                pos_vec2 = pos2 - pos

                uv_reader.set_row(row1)
                uv1 = uv_reader.get_data2f()
                uv_reader.set_row(row2)
                uv2 = uv_reader.get_data2f()
                uv_vec1 = uv1 - uv
                uv_vec2 = uv2 - uv

                # compute a vector pointing in the +U direction, in texture space
                # and in world space

                if abs(uv_vec1.y) < epsilon:
                    u_vec_local = uv_vec1
                    u_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.y) < epsilon:
                    u_vec_local = uv_vec2
                    u_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.y / uv_vec2.y)
                    u_vec_local = uv_vec1 - uv_vec2 * scale
                    # u_vec_local.y will be 0 and thus point in the -/+U direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space U-vector
                    u_vec_world = pos_vec1 - pos_vec2 * scale

                if u_vec_local.x < 0.:
                    u_vec_world *= -1.

                # compute a vector pointing in the +V direction, in texture space
                # and in world space

                if abs(uv_vec1.x) < epsilon:
                    v_vec_local = uv_vec1
                    v_vec_world = Vec3(pos_vec1)
                elif abs(uv_vec2.x) < epsilon:
                    v_vec_local = uv_vec2
                    v_vec_world = Vec3(pos_vec2)
                else:
                    scale = (uv_vec1.x / uv_vec2.x)
                    v_vec_local = uv_vec1 - uv_vec2 * scale
                    # v_vec_local.x will be 0 and thus point in the -/+V direction;
                    # replacing the texture-space vectors with the corresponding
                    # world-space vectors will therefore yield a world-space V-vector
                    v_vec_world = pos_vec1 - pos_vec2 * scale

                if v_vec_local.y < 0.:
                    v_vec_world *= -1.

                tangent_plane = Plane(normal, Point3())
                # the tangent vector is the world-space U-vector projected onto
                # the tangent plane
                tangent = Vec3(tangent_plane.project(Point3(u_vec_world)))

                if not tangent.normalize():
                    continue

                # the bitangent vector is the world-space V-vector projected onto
                # the tangent plane
                bitangent = Vec3(tangent_plane.project(Point3(v_vec_world)))

                if not bitangent.normalize():
                    continue

                if flip_tangent:
                    tangent *= -1.

                if flip_bitangent:
                    bitangent *= -1.

                tan_writer.set_data3f(tangent)
                bitan_writer.set_data3f(bitangent)
                processed_rows.append(row)

        self._is_tangent_space_initialized = True

    def is_tangent_space_initialized(self):

        return self._is_tangent_space_initialized

    def bake_texture(self, texture):

        vertex_data = self._geom.node().modify_geom(0).modify_vertex_data()
        geom_copy = self._geom.copy_to(self.world)
        geom_copy.detach_node()
        geom_copy.set_texture(TextureStage.get_default(), texture)
        geom_copy.flatten_light()
        geom_copy.apply_texture_colors()
        vertex_data_copy = geom_copy.node().modify_geom(0).modify_vertex_data()
        array = vertex_data_copy.modify_array(10)
        vertex_data.set_array(2, array)

    def reset_vertex_colors(self):

        vertex_data = self._geom.node().modify_geom(0).modify_vertex_data()
        array = GeomVertexArrayData(self._initial_vertex_colors)
        vertex_data.set_array(2, array)

    def get_subobj_selection(self, subobj_lvl):

        return []

    def set_wireframe_color(self, color):

        render_mode = GlobalData["render_mode"]
        state_id = self._render_state_ids[render_mode]["unselected"]

        if state_id in ("wire_unselected", "filled_wire_unselected"):
            render_state = self.__make_wireframe_render_state(state_id, color)
            self._geom.set_state(render_state)

    def update_selection_state(self, is_selected=True):

        render_mode = GlobalData["render_mode"]

        if render_mode == "shaded":
            return

        self.update_render_mode(is_selected)

    def update_render_mode(self, is_selected):

        render_mode = GlobalData["render_mode"]
        selection_state = "selected" if is_selected else "unselected"
        state_id = self._render_state_ids[render_mode][selection_state]

        if state_id in ("wire_unselected", "filled_wire_unselected"):
            color = self._model.get_color()
            render_state = self.__make_wireframe_render_state(state_id, color)
        else:
            render_state = self._render_states[state_id]

        self._geom.set_state(render_state)
        self._geom.set_two_sided(GlobalData["two_sided"])

        state_id = "filled" if (is_selected or render_mode != "wire") else "wire"
        picking_state = self._picking_states[state_id]
        Mgr.do("set_basic_geom_picking_color", str(self._picking_col_id), picking_state)

    def set_two_sided(self, two_sided=True):

        self._geom.set_two_sided(two_sided)

    def get_data_to_store(self, event_type, prop_id=""):

        data = {}

        if event_type == "creation":

            data["geom_obj"] = {"main": self}
            prop_ids = self.get_property_ids()

            for prop_id in prop_ids:
                data[prop_id] = {"main": self.get_property(prop_id)}

        elif event_type == "prop_change":

            if prop_id == "editable state":
                data["geom_obj"] = {"main": self}
            elif prop_id in self.get_property_ids():
                data[prop_id] = {"main": self.get_property(prop_id)}

        return data

    def restore_data(self, data_ids, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()

        if "self" in data_ids:

            for prop_id in self.get_property_ids():
                val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                self.set_property(prop_id, val, restore_type)

            self._geom.reparent_to(self._model.get_origin())
            self.register()
            self.update_render_mode(self._model.is_selected())
            self.set_two_sided(GlobalData["two_sided"])

        else:

            for prop_id in self.get_property_ids():
                if prop_id in data_ids:
                    val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
                    self.set_property(prop_id, val, restore_type)
                    data_ids.remove(prop_id)

    def get_property_ids(self, for_hist=False):

        return self._prop_ids + self._type_prop_ids

    def get_type_property_ids(self):

        return self._type_prop_ids


MainObjects.add_class(BasicGeomManager)
