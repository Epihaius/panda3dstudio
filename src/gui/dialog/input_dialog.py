from .dialog import *


class InputDialogField(DialogInputField):

    def __init__(self, parent, width, on_key_enter=None, on_key_escape=None):

        DialogInputField.__init__(self, parent, "input", "string", None, width,
                                  on_key_enter=on_key_enter, on_key_escape=on_key_escape)


class InputDialog(Dialog):

    def __init__(self, title="", message="", default_input="", choices="okcancel",
                 ok_alias="OK", on_yes=None, on_no=None, on_cancel=None):

        def command():

            if on_yes:
                on_yes(self._input)

        Dialog.__init__(self, title, choices, ok_alias, command, on_no, on_cancel)

        self._input = default_input
        client_sizer = self.get_client_sizer()
        borders = (50, 50, 30, 30)
        text = DialogMessageText(self, message)
        client_sizer.add(text, borders=borders, alignment="center_h")
        on_key_enter = lambda: self.close(answer="yes")
        field = InputDialogField(self, 100, on_key_enter=on_key_enter, on_key_escape=self.close)
        field.set_input_parser(self.__parse_input)
        borders = (50, 50, 30, 0)
        client_sizer.add(field, borders=borders, expand=True)

        self.finalize()

        field.set_text(default_input)
        field.on_left_down()
        field._on_left_up()

    def __parse_input(self, input_text):

        self._input = input_text.strip()

        return self._input
