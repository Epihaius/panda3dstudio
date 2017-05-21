from .base import *
from .base import Material as BaseMaterial


class Material(object):

    def __getstate__(self):

        state = self.__dict__.copy()
        state["_owner_ids"] = []

        return state

    def __str__(self):

        return self._name

    def __init__(self, material_id, name, shows_vert_colors=None, flat_color=None, base_material=None,
                 base_props=None, tex_maps=None, layers=None, uses_layers=None):

        self._id = material_id
        self._name = name
        self._shows_vert_colors = False if shows_vert_colors is None else shows_vert_colors
        self._flat_color = (1., 1., 1., 1.) if flat_color is None else flat_color
        self._base_mat = base_material if base_material else BaseMaterial(name)
        prop_ids = ("diffuse", "ambient", "emissive", "specular", "shininess", "alpha")
        self._base_prop_ids = prop_ids

        if base_props:
            self._base_props = base_props
        else:
            props = dict((prop_id, {"value": (0., 0., 0., 1.), "on": False})
                         for prop_id in prop_ids)
            props["diffuse"]["value"] = (1., 1., 1., 1.)
            props["ambient"]["value"] = (1., 1., 1., 1.)
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
                         "color+gloss", "normal+gloss", "glow", "color+glow",
                         "vertex color")
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
        material = Mgr.do("create_material", self._shows_vert_colors, self._flat_color,
                          base_material, base_props, tex_maps, layers, uses_layers)

        return material

    def equals(self, other):

        if self._shows_vert_colors != other.shows_vertex_colors():
            return False

        if self._flat_color != other.get_flat_color():
            return False

        other_base_mat = BaseMaterial(other.get_base_material())
        other_base_mat.set_name(self._base_mat.get_name())

        if self._base_mat != other_base_mat:
            return False

        if not other.is_property_equal_to("alpha", self._base_props["alpha"]):
            return False

        for map_type, tex_map in other.get_tex_maps():
            if not self._tex_maps[map_type].equals(tex_map):
                return False

        if self._uses_layers != other.uses_layers():
            return False

        if self._uses_layers:

            if set(self._layers) != set(other.get_uv_sets()):
                return False

            for uv_set_id, layers in self._layers.iteritems():
                for layer_index, layer in enumerate(layers):
                    if not other.get_layer(uv_set_id, layer_index).equals(layer):
                        return False

        return True

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
            owner = Mgr.get("model", owner_id)
            origin = owner.get_origin()
            origin.set_material(base_material)

    def set_property(self, prop_id, value, apply_base_mat=True):

        base_props = self._base_props

        if prop_id == "name":

            self.set_name(value)

        elif prop_id == "show_vert_colors":

            self.show_vertex_colors(value)

        elif prop_id == "flat_color":

            self.set_flat_color(value)

        elif prop_id in self._base_prop_ids:

            props = base_props[prop_id]
            props.update(value)
            val = props["value"]
            on = props["on"]
            bm = self._base_mat

            def set_alpha(value, on):

                attrib = TransparencyAttrib.M_alpha if on else TransparencyAttrib.M_none
                diffuse_props = base_props["diffuse"]
                diffuse_value = list(diffuse_props["value"])

                if on:

                    diffuse_value[3] = value

                    for owner_id in self._owner_ids:
                        owner = Mgr.get("model", owner_id)
                        origin = owner.get_origin()
                        origin.set_transparency(attrib)
                        origin.set_alpha_scale(value)
                else:

                    diffuse_value[3] = 1.

                    for owner_id in self._owner_ids:
                        owner = Mgr.get("model", owner_id)
                        origin = owner.get_origin()
                        origin.set_transparency(attrib)
                        origin.clear_color_scale()

                diffuse_props["value"] = tuple(diffuse_value)

                if diffuse_props["on"]:
                    bm.set_diffuse(VBase4(*diffuse_value))

            if prop_id == "diffuse":
                val = list(val)
                alpha_props = base_props["alpha"]
                val[3] = alpha_props["value"] if alpha_props["on"] else 1.
                base_props["diffuse"]["value"] = tuple(val)
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

            self.set_map_transform(self._selected_map_type, None, "offset", 0, value)

        elif prop_id == "tex_map_offset_v":

            self.set_map_transform(self._selected_map_type, None, "offset", 1, value)

        elif prop_id == "tex_map_rotate":

            self.set_map_transform(self._selected_map_type, None, "rotate", 0, value)

        elif prop_id == "tex_map_scale_u":

            self.set_map_transform(self._selected_map_type, None, "scale", 0, value)

        elif prop_id == "tex_map_scale_v":

            self.set_map_transform(self._selected_map_type, None, "scale", 1, value)

        return value

    def show_vertex_colors(self, shows_vert_colors=True):

        origins = [Mgr.get("model", owner_id).get_origin()
                   for owner_id in self._owner_ids]

        if shows_vert_colors:
            for origin in origins:
                origin.set_color_off()
        else:
            for origin in origins:
                origin.set_color(self._flat_color)

        self._shows_vert_colors = shows_vert_colors

    def shows_vertex_colors(self):

        return self._shows_vert_colors

    def set_flat_color(self, color):

        origins = [Mgr.get("model", owner_id).get_origin()
                   for owner_id in self._owner_ids]

        if not self._shows_vert_colors:
            for origin in origins:
                origin.set_color(color)

        self._flat_color = color

    def get_flat_color(self):

        return self._flat_color

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

    def has_base_properties(self):

        bm = self._base_mat
        has_base_props = (bm.has_diffuse() or bm.has_ambient() or bm.has_emission()
                          or bm.has_specular()) and bm.get_shininess != 10.

        return has_base_props

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

        origins = [Mgr.get("model", owner_id).get_origin()
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
                                                                  t["rotate"][0],
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
                                                                  t["rotate"][0],
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

        d = dict((l.get_sort(), l) for group in self._layers.itervalues() for l in group)

        return [d[i] for i in sorted(d)]

    def add_layer(self, layer):

        count = sum([len(group) for group in self._layers.itervalues()])
        layer.set_sort(count)
        self._layers.setdefault(layer.get_uv_set_id(), []).append(layer)

        if not (self._uses_layers and layer.is_active()):
            return

        origins = [Mgr.get("model", owner_id).get_origin()
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
                origin = Mgr.get("model", owner_id).get_origin()
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
            origin = Mgr.get("model", owner_id).get_origin()
            origin.clear_texture(tex_stage)
            origin.clear_tex_transform(tex_stage)

    def get_tex_stages(self, uv_set_id):

        if uv_set_id not in self._layers:
            return []

        stages = [l.get_tex_stage() for l in self._layers[uv_set_id]]

        if uv_set_id == 0:
            map_types = ("color", "normal", "height", "normal+height", "gloss",
                         "color+gloss", "normal+gloss", "glow", "color+glow")
            stages += [Mgr.get("tex_stage", map_type) for map_type in map_types]

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

            owners = [Mgr.get("model", owner_id) for owner_id in self._owner_ids]

            if map_type == "vertex color":

                if texture:
                    for owner in owners:
                        owner.get_geom_object().bake_texture(texture)
                else:
                    for owner in owners:
                        owner.get_geom_object().reset_vertex_colors()

                return

            if texture:

                for owner in owners:
                    owner.get_origin().set_texture(tex_stage, texture)

                if "normal" in map_type and tex_map.is_active():
                    for owner in owners:
                        if not owner.has_tangent_space():
                            owner.init_tangent_space()

            else:

                for owner in owners:
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

        if not tex_map or map_type == "vertex color":
            return

        tex_map.set_transform(transf_type, comp_index, value)
        transform = tex_map.get_transform(transf_type)
        transform = transform[0] if transf_type == "rotate" else VBase2(*transform)
        tex_stage = tex_map.get_tex_stage()

        for owner_id in self._owner_ids:

            origin = Mgr.get("model", owner_id).get_origin()

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
                self.set_map_active("normal+gloss", is_active=False)
            elif map_type == "color+glow":
                self.set_map_active("color+gloss", is_active=False)
            elif map_type == "color":
                self.set_map_active("color+gloss", is_active=False)
                self.set_map_active("color+glow", is_active=False)
            elif map_type in ("normal", "height"):
                if map_type == "normal":
                    self.set_map_active("normal+gloss", is_active=False)
                self.set_map_active("normal+height", is_active=False)
            elif map_type in ("glow", "gloss"):
                if map_type == "gloss":
                    self.set_map_active("normal+gloss", is_active=False)
                self.set_map_active("color+" + map_type, is_active=False)
            elif map_type == "normal+gloss":
                self.set_map_active("color+gloss", is_active=False)
                self.set_map_active("normal+height", is_active=False)
            elif map_type == "normal+height":
                self.set_map_active("normal+gloss", is_active=False)

        tex_map.set_active(is_active)

        is_color_map = map_type in ("color", "layer")
        is_color_map_used = self._uses_layers != (layer_id is None)
        apply_map = not is_color_map or is_color_map_used
        texture = tex_map.get_texture()

        if apply_map and texture:

            owners = [Mgr.get("model", owner_id) for owner_id in self._owner_ids]

            if map_type == "vertex color":

                if is_active:
                    for owner in owners:
                        owner.get_geom_object().bake_texture(texture)
                else:
                    for owner in owners:
                        owner.get_geom_object().reset_vertex_colors()

                return

            tex_stage = tex_map.get_tex_stage()

            if is_active:
                t = tex_map.get_transform()
                tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                                  t["rotate"][0],
                                                                  VBase2(*t["scale"]))
                handle_tex = lambda origin: origin.set_texture(tex_stage, texture)
                handle_transform = lambda origin: (origin.set_tex_transform(tex_stage, tr_state)
                                                   if not tr_state.is_identity() else None)
            else:
                handle_tex = lambda origin: origin.clear_texture(tex_stage)
                handle_transform = lambda origin: origin.clear_tex_transform(tex_stage)

            for owner in owners:
                origin = owner.get_origin()
                handle_tex(origin)
                handle_transform(origin)

            if is_active and "normal" in map_type:
                for owner in owners:
                    if not owner.has_tangent_space():
                        owner.init_tangent_space()

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
        owners = [Mgr.get("model", owner_id) for owner_id in self._owner_ids]
        origins = [owner.get_origin() for owner in owners]

        for map_type, tex_map in self._tex_maps.iteritems():

            if tex_map.get_texture():

                tex_map.set_texture()
                change = True

                if map_type == "vertex color":

                    for owner in owners:
                        owner.get_geom_object().reset_vertex_colors()

                    continue

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
            return False

        origin = owner.get_origin()
        origin.set_color_off() if self._shows_vert_colors else origin.set_color(self._flat_color)
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

            if map_type == "vertex color":

                if texture:
                    owner.get_geom_object().bake_texture(texture)
                else:
                    owner.get_geom_object().reset_vertex_colors()

                continue

            tex_stage = tex_map.get_tex_stage()
            t = tex_map.get_transform()
            tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                              t["rotate"][0],
                                                              VBase2(*t["scale"]))

            if texture:
                origin.set_texture(tex_stage, texture)

            if not tr_state.is_identity():
                origin.set_tex_transform(tex_stage, tr_state)

            if "normal" in map_type and texture:
                if not owner.has_tangent_space():
                    owner.init_tangent_space()

        if self._uses_layers:

            layers = [l for group in self._layers.itervalues()
                      for l in group if l.is_active()]

            for layer in layers:

                texture = layer.get_texture()
                tex_stage = layer.get_tex_stage()
                t = layer.get_transform()
                tr_state = TransformState.make_pos_rotate_scale2d(VBase2(*t["offset"]),
                                                                  t["rotate"][0],
                                                                  VBase2(*t["scale"]))

                if texture:
                    origin.set_texture(tex_stage, texture)

                if not tr_state.is_identity():
                    origin.set_tex_transform(tex_stage, tr_state)

        if not owner_id in self._owner_ids:
            self._owner_ids.append(owner_id)

        return True

    def remove(self, owner):

        owner_id = owner.get_id()

        if not owner_id in self._owner_ids:
            return False

        owner.get_geom_object().reset_vertex_colors()
        origin = owner.get_origin()

        if origin:
            origin.clear_material()
            origin.clear_texture()
            origin.clear_tex_transform()
            origin.clear_color_scale()
            origin.set_transparency(TransparencyAttrib.M_none)
            origin.set_color(owner.get_color())

        self._owner_ids.remove(owner_id)

        if not self._owner_ids:
            Mgr.do("unregister_material", self)

        if owner.get_geom_type() != "basic_geom":
            if owner.has_tangent_space():
                owner.clear_tangent_space()

        return True

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

    def strip(self):

        for owner in (Mgr.get("model", owner_id) for owner_id in self._owner_ids):

            owner.get_geom_object().reset_vertex_colors()
            origin = owner.get_origin()
            origin.clear_material()
            origin.clear_texture()
            origin.clear_tex_transform()
            origin.clear_color_scale()
            origin.set_transparency(TransparencyAttrib.M_none)
            origin.set_color(owner.get_color())

            if owner.get_geom_type() != "basic_geom":
                if owner.has_tangent_space():
                    owner.clear_tangent_space()

        self._owner_ids = []
        Mgr.do("unregister_material", self)


