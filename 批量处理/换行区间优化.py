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
import unicodedata

class KeepNewlineInRanges:
    def __init__(self, root):
        self.root = root
        self.root.title("换行符区间保留工具")
        self.root.geometry("850x750")
        self.root.configure(bg='#1e1e1e')
        
        self.setup_dark_theme()
        
        # 数据
        self.script_path = ""
        self.chunk_cache = {}
        self.id_to_chunk = {}
        self.chunk_files = []
        
        # 区间设置（全角宽度区间，左闭右开）
        self.ranges = [(10, 15), (25, 30), (40, 45)]
        
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
        
        # 区间设置
        range_frame = ttk.LabelFrame(self.root, text="换行符保留区间（全角宽度，左闭右开）", padding="10")
        range_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(range_frame, text="区间格式: 起始-结束，多个区间用英文逗号分隔，例如 10-15,25-30,40-45").pack(anchor="w", padx=5)
        self.range_entry = ttk.Entry(range_frame, width=60)
        self.range_entry.insert(0, "10-15,25-30,40-45")
        self.range_entry.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(range_frame, text="说明: 半角字符宽0.5，全角字符宽1。换行符本身不占宽度，仅当累计宽度落在区间内时才保留换行符。",
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
    
    # ---------- 核心函数：保留特定全角宽度区间内的换行符 ----------
    @staticmethod
    def keep_newlines_in_ranges(text, ranges):
        """
        保留原始文本中落在指定全角宽度区间内的换行符，删除其他换行符。
        宽度计算：半角字符宽0.5，全角字符宽1。
        内部使用整数放大2倍：半角宽=1，全角宽=2。
        
        参数:
            text: 原始字符串（可能包含 \\n）
            ranges: 列表，每个元素为 (start, end) 全角宽度闭开区间，例如 [(10,15), (25,30)]
        
        返回:
            处理后的字符串
        """
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 将全角宽度区间转换为内部整数宽度区间（放大2倍）
        int_ranges = [(start*2, end*2) for start, end in ranges]
        # 构建快速判断集合：哪些内部宽度值需要保留换行符
        keep_positions = set()
        for start, end in int_ranges:
            for pos in range(start, end):
                keep_positions.add(pos)
        
        result_chars = []
        width = 0  # 内部整数宽度（半角=1，全角=2）
        
        for ch in text:
            if ch == '\n':
                if width in keep_positions:
                    result_chars.append('\n')
                # 否则丢弃
            else:
                result_chars.append(ch)
                # 累加宽度
                # 使用 unicodedata 判断全角/宽字符
                if unicodedata.east_asian_width(ch) in ('F', 'W', 'A'):
                    width += 2
                else:
                    width += 1
        return ''.join(result_chars)
    # ------------------------------------------------
    
    def parse_ranges_from_entry(self):
        """从输入框解析区间，返回列表 [(start,end), ...] 全角宽度"""
        entry_text = self.range_entry.get().strip()
        ranges = []
        for part in entry_text.split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                try:
                    s, e = part.split('-')
                    start = int(s.strip())
                    end = int(e.strip())
                    if start >= end:
                        self.queue_log(f"区间 {start}-{end} 无效（起始不小于结束），已忽略")
                        continue
                    ranges.append((start, end))
                except ValueError:
                    self.queue_log(f"无法解析区间: {part}，已忽略")
            else:
                self.queue_log(f"区间格式错误（缺少横线）: {part}，已忽略")
        if not ranges:
            # 使用默认
            self.queue_log("未解析到有效区间，使用默认: 10-15,25-30,40-45")
            return [(10,15), (25,30), (40,45)]
        return ranges
    
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
        self.queue_log("正在分析需要修改的对话...")
        ranges = self.parse_ranges_from_entry()
        affected = []
        for did, chunk_num in self.id_to_chunk.items():
            data = self.chunk_cache[chunk_num].get(str(did), {})
            text = data.get('t', '')
            new_text = self.keep_newlines_in_ranges(text, ranges)
            if new_text != text:
                # 只记录前50字符用于预览
                affected.append((did, text[:50].replace('\n', '↵'), new_text[:50].replace('\n', '↵')))
        self.root.after(0, lambda: self.show_preview_window(affected, ranges))
    
    def show_preview_window(self, affected, ranges):
        preview_win = tk.Toplevel(self.root)
        preview_win.title("修改预览")
        preview_win.geometry("700x600")
        preview_win.configure(bg='#1e1e1e')
        text_widget = scrolledtext.ScrolledText(preview_win, font=("Consolas", 10),
                                                bg='#252526', fg='#d4d4d4')
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        
        range_str = ", ".join([f"{s}-{e}" for s,e in ranges])
        text_widget.insert(tk.END, f"===== 保留换行符区间（全角宽度）: {range_str} =====\n\n")
        text_widget.insert(tk.END, f"共找到 {len(affected)} 条对话将会修改\n\n")
        for did, old, new in affected[:100]:
            text_widget.insert(tk.END, f"ID {did}:\n  原: {old}...\n  新: {new}...\n\n")
        if len(affected) > 100:
            text_widget.insert(tk.END, f"... 还有 {len(affected)-100} 条未显示\n")
        ttk.Button(preview_win, text="关闭", command=preview_win.destroy).pack(pady=10)
    
    def start_execute(self):
        if not self.id_to_chunk:
            self.queue_log("请先加载脚本数据")
            return
        if self.worker_thread and self.worker_thread.is_alive():
            self.queue_log("已有任务运行中")
            return
        if not messagebox.askyesno("确认", "此操作将删除不在指定区间内的换行符，是否继续？\n建议先预览。"):
            return
        if messagebox.askyesno("备份", "是否在修改前备份所有文件？"):
            self.backup_files()
        self.worker_thread = threading.Thread(target=self.do_execute, daemon=True)
        self.worker_thread.start()
    
    def do_execute(self):
        self.queue_log("开始处理：保留区间内换行符，删除其他...")
        ranges = self.parse_ranges_from_entry()
        
        affected_chunks = set()
        modified_count = 0
        for did, chunk_num in self.id_to_chunk.items():
            key = str(did)
            data = self.chunk_cache[chunk_num].get(key, {})
            if 't' in data:
                text = data['t']
                new_text = self.keep_newlines_in_ranges(text, ranges)
                if new_text != text:
                    data['t'] = new_text
                    modified_count += 1
                    affected_chunks.add(chunk_num)
        
        self.queue_log(f"分析完成，共修改 {modified_count} 条对话，影响 {len(affected_chunks)} 个块")
        
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
                sorted_data = {k: chunk_data[k] for k in sorted(chunk_data.keys(), key=lambda x: int(x))}
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    json.dump(sorted_data, f, ensure_ascii=False, indent=2)
                saved += 1
            except Exception as e:
                self.queue_log(f"保存块 {chunk_num} 失败: {e}")
            prog = (i+1)*100//total
            self.queue_progress(prog)
        
        self.queue_log(f"操作完成！修改 {modified_count} 条对话，保存 {saved}/{total} 个文件")
        self.queue_progress(0)
        self.root.after(0, lambda: messagebox.showinfo("完成", f"处理完成！\n修改对话: {modified_count} 条\n保存文件: {saved} 个"))
    
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
    app = KeepNewlineInRanges(root)
    root.mainloop()

if __name__ == "__main__":
    main()