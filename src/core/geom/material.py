from ..base import *


SS = SamplerState
WRAP_MODES = (SS.WM_repeat, SS.WM_clamp, SS.WM_border_color, SS.WM_mirror, SS.WM_mirror_once)
WRAP_MODE_IDS = ("repeat", "clamp", "border_color", "mirror", "mirror_once")
FILTER_TYPES = (SS.FT_nearest, SS.FT_linear, SS.FT_nearest_mipmap_nearest,
                SS.FT_nearest_mipmap_linear, SS.FT_linear_mipmap_nearest,
                SS.FT_linear_mipmap_linear, SS.FT_shadow, SS.FT_default)
FILTER_TYPE_IDS = ("nearest", "linear", "nearest_mipmap_nearest", "nearest_mipmap_linear",
                   "linear_mipmap_nearest", "linear_mipmap_linear", "shadow", "linear")

TS = TextureStage
FXMAP_TYPES = (TS.M_normal, TS.M_height, TS.M_normal_height, TS.M_gloss,
               TS.M_modulate_gloss, TS.M_normal_gloss, TS.M_glow, TS.M_modulate_glow)
FXMAP_IDS = ("normal", "height", "normal+height", "gloss",
             "color+gloss", "normal+gloss", "glow", "color+glow")
BLEND_MODES = (TS.M_modulate, TS.M_replace, TS.M_decal, TS.M_add,
               TS.M_blend, TS.M_blend_color_scale, TS.M_selector)
BLEND_MODE_IDS = ("modulate", "replace", "decal", "add",
                  "blend", "blend_color_scale", "selector")
COMBINE_MODES = (TS.CM_modulate, TS.CM_interpolate, TS.CM_replace, TS.CM_subtract,
                 TS.CM_add, TS.CM_add_signed, TS.CM_dot3_rgb, TS.CM_dot3_rgba)
COMBINE_MODE_IDS = ("modulate", "interpolate", "replace", "subtract",
                    "add", "add_signed", "dot3rgb", "dot3rgba")
COMBINE_MODE_SOURCES = (TS.CS_texture, TS.CS_previous, TS.CS_last_saved_result,
                        TS.CS_primary_color, TS.CS_constant, TS.CS_constant_color_scale)
COMBINE_MODE_SOURCE_IDS = ("texture", "previous_layer", "last_stored_layer",
                           "primary_color", "constant_color", "const_color_scale")
COMBINE_MODE_SRC_CHANNELS = (TS.CO_src_color, TS.CO_one_minus_src_color,
                             TS.CO_src_alpha, TS.CO_one_minus_src_alpha)
COMBINE_MODE_SRC_CHANNEL_IDS = ("rgb", "1-rgb", "alpha", "1-alpha")


def __set_texmap_properties(tex_map, texture, stage, tex_xforms):

    tex_map.border_color = tuple(texture.border_color)
    wrap_ids = {k: v for k, v in zip(WRAP_MODES, WRAP_MODE_IDS)}
    wrap_u_mode = texture.wrap_u
    wrap_v_mode = texture.wrap_v
    tex_map.lock_wrap_modes(False)
    tex_map.wrap_u = wrap_ids[wrap_u_mode]
    tex_map.wrap_v = wrap_ids[wrap_v_mode]
    tex_map.lock_wrap_modes(wrap_u_mode == wrap_v_mode)
    filter_ids = {k: v for k, v in zip(FILTER_TYPES, FILTER_TYPE_IDS)}
    tex_map.minfilter = filter_ids[texture.minfilter]
    tex_map.magfilter = filter_ids[texture.magfilter]
    tex_map.anisotropic_degree = texture.anisotropic_degree

    if stage in tex_xforms:
        transform = tex_xforms[stage]
        tex_offset_u, tex_offset_v = transform.get_pos2d()
        tex_rotate = transform.get_rotate2d()
        tex_scale_u, tex_scale_v = transform.get_scale2d()
        tex_map.set_transform("offset", 0, tex_offset_u)
        tex_map.set_transform("offset", 1, tex_offset_v)
        tex_map.set_transform("rotate", 0, tex_rotate)
        tex_map.set_transform("scale", 0, tex_scale_u)
        tex_map.set_transform("scale", 1, tex_scale_v)


