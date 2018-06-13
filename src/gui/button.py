from .base import *
from .tooltip import ToolTip


class Button(Widget):

    _btns = {}

    def set_hotkey(self, hotkey=None, interface_id="main"):

        btns = self._btns.setdefault(interface_id, {})

        if self._hotkey in btns:
            del btns[self._hotkey]

        if hotkey:
            btns[hotkey] = self

        self._hotkey = hotkey
        self._interface_id = interface_id

    def enable_hotkey(self, enable=True):

        hotkey = self._hotkey

        if hotkey is None:
            return

        btns = self._btns.get(self._interface_id, {})

        if enable:
            btns[hotkey] = self
        elif hotkey in btns:
            del btns[hotkey]

    @classmethod
    def handle_hotkey(cls, hotkey, is_repeat, interface_id="main"):

        btns = cls._btns.get(interface_id, {})

        if hotkey in btns:

            btn = btns[hotkey]

            if not is_repeat:
                btn.press()

            return True

        return False

    def __init__(self, parent, gfx_data, text="", icon_id="", tooltip_text="", command=None,
                 text_alignment="center", icon_alignment="center", button_type="",
                 stretch_dir="horizontal"):

        if gfx_data["normal"] and gfx_data["normal"][0][0] not in TextureAtlas["regions"]:
            gfx_data["normal"] = ()

        if "disabled" in gfx_data:
            if gfx_data["disabled"][0][0] not in TextureAtlas["regions"]:
                del gfx_data["disabled"]

        Widget.__init__(self, "button", parent, gfx_data, initial_state="normal",
                        stretch_dir=stretch_dir)

        self._hotkey = None
        self._interface_id = ""
        self._text = text
        self._button_type = button_type
        self._group = None

        if text:
            skin_text = Skin["text"][button_type]
            font = skin_text["font"]
            color = skin_text["color"]
            self._label = label = font.create_image(text, color)
            color = Skin["colors"]["disabled_{}_text".format(button_type)]
            self._label_disabled = font.create_image(text, color)
            self.set_size((label.get_x_size(), 0), includes_borders=False, is_min=True)
        else:
            self._label = self._label_disabled = None

        if icon_id:

            width, height = self.get_min_size()

            if width < height:
                self.set_size((height, height), is_min=True)

            x, y, w, h = TextureAtlas["regions"][icon_id]
            img = PNMImage(w, h, 4)
            img.copy_sub_image(TextureAtlas["image"], 0, 0, x, y, w, h)
            self._icon = img
            self._icon_disabled = icon_disabled = PNMImage(img)
            icon_disabled.make_grayscale()
            icon_disabled -= LColorf(0., 0., 0., .25)
            icon_disabled.make_rgb()

        else:

            self._icon = self._icon_disabled = None

        self._text_alignment = text_alignment
        self._icon_alignment = icon_alignment
        self._is_pressed = False
        self._has_mouse = False
        self._is_active = False
        self._delay_card_update = False
        self._command = command if command else lambda: None

        if tooltip_text:
            self._tooltip_label = ToolTip.create_label(tooltip_text)
        else:
            self._tooltip_label = None

    def destroy(self):

        Widget.destroy(self)

        if self._tooltip_label:
            ToolTip.hide()

        if self._group:
            self._group.destroy()
            self._group = None

        self._command = lambda: None

    def set_group(self, group):

        self._group = group

    def set_text(self, text=""):

        if self._text == text:
            return False

        self._text = text

        if text:
            skin_text = Skin["text"][self._button_type]
            font = skin_text["font"]
            color = skin_text["color"]
            self._label = label = font.create_image(text, color)
            color = Skin["colors"]["disabled_{}_text".format(self._button_type)]
            self._label_disabled = font.create_image(text, color)
            width = label.get_x_size()
            height = label.get_y_size()
            self.set_size((width, height), includes_borders=False, is_min=True)
        else:
            self._label = self._label_disabled = None
            self.set_size((0, 0), is_min=True)

        return True

    def set_command(self, command):

        self._command = command if command else lambda: None

    def get_command(self):

        return self._command

    def get_label(self):

        return self._label

    def get_image(self, state=None, composed=True):

        width, height = self.get_size()
        image = Widget.get_image(self, state, composed)

        if not image:
            image = PNMImage(width, height, 4)

        l, r, b, t = self.get_gfx_inner_borders()

        if self._text:

            if not self.is_enabled():
                label = self._label_disabled
            else:
                label = self._label

            w = label.get_x_size()
            h = label.get_y_size()

            if self._text_alignment == "center":
                x = (l + width - r - w) // 2
            elif self._text_alignment == "right":
                x = width - r - w
            else:
                x = l

            y = (height - h) // 2 + 1

            image.blend_sub_image(label, x, y, 0, 0)

        if self._icon:

            if not self.is_enabled():
                icon = self._icon_disabled
            else:
                icon = self._icon

            w = icon.get_x_size()
            h = icon.get_y_size()

            if self._icon_alignment == "center":
                x = (width - w) // 2
            elif self._icon_alignment == "right":
                x = width - w
            else:
                x = 0

            x = (width - w) // 2
            y = (height - h) // 2

            image.blend_sub_image(icon, x, y, 0, 0)

        return image

    def delay_card_update(self, delay=True):

        self._delay_card_update = delay

    def is_card_update_delayed(self):

        return self._delay_card_update

    def __card_update_task(self):

        prev_state = self.get_state()
        active_state = "active" if self.has_state("active") else ""
        pressed_state = "pressed" if self.has_state("pressed") else ""
        hilited_state = "hilited" if self.has_state("hilited") else ""
        disabled_state = "disabled" if self.has_state("disabled") else "normal"
        state = ((pressed_state if pressed_state and self._is_pressed else
                 (active_state if active_state and self._is_active else
                 (hilited_state if hilited_state and self._has_mouse else "normal")))
                 if self.is_enabled() else disabled_state)
        self.set_state(state)
        image = self.get_image(composed=False)

        if not image:
            self.set_state(prev_state)
            return

        parent = self.get_parent()

        if not parent or self.is_hidden():
            return

        x, y = self.get_pos()
        w, h = self.get_size()
        img = PNMImage(w, h, 4)
        parent_img = parent.get_image(composed=False)

        if parent_img:
            img.copy_sub_image(parent_img, 0, 0, x, y, w, h)

        img.blend_sub_image(image, 0, 0, 0, 0)
        self.get_card().copy_sub_image(self, img, w, h)

    def __update_card_image(self):

        task = self.__card_update_task

        if self._delay_card_update:
            task_id = "update_card_image"
            PendingTasks.add(task, task_id, sort=1, id_prefix=self.get_widget_id(),
                             batch_id="widget_card_update")
        else:
            task()

    def on_enter(self):

        self._has_mouse = True
        self.__update_card_image()

        if self._tooltip_label:
            ToolTip.show(self._tooltip_label)

    def on_leave(self, force=False):

        if not (force or self._has_mouse):
            return False

        self._is_pressed = False
        self._has_mouse = False
        self.__update_card_image()

        if self._tooltip_label:
            ToolTip.hide()

        return True

    def on_left_down(self):

        self._is_pressed = True
        self.__update_card_image()

    def on_left_up(self):

        if self._is_pressed:
            self._is_pressed = False
            self.__update_card_image()
            self._command()
            return True

        return False

    def set_pressed(self, pressed=True):

        self._is_pressed = pressed

    def is_pressed(self):

        return self._is_pressed

    def press(self):

        self._command()

    def set_tooltip_text(self, text):

        if text:
            self._tooltip_label = ToolTip.create_label(text)
        else:
            self._tooltip_label = None

        if self.get_mouse_watcher().get_over_region() == self.get_mouse_region():
            ToolTip.update(self._tooltip_label) if self._tooltip_label else ToolTip.hide()

    def set_active(self, is_active=True):

        if self._is_active == is_active:
            return False

        self._is_active = is_active
        self.__update_card_image()

        return True

    def is_active(self):

        return self._is_active

    def hide(self, recurse=True):

        if Widget.hide(self, recurse):
            active_state = "active" if self.has_state("active") else "normal"
            disabled_state = "disabled" if self.has_state("disabled") else "normal"
            state = ((active_state if self._is_active else "normal") if self.is_enabled()
                     else disabled_state)
            self.set_state(state)
            self._is_pressed = False

    def enable(self, enable=True, check_group_disablers=True):

        if enable and not self.is_always_enabled() and self._group and check_group_disablers:
            for disabler in self._group.get_disablers().values():
                if disabler():
                    return False

        if not Widget.enable(self, enable):
            return False

        if not enable:
            self._is_active = False

        self.enable_hotkey(enable)
        self.__update_card_image()

        return True


