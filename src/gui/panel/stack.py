from ..base import *


class PanelStackParent(wx.PyPanel, BaseObject, FocusResetter):

    def __init__(self, parent, pos, size, focus_receiver=None, interface_id=""):

        wx.PyPanel.__init__(self, parent, pos=pos, size=size)
        BaseObject.__init__(self, interface_id)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus()
        self.Bind(wx.EVT_RIGHT_DOWN, self.__on_right_down)

    def __on_right_down(self, event):

        self.dispatch_event("panel_right_down", event)


class PanelStackFrame(wx.PyPanel, BaseObject, FocusResetter):

    def __init__(self, parent, pos, size, stack, focus_receiver=None, interface_id=""):

        wx.PyPanel.__init__(self, parent, pos=pos, size=size)
        BaseObject.__init__(self, interface_id)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus(on_click=self.__on_left_down)

        w, h = size
        self._height = h
        self._stack = stack

        image_main = Cache.load(
            "image", os.path.join(GFX_PATH, "panel_main.png"))

        border = {}

        for part in ("topleft", "topright", "bottomright", "bottomleft", "left",
                     "right", "top", "bottom"):

            img = wx.Image(os.path.join(
                GFX_PATH, "panelstack_border_%s.png" % part))

            if not img.HasAlpha():
                img.InitAlpha()

            border[part] = img

        for part in ("topleft", "topright", "bottomright", "bottomleft"):
            border[part] = border[part].ConvertToBitmap()

        corner_l = border["topleft"].GetSize()
        corner_r = border["topright"].GetSize()

        img = border["left"]
        w_border_l = img.GetWidth()
        border["left"] = img.Scale(
            w_border_l, h - corner_l[1] * 2).ConvertToBitmap()
        img = border["right"]
        w_border_r = img.GetWidth()
        border["right"] = img.Scale(
            w_border_r, h - corner_r[1] * 2).ConvertToBitmap()
        img = border["top"]
        h_border_t = img.GetHeight()
        border["top"] = img.Scale(
            w - corner_l[0] - corner_r[0], h_border_t).ConvertToBitmap()
        img = border["bottom"]
        h_border_b = img.GetHeight()
        border["bottom"] = img.Scale(
            w - corner_l[0] - corner_r[0], h_border_b).ConvertToBitmap()

        self._scrollbar_border = w_border_r
        self._scrollbar_offset = corner_r[0] - w_border_r
        self._scrollbar_collapsed = 3
        self._scrollbar_expanded = 20

        self._bitmap_right = image_main.Scale(corner_r[0], h).ConvertToBitmap()
        dc = wx.MemoryDC(self._bitmap_right)
        dc.DrawBitmap(border["topright"], 0, 0)
        dc.DrawBitmap(border["bottomright"], 0, h - corner_r[1])
        dc.DrawBitmap(border["right"], corner_r[0] - w_border_r, corner_r[1])

        self._bitmap = image_main.Scale(w, h).ConvertToBitmap()
        dc.SelectObject(self._bitmap)
        dc.DrawBitmap(border["topleft"], 0, 0)
        dc.DrawBitmap(border["bottomleft"], 0, h - corner_l[1])
        dc.DrawBitmap(border["left"], 0, corner_l[1])
        dc.DrawBitmap(border["top"], corner_l[0], 0)
        dc.DrawBitmap(border["bottom"], corner_l[0], h - h_border_b)
        dc.SelectObject(wx.NullBitmap)

        stack_pos = wx.Point(w_border_l, h_border_t)
        stack_width = w - w_border_l - self._scrollbar_collapsed - w_border_r * 2
        stack_size = wx.Size(stack_width, h - h_border_t - h_border_b)
        self._stack_parent = PanelStackParent(
            self, stack_pos, stack_size, focus_receiver, interface_id)
        img = image_main
        r = img.GetRed(0, 0)
        g = img.GetGreen(0, 0)
        b = img.GetBlue(0, 0)
        self._main_color = wx.Colour(r, g, b)
        self._stack_parent.SetBackgroundColour(self._main_color)
        self._stack_parent.Refresh()

        self._is_enabled = True
        self._has_mouse = False
        self._is_scrollbar_expanded = False
        self._scrollctrls = ("thumb", "arrow_up", "arrow_down", "track")
        self._is_clicked = dict((ctrl, False) for ctrl in self._scrollctrls)
        self._is_hilited = dict((ctrl, False) for ctrl in self._scrollctrls)

        rect_x = w - self._scrollbar_collapsed - w_border_r * 2
        rect_y = h_border_t
        rect_w = self._scrollbar_collapsed + w_border_r * 2
        rect_h = h - h_border_t - h_border_b
        self._mouse_rect = wx.Rect(rect_x, rect_y, rect_w, rect_h)
        rect_x += w_border_r
        rect_w = self._scrollbar_collapsed
        self._scrollctrl_rects = {}
        rect = wx.Rect(rect_x, rect_y, rect_w, rect_h)
        self._scrollctrl_rects["track"] = rect
        rect = wx.Rect(rect_x, rect_y, rect_w, rect_h - rect_w * 2)
        self._scrollctrl_rects["thumb"] = rect
        rect_y += rect_h - self._scrollbar_expanded * 2
        rect_h = self._scrollbar_expanded
        rect = wx.Rect(rect_x, rect_y, rect_w, rect_h)
        self._scrollctrl_rects["arrow_up"] = rect
        x = w - rect_h // 2 - w_border_r
        y = rect_y + rect_h - 8
        self._arrows = {}
        arrow = (wx.Point(x - 6, y), wx.Point(x + 6, y), wx.Point(x, y - 6))
        self._arrows["up"] = arrow
        y += rect_h
        arrow = (wx.Point(x - 5, y - 5),
                 wx.Point(x + 5, y - 5), wx.Point(x, y))
        self._arrows["down"] = arrow
        rect_y += rect_h
        rect = wx.Rect(rect_x, rect_y, rect_w, rect_h)
        self._scrollctrl_rects["arrow_down"] = rect
        rect_x = w - self._scrollbar_expanded - w_border_r * 2 - self._scrollbar_offset
        rect_w = self._scrollbar_expanded + w_border_r * 2
        self._refresh_rect = wx.Rect(rect_x, 0, rect_w, h)
        self._scrollctrl_border_lines = dict(
            (ctrl, []) for ctrl in self._scrollctrls)
        ctrl_colors = {
            "normal": wx.Colour(*[int(c * .95) for c in (r, g, b)]),
            "hilited": wx.Colour(*[int(c * 1.025) for c in (r, g, b)]),
            "pressed": wx.Colour(*[int(c * 1.1) for c in (r, g, b)])
        }
        track_colors = {
            "normal": wx.Colour(*[int(c * .8) for c in (r, g, b)]),
            "hilited": wx.Colour(*[int(c * .83) for c in (r, g, b)]),
            "pressed": wx.Colour(*[int(c * .86) for c in (r, g, b)])
        }
        scale_max = 255. / max(r, g, b)
        scale_step = (scale_max - .5) * .12
        scalings = [.5 + scale_step * i for i in (5., .8, 8., .5)]
        ctrl_border_colors = [
            wx.Colour(*[int(c * s) for c in (r, g, b)]) for s in scalings]
        track_border_colors = [wx.Colour(*[int(c * s) for c in (r, g, b)])
                               for s in (.55, .65, .5, .7)]
        self._scrollctrl_colors = dict((ctrl, ctrl_colors)
                                       for ctrl in self._scrollctrls[:-1])
        self._scrollctrl_colors["track"] = track_colors
        self._scrollctrl_border_colors = dict((ctrl, ctrl_border_colors)
                                              for ctrl in self._scrollctrls[:-1])
        self._scrollctrl_border_colors["track"] = track_border_colors
        self._scroll_start = 0
        self._scroll_offset = 0
        self._scroll_page_up = False
        self.__update_border_lines()

        self._scroll_timer = wx.Timer(self)
        self._cont_scroll_timer = wx.Timer(self)
        self._delay_timer = wx.Timer(self)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.__draw)
        self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
        self.Bind(wx.EVT_LEFT_DCLICK, self.__on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.__on_left_up)
        self.bind_event("mouse_wheel", self.__on_mouse_wheel)
        self.Bind(wx.EVT_MOUSE_CAPTURE_CHANGED, self.__on_release_mouse)
        self.Bind(wx.EVT_TIMER, lambda evt: self.__scroll_by_step(),
                  self._scroll_timer)
        self.Bind(wx.EVT_TIMER, lambda evt: self._scroll_timer.Start(
            200), self._cont_scroll_timer)
        self.Bind(wx.EVT_TIMER, lambda evt: self.__update(), self._delay_timer)

    def destroy(self):

        self.unbind_event("mouse_wheel")

    def __draw(self, event):

        dc = wx.AutoBufferedPaintDCFactory(self)
        dc.DrawBitmap(self._bitmap, 0, 0)
        dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))
        dc.SetBrush(wx.Brush(self._main_color))
        rect = wx.Rect(*self._mouse_rect)
        rect.y = 0
        rect.height = self._height
        dc.DrawRectangleRect(rect)
        dc.DrawBitmap(self._bitmap_right, rect.x - self._scrollbar_offset, 0)

        ctrls = self._scrollctrls[-1:] + self._scrollctrls[:-1]

        for ctrl in ctrls:
            state = "pressed" if self._is_clicked[ctrl] else (
                "hilited" if self._is_hilited[ctrl] else "normal")
            dc.SetBrush(wx.Brush(self._scrollctrl_colors[ctrl][state]))
            pens = [wx.Pen(color)
                    for color in self._scrollctrl_border_colors[ctrl]]
            dc.DrawRectangleRect(self._scrollctrl_rects[ctrl])
            dc.DrawLineList(self._scrollctrl_border_lines[ctrl], pens)

        dc.SetPen(wx.Pen(wx.Colour(), 1, wx.TRANSPARENT))

        if self._is_scrollbar_expanded:
            for direction in ("up", "down"):
                is_clicked = self._is_clicked["arrow_%s" % direction]
                is_hilited = self._is_hilited["arrow_%s" % direction]
                c = 255 if is_clicked else (200 if is_hilited else 0)
                dc.SetBrush(wx.Brush(wx.Colour(c, c, c)))
                dc.DrawPolygon(self._arrows[direction])

    def __update_border_lines(self, thumb_only=False):

        def get_lines(rect):

            x, y, w, h = rect
            w -= 1
            h -= 1
            top = (x, y, x + w + 1, y)
            bottom = (x, y + h, x + w + 1, y + h)
            left = (x, y, x, y + h)
            right = (x + w, y, x + w, y + h)

            return (top, bottom, left, right)

        ctrls = ("thumb",) if thumb_only else self._scrollctrls

        for ctrl in ctrls:
            self._scrollctrl_border_lines[ctrl] = get_lines(
                self._scrollctrl_rects[ctrl])

    def __update(self):

        if self._is_scrollbar_expanded == self._has_mouse:
            return

        rects = [self._mouse_rect] + self._scrollctrl_rects.values()
        d = self._scrollbar_expanded - self._scrollbar_collapsed

        if self._has_mouse:

            w, h = self._stack_parent.GetSize()
            self._stack_parent.SetSize(wx.Size(w - d, h))

            for rect in rects:
                rect.width += d
                rect.x -= d

        else:

            w, h = self._stack_parent.GetSize()
            self._stack_parent.SetSize(wx.Size(w + d, h))

            for rect in rects:
                rect.width -= d
                rect.x += d

            self._is_clicked = dict((ctrl, False)
                                    for ctrl in self._scrollctrls)

        self._is_scrollbar_expanded = self._has_mouse
        self.__update_border_lines()
        self.RefreshRect(self._refresh_rect)

    def __on_release_mouse(self, event):

        self._is_clicked = dict((ctrl, False) for ctrl in self._scrollctrls)
        self._cont_scroll_timer.Stop()
        self._scroll_timer.Stop()
        self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
        self.bind_event("mouse_wheel", self.__on_mouse_wheel)

        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
        has_mouse = self._mouse_rect.Contains(mouse_pos)

        if self._has_mouse != has_mouse:
            self._has_mouse = has_mouse
            self._delay_timer.Start(400, oneShot=True)

        if not self._has_mouse:
            self._is_hilited = dict((ctrl, False)
                                    for ctrl in self._scrollctrls)

        self.RefreshRect(self._scrollctrl_rects["track"])

    def __on_enter(self, event=None):

        self.Bind(wx.EVT_MOTION, self.__on_motion)

    def __on_leave(self, event=None):

        self.Unbind(wx.EVT_MOTION)

        self._is_hilited = dict((ctrl, False) for ctrl in self._scrollctrls)
        self.RefreshRect(self._scrollctrl_rects["track"])

        if self._has_mouse:
            self._has_mouse = False
            self._delay_timer.Start(400, oneShot=True)

    def __on_mouse_wheel(self, event):

        track_rect = self._scrollctrl_rects["track"]
        height = track_rect.height - self._scrollbar_expanded * 2
        y_min = track_rect.y
        thumb_rect = self._scrollctrl_rects["thumb"]
        y_max = y_min + height - thumb_rect.height
        y = thumb_rect.y + 10 * (1 if event.GetWheelRotation() < 0 else -1)
        y = min(y_max, max(y_min, y))
        thumb_rect.y = y
        self._stack.update_pos(-1. * (y - y_min) / height)
        self.__update_border_lines(thumb_only=True)
        self.RefreshRect(track_rect)

    def __scroll(self, mouse_pos):

        mouse_x, mouse_y = mouse_pos
        track_rect = self._scrollctrl_rects["track"]
        height = track_rect.height - self._scrollbar_expanded * 2
        y_min = track_rect.y
        thumb_rect = self._scrollctrl_rects["thumb"]

        if abs(mouse_x - thumb_rect.x - thumb_rect.width * .5) > 150:
            y = self._scroll_start
        else:
            y_max = y_min + height - thumb_rect.height
            y = min(y_max, max(y_min, mouse_y - self._scroll_offset))

        thumb_rect.y = y
        self._stack.update_pos(-1. * (y - y_min) / height)
        self.__update_border_lines(thumb_only=True)
        self.RefreshRect(track_rect)

    def __scroll_by_page(self):

        thumb_rect = self._scrollctrl_rects["thumb"]
        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()

        if self._scroll_page_up:
            if thumb_rect.y < mouse_pos.y:
                return
        elif mouse_pos.y < thumb_rect.bottom:
            return

        track_rect = self._scrollctrl_rects["track"]
        height = track_rect.height - self._scrollbar_expanded * 2
        y_min = track_rect.y
        thumb_height = thumb_rect.height
        y_max = y_min + height - thumb_height
        y = thumb_rect.y + thumb_height * (-1 if self._scroll_page_up else 1)
        y = min(y_max, max(y_min, y))
        thumb_rect.y = y
        self._stack.update_pos(-1. * (y - y_min) / height)

    def __scroll_by_step(self):

        if self._is_clicked["arrow_up"]:
            self._stack.move_panel_up()
        elif self._is_clicked["arrow_down"]:
            self._stack.move_panel_down()
        elif self._is_clicked["track"]:
            self.__scroll_by_page()
        else:
            return

        self.__update_border_lines(thumb_only=True)
        self.RefreshRect(self._scrollctrl_rects["track"])

    def __on_motion(self, event):

        mouse_pos = event.GetPosition()

        if True in self._is_clicked.itervalues():

            if self._is_clicked["thumb"]:
                self.__scroll(mouse_pos)

            return

        for ctrl in self._scrollctrls:

            ctrl_hilited = self._scrollctrl_rects[ctrl].Contains(mouse_pos)

            if self._is_hilited[ctrl] != ctrl_hilited:
                self._is_hilited[ctrl] = ctrl_hilited
                self.RefreshRect(self._scrollctrl_rects[ctrl])

        has_mouse = self._mouse_rect.Contains(mouse_pos)

        if self._has_mouse != has_mouse:
            self._has_mouse = has_mouse
            self._delay_timer.Start(400, oneShot=True)

    def __on_left_down(self, event):

        if not self._has_mouse or not self._is_enabled:
            return

        mouse_pos = event.GetPosition()

        for ctrl in self._scrollctrls:

            rect = self._scrollctrl_rects[ctrl]

            if rect.Contains(mouse_pos):

                Mgr.do("accept_field_input")
                self.Unbind(wx.EVT_ENTER_WINDOW)
                self.Unbind(wx.EVT_LEAVE_WINDOW)
                self.unbind_event("mouse_wheel")
                self.CaptureMouse()
                self._is_clicked[ctrl] = True

                if ctrl == "thumb":
                    self._scroll_start = rect.GetPosition().y
                    self._scroll_offset = mouse_pos.y - self._scroll_start
                elif ctrl == "arrow_up":
                    self._stack.move_panel_up()
                    self._cont_scroll_timer.Start(500, oneShot=True)
                elif ctrl == "arrow_down":
                    self._stack.move_panel_down()
                    self._cont_scroll_timer.Start(500, oneShot=True)
                elif ctrl == "track":
                    self._scroll_page_up = mouse_pos.y < self._scrollctrl_rects[
                        "thumb"].y
                    self.__scroll_by_step()
                    self._cont_scroll_timer.Start(500, oneShot=True)

                self.RefreshRect(rect)
                break

    def __on_left_up(self, event):

        if True in self._is_clicked.itervalues():
            self.ReleaseMouse()

        self._is_clicked = dict((ctrl, False) for ctrl in self._scrollctrls)
        self.RefreshRect(self._scrollctrl_rects["track"])

    def get_stack_parent(self):

        return self._stack_parent

    def update_scrollbar(self, panel_height, rel_offset):

        w, h = self._stack_parent.GetSize()
        h_min = self._scrollbar_expanded
        track_rect = self._scrollctrl_rects["track"]
        h_max = track_rect.height - h_min * 2
        thumb_height = min(h_max, max(h_min, int(h_max * h / panel_height)))
        thumb_rect = self._scrollctrl_rects["thumb"]
        thumb_rect.height = thumb_height
        y_min = track_rect.y
        y = y_min + int(rel_offset * h_max)
        y_max = y_min + h_max - thumb_rect.height
        y = min(y_max, max(y_min, y))
        thumb_rect.y = y
        self.__update_border_lines(thumb_only=True)
        self.RefreshRect(track_rect)

    def enable(self, enable=True):

        if self._is_enabled == enable:
            return

        self._is_enabled = enable

        if enable:

            self.Bind(wx.EVT_ENTER_WINDOW, self.__on_enter)
            self.Bind(wx.EVT_LEAVE_WINDOW, self.__on_leave)
            self.bind_event("mouse_wheel", self.__on_mouse_wheel)

            mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
            rect = wx.Rect(0, 0, *self.GetSize())

            if rect.Contains(mouse_pos):
                self.__on_enter()

        else:

            self.Unbind(wx.EVT_ENTER_WINDOW)
            self.Unbind(wx.EVT_LEAVE_WINDOW)
            self.unbind_event("mouse_wheel")
            self.__on_leave()


