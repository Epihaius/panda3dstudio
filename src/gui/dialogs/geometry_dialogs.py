from ..base import *
from ..dialog import *


class SurfaceToModelDialog(Dialog):

    def __init__(self):

        Dialog.__init__(self, "", choices="okcancel", on_yes=self.__on_yes)

        widgets = Skin.layout.create(self, "surface_to_model")
        checkbtns = widgets["checkbuttons"]
        radio_btn_groups = widgets["radiobutton_groups"]
        fields = widgets["fields"]

        self._model_basename = ""
        self._creation_method = "per_src"
        self._copy_surfaces = False

        field = fields["name"]
        field.value_id = "name"
        field.value_type = "string"
        field.set_value_handler(self.__handle_name)
        field.set_input_parser(self.__parse_input)

        radio_btns = radio_btn_groups["creation_method"]
        method_ids = ("per_src", "per_surface", "single")

        def set_creation_method(method_id):

            self._creation_method = method_id

        for method_id in method_ids:
            command = lambda m=method_id: set_creation_method(m)
            radio_btns.set_button_command(method_id, command)

        radio_btns.set_selected_button("per_src")

        checkbtn = checkbtns["copy"]
        checkbtn.command = self.__copy_surfaces

        self.finalize()

    def __parse_input(self, input_text):

        self._input = input_text.strip()

        return self._input

    def __handle_name(self, value_id, name, state):

        self._model_basename = name

    def __copy_surfaces(self, copy_surfaces):

        self._copy_surfaces = copy_surfaces

    def __on_yes(self):

        Mgr.update_remotely("poly_surface_to_model", "create", self._model_basename,
                            self._creation_method, self._copy_surfaces)


class GeometryFromModelDialog(Dialog):

    def __init__(self, model_name=None):

        Dialog.__init__(self, "", choices="okcancel", on_yes=self.__on_yes)

        model_descr = "other models" if model_name is None else f'"{model_name}"'
        model_text = "models" if model_name is None else "model"
        text_vars = {"model_descr": model_descr, "model_text": model_text}
        widgets = Skin.layout.create(self, "geometry_from_model", text_vars)
        checkbtns = widgets["checkbuttons"]

        self._delete_src_geometry = True
        self._keep_src_models = False

        checkbtn = checkbtns["delete"]
        checkbtn.command = self.__delete_src_geometry
        checkbtn.check()

        checkbtn = checkbtns["keep"]
        checkbtn.command = self.__keep_src_models

        self.finalize()

    def __delete_src_geometry(self, delete_src_geometry):

        self._delete_src_geometry = delete_src_geometry

    def __keep_src_models(self, keep_src_models):

        self._keep_src_models = keep_src_models

    def __on_yes(self):

        Mgr.update_remotely("geometry_from_model", "add",
            self._delete_src_geometry, self._keep_src_models)
