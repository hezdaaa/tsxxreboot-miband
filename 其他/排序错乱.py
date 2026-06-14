import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

class ScriptMoverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("脚本块移动与重排序工具")
        self.root.geometry("700x550")
        self.root.configure(bg='#1e1e1e')
        
        self.script_path = None          # common/script 目录
        self.full_data = {}              # {str(id): dict}
        self.total_dialogues = 0
        self.chunk_size = 500
        
        self.setup_ui()
        self.setup_style()
        
    # ---------- UI 构建 ----------
    def setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#1e1e1e', foreground='#d4d4d4',
                        fieldbackground='#252526', insertcolor='#d4d4d4')
        style.configure('TButton', background='#333333', foreground='#d4d4d4')
        style.map('TButton', background=[('active', '#555555')])
        style.configure('TLabel', background='#1e1e1e', foreground='#d4d4d4')
        style.configure('TLabelframe', background='#1e1e1e', foreground='#d4d4d4')
        style.configure('TEntry', fieldbackground='#252526', foreground='#d4d4d4')
        
    def setup_ui(self):
        # 路径选择
        path_frame = ttk.LabelFrame(self.root, text="项目设置", padding="10")
        path_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(path_frame, text="选择脚本目录 (common/script)", 
                   command=self.select_script_folder).pack(side="left", padx=5)
        self.path_label = ttk.Label(path_frame, text="未加载", foreground="#569cd6")
        self.path_label.pack(side="left", padx=10)
        
        self.info_label = ttk.Label(path_frame, text="对话总数: 0")
        self.info_label.pack(side="right", padx=10)
        
        # 移动操作区域
        move_frame = ttk.LabelFrame(self.root, text="移动脚本块", padding="10")
        move_frame.pack(fill="x", padx=10, pady=5)
        
        row1 = ttk.Frame(move_frame)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="起始ID:").pack(side="left", padx=5)
        self.start_id = ttk.Entry(row1, width=10)
        self.start_id.pack(side="left", padx=5)
        ttk.Label(row1, text="结束ID:").pack(side="left", padx=5)
        self.end_id = ttk.Entry(row1, width=10)
        self.end_id.pack(side="left", padx=5)
        ttk.Label(row1, text="目标ID:").pack(side="left", padx=5)
        self.target_id = ttk.Entry(row1, width=10)
        self.target_id.pack(side="left", padx=5)
        
        row2 = ttk.Frame(move_frame)
        row2.pack(fill="x", pady=5)
        self.insert_before = tk.BooleanVar(value=True)
        ttk.Radiobutton(row2, text="插入到目标ID之前", variable=self.insert_before, 
                        value=True).pack(side="left", padx=10)
        ttk.Radiobutton(row2, text="插入到目标ID之后", variable=self.insert_before, 
                        value=False).pack(side="left", padx=10)
        
        btn_frame = ttk.Frame(move_frame)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="执行移动并重排", command=self.move_and_renumber,
                   width=20).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="仅重新编号 (保持顺序)", command=self.renumber_only,
                   width=20).pack(side="left", padx=5)
        
        # 状态与保存
        action_frame = ttk.LabelFrame(self.root, text="操作", padding="10")
        action_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_label = ttk.Label(action_frame, text="就绪", foreground="#6a9955")
        self.status_label.pack(side="left", padx=5)
        
        ttk.Button(action_frame, text="备份脚本文件夹", command=self.backup_script,
                   width=15).pack(side="right", padx=5)
        ttk.Button(action_frame, text="保存更改到文件", command=self.save_all_changes,
                   width=15).pack(side="right", padx=5)
        ttk.Button(action_frame, text="重新加载脚本", command=self.reload_script,
                   width=15).pack(side="right", padx=5)
        
        # 输出日志
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding="10")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=12, bg='#252526', fg='#d4d4d4',
                                insertbackground='#d4d4d4', wrap='word')
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        
    # ---------- 核心数据加载与保存 ----------
    def log(self, msg, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "error":
            self.log_text.insert(tk.END, f"[{timestamp}] ❌ {msg}\n", "error")
            self.log_text.tag_config("error", foreground="#ff6666")
        elif level == "warning":
            self.log_text.insert(tk.END, f"[{timestamp}] ⚠️ {msg}\n", "warning")
            self.log_text.tag_config("warning", foreground="#ffcc00")
        else:
            self.log_text.insert(tk.END, f"[{timestamp}] ✅ {msg}\n", "info")
            self.log_text.tag_config("info", foreground="#6a9955")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def select_script_folder(self):
        folder = filedialog.askdirectory(title="选择 common/script 文件夹")
        if not folder:
            return
        # 检查是否是 script 目录，自动调整
        if os.path.basename(folder) != "script":
            if os.path.exists(os.path.join(folder, "script")):
                folder = os.path.join(folder, "script")
            else:
                messagebox.showerror("错误", "请选择正确的 script 文件夹（包含 scriptData*.txt）")
                return
        self.script_path = folder
        self.path_label.config(text=f"脚本目录: {folder}")
        self.load_all_scripts()
        
    def load_all_scripts(self):
        if not self.script_path:
            return
        self.full_data = {}
        files = [f for f in os.listdir(self.script_path) 
                 if f.lower().startswith("scriptdata") and f.lower().endswith(".txt")]
        if not files:
            self.log("未找到任何 scriptData*.txt 文件", "error")
            return
        
        def extract_num(name):
            match = re.search(r'(\d+)', name)
            return int(match.group(1)) if match else 0
        files.sort(key=extract_num)
        
        total = 0
        for filename in files:
            path = os.path.join(self.script_path, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    chunk = json.load(f)
                for k, v in chunk.items():
                    self.full_data[str(k)] = v
                total += len(chunk)
            except Exception as e:
                self.log(f"加载 {filename} 失败: {e}", "error")
        
        self.total_dialogues = len(self.full_data)
        self.info_label.config(text=f"对话总数: {self.total_dialogues}")
        self.log(f"成功加载 {self.total_dialogues} 条对话，来自 {len(files)} 个块文件")
        
    def save_all_changes(self):
        if not self.script_path or not self.full_data:
            self.log("没有数据可保存", "warning")
            return
        # 按新 ID 分块
        chunk_dict = {}
        for id_str, data in self.full_data.items():
            try:
                id_num = int(id_str)
            except:
                continue
            chunk_num = (id_num - 1) // self.chunk_size + 1
            if chunk_num not in chunk_dict:
                chunk_dict[chunk_num] = {}
            chunk_dict[chunk_num][id_str] = data
        
        total_saved = 0
        for chunk_num, chunk_data in chunk_dict.items():
            # 保证键排序
            sorted_chunk = {k: chunk_data[k] for k in sorted(chunk_data.keys(), key=int)}
            filename = os.path.join(self.script_path, f"scriptData{chunk_num}.txt")
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(sorted_chunk, f, ensure_ascii=False, indent=2)
                total_saved += len(sorted_chunk)
            except Exception as e:
                self.log(f"保存 {filename} 失败: {e}", "error")
                return False
        self.log(f"已保存 {total_saved} 条对话到 {len(chunk_dict)} 个块文件")
        return True
        
    def backup_script(self):
        if not self.script_path:
            self.log("请先加载脚本", "warning")
            return
        backup_dir = self.script_path + f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copytree(self.script_path, backup_dir)
            self.log(f"备份成功: {backup_dir}")
        except Exception as e:
            self.log(f"备份失败: {e}", "error")
            
    def reload_script(self):
        self.load_all_scripts()
        self.log("脚本重新加载完成")
        
    # ---------- 移动与重排序逻辑 ----------
    def get_current_order_list(self):
        """返回当前 full_data 中按 ID 数字排序的 (old_id, data) 列表"""
        items = []
        for id_str, data in self.full_data.items():
            try:
                items.append((int(id_str), data))
            except:
                continue
        items.sort(key=lambda x: x[0])
        return items
    
    def rebuild_with_new_ids(self, ordered_items):
        """
        根据 ordered_items 列表（每个元素为 (old_id, data)）重新分配连续 ID，
        并更新所有对话中的选项跳转ID (c1t, c2t, c3t, c4t)。
        返回新的 full_data 字典。
        """
        # 建立 old_id -> new_id 映射
        id_map = {}
        new_data = {}
        for new_id, (old_id, data) in enumerate(ordered_items, start=1):
            id_map[old_id] = new_id
            # 浅拷贝数据，待会再修改引用
            new_data[str(new_id)] = data.copy()
        
        # 更新所有对话中的跳转字段
        for new_id_str, data in new_data.items():
            # 更新 c1t, c2t, c3t, c4t
            for field in ['c1t', 'c2t', 'c3t', 'c4t']:
                if field in data:
                    old_target = data[field]
                    if isinstance(old_target, int) and old_target in id_map:
                        data[field] = id_map[old_target]
                    elif isinstance(old_target, str) and old_target.isdigit():
                        old_int = int(old_target)
                        if old_int in id_map:
                            data[field] = id_map[old_int]
                    # 其他情况保留原值（可能为空或无效）
        return new_data, id_map
    
    def move_and_renumber(self):
        if not self.full_data:
            self.log("没有加载脚本，无法操作", "error")
            return
        
        try:
            start = int(self.start_id.get().strip())
            end = int(self.end_id.get().strip())
            target = int(self.target_id.get().strip())
        except ValueError:
            self.log("请正确填写起始ID、结束ID和目标ID（数字）", "error")
            return
        
        if start > end:
            self.log("起始ID不能大于结束ID", "error")
            return
        
        # 获取当前顺序列表
        order = self.get_current_order_list()
        all_ids = [item[0] for item in order]
        
        if start not in all_ids or end not in all_ids:
            self.log("起始ID或结束ID在当前脚本中不存在", "error")
            return
        if target not in all_ids:
            self.log("目标ID在当前脚本中不存在", "error")
            return
        
        # 找到索引范围
        idx_start = all_ids.index(start)
        idx_end = all_ids.index(end)
        if idx_start > idx_end:
            self.log("内部错误：起始索引大于结束索引", "error")
            return
        
        # 目标索引
        target_idx = all_ids.index(target)
        if self.insert_before.get():
            insert_pos = target_idx
        else:
            insert_pos = target_idx + 1
        
        # 检查目标是否在源区间内部（不允许）
        if insert_pos >= idx_start and insert_pos <= idx_end+1:
            self.log("目标位置位于要移动的区间内部，不允许操作", "error")
            return
        
        # 切出源区间
        source_slice = order[idx_start:idx_end+1]
        remaining = order[:idx_start] + order[idx_end+1:]
        
        # 插入到新位置
        new_order = remaining[:insert_pos] + source_slice + remaining[insert_pos:]
        
        # 重新编号并更新引用
        new_data, id_map = self.rebuild_with_new_ids(new_order)
        
        # 显示映射信息（仅前几个示例）
        self.full_data = new_data
        self.total_dialogues = len(self.full_data)
        self.info_label.config(text=f"对话总数: {self.total_dialogues}")
        
        self.log(f"移动完成: 共移动 {len(source_slice)} 条对话 (ID {start}~{end}) "
                 f"到目标ID {target} {'之前' if self.insert_before.get() else '之后'}")
        self.log(f"重新生成连续ID，共 {self.total_dialogues} 条，已更新选项跳转引用")
        self.status_label.config(text="更改已应用，请点击保存", foreground="#ffcc00")
        
    def renumber_only(self):
        """仅重排 ID，不改变顺序"""
        if not self.full_data:
            self.log("没有加载脚本", "error")
            return
        order = self.get_current_order_list()
        new_data, id_map = self.rebuild_with_new_ids(order)
        self.full_data = new_data
        self.total_dialogues = len(self.full_data)
        self.info_label.config(text=f"对话总数: {self.total_dialogues}")
        self.log(f"重新编号完成，共 {self.total_dialogues} 条对话，已更新选项跳转引用")
        self.status_label.config(text="更改已应用，请点击保存", foreground="#ffcc00")

if __name__ == "__main__":
    import re
    root = tk.Tk()
    app = ScriptMoverApp(root)
    root.mainloop()