class PanelStack(wx.PyPanel, BaseObject, FocusResetter):

    def __init__(self, frame_parent, pos, size, focus_receiver=None, interface_id=""):

        frame = PanelStackFrame(frame_parent, pos, size,
                                self, focus_receiver, interface_id)
        parent = frame.get_stack_parent()
        self._width = parent.GetSize()[0]

        wx.PyPanel.__init__(self, parent)
        BaseObject.__init__(self, interface_id)
        FocusResetter.__init__(self, focus_receiver)

        self.refuse_focus()

        self._frame = frame
        self._clicked_panel = None
        self._panels = []
        self._panel_groups = []
        self._is_enabled = True

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        self._drag_offset = 0

        def get_all_panels():

            panels = [
                pnl for grp in self._panel_groups for pnl in grp.get_panels()]
            panels += self._panels

            return panels

        def get_other_panels():

            panels = get_all_panels()
            panels.remove(self._clicked_panel)

            return panels

        def toggle_expand(event):

            self._clicked_panel.expand(not self._clicked_panel.is_expanded())

        def expand_panels(expand=True, all_panels=True):

            panels = get_all_panels() if all_panels else get_other_panels()

            for panel in panels:
                panel.expand(expand)

        def expand_sections(expand=True):

            if not self._clicked_panel.is_expanded():
                return

            for section in self._clicked_panel.get_sections():
                section.expand(expand)

        self._menu_items = {"panels": {}, "panel_groups": {}}
        self._menu = wx.Menu()
        self._nav_menu = wx.Menu()
        self._menu.AppendMenu(-1, "Go to", self._nav_menu)
        self._menu.AppendSeparator()
        item = self._menu.Append(-1, "Collapse panel")
        self.Bind(wx.EVT_MENU, toggle_expand, item)
        self._menu_items["collapse_panel"] = item
        item = self._menu.Append(-1, "Collapse all sections")
        self.Bind(wx.EVT_MENU, lambda evt: expand_sections(False), item)
        self._menu_items["collapse_sections"] = item
        item = self._menu.Append(-1, "Expand all sections")
        self.Bind(wx.EVT_MENU, lambda evt: expand_sections(), item)
        self._menu_items["expand_sections"] = item
        self._menu.AppendSeparator()
        item = self._menu.Append(-1, "Collapse other panels")
        self.Bind(wx.EVT_MENU, lambda evt: expand_panels(False, False), item)
        self._menu_items["collapse_other_panels"] = item
        item = self._menu.Append(-1, "Expand other panels")
        self.Bind(wx.EVT_MENU, lambda evt: expand_panels(True, False), item)
        self._menu_items["expand_other_panels"] = item
        item = self._menu.Append(-1, "Collapse all panels")
        self.Bind(wx.EVT_MENU, lambda evt: expand_panels(False), item)
        item = self._menu.Append(-1, "Expand all panels")
        self.Bind(wx.EVT_MENU, lambda evt: expand_panels(), item)

        self.Bind(wx.EVT_SIZE, self.__on_size)
        self.bind_event("panel_left_down", self.__start_drag)
        self.bind_event("panel_right_down", self.__on_right_down)
        self.Bind(wx.EVT_LEFT_UP, self.__end_drag)
        self.Bind(wx.EVT_MOUSE_CAPTURE_CHANGED, self.__on_release_mouse)

    def destroy(self):

        self._frame.destroy()
        self.unbind_event("panel_left_down")
        self.unbind_event("panel_right_down")

    def __clamp_y(self, y):

        height = self.GetSize()[1]
        height_parent = self.GetParent().GetSize()[1]

        return min(0, max(y, height_parent - height))

    def __on_size(self, event):

        x, y = self.GetPosition()
        y_clamped = self.__clamp_y(y)
        height = self.GetSize()[1]

        if y != y_clamped:
            y = y_clamped
            self.SetPosition(wx.Point(x, y))

        rel_offset = -1. * y / height
        self._frame.update_scrollbar(height, rel_offset)

    def __on_motion(self, event):

        mouse_pos = wx.GetMousePosition() - self.GetParent().GetScreenPosition()
        y = mouse_pos.y - self._drag_offset
        y = self.__clamp_y(y)
        self.SetPosition(wx.Point(0, y))
        height = self.GetSize()[1]
        rel_offset = -1. * y / height
        self._frame.update_scrollbar(height, rel_offset)

    def __on_right_down(self, event, panel=None):

        if panel:
            if event.GetEventObject() not in self.GetChildren():
                return
        elif event.GetEventObject() is not self.GetParent():
            return

        for group, item in self._menu_items["panel_groups"].iteritems():
            item.SetItemLabel(group.get_current_panel().get_header())

        if panel:
            item = self._menu_items["collapse_panel"]
            item.Enable()
            item.SetItemLabel("%s panel" % (
                "Collapse" if panel.is_expanded() else "Expand"))
            self._menu_items["collapse_other_panels"].Enable()
            self._menu_items["expand_other_panels"].Enable()
            self._menu_items["collapse_sections"].Enable()
            self._menu_items["expand_sections"].Enable()
        else:
            self._menu_items["collapse_panel"].Enable(False)
            self._menu_items["collapse_other_panels"].Enable(False)
            self._menu_items["expand_other_panels"].Enable(False)
            self._menu_items["collapse_sections"].Enable(False)
            self._menu_items["expand_sections"].Enable(False)

        self._clicked_panel = panel
        self.PopupMenu(self._menu)
        self._clicked_panel = None

    def __on_release_mouse(self, event):

        self.Unbind(wx.EVT_MOTION)

    def __start_drag(self, event):

        if event.GetEventObject() not in self.GetChildren():
            return

        self.CaptureMouse()
        self.Bind(wx.EVT_MOTION, self.__on_motion)
        mouse_pos = wx.GetMousePosition() - self.GetScreenPosition()
        self._drag_offset = mouse_pos.y

    def __end_drag(self, event):

        if self.HasCapture():
            self.ReleaseMouse()

    def update_pos(self, rel_offset):

        offset = int(rel_offset * self.GetSize()[1])
        self.SetPosition(wx.Point(0, self.__clamp_y(offset)))

    def move_panel_up(self):

        y = self.GetPosition()[1]
        parent_rect = wx.Rect(0, -y, *self.GetParent().GetSize())
        sizer_items = self.GetSizer().GetChildren()
        offset = y

        for item in sizer_items:

            if not item.IsShown():
                continue

            rect = item.GetRect()

            if -rect.y == y:
                break

            offset = -rect.y

            if rect.Intersects(parent_rect):
                break

        offset = self.__clamp_y(offset)
        self.SetPosition(wx.Point(0, offset))
        height = self.GetSize()[1]
        rel_offset = -1. * offset / height
        self._frame.update_scrollbar(height, rel_offset)

    def move_panel_down(self):

        y = self.GetPosition()[1]
        height = self.GetSize()[1]
        w_parent, h_parent = self.GetParent().GetSize()
        parent_rect = wx.Rect(0, -y, w_parent, h_parent)
        sizer_items = self.GetSizer().GetChildren()
        offset = y
        prev_found = False

        for item in sizer_items:

            if not item.IsShown():
                continue

            rect = item.GetRect()

            if prev_found:
                offset = -rect.y
                break

            if -rect.y == y:
                prev_found = True
                continue

            if rect.Intersects(parent_rect):
                prev_found = True

        if offset + height < h_parent:
            offset = min(0, h_parent - height)

        offset = self.__clamp_y(offset)
        self.SetPosition(wx.Point(0, offset))
        rel_offset = -1. * offset / height
        self._frame.update_scrollbar(height, rel_offset)

    def __scroll_to_panel(self, panel):

        y = self.GetPosition()[1]
        height = self.GetSize()[1]
        w_parent, h_parent = self.GetParent().GetSize()
        offset = -panel.GetPosition()[1]

        if offset + height < h_parent:
            offset = min(0, h_parent - height)

        offset = self.__clamp_y(offset)
        self.SetPosition(wx.Point(0, offset))
        rel_offset = -1. * offset / height
        self._frame.update_scrollbar(height, rel_offset)

    def get_width(self):

        return self._width

    def add_panel(self, panel):

        self._panels.append(panel)

        item = self._nav_menu.Append(-1, panel.get_header())
        self.Bind(wx.EVT_MENU, lambda evt: self.__scroll_to_panel(panel), item)
        self._menu_items["panels"][panel] = item

    def get_panels(self):

        return self._panels

    def add_panel_group(self, panel_group):

        self._panel_groups.append(panel_group)

        item = self._nav_menu.Append(-1, "<panel group>")
        panel = panel_group.get_current_panel()
        self.Bind(wx.EVT_MENU, lambda evt: self.__scroll_to_panel(panel), item)
        self._menu_items["panel_groups"][panel_group] = item

    def get_panel_groups(self):

        return self._panel_groups

    def enable(self, enable=True):

        if self._is_enabled == enable:
            return

        self._is_enabled = enable
        self._frame.enable(enable)

        for panel_group in self._panel_groups:
            panel_group.enable(enable)

        for panel in self._panels:
            panel.enable(enable)

    def disable(self, show=True):

        if not self._is_enabled:
            return

        self._is_enabled = False
        self._frame.enable(False)

        for panel_group in self._panel_groups:
            panel_group.disable(show)

        for panel in self._panels:
            panel.disable(show)
