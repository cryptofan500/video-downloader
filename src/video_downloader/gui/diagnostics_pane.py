"""
Diagnostics pane component for GUI.

Provides system diagnostics and logging display with scrollable textbox.
"""

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk


class DiagnosticsPane(ctk.CTkFrame):
    """
    System diagnostics and logging pane.

    Displays log messages with timestamps and severity levels.
    """

    def __init__(self, master: ctk.CTk | ctk.CTkFrame):
        """
        Initialize diagnostics pane.

        Args:
            master: Parent widget
        """
        super().__init__(master)

        # Configure grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        self.label = ctk.CTkLabel(self, text="System Diagnostics", font=("Helvetica", 16, "bold"))
        self.label.grid(row=0, column=0, pady=(10, 5), sticky="w", padx=10)

        # Textbox for logs (scrollable)
        self.textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("Consolas", 11),
            state="disabled",  # Read-only by default
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Bind right-click context menu
        self.textbox.bind("<Button-3>", self._show_context_menu)
        self.textbox.bind("<Button-2>", self._show_context_menu)  # macOS
        # Bind Ctrl+C for copy
        self.textbox.bind("<Control-c>", self._copy_selection)
        self.textbox.bind("<Control-C>", self._copy_selection)
        # Bind Ctrl+A for select all
        self.textbox.bind("<Control-a>", self._select_all)
        self.textbox.bind("<Control-A>", self._select_all)

        # Buttons frame
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, pady=(0, 10))

        # Clear button
        self.clear_btn = ctk.CTkButton(
            button_frame, text="Clear Logs", command=self.clear_logs, width=100
        )
        self.clear_btn.pack(side="left", padx=5)

        # Export button
        self.export_btn = ctk.CTkButton(
            button_frame, text="Export Logs", command=self._export_logs, width=100
        )
        self.export_btn.pack(side="left", padx=5)

    def _show_context_menu(self, event: tk.Event) -> None:
        """Display right-click context menu."""
        menu = tk.Menu(self, tearoff=0)

        # Check if there's selected text
        try:
            self.textbox.selection_get()
            has_selection = True
        except tk.TclError:
            has_selection = False

        has_content = bool(self.textbox.get("0.0", "end").strip())

        # Copy
        menu.add_command(
            label="Copy",
            command=self._copy_selection,
            state="normal" if has_selection else "disabled",
            accelerator="Ctrl+C",
        )

        menu.add_separator()

        # Select All
        menu.add_command(
            label="Select All",
            command=self._select_all,
            state="normal" if has_content else "disabled",
            accelerator="Ctrl+A",
        )

        menu.add_separator()

        # Export
        menu.add_command(
            label="Export Logs...",
            command=self._export_logs,
            state="normal" if has_content else "disabled",
        )

        # Show menu at cursor position
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_selection(self, event: tk.Event | None = None) -> str:
        """Copy selected text to clipboard."""
        try:
            selected = self.textbox.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected)
        except tk.TclError:
            # No selection, copy all
            content = self.textbox.get("0.0", "end").strip()
            if content:
                self.clipboard_clear()
                self.clipboard_append(content)
        return "break"

    def _select_all(self, event: tk.Event | None = None) -> str:
        """Select all text in textbox."""
        self.textbox.configure(state="normal")
        self.textbox.tag_add("sel", "0.0", "end")
        self.textbox.configure(state="disabled")
        return "break"

    def log(self, message: str, level: str = "INFO") -> None:
        """
        Add log message to textbox (thread-safe).

        Args:
            message: Log message
            level: Severity level (INFO, SUCCESS, WARNING, ERROR)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color coding by level
        color_map = {
            "INFO": "#FFFFFF",
            "SUCCESS": "#00FF00",
            "WARNING": "#FFA500",
            "ERROR": "#FF0000",
        }
        color = color_map.get(level, "#FFFFFF")

        log_entry = f"[{timestamp}] [{level}] {message}\n"

        # Make textbox temporarily editable
        self.textbox.configure(state="normal")

        # Insert with color (if supported)
        self.textbox.insert("end", log_entry)

        # Auto-scroll to bottom
        self.textbox.see("end")

        # Make read-only again
        self.textbox.configure(state="disabled")

    def clear_logs(self) -> None:
        """Clear all logs from textbox."""
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.configure(state="disabled")
        self.log("Logs cleared")

    def _export_logs(self) -> None:
        """Export logs to file."""
        content = self.textbox.get("0.0", "end").strip()
        if not content:
            self.log("No logs to export", "WARNING")
            return

        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"video_downloader_logs_{timestamp}.txt"

        # Get user's Downloads folder as default location
        from video_downloader.utils.user_dirs import get_downloads_folder

        downloads_folder = get_downloads_folder()

        # Open save dialog
        filepath = filedialog.asksaveasfilename(
            title="Export Logs",
            initialdir=str(downloads_folder),
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")],
        )

        if not filepath:
            return  # User cancelled

        try:
            Path(filepath).write_text(content, encoding="utf-8")
            self.log(f"Logs exported to: {filepath}", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to export logs: {e}", "ERROR")

    def get_logs(self) -> str:
        """
        Get all log content.

        Returns:
            All log text
        """
        return self.textbox.get("0.0", "end")
