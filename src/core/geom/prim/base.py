from ..base import *

FRAG_SHADER = """
    #version 150 compatibility

    uniform sampler2D p3d_Texture0;
    uniform struct PandaMaterial {
        vec4 ambient;
        vec4 diffuse;
        vec4 emission;
        vec3 specular;
        float shininess;
    } p3d_Material;

    uniform struct {
        vec4 ambient;
    } p3d_LightModel;

    in vec4 flat_color;
    in vec3 mynormal;
    in vec3 v;
    in vec2 texcoord;

    #define MAX_LIGHTS 1 // to be modified when needed

    // https://en.wikibooks.org/wiki/GLSL_Programming/Blender/Diffuse_Reflection

    void main() {

        vec3 texcolor = texture(p3d_Texture0, texcoord).rgb;
        vec3 EyeDir = normalize(-v); // we are in Eye Coordinates, so EyePos is (0., 0., 0.)
        float attenuation;

        // Lights
        vec3 lightcolor = vec3(0., 0., 0.);

        // Ambient
        lightcolor += vec3(p3d_LightModel.ambient * p3d_Material.ambient);

        // Emission
        lightcolor += vec3(p3d_Material.emission);

        for (int lm=0; lm<MAX_LIGHTS; lm++)
        {

            vec3 LightDir = vec3(0., 0., 0.);

            if (gl_LightSource[lm].position.w == 0.) // Directional light?
            {
                LightDir = normalize(vec3(gl_LightSource[lm].position.xyz));
                attenuation = 1.; // no attenuation with Dir Light
            }
            else // point or spot light?
            {
                LightDir = normalize(gl_LightSource[lm].position.xyz - v);
                // Diffuse and Specular Attenuation for point and spotlight
                attenuation = 1. / (gl_LightSource[lm].constantAttenuation
                                    + gl_LightSource[lm].linearAttenuation * length(LightDir)
                                    + gl_LightSource[lm].quadraticAttenuation
                                        * length(LightDir) * length(LightDir));
                if (gl_LightSource[lm].spotCutoff <= 90.) // spotlight?
                {
                    float clampedCosine = max(0., dot(-LightDir, gl_LightSource[lm].spotDirection));
                    if (clampedCosine < gl_LightSource[lm].spotCosCutoff)
                    // outside of spotlight cone?
                    {
                        attenuation = 0.;
                    }
                    else
                    {
                        attenuation = attenuation * pow(clampedCosine, gl_LightSource[lm].spotExponent);
                    }
                }
            }

            vec3 ReflectDir = normalize(-reflect(LightDir, mynormal));

            // Diffuse
            float NdotL = dot(normalize(mynormal), LightDir);
            vec3 diffuseandspec = clamp(p3d_Material.diffuse.rgb * gl_LightSource[lm].diffuse.rgb
                                        * NdotL, 0., 1.);

            // Specular
            vec4 specular = vec4(p3d_Material.specular, 1) * gl_LightSource[lm].specular
                            * pow(max(dot(ReflectDir, EyeDir), 0), p3d_Material.shininess);
            specular = clamp(specular, 0., 1.);
            diffuseandspec += specular.xyz;

            diffuseandspec *= attenuation;
            diffuseandspec = clamp(diffuseandspec, 0., 1.);
            lightcolor += diffuseandspec;
        }

        // TexColor combined with LightColor
        texcolor *= lightcolor;

        // Final Color
        gl_FragColor = vec4(texcolor, 1.) * flat_color;

    }
"""


class PrimitiveManager(BaseObject, CreationPhaseManager, ObjPropDefaultsManager):

    def __init__(self, prim_type):

        CreationPhaseManager.__init__(self, prim_type, has_color=True)
        ObjPropDefaultsManager.__init__(self, prim_type)

    def setup(self, creation_phases, status_text):

        sort = PendingTasks.get_sort("clear_geom_data", "object")

        if sort is None:
            PendingTasks.add_task_id("clear_geom_data", "object", 1)
            PendingTasks.add_task_id("set_geom_data", "object", 2)
            PendingTasks.add_task_id("make_editable", "object", 3)

        phase_starter, phase_handler = creation_phases.pop(0)
        creation_starter = self.__get_prim_creation_starter(phase_starter)
        creation_phases.insert(0, (creation_starter, phase_handler))

        return CreationPhaseManager.setup(self, creation_phases, status_text)

    def __get_prim_creation_starter(self, main_creation_func):

        def start_primitive_creation():

            model_id = self.generate_object_id()
            name = Mgr.get("next_obj_name", self.get_object_type())
            model = Mgr.do("create_model", model_id, name, self.get_origin_pos())
            next_color = self.get_next_object_color()
            model.set_color(next_color, update_app=False)
            prim = self.init_primitive(model)
            self.init_object(prim)
            model.set_geom_object(prim)

            main_creation_func()

        return start_primitive_creation

    def get_primitive(self):

        return self.get_object()

    def init_primitive(self, model):
        """ Override in derived class """

        return None

    def apply_default_size(self, prim):
        """ Override in derived class """

        pass

    def create_instantly(self, origin_pos):

        model_id = self.generate_object_id()
        obj_type = self.get_object_type()
        name = Mgr.get("next_obj_name", obj_type)
        model = Mgr.do("create_model", model_id, name, origin_pos)
        next_color = self.get_next_object_color()
        model.set_color(next_color, update_app=False)
        prim = self.init_primitive(model)
        self.apply_default_size(prim)
        prim.get_geom_data_object().finalize_geometry()
        model.set_geom_object(prim)
        Mgr.update_remotely("next_obj_name", Mgr.get("next_obj_name", obj_type))
        self.set_next_object_color()
        # make undo/redoable
        self.add_history(model)