class MaterialManager(object):

    def __init__(self):

        self._materials = {}
        self._materials_backup = None
        self._registry_backup_created = False
        self._library = {}
        self._selected_material_id = None
        self._base_props = {}
        self._ready_props = {}
        self._owner_selection_mode = "replace"
        self._dupe_handling = "skip"
        self._picking_op = ""
        self._id_generator = id_generator()

        self._pixel_under_mouse = VBase4()

    def setup(self):

        if "texture_maps_ok" not in MainObjects.get_setup_results():
            return False

        Mgr.accept("create_material", self.__create_material)
        Mgr.accept("register_material", self.__register_material)
        Mgr.accept("unregister_material", self.__unregister_material)
        Mgr.accept("set_material_library", self.__set_library)
        Mgr.accept("create_material_registry_backup", self.__create_registry_backup)
        Mgr.expose("material", lambda material_id: self._materials.get(material_id))
        Mgr.expose("materials", lambda: self._materials)
        Mgr.expose("material_library", lambda: self._library)
        Mgr.add_app_updater("new_material", self.__update_new_material)
        Mgr.add_app_updater("extracted_material", self.__extract_material)
        Mgr.add_app_updater("applied_material", self.__apply_material)
        Mgr.add_app_updater("removed_material", self.__remove_material)
        Mgr.add_app_updater("scene_materials", self.__update_scene)
        Mgr.add_app_updater("material_library", self.__update_library)
        Mgr.add_app_updater("material_owner_sel_mode", self.__set_mat_owner_selection_mode)
        Mgr.add_app_updater("material_owners", self.__select_material_owners)
        Mgr.add_app_updater("material_owner_picking", self.__start_material_owner_picking)
        Mgr.add_app_updater("material_selection", self.__select_material)
        Mgr.add_app_updater("material_prop", self.__set_material_property)
        Mgr.add_app_updater("ready_material_prop", self.__set_ready_material_property)
        Mgr.add_app_updater("ready_material_color_selection", self.__select_ready_material_color_type)
        Mgr.add_app_updater("selected_obj_mat_prop", self.__apply_ready_material_property)
        Mgr.add_app_updater("selected_obj_mat_props", self.__apply_ready_material_properties)
        Mgr.add_app_updater("selected_obj_tex", self.__apply_ready_material_texture)
        Mgr.add_app_updater("dupe_material_handling", self.__handle_dupe_material_loading)
        Mgr.add_notification_handler("long_process_cancelled", "material_mgr",
                                     self.__restore_registry_backup)

        prop_ids = ("diffuse", "ambient", "emissive", "specular", "shininess", "alpha")
        white = {"value": (1., 1., 1., 1.), "on": False}
        black = {"value": (0., 0., 0., 1.), "on": False}
        shininess = {"value": 10., "on": True}
        alpha = {"value": 1., "on": False}
        defaults = (white.copy(), white.copy(), black.copy(), black.copy(), shininess, alpha)
        base_props = dict((prop_id, default) for prop_id, default in zip(prop_ids, defaults))
        self._base_props = base_props

        self.__init_new_material(base_props, select=True)
        mat_id = self._materials.keys()[0]

        for prop_id, default in zip(prop_ids, defaults):
            Mgr.update_remotely("material_prop", mat_id, prop_id, default)

        def reset_ready_props():

            ready_defaults = (white.copy(), white.copy(), black.copy(), black.copy(),
                              shininess.copy(), alpha.copy())
            self._ready_props = dict((prop_id, default)
                                     for prop_id, default in zip(prop_ids, ready_defaults))

            for prop_id, default in reversed(zip(prop_ids, ready_defaults)):
                Mgr.update_remotely("ready_material_prop", prop_id, default)

        reset_ready_props()
        Mgr.add_app_updater("reset_ready_material_props", reset_ready_props)

        add_state = Mgr.add_state
        add_state("material_owner_picking_mode", -10, self.__enter_picking_mode,
                  self.__exit_picking_mode)

        def exit_owner_picking_mode():

            Mgr.exit_state("material_owner_picking_mode")

        bind = Mgr.bind_state
        bind("material_owner_picking_mode", "pick material owner -> navigate", "space",
             lambda: Mgr.enter_state("navigation_mode"))
        bind("material_owner_picking_mode", "pick material owner", "mouse1", self.__pick_owner)
        bind("material_owner_picking_mode", "exit material owner picking", "escape",
             exit_owner_picking_mode)
        bind("material_owner_picking_mode", "cancel material owner picking", "mouse3-up",
             exit_owner_picking_mode)

        status_data = GlobalData["status_data"]
        mode_text = "Pick material owner"
        info_text = "LMB to pick object; RMB to end"
        status_data["pick_material_owner"] = {"mode": mode_text, "info": info_text}

        return "materials_ok"

    def __get_models(self, objs):

        def get_grouped_models(group, models):

            for member in group.get_members():
                if member.get_type() == "model":
                    models.append(member)
                elif member.get_type() == "group" and not member.is_open():
                    get_grouped_models(member, models)

        models = []

        for obj in objs:
            if obj.get_type() == "model":
                models.append(obj)
            elif obj.get_type() == "group" and not obj.is_open():
                get_grouped_models(obj, models)

        return models

    def __enter_picking_mode(self, prev_state_id, is_active):

        if GlobalData["active_obj_level"] != "top":
            GlobalData["active_obj_level"] = "top"
            Mgr.update_app("active_obj_level")

        Mgr.add_task(self.__update_cursor, "update_matrl_owner_picking_cursor")
        Mgr.update_app("status", "pick_material_owner")

    def __exit_picking_mode(self, next_state_id, is_active):

        if not is_active:
            self._picking_op = ""

        self._pixel_under_mouse = VBase4() # force an update of the cursor
                                           # next time self.__update_cursor()
                                           # is called
        Mgr.remove_task("update_matrl_owner_picking_cursor")
        Mgr.set_cursor("main")

    def __pick_owner(self):

        obj = Mgr.get("object", pixel_color=self._pixel_under_mouse)
        objs = self.__get_models([obj]) if obj else None

        if objs:
            if self._picking_op == "extract":
                self.__extract_material(objs)
            elif self._picking_op == "apply":
                self.__apply_material(objs)

    def __update_cursor(self, task):

        pixel_under_mouse = Mgr.get("pixel_under_mouse")

        if self._pixel_under_mouse != pixel_under_mouse:
            Mgr.set_cursor("main" if pixel_under_mouse == VBase4() else "select")
            self._pixel_under_mouse = pixel_under_mouse

        return task.cont

    def __start_material_owner_picking(self, picking_op):

        self._picking_op = picking_op
        Mgr.enter_state("material_owner_picking_mode")

    def __get_unique_material_name(self, requested_name="", material=None):

        materials = self._library.values()

        if material and material in materials:
            materials.remove(material)

        namelist = [m.get_name() for m in materials]
        search_pattern = r"^Material\s*(\d+)$"
        naming_pattern = "Material %04d"

        return get_unique_name(requested_name, namelist, search_pattern, naming_pattern)

    def __init_new_material(self, base_props, select=False):

        material_id = ("material",) + self._id_generator.next()
        material_name = self.__get_unique_material_name()
        material = Material(material_id, material_name)

        for prop_id, prop_data in base_props.iteritems():
            material.set_property(prop_id, prop_data)

        material.register()

        Mgr.update_remotely("new_material", material_id, material_name, select=select)

    def __create_material(self, shows_vert_colors=None, flat_color=None, base_material=None,
                          base_props=None, tex_maps=None, layers=None, uses_layers=None):

        material_id = ("material",) + self._id_generator.next()
        name = ""
        material = Material(material_id, name, shows_vert_colors, flat_color, base_material,
                            base_props, tex_maps, layers, uses_layers)

        return material

    def __register_material(self, material, in_library=False):

        material_id = material.get_id()
        self._materials[material_id] = material

        if in_library:
            self._library[material_id] = material

    def __unregister_material(self, material, in_library=False):

        material_id = material.get_id()

        if material_id not in self._materials:
            return

        if in_library:

            del self._library[material_id]

            if not material.get_owner_ids():
                del self._materials[material_id]

        elif material_id not in self._library:

            del self._materials[material_id]

    def __create_registry_backup(self):

        if self._registry_backup_created:
            return

        self._materials_backup = self._materials.copy()
        task = self.__remove_registry_backup
        task_id = "remove_material_registry_backup"
        PendingTasks.add(task, task_id, "object", sort=100)
        self._registry_backup_created = True
        logging.info('Material registry backup created.')

    def __restore_registry_backup(self, info=""):

        if not self._registry_backup_created:
            return

        self._materials = self._materials_backup
        logging.info('Material registry backup restored;\ninfo: %s', info)
        self.__remove_registry_backup()

    def __remove_registry_backup(self):

        if not self._registry_backup_created:
            return

        self._materials_backup = None
        self._registry_backup_created = False
        logging.info('Material registry backup removed.')

    def __select_material(self, material_id):

        self._selected_material_id = material_id
        material = self._library[material_id]

        shows_vert_colors = material.shows_vertex_colors()
        prop_id = "show_vert_colors"
        Mgr.update_remotely("material_prop", material_id, prop_id, shows_vert_colors)

        flat_color = material.get_flat_color()
        prop_id = "flat_color"
        Mgr.update_remotely("material_prop", material_id, prop_id, flat_color)

        for prop_id, prop_data in material.get_base_properties().iteritems():
            Mgr.update_remotely("material_prop", material_id, prop_id, prop_data)

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

        source_material = self._library[source_material_id]
        source_name = source_material.get_name()
        original_name = re.sub(r" - copy$| - copy \(\d+\)$", "", source_name, 1)
        copy_name = original_name + " - copy"
        copy_name = self.__get_unique_material_name(copy_name)
        material = source_material.copy()
        material.set_name(copy_name)
        material.register()
        Mgr.update_remotely("new_material", material.get_id(), copy_name)

    def __clear_scene(self):

        owner_ids = []

        for material in self._materials.itervalues():
            owner_ids.extend(material.get_owner_ids())

        owners = [Mgr.get("model", owner_id) for owner_id in owner_ids]

        # make undo/redoable

        Mgr.do("update_history_time")

        obj_data = {}

        for obj in owners:
            obj.set_material(None)
            obj_data[obj.get_id()] = obj.get_data_to_store("prop_change", "material")

        event_descr = 'Remove materials from scene'
        event_data = {"objects": obj_data}

        Mgr.do("add_history", event_descr, event_data, update_time_id=False)

    def __update_scene(self, update_type):

        if update_type == "clear":
            self.__clear_scene()

    def __extract_material(self, objs=None):

        if not objs:
            objs = self.__get_models(Mgr.get("selection", "top"))

        if not objs:
            return

        new_materials = []
        lib_material = None

        for obj in objs:

            material = obj.get_material()

            if material:

                if material.get_id() in self._library:
                    lib_material = material
                else:
                    material.set_name(self.__get_unique_material_name(material.get_name()))
                    material.register()
                    new_materials.append(material)

        for material in new_materials[:-1]:
            name = material.get_name()
            Mgr.update_remotely("new_material", material.get_id(), name, select=False)

        for material in new_materials[-1:]:
            name = material.get_name()
            Mgr.update_remotely("new_material", material.get_id(), name)
        else:
            if lib_material:
                Mgr.update_remotely("material_selection", lib_material.get_id())

    def __apply_material(self, objs=None, clear_material=False):

        if not objs:
            objs = self.__get_models(Mgr.get("selection", "top"))

        if not objs:
            return

        material = None if clear_material else self._materials.get(self._selected_material_id)
        changed_objs = [obj for obj in objs if obj.set_property("material", material)]

        if changed_objs:

            obj_data = {}
            event_data = {"objects": obj_data}

            if len(changed_objs) == 1:

                if clear_material:
                    event_descr = 'Remove material from "%s"' % changed_objs[0].get_name()
                else:
                    args = (changed_objs[0].get_name(), material)
                    event_descr = 'Change material of "%s"\nto "%s"' % args

            else:

                if clear_material:
                    event_descr = 'Remove material from objects:\n'
                else:
                    event_descr = 'Change material of objects:\n'

                for obj in changed_objs:
                    event_descr += '\n    "%s"' % obj.get_name()

                if not clear_material:
                    event_descr += '\n\nto "%s"' % material

            for obj in changed_objs:
                obj_data[obj.get_id()] = obj.get_data_to_store("prop_change", "material")

            Mgr.do("add_history", event_descr, event_data)

    def __handle_dupe_material_loading(self, duplicate_handling):

        self._dupe_handling = duplicate_handling

    def __save_library(self, filename):

        with open(filename, "wb") as lib_file:
            cPickle.dump(self._library, lib_file, -1)

    def __load_library(self, filename=None, library=None, merge=False):

        from_scene = False

        if library == "scene":
            from_scene = True
            library = dict((m_id, m) for m_id, m in self._materials.iteritems()
                           if m.get_owner_ids())
        elif not library:
            with open(filename, "rb") as lib_file:
                library = cPickle.load(lib_file)

        if not library:

            if not merge:
                Mgr.update_remotely("material_library", "clear")
                self.__clear_library()

            return

        Mgr.update_remotely("material_library", "clear")

        if not merge:
            for material_id in self._library.copy():
                if material_id not in library:
                    material = self._library[material_id]
                    material.unregister()

        dupe_handling = self._dupe_handling

        if dupe_handling == "copy":

            def copy_material(material_id):

                loaded_material = library[material_id]
                name = loaded_material.get_name()
                material = loaded_material.copy()
                material.set_name(self.__get_unique_material_name(name))
                material.register()
                self._materials[material.get_id()] = material

        elif dupe_handling == "replace":

            def replace_material(material_id):

                old_material = self._materials[material_id]
                owner_ids = old_material.get_owner_ids()
                old_material.strip()

                if material_id in self._library:
                    old_material.unregister()

                material = library[material_id]
                material.set_name(self.__get_unique_material_name(material.get_name()))
                material.register()
                self._materials[material_id] = material

                for owner in (Mgr.get("model", owner_id) for owner_id in owner_ids):
                    material.apply(owner)

        for material_id in library:
            if material_id in self._library:
                if dupe_handling == "skip":
                    continue
                elif dupe_handling == "copy":
                    copy_material(material_id)
                elif dupe_handling == "replace":
                    replace_material(material_id)
            elif not from_scene and material_id in self._materials:
                if dupe_handling == "skip":
                    material = self._materials[material_id]
                    material.set_name(self.__get_unique_material_name(material.get_name()))
                    material.register()
                elif dupe_handling == "copy":
                    copy_material(material_id)
                elif dupe_handling == "replace":
                    replace_material(material_id)
            else:
                material = library[material_id]
                material.set_name(self.__get_unique_material_name(material.get_name()))
                material.register()
                self._materials[material_id] = material

        materials = self._library.values()

        for material in materials[:-1]:
            Mgr.update_remotely("new_material", material.get_id(), material.get_name(), select=False)

        for material in materials[-1:]:
            Mgr.update_remotely("new_material", material.get_id(), material.get_name())

    def __clear_library(self):

        materials = self._library.values()

        for material in materials:
            material.unregister()

        self.__init_new_material(self._base_props, select=True)

    def __set_library(self, library):

        Mgr.update_remotely("material_library", "clear")
        dupe_handling = self._dupe_handling
        self._dupe_handling = "replace"
        self.__load_library(library=library)
        self._dupe_handling = dupe_handling

    def __update_library(self, update_type, filename=None):

        if update_type == "save":
            self.__save_library(filename)
        elif update_type == "load":
            if filename is None:
                self.__load_library(library="scene")
            else:
                self.__load_library(filename)
        elif update_type == "merge":
            if filename is None:
                self.__load_library(library="scene", merge=True)
            else:
                self.__load_library(filename, merge=True)
        elif update_type == "clear":
            self.__clear_library()

    def __remove_material(self, material_id):

        material = self._library[material_id]
        material.unregister()

        if not self._library:
            self.__init_new_material(self._base_props, select=True)

    def __set_mat_owner_selection_mode(self, selection_mode):

        self._owner_selection_mode = selection_mode

    def __select_material_owners(self, material_id):

        if GlobalData["active_obj_level"] != "top":
            GlobalData["active_obj_level"] = "top"
            Mgr.update_app("active_obj_level")

        material = self._library[material_id]
        owners = set()

        for owner_id in material.get_owner_ids():
            obj = Mgr.get("model", owner_id).get_toplevel_object(get_group=True)
            owners.add(obj)

        sel_mode = self._owner_selection_mode
        selection = Mgr.get("selection", "top")

        if sel_mode == "add_to":
            selection.add(owners)
        elif sel_mode == "remove_from":
            selection.remove(owners)
        elif sel_mode == "replace":
            selection.replace(owners)

    def __set_material_property(self, material_id, prop_id, value):

        material = self._library[material_id]

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

        selection = self.__get_models(Mgr.get("selection", "top"))

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
            event_descr = 'Change %s of "%s"\nto %s' % (prop_name, name, val_str)

        else:

            event_descr = 'Change %s of objects:\n' % prop_name

            for obj in changed_objs:
                name = obj.get_name()
                event_descr += '\n    "%s"' % name

            event_descr += '\n\nto %s' % val_str

        event_data = {"objects": obj_data}
        Mgr.do("add_history", event_descr, event_data)

    def __apply_ready_material_properties(self):

        selection = self.__get_models(Mgr.get("selection", "top"))

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

        selection = self.__get_models(Mgr.get("selection", "top"))

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
            event_descr = 'Change %s %s of "%s"\nto %s' % (map_type, tex_str, name, filedescr)

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