def __set_layer_properties(layer, stage, tex_attrib, off_stages, tex_xforms):

    if stage in off_stages:
        layer.active = False

    texture = tex_attrib.get_on_texture(stage)

    if texture:
        rgb_filename = texture.get_fullpath().to_os_specific()
        alpha_filename = texture.get_alpha_fullpath().to_os_specific()
        layer.set_texture(rgb_filename, alpha_filename)
        __set_texmap_properties(layer, texture, stage, tex_xforms)

    layer.sort = stage.sort
    layer.priority = stage.priority

    mode = stage.mode

    if mode == TS.M_combine:

        layer.blend_mode = "modulate"

        cmbmode_data = {}
        cmbmode_data["channels"] = "rgb"
        mode_ids = list(COMBINE_MODE_IDS)
        combine_ids = {k: v for k, v in zip(COMBINE_MODES, COMBINE_MODE_IDS)}
        combine_ids[TS.CM_undefined] = "modulate"

        for channels in ("rgb", "alpha"):

            cmbmode_data[channels] = data = {}
            data["source_index"] = 0
            data["sources"] = sources = {}

            for mode_id in mode_ids:
                sources[mode_id] = [["texture", channels]]

        combine_rgb_mode = stage.get_combine_rgb_mode()
        combine_alpha_mode = stage.get_combine_alpha_mode()
        combine_rgb_mode_id = combine_ids[combine_rgb_mode]
        combine_alpha_mode_id = combine_ids[combine_alpha_mode]
        cmbmode_data["rgb"]["on"] = combine_rgb_mode != TS.CM_undefined
        cmbmode_data["alpha"]["on"] = combine_alpha_mode != TS.CM_undefined
        cmbmode_data["rgb"]["mode"] = combine_rgb_mode_id
        cmbmode_data["alpha"]["mode"] = combine_alpha_mode_id

        mode_ids.remove("replace")

        for channels in ("rgb", "alpha"):

            sources = cmbmode_data[channels]["sources"]

            for mode_id in mode_ids:
                sources[mode_id].append(["previous_layer", channels])

            sources["interpolate"].append(["last_stored_layer", channels])

        combine_src_ids = {k: v for k, v in zip(COMBINE_MODE_SOURCES, COMBINE_MODE_SOURCE_IDS)}
        combine_src_chnl_ids = {k: v for k, v in zip(COMBINE_MODE_SRC_CHANNELS,
                                COMBINE_MODE_SRC_CHANNEL_IDS)}

        source_ids = cmbmode_data["rgb"]["sources"][combine_rgb_mode_id]
        src_count = len(source_ids)

        if combine_rgb_mode != TS.CM_undefined:

            source = stage.get_combine_rgb_source0()
            source_channel = stage.get_combine_rgb_operand0()
            source_ids[0][0] = combine_src_ids[source]
            source_ids[0][1] = combine_src_chnl_ids[source_channel]

            if src_count > 1:
                source = stage.get_combine_rgb_source1()
                source_channel = stage.get_combine_rgb_operand1()
                source_ids[1][0] = combine_src_ids[source]
                source_ids[1][1] = combine_src_chnl_ids[source_channel]

            if src_count > 2:
                source = stage.get_combine_rgb_source2()
                source_channel = stage.get_combine_rgb_operand2()
                source_ids[2][0] = combine_src_ids[source]
                source_ids[2][1] = combine_src_chnl_ids[source_channel]

        if combine_alpha_mode != TS.CM_undefined:

            source_ids = cmbmode_data["alpha"]["sources"][combine_alpha_mode_id]
            src_count = len(source_ids)

            source = stage.get_combine_alpha_source0()
            source_channel = stage.get_combine_alpha_operand0()
            source_ids[0][0] = combine_src_ids[source]
            source_ids[0][1] = combine_src_chnl_ids[source_channel]

            if src_count > 1:
                source = stage.get_combine_alpha_source1()
                source_channel = stage.get_combine_alpha_operand1()
                source_ids[1][0] = combine_src_ids[source]
                source_ids[1][1] = combine_src_chnl_ids[source_channel]

            if src_count > 2:
                source = stage.get_combine_alpha_source2()
                source_channel = stage.get_combine_alpha_operand2()
                source_ids[2][0] = combine_src_ids[source]
                source_ids[2][1] = combine_src_chnl_ids[source_channel]

        layer.set_combine_mode_data(cmbmode_data)
        layer.stored = stage.saved_result
        layer.rgb_scale = stage.rgb_scale
        layer.alpha_scale = stage.alpha_scale
        layer.color = tuple(stage.color)

    elif mode in BLEND_MODES:

        layer.blend_mode = BLEND_MODE_IDS[BLEND_MODES.index(mode)]


