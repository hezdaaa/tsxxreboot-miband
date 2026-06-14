import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import re
import json
import os
import threading
from queue import Queue
import gc

class GalgameScriptConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Galgame剧本格式转换器 - 多语言适配版")
        self.root.geometry("1000x750")
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text = tk.StringVar(value="就绪")
        self.is_processing = False
        self.cancel_processing = False
        self.queue = Queue()
        
        self.setup_ui()
        self.check_queue()
    
    # ---------- UI 界面 ----------
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(control_frame, text="ID起始（固定1）:").grid(row=0, column=0, sticky=tk.W, padx=(0,5))
        self.id_start_var = tk.StringVar(value="1")
        ttk.Entry(control_frame, textvariable=self.id_start_var, width=10, state="readonly").grid(row=0, column=1, sticky=tk.W, padx=(0,10))
        
        ttk.Button(control_frame, text="转换", command=self.start_conversion).grid(row=0, column=2, padx=5)
        self.cancel_button = ttk.Button(control_frame, text="取消", command=self.cancel_processing_func, state=tk.DISABLED)
        self.cancel_button.grid(row=0, column=3, padx=5)
        ttk.Button(control_frame, text="导入JSON文件", command=self.import_json_files).grid(row=0, column=4, padx=5)
        ttk.Button(control_frame, text="导出TXT", command=self.export_txt).grid(row=0, column=5, padx=5)
        ttk.Button(control_frame, text="清除", command=self.clear_all).grid(row=0, column=6, padx=5)
        ttk.Button(control_frame, text="加载示例", command=self.load_example).grid(row=0, column=7, padx=5)
        
        self.file_info_var = tk.StringVar(value="未选择文件")
        ttk.Label(control_frame, textvariable=self.file_info_var, foreground="blue").grid(row=0, column=8, padx=20)
        
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0,10))
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_text)
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5,0))
        
        ttk.Label(main_frame, text="原始剧本格式:").grid(row=2, column=0, sticky=tk.W, pady=(0,5))
        ttk.Label(main_frame, text="转换后格式 (JSON):").grid(row=2, column=1, sticky=tk.W, pady=(0,5))
        
        self.input_text = scrolledtext.ScrolledText(main_frame, height=25, width=50, wrap=tk.WORD)
        self.input_text.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0,10))
        self.output_text = scrolledtext.ScrolledText(main_frame, height=25, width=50, wrap=tk.WORD)
        self.output_text.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10,0))
        
        self.imported_files = []
        self._bind_mouse_wheel()
    
    def _bind_mouse_wheel(self):
        def on_wheel(event, widget):
            widget.yview_scroll(int(-1*(event.delta/120)), "units")
        self.input_text.bind("<MouseWheel>", lambda e: on_wheel(e, self.input_text))
        self.output_text.bind("<MouseWheel>", lambda e: on_wheel(e, self.output_text))
        # Linux 滚轮支持
        self.input_text.bind("<Button-4>", lambda e: self.input_text.yview_scroll(-1, "units"))
        self.input_text.bind("<Button-5>", lambda e: self.input_text.yview_scroll(1, "units"))
        self.output_text.bind("<Button-4>", lambda e: self.output_text.yview_scroll(-1, "units"))
        self.output_text.bind("<Button-5>", lambda e: self.output_text.yview_scroll(1, "units"))
    
    def check_queue(self):
        try:
            while not self.queue.empty():
                msg_type, data = self.queue.get_nowait()
                if msg_type == "progress_update":
                    self.progress_var.set(data["progress"]); self.progress_text.set(data["message"])
                elif msg_type == "status_update":
                    self.status_var.set(data)
                elif msg_type == "file_info":
                    self.file_info_var.set(data)
                elif msg_type == "output_text":
                    self.output_text.delete("1.0", tk.END); self.output_text.insert("1.0", data)
                elif msg_type == "input_text":
                    self.input_text.delete("1.0", tk.END); self.input_text.insert("1.0", data)
                elif msg_type == "processing_done":
                    self.is_processing = False; self.cancel_processing = False
                    self.cancel_button.config(state=tk.DISABLED); self.progress_text.set("完成")
                elif msg_type == "processing_error":
                    self.is_processing = False; self.cancel_processing = False
                    self.cancel_button.config(state=tk.DISABLED); self.progress_text.set("出错")
                    messagebox.showerror("错误", data)
        except Exception as e:
            print(f"队列错误: {e}")
        self.root.after(100, self.check_queue)
    
    def start_conversion(self):
        if self.is_processing: return
        self.is_processing = True
        self.cancel_processing = False
        self.cancel_button.config(state=tk.NORMAL)
        threading.Thread(target=self.convert_script_thread, daemon=True).start()
    
    def cancel_processing_func(self):
        self.cancel_processing = True
        self.status_var.set("正在取消...")
    
    def import_json_files(self):
        if self.is_processing: messagebox.showwarning("警告", "正在处理中"); return
        files = filedialog.askopenfilenames(title="选择JSON文件", filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not files: return
        self.is_processing = True; self.cancel_processing = False
        self.cancel_button.config(state=tk.NORMAL)
        threading.Thread(target=self._process_files_import, args=(files,), daemon=True).start()
    
    def _process_files_import(self, files):
        try:
            self.queue.put(("status_update", f"导入 {len(files)} 个文件..."))
            self.imported_files = list(files)
            all_content = ""
            for fp in files:
                if self.cancel_processing: break
                with open(fp, 'r', encoding='utf-8-sig') as f:
                    all_content += f"\n{'='*60}\n文件: {os.path.basename(fp)}\n{'='*60}\n" + f.read()
                gc.collect()
            self.queue.put(("input_text", all_content))
            self.queue.put(("file_info", f"已导入 {len(files)} 个文件"))
            self.queue.put(("status_update", "导入完成"))
        except Exception as e:
            self.queue.put(("processing_error", f"导入错误: {e}"))
        finally:
            self.queue.put(("processing_done", None))
    
    def export_txt(self):
        output_text = self.output_text.get("1.0", tk.END).strip()
        if not output_text: messagebox.showwarning("警告", "没有可导出的内容"); return
        save_dir = filedialog.askdirectory(title="选择保存目录")
        if not save_dir: return
        try:
            data = json.loads(output_text)
            if not isinstance(data, dict): raise ValueError("不是JSON对象")
            items = sorted(data.items(), key=lambda x: int(x[0]))
            total = len(items)
            chunk_size = 500
            for i in range(0, total, chunk_size):
                chunk = dict(items[i:i+chunk_size])
                fname = f"scriptData{i//chunk_size+1}.txt"
                with open(os.path.join(save_dir, fname), 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("完成", f"导出 {total} 条对话到 {save_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def clear_all(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.imported_files = []
        self.file_info_var.set("未选择文件")
        self.status_var.set("已清除")
        self.progress_var.set(0)
        self.progress_text.set("就绪")
    
    # ---------- 工具函数 ----------
    def clean_text(self, text):
        if not text: return ""
        text = text.replace("\\n", "\n")
        for ch in ["%n", "；", "\\t", "\\r"]:
            text = text.replace(ch, "")
        return text.strip()
    
    def format_speaker(self, name):
        if not name: return ""
        if "【" not in name and "】" not in name:
            return f"【{name}】"
        return name
    
    # ---------- 核心提取（多语言/单语言通用） ----------
    def extract_text_from_entry(self, entry):
        """
        提取文本，优先返回第二个（中文）。
        支持结构:
        - 单语言: entry[1] = [[speaker/null, "文本", ...]]
        - 多语言: entry[1] = [[null, "日文", ...], [null, "中文", ...]]
        """
        try:
            if not isinstance(entry, list) or len(entry) < 2:
                return ""
            texts = []
            if isinstance(entry[1], list):
                for inner in entry[1]:
                    if isinstance(inner, list) and len(inner) >= 2 and isinstance(inner[1], str):
                        texts.append(inner[1])
                if texts:
                    return self.clean_text(texts[1] if len(texts) >= 2 else texts[0])
            # 极端情况：entry[1] 直接是字符串
            if isinstance(entry[1], str):
                return self.clean_text(entry[1])
        except Exception:
            pass
        return ""
    
    def extract_speaker_from_entry(self, entry):
        if not isinstance(entry, list): return ""
        # 优先 entry[0]（非 null）
        if len(entry) >= 1 and isinstance(entry[0], str) and entry[0].strip():
            return entry[0]
        # 其次 entry[1][0][0]
        try:
            if len(entry) >= 2 and isinstance(entry[1], list) and len(entry[1]) > 0:
                inner = entry[1][0]
                if isinstance(inner, list) and len(inner) >= 1:
                    sp = inner[0]
                    if isinstance(sp, str) and sp.strip():
                        return sp
        except Exception:
            pass
        return ""
    
    def extract_background_and_blur_from_entry(self, entry):
        if len(entry) < 5 or not isinstance(entry[4], dict): return "", False
        data_arr = entry[4].get("data", [])
        if not isinstance(data_arr, list): return "", False
        for item in data_arr:
            if isinstance(item, list) and len(item) >= 3 and item[1] == "stage":
                params = item[2]
                if isinstance(params, dict):
                    redraw = params.get("redraw", {})
                    img = redraw.get("imageFile", {})
                    if isinstance(img, dict):
                        file = img.get("file", "")
                        if isinstance(file, str) and file:
                            if '.' in file: file = file.rsplit('.', 1)[0]
                            has_blur = self._check_doBoxBlur(img)
                            return file, has_blur
        return "", False
    
    def _check_doBoxBlur(self, obj):
        if isinstance(obj, dict):
            return any(self._check_doBoxBlur(v) for v in obj.values())
        elif isinstance(obj, list):
            return any(self._check_doBoxBlur(x) for x in obj)
        elif isinstance(obj, str) and "doBoxBlur" in obj:
            return True
        return False
    
    def extract_characters_from_entry(self, entry):
        if len(entry) < 5 or not isinstance(entry[4], dict): return ""
        data_arr = entry[4].get("data", [])
        if not isinstance(data_arr, list): return ""
        chars = []
        for item in data_arr:
            if isinstance(item, list) and len(item) >= 3 and item[1] == "character":
                params = item[2]
                if isinstance(params, dict) and params.get("showmode") == 3:
                    redraw = params.get("redraw", {})
                    img = redraw.get("imageFile", {})
                    if isinstance(img, dict):
                        file = img.get("file", "")
                        if isinstance(file, str) and file:
                            opts = img.get("options", {})
                            parts = []
                            dress = opts.get("dress", "")
                            pose = opts.get("pose", "")
                            if dress: parts.append(f"dress={dress}")
                            if pose: parts.append(f"pose={pose}")
                            query = "&".join(parts)
                            chars.append(f"{file}?{query}" if query else file)
        return ";".join(chars)
    
    def extract_cg_from_entry(self, entry):
        """
        提取 CG/事件图/SD 插画。
        匹配 sdlayer、event、centerlayer，对 centerlayer 要求 showmode == 3。
        """
        if len(entry) < 5 or not isinstance(entry[4], dict): return ""
        data_arr = entry[4].get("data", [])
        if not isinstance(data_arr, list): return ""
        cgs = []
        for item in data_arr:
            if isinstance(item, list) and len(item) >= 3 and item[1] in ("sdlayer", "event", "centerlayer"):
                params = item[2]
                if isinstance(params, dict):
                    # 如果是 centerlayer，只提取可见图层
                    if item[1] == "centerlayer" and params.get("showmode") != 3:
                        continue
                    img = params.get("redraw", {}).get("imageFile", {})
                    if isinstance(img, dict):
                        file = img.get("file", "")
                        if isinstance(file, str) and file:
                            if '.' in file: file = file.rsplit('.', 1)[0]
                            cgs.append(file)
        return ";".join(cgs)
    
    # ---------- 构建条目字典 ----------
    def entry_to_dict(self, entry):
        text = self.extract_text_from_entry(entry)
        if not text: return None
        speaker = self.format_speaker(self.extract_speaker_from_entry(entry))
        bg, blur = self.extract_background_and_blur_from_entry(entry)
        chars = self.extract_characters_from_entry(entry)
        cg = self.extract_cg_from_entry(entry)   # 已包含 SD 图层
        return {
            "speaker_raw": speaker.strip("【】") if speaker else "",
            "speaker": speaker,
            "text": text,
            "background": bg,
            "blur": blur,
            "characters": chars,
            "cg": cg
        }
    
    # ---------- 立绘处理逻辑（沿用原版） ----------
    def process_characters(self, entries):
        def get_raw(s):
            m = re.search(r'【(.+?)】', s)
            return m.group(1) if m else s.strip()
        def unique(s):
            return ';'.join(dict.fromkeys(s.split(';'))) if s else s
        
        is_ref = [False] * len(entries)
        for i, item in enumerate(entries):
            sp = item.get("speaker", "")
            ch = item.get("characters", "")
            if not sp or not ch: continue
            poses = ch.split(';')
            ori_len = len(poses)
            poses = list(dict.fromkeys(poses))
            raw = get_raw(sp)
            matched = [p for p in poses if p.startswith(raw + '.')]
            if matched:
                item["characters"] = matched[0]
                if ori_len > 1: is_ref[i] = True
            else:
                item["characters"] = ';'.join(poses)
        for i, item in enumerate(entries):
            if is_ref[i]: continue
            ch = item.get("characters", "")
            if not ch: continue
            poses = list(dict.fromkeys(ch.split(';')))
            if len(poses) <= 1:
                item["characters"] = ';'.join(poses)
                continue
            raw = get_raw(item.get("speaker", ""))
            ref_idx = None
            for j in range(i-1, -1, -1):
                if is_ref[j]: ref_idx = j; break
            if ref_idx is not None:
                ref_raw = get_raw(entries[ref_idx].get("speaker", ""))
                matched = [p for p in poses if p.startswith(ref_raw + '.')]
                item["characters"] = matched[0] if matched else poses[0]
            else:
                item["characters"] = poses[0]
        for item in entries:
            if "characters" in item:
                item["characters"] = unique(item["characters"])
    
    # ---------- 解析入口：先尝试整体JSON，再正则扫描 ----------
    def find_all_script_entries_ordered(self, input_data):
        # 去除 BOM
        if input_data.startswith('\ufeff'):
            input_data = input_data[1:]
        
        # 1) 尝试整体 JSON 解析（支持数组或 {"texts":[...]}）
        try:
            parsed = json.loads(input_data)
            raw_items = []
            if isinstance(parsed, list):
                raw_items = parsed
            elif isinstance(parsed, dict) and "texts" in parsed:
                raw_items = parsed["texts"]
            if raw_items:
                entries = []
                for item in raw_items:
                    if self.cancel_processing: break
                    if not isinstance(item, list): continue
                    d = self.entry_to_dict(item)
                    if d: entries.append(d)
                    # nexts 跳转
                    if len(item) >= 5 and isinstance(item[4], dict):
                        nexts = item[4].get("nexts")
                        if isinstance(nexts, list):
                            for nxt in nexts:
                                if isinstance(nxt, dict) and "target" in nxt:
                                    entries.append({
                                        "speaker_raw": f"[{nxt['target']}]",
                                        "speaker": f"[{nxt['target']}]",
                                        "text": "", "background": "ecall",
                                        "blur": False, "characters": "", "cg": ""
                                    })
                self.queue.put(("status_update", f"JSON解析：{len(raw_items)}原始条目 → {len(entries)}有效条目"))
                return entries
        except (json.JSONDecodeError, ValueError):
            pass  # 不是完整JSON，继续正则扫描
        
        # 2) 正则扫描（兼容旧单语言及散列多语言）
        chapter_pattern = re.compile(r'chapter.*?(\d+-\d+)', re.IGNORECASE)
        chapter_matches = [(m.start(), m.group(1)) for m in chapter_pattern.finditer(input_data)]
        seen = set()
        unique_chapters = []
        for pos, cs in chapter_matches:
            if cs not in seen:
                seen.add(cs)
                unique_chapters.append((pos, cs))
        unique_chapters.sort(key=lambda x: x[0])
        
        # 正则模式（按优先级排列）
        dialogue_patterns = [
            # 多语言无说话者 [null,[[null,"日文"],[null,"中文"]] ...
            (r'\[null,\s*\[\[null,\s*"([^"]*)"[^\]]*\]\s*,\s*\[null,\s*"([^"]*)"', "multi_no_speaker"),
            # 多语言有说话者 ["说话者",[[null,"日文"],[null,"中文"]] ...
            (r'\["([^"]*)",\s*\[\[null,\s*"([^"]*)"[^\]]*\]\s*,\s*\[null,\s*"([^"]*)"', "multi_speaker"),
            # 单语言无说话者
            (r'\[null,\s*\[\[null,\s*"([^"]*)"[^\]]*\]\][^\]]*\]', "no_speaker"),
            # 单语言有说话者（内层说话者）
            (r'\["([^"]*)",\s*\[\["([^"]*)",\s*"([^"]*)"[^\]]*\]\][^\]]*\]', "inner_speaker"),
            # 单语言有说话者（外层说话者）
            (r'\["([^"]*)",\s*\[\[null,\s*"([^"]*)"[^\]]*\]\][^\]]*\]', "outer_speaker"),
            (r'\["([^"]*)",\s*\[\[null,\s*"([^"]*)",\d+,"[^"]*","[^"]*"\]\][^\]]*\]', "outer_speaker"),
            (r'\[null,\s*\[\[null,\s*"([^"]*)",\d+,"[^"]*","[^"]*"\]\][^\]]*\]', "no_speaker")
        ]
        
        current_pos = 0
        length = len(input_data)
        all_items = []
        
        while current_pos < length:
            if self.cancel_processing: break
            
            earliest_match = None
            earliest_idx = -1
            earliest_pos = length
            
            for i, (pat, _) in enumerate(dialogue_patterns):
                m = re.search(pat, input_data[current_pos:])
                if m:
                    pos = current_pos + m.start()
                    if pos < earliest_pos:
                        earliest_pos = pos
                        earliest_match = m
                        earliest_idx = i
            
            if earliest_match is None: break
            
            start_pos = earliest_pos
            pos = start_pos
            stack = 0
            in_string = False
            escape = False
            end_pos = -1
            
            while pos < length:
                ch = input_data[pos]
                if not in_string:
                    if ch == '[': stack += 1
                    elif ch == ']':
                        stack -= 1
                        if stack == 0:
                            end_pos = pos + 1
                            break
                    elif ch == '"': in_string = True
                else:
                    if ch == '"' and not escape: in_string = False
                    elif ch == '\\' and not escape: escape = True
                    else: escape = False
                pos += 1
            
            if end_pos == -1:
                current_pos = start_pos + 1
                continue
            
            entry_str = input_data[start_pos:end_pos]
            
            try:
                entry = json.loads(entry_str)
                if isinstance(entry, list) and len(entry) >= 2:
                    d = self.entry_to_dict(entry)
                    if d: all_items.append((start_pos, d, True))
                    # nexts 跳转
                    if len(entry) >= 5 and isinstance(entry[4], dict):
                        nexts = entry[4].get("nexts")
                        if isinstance(nexts, list):
                            for nxt in nexts:
                                if isinstance(nxt, dict) and "target" in nxt:
                                    all_items.append((end_pos, {
                                        "speaker_raw": f"[{nxt['target']}]",
                                        "speaker": f"[{nxt['target']}]",
                                        "text": "", "background": "ecall",
                                        "blur": False, "characters": "", "cg": ""
                                    }, False))
            except json.JSONDecodeError:
                ptype = dialogue_patterns[earliest_idx][1]
                if ptype == "multi_no_speaker":
                    text = earliest_match.group(2)
                elif ptype == "multi_speaker":
                    text = earliest_match.group(3)
                elif ptype == "no_speaker":
                    text = earliest_match.group(2)
                elif ptype == "inner_speaker":
                    text = earliest_match.group(4)
                else:
                    text = earliest_match.group(3)
                text = self.clean_text(text)
                if text:
                    all_items.append((start_pos, {"speaker_raw":"","speaker":"","text":text,"background":"","blur":False,"characters":"","cg":""}, True))
            
            current_pos = end_pos
        
        all_items.sort(key=lambda x: x[0])
        
        # 插入章节标记
        final_entries = []
        chap_idx = 0
        for pos, item, _ in all_items:
            while chap_idx < len(unique_chapters) and unique_chapters[chap_idx][0] < pos:
                cs = unique_chapters[chap_idx][1]
                final_entries.append({
                    "speaker_raw": f"[CHAPTER{cs}]", "speaker": f"[CHAPTER{cs}]",
                    "text": "", "background": "ecall", "blur": False,
                    "characters": "", "cg": ""
                })
                chap_idx += 1
            final_entries.append(item)
        while chap_idx < len(unique_chapters):
            cs = unique_chapters[chap_idx][1]
            final_entries.append({
                "speaker_raw": f"[CHAPTER{cs}]", "speaker": f"[CHAPTER{cs}]",
                "text": "", "background": "ecall", "blur": False,
                "characters": "", "cg": ""
            })
            chap_idx += 1
        
        return final_entries
    
    # ---------- 转换线程 ----------
    def convert_script_thread(self):
        try:
            if self.imported_files:
                self.queue.put(("progress_update", {"progress":0, "message":"读取文件中..."}))
                all_entries = []
                for i, fp in enumerate(self.imported_files):
                    if self.cancel_processing: break
                    with open(fp, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                    entries = self.find_all_script_entries_ordered(content)
                    all_entries.extend(entries)
                    self.queue.put(("progress_update", {"progress":(i+1)/len(self.imported_files)*50, "message":f"处理 {os.path.basename(fp)}"}))
                if self.cancel_processing: return
                entries = all_entries
            else:
                input_data = self.input_text.get("1.0", tk.END).strip()
                if not input_data:
                    self.queue.put(("output_text", "请输入数据")); self.queue.put(("processing_done", None)); return
                entries = self.find_all_script_entries_ordered(input_data)
                self.queue.put(("status_update", f"成功提取 {len(entries)} 条对话"))
            
            if self.cancel_processing: return
            if not entries:
                self.queue.put(("status_update", "警告: 未找到匹配的剧本条目"))
                self.queue.put(("output_text", "（无有效条目）"))
                self.queue.put(("processing_done", None)); return
            
            self.process_characters(entries)
            
            result = {}
            for i, item in enumerate(entries):
                eid = i + 1
                out = {}
                if item.get("background"): out["b"] = item["background"]
                if item.get("speaker"): out["s"] = item["speaker"]
                if item.get("text"): out["t"] = item["text"]
                if item.get("characters"): out["c"] = item["characters"]
                if item.get("blur"): out["z"] = 2
                if item.get("cg"): out["cg"] = item["cg"]   # 已包含 SD 图层
                if out: result[str(eid)] = out
            
            output_str = json.dumps(result, ensure_ascii=False, indent=2)
            self.queue.put(("output_text", output_str))
            self.queue.put(("status_update", f"完成，共 {len(entries)} 条对话"))
            self.queue.put(("processing_done", None))
        except Exception as e:
            self.queue.put(("processing_error", f"转换错误: {e}"))
    
    # ---------- 加载示例（多语言数组） ----------
    def load_example(self):
        example_str = '''[
  ["风实花", [[null, "日文测试1", 12], [null, "中文测试1", 12]], [], 0, {"data": []}],
  ["李空",   [[null, "日文测试2", 20], [null, "中文测试2", 15]], [], 0, {"data": []}],
  [null,     [[null, "日文测试3", 5],  [null, "中文测试3", 12]], [], 0, {"data": []}]
]'''
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", example_str)
        self.imported_files = []
        self.file_info_var.set("多语言示例(数组)")
        self.status_var.set("已加载多语言示例，点击“转换”测试")

def main():
    root = tk.Tk()
    app = GalgameScriptConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()