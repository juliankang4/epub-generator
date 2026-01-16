import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from epub_gen import EpubGenerator

class EpubGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("웹소설 EPUB 생성기 v1.0")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Style
        self.style = ttk.Style()
        self.style.configure("TButton", padding=5)
        self.style.configure("TLabel", padding=5)

        # UI Elements
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main_frame, text="원고를 EPUB로 변환합니다", font=("Helvetica", 16, "bold")).pack(pady=10)

        # File Selection
        self.file_path = tk.StringVar()
        file_frame = ttk.LabelFrame(main_frame, text="1. 원고 파일 선택 (.txt)", padding=10)
        file_frame.pack(fill=tk.X, pady=10)
        
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=40)
        self.file_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="찾기", command=self.browse_file).pack(side=tk.LEFT)

        # Metadata
        meta_frame = ttk.LabelFrame(main_frame, text="2. 도서 정보 입력", padding=10)
        meta_frame.pack(fill=tk.X, pady=10)

        ttk.Label(meta_frame, text="제목:").grid(row=0, column=0, sticky=tk.W)
        self.title_entry = ttk.Entry(meta_frame, width=35)
        self.title_entry.grid(row=0, column=1, pady=5)
        self.title_entry.insert(0, "나의 소설")

        ttk.Label(meta_frame, text="작가명:").grid(row=1, column=0, sticky=tk.W)
        self.author_entry = ttk.Entry(meta_frame, width=35)
        self.author_entry.grid(row=1, column=1, pady=5)
        self.author_entry.insert(0, "작가명")

        # Action Button
        self.generate_btn = ttk.Button(main_frame, text="EPUB 파일 생성하기", command=self.start_generation)
        self.generate_btn.pack(pady=20, fill=tk.X)

        # Status Bar
        self.status_var = tk.StringVar(value="대기 중...")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="gray").pack(side=tk.BOTTOM)

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="텍스트 파일 선택",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filename:
            self.file_path.set(filename)
            # Try to guess title from filename
            base = os.path.basename(filename)
            title = os.path.splitext(base)[0]
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, title)

    def start_generation(self):
        input_file = self.file_path.get()
        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("오류", "원고 파일을 선택해 주세요.")
            return

        title = self.title_entry.get()
        author = self.author_entry.get()
        
        output_file = filedialog.asksaveasfilename(
            title="저장 위치 선택",
            defaultextension=".epub",
            initialfile=f"{title}.epub",
            filetypes=(("EPUB files", "*.epub"), ("All files", "*.*"))
        )
        
        if not output_file:
            return

        # Disable UI and show progress
        self.generate_btn.config(state=tk.DISABLED)
        self.status_var.set("생성 중... 잠시만 기다려 주세요.")
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start()

        # Run in thread to keep UI responsive
        threading.Thread(target=self.generate_epub, args=(input_file, output_file, title, author), daemon=True).start()

    def generate_epub(self, input_file, output_file, title, author):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                raw_text = f.read()

            gen = EpubGenerator(title, author)
            gen.process_text(raw_text)
            gen.generate(output_file)
            
            self.root.after(0, lambda: self.finish_generation(True, output_file))
        except Exception as e:
            self.root.after(0, lambda: self.finish_generation(False, str(e)))

    def finish_generation(self, success, message):
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state=tk.NORMAL)
        
        if success:
            self.status_var.set("변환 완료!")
            messagebox.showinfo("성공", f"EPUB 파일이 성공적으로 생성되었습니다!\n\n위치: {message}")
        else:
            self.status_var.set("오류 발생")
            messagebox.showerror("실패", f"변환 중 오류가 발생했습니다:\n{message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = EpubGuiApp(root)
    root.mainloop()
