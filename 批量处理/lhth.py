import os
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import Counter
import threading
import copy

def split_character_name(name):
    """将立绘名称拆分为 (主体, 后缀)，后缀可能是 '_数字' 或空字符串"""
    if not name:
        return '', ''
    match = re.match(r'^(.*?)(_\d+)?$', name)
    if match:
        base = match.group(1) or ''
        suffix = match.group(2) or ''
        return base, suffix
    return name, ''

def extract_base_name(name):
    """仅提取主体部分"""
    base, _ = split_character_name(name)
    return base

class CharacterBatchRenameTool:
    def __init__(self, root):
        self.root = root
        self.root.title("立绘批量重命名工具（可选忽略后缀）")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e1e')

        # 数据存储
        self.script_path = ""
        self.script_files = []
        self.all_data = {}
        self.character_stats = Counter()
        self.modified = False

        # 历史记录
        self.history = []
        self.history_limit = 20

        # 选项变量
        self.ignore_suffix_var = tk.BooleanVar(value=True)   # 是否忽略数字后缀
        self.match_case_var = tk.BooleanVar(value=True)

        self.create_widgets()
        self.setup_styles()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#1e1e1e', foreground='#d4d4d4',
                        fieldbackground='#252526', selectbackground='#264f78')
        style.configure('TButton', background='#333333', foreground='#d4d4d4')
        style.map('TButton', background=[('active', '#555555')])
        style.configure('TLabel', background='#1e1e1e', foreground='#d4d4d4')
        style.configure('TLabelframe', background='#1e1e1e', foreground='#d4d4d4')
        style.configure('TEntry', fieldbackground='#252526', foreground='#d4d4d4')
        style.configure('TCombobox', fieldbackground='#252526', foreground='#d4d4d4')

    def create_widgets(self):
        # 顶部框架：选择文件夹
        top_frame = ttk.LabelFrame(self.root, text="脚本文件夹", padding=10)
        top_frame.pack(fill="x", padx=10, pady=5)

        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(top_frame, textvariable=self.path_var, width=60)
        path_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)

        ttk.Button(top_frame, text="浏览...", command=self.select_folder).pack(side="left", padx=2)
        ttk.Button(top_frame, text="加载脚本", command=self.load_scripts_thread).pack(side="left", padx=2)

        # 主内容区域：左右分栏
        main_panel = ttk.Frame(self.root)
        main_panel.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧：立绘列表
        left_frame = ttk.LabelFrame(main_panel, text="立绘统计（可根据后缀选项变化）", padding=5)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0,5))

        # 搜索框
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill="x", pady=5)
        ttk.Label(search_frame, text="筛选:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind('<KeyRelease>', self.filter_list)

        # 立绘列表（带滚动条）
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.character_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            bg='#252526',
            fg='#d4d4d4',
            selectbackground='#264f78',
            selectforeground='#ffffff',
            relief='flat'
        )
        self.character_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.character_listbox.yview)
        self.character_listbox.bind('<Double-Button-1>', self.on_listbox_double_click)

        # 右侧：替换操作
        right_frame = ttk.LabelFrame(main_panel, text="批量替换", padding=10)
        right_frame.pack(side="right", fill="y", padx=(5,0))

        ttk.Label(right_frame, text="旧名称:").grid(row=0, column=0, sticky="w", pady=5)
        self.old_name_var = tk.StringVar()
        old_entry = ttk.Entry(right_frame, textvariable=self.old_name_var, width=25)
        old_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(right_frame, text="新名称:").grid(row=1, column=0, sticky="w", pady=5)
        self.new_name_var = tk.StringVar()
        new_entry = ttk.Entry(right_frame, textvariable=self.new_name_var, width=25)
        new_entry.grid(row=1, column=1, pady=5, padx=5)

        # 选项区
        ttk.Checkbutton(right_frame, text="区分大小写", variable=self.match_case_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Checkbutton(right_frame, text="匹配时忽略数字后缀（替换时保留原后缀）",
                        variable=self.ignore_suffix_var,
                        command=self.on_ignore_suffix_changed).grid(row=3, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(right_frame, text="替换预览:").grid(row=4, column=0, columnspan=2, sticky="w", pady=(10,0))
        self.preview_text = scrolledtext.ScrolledText(
            right_frame, width=30, height=8,
            bg='#252526', fg='#d4d4d4', insertbackground='#d4d4d4',
            font=("Consolas", 9)
        )
        self.preview_text.grid(row=5, column=0, columnspan=2, pady=5)
        self.preview_text.insert('1.0', "点击“预览替换”查看影响\n")
        self.preview_text.config(state='disabled')

        btn_frame = ttk.Frame(right_frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="预览替换", command=self.preview_replace).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="执行替换", command=self.execute_replace).pack(side="left", padx=2)

        # 底部状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side="bottom", fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(status_frame, text="就绪", foreground="#6a9955")
        self.status_label.pack(side="left")

        self.modified_label = ttk.Label(status_frame, text="", foreground="#ffcc00")
        self.modified_label.pack(side="right")

        ttk.Button(status_frame, text="保存所有修改", command=self.save_all).pack(side="right", padx=5)
        ttk.Button(status_frame, text="撤回", command=self.undo).pack(side="right", padx=5)

        # 初始化列表
        self.character_listbox.config(state='normal')
        self.character_listbox.insert(tk.END, "请先加载脚本")

    def select_folder(self):
        folder = filedialog.askdirectory(title="选择包含 scriptData*.txt 的文件夹")
        if folder:
            self.script_path = folder
            self.path_var.set(folder)
            self.status_label.config(text=f"已选择文件夹: {folder}", foreground="#569cd6")

    def load_scripts_thread(self):
        if not self.script_path:
            messagebox.showwarning("警告", "请先选择脚本文件夹")
            return

        self.status_label.config(text="正在加载脚本...", foreground="#569cd6")
        self.character_listbox.config(state='normal')
        self.character_listbox.delete(0, tk.END)
        self.character_listbox.insert(tk.END, "加载中，请稍候...")
        self.modified = False
        self.modified_label.config(text="")
        self.history.clear()

        thread = threading.Thread(target=self.load_scripts, daemon=True)
        thread.start()

    def load_scripts(self):
        try:
            script_files = []
            for f in os.listdir(self.script_path):
                if f.lower().startswith("scriptdata") and f.lower().endswith(".txt"):
                    script_files.append(os.path.join(self.script_path, f))

            if not script_files:
                self.root.after(0, lambda: messagebox.showwarning("警告", "未找到 scriptData*.txt 文件"))
                self.root.after(0, lambda: self.status_label.config(text="未找到脚本文件", foreground="#ff6666"))
                return

            script_files.sort()
            self.script_files = script_files

            all_data = {}

            total_files = len(script_files)
            for idx, file_path in enumerate(script_files):
                self.root.after(0, lambda i=idx+1, t=total_files: self.status_label.config(
                    text=f"正在加载 {i}/{t}: {os.path.basename(file_path)}", foreground="#569cd6"))

                content = None
                for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                if content is None:
                    continue

                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    continue

                for key, value in data.items():
                    all_data[key] = value

            self.root.after(0, lambda: self._on_load_complete(all_data))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"加载失败: {str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="加载失败", foreground="#ff6666"))

    def _on_load_complete(self, all_data):
        self.all_data = all_data
        self.refresh_stats()   # 根据当前 ignore_suffix 选项刷新统计
        self.status_label.config(text=f"加载完成，共 {len(all_data)} 条对话", foreground="#6a9955")
        self.modified = False
        self.modified_label.config(text="")

    def refresh_stats(self):
        """根据当前 ignore_suffix 选项重新计算统计并刷新列表"""
        if not self.all_data:
            self.character_stats = Counter()
            self.filter_list()
            return

        new_counter = Counter()
        for script in self.all_data.values():
            if 'c' in script and script['c']:
                name = script['c']
                if self.ignore_suffix_var.get():
                    key = extract_base_name(name)
                else:
                    key = name
                new_counter[key] += 1

        self.character_stats = new_counter
        self.filter_list()   # 应用过滤并刷新显示

    def on_ignore_suffix_changed(self):
        """当忽略后缀选项改变时，重新统计列表"""
        self.refresh_stats()
        # 同时清空预览区域，避免混淆
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', "选项已更改，请重新点击“预览替换”\n")
        self.preview_text.config(state='disabled')

    def filter_list(self, event=None):
        search = self.search_var.get().lower()
        self.character_listbox.config(state='normal')
        self.character_listbox.delete(0, tk.END)

        if not self.character_stats:
            self.character_listbox.insert(tk.END, "暂无数据")
        else:
            for name, count in sorted(self.character_stats.items(), key=lambda x: (-x[1], x[0])):
                if not search or search in name.lower():
                    self.character_listbox.insert(tk.END, f"{name}  ({count} 次)")
        # 保持 normal 状态

    def on_listbox_double_click(self, event):
        try:
            selection = self.character_listbox.curselection()
            if selection:
                line = self.character_listbox.get(selection[0])
                if '(' in line:
                    base_name = line.rsplit('  (', 1)[0].strip()
                    self.old_name_var.set(base_name)
                    self.status_label.config(text=f"已选择: {base_name}", foreground="#569cd6")
        except Exception as e:
            print(f"双击事件出错: {e}")

    def preview_replace(self):
        old = self.old_name_var.get().strip()
        new = self.new_name_var.get().strip()
        if not old:
            messagebox.showwarning("警告", "请输入旧名称")
            return

        ignore_suffix = self.ignore_suffix_var.get()
        match_case = self.match_case_var.get()

        affected = 0
        examples = []
        # 遍历所有对话统计匹配项
        for script in self.all_data.values():
            if 'c' not in script:
                continue
            current_name = script['c']
            # 匹配逻辑
            if ignore_suffix:
                current_compare = extract_base_name(current_name)
                old_compare = extract_base_name(old)
            else:
                current_compare = current_name
                old_compare = old

            if (match_case and current_compare == old_compare) or (not match_case and current_compare.lower() == old_compare.lower()):
                affected += 1
                if len(examples) < 3:
                    examples.append(current_name)

        # 构建预览文本
        preview = f"匹配模式: {'忽略数字后缀' if ignore_suffix else '精确匹配（保留后缀）'}\n"
        preview += f"旧名称: {old}\n新名称: {new}\n区分大小写: {'是' if match_case else '否'}\n"
        preview += f"将影响 {affected} 条对话\n\n"
        if examples:
            preview += "示例原名称:\n" + "\n".join(examples) + "\n\n"
            preview += "替换后示例:\n"
            for ex in examples:
                if ignore_suffix:
                    # 保留后缀
                    _, suffix = split_character_name(ex)
                    new_base = extract_base_name(new)
                    preview += f"{ex} -> {new_base}{suffix}\n"
                else:
                    preview += f"{ex} -> {new}\n"
        else:
            preview += "无匹配项"

        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', preview)
        self.preview_text.config(state='disabled')

    def push_history(self):
        if len(self.history) >= self.history_limit:
            self.history.pop(0)
        self.history.append(copy.deepcopy(self.all_data))

    def undo(self):
        if not self.history:
            messagebox.showinfo("提示", "没有可撤回的操作")
            return

        self.all_data = copy.deepcopy(self.history.pop())
        self.modified = True
        self.modified_label.config(text="有未保存的修改")
        self.status_label.config(text="已撤回上一次替换", foreground="#ffcc00")
        self.refresh_stats()

    def execute_replace(self):
        old = self.old_name_var.get().strip()
        new = self.new_name_var.get().strip()
        if not old:
            messagebox.showwarning("警告", "请输入旧名称")
            return

        ignore_suffix = self.ignore_suffix_var.get()
        match_case = self.match_case_var.get()

        # 确认对话框
        mode_str = "忽略后缀（保留原后缀）" if ignore_suffix else "精确匹配（完全替换）"
        if not messagebox.askyesno("确认替换",
                                   f"当前模式: {mode_str}\n"
                                   f"将把所有匹配 '{old}' 的立绘替换为 '{new}'。\n"
                                   f"此操作不可撤销，建议先备份。"):
            return

        self.push_history()

        replaced_count = 0
        for script in self.all_data.values():
            if 'c' not in script:
                continue
            current_name = script['c']
            # 匹配判断
            if ignore_suffix:
                current_compare = extract_base_name(current_name)
                old_compare = extract_base_name(old)
            else:
                current_compare = current_name
                old_compare = old

            if (match_case and current_compare == old_compare) or (not match_case and current_compare.lower() == old_compare.lower()):
                if ignore_suffix:
                    _, suffix = split_character_name(current_name)
                    new_base = extract_base_name(new)
                    script['c'] = new_base + suffix
                else:
                    script['c'] = new
                replaced_count += 1

        if replaced_count > 0:
            self.modified = True
            self.modified_label.config(text="有未保存的修改")
            self.status_label.config(text=f"已替换 {replaced_count} 处，请记得保存", foreground="#ffcc00")
            self.refresh_stats()
        else:
            messagebox.showinfo("提示", "没有找到匹配的立绘名称")
            self.history.pop()

    def save_all(self):
        if not self.modified:
            messagebox.showinfo("提示", "没有需要保存的修改")
            return

        if not self.script_files:
            messagebox.showerror("错误", "脚本文件列表为空")
            return

        try:
            saved_count = 0
            for file_path in self.script_files:
                base = os.path.basename(file_path)
                match = re.search(r'(\d+)', base)
                if not match:
                    continue
                chunk_num = int(match.group(1))
                start_id = (chunk_num - 1) * 500 + 1
                end_id = chunk_num * 500

                chunk_data = {}
                for i in range(start_id, end_id + 1):
                    key = str(i)
                    if key in self.all_data:
                        chunk_data[key] = self.all_data[key]

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk_data, f, ensure_ascii=False, indent=2)
                saved_count += 1

            self.modified = False
            self.modified_label.config(text="")
            self.history.clear()
            self.status_label.config(text=f"已保存 {saved_count} 个文件", foreground="#6a9955")
            messagebox.showinfo("保存成功", f"所有修改已保存到 {saved_count} 个文件中")
        except Exception as e:
            messagebox.showerror("保存失败", f"保存时发生错误: {str(e)}")
            self.status_label.config(text="保存失败", foreground="#ff6666")

def main():
    root = tk.Tk()
    app = CharacterBatchRenameTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()