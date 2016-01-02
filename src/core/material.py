from .base import *
from .base import Material as BaseMaterial


class Material(object):

    def __str__(self):

        return self._name

    def __init__(self, material_id, name, base_material=None, base_props=None,
                 tex_maps=None, layers=None, uses_layers=None):

        self._id = material_id
        self._name = name
        self._base_mat = base_material if base_material else BaseMaterial(name)
        prop_ids = ("diffuse", "ambient", "emissive",
                    "specular", "shininess", "alpha")
        self._base_prop_ids = prop_ids

        if base_props:
            self._base_props = base_props
        else:
            props = dict(
                (prop_id, {"value": (0., 0., 0., 1.), "on": False}) for prop_id in prop_ids)
            props["diffuse"]["value"] = (1., 1., 1., 1.)
            props["alpha"]["value"] = 1.
            props["shininess"]["value"] = 10.
            props["shininess"]["on"] = True
            self._base_props = props
            self._base_mat.set_shininess(10.)

        self._uses_layers = False if uses_layers is None else uses_layers

        if layers:
            self._layers = layers
        else:
            self._layers = {}
            self._layers[0] = [Mgr.do("create_tex_layer", self)]

        if tex_maps:
            self._tex_maps = tex_maps
        else:
            map_types = ("color", "normal", "height", "normal+height", "gloss",
                         "color+gloss", "glow", "color+glow")
            self._tex_maps = dict((t, Mgr.do("create_tex_map", t))
                                  for t in map_types)
            self._tex_maps["color"].set_active(True)

        self._owner_ids = []
        self._selected_map_type = "color"
        self._selected_layer_id = self.get_layers()[0].get_id()

        Mgr.do("register_material", self)

    def copy(self, copy_layers=None):

        base_material = BaseMaterial(self._base_mat)
        base_props = {}

        for k, v in self._base_props.iteritems():
            base_props[k] = v.copy()

        tex_maps = {}

        for map_type, tex_map in self._tex_maps.iteritems():
            tex_maps[map_type] = tex_map.copy()

        if copy_layers is False:

            layers = None

        else:

            layers = {}

            for uv_set_id, maps in self._layers.iteritems():
                layers[uv_set_id] = [m.copy(copy_name=True) for m in maps]

        uses_layers = False if copy_layers is False else self._uses_layers
        material = Mgr.do("create_material", base_material, base_props,
                          tex_maps, layers, uses_layers)

        return material

    def get_id(self):

        return self._id

    def set_name(self, name):

        if self._name == name:
            return

        self._name = name

    def get_name(self):

        return self._name

    def __apply_base_material(self):

        # since attributes get locked when the BaseMaterial is applied to a Node, a
        # new BaseMaterial must be copied from the original one and applied
        # instead
        base_material = BaseMaterial(self._base_mat)

        for owner_id in self._owner_ids:
            owner = Mgr.get("object", owner_id)
            origin = owner.get_origin()
            origin.set_material(base_material)

    def set_property(self, prop_id, value, apply_base_mat=True):

        if prop_id == "name":

            self.set_name(value)

        elif prop_id in self._base_prop_ids:

            props = self._base_props[prop_id]
            props.update(value)
            val = props["value"]
            on = props["on"]
            bm = self._base_mat

            def set_alpha(value, on):

                attrib = TransparencyAttrib.M_alpha if on else TransparencyAttrib.M_none

                if on:
                    for owner_id in self._owner_ids:
                        owner = Mgr.get("object", owner_id)
                        origin = owner.get_origin()
                        origin.set_transparency(attrib)
                        origin.set_alpha_scale(value)
                else:
                    for owner_id in self._owner_ids:
                        owner = Mgr.get("object", owner_id)
                        origin = owner.get_origin()
                        origin.set_transparency(attrib)
                        origin.clear_color_scale()

            if prop_id == "diffuse":
                bm.set_diffuse(VBase4(*val)) if on else bm.clear_diffuse()
            elif prop_id == "ambient":
                bm.set_ambient(VBase4(*val)) if on else bm.clear_ambient()
            elif prop_id == "emissive":
                bm.set_emission(VBase4(*val)) if on else bm.clear_emission()
            elif prop_id == "specular":
                bm.set_specular(VBase4(*val)) if on else bm.clear_specular()
            elif prop_id == "shininess":
                bm.set_shininess(val)
            elif prop_id == "alpha":
                set_alpha(val, on)

            if apply_base_mat:
                self.__apply_base_material()

            return props

        elif prop_id == "layers_on":

            self.use_layers(value)

        elif prop_id == "texture":

            layer_id = value["layer_id"]
            tex_data = value["tex_data"]
            self.set_texture(tex_data, layer_id)

        elif prop_id == "tex_map_select":

            self._selected_map_type = value
            tex_map = self._tex_maps[value]
            on = tex_map.is_active()
            rgb_filename, alpha_filename = tex_map.get_tex_filenames()
            border_color = tex_map.get_border_color()
            wrap_u = tex_map.get_wrap_mode("u")
            wrap_v = tex_map.get_wrap_mode("v")
            wrap_lock = tex_map.are_wrap_modes_locked()
            filter_min = tex_map.get_filter_type("min")
            filter_mag = tex_map.get_filter_type("mag")
            degree = tex_map.get_anisotropic_degree()
            transform = tex_map.get_transform()
            mat_id = self._id
            Mgr.update_remotely("material_prop", mat_id, "tex_map_on", on)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_file_main", rgb_filename)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_file_alpha", alpha_filename)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_border_color", border_color)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_wrap_u", wrap_u)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_wrap_v", wrap_v)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_wrap_lock", wrap_lock)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_filter_min", filter_min)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_filter_mag", filter_mag)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_anisotropic_degree", degree)
            Mgr.update_remotely("material_prop", mat_id,
                                "tex_map_transform", transform)

        elif prop_id == "tex_map_on":

            self.set_map_active(self._selected_map_type, is_active=value)

        elif prop_id == "tex_map_border_color":

            tex_map = self._tex_maps[self._selected_map_type]
            tex_map.set_border_color(value)

        elif prop_id == "tex_map_wrap_u":

            tex_map = self._tex_maps[self._selected_map_type]
            tex_map.set_wrap_mode("u", value)

            if tex_map.are_wrap_modes_locked():
                Mgr.update_remotely("material_prop", self._id,
                                    "tex_map_wrap_v", value)

        elif prop_id == "tex_map_wrap_v":

            tex_map = self._tex_maps[self._selected_map_type]
            tex_map.set_wrap_mode("v", value)

            if tex_map.are_wrap_modes_locked():
                Mgr.update_remotely("material_prop", self._id,
                                    "tex_map_wrap_u", value)

        elif prop_id == "tex_map_wrap_lock":

            tex_map = self._tex_maps[self._selected_map_type]
            tex_map.lock_wrap_modes(value)

            if value:
                mode_id = tex_map.get_wrap_mode("u")
                Mgr.update_remotely("material_prop", self._id,
                                    "tex_map_wrap_v", mode_id)

        elif prop_id == "tex_map_filter_min":

            tex_map = self._tex_maps[self._selected_map_type]
            tex_map.set_filter_type("min", value)

        elif prop_id == "tex_map_filter_mag":

            tex_map = self._tex_maps[self._selected_map_type]
            tex_map.set_filter_type("mag", value)

        elif prop_id == "tex_map_anisotropic_degree":

            value = max(1, min(value, 16))
            tex_map = self._tex_maps[self._selected_map_type]
            tex_map.set_anisotropic_degree(value)

        elif prop_id == "tex_map_offset_u":

            self.set_map_transform(
                self._selected_map_type, None, "offset", 0, value)

        elif prop_id == "tex_map_offset_v":

            self.set_map_transform(
                self._selected_map_type, None, "offset", 1, value)

        elif prop_id == "tex_map_rotate":

            self.set_map_transform(
                self._selected_map_type, None, "rotate", 0, value)

        elif prop_id == "tex_map_scale_u":

            self.set_map_transform(
                self._selected_map_type, None, "scale", 0, value)

        elif prop_id == "tex_map_scale_v":

            self.set_map_transform(
                self._selected_map_type, None, "scale", 1, value)

        return value

    def is_property_equal_to(self, prop_id, value):

        if prop_id in self._base_prop_ids:
            prop_data = self._base_props[prop_id]
            on = prop_data["on"]
            val = prop_data["value"]
            state_equal = value["on"] == on
            val_equal = value["value"] == val
            return state_equal and (val_equal or not on)

    def set_base_properties(self, properties):

        for prop_id, value in properties.iteritems():
            self.set_property(prop_id, value, apply_base_mat=False)

        self.__apply_base_material()

    def get_base_properties(self):

        return self._base_props

    def get_base_material(self):

        return self._base_mat

    def get_owner_ids(self):

        return self._owner_ids

    def get_selected_map_type(self):

        return self._selected_map_type

    def get_tex_map(self, map_type):

        return self._tex_maps[map_type]

    def get_tex_maps(self):

        return self._tex_maps.iteritems()

    def use_layers(self, uses_layers=True):

        if self._uses_layers == uses_layers:
            return

        origins = [Mgr.get("object", owner_id).get_origin()
                   for owner_id in self._owner_ids]
        layers = [l for group in self._layers.itervalues()
                  for l in group if l.is_active()]
        color_map = self._tex_maps["color"]

        if color_map.is_active():
            color_tex_stage = color_map.get_tex_stage()
        else:
            color_map = None

        if uses_layers:

            if color_map:

                for origin in origins:

                    origin.clear_texture(color_tex_stage)
                    origin.clear_tex_transform(color_tex_stage)

            for layer in layers:

                texture = layer.get_texture()
                tex_stage = layer.get_tex_stage()
                t = layer.get_transform()
                tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                                  t["rotate"][
                                                                      0],
                                                                  VBase2(*t["scale"]))

                if texture:
                    for origin in origins:
                        origin.set_texture(tex_stage, texture)

                if not tr_state.is_identity():
                    for origin in origins:
                        origin.set_tex_transform(tex_stage, tr_state)

        else:

            for layer in layers:

                tex_stage = layer.get_tex_stage()

                for origin in origins:
                    origin.clear_texture(tex_stage)
                    origin.clear_tex_transform(tex_stage)

            if color_map:

                texture = color_map.get_texture()
                t = color_map.get_transform()
                tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                                  t["rotate"][
                                                                      0],
                                                                  VBase2(*t["scale"]))

                if texture:
                    for origin in origins:
                        origin.set_texture(color_tex_stage, texture)

                if not tr_state.is_identity():
                    for origin in origins:
                        origin.set_tex_transform(color_tex_stage, tr_state)

        self._uses_layers = uses_layers

    def uses_layers(self):

        return self._uses_layers

    def set_selected_layer_id(self, layer_id):

        self._selected_layer_id = layer_id

    def get_selected_layer_id(self):

        return self._selected_layer_id

    def get_layer(self, uv_set_id=0, layer_index=0):

        return self._layers[uv_set_id][layer_index]

    def get_layers(self):

        d = dict((l.get_sort(), l)
                 for group in self._layers.itervalues() for l in group)

        return [d[i] for i in sorted(d.iterkeys())]

    def add_layer(self, layer):

        count = sum([len(group) for group in self._layers.itervalues()])
        layer.set_sort(count)
        self._layers.setdefault(layer.get_uv_set_id(), []).append(layer)

        if not (self._uses_layers and layer.is_active()):
            return

        origins = [Mgr.get("object", owner_id).get_origin()
                   for owner_id in self._owner_ids]
        tex_stage = layer.get_tex_stage()
        texture = layer.get_texture()
        t = layer.get_transform()
        tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                          t["rotate"][0],
                                                          VBase2(*t["scale"]))

        if texture:
            for origin in origins:
                origin.set_texture(tex_stage, texture)

        if not tr_state.is_identity():
            for origin in origins:
                origin.set_tex_transform(tex_stage, tr_state)

    def set_layer_uv_set_id(self, layer, uv_set_id):

        old_id = layer.get_uv_set_id()

        if layer.set_uv_set_id(uv_set_id):

            group = self._layers[old_id]
            group.remove(layer)

            if not group:
                del self._layers[old_id]

            self._layers.setdefault(uv_set_id, []).append(layer)
            self.reapply_layer(layer)

    def reapply_layer(self, layer):

        if not (self._uses_layers and layer.is_active()):
            return

        tex_stage = layer.get_tex_stage()
        texture = layer.get_texture()

        if texture:
            for owner_id in self._owner_ids:
                origin = Mgr.get("object", owner_id).get_origin()
                origin.set_texture(tex_stage, texture)

    def remove_layer(self, layer):

        uv_set_id = layer.get_uv_set_id()
        self._layers[uv_set_id].remove(layer)

        if not self._layers[uv_set_id]:
            del self._layers[uv_set_id]

        layers = self.get_layers()

        for i, l in enumerate(layers):
            l.set_sort(i)

        if not (self._uses_layers and layer.is_active()):
            return

        tex_stage = layer.get_tex_stage()

        for owner_id in self._owner_ids:
            origin = Mgr.get("object", owner_id).get_origin()
            origin.clear_texture(tex_stage)
            origin.clear_tex_transform(tex_stage)

    def get_tex_stages(self, uv_set_id):

        if uv_set_id not in self._layers:
            return []

        stages = [l.get_tex_stage() for l in self._layers[uv_set_id]]

        if uv_set_id == 0:
            map_types = ("color", "normal", "height", "normal+height", "gloss",
                         "color+gloss", "glow", "color+glow")
            stages += [Mgr.get("tex_stage", map_type)
                       for map_type in map_types]

        return stages

    def get_uv_sets(self):

        return self._layers.keys()

    def set_texture(self, tex_data, layer_id=None):

        map_type = tex_data["map_type"]
        rgb_filename = tex_data["rgb_filename"]
        alpha_filename = tex_data["alpha_filename"]

        if layer_id is None:
            tex_map = self._tex_maps[map_type]
        else:
            tex_map = Mgr.get("tex_layer", layer_id)

        if not tex_map:
            return

        if tex_map.has_texture(rgb_filename, alpha_filename):
            return

        texture = tex_map.set_texture(rgb_filename, alpha_filename)

        if not tex_map.is_active():
            return

        tex_stage = tex_map.get_tex_stage()

        is_color_map = map_type in ("color", "layer")
        is_color_map_used = self._uses_layers != (layer_id is None)
        apply_map = not is_color_map or is_color_map_used

        if apply_map:
            if texture:
                for owner_id in self._owner_ids:
                    owner = Mgr.get("object", owner_id)
                    owner.get_origin().set_texture(tex_stage, texture)
            else:
                for owner_id in self._owner_ids:
                    owner = Mgr.get("object", owner_id)
                    owner.get_origin().clear_texture(tex_stage)

    def get_texture(self, map_type, layer_id=None):

        if layer_id is None:
            tex_map = self._tex_maps[map_type]
        else:
            tex_map = Mgr.get("tex_layer", layer_id)

        if not tex_map:
            return

        return tex_map.get_texture()

    def has_texture(self, tex_data, layer_id=None):

        map_type = tex_data["map_type"]
        rgb_filename = tex_data["rgb_filename"]
        alpha_filename = tex_data["alpha_filename"]

        if layer_id is None:
            tex_map = self._tex_maps[map_type]
        else:
            tex_map = Mgr.get("tex_layer", layer_id)

        if not tex_map:
            return False

        return tex_map.has_texture(rgb_filename, alpha_filename)

    def set_map_transform(self, map_type, layer_id, transf_type, comp_index, value):

        if layer_id is None:
            tex_map = self._tex_maps[map_type]
        else:
            tex_map = Mgr.get("tex_layer", layer_id)

        if not tex_map:
            return

        tex_map.set_transform(transf_type, comp_index, value)
        transform = tex_map.get_transform(transf_type)
        transform = transform[
            0] if transf_type == "rotate" else VBase2(*transform)
        tex_stage = tex_map.get_tex_stage()

        for owner_id in self._owner_ids:

            origin = Mgr.get("object", owner_id).get_origin()

            if transf_type == "offset":
                origin.set_tex_offset(tex_stage, transform)
            if transf_type == "rotate":
                origin.set_tex_rotate(tex_stage, transform)
            if transf_type == "scale":
                origin.set_tex_scale(tex_stage, transform)

            if origin.get_tex_transform(tex_stage).is_identity():
                origin.clear_tex_transform(tex_stage)

    def get_map_transform(self, map_type, layer_id=None):

        if layer_id is None:
            tex_map = self._tex_maps[map_type]
        else:
            tex_map = Mgr.get("tex_layer", layer_id)

        return tex_map.get_transform()

    def set_map_active(self, map_type, layer_id=None, is_active=True):

        if layer_id is None:
            tex_map = self._tex_maps[map_type]
        else:
            tex_map = Mgr.get("tex_layer", layer_id)

        if not tex_map or tex_map.is_active() == is_active:
            return

        if is_active:
            if "+" in map_type:
                for mtype in map_type.split("+"):
                    self.set_map_active(mtype, is_active=False)
            if map_type == "color+gloss":
                self.set_map_active("color+glow", is_active=False)
            elif map_type == "color+glow":
                self.set_map_active("color+gloss", is_active=False)
            elif map_type == "color":
                self.set_map_active("color+gloss", is_active=False)
                self.set_map_active("color+glow", is_active=False)
            elif map_type in ("normal", "height"):
                self.set_map_active("normal+height", is_active=False)
            elif map_type in ("glow", "gloss"):
                self.set_map_active("color+" + map_type, is_active=False)

        tex_map.set_active(is_active)
        tex_stage = tex_map.get_tex_stage()

        if is_active:
            texture = tex_map.get_texture()
            t = tex_map.get_transform()
            tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                              t["rotate"][0],
                                                              VBase2(*t["scale"]))
            handle_tex = lambda origin: (origin.set_texture(tex_stage, texture)
                                         if texture else None)
            handle_transform = lambda origin: (origin.set_tex_transform(tex_stage, tr_state)
                                               if not tr_state.is_identity() else None)
        else:
            handle_tex = lambda origin: origin.clear_texture(tex_stage)
            handle_transform = lambda origin: origin.clear_tex_transform(
                tex_stage)

        is_color_map = map_type in ("color", "layer")
        is_color_map_used = self._uses_layers != (layer_id is None)
        apply_map = not is_color_map or is_color_map_used

        if apply_map:
            for owner_id in self._owner_ids:
                origin = Mgr.get("object", owner_id).get_origin()
                handle_tex(origin)
                handle_transform(origin)

    def is_map_active(self, map_type, layer_id=None):

        if layer_id is None:
            tex_map = self._tex_maps[map_type]
        else:
            tex_map = Mgr.get("tex_layer", layer_id)

        if not tex_map:
            return False

        return tex_map.is_active()

    def has_tex_maps(self):

        for map_type, tex_map in self._tex_maps.iteritems():
            if tex_map.get_texture():
                return True

        return False

    def clear_tex_maps(self):

        change = False
        origins = [Mgr.get("object", owner_id).get_origin()
                   for owner_id in self._owner_ids]

        for map_type, tex_map in self._tex_maps.iteritems():

            if tex_map.get_texture():

                tex_map.set_texture()
                change = True

                if map_type == "color" and self._uses_layers:
                    continue

                tex_stage = tex_map.get_tex_stage()

                for origin in origins:
                    origin.clear_texture(tex_stage)
                    origin.clear_tex_transform(tex_stage)

        return change

    def apply(self, owner, force=False):

        owner_id = owner.get_id()

        if not force and owner_id in self._owner_ids:
            return

        origin = owner.get_origin()
        origin.set_material(BaseMaterial(self._base_mat))

        alpha_prop = self._base_props["alpha"]
        alpha = alpha_prop["value"]
        on = alpha_prop["on"]
        attrib = TransparencyAttrib.M_alpha if on else TransparencyAttrib.M_none
        origin.set_transparency(attrib)
        origin.set_alpha_scale(alpha)

        for map_type, tex_map in self._tex_maps.iteritems():

            if not tex_map.is_active() or (map_type == "color" and self._uses_layers):
                continue

            texture = tex_map.get_texture()
            tex_stage = tex_map.get_tex_stage()
            t = tex_map.get_transform()
            tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                              t["rotate"][0],
                                                              VBase2(*t["scale"]))

            if texture:
                origin.set_texture(tex_stage, texture)

            if not tr_state.is_identity():
                origin.set_tex_transform(tex_stage, tr_state)

        if self._uses_layers:

            layers = [l for group in self._layers.itervalues()
                      for l in group if l.is_active()]

            for layer in layers:

                texture = layer.get_texture()
                tex_stage = layer.get_tex_stage()
                t = layer.get_transform()
                tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                                  t["rotate"][
                                                                      0],
                                                                  VBase2(*t["scale"]))

                if texture:
                    origin.set_texture(tex_stage, texture)

                if not tr_state.is_identity():
                    origin.set_tex_transform(tex_stage, tr_state)

        if not owner_id in self._owner_ids:
            self._owner_ids.append(owner_id)

    def remove(self, owner):

        owner_id = owner.get_id()

        if not owner_id in self._owner_ids:
            return

        origin = owner.get_origin()
        origin.clear_material()
        origin.clear_texture()
        origin.clear_tex_transform()
        origin.clear_color_scale()
        origin.set_transparency(TransparencyAttrib.M_none)
        self._owner_ids.remove(owner_id)

        if not self._owner_ids:
            Mgr.do("unregister_material", self)

    def register(self):

        Mgr.do("register_material", self, in_library=True)

        for layers in self._layers.itervalues():
            for layer in layers:
                Mgr.do("register_tex_layer", layer)

    def unregister(self):

        Mgr.do("unregister_material", self, in_library=True)

        for layers in self._layers.itervalues():
            for layer in layers:
                Mgr.do("unregister_tex_layer", layer)

    def destroy(self):

        for owner in [Mgr.get("object", owner_id) for owner_id in self._owner_ids]:
            origin = owner.get_origin()
            origin.clear_material()
            origin.clear_texture()
            origin.clear_tex_transform()
            origin.clear_color_scale()
            origin.set_transparency(TransparencyAttrib.M_none)

        self._owner_ids = []