class ButtonGroup(object):

    def __init__(self):

        self._btns = {}
        self._disablers = {}

    def destroy(self):

        if not self._btns:
            return False

        self._btns.clear()
        self._disablers.clear()

        return True

    def add_button(self, button, button_id):

        self._btns[button_id] = button
        button.set_group(self)

    def get_buttons(self):

        return list(self._btns.values())

    def get_button(self, btn_id):

        return self._btns[btn_id]

    def add_disabler(self, disabler_id, disabler):

        self._disablers[disabler_id] = disabler

    def remove_disabler(self, disabler_id):

        del self._disablers[disabler_id]

    def get_disablers(self):

        return self._disablers

    def enable(self, enable=True):

        if enable:
            for disabler in self._disablers.values():
                if disabler():
                    return False

        for btn in self._btns.values():
            btn.enable(enable, check_group_disablers=False)

        return True


class ToggleButtonGroup(ButtonGroup):

    def __init__(self):

        ButtonGroup.__init__(self)

        self._default_toggle_id = None
        self._toggle_id = ""

        self._activators = {"": lambda: None}
        self._deactivators = {"": lambda: None}

    def destroy(self):

        if not ButtonGroup.destroy(self):
            return

        self._activators.clear()
        self._deactivators.clear()

    def __toggle(self, toggle_id):

        if toggle_id == self._toggle_id:
            if self._default_toggle_id is not None:
                self._deactivators[toggle_id]()
                self._activators[self._default_toggle_id]()
                self._toggle_id = self._default_toggle_id
        else:
            self._deactivators[self._toggle_id]()
            self._activators[toggle_id]()
            self._toggle_id = toggle_id

    def set_default_toggle(self, toggle_id, toggle):

        self._default_toggle_id = self._toggle_id = toggle_id
        self._activators[toggle_id], self._deactivators[toggle_id] = toggle

    def add_button(self, button, toggle_id, toggle):

        ButtonGroup.add_button(self, button, toggle_id)

        button.set_command(lambda: self.__toggle(toggle_id))
        self._activators[toggle_id], self._deactivators[toggle_id] = toggle

    def deactivate(self):

        for btn in self.get_buttons():
            btn.set_active(False)

        if self._default_toggle_id is None:
            default_toggle_id = ""
        else:
            default_toggle_id = self._default_toggle_id

        if self._toggle_id != default_toggle_id:
            self._toggle_id = default_toggle_id

    def set_active_button(self, toggle_id):

        self.deactivate()
        self.get_button(toggle_id).set_active()
        self._toggle_id = toggle_id

    def get_active_button_id(self):

        return self._toggle_id


__all__ = ("Button", "ButtonGroup", "ToggleButtonGroup")
