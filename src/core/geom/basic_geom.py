from .data import *


class BasicGeomManager(ObjectManager, PickingColorIDManager):

    def __init__(self):

        ObjectManager.__init__(self, "basic_geom", self.__create, "sub", pickable=True)
        PickingColorIDManager.__init__(self)
        PickableTypes.add("basic_geom")

        self._id_generator = id_generator()

    def setup(self):

        BasicGeomObject.init_render_states()

        return True

    def __create(self, geom, name):

        model_id = ("basic_geom",) + self._id_generator.next()
        model = Mgr.do("create_model", model_id, name, Point3(), (.7, .7, 1.))
        picking_col_id = self.get_next_picking_color_id()
        basic_geom_obj = BasicGeomObject(model, geom, picking_col_id)
        model.set_geom_object(basic_geom_obj)

        return basic_geom_obj, picking_col_id


class BasicGeomObject(BaseObject):

    _render_states = {}

    @classmethod
    def init_render_states(cls):

        render_states = cls._render_states
        np = NodePath("render_state")
        render_states["default"] = np.get_state()
        np.set_light_off(1)
        np.set_texture_off(1)
        render_states["flat"] = np.get_state()
        np.set_color(1., 1., 1., 1., 1)
        render_states["flat_white"] = np.get_state()

    def __getstate__(self):

        d = self.__dict__.copy()
        del d["_model"]
        del d["_picking_states"]

        return d

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

        prop_ids = []
        self._prop_ids = prop_ids
        self._type_prop_ids = prop_ids
        self._type = "basic_geom"
        self._model = model
        self._geom = geom
        self._picking_col_id = picking_col_id

        model.get_pivot().set_transform(geom.get_transform())
        geom.clear_transform()
        model_orig = model.get_origin()
        model_orig.set_state(geom.get_state())
        color = geom.get_color() if geom.has_color() else VBase4(1., 1., 1., 1.)
        model.set_color(color, update_app=False)
        geom.set_state(RenderState.make_empty())
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

        self.update_render_mode()
        self.set_two_sided(GlobalData["two_sided"])

    def destroy(self):

        self._geom.remove_node()
        self._geom = None
        Mgr.do("unregister_basic_geom", self)
        Mgr.do("clear_basic_geom_picking_color", str(self._picking_col_id))

    def is_valid(self):

        return False

    def get_type(self):

        return self._type

    def set_geom(self, geom):

        self._geom = geom

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

    def replace(self, geom_obj):
        pass

    def get_subobj_selection(self, subobj_lvl):

        return []

    def update_selection_state(self, is_selected=True):

        render_mode = GlobalData["render_mode"]

        if render_mode == "shaded":
            return

        render_states = self._render_states
        geom = self._geom

        state_id = "filled" if (is_selected or render_mode != "wire") else "wire"
        picking_state = self._picking_states[state_id]
        Mgr.do("set_basic_geom_picking_color", str(self._picking_col_id), picking_state)

        if render_mode == "wire":
            geom.set_state(render_states["flat_white" if is_selected else "flat"])
            geom.set_render_mode_wireframe()
        else:
            color = VBase4(1., 1., 1., 1.) if is_selected else self._model.get_color()
            geom.set_render_mode_filled_wireframe(color)

    def update_render_mode(self):

        render_mode = GlobalData["render_mode"]
        render_states = self._render_states
        geom = self._geom
        is_selected = self._model.is_selected()

        state_id = "filled" if (is_selected or "shaded" in render_mode) else "wire"
        picking_state = self._picking_states[state_id]
        Mgr.do("set_basic_geom_picking_color", str(self._picking_col_id), picking_state)

        if render_mode == "shaded":
            geom.set_state(render_states["default"])
            geom.set_render_mode_filled()
        elif render_mode == "wire":
            geom.set_state(render_states["flat_white" if is_selected else "flat"])
            geom.set_render_mode_wireframe()
        else:
            geom.set_state(render_states["default"])
            color = VBase4(1., 1., 1., 1.) if is_selected else self._model.get_color()
            geom.set_render_mode_filled_wireframe(color)

    def set_two_sided(self, two_sided=True):

        self._geom.set_two_sided(two_sided)

    def register(self):

        Mgr.do("register_basic_geom", self)

        self.update_render_mode()
        self.set_two_sided(GlobalData["two_sided"])

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
