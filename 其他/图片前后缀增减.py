import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

class BatchRenameTool:
    def __init__(self, root):
        self.root = root
        self.root.title("批量文件重命名 - 添加/移除 前缀/后缀")
        self.root.geometry("850x650")
        self.root.resizable(True, True)

        # 变量
        self.folder_path = tk.StringVar()
        self.operation = tk.StringVar()          # 操作类型
        self.operation.set("添加前缀")
        self.process_string = tk.StringVar()     # 要添加或移除的字符串
        self.case_sensitive = tk.BooleanVar(value=False)  # 仅移除操作有用
        self.recursive = tk.BooleanVar(value=False)
        self.filter_type = tk.StringVar()        # 过滤类型
        self.filter_type.set("所有文件")
        self.custom_extensions = tk.StringVar()  # 自定义扩展名（逗号分隔）

        # 常用图片扩展名（供过滤选择）
        self.image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico'}
        self.all_exts_preset = ["所有文件", "图片文件", "自定义"]

        self.create_widgets()
        self.update_ui_for_operation()   # 初始更新控件状态

    # ---------- 界面构建 ----------
    def create_widgets(self):
        # 文件夹选择区
        frame_select = tk.LabelFrame(self.root, text="选择文件夹", padx=5, pady=5)
        frame_select.pack(fill="x", padx=10, pady=5)

        tk.Entry(frame_select, textvariable=self.folder_path, width=50).pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(frame_select, text="浏览...", command=self.select_folder).pack(side="right", padx=5)

        # 操作设置区
        frame_ops = tk.LabelFrame(self.root, text="重命名设置", padx=5, pady=5)
        frame_ops.pack(fill="x", padx=10, pady=5)

        # 操作类型下拉框
        tk.Label(frame_ops, text="操作类型：").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.operation_combo = ttk.Combobox(frame_ops, textvariable=self.operation,
                                            values=["添加前缀", "添加后缀", "移除前缀", "移除后缀"],
                                            state="readonly", width=12)
        self.operation_combo.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.operation_combo.bind("<<ComboboxSelected>>", lambda e: self.update_ui_for_operation())

        # 字符串输入（标签动态变化）
        self.string_label = tk.Label(frame_ops, text="要添加的前缀：")
        self.string_label.grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.string_entry = tk.Entry(frame_ops, textvariable=self.process_string, width=25)
        self.string_entry.grid(row=0, column=3, sticky="w", padx=5, pady=2)

        # 大小写敏感复选框（移除操作时才有效）
        self.case_check = tk.Checkbutton(frame_ops, text="区分大小写", variable=self.case_sensitive)
        self.case_check.grid(row=0, column=4, padx=10, pady=2)

        # 递归复选框
        tk.Checkbutton(frame_ops, text="包含子文件夹", variable=self.recursive).grid(row=0, column=5, padx=5, pady=2)

        # 过滤设置区
        frame_filter = tk.LabelFrame(self.root, text="文件过滤", padx=5, pady=5)
        frame_filter.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_filter, text="文件类型：").pack(side="left", padx=5)
        self.filter_combo = ttk.Combobox(frame_filter, textvariable=self.filter_type,
                                         values=self.all_exts_preset, state="readonly", width=12)
        self.filter_combo.pack(side="left", padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.toggle_custom_ext())

        self.ext_label = tk.Label(frame_filter, text="扩展名（逗号分隔）：")
        self.ext_entry = tk.Entry(frame_filter, textvariable=self.custom_extensions, width=20)
        self.ext_label.pack(side="left", padx=5)
        self.ext_entry.pack(side="left", padx=5)
        self.ext_label.pack_forget()   # 初始隐藏
        self.ext_entry.pack_forget()
        self.custom_extensions.set(".jpg,.png,.gif")  # 默认示例

        # 操作按钮区
        frame_buttons = tk.Frame(self.root)
        frame_buttons.pack(fill="x", padx=10, pady=5)

        tk.Button(frame_buttons, text="预览修改", command=self.preview_rename, bg="#e0e0e0").pack(side="left", padx=5)
        tk.Button(frame_buttons, text="执行重命名", command=self.execute_rename, bg="#4caf50", fg="white").pack(side="left", padx=5)
        tk.Button(frame_buttons, text="清空日志", command=self.clear_log).pack(side="left", padx=5)

        # 文件列表表格（预览）
        frame_list = tk.LabelFrame(self.root, text="文件列表（预览显示修改前后）", padx=5, pady=5)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("原文件名", "新文件名", "状态")
        self.tree = ttk.Treeview(frame_list, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.column("原文件名", width=250)
        self.tree.column("新文件名", width=250)
        self.tree.column("状态", width=120)
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

    # ---------- 控件联动 ----------
    def update_ui_for_operation(self):
        op = self.operation.get()
        if op == "添加前缀":
            self.string_label.config(text="要添加的前缀：")
            self.case_check.config(state="disabled")
        elif op == "添加后缀":
            self.string_label.config(text="要添加的后缀：")
            self.case_check.config(state="disabled")
        elif op == "移除前缀":
            self.string_label.config(text="要去除的前缀：")
            self.case_check.config(state="normal")
        elif op == "移除后缀":
            self.string_label.config(text="要去除的后缀：")
            self.case_check.config(state="normal")

    def toggle_custom_ext(self):
        if self.filter_type.get() == "自定义":
            self.ext_label.pack(side="left", padx=5)
            self.ext_entry.pack(side="left", padx=5)
        else:
            self.ext_label.pack_forget()
            self.ext_entry.pack_forget()

    # ---------- 文件夹选择 ----------
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

    # ---------- 文件收集（根据过滤条件） ----------
    def get_files(self):
        folder = self.folder_path.get().strip()
        if not folder or not os.path.isdir(folder):
            return []

        # 解析扩展名集合
        ext_filter = set()
        filter_type = self.filter_type.get()
        if filter_type == "图片文件":
            ext_filter = self.image_exts
        elif filter_type == "自定义":
            raw = self.custom_extensions.get().strip()
            if raw:
                parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
                ext_filter = set(p if p.startswith(".") else "." + p for p in parts)

        # 遍历获取文件
        files = []
        if self.recursive.get():
            for root_dir, _, file_names in os.walk(folder):
                for f in file_names:
                    full_path = os.path.join(root_dir, f)
                    if self._ext_match(f, ext_filter):
                        rel_path = os.path.relpath(full_path, folder)
                        files.append((full_path, rel_path))
        else:
            for f in os.listdir(folder):
                full_path = os.path.join(folder, f)
                if os.path.isfile(full_path) and self._ext_match(f, ext_filter):
                    files.append((full_path, f))
        return files

    def _ext_match(self, filename, ext_set):
        """如果ext_set为空则不过滤"""
        if not ext_set:
            return True
        ext = Path(filename).suffix.lower()
        return ext in ext_set

    # ---------- 计算新文件名（核心逻辑） ----------
    def compute_new_name(self, old_name):
        op = self.operation.get()
        string = self.process_string.get().strip()
        if not string:
            return old_name

        # 对于后缀操作需要分离主体和扩展名
        if op in ("添加后缀", "移除后缀"):
            base, ext = os.path.splitext(old_name)
            if op == "添加后缀":
                return base + string + ext
            else:  # 移除后缀
                if not self.case_sensitive.get():
                    lower_base = base.lower()
                    lower_suffix = string.lower()
                    if lower_base.endswith(lower_suffix):
                        return base[:-len(string)] + ext
                else:
                    if base.endswith(string):
                        return base[:-len(string)] + ext
                return old_name
        else:  # 添加前缀 / 移除前缀
            if op == "添加前缀":
                return string + old_name
            else:  # 移除前缀
                if not self.case_sensitive.get():
                    lower_name = old_name.lower()
                    lower_prefix = string.lower()
                    if lower_name.startswith(lower_prefix):
                        return old_name[len(string):]
                else:
                    if old_name.startswith(string):
                        return old_name[len(string):]
                return old_name

    # ---------- 预览 ----------
    def preview_rename(self):
        self.clear_preview()
        files = self.get_files()
        if not files:
            self.log("未找到符合过滤条件的文件，请检查文件夹和过滤设置。")
            return

        op = self.operation.get()
        string = self.process_string.get().strip()
        if not string:
            self.log("警告：未输入字符串，预览不会改变文件名。")

        rename_map = {}
        for full_path, rel_path in files:
            dir_name = os.path.dirname(full_path)
            old_base = os.path.basename(full_path)
            new_base = self.compute_new_name(old_base)
            status = "待重命名" if new_base != old_base else "无变化"

            if new_base != old_base:
                new_full = os.path.join(dir_name, new_base)
                if os.path.exists(new_full):
                    status = "冲突：目标已存在"
                elif (dir_name, new_base) in rename_map:
                    status = "冲突：多个文件重名"
                else:
                    rename_map[(dir_name, new_base)] = full_path

            self.tree.insert("", tk.END, values=(rel_path, new_base, status))
        self.log("预览完成。")

    # ---------- 执行重命名 ----------
    def execute_rename(self):
        if not self.folder_path.get().strip():
            messagebox.showwarning("警告", "请先选择一个文件夹。")
            return

        string = self.process_string.get().strip()
        if not string:
            messagebox.showwarning("警告", "请输入要添加或移除的字符串。")
            return

        # 简单非法字符检查
        illegal_chars = r'\/:*?"<>|'
        if any(c in string for c in illegal_chars):
            messagebox.showerror("错误", f"字符串不能包含以下字符：{illegal_chars}")
            return

        files = self.get_files()
        if not files:
            self.log("未找到符合条件的文件。")
            return

        success = 0
        skip = 0
        conflict = 0
        rename_map = {}

        for full_path, rel_path in files:
            dir_name = os.path.dirname(full_path)
            old_base = os.path.basename(full_path)
            new_base = self.compute_new_name(old_base)

            if new_base == old_base:
                self.log(f"跳过：{rel_path} (无需重命名)")
                skip += 1
                continue

            new_full = os.path.join(dir_name, new_base)
            if os.path.exists(new_full):
                self.log(f"错误：{rel_path} -> {new_base} 目标文件已存在")
                conflict += 1
                continue
            if (dir_name, new_base) in rename_map:
                self.log(f"错误：{rel_path} -> {new_base} 与另一个文件重名冲突")
                conflict += 1
                continue

            try:
                os.rename(full_path, new_full)
                self.log(f"成功：{rel_path} -> {new_base}")
                rename_map[(dir_name, new_base)] = full_path
                success += 1
            except Exception as e:
                self.log(f"异常：{rel_path} 重命名失败 - {str(e)}")
                conflict += 1

        self.log(f"\n操作完成：成功 {success} 个，跳过 {skip} 个，失败/冲突 {conflict} 个。")
        # 预览更新
        self.preview_rename()

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchRenameTool(root)
    root.mainloop()