class Primitive(GeomDataOwner):

    def __init__(self, prim_type, model, type_prop_ids):

        GeomDataOwner.__init__(self, [], type_prop_ids, model)

        self._type = prim_type
        # the following "initial coordinates" correspond to the vertex positions
        # at the time the geometry is created or recreated; it is kept around to
        # facilitate reshaping the primitive (when "baking" the new size into
        # the vertices or computing the new vertex positions)
        self._initial_coords = {}

    def define_geom_data(self):
        """
        Define the geometry of the primitive; the vertex properties and how those
        vertices are combined into triangles and polygons.

        Override in derived class.

        """

        pass

    def update(self, data):
        """
        Update the primitive with the given data.

        Override in derived class.

        """

        pass

    def create(self):

        geom_data_obj = Mgr.do("create_geom_data", self)
        self.set_geom_data_object(geom_data_obj)
        geom_data = self.define_geom_data()
        data = geom_data_obj.process_geom_data(geom_data)
        self.update(data)
        geom_data_obj.create_geometry(self._type)

    def recreate_geometry(self):

        obj_id = self.get_toplevel_object().get_id()
        task = self.get_geom_data_object().clear_subobjects
        task_id = "clear_geom_data"
        PendingTasks.add(task, task_id, "object", id_prefix=obj_id)
        Mgr.do("update_picking_col_id_ranges")

        def task():

            geom_data_obj = self.get_geom_data_object()
            geom_data = self.define_geom_data()
            data = geom_data_obj.process_geom_data(geom_data)
            self.update(data)
            geom_data_obj.create_subobjects(rebuild=True)
            self.update_initial_coords()
            self.finalize()

        task_id = "set_geom_data"
        PendingTasks.add(task, task_id, "object", id_prefix=obj_id)

        self.get_model().update_group_bbox()

    def is_valid(self):

        return False

    def get_type(self):

        return self._type

    def update_initial_coords(self):

        self._initial_coords = self.get_geom_data_object().get_vertex_coords()

    def reset_initial_coords(self):

        self.get_geom_data_object().set_vertex_coords(self._initial_coords)

    def restore_initial_coords(self, coords):

        self._initial_coords = coords

    def get_initial_coords(self):

        return self._initial_coords

    def get_initial_pos(self, vertex_id):

        return self._initial_coords[vertex_id]

    def set_origin(self, origin):

        self.get_geom_data_object().set_origin(origin)

    def get_origin(self):

        geom_data_obj = self.get_geom_data_object()

        if geom_data_obj:
            return geom_data_obj.get_origin()

    def finalize(self, update_poly_centers=True):

        self.get_geom_data_object().finalize_geometry(update_poly_centers)

    def set_property(self, prop_id, value, restore=""):

        if prop_id == "editable state":

            obj_type = "editable_geom"
            geom_data_obj = self.get_geom_data_object()
            Mgr.do("create_%s" % obj_type, self.get_model(), geom_data_obj)
            Mgr.update_remotely("selected_obj_types", (obj_type,))

            return True

        else:

            return self.get_geom_data_object().set_property(prop_id, value, restore)

    def get_property_to_store(self, prop_id, event_type=""):

        data = {prop_id: {"main": self.get_property(prop_id)}}

        return data

    def restore_property(self, prop_id, restore_type, old_time_id, new_time_id):

        obj_id = self.get_toplevel_object().get_id()
        val = Mgr.do("load_last_from_history", obj_id, prop_id, new_time_id)
        self.set_property(prop_id, val, restore_type)
