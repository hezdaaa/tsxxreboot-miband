import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

class BatchRenameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量去后缀工具")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        # 变量
        self.folder_path = tk.StringVar()
        self.suffix_to_remove = tk.StringVar()
        self.case_sensitive = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=False)
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

        self.create_widgets()

    def create_widgets(self):
        # 选择文件夹区域
        frame_select = tk.LabelFrame(self.root, text="选择文件夹", padx=5, pady=5)
        frame_select.pack(fill="x", padx=10, pady=5)

        tk.Entry(frame_select, textvariable=self.folder_path, width=50).pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(frame_select, text="浏览...", command=self.select_folder).pack(side="right", padx=5)

        # 后缀设置区域
        frame_suffix = tk.LabelFrame(self.root, text="要去除的后缀", padx=5, pady=5)
        frame_suffix.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_suffix, text="后缀内容（如 _thumb）：").pack(side="left", padx=5)
        tk.Entry(frame_suffix, textvariable=self.suffix_to_remove, width=30).pack(side="left", padx=5)
        tk.Checkbutton(frame_suffix, text="区分大小写", variable=self.case_sensitive).pack(side="left", padx=10)
        tk.Checkbutton(frame_suffix, text="包含子文件夹", variable=self.recursive).pack(side="left", padx=10)

        # 预览按钮和操作按钮
        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(fill="x", padx=10, pady=5)
        tk.Button(frame_buttons, text="预览修改", command=self.preview_rename, bg="#e0e0e0").pack(side="left", padx=5)
        tk.Button(frame_buttons, text="执行重命名", command=self.execute_rename, bg="#4caf50", fg="white").pack(side="left", padx=5)
        tk.Button(frame_buttons, text="清空日志", command=self.clear_log).pack(side="left", padx=5)

        # 文件列表表格
        frame_list = tk.LabelFrame(self.root, text="文件列表（预览显示修改前后）", padx=5, pady=5)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("原文件名", "新文件名", "状态")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings")
        self.tree.heading("原文件名", text="原文件名")
        self.tree.heading("新文件名", text="新文件名")
        self.tree.heading("状态", text="状态")
        self.tree.column("原文件名", width=200)
        self.tree.column("新文件名", width=200)
        self.tree.column("状态", width=100)

        scrollbar = ttk.Scrollbar(frame_list, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 日志区域
        frame_log = tk.LabelFrame(self.root, text="操作日志", padx=5, pady=5)
        frame_log.pack(fill="both", expand=False, padx=10, pady=5)
        self.log_text = tk.Text(frame_log, height=8, wrap="word")
        scroll_log = ttk.Scrollbar(frame_log, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll_log.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll_log.pack(side="right", fill="y")

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.clear_preview()

    def clear_preview(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def get_image_files(self):
        folder = self.folder_path.get().strip()
        if not folder or not os.path.isdir(folder):
            return []
        images = []
        if self.recursive.get():
            for root, dirs, files in os.walk(folder):
                for f in files:
                    ext = Path(f).suffix.lower()
                    if ext in self.image_extensions:
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, folder)
                        images.append((full_path, rel_path))
        else:
            for f in os.listdir(folder):
                full_path = os.path.join(folder, f)
                if os.path.isfile(full_path):
                    ext = Path(f).suffix.lower()
                    if ext in self.image_extensions:
                        images.append((full_path, f))
        return images

    def compute_new_name(self, old_name):
        """去除主文件名末尾的指定后缀（保留扩展名）"""
        suffix = self.suffix_to_remove.get().strip()
        if not suffix:
            return old_name

        # 分离文件名和扩展名
        base, ext = os.path.splitext(old_name)

        if not self.case_sensitive.get():
            # 不区分大小写：比较时统一小写
            lower_base = base.lower()
            lower_suffix = suffix.lower()
            if lower_base.endswith(lower_suffix):
                # 截取原文件名（保留原始大小写）
                return base[:-len(suffix)] + ext
        else:
            if base.endswith(suffix):
                return base[:-len(suffix)] + ext

        return old_name

    def preview_rename(self):
        self.clear_preview()
        images = self.get_image_files()
        if not images:
            self.log("未找到任何图片文件，请确认文件夹路径和递归选项。")
            return

        suffix = self.suffix_to_remove.get().strip()
        if not suffix:
            self.log("警告：未输入要去除的后缀，预览不会修改任何文件名。")

        rename_map = {}
        for full_path, rel_path in images:
            dir_name = os.path.dirname(full_path)
            old_base = os.path.basename(full_path)
            new_base = self.compute_new_name(old_base)
            status = "待重命名" if new_base != old_base else "无变化"

            if new_base != old_base:
                new_full = os.path.join(dir_name, new_base)
                if os.path.exists(new_full):
                    status = "冲突：目标文件已存在"
                elif (dir_name, new_base) in rename_map:
                    status = "冲突：多个文件重命名后相同"
                else:
                    rename_map[(dir_name, new_base)] = full_path

            self.tree.insert("", tk.END, values=(rel_path, new_base, status))

        self.log("预览完成。")

    def execute_rename(self):
        if not self.folder_path.get().strip():
            messagebox.showwarning("警告", "请先选择一个文件夹。")
            return
        suffix = self.suffix_to_remove.get().strip()
        if not suffix:
            if not messagebox.askyesno("确认", "您没有输入要去除的后缀，将不会有任何文件被重命名。是否继续？"):
                return

        images = self.get_image_files()
        if not images:
            self.log("未找到图片文件。")
            return

        success_count = 0
        skip_count = 0
        conflict_count = 0

        rename_map = {}
        for full_path, rel_path in images:
            dir_name = os.path.dirname(full_path)
            old_base = os.path.basename(full_path)
            new_base = self.compute_new_name(old_base)

            if new_base == old_base:
                self.log(f"跳过：{rel_path} (无需重命名)")
                skip_count += 1
                continue

            new_full = os.path.join(dir_name, new_base)
            if os.path.exists(new_full):
                self.log(f"错误：{rel_path} -> {new_base} 失败，目标文件已存在")
                conflict_count += 1
                continue
            if (dir_name, new_base) in rename_map:
                self.log(f"错误：{rel_path} -> {new_base} 失败，与另一个文件重名冲突")
                conflict_count += 1
                continue

            try:
                os.rename(full_path, new_full)
                self.log(f"成功：{rel_path} -> {new_base}")
                rename_map[(dir_name, new_base)] = full_path
                success_count += 1
            except Exception as e:
                self.log(f"异常：{rel_path} 重命名失败 - {str(e)}")
                conflict_count += 1

        self.log(f"\n操作完成：成功 {success_count} 个，跳过 {skip_count} 个，失败/冲突 {conflict_count} 个。")
        self.preview_rename()

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchRenameApp(root)
    root.mainloop()