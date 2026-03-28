"""
Custom widgets with enhanced functionality.
"""

import re
import tkinter as tk

import customtkinter as ctk


class URLEntry(ctk.CTkEntry):
    """
    Enhanced entry widget with right-click context menu for URL input.

    Features:
    - Right-click menu with Cut, Copy, Paste, Clear, Select All
    - Smart "Paste URL" that validates clipboard content
    - Placeholder text support (inherited from CTkEntry)
    """

    # Pattern to validate URLs
    URL_PATTERN = re.compile(
        r"^https?://"  # http:// or https://
        r'[^\s<>"{}|\\^`\[\]]+'  # valid URL characters
        r"$",
        re.IGNORECASE,
    )

    def __init__(self, master: ctk.CTk, **kwargs) -> None:
        super().__init__(master, **kwargs)

        # Bind right-click event
        self.bind("<Button-3>", self._show_context_menu)
        # Also bind for macOS
        self.bind("<Button-2>", self._show_context_menu)
        # Bind Control+V as backup (sometimes CTkEntry doesn't handle it)
        self.bind("<Control-v>", self._paste_from_clipboard)
        self.bind("<Control-V>", self._paste_from_clipboard)

    def _show_context_menu(self, event: tk.Event) -> None:
        """Display right-click context menu."""
        menu = tk.Menu(self, tearoff=0)

        # Get clipboard content for smart paste
        try:
            clipboard = self.clipboard_get()
        except tk.TclError:
            clipboard = ""

        is_valid_url = bool(self.URL_PATTERN.match(clipboard.strip()))

        # Check if there's a selection
        try:
            has_selection = bool(self.selection_get())
        except tk.TclError:
            has_selection = False

        has_content = bool(self.get())

        # Cut
        menu.add_command(
            label="Cut", command=self._cut, state="normal" if has_selection else "disabled"
        )

        # Copy
        menu.add_command(
            label="Copy", command=self._copy, state="normal" if has_selection else "disabled"
        )

        # Paste
        menu.add_command(
            label="Paste",
            command=self._paste_from_clipboard,
            state="normal" if clipboard else "disabled",
        )

        menu.add_separator()

        # Smart Paste URL (validates URL format)
        paste_url_label = "Paste URL" if is_valid_url else "Paste URL (invalid)"
        menu.add_command(
            label=paste_url_label,
            command=lambda: self._paste_url(clipboard.strip()),
            state="normal" if is_valid_url else "disabled",
        )

        menu.add_separator()

        # Select All
        menu.add_command(
            label="Select All",
            command=self._select_all,
            state="normal" if has_content else "disabled",
        )

        # Clear
        menu.add_command(
            label="Clear", command=self._clear, state="normal" if has_content else "disabled"
        )

        # Show menu at cursor position
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _cut(self, event: tk.Event | None = None) -> str:
        """Cut selected text to clipboard."""
        try:
            selected = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected)
            self.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        return "break"

    def _copy(self, event: tk.Event | None = None) -> str:
        """Copy selected text to clipboard."""
        try:
            selected = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected)
        except tk.TclError:
            pass
        return "break"

    def _paste_from_clipboard(self, event: tk.Event | None = None) -> str:
        """Paste from clipboard at cursor position."""
        try:
            clipboard = self.clipboard_get()
            # If there's a selection, replace it
            try:
                self.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            self.insert("insert", clipboard)
        except tk.TclError:
            pass
        return "break"

    def _paste_url(self, url: str) -> None:
        """Clear field and paste validated URL."""
        self.delete(0, "end")
        self.insert(0, url)

    def _select_all(self, event: tk.Event | None = None) -> str:
        """Select all text in entry."""
        self.select_range(0, "end")
        self.icursor("end")
        return "break"

    def _clear(self, event: tk.Event | None = None) -> str:
        """Clear all text from entry."""
        self.delete(0, "end")
        return "break"
