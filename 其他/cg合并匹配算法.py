import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import glob
import threading
from queue import Queue
import re
import gc

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    import difflib

class SmartCGMigrator:
    def __init__(self, root):
        self.root = root
        self.root.title("智能CG迁移 - 旧版驱动匹配")
        self.root.geometry("900x800")
        
        self.old_file_path = ""
        self.new_dir_path = ""
        self.old_items = []
        self.new_items = []
        self.new_files = []
        self.output_split = {}
        self.is_processing = False
        self.cancel_flag = False
        self.queue = Queue()
        
        self.setup_ui()
        self.check_queue()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 旧版文件
        ttk.Label(main_frame, text="旧版JSON文件（含cg字段）", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0,5))
        frame1 = ttk.Frame(main_frame)
        frame1.grid(row=1, column=0, sticky=tk.W+tk.E, pady=2)
        self.old_path_var = tk.StringVar()
        ttk.Entry(frame1, textvariable=self.old_path_var, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(frame1, text="浏览", command=self.select_old_file).pack(side=tk.LEFT)
        
        # 新版文件夹
        ttk.Label(main_frame, text="新版文件夹（scriptData*.txt）", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=(10,5))
        frame2 = ttk.Frame(main_frame)
        frame2.grid(row=3, column=0, sticky=tk.W+tk.E, pady=2)
        self.new_dir_var = tk.StringVar()
        ttk.Entry(frame2, textvariable=self.new_dir_var, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(frame2, text="浏览", command=self.select_new_dir).pack(side=tk.LEFT)
        
        # 参数
        param_frame = ttk.LabelFrame(main_frame, text="匹配参数", padding="5")
        param_frame.grid(row=4, column=0, sticky=tk.W+tk.E, pady=10)
        
        # 相似度阈值
        ttk.Label(param_frame, text="相似度阈值:").grid(row=0, column=0, sticky=tk.W)
        self.threshold_var = tk.DoubleVar(value=0.75)
        scale = ttk.Scale(param_frame, from_=0.0, to=1.0, variable=self.threshold_var, orient=tk.HORIZONTAL, length=200)
        scale.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.thresh_label = ttk.Label(param_frame, text="0.75")
        self.thresh_label.grid(row=0, column=2, sticky=tk.W)
        scale.configure(command=lambda x: self.thresh_label.configure(text=f"{float(x):.2f}"))
        
        # 搜索范围
        ttk.Label(param_frame, text="向后搜索范围（行）:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.search_range_var = tk.IntVar(value=200)
        ttk.Spinbox(param_frame, from_=20, to=1000, textvariable=self.search_range_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # 偏移容忍
        ttk.Label(param_frame, text="偏移容忍（行）:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.offset_tolerance_var = tk.IntVar(value=50)
        ttk.Spinbox(param_frame, from_=10, to=200, textvariable=self.offset_tolerance_var, width=8).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(param_frame, text="匹配位置偏移超过此值则视为删除").grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=5)
        
        # 严格说话人
        self.strict_speaker_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(param_frame, text="严格匹配说话人", variable=self.strict_speaker_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 忽略空白
        self.normalize_text_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(param_frame, text="忽略空白差异", variable=self.normalize_text_var).grid(row=4, column=0, columnspan=2, sticky=tk.W)
        
        # 引擎
        engine_frame = ttk.Frame(param_frame)
        engine_frame.grid(row=5, column=0, columnspan=4, sticky=tk.W, pady=5)
        ttk.Label(engine_frame, text="相似度引擎:").pack(side=tk.LEFT)
        self.engine_var = tk.StringVar(value="rapidfuzz" if RAPIDFUZZ_AVAILABLE else "difflib")
        if RAPIDFUZZ_AVAILABLE:
            ttk.Radiobutton(engine_frame, text="rapidfuzz (快)", variable=self.engine_var, value="rapidfuzz").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(engine_frame, text="difflib (慢)", variable=self.engine_var, value="difflib").pack(side=tk.LEFT, padx=5)
        
        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="开始匹配", command=self.start_migration)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.cancel_btn = ttk.Button(btn_frame, text="取消", command=self.cancel_migration, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        self.save_btn = ttk.Button(btn_frame, text="保存结果", command=self.save_split_results, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=7, column=0, sticky=tk.W)
        
        # 统计
        self.stats_text = scrolledtext.ScrolledText(main_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        self.stats_text.grid(row=8, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(8, weight=1)
    
    def select_old_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON/TXT files", "*.json *.txt"), ("All files", "*.*")])
        if path:
            self.old_path_var.set(path)
            self.old_file_path = path
    
    def select_new_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.new_dir_var.set(path)
            self.new_dir_path = path
    
    def normalize_text(self, text):
        if not text:
            return ""
        # 去除所有空白字符（包括换行、空格、制表）
        return re.sub(r'\s+', '', text).strip()
    
    def similarity(self, text1, text2, engine):
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        if engine == "rapidfuzz" and RAPIDFUZZ_AVAILABLE:
            return fuzz.ratio(text1, text2) / 100.0
        else:
            return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def start_migration(self):
        if not self.old_file_path or not self.new_dir_path:
            messagebox.showwarning("警告", "请选择文件")
            return
        if self.is_processing:
            return
        
        # 加载旧版
        try:
            with open(self.old_file_path, 'r', encoding='utf-8') as f:
                old_dict = json.load(f)
            self.old_items = []
            for key in sorted(old_dict.keys(), key=lambda x: int(x)):
                val = old_dict[key]
                self.old_items.append({
                    "id": key,
                    "s": val.get("s", ""),
                    "t": val.get("t", ""),
                    "cg": val.get("cg", "")
                })
        except Exception as e:
            messagebox.showerror("错误", f"加载旧版失败: {e}")
            return
        
        # 加载新版分文件
        pattern = os.path.join(self.new_dir_path, "scriptData*.txt")
        file_list = glob.glob(pattern)
        if not file_list:
            messagebox.showerror("错误", "未找到 scriptData*.txt 文件")
            return
        self.new_files = sorted(file_list)
        new_dict = {}
        for fpath in self.new_files:
            with open(fpath, 'r', encoding='utf-8') as f:
                new_dict.update(json.load(f))
        self.new_items = []
        for key in sorted(new_dict.keys(), key=lambda x: int(x)):
            val = new_dict[key]
            self.new_items.append({
                "id": key,
                "s": val.get("s", ""),
                "t": val.get("t", ""),
                "original_val": val
            })
        
        self.is_processing = True
        self.cancel_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set(f"旧版 {len(self.old_items)} 条，新版 {len(self.new_items)} 条")
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, f"旧版条目: {len(self.old_items)}\n新版条目: {len(self.new_items)}\n")
        self.stats_text.insert(tk.END, f"阈值: {self.threshold_var.get()}\n搜索范围: {self.search_range_var.get()}\n偏移容忍: {self.offset_tolerance_var.get()}\n")
        self.stats_text.insert(tk.END, f"严格说话人: {self.strict_speaker_var.get()}\n忽略空白: {self.normalize_text_var.get()}\n")
        self.stats_text.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.migrate_worker)
        thread.daemon = True
        thread.start()
    
    def cancel_migration(self):
        if self.is_processing:
            self.cancel_flag = True
            self.status_var.set("取消中...")
    
    def migrate_worker(self):
        """旧版驱动匹配：以旧版为基准，在新版中搜索最佳匹配"""
        try:
            threshold = self.threshold_var.get()
            search_range = self.search_range_var.get()
            offset_tol = self.offset_tolerance_var.get()
            strict_speaker = self.strict_speaker_var.get()
            normalize = self.normalize_text_var.get()
            engine = self.engine_var.get()
            
            old_len = len(self.old_items)
            new_len = len(self.new_items)
            
            # 预处理旧版文本和说话人
            old_texts = []
            old_speakers = []
            old_cgs = []
            for item in self.old_items:
                text = item["t"]
                if normalize:
                    text = self.normalize_text(text)
                old_texts.append(text)
                old_speakers.append(item["s"])
                old_cgs.append(item["cg"])
            
            # 预处理新版文本和说话人（为了加速，提前计算好）
            new_texts = []
            new_speakers = []
            for item in self.new_items:
                text = item["t"]
                if normalize:
                    text = self.normalize_text(text)
                new_texts.append(text)
                new_speakers.append(item["s"])
            
            # 匹配结果字典
            result = {}
            
            # 指针
            old_idx = 0
            new_idx = 0
            matched = 0
            inserted = 0
            deleted = 0
            low_conf = 0
            
            # 主循环：遍历旧版每一行
            while old_idx < old_len and new_idx < new_len:
                if self.cancel_flag:
                    return
                
                old_text = old_texts[old_idx]
                old_speaker = old_speakers[old_idx]
                old_cg = old_cgs[old_idx]
                
                # 在新版中从 new_idx 开始向后搜索 search_range 行
                end = min(new_len, new_idx + search_range)
                best_idx = -1
                best_score = 0.0
                for i in range(new_idx, end):
                    if strict_speaker and old_speaker and new_speakers[i]:
                        if old_speaker != new_speakers[i]:
                            continue
                    score = self.similarity(old_text, new_texts[i], engine)
                    if score > best_score:
                        best_score = score
                        best_idx = i
                        if score >= 0.99:  # 完全匹配时提前退出
                            break
                
                if best_idx != -1 and best_score >= threshold:
                    offset = best_idx - new_idx
                    if offset <= offset_tol:
                        # 正常匹配：将 best_idx 之前未匹配的新版行标记为插入
                        for k in range(new_idx, best_idx):
                            ins_item = self.new_items[k]
                            ins_val = ins_item["original_val"].copy()
                            if "cg" in ins_val:
                                del ins_val["cg"]
                            result[ins_item["id"]] = ins_val
                            inserted += 1
                        # 匹配行：迁移 cg
                        matched_item = self.new_items[best_idx]
                        matched_val = matched_item["original_val"].copy()
                        matched_val["cg"] = old_cg
                        result[matched_item["id"]] = matched_val
                        matched += 1
                        if best_score < 0.8:
                            low_conf += 1
                        # 移动指针
                        old_idx += 1
                        new_idx = best_idx + 1
                    else:
                        # 偏移过大：视为旧版删除（该行在新版中位置太远，不匹配）
                        deleted += 1
                        old_idx += 1
                else:
                    # 未找到匹配：旧版删除
                    deleted += 1
                    old_idx += 1
                
                # 进度更新（按旧版进度）
                if old_idx % 500 == 0:
                    progress = (old_idx / old_len) * 100
                    self.queue.put(("progress", progress))
                    self.queue.put(("status", f"处理中: 旧版 {old_idx}/{old_len} | 匹配={matched} 插入={inserted} 删除={deleted}"))
            
            # 循环结束：处理剩余的新版行（全部为插入）
            while new_idx < new_len:
                ins_item = self.new_items[new_idx]
                ins_val = ins_item["original_val"].copy()
                if "cg" in ins_val:
                    del ins_val["cg"]
                result[ins_item["id"]] = ins_val
                new_idx += 1
                inserted += 1
            
            # 注意：剩余旧版行已经在上面的循环中通过 deleted 计数了，无需额外处理
            
            self.queue.put(("progress", 100))
            self.queue.put(("status", f"完成！匹配={matched}, 插入={inserted}, 删除={deleted}, 低置信={low_conf}"))
            stats_msg = f"\n统计:\n成功匹配: {matched}\n新版插入行: {inserted}\n旧版删除行: {deleted}\n低置信度匹配(<0.8): {low_conf}\n"
            self.queue.put(("stats", stats_msg))
            
            self.output_data = result
            self.split_results()
            self.queue.put(("done", None))
            
        except Exception as e:
            self.queue.put(("error", str(e)))
    
    def split_results(self):
        if not hasattr(self, 'output_data') or not self.output_data:
            return
        self.output_split = {}
        for fpath in self.new_files:
            with open(fpath, 'r', encoding='utf-8') as f:
                original = json.load(f)
            new_chunk = {}
            for key, val in original.items():
                if key in self.output_data:
                    new_chunk[key] = self.output_data[key]
                else:
                    new_chunk[key] = val
            self.output_split[fpath] = new_chunk
    
    def save_split_results(self):
        if not hasattr(self, 'output_split') or not self.output_split:
            messagebox.showwarning("警告", "没有结果可保存")
            return
        save_dir = filedialog.askdirectory(title="选择保存目录")
        if not save_dir:
            return
        try:
            for fpath, chunk in self.output_split.items():
                base = os.path.basename(fpath)
                out_path = os.path.join(save_dir, base)
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"已保存 {len(self.output_split)} 个文件到 {save_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def check_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == "progress":
                    self.progress_var.set(msg[1])
                elif msg[0] == "status":
                    self.status_var.set(msg[1])
                elif msg[0] == "stats":
                    self.stats_text.config(state=tk.NORMAL)
                    self.stats_text.insert(tk.END, msg[1])
                    self.stats_text.see(tk.END)
                    self.stats_text.config(state=tk.DISABLED)
                elif msg[0] == "done":
                    self.is_processing = False
                    self.start_btn.config(state=tk.NORMAL)
                    self.cancel_btn.config(state=tk.DISABLED)
                    self.save_btn.config(state=tk.NORMAL)
                elif msg[0] == "error":
                    self.is_processing = False
                    self.start_btn.config(state=tk.NORMAL)
                    self.cancel_btn.config(state=tk.DISABLED)
                    self.save_btn.config(state=tk.DISABLED)
                    messagebox.showerror("错误", msg[1])
        except:
            pass
        self.root.after(100, self.check_queue)

def main():
    root = tk.Tk()
    app = SmartCGMigrator(root)
    root.mainloop()

if __name__ == "__main__":
    main()