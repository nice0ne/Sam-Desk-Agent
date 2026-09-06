"""Memory Viewer Window for Sam-Desk-Agent.

Provides a graphical user interface to inspect, search, and manage procedural skills
(learned workflow recipes) and user preferences stored in SQLite.
"""

import json
from typing import Optional, List, Dict, Any
import tkinter as tk
from tkinter import ttk, messagebox

from src.memory.db import DatabaseManager
from src.memory.skill_store import SkillStore


class MemoryViewerWindow:
    """Memory & Learned Skills GUI Dialog for Sam-Desk-Agent."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        skill_store: Optional[SkillStore] = None,
        master: Optional[tk.Tk] = None,
    ):
        self.db_manager = db_manager or DatabaseManager()
        self.skill_store = skill_store or SkillStore(self.db_manager)
        self.master = master
        self.root: Optional[tk.Toplevel | tk.Tk] = None

    def show(self) -> None:
        """Display the Memory Viewer window."""
        if self.root is not None and self.root.winfo_exists():
            self.root.lift()
            return

        if self.master:
            self.root = tk.Toplevel(self.master)
        else:
            self.root = tk.Tk()

        self.root.title("Memori & Pembelajaran Mandiri - Sam-Desk-Agent")
        self.root.geometry("720x560")
        self.root.minsize(640, 480)
        self.root.attributes("-topmost", True)

        main_frame = ttk.Frame(self.root, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(
            main_frame,
            text="💾 Database Memori & Resep Otomatisasi",
            font=("Segoe UI", 13, "bold")
        )
        title_label.pack(anchor=tk.W, pady=(0, 10))

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Resep Otomatisasi (Skills)
        self.tab_skills = ttk.Frame(notebook, padding="10")
        notebook.add(self.tab_skills, text="⚡ Resep Alur Kerja (Procedural Skills)")
        self._build_skills_tab()

        # Tab 2: Preferensi Pengguna
        self.tab_prefs = ttk.Frame(notebook, padding="10")
        notebook.add(self.tab_prefs, text="👤 Preferensi Pengguna")
        self._build_preferences_tab()

        # Bottom Frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(12, 0))

        btn_refresh = ttk.Button(btn_frame, text="🔄 Segarkan Data", command=self.refresh_all)
        btn_refresh.pack(side=tk.LEFT)

        btn_close = ttk.Button(btn_frame, text="Tutup", command=self.root.destroy)
        btn_close.pack(side=tk.RIGHT)

        self.refresh_all()

        if not self.master:
            self.root.mainloop()

    def _build_skills_tab(self) -> None:
        # Table frame
        table_frame = ttk.Frame(self.tab_skills)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "intent", "description", "success_count", "updated_at")
        self.skill_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)

        self.skill_tree.heading("id", text="ID")
        self.skill_tree.heading("intent", text="Perintah / Kata Kunci")
        self.skill_tree.heading("description", text="Deskripsi")
        self.skill_tree.heading("success_count", text="Sukses")
        self.skill_tree.heading("updated_at", text="Diperbarui")

        self.skill_tree.column("id", width=35, anchor=tk.CENTER)
        self.skill_tree.column("intent", width=180)
        self.skill_tree.column("description", width=200)
        self.skill_tree.column("success_count", width=60, anchor=tk.CENTER)
        self.skill_tree.column("updated_at", width=130)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.skill_tree.yview)
        self.skill_tree.configure(yscroll=scrollbar.set)

        self.skill_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.skill_tree.bind("<<TreeviewSelect>>", self._on_skill_selected)

        # Detail step view
        detail_frame = ttk.LabelFrame(self.tab_skills, text="Detail Langkah Aksi JSON", padding="6")
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.txt_skill_detail = tk.Text(detail_frame, height=6, wrap=tk.WORD, font=("Consolas", 9))
        self.txt_skill_detail.pack(fill=tk.BOTH, expand=True)

        action_bar = ttk.Frame(self.tab_skills)
        action_bar.pack(fill=tk.X, pady=(6, 0))

        btn_delete_skill = ttk.Button(action_bar, text="🗑️ Hapus Resep Terpilih", command=self._on_delete_skill)
        btn_delete_skill.pack(side=tk.RIGHT)

    def _build_preferences_tab(self) -> None:
        table_frame = ttk.Frame(self.tab_prefs)
        table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("key", "value", "updated_at")
        self.pref_tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)

        self.pref_tree.heading("key", text="Kunci (Key)")
        self.pref_tree.heading("value", text="Nilai (Value)")
        self.pref_tree.heading("updated_at", text="Terakhir Diperbarui")

        self.pref_tree.column("key", width=150)
        self.pref_tree.column("value", width=250)
        self.pref_tree.column("updated_at", width=140)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.pref_tree.yview)
        self.pref_tree.configure(yscroll=scrollbar.set)

        self.pref_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        pref_action_bar = ttk.Frame(self.tab_prefs)
        pref_action_bar.pack(fill=tk.X, pady=(8, 0))

        btn_del_pref = ttk.Button(pref_action_bar, text="🗑️ Hapus Preferensi", command=self._on_delete_pref)
        btn_del_pref.pack(side=tk.RIGHT, padx=4)

    def refresh_all(self) -> None:
        self.refresh_skills()
        self.refresh_preferences()

    def refresh_skills(self) -> None:
        for item in self.skill_tree.get_children():
            self.skill_tree.delete(item)
        self.txt_skill_detail.delete("1.0", tk.END)

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, intent_key, description, steps_json, success_count, updated_at FROM skills ORDER BY id DESC")
                for row in cursor.fetchall():
                    self.skill_tree.insert("", tk.END, values=(
                        row["id"],
                        row["intent_key"],
                        row["description"] or "-",
                        row["success_count"],
                        str(row["updated_at"])[:19]
                    ), tags=(row["steps_json"],))
        except Exception as e:
            print(f"[MemoryViewer] Error refreshing skills: {e}")

    def refresh_preferences(self) -> None:
        for item in self.pref_tree.get_children():
            self.pref_tree.delete(item)

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, updated_at FROM preferences ORDER BY key ASC")
                for row in cursor.fetchall():
                    self.pref_tree.insert("", tk.END, values=(
                        row["key"],
                        row["value"],
                        str(row["updated_at"])[:19]
                    ))
        except Exception as e:
            print(f"[MemoryViewer] Error refreshing preferences: {e}")

    def _on_skill_selected(self, event=None) -> None:
        selected = self.skill_tree.selection()
        if not selected:
            return
        item_id = selected[0]
        tags = self.skill_tree.item(item_id, "tags")
        if tags:
            try:
                formatted = json.dumps(json.loads(tags[0]), indent=2, ensure_ascii=False)
            except Exception:
                formatted = tags[0]
            self.txt_skill_detail.delete("1.0", tk.END)
            self.txt_skill_detail.insert("1.0", formatted)

    def _on_delete_skill(self) -> None:
        selected = self.skill_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih resep yang ingin dihapus terlebih dahulu.", parent=self.root)
            return
        item_id = selected[0]
        skill_db_id = self.skill_tree.item(item_id, "values")[0]

        if messagebox.askyesno("Konfirmasi", f"Yakin ingin menghapus resep ID {skill_db_id}?", parent=self.root):
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM skills WHERE id = ?", (skill_db_id,))
                    conn.commit()
                self.refresh_skills()
                messagebox.showinfo("Sukses", "Resep berhasil dihapus.", parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus resep: {e}", parent=self.root)

    def _on_delete_pref(self) -> None:
        selected = self.pref_tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Pilih preferensi yang ingin dihapus terlebih dahulu.", parent=self.root)
            return
        item_id = selected[0]
        pref_key = self.pref_tree.item(item_id, "values")[0]

        if messagebox.askyesno("Konfirmasi", f"Yakin ingin menghapus preferensi '{pref_key}'?", parent=self.root):
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM preferences WHERE key = ?", (pref_key,))
                    conn.commit()
                self.refresh_preferences()
                messagebox.showinfo("Sukses", "Preferensi berhasil dihapus.", parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus preferensi: {e}", parent=self.root)
