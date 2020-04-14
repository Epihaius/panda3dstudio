from panda3d.core import Shader
from . import (region_sel, region_sel_point, region_sel_subobj, region_sel_normal,
    grid, normal, surface_normal, extrusion_inset, solidify, prim, cone, torus,
    locked_wireframe, snap)


class Shaders:

    region_sel_mask = Shader.make(Shader.SL_GLSL, region_sel.VERT_SHADER_MASK,
        region_sel.FRAG_SHADER_MASK)
    grid = Shader.make(Shader.SL_GLSL, grid.VERT_SHADER, grid.FRAG_SHADER,
        grid.GEOM_SHADER)
    normal = Shader.make(Shader.SL_GLSL, normal.VERT_SHADER, normal.FRAG_SHADER,
        normal.GEOM_SHADER)
    surface_normal = Shader.make(Shader.SL_GLSL, surface_normal.VERT_SHADER,
        surface_normal.FRAG_SHADER)
    extrusion_inset = Shader.make(Shader.SL_GLSL, extrusion_inset.VERT_SHADER,
        extrusion_inset.FRAG_SHADER, extrusion_inset.GEOM_SHADER)
    solidify = Shader.make(Shader.SL_GLSL, solidify.VERT_SHADER, solidify.FRAG_SHADER,
        solidify.GEOM_SHADER)
    cone_shaded = Shader.make(Shader.SL_GLSL, cone.VERT_SHADER, prim.FRAG_SHADER,
        cone.GEOM_SHADER)
    cone_wire = Shader.make(Shader.SL_GLSL, cone.VERT_SHADER_WIRE,
        locked_wireframe.FRAG_SHADER, locked_wireframe.GEOM_SHADER)
    torus_shaded = Shader.make(Shader.SL_GLSL, torus.VERT_SHADER, prim.FRAG_SHADER)
    torus_wire = Shader.make(Shader.SL_GLSL, torus.VERT_SHADER_WIRE,
        locked_wireframe.FRAG_SHADER, locked_wireframe.GEOM_SHADER)
    locked_wireframe = Shader.make(Shader.SL_GLSL, locked_wireframe.VERT_SHADER,
        locked_wireframe.FRAG_SHADER, locked_wireframe.GEOM_SHADER)
    snap = {
        "vert": Shader.make(Shader.SL_GLSL, snap.VERT_SHADER_V, snap.FRAG_SHADER,
            snap.GEOM_SHADER_V),
        "edge": Shader.make(Shader.SL_GLSL, snap.VERT_SHADER_E, snap.FRAG_SHADER,
            snap.GEOM_SHADER_E),
        "poly": Shader.make(Shader.SL_GLSL, snap.VERT_SHADER_P, snap.FRAG_SHADER,
            snap.GEOM_SHADER_P)
    }
