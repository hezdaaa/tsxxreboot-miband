import os
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import Counter
import threading
import copy

def extract_cg_name(name):
    """直接返回CG名称（无后缀拆分）"""
    return name if name else ''

class CGBatchRenameTool:
    def __init__(self, root):
        self.root = root
        self.root.title("CG批量重命名工具（增强版）")
        self.root.geometry("1000x750")
        self.root.configure(bg='#1e1e1e')

        # 数据存储
        self.script_path = ""
        self.script_files = []
        self.all_data = {}
        self.cg_stats = Counter()
        self.cg_first_id = {}          # 新增：记录每个CG首次出现的ID
        self.modified = False

        # 历史记录
        self.history = []
        self.history_limit = 20

        # 隐藏sd标志
        self.hide_sd = tk.BooleanVar(value=False)

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
        style.configure('TCheckbutton', background='#1e1e1e', foreground='#d4d4d4')

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

        # 左侧：CG列表
        left_frame = ttk.LabelFrame(main_panel, text="CG统计", padding=5)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0,5))

        # 搜索框 + 隐藏sd选项
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill="x", pady=5)

        ttk.Label(search_frame, text="筛选:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind('<KeyRelease>', self.filter_list)

        # 新增：隐藏sd复选框
        self.hide_sd_check = ttk.Checkbutton(
            search_frame, text="隐藏 sd 开头", variable=self.hide_sd,
            command=self.filter_list
        )
        self.hide_sd_check.pack(side="left", padx=5)

        # CG列表（带滚动条）
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.cg_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            bg='#252526',
            fg='#d4d4d4',
            selectbackground='#264f78',
            selectforeground='#ffffff',
            relief='flat'
        )
        self.cg_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.cg_listbox.yview)

        # 双击列表项：填入旧名称并自动预览
        self.cg_listbox.bind('<Double-Button-1>', self.on_listbox_double_click)

        # 右侧：替换操作
        right_frame = ttk.LabelFrame(main_panel, text="批量替换（完整名称匹配）", padding=10)
        right_frame.pack(side="right", fill="y", padx=(5,0))

        ttk.Label(right_frame, text="旧CG名称:").grid(row=0, column=0, sticky="w", pady=5)
        self.old_name_var = tk.StringVar()
        old_entry = ttk.Entry(right_frame, textvariable=self.old_name_var, width=25)
        old_entry.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(right_frame, text="新CG名称:").grid(row=1, column=0, sticky="w", pady=5)
        self.new_name_var = tk.StringVar()
        new_entry = ttk.Entry(right_frame, textvariable=self.new_name_var, width=25)
        new_entry.grid(row=1, column=1, pady=5, padx=5)

        # 替换选项
        self.match_case_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(right_frame, text="区分大小写", variable=self.match_case_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(right_frame, text="替换预览:").grid(row=3, column=0, columnspan=2, sticky="w", pady=(10,0))
        self.preview_text = scrolledtext.ScrolledText(
            right_frame, width=35, height=10,
            bg='#252526', fg='#d4d4d4', insertbackground='#d4d4d4',
            font=("Consolas", 9)
        )
        self.preview_text.grid(row=4, column=0, columnspan=2, pady=5)
        self.preview_text.insert('1.0', "双击左侧CG名称或点击“预览替换”查看影响\n")
        self.preview_text.config(state='disabled')

        btn_frame = ttk.Frame(right_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="预览替换", command=self.preview_replace).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="执行替换", command=self.execute_replace).pack(side="left", padx=2)

        # 去除 ev 末尾字符按钮
        ev_btn_frame = ttk.Frame(right_frame)
        ev_btn_frame.grid(row=6, column=0, columnspan=2, pady=5)
        ttk.Button(ev_btn_frame, text="去除所有 ev 开头的 CG 的最后一个字符",
                   command=self.preview_ev_trim, width=35).pack()

        # 新增：去除特定格式CG按钮
        remove_btn_frame = ttk.Frame(right_frame)
        remove_btn_frame.grid(row=7, column=0, columnspan=2, pady=5)
        ttk.Button(remove_btn_frame, text="去除特定格式CG（以 {'fliptype': 'vlist', 'storage': 开头）",
                   command=self.preview_remove_special_cg, width=35).pack()

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
        self.cg_listbox.config(state='normal')
        self.cg_listbox.insert(tk.END, "请先加载脚本")

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
        self.cg_listbox.config(state='normal')
        self.cg_listbox.delete(0, tk.END)
        self.cg_listbox.insert(tk.END, "加载中，请稍候...")
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
            cg_counter = Counter()
            cg_first_id = {}   # 记录首次出现的ID

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
                    print(f"无法读取文件: {file_path}")
                    continue

                try:
                    data = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"JSON解析失败 {file_path}: {e}")
                    continue

                for key, value in data.items():
                    all_data[key] = value
                    if 'cg' in value and value['cg']:
                        cg_name = extract_cg_name(value['cg'])
                        cg_counter[cg_name] += 1
                        # 记录首次出现ID（取最小的ID）
                        if cg_name not in cg_first_id or int(key) < int(cg_first_id[cg_name]):
                            cg_first_id[cg_name] = key

            self.root.after(0, lambda: self._on_load_complete(all_data, cg_counter, cg_first_id))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"加载失败: {str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="加载失败", foreground="#ff6666"))

    def _on_load_complete(self, all_data, cg_counter, cg_first_id):
        self.all_data = all_data
        self.cg_stats = cg_counter
        self.cg_first_id = cg_first_id

        self.cg_listbox.config(state='normal')
        self.cg_listbox.delete(0, tk.END)
        self.filter_list()  # 应用当前筛选

        self.status_label.config(text=f"加载完成，共 {len(all_data)} 条对话，{len(cg_counter)} 个不同CG", foreground="#6a9955")
        self.modified = False
        self.modified_label.config(text="")

    def filter_list(self, event=None):
        """根据搜索文本和隐藏sd标志刷新列表"""
        search = self.search_var.get().lower()
        hide_sd = self.hide_sd.get()
        self.cg_listbox.config(state='normal')
        self.cg_listbox.delete(0, tk.END)

        if not self.cg_stats:
            self.cg_listbox.insert(tk.END, "暂无数据")
            return

        # 排序：按名称升序
        items = sorted(self.cg_stats.items(), key=lambda x: x[0].lower())
        for name, count in items:
            # 隐藏sd开头的CG（不区分大小写）
            if hide_sd and name.lower().startswith('sd'):
                continue
            # 搜索筛选
            if search and search not in name.lower():
                continue
            # 获取首次出现ID，如果没有则显示未知
            first_id = self.cg_first_id.get(name, '?')
            self.cg_listbox.insert(tk.END, f"[{first_id}] {name}  ({count} 次)")

    def on_listbox_double_click(self, event):
        try:
            selection = self.cg_listbox.curselection()
            if selection:
                line = self.cg_listbox.get(selection[0])
                match = re.search(r'\]\s*(.+?)\s+\(', line)
                if match:
                    cg_name = match.group(1).strip()
                    self.old_name_var.set(cg_name)
                    self.new_name_var.set(cg_name)  # 新增：同时填充新名称输入框
                    self.status_label.config(text=f"已选择: {cg_name}，正在预览...", foreground="#569cd6")
                    self.preview_replace()
        except Exception as e:
            print(f"双击事件出错: {e}")

    def get_first_matching_dialog(self, old_cg, match_case):
        """返回第一个匹配的对话 (id, 说话人, 对话内容)"""
        for dialog_id, script in self.all_data.items():
            if 'cg' in script and script['cg']:
                cg_val = script['cg']
                if (match_case and cg_val == old_cg) or (not match_case and cg_val.lower() == old_cg.lower()):
                    speaker = script.get('s', '（未知说话人）')
                    content = script.get('t', '（无对话文本）')
                    if len(content) > 200:
                        content = content[:200] + "..."
                    return dialog_id, speaker, content
        return None, None, None

    def preview_replace(self):
        old = self.old_name_var.get().strip()
        new = self.new_name_var.get().strip()
        if not old:
            messagebox.showwarning("警告", "请输入旧CG名称")
            return

        match_case = self.match_case_var.get()
        affected = 0
        examples = []

        for script in self.all_data.values():
            if 'cg' in script:
                cg_val = script['cg']
                if (match_case and cg_val == old) or (not match_case and cg_val.lower() == old.lower()):
                    affected += 1
                    if len(examples) < 3:
                        examples.append(cg_val)

        first_id, first_speaker, first_content = self.get_first_matching_dialog(old, match_case)

        preview = f"旧CG: {old}\n新CG: {new}\n区分大小写: {'是' if match_case else '否'}\n"
        preview += f"将影响 {affected} 条对话\n\n"

        if first_id is not None:
            preview += f"【首个匹配对话】\n编号: {first_id}\n说话人: {first_speaker}\n内容: {first_content}\n\n"
        else:
            preview += "（无匹配对话）\n\n"

        if examples:
            preview += "示例原CG名称:\n" + "\n".join(examples) + "\n\n"
            preview += "替换后示例:\n"
            for ex in examples:
                preview += f"{ex} -> {new}\n"
        else:
            preview += "无匹配项"

        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', preview)
        self.preview_text.config(state='disabled')

    def preview_ev_trim(self):
        """预览去除所有 ev 开头 CG 的最后一个字符的效果"""
        ev_names = {name for name in self.cg_stats.keys() if name.lower().startswith('ev')}
        if not ev_names:
            messagebox.showinfo("提示", "没有找到以 ev 开头的 CG 名称")
            return

        mapping = {}
        conflicts = []
        for name in ev_names:
            if len(name) <= 2:
                conflicts.append(f"“{name}” 长度过短，无法去除末尾字符")
                continue
            new_name = name[:-1]
            if new_name in ev_names:
                conflicts.append(f"“{name}” 去除后与已有的 “{new_name}” 冲突")
            mapping[name] = new_name

        if not mapping:
            messagebox.showwarning("警告", "没有可处理的 ev CG（可能都存在冲突或长度不足）")
            return

        affected_total = sum(self.cg_stats[name] for name in mapping)

        sample_old = next(iter(mapping.keys()))
        sample_new = mapping[sample_old]
        first_id, first_speaker, first_content = self.get_first_matching_dialog(sample_old, True)

        preview = f"【批量去除 ev 末尾字符】\n将处理 {len(mapping)} 个不同的 ev CG，共影响 {affected_total} 条对话。\n\n"
        if conflicts:
            preview += "⚠️ 警告：以下项目将被跳过：\n" + "\n".join(conflicts) + "\n\n"
        preview += "示例转换：\n"
        for i, (old_c, new_c) in enumerate(list(mapping.items())[:5]):
            preview += f"{old_c}  ->  {new_c}\n"
        if len(mapping) > 5:
            preview += f"... 等 {len(mapping)} 项\n\n"

        if first_id is not None:
            preview += f"【首个匹配对话（使用 {sample_old}）】\n编号: {first_id}\n说话人: {first_speaker}\n内容: {first_content}\n\n"

        preview += "是否确认执行此批量替换？"

        if messagebox.askyesno("确认批量替换", preview):
            self.execute_ev_trim(mapping)

    def execute_ev_trim(self, mapping):
        self.push_history()
        replaced_count = 0
        for script in self.all_data.values():
            if 'cg' in script:
                old_cg = script['cg']
                if old_cg in mapping:
                    new_cg = mapping[old_cg]
                    script['cg'] = new_cg
                    replaced_count += 1

        if replaced_count > 0:
            self.modified = True
            self.modified_label.config(text="有未保存的修改")
            self.status_label.config(text=f"已去除 ev 末尾字符，共替换 {replaced_count} 处，请记得保存", foreground="#ffcc00")
            self.rebuild_stats()
        else:
            messagebox.showinfo("提示", "没有找到需要替换的 ev CG")
            self.history.pop()

    # ================= 新增功能：去除特定格式CG =================
    def preview_remove_special_cg(self):
        """预览删除所有以特定字符串开头的CG字段"""
        target_prefix = "{'fliptype': 'vlist', 'storage':"
        affected = 0
        examples = []
        for script in self.all_data.values():
            if 'cg' in script and script['cg']:
                cg_val = script['cg']
                if cg_val.startswith(target_prefix):
                    affected += 1
                    if len(examples) < 3:
                        examples.append(cg_val)

        if affected == 0:
            messagebox.showinfo("提示", "没有找到需要删除的CG字段")
            return

        # 获取第一个匹配对话的信息
        first_id, first_speaker, first_content = None, None, None
        for dialog_id, script in self.all_data.items():
            if 'cg' in script and script['cg'] and script['cg'].startswith(target_prefix):
                first_id = dialog_id
                first_speaker = script.get('s', '（未知说话人）')
                first_content = script.get('t', '（无对话文本）')
                if len(first_content) > 200:
                    first_content = first_content[:200] + "..."
                break

        preview = f"【删除特定格式CG】\n将删除所有以如下前缀开头的CG字段：\n{target_prefix}\n"
        preview += f"共影响 {affected} 条对话。\n\n"
        if examples:
            preview += "示例（将被删除的CG值）：\n" + "\n".join(examples) + "\n\n"
        if first_id:
            preview += f"【首个匹配对话】\n编号: {first_id}\n说话人: {first_speaker}\n内容: {first_content}\n\n"
        preview += "是否确认删除这些CG字段？"

        if messagebox.askyesno("确认删除", preview):
            self.execute_remove_special_cg(target_prefix)

    def execute_remove_special_cg(self, target_prefix):
        self.push_history()
        removed_count = 0
        for script in self.all_data.values():
            if 'cg' in script and script['cg'] and script['cg'].startswith(target_prefix):
                del script['cg']   # 直接删除该字段
                removed_count += 1

        if removed_count > 0:
            self.modified = True
            self.modified_label.config(text="有未保存的修改")
            self.status_label.config(text=f"已删除 {removed_count} 处特定格式CG，请记得保存", foreground="#ffcc00")
            self.rebuild_stats()
        else:
            messagebox.showinfo("提示", "没有找到需要删除的CG")
            self.history.pop()
    # =======================================================

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
        self.status_label.config(text="已撤回上一次操作", foreground="#ffcc00")
        self.rebuild_stats()

    def execute_replace(self):
        old = self.old_name_var.get().strip()
        new = self.new_name_var.get().strip()
        if not old:
            messagebox.showwarning("警告", "请输入旧CG名称")
            return

        if not messagebox.askyesno("确认替换", f"确定要将所有值为 '{old}' 的CG替换为 '{new}' 吗？\n此操作不可撤销，建议先备份。"):
            return

        match_case = self.match_case_var.get()
        self.push_history()

        replaced_count = 0
        for script in self.all_data.values():
            if 'cg' in script:
                cg_val = script['cg']
                if (match_case and cg_val == old) or (not match_case and cg_val.lower() == old.lower()):
                    script['cg'] = new
                    replaced_count += 1

        if replaced_count > 0:
            self.modified = True
            self.modified_label.config(text="有未保存的修改")
            self.status_label.config(text=f"已替换 {replaced_count} 处，请记得保存", foreground="#ffcc00")
            self.rebuild_stats()
        else:
            messagebox.showinfo("提示", "没有找到匹配的CG名称")
            self.history.pop()

    def rebuild_stats(self):
        new_counter = Counter()
        new_first_id = {}
        # 重新扫描所有数据，重建统计和首次ID
        for key, script in self.all_data.items():
            if 'cg' in script and script['cg']:
                cg_name = extract_cg_name(script['cg'])
                new_counter[cg_name] += 1
                if cg_name not in new_first_id or int(key) < int(new_first_id[cg_name]):
                    new_first_id[cg_name] = key
        self.cg_stats = new_counter
        self.cg_first_id = new_first_id
        self.filter_list()

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
    app = CGBatchRenameTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()