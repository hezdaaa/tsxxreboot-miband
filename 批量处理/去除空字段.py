import os
import json
import re
import sys
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import time
import threading
import queue

class RemoveEmptyFieldsTool:
    def __init__(self, root):
        self.root = root
        self.root.title("一键去除空字段工具")
        self.root.geometry("850x750")
        self.root.configure(bg='#1e1e1e')
        
        self.setup_dark_theme()
        
        # 数据
        self.script_path = ""
        self.chunk_cache = {}      # chunk_num -> data dict
        self.id_to_chunk = {}      # dialog_id -> chunk_num
        self.chunk_files = []      # 文件名列表
        
        # 选项
        self.remove_empty_entries_var = tk.BooleanVar(value=False)
        
        # 线程控制
        self.worker_thread = None
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        
        self.create_widgets()
        self.process_log_queue()
    
    def setup_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#1e1e1e', foreground='#d4d4d4',
                       fieldbackground='#252526', insertcolor='#d4d4d4',
                       selectbackground='#264f78', selectforeground='#d4d4d4',
                       troughcolor='#3c3c3c')
        style.configure('TButton', background='#333333', foreground='#d4d4d4', borderwidth=1)
        style.map('TButton', background=[('active', '#555555'), ('pressed', '#444444')])
        style.configure('TLabel', background='#1e1e1e', foreground='#d4d4d4')
        style.configure('TLabelframe', background='#1e1e1e', foreground='#d4d4d4',
                       bordercolor='#555555')
        style.configure('TLabelframe.Label', background='#1e1e1e', foreground='#569cd6')
        style.configure('TEntry', fieldbackground='#252526', foreground='#d4d4d4',
                       insertcolor='#d4d4d4', bordercolor='#555555')
        style.configure('TCheckbutton', background='#1e1e1e', foreground='#d4d4d4')
    
    def create_widgets(self):
        # 控制面板
        control_frame = ttk.LabelFrame(self.root, text="项目设置", padding="10")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        path_frame = ttk.Frame(control_frame)
        path_frame.pack(fill="x", pady=(0,5))
        ttk.Label(path_frame, text="脚本文件夹:").pack(side="left", padx=5)
        self.path_label = ttk.Label(path_frame, text="未选择", foreground="#569cd6")
        self.path_label.pack(side="left", padx=5)
        ttk.Button(path_frame, text="选择脚本文件夹", command=self.select_script_folder).pack(side="left", padx=5)
        
        # 选项设置
        option_frame = ttk.LabelFrame(self.root, text="处理选项", padding="10")
        option_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Checkbutton(option_frame, text="删除整个空对话（若所有字段均为空）",
                        variable=self.remove_empty_entries_var).pack(anchor="w", padx=5, pady=2)
        ttk.Label(option_frame, text="说明：去除所有值为空字符串、null、空列表、空字典的字段。",
                  foreground="#858585").pack(anchor="w", padx=5)
        
        # 操作按钮
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=5)
        self.preview_btn = ttk.Button(action_frame, text="预览修改", command=self.start_preview, width=12)
        self.preview_btn.pack(side="left", padx=5)
        self.execute_btn = ttk.Button(action_frame, text="执行修改", command=self.start_execute, width=12)
        self.execute_btn.pack(side="left", padx=5)
        ttk.Button(action_frame, text="清除缓存", command=self.clear_cache, width=10).pack(side="left", padx=5)
        
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(action_frame, variable=self.progress_var,
                                            maximum=100, length=200, mode='determinate')
        self.progress_bar.pack(side="right", padx=10)
        
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding="10")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, font=("Consolas", 9), height=12,
            bg='#252526', fg='#d4d4d4', insertbackground='#d4d4d4',
            selectbackground='#264f78', relief='flat'
        )
        self.log_text.pack(fill="both", expand=True)
    
    def queue_log(self, msg):
        self.log_queue.put(msg)
    
    def queue_progress(self, value):
        self.progress_queue.put(value)
    
    def process_log_queue(self):
        try:
            logs = []
            while True:
                try:
                    logs.append(self.log_queue.get_nowait())
                except queue.Empty:
                    break
            if logs:
                for msg in logs:
                    timestamp = time.strftime("%H:%M:%S")
                    self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
                self.log_text.see(tk.END)
            try:
                prog = self.progress_queue.get_nowait()
                self.progress_var.set(prog)
            except queue.Empty:
                pass
        finally:
            self.root.after(100, self.process_log_queue)
    
    def select_script_folder(self):
        folder = filedialog.askdirectory(title="选择脚本文件夹（包含scriptDataX.txt）")
        if not folder:
            return
        self.script_path = folder
        self.path_label.config(text=f"脚本: {os.path.basename(folder)}")
        self.start_load_scripts()
    
    def start_load_scripts(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.queue_log("已有任务运行中，请稍后")
            return
        self.worker_thread = threading.Thread(target=self.load_all_scripts, daemon=True)
        self.worker_thread.start()
    
    def load_all_scripts(self):
        self.queue_log("开始加载脚本...")
        if not self.script_path or not os.path.exists(self.script_path):
            self.queue_log("错误: 脚本文件夹不存在")
            return
        
        chunk_cache = {}
        id_to_chunk = {}
        chunk_files = []
        
        try:
            files = [f for f in os.listdir(self.script_path)
                    if f.lower().startswith("scriptdata") and f.lower().endswith(".txt")]
            def extract_number(filename):
                m = re.search(r'(\d+)', filename)
                return int(m.group(1)) if m else 0
            files.sort(key=extract_number)
            chunk_files = files
            
            total = 0
            for i, filename in enumerate(files):
                file_path = os.path.join(self.script_path, filename)
                chunk_num = extract_number(filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        chunk_cache[chunk_num] = data
                        for id_str in data:
                            did = int(id_str)
                            id_to_chunk[did] = chunk_num
                        total += len(data)
                except Exception as e:
                    self.queue_log(f"警告: 加载{filename}失败: {e}")
                    chunk_cache[chunk_num] = {}
                prog = (i+1)*100//len(files)
                self.queue_progress(prog)
            
            self.chunk_cache = chunk_cache
            self.id_to_chunk = id_to_chunk
            self.chunk_files = chunk_files
            self.queue_log(f"加载完成: {len(chunk_cache)}个块, {total}条对话, 索引{len(id_to_chunk)}个ID")
            self.queue_progress(0)
        except Exception as e:
            self.queue_log(f"加载失败: {e}")
    
    # ---------- 核心函数：递归去除空字段 ----------
    @staticmethod
    def remove_empty_fields(obj, remove_empty_entries=False):
        """
        递归删除字典中值为空（None, "", [], {}）的键。
        如果 remove_empty_entries 为 True 且字典变空，则返回 None 表示删除整个条目。
        对于列表，递归处理每个元素并过滤掉 None 和空字典/空列表（可选）。
        
        返回处理后的对象（原地修改但返回新对象以避免副作用）。
        """
        if isinstance(obj, dict):
            # 复制一份，避免迭代中修改原字典
            new_dict = {}
            for k, v in obj.items():
                processed_v = RemoveEmptyFieldsTool.remove_empty_fields(v, remove_empty_entries)
                # 跳过值为空的字段（None、空字符串、空列表、空字典）
                if processed_v is None:
                    continue
                if processed_v == "":
                    continue
                if isinstance(processed_v, list) and len(processed_v) == 0:
                    continue
                if isinstance(processed_v, dict) and len(processed_v) == 0:
                    continue
                new_dict[k] = processed_v
            # 如果删除所有字段后字典为空且要求删除空条目，返回 None
            if remove_empty_entries and len(new_dict) == 0:
                return None
            return new_dict
        
        elif isinstance(obj, list):
            new_list = []
            for item in obj:
                processed_item = RemoveEmptyFieldsTool.remove_empty_fields(item, remove_empty_entries)
                if processed_item is None:
                    continue
                if processed_item == "":
                    continue
                if isinstance(processed_item, list) and len(processed_item) == 0:
                    continue
                if isinstance(processed_item, dict) and len(processed_item) == 0:
                    continue
                new_list.append(processed_item)
            return new_list
        
        else:
            # 基本类型：字符串、数字、布尔等，直接返回
            return obj
    # ------------------------------------------------
    
    def start_preview(self):
        if not self.id_to_chunk:
            self.queue_log("请先加载脚本数据")
            return
        if self.worker_thread and self.worker_thread.is_alive():
            self.queue_log("已有任务运行中")
            return
        self.worker_thread = threading.Thread(target=self.preview_changes, daemon=True)
        self.worker_thread.start()
    
    def preview_changes(self):
        self.queue_log("正在分析需要删除的空字段...")
        remove_empty_entries = self.remove_empty_entries_var.get()
        affected_info = []  # (chunk_num, dialog_id, removed_fields)
        
        for did, chunk_num in self.id_to_chunk.items():
            original_dialog = self.chunk_cache[chunk_num].get(str(did), {})
            if not original_dialog:
                continue
            # 应用删除逻辑
            processed = self.remove_empty_fields(original_dialog, remove_empty_entries)
            # 找出被删除的字段（仅第一层，深层删除也可通过递归对比）
            removed = []
            if isinstance(processed, dict):
                original_keys = set(original_dialog.keys())
                new_keys = set(processed.keys())
                removed_keys = original_keys - new_keys
                if removed_keys:
                    removed = list(removed_keys)
            # 如果整个对话被删除
            if processed is None or (isinstance(processed, dict) and len(processed) == 0):
                affected_info.append((chunk_num, did, ["[整个对话将被删除]"]))
            elif removed:
                affected_info.append((chunk_num, did, removed))
        
        self.root.after(0, lambda: self.show_preview_window(affected_info, remove_empty_entries))
    
    def show_preview_window(self, affected_info, remove_empty_entries):
        preview_win = tk.Toplevel(self.root)
        preview_win.title("修改预览 - 待删除的空字段")
        preview_win.geometry("800x600")
        preview_win.configure(bg='#1e1e1e')
        text_widget = scrolledtext.ScrolledText(preview_win, font=("Consolas", 10),
                                                bg='#252526', fg='#d4d4d4')
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget.insert(tk.END, f"===== 删除空字段设置: 删除整个空对话 = {remove_empty_entries} =====\n\n")
        text_widget.insert(tk.END, f"共 {len(affected_info)} 条对话将发生修改\n\n")
        for chunk_num, did, removed in affected_info[:200]:
            text_widget.insert(tk.END, f"块 {chunk_num} | ID {did}:\n")
            text_widget.insert(tk.END, f"  删除字段: {', '.join(removed)}\n\n")
        if len(affected_info) > 200:
            text_widget.insert(tk.END, f"... 还有 {len(affected_info)-200} 条未显示\n")
        ttk.Button(preview_win, text="关闭", command=preview_win.destroy).pack(pady=10)
    
    def start_execute(self):
        if not self.id_to_chunk:
            self.queue_log("请先加载脚本数据")
            return
        if self.worker_thread and self.worker_thread.is_alive():
            self.queue_log("已有任务运行中")
            return
        if not messagebox.askyesno("确认", "此操作将永久删除空字段，是否继续？\n建议先预览。"):
            return
        if messagebox.askyesno("备份", "是否在修改前备份所有文件？"):
            self.backup_files()
        self.worker_thread = threading.Thread(target=self.do_execute, daemon=True)
        self.worker_thread.start()
    
    def do_execute(self):
        self.queue_log("开始处理：删除空字段...")
        remove_empty_entries = self.remove_empty_entries_var.get()
        
        affected_chunks = set()
        modified_count = 0
        deleted_entries_count = 0
        
        for did, chunk_num in self.id_to_chunk.items():
            key = str(did)
            original = self.chunk_cache[chunk_num].get(key, {})
            if not original:
                continue
            processed = self.remove_empty_fields(original, remove_empty_entries)
            # 比较是否变化
            if processed is None:
                # 整个对话被删除
                del self.chunk_cache[chunk_num][key]
                deleted_entries_count += 1
                modified_count += 1
                affected_chunks.add(chunk_num)
            elif processed != original:
                self.chunk_cache[chunk_num][key] = processed
                modified_count += 1
                affected_chunks.add(chunk_num)
        
        self.queue_log(f"分析完成，共修改 {modified_count} 条对话（其中删除整个对话 {deleted_entries_count} 条），影响 {len(affected_chunks)} 个块")
        
        if modified_count == 0:
            self.queue_log("没有需要修改的内容")
            return
        
        self.queue_log("开始保存文件...")
        saved = 0
        total = len(affected_chunks)
        for i, chunk_num in enumerate(sorted(affected_chunks)):
            chunk_data = self.chunk_cache[chunk_num]
            chunk_file = os.path.join(self.script_path, f"scriptData{chunk_num}.txt")
            try:
                # 按ID数字排序保存
                sorted_data = {k: chunk_data[k] for k in sorted(chunk_data.keys(), key=lambda x: int(x))}
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    json.dump(sorted_data, f, ensure_ascii=False, indent=2)
                saved += 1
            except Exception as e:
                self.queue_log(f"保存块 {chunk_num} 失败: {e}")
            prog = (i+1)*100//total if total else 0
            self.queue_progress(prog)
        
        self.queue_log(f"操作完成！修改 {modified_count} 条对话，保存 {saved}/{len(affected_chunks)} 个文件")
        self.queue_progress(0)
        self.root.after(0, lambda: messagebox.showinfo("完成", f"处理完成！\n修改对话: {modified_count} 条\n删除整个对话: {deleted_entries_count} 条\n保存文件: {saved} 个"))
    
    def backup_files(self):
        if not self.script_path or not self.chunk_files:
            return
        backup_folder = os.path.join(self.script_path, "backup_" + time.strftime("%Y%m%d_%H%M%S"))
        try:
            os.makedirs(backup_folder)
            for filename in self.chunk_files:
                src = os.path.join(self.script_path, filename)
                dst = os.path.join(backup_folder, filename)
                with open(src, 'rb') as fs, open(dst, 'wb') as fd:
                    fd.write(fs.read())
            self.queue_log(f"备份完成: {backup_folder} ({len(self.chunk_files)} 个文件)")
        except Exception as e:
            self.queue_log(f"备份失败: {e}")
            if not messagebox.askyesno("继续", "备份失败，是否继续？"):
                return False
        return True
    
    def clear_cache(self):
        self.chunk_cache.clear()
        self.id_to_chunk.clear()
        self.queue_log("缓存已清除")

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    root = tk.Tk()
    app = RemoveEmptyFieldsTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()