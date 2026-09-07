import tkinter as tk
from tkinter import font as tkfont
from config import *
from time_formatter import parse_lrc_lyrics


class LyricsDisplay(tk.Frame):
    """
    Middle section of the player: dynamic, time-synced scrolling lyrics.

    Lyrics are supplied as raw LRC-format text (via set_lyrics) and parsed
    with time_formatter.parse_lrc_lyrics into plain (seconds, text) pairs -
    no timestamps are ever shown to the user. As playback time advances
    (via update_time), the line matching the current time is centered and
    highlighted (bigger, whiter text); surrounding lines fade out the
    further they are from "now", using the shades already defined in
    config.py.

    Each line is pre-wrapped once (using the largest/boldest font it could
    ever be shown in) so that switching a line in and out of the highlighted
    state never changes how it wraps - only its color/size - which keeps
    the whole list from visually jumping around as playback progresses.
    """

    # Vertical gap (px) added between each lyric line, on top of its own
    # text height. Adjust this to make lines feel more/less cramped.
    LINE_GAP = 20

    FONT_SIZE_NORMAL = 12
    FONT_SIZE_ACTIVE = 17
    # How many lines out on either side still get the "nearby" shade
    # before falling back to the dimmest "far" shade.
    NEARBY_RANGE = 1
    # Scroll easing factor: fraction of the remaining distance covered
    # on each animation tick (higher = snappier, lower = smoother/slower).
    SCROLL_EASE = 0.25

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_COLOR, **kwargs)

        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Font used purely to measure/pre-wrap text - always the largest
        # size a line can appear at, so wrapping never changes on highlight.
        self._wrap_font = tkfont.Font(
            family=FONT_FAMILY, size=self.FONT_SIZE_ACTIVE, weight="bold"
        )

        self._lines = []  # list of (seconds, raw_text), timestamp-free
        self._item_ids = []  # canvas text item ids, parallel to _lines
        self._line_top_offsets = (
            []
        )  # top y-offset of each line's slot, parallel to _lines
        self._line_slot_heights = []  # height of each line's slot, parallel to _lines
        self._content_height = 0.0
        self._current_index = -1
        self._canvas_height = 1
        self._canvas_width = 1

        self._scroll_fraction = 0.0
        self._scroll_target = 0.0
        self._scroll_animating = False

        # Lyric offset in seconds, applied only to which line looks "current" -
        # never to the actual playback timer. Positive = advance lyrics
        # (line is picked earlier); negative = delay them (picked later).
        self._offset = 0.0
        self._last_raw_time = 0.0

        self._placeholder_id = self.canvas.create_text(
            0,
            0,
            text="Lyrics will be displayed here",
            fill=COLOR_MUTED_FG,
            font=(FONT_FAMILY, self.FONT_SIZE_NORMAL),
            anchor="center",
        )

    """Public API"""

    def show_loading(self, message="Fetching lyrics......"):
        """Clear any currently displayed lyrics and show a temporary loading message - call this as soon as a new fetch starts, so the old song's lyrics never linger on screen."""
        self._show_placeholder(message)

    def set_lyrics(self, raw_lyrics):
        """Parse raw LRC-format lyrics and render them, ready for time syncing."""
        self._current_index = -1
        self._scroll_fraction = 0.0
        self._scroll_target = 0.0

        self._lines = parse_lrc_lyrics(raw_lyrics)

        if not self._lines:
            self._show_placeholder("Lyrics not found, maybe try another song.")
            return

        self._render_lines()
        self._set_current_index(0, animate=False)

    def update_time(self, current_time):
        """Update the highlighted/centered line for the given playback time (seconds)."""
        self._last_raw_time = current_time
        if not self._lines:
            return
        index = self._find_current_index(current_time + self._offset)
        if index != self._current_index:
            self._set_current_index(index)

    def set_offset(self, offset_seconds):
        """
        Set the lyric offset in seconds - shifts which line is considered
        "current" without affecting actual playback timing at all.

        Positive values advance the lyrics (a line is shown earlier than its
        timestamp); negative values delay them (shown later). Re-evaluates
        immediately using the last known playback time, so adjusting the
        offset mid-song updates the highlighted line right away instead of
        waiting for the next natural update_time() call.
        """
        if offset_seconds == self._offset:
            return
        self._offset = offset_seconds
        if not self._lines:
            return
        index = self._find_current_index(self._last_raw_time + self._offset)
        if index != self._current_index:
            self._set_current_index(index)

    """Internal helpers"""

    def _show_placeholder(self, message):
        """Clear any rendered lyrics and show a centered status message instead (used for both the loading state and the empty/no-lyrics state)."""
        self._current_index = -1
        self.canvas.delete("all")
        self._lines = []
        self._item_ids = []
        self._line_top_offsets = []
        self._line_slot_heights = []
        self._content_height = 0.0
        self._placeholder_id = self.canvas.create_text(
            self._canvas_width // 2,
            self._canvas_height // 2,
            text=message,
            fill=COLOR_MUTED_FG,
            font=(FONT_FAMILY, self.FONT_SIZE_NORMAL),
            anchor="center",
        )

    def _wrap_text(self, text, max_width):
        """Greedily word-wrap text to max_width pixels, measured with self._wrap_font."""
        if max_width <= 0:
            return text
        words = text.split()
        if not words:
            return text

        wrapped_rows = []
        current_row = words[0]
        for word in words[1:]:
            candidate = f"{current_row} {word}"
            if self._wrap_font.measure(candidate) <= max_width:
                current_row = candidate
            else:
                wrapped_rows.append(current_row)
                current_row = word
        wrapped_rows.append(current_row)
        return "\n".join(wrapped_rows)

    def _render_lines(self):
        """(Re)build all lyric canvas items, pre-wrapped and laid out with no overlap."""
        self.canvas.delete("all")
        self._item_ids = []
        self._line_top_offsets = []
        self._line_slot_heights = []

        center_x = self._canvas_width // 2
        wrap_width = int(self._canvas_width * 0.9) if self._canvas_width > 1 else 0
        row_height = self._wrap_font.metrics("linespace")

        running_top = 0.0
        for _, text in self._lines:
            wrapped_text = self._wrap_text(text, wrap_width)
            row_count = wrapped_text.count("\n") + 1
            slot_height = row_count * row_height + self.LINE_GAP

            self._line_top_offsets.append(running_top)
            self._line_slot_heights.append(slot_height)

            center_y = running_top + slot_height / 2
            item_id = self.canvas.create_text(
                center_x,
                center_y,
                text=wrapped_text,
                fill=COLOR_FAR_FG,
                font=(FONT_FAMILY, self.FONT_SIZE_NORMAL),
                anchor="center",
                justify="center",
            )
            self._item_ids.append(item_id)

            running_top += slot_height

        self._content_height = running_top
        self._update_scrollregion()

    def _find_current_index(self, current_time):
        """Return the index of the last line whose timestamp is <= current_time."""
        index = 0
        for i, (t, _) in enumerate(self._lines):
            if t <= current_time:
                index = i
            else:
                break
        return index

    def _set_current_index(self, index, animate=True):
        self._current_index = index
        for i, item_id in enumerate(self._item_ids):
            distance = abs(i - index)
            if distance == 0:
                fill = COLOR_ACTIVE_FG
                font = (FONT_FAMILY, self.FONT_SIZE_ACTIVE, "bold")
            elif distance <= self.NEARBY_RANGE:
                fill = COLOR_NEARBY_FG
                font = (FONT_FAMILY, self.FONT_SIZE_NORMAL)
            else:
                fill = COLOR_FAR_FG
                font = (FONT_FAMILY, self.FONT_SIZE_NORMAL)
            self.canvas.itemconfig(item_id, fill=fill, font=font)
        self._scroll_to_current(animate=animate)

    def _on_canvas_resize(self, event):
        self._canvas_width = event.width
        self._canvas_height = event.height

        if not self._lines:
            self.canvas.coords(
                self._placeholder_id, self._canvas_width // 2, self._canvas_height // 2
            )
            return

        # Width changed, so re-wrap and re-lay-out every line from scratch.
        self._render_lines()
        if self._current_index >= 0:
            self._set_current_index(self._current_index, animate=False)
        else:
            self._scroll_to_current(animate=False)

    def _update_scrollregion(self):
        pad = self._canvas_height / 2
        self.canvas.configure(
            scrollregion=(0, -pad, self._canvas_width, self._content_height + pad)
        )

    def _compute_target_fraction(self):
        if not self._lines or self._canvas_height <= 1 or self._current_index < 0:
            return 0.0
        pad = self._canvas_height / 2
        scroll_range = self._content_height + 2 * pad
        if scroll_range <= 0:
            return 0.0
        current_top = self._line_top_offsets[self._current_index]
        current_height = self._line_slot_heights[self._current_index]
        current_line_y = current_top + current_height / 2
        desired_top = current_line_y - self._canvas_height / 2
        fraction = (desired_top + pad) / scroll_range
        return max(0.0, min(1.0, fraction))

    def _scroll_to_current(self, animate=True):
        self._scroll_target = self._compute_target_fraction()
        if not animate:
            self._scroll_fraction = self._scroll_target
            self.canvas.yview_moveto(self._scroll_fraction)
            return
        if not self._scroll_animating:
            self._scroll_animating = True
            self._scroll_step()

    def _scroll_step(self):
        diff = self._scroll_target - self._scroll_fraction
        if abs(diff) < 0.001:
            self._scroll_fraction = self._scroll_target
            self.canvas.yview_moveto(self._scroll_fraction)
            self._scroll_animating = False
            return
        self._scroll_fraction += diff * self.SCROLL_EASE
        self.canvas.yview_moveto(self._scroll_fraction)
        self.after(20, self._scroll_step)