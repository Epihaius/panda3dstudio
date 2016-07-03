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
        model = Mgr.do("create_model", model_id, name, Point3(), (.7, .7, 1.))
        picking_col_id = self.get_next_picking_color_id()
        basic_geom = BasicGeom(model, geom, picking_col_id)
        model.set_geom_object(basic_geom)

        return basic_geom, picking_col_id


class BasicGeom(BaseObject):

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
        np.set_color(1., 1., 1., 1., 1)
        state_flat_white = np.get_state()
        attrib = RenderModeAttrib.make(RenderModeAttrib.M_wireframe)
        state_wire_white = state_flat_white.add_attrib(attrib)
        attrib = RenderModeAttrib.make(RenderModeAttrib.M_filled_wireframe, 1.,
                                       False, (1., 1., 1., 1.))
        state_filled_wire_white = state_empty.add_attrib(attrib)
        render_states = cls._render_states
        render_states["shaded"] = {}
        render_states["shaded"]["unselected"] = state_empty
        render_states["shaded"]["selected"] = state_empty
        render_states["flat"] = state_flat
        render_states["wire"] = {}
        render_states["wire"]["unselected"] = "wire_unselected"
        render_states["wire"]["selected"] = state_wire_white
        render_states["shaded+wire"] = {}
        render_states["shaded+wire"]["unselected"] = "filled_wire_unselected"
        render_states["shaded+wire"]["selected"] = state_filled_wire_white

    def __get_render_state(self, render_state_id):

        color = self._model.get_color()

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
        del state["_model"]
        del state["_picking_states"]

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

    def __init__(self, model, geom, picking_col_id):

        self._prop_ids = []
        self._type_prop_ids = []
        self._type = "basic_geom"
        self._model = model
        self._geom = geom
        self._picking_col_id = picking_col_id

        model.get_pivot().set_transform(geom.get_transform())
        geom.clear_transform()
        model_orig = model.get_origin()
        render_state = geom.get_state()
        geom.set_state(RenderState.make_empty())

        material, uv_set_names = render_state_to_material(render_state)

        src_vert_data = geom.node().get_geom(0).get_vertex_data()
        src_format = src_vert_data.get_format()
        dest_format = Mgr.get("vertex_format_poly")
        dest_vert_data = src_vert_data.convert_to(dest_format)
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
            self.get_toplevel_object().set_material(material)

        color = tuple([random.random() * .5 + .5 for i in range(3)] + [1.])
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

        obj_id = self.get_toplevel_object().get_id()
        PendingTasks.add(update_render_mode, "update_render_mode", "object", 0, obj_id)

    def destroy(self):

        self._geom.remove_node()
        self._geom = None
        Mgr.do("unregister_basic_geom", self)
        Mgr.do("clear_basic_geom_picking_color", str(self._picking_col_id))

    def get_type(self):

        return self._type

    def get_geom(self):

        return self._geom

    def set_model(self, model):

        self._model = model

    def get_model(self):

        return self._model

    def get_toplevel_object(self):

        return self._model

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

    def get_subobj_selection(self, subobj_lvl):

        return []

    def update_selection_state(self, is_selected=True):

        render_mode = GlobalData["render_mode"]

        if render_mode == "shaded":
            return

        self.update_render_mode(is_selected)

    def update_render_mode(self, is_selected):

        render_mode = GlobalData["render_mode"]
        selection_state = "selected" if is_selected else "unselected"
        render_state = self._render_states[render_mode][selection_state]

        if render_state in ("wire_unselected", "filled_wire_unselected"):
            render_state = self.__get_render_state(render_state)

        self._geom.set_state(render_state)
        self._geom.set_two_sided(GlobalData["two_sided"])

        state_id = "filled" if (is_selected or render_mode != "wire") else "wire"
        picking_state = self._picking_states[state_id]
        Mgr.do("set_basic_geom_picking_color", str(self._picking_col_id), picking_state)

    def set_two_sided(self, two_sided=True):

        self._geom.set_two_sided(two_sided)

    def register(self):

        Mgr.do("register_basic_geom", self)

    def unregister(self):

        Mgr.do("unregister_basic_geom", self)

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