class MaterialManager(object):

    def __init__(self):

        self._materials = {}
        self._lib_materials = {}
        self._selected_material_id = None
        self._base_props = {}
        self._ready_props = {}
        self._owner_selection_mode = "replace"
        self._id_generator = id_generator()

    def setup(self):

        if "texture_maps_ok" not in MainObjects.get_setup_results():
            return False

        Mgr.accept("create_material", self.__create_material)
        Mgr.accept("register_material", self.__register_material)
        Mgr.accept("unregister_material", self.__unregister_material)
        Mgr.expose(
            "material", lambda material_id: self._materials.get(material_id))
        Mgr.expose("materials", lambda: self._materials)
        Mgr.add_app_updater("new_material", self.__update_new_material)
        Mgr.add_app_updater("extracted_material", self.__extract_material)
        Mgr.add_app_updater("removed_material", self.__remove_material)
        Mgr.add_app_updater("cleared_material_lib", self.__clear_library)
        Mgr.add_app_updater("material_owner_sel_mode",
                            self.__set_mat_owner_selection_mode)
        Mgr.add_app_updater("material_owners", self.__select_material_owners)
        Mgr.add_app_updater("material_selection", self.__select_material)
        Mgr.add_app_updater("material_prop", self.__set_material_property)
        Mgr.add_app_updater("ready_material_prop",
                            self.__set_ready_material_property)
        Mgr.add_app_updater("ready_material_color_selection",
                            self.__select_ready_material_color_type)
        Mgr.add_app_updater("selected_obj_mat_prop",
                            self.__apply_ready_material_property)
        Mgr.add_app_updater("selected_obj_mat_props",
                            self.__apply_ready_material_properties)
        Mgr.add_app_updater("selected_obj_tex",
                            self.__apply_ready_material_texture)

        prop_ids = ("diffuse", "ambient", "emissive",
                    "specular", "shininess", "alpha")
        white = {"value": (1., 1., 1., 1.), "on": True}
        black = {"value": (0., 0., 0., 1.), "on": False}
        shininess = {"value": 10., "on": True}
        alpha = {"value": 1., "on": False}
        defaults = (white,) + tuple([black.copy()
                                     for i in range(3)]) + (shininess, alpha)
        base_props = dict((prop_id, default)
                          for prop_id, default in zip(prop_ids, defaults))
        self._base_props = base_props

        self.__init_new_material(base_props, select=True)
        mat_id = self._materials.keys()[0]

        for prop_id, default in zip(prop_ids, defaults):
            Mgr.update_remotely("material_prop", mat_id, prop_id, default)

        def reset_ready_props():

            ready_defaults = (white.copy(),) + \
                tuple([black.copy() for i in range(3)])
            ready_defaults += (shininess.copy(), alpha.copy())
            self._ready_props = dict(
                (prop_id, default) for prop_id, default in zip(prop_ids, ready_defaults))

            for prop_id, default in zip(prop_ids, ready_defaults)[::-1]:
                Mgr.update_remotely("ready_material_prop", prop_id, default)

        reset_ready_props()
        Mgr.add_app_updater("reset_ready_material_props", reset_ready_props)

        return "materials_ok"

    def __get_unique_material_name(self, requested_name="", material=None):

        materials = self._lib_materials.values()

        if material and material in materials:
            materials.remove(material)

        namestring = "\n".join([m.get_name() for m in materials])
        search_pattern = r"^Material\s*(\d+)$"
        naming_pattern = "Material %04d"

        return get_unique_name(requested_name, namestring, search_pattern, naming_pattern)

    def __init_new_material(self, base_props, select=False):

        material_id = ("material",) + self._id_generator.next()
        material_name = self.__get_unique_material_name()
        material = Material(material_id, material_name)

        for prop_id, prop_data in base_props.iteritems():
            material.set_property(prop_id, prop_data)

        material.register()

        Mgr.update_remotely("new_material", material_id,
                            material_name, select=select)

    def __create_material(self, base_material=None, base_props=None,
                          tex_maps=None, layers=None, uses_layers=None):

        material_id = ("material",) + self._id_generator.next()
        name = ""
        material = Material(material_id, name, base_material, base_props,
                            tex_maps, layers, uses_layers)

        return material

    def __register_material(self, material, in_library=False):

        material_id = material.get_id()

        if in_library:
            self._lib_materials[material_id] = material
        else:
            self._materials[material_id] = material

    def __unregister_material(self, material, in_library=False):

        material_id = material.get_id()

        if in_library:
            del self._lib_materials[material_id]
        elif material_id not in self._lib_materials:
            del self._materials[material_id]

    def __select_material(self, material_id):

        self._selected_material_id = material_id
        material = self._lib_materials[material_id]

        for prop_id, prop_data in material.get_base_properties().iteritems():
            Mgr.update_remotely(
                "material_prop", material_id, prop_id, prop_data)

        map_type = material.get_selected_map_type()
        prop_id = "tex_map_select"
        material.set_property(prop_id, map_type)
        Mgr.update_remotely("material_prop", material_id, prop_id, map_type)

        uses_layers = material.uses_layers()
        prop_id = "layers_on"
        Mgr.update_remotely("material_prop", material_id, prop_id, uses_layers)

        prop_id = "layers"
        prop_data = tuple((layer.get_id(), layer.get_name())
                          for layer in material.get_layers())
        Mgr.update_remotely("material_prop", material_id, prop_id, prop_data)

        layer_id = material.get_selected_layer_id()
        Mgr.update_remotely("tex_layer_selection", layer_id)

    def __update_new_material(self, source_material_id):

        if source_material_id is None:
            self.__init_new_material(self._base_props, select=True)
            return

        source_material = self._lib_materials[source_material_id]
        source_name = source_material.get_name()
        original_name = re.sub(
            r" - copy$| - copy \(\d+\)$", "", source_name, 1)
        copy_name = original_name + " - copy"
        copy_name = self.__get_unique_material_name(copy_name)
        material = source_material.copy()
        material.set_name(copy_name)
        material.register()
        Mgr.update_remotely("new_material", material.get_id(), copy_name)

    def __extract_material(self, from_selection=True):

        # TODO: handle poly selection

        selection = [obj for obj in Mgr.get(
            "selection") if obj.get_type() == "model"]

        if not selection:
            return

        new_materials = []
        lib_material = None

        for obj in selection:

            material = obj.get_material()

            if material:

                if material.get_id() in self._lib_materials:

                    lib_material = material

                else:

                    material.set_name(
                        self.__get_unique_material_name(material.get_name()))
                    material.register()
                    new_materials.append(material)

        for material in new_materials[:-1]:
            name = material.get_name()
            Mgr.update_remotely(
                "new_material", material.get_id(), name, select=False)

        for material in new_materials[-1:]:
            name = material.get_name()
            Mgr.update_remotely("new_material", material.get_id(), name)
        else:
            if lib_material:
                Mgr.update_remotely("material_selection",
                                    lib_material.get_id())

    def __remove_material(self, material_id):

        material = self._lib_materials[material_id]
        material.unregister()

        if not material.get_owner_ids():
            del self._materials[material_id]

        if not self._lib_materials:
            self.__init_new_material(self._base_props, select=True)

    def __clear_library(self):

        materials = self._lib_materials.values()

        for material in materials:

            material.unregister()

            if not material.get_owner_ids():
                del self._materials[material.get_id()]

        self.__init_new_material(self._base_props, select=True)

    def __set_mat_owner_selection_mode(self, selection_mode):

        self._owner_selection_mode = selection_mode

    def __select_material_owners(self, material_id):

        material = self._lib_materials[material_id]
        owners = [Mgr.get("object", owner_id)
                  for owner_id in material.get_owner_ids()]
        Mgr.do("%s_selection" % self._owner_selection_mode, owners)

    def __set_material_property(self, material_id, prop_id, value):

        material = self._lib_materials[material_id]

        if prop_id == "name":
            value = self.__get_unique_material_name(value, material)

        value = material.set_property(prop_id, value)
        Mgr.update_remotely("material_prop", material_id, prop_id, value)

    def __set_ready_material_property(self, prop_id, value):

        ready_prop_data = self._ready_props[prop_id]
        ready_prop_data.update(value)

        Mgr.update_remotely("ready_material_prop", prop_id, ready_prop_data)

    def __select_ready_material_color_type(self, color_type):

        value = self._ready_props[color_type]

        Mgr.update_remotely("ready_material_prop", color_type, value)

    def __apply_ready_material_property(self, prop_id):

        # TODO: handle poly selection

        selection = [obj for obj in Mgr.get(
            "selection") if obj.get_type() == "model"]

        if not selection:
            return

        value = self._ready_props[prop_id]

        if prop_id in ("shininess", "alpha"):
            prop_name = prop_id
            val_str = "%.3f" % value["value"]
        else:
            prop_name = "%s color" % prop_id
            r, g, b = value["value"][:3]
            val_str = "R:%.3f | G:%.3f | B:%.3f" % (r, g, b)

        val_str = "None" if not value["on"] else val_str

        owners = {}
        changed_objs = []

        for obj in selection:
            owners.setdefault(obj.get_material(), []).append(obj)

        for material, objects in owners.iteritems():

            if material:

                if material.is_property_equal_to(prop_id, value):
                    continue

                new_material = material.copy()

            else:

                new_material = self.__create_material()

            new_material.set_property(prop_id, value)

            for owner in objects:
                owner.replace_material(new_material)
                changed_objs.append(owner)

        if not changed_objs:
            return

        # make undo/redoable
        obj_data = {}

        for obj in changed_objs:
            obj_id = obj.get_id()
            material = obj.get_material()
            obj_data[obj_id] = {"material": {"main": material}}

        if len(changed_objs) == 1:

            name = changed_objs[0].get_name()
            event_descr = 'Change %s of "%s"\nto %s' % (
                prop_name, name, val_str)

        else:

            event_descr = 'Change %s of objects:\n' % prop_name

            for obj in changed_objs:
                name = obj.get_name()
                event_descr += '\n    "%s"' % name

            event_descr += '\n\nto %s' % val_str

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data)

    def __apply_ready_material_properties(self):

        # TODO: handle poly selection

        selection = [obj for obj in Mgr.get(
            "selection") if obj.get_type() == "model"]

        if not selection:
            return

        properties = self._ready_props
        owners = {}
        changed_objs = []

        for obj in selection:
            owners.setdefault(obj.get_material(), []).append(obj)

        for material, objects in owners.iteritems():

            props = properties.copy()

            if material:

                for prop_id, value in properties.iteritems():
                    if material.is_property_equal_to(prop_id, value):
                        del props[prop_id]

                if not props:
                    continue

                new_material = material.copy()

            else:

                new_material = self.__create_material()

            new_material.set_base_properties(props)

            for owner in objects:
                owner.replace_material(new_material)
                changed_objs.append(owner)

        if not changed_objs:
            return

        # make undo/redoable
        obj_data = {}

        for obj in changed_objs:
            obj_id = obj.get_id()
            material = obj.get_material()
            obj_data[obj_id] = {"material": {"main": material}}

        if len(changed_objs) == 1:

            name = changed_objs[0].get_name()
            event_descr = 'Change material properties of "%s"' % name

        else:

            event_descr = 'Change material properties of objects:\n'

            for obj in changed_objs:
                name = obj.get_name()
                event_descr += '\n    "%s"' % name

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data)

    def __apply_ready_material_texture(self, tex_data):

        # TODO: handle poly selection

        selection = [obj for obj in Mgr.get(
            "selection") if obj.get_type() == "model"]

        if not selection:
            return

        owners = {}
        changed_objs = []
        map_type = tex_data["map_type"]
        rgb_filename = tex_data["rgb_filename"]
        alpha_filename = tex_data["alpha_filename"]
        empty_tex = rgb_filename == ""

        for obj in selection:
            owners.setdefault(obj.get_material(), []).append(obj)

        for material, objects in owners.iteritems():

            if material:

                if empty_tex and map_type == "all":
                    if not material.has_tex_maps():
                        continue
                elif material.has_texture(tex_data) and (empty_tex or material.is_map_active(map_type)):
                    continue

                copy_layers = False if map_type == "color" else True
                new_material = material.copy(copy_layers=copy_layers)

            else:

                if empty_tex:
                    continue

                new_material = self.__create_material()

            if empty_tex:
                if map_type == "all":
                    new_material.clear_tex_maps()
                else:
                    new_material.set_texture(tex_data)
                    new_material.set_map_active(map_type, is_active=False)
            else:
                new_material.set_texture(tex_data)
                new_material.set_map_active(map_type, is_active=True)

            for owner in objects:
                owner.replace_material(new_material)
                changed_objs.append(owner)

        if not changed_objs:
            return

        tex_str = "textures" if map_type == "all" else "texture"
        filedescr = ("RGBA -> %s" % rgb_filename) if rgb_filename else "None"

        # make undo/redoable
        obj_data = {}

        for obj in changed_objs:
            obj_id = obj.get_id()
            material = obj.get_material()
            obj_data[obj_id] = {"material": {"main": material}}

        if len(changed_objs) == 1:

            name = changed_objs[0].get_name()
            event_descr = 'Change %s %s of "%s"\nto %s' % (
                map_type, tex_str, name, filedescr)

        else:

            event_descr = 'Change %s %s of objects:\n' % (map_type, tex_str)

            for obj in changed_objs:
                name = obj.get_name()
                event_descr += '\n    "%s"' % name

            event_descr += '\n\nto %s' % filedescr

        if alpha_filename:
            event_descr += '\n+ ALPHA -> %s' % alpha_filename

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data)


MainObjects.add_class(MaterialManager)
