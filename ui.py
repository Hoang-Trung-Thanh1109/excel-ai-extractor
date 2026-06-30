"""CustomTkinter user interface for the Excel AI Extractor."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from ai_engine import AIEngine
from document_reader import DocumentReader
from excel_engine import ExcelEngine


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Replace this with your Gemini API key.
GEMINI_API_KEY = "AQ.Ab8RN6L0W0gmOtyFh8yhAPRc3wF9X6YRS8r6ngBhDRu82R4l5g"

class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Excel AI Extractor")
        self.geometry("1200x760")
        self.minsize(1040, 680)

        self.reader = DocumentReader()
        self.output_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.selected_files: list[str] = []
        self.last_output_path: str = ""

        self._build_layout()
        self.after(150, self._poll_worker_queue)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=16)
        header.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Excel AI Extractor",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.grid(row=0, column=0, padx=18, pady=(16, 2), sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Tạo Excel từ Prompt, PDF hoặc DOCX bằng Gemini 2.5 Flash.",
        )
        subtitle.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")

        body = ctk.CTkFrame(self, corner_radius=16)
        body.grid(row=1, column=0, padx=18, pady=(0, 18), sticky="nsew")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # Left panel: Canvas + Scrollbar tu build (dam bao scroll hoat dong khong phu thuoc customtkinter)
        left_outer = ctk.CTkFrame(body, corner_radius=16)
        left_outer.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")
        left_outer.grid_rowconfigure(0, weight=1)
        left_outer.grid_columnconfigure(0, weight=1)

        left_canvas = tk.Canvas(left_outer, borderwidth=0, highlightthickness=0)
        left_scrollbar = tk.Scrollbar(left_outer, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        left_scrollbar.grid(row=0, column=1, sticky="ns")
        left_canvas.grid(row=0, column=0, sticky="nsew")

        left = tk.Frame(left_canvas)
        left.grid_columnconfigure(1, weight=1)
        left_win_id = left_canvas.create_window((0, 0), window=left, anchor="nw")

        def _on_inner_resize(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))

        def _on_canvas_resize(event):
            left_canvas.itemconfig(left_win_id, width=event.width)

        def _on_mousewheel(event):
            if event.num == 4:
                left_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                left_canvas.yview_scroll(1, "units")
            else:
                left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        left.bind("<Configure>", _on_inner_resize)
        left_canvas.bind("<Configure>", _on_canvas_resize)
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        left_canvas.bind_all("<Button-4>", _on_mousewheel)
        left_canvas.bind_all("<Button-5>", _on_mousewheel)

        right = ctk.CTkFrame(body, corner_radius=16)
        right.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._build_inputs(left)
        self._build_output_panel(right)

    def _build_inputs(self, parent: tk.Frame) -> None:
        section_title = ctk.CTkLabel(parent, text="Nguồn dữ liệu", font=ctk.CTkFont(size=18, weight="bold"))
        section_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ctk.CTkLabel(parent, text="Model").grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.model_var = tk.StringVar(value="gemini-2.5-flash")
        self.model_entry = ctk.CTkEntry(parent, textvariable=self.model_var, height=38)
        self.model_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        ctk.CTkLabel(parent, text="Prompt").grid(row=3, column=0, sticky="w", pady=(0, 6))
        self.prompt_text = ctk.CTkTextbox(parent, height=190, wrap="word")
        self.prompt_text.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0, 12))
        self.prompt_text.insert(
            "1.0",
            "ao bang Excel tu prompt nay hoac tu tai lieu dinh kem. Hay sinh cau truc ro rang, du lieu hop ly va de doc trong Excel.",
        )

        ctk.CTkLabel(parent, text="Tài liệu đính kèm").grid(row=5, column=0, sticky="w", pady=(0, 6))
        self.file_listbox = tk.Listbox(parent, height=6, activestyle="none")
        self.file_listbox.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        file_buttons = ctk.CTkFrame(parent, fg_color="transparent")
        file_buttons.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        file_buttons.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(file_buttons, text="Thêm PDF", command=self._add_pdf).grid(
            row=0, column=0, padx=(0, 6), sticky="ew"
        )
        ctk.CTkButton(file_buttons, text="Thêm DOCX", command=self._add_docx).grid(
            row=0, column=1, padx=6, sticky="ew"
        )
        ctk.CTkButton(file_buttons, text="Xóa tất cả", command=self._clear_files).grid(
            row=0, column=2, padx=(6, 0), sticky="ew"
        )

        ctk.CTkLabel(parent, text="Output Excel").grid(row=8, column=0, sticky="w", pady=(0, 6))
        self.output_path_var = tk.StringVar(value=str(Path.cwd() / "outputs" / "excel_ai_extractor.xlsx"))
        self.output_entry = ctk.CTkEntry(parent, textvariable=self.output_path_var, height=38)
        self.output_entry.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        output_buttons = ctk.CTkFrame(parent, fg_color="transparent")
        output_buttons.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        output_buttons.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(output_buttons, text="Chọn nơi lưu", command=self._browse_output).grid(
            row=0, column=0, padx=(0, 6), sticky="ew"
        )
        ctk.CTkButton(output_buttons, text="Mở thư mục", command=self._open_output_folder).grid(
            row=0, column=1, padx=(6, 0), sticky="ew"
        )

        self.generate_button = ctk.CTkButton(
            parent,
            text="Tạo Excel",
            height=44,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._start_generation,
        )
        self.generate_button.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(4, 8))

        self.progress = ctk.CTkProgressBar(parent)
        self.progress.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.progress.set(0)

        self.status_var = tk.StringVar(value="Sẵn sàng.")
        self.status_label = ctk.CTkLabel(parent, textvariable=self.status_var)
        self.status_label.grid(row=13, column=0, columnspan=2, sticky="w")

    def _build_output_panel(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="Nhật ký", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 8), sticky="w"
        )

        self.summary_label = ctk.CTkLabel(
            parent,
            text="Sau khi tạo xong, ứng dụng sẽ mở file Excel tự động.",
            justify="left",
            wraplength=320,
        )
        self.summary_label.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        self.log_text = tk.Text(
            parent,
            height=20,
            wrap="word",
            state="disabled",
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            relief="flat",
            padx=12,
            pady=12,
        )
        self.log_text.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="nsew")

    def _add_pdf(self) -> None:
        files = filedialog.askopenfilenames(title="Chọn PDF", filetypes=[("PDF files", "*.pdf")])
        self._add_files(files)

    def _add_docx(self) -> None:
        files = filedialog.askopenfilenames(title="Chọn DOCX", filetypes=[("Word documents", "*.docx")])
        self._add_files(files)

    def _add_files(self, files: tuple[str, ...]) -> None:
        for file_path in files:
            if file_path and file_path not in self.selected_files:
                self.selected_files.append(file_path)
                self.file_listbox.insert(tk.END, file_path)
                self._log(f"Da them: {file_path}")

    def _clear_files(self) -> None:
        self.selected_files.clear()
        self.file_listbox.delete(0, tk.END)
        self._log("Đã xóa tất cả tài liệu đính kèm.")

    def _browse_output(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Chọn nơi lưu Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile=Path(self.output_path_var.get()).name or "excel_ai_extractor.xlsx",
        )
        if file_path:
            self.output_path_var.set(file_path)

    def _open_output_folder(self) -> None:
        folder = Path(self.output_path_var.get()).expanduser().resolve().parent
        if folder.exists():
            ExcelEngine().open_workbook(str(folder))

    def _start_generation(self) -> None:
        if self.generate_button.cget("state") == "disabled":
            return

        api_key = GEMINI_API_KEY.strip()
        prompt = self.prompt_text.get("1.0", "end").strip()
        model = self.model_var.get().strip() or "gemini-2.5-flash"

        if not api_key or api_key == "PASTE_YOUR_GEMINI_API_KEY_HERE":
            messagebox.showerror(
                "Thieu API key",
                "Hay thay GEMINI_API_KEY trong ui.py bang API key that cua ban.",
            )
            return

        if not prompt and not self.selected_files:
            messagebox.showerror("Thieu du lieu", "Hay nhap prompt hoac dinh kem it nhat 1 file PDF/DOCX.")
            return

        self._set_busy(True)
        self._log("Bắt đầu xử lý...")
        self.status_var.set("Đang chuẩn bị dữ liệu...")

        worker = threading.Thread(
            target=self._worker_run,
            args=(api_key, model, prompt, list(self.selected_files), self.output_path_var.get().strip()),
            daemon=True,
        )
        worker.start()

    def _worker_run(
        self,
        api_key: str,
        model: str,
        prompt: str,
        files: list[str],
        output_path: str,
    ) -> None:
        try:
            ai_engine = AIEngine(api_key=api_key, model=model, logger=self._queue_log)
            document_context = self.reader.read_documents(files)
            workbook_spec = ai_engine.generate_workbook_spec(
                user_prompt=prompt,
                document_context=document_context,
            )

            excel_engine = ExcelEngine(logger=self._queue_log)
            result = excel_engine.save_workbook(
                {
                    "workbook_title": workbook_spec.workbook_title,
                    "sheets": workbook_spec.sheets,
                },
                output_path=output_path,
            )

            excel_engine.open_workbook(result.path)
            self.output_queue.put(("success", result.path))
        except Exception as exc:
            self.output_queue.put(("error", str(exc)))

    def _poll_worker_queue(self) -> None:
        try:
            while True:
                event_type, payload = self.output_queue.get_nowait()
                if event_type == "log":
                    self._log(str(payload))
                elif event_type == "success":
                    self.last_output_path = str(payload)
                    self._log(f"Hoan tat: {payload}")
                    self.status_var.set("Đã tạo xong và đã mở file Excel.")
                    messagebox.showinfo("Thành công", f"Đã tạo file Excel:\n{payload}")
                    self._set_busy(False)
                elif event_type == "error":
                    self._log(f"Loi: {payload}")
                    self.status_var.set("Có lỗi xảy ra.")
                    messagebox.showerror("Lỗi", str(payload))
                    self._set_busy(False)
        except queue.Empty:
            pass

        self.after(150, self._poll_worker_queue)

    def _queue_log(self, message: str) -> None:
        self.output_queue.put(("log", message))

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.generate_button.configure(state=state)
        if busy:
            self.progress.start()
            self.status_var.set("Đang xử lý...")
        else:
            self.progress.stop()
            self.progress.set(0)

    def _log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")


def main() -> None:
    app = MainWindow()
    app.mainloop()