def render_state_to_material(render_state, geom_vertex_format, other_materials=None):

    default_uv_set_name = InternalName.get_texcoord()
    uv_set_list = [default_uv_set_name]
    uv_set_list += [InternalName.get_texcoord_name(str(i)) for i in range(1, 8)]
    uv_set_names = {}

    src_uv_set_names = list(geom_vertex_format.get_texcoords())
    uv_set_list_tmp = uv_set_list[:]

    for uv_set_name in uv_set_list:
        if uv_set_name in src_uv_set_names:
            uv_set_list_tmp.remove(uv_set_name)
            src_uv_set_names.remove(uv_set_name)
            uv_set_names[uv_set_name] = uv_set_name

    for src_uv_set_name, dest_uv_set_name in zip(src_uv_set_names, uv_set_list_tmp):
        uv_set_names[src_uv_set_name] = dest_uv_set_name

    if render_state.is_empty():

        create_material = False

    else:

        if render_state.has_attrib(ColorAttrib):
            color_attrib = render_state.get_attrib(ColorAttrib)
        else:
            color_attrib = ColorAttrib.make_off()

        if render_state.has_attrib(ColorScaleAttrib):
            color_scale_attrib = render_state.get_attrib(ColorScaleAttrib)
        else:
            color_scale_attrib = ColorScaleAttrib.make_off()

        if render_state.has_attrib(MaterialAttrib):
            mat_attrib = render_state.get_attrib(MaterialAttrib)
        else:
            mat_attrib = MaterialAttrib.make_off()

        if render_state.has_attrib(TextureAttrib):
            tex_attrib = render_state.get_attrib(TextureAttrib)
        else:
            tex_attrib = TextureAttrib.make_off()

        if render_state.has_attrib(TransparencyAttrib):
            transp_attrib = render_state.get_attrib(TransparencyAttrib)
        else:
            transp_attrib = TransparencyAttrib.make(TransparencyAttrib.M_none)

        if (color_attrib.get_color_type() == ColorAttrib.T_off
                and color_scale_attrib.is_off() and mat_attrib.is_off()
                and tex_attrib.is_off()
                and transp_attrib.mode == TransparencyAttrib.M_none):
            create_material = False
        else:
            create_material = True

    if create_material:

        material = Mgr.do("create_material")

        if color_attrib.color_type == ColorAttrib.T_vertex:
            material.set_property("show_vert_colors", True)
        elif color_attrib.color_type == ColorAttrib.T_flat:
            color = color_attrib.color
            material.set_property("flat_color", tuple(color))

        if not mat_attrib.is_off():

            m = mat_attrib.material
            diffuse = {"value": tuple(m.get_diffuse()), "on": m.has_diffuse()}
            ambient = {"value": tuple(m.get_ambient()), "on": m.has_ambient()}
            emissive = {"value": tuple(m.get_emission()), "on": m.has_emission()}
            specular = {"value": tuple(m.get_specular()), "on": m.has_specular()}
            shininess = {"value": m.get_shininess(), "on": True}

            material.set_property("diffuse", diffuse)
            material.set_property("ambient", ambient)
            material.set_property("emissive", emissive)
            material.set_property("specular", specular)
            material.set_property("shininess", shininess)

        alpha_value = color_scale_attrib.get_scale()[3]
        alpha_on = transp_attrib.mode != TransparencyAttrib.M_none
        alpha = {"value": alpha_value, "on": alpha_on}
        material.set_property("alpha", alpha)

        if not tex_attrib.is_off():

            colormap_stages = []
            layer_stages = []
            fxmap_stages = []
            off_stages = tex_attrib.get_off_stages()
            all_stages = off_stages + tex_attrib.get_on_stages()
            tex_xforms = {}

            if render_state.has_attrib(TexMatrixAttrib):

                tex_matrix_attrib = render_state.get_attrib(TexMatrixAttrib)

                for stage in tex_matrix_attrib.get_stages():
                    tex_xforms[stage] = tex_matrix_attrib.get_transform(stage)

            for stage in all_stages:

                mode = stage.mode

                if mode == TS.M_modulate:
                    colormap_stages.append(stage)
                elif mode == TS.M_combine or mode in BLEND_MODES:
                    layer_stages.append(stage)
                elif mode in FXMAP_TYPES:
                    fxmap_stages.append(stage)

            if not layer_stages and len(colormap_stages) == 1:

                stage = colormap_stages[0]
                uv_set_name = stage.texcoord_name

                if uv_set_name != default_uv_set_name:

                    if uv_set_names[uv_set_name] != default_uv_set_name:

                        uv_name = uv_set_names[uv_set_name]

                        for src_uv_name, dest_uv_name in uv_set_names.items():
                            if dest_uv_name == default_uv_set_name:
                                uv_set_names[src_uv_name] = uv_name
                                break

                        uv_set_names[uv_set_name] = default_uv_set_name

                texture = tex_attrib.get_on_texture(stage)

                if texture:
                    map_data = {}
                    map_data["map_type"] = "color"
                    rgb_filename = texture.get_fullpath().to_os_specific()
                    alpha_filename = texture.get_alpha_fullpath().to_os_specific()
                    map_data["rgb_filename"] = rgb_filename
                    map_data["alpha_filename"] = alpha_filename
                    material.set_texture(map_data)
                    tex_map = material.get_tex_map("color")
                    __set_texmap_properties(tex_map, texture, stage, tex_xforms)
                else:
                    material.set_map_active("color", active=False)

            elif colormap_stages:

                layer_stages.extend(colormap_stages)

            fxmap_ids = {k: v for k, v in zip(FXMAP_TYPES, FXMAP_IDS)}

            for stage in fxmap_stages:

                texture = tex_attrib.get_on_texture(stage)

                if texture:
                    map_data = {}
                    map_type = fxmap_ids[stage.mode]
                    map_data["map_type"] = map_type
                    rgb_filename = texture.get_fullpath().to_os_specific()
                    alpha_filename = texture.get_alpha_fullpath().to_os_specific()
                    map_data["rgb_filename"] = rgb_filename
                    map_data["alpha_filename"] = alpha_filename
                    material.set_texture(map_data)
                    material.set_map_active(map_type)
                    tex_map = material.get_tex_map(map_type)
                    __set_texmap_properties(tex_map, texture, stage, tex_xforms)

            if layer_stages:

                material.use_layers(True)
                stages_by_uv_set = {}

                for stage in layer_stages:
                    uv_set_name = stage.texcoord_name
                    stages_by_uv_set.setdefault(uv_set_name, []).append(stage)

                # limit the number of texture coordinate sets to 8
                if len(stages_by_uv_set) > 8:

                    uv_sets_by_priority = []

                    for uv_set_name, stages in stages_by_uv_set.items():
                        # check the highest priority of all texture stages
                        # that use a particular texture coordinate set
                        priority = max(stage.priority for stage in stages)
                        uv_sets_by_priority.append((priority, uv_set_name))

                    uv_sets_by_priority.sort(reverse=True)
                    del uv_sets_by_priority[:8]

                    # low-priority texture stages that use the remaining texture
                    # coordinate sets will not be used
                    for priority, uv_set_name in uv_sets_by_priority:

                        for stage in stages_by_uv_set[uv_set_name]:
                            layer_stages.remove(stage)

                        del stages_by_uv_set[uv_set_name]

                # sort stages

                d = {}

                for stage in layer_stages:
                    d.setdefault(stage.sort, []).append(stage)

                layer_stages = []

                for sort in sorted(d):
                    layer_stages.extend(d[sort])

                # give the stages consecutive sort values
                for i, stage in enumerate(layer_stages):
                    stage.sort = i

                src_uv_set_names = set(stages_by_uv_set)
                dest_uv_set_names = set(uv_set_list[:len(stages_by_uv_set)])
                common = src_uv_set_names & dest_uv_set_names
                stage = layer_stages.pop(0)
                layer = material.get_layer()
                layer.name = Mgr.get("unique_tex_layer_name", material, stage.name, layer)
                src_uv_name = stage.texcoord_name
                uv_set_name = src_uv_name if src_uv_name in common else uv_set_names[src_uv_name]
                material.set_layer_uv_set_id(layer, uv_set_list.index(uv_set_name))
                __set_layer_properties(layer, stage, tex_attrib, off_stages, tex_xforms)

                for stage in layer_stages:
                    layer = Mgr.do("create_tex_layer", material)
                    layer.name = Mgr.get("unique_tex_layer_name", material, stage.name)
                    src_uv_name = stage.texcoord_name
                    uv_set_name = src_uv_name if src_uv_name in common else uv_set_names[src_uv_name]
                    layer.uv_set_id = uv_set_list.index(uv_set_name)
                    __set_layer_properties(layer, stage, tex_attrib, off_stages, tex_xforms)
                    material.add_layer(layer)

        else:

            material.set_map_active("color", active=False)

        if other_materials:
            for other_material in other_materials:
                if material.equals(other_material):
                    Mgr.do("unregister_material", material)
                    material = other_material
                    break

    else:

        material = None

    names = list(uv_set_names.values())
    uv_set_names.update({name: name for name in uv_set_list if name not in names})

    return material, uv_set_names
