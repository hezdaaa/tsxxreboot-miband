import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# 支持的图片格式
IMG_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}


def is_pure_digit_filename(filename):
    """判断文件名（不含扩展名）是否全由数字及可选一个小数点组成，且格式为合法的数字（例如 "1"、"2.5"、"100"）。"""
    name = os.path.splitext(filename)[0]
    return bool(re.fullmatch(r'\d+(?:\.\d+)?', name))


def natural_sort_key(filename):
    """生成用于自然排序的键值。返回元组 (not is_pure_digit, 自然排序分解列表)"""
    name = os.path.splitext(filename)[0]
    pure = is_pure_digit_filename(filename)

    def convert(text):
        return int(text) if text.isdigit() else text.lower()

    parts = [convert(c) for c in re.split(r'(\d+)', name) if c]
    return (not pure, parts)


def get_image_files(folder):
    """返回文件夹下所有图片文件的完整路径列表"""
    files = []
    try:
        for f in os.listdir(folder):
            ext = os.path.splitext(f)[1].lower()
            if ext in IMG_EXTS:
                files.append(os.path.join(folder, f))
    except Exception:
        pass
    return files


def sort_images(files):
    """排序规则：
    1. 纯数字文件名（如 "1.png", "2.5.png"）排在前面，按数值升序。
    2. 其他文件按自然顺序排列（例如 a1-1 < a1-2 < a2-1 < a10）。
    """
    pure_digit = [f for f in files if is_pure_digit_filename(os.path.basename(f))]
    pure_digit.sort(key=lambda x: float(os.path.splitext(os.path.basename(x))[0]))

    normal = [f for f in files if not is_pure_digit_filename(os.path.basename(f))]
    normal.sort(key=lambda x: natural_sort_key(os.path.basename(x)))

    return pure_digit + normal


def find_all_subfolders(root_path):
    """返回根目录下所有直接子文件夹（仅一级），按名称自然排序"""
    if not os.path.isdir(root_path):
        return []

    subfolders = []
    for name in os.listdir(root_path):
        full = os.path.join(root_path, name)
        if os.path.isdir(full):
            subfolders.append((name, full))

    # 按名称自然排序
    subfolders.sort(key=lambda x: natural_sort_key(x[0]))
    return subfolders


class RenameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量重命名 - 自然排序 & 自动覆盖")
        self.root.geometry("850x650")

        self.parent_folder = tk.StringVar()
        self.subfolders = []           # 存储 (文件夹名, 完整路径)
        self.current_subfolder = tk.StringVar()
        self.preview_data = []          # 当前选中文件夹的预览数据

        # ----- 顶部：选择根目录 -----
        top_frame = ttk.LabelFrame(root, text="1. 选择包含子文件夹的根目录", padding=10)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        select_frame = ttk.Frame(top_frame)
        select_frame.pack(fill=tk.X)
        ttk.Label(select_frame, text="根目录:").pack(side=tk.LEFT)
        ttk.Entry(select_frame, textvariable=self.parent_folder, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(select_frame, text="浏览", command=self.select_parent_folder).pack(side=tk.LEFT)
        ttk.Button(select_frame, text="扫描子文件夹", command=self.scan_subfolders).pack(side=tk.LEFT, padx=5)

        # 扫描结果显示区域
        result_frame = ttk.LabelFrame(top_frame, text="检测到的子文件夹", padding=5)
        result_frame.pack(fill=tk.X, pady=10)

        self.subfolder_listbox = tk.Listbox(result_frame, height=4, exportselection=False)
        self.subfolder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_sub = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.subfolder_listbox.yview)
        self.subfolder_listbox.configure(yscrollcommand=scroll_sub.set)
        scroll_sub.pack(side=tk.RIGHT, fill=tk.Y)

        # 选择预览子文件夹
        preview_select_frame = ttk.Frame(top_frame)
        preview_select_frame.pack(fill=tk.X, pady=5)
        ttk.Label(preview_select_frame, text="选择要预览的子文件夹:").pack(side=tk.LEFT)
        self.subfolder_combo = ttk.Combobox(preview_select_frame, textvariable=self.current_subfolder,
                                            state="readonly", width=30)
        self.subfolder_combo.pack(side=tk.LEFT, padx=5)
        self.subfolder_combo.bind('<<ComboboxSelected>>', self.on_subfolder_selected)
        ttk.Button(preview_select_frame, text="刷新预览", command=self.refresh_preview).pack(side=tk.LEFT, padx=5)

        # ----- 预览表格 -----
        preview_frame = ttk.LabelFrame(root, text="2. 重命名预览", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("原文件名", "新文件名")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=18)
        self.tree.heading("原文件名", text="原文件名")
        self.tree.heading("新文件名", text="新文件名")
        self.tree.column("原文件名", width=450)
        self.tree.column("新文件名", width=250)

        tree_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ----- 底部按钮 -----
        bottom_frame = ttk.Frame(root, padding=10)
        bottom_frame.pack(fill=tk.X)
        ttk.Button(bottom_frame, text="执行所有子文件夹的重命名（自动覆盖）", command=self.execute_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="退出", command=root.quit).pack(side=tk.RIGHT, padx=5)

        self.status_var = tk.StringVar()
        ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, padx=10, pady=5)

    def select_parent_folder(self):
        folder = filedialog.askdirectory(title="选择包含子文件夹的根目录")
        if folder:
            self.parent_folder.set(folder)
            self.scan_subfolders()

    def scan_subfolders(self):
        parent = self.parent_folder.get()
        if not parent:
            messagebox.showwarning("提示", "请先选择根目录")
            return

        self.subfolders = find_all_subfolders(parent)
        self.subfolder_listbox.delete(0, tk.END)
        if not self.subfolders:
            messagebox.showinfo("提示", "未找到任何子文件夹")
            self.subfolder_combo['values'] = []
            self.current_subfolder.set("")
            self.clear_preview()
            self.status_var.set("未找到子文件夹")
            return

        for name, path in self.subfolders:
            self.subfolder_listbox.insert(tk.END, f"{name}  ({path})")

        self.subfolder_combo['values'] = [name for name, _ in self.subfolders]
        self.current_subfolder.set(self.subfolders[0][0])
        self.refresh_preview()
        self.status_var.set(f"找到 {len(self.subfolders)} 个子文件夹")

    def on_subfolder_selected(self, event=None):
        self.refresh_preview()

    def refresh_preview(self):
        folder_name = self.current_subfolder.get()
        if not folder_name:
            return

        folder_path = None
        for name, path in self.subfolders:
            if name == folder_name:
                folder_path = path
                break

        if not folder_path:
            return

        files = get_image_files(folder_path)
        if not files:
            self.clear_preview()
            self.status_var.set(f"子文件夹 {folder_name} 中没有图片文件")
            return

        sorted_files = sort_images(files)
        self.clear_preview()
        self.preview_data = []

        for idx, fpath in enumerate(sorted_files, start=1):
            base = os.path.basename(fpath)
            ext = os.path.splitext(base)[1]
            new_name = f"Page_{idx}{ext}"
            self.preview_data.append((fpath, new_name))
            self.tree.insert("", tk.END, values=(base, new_name))

        self.status_var.set(f"子文件夹 {folder_name}: 共 {len(sorted_files)} 张图片")

    def clear_preview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.preview_data = []

    def execute_all(self):
        if not self.subfolders:
            messagebox.showinfo("提示", "没有可处理的子文件夹")
            return

        if not messagebox.askyesno("确认", f"将对 {len(self.subfolders)} 个子文件夹执行重命名，\n"
                                           f"若目标文件已存在将自动覆盖，是否继续？"):
            return

        total_renamed = 0
        errors = []

        for folder_name, folder_path in self.subfolders:
            files = get_image_files(folder_path)
            if not files:
                continue

            sorted_files = sort_images(files)
            rename_map = {}
            for idx, fpath in enumerate(sorted_files, start=1):
                ext = os.path.splitext(fpath)[1]
                new_name = f"Page_{idx}{ext}"
                rename_map[fpath] = new_name

            # 直接重命名，使用 os.replace 强制覆盖
            for old_path, new_name in rename_map.items():
                new_path = os.path.join(folder_path, new_name)
                try:
                    os.replace(old_path, new_path)
                    total_renamed += 1
                except Exception as e:
                    errors.append(f"子文件夹 {folder_name}: {os.path.basename(old_path)} 失败 - {e}")

        # 刷新当前预览
        if self.current_subfolder.get():
            self.refresh_preview()

        # 结果汇报
        if errors:
            messagebox.showerror("部分错误", f"完成 {total_renamed} 个文件，以下错误:\n" + "\n".join(errors[:10]))
            self.status_var.set(f"完成，部分错误，共重命名 {total_renamed} 个文件")
        else:
            messagebox.showinfo("完成", f"全部成功，共重命名 {total_renamed} 个文件")
            self.status_var.set(f"批量完成，共处理 {total_renamed} 个文件")


def main():
    root = tk.Tk()
    app = RenameApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()