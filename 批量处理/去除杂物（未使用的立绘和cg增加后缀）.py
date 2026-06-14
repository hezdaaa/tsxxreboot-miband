import os
import json
import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading


class CgPostfixTool:
    def __init__(self, root):
        self.root = root
        self.root.title("CG后缀添加 & 立绘字段清理 & 图片引用清理")
        self.root.geometry("950x800")  # 稍微调高
        self.root.configure(bg='#1e1e1e')

        self.setup_dark_theme()

        # 数据 - 原有
        self.script_path = ""
        self.all_dialogues = {}
        self.total_dialogues = 0
        self.cg_fix_list = []      # (dialogue_id, old_cg, new_cg)
        self.c_remove_list = []    # (dialogue_id, old_c_value)
        self.cg_modified_count = 0
        self.c_removed_count = 0

        # 数据 - 新增图片引用
        self.evig_path = ""
        self.orphan_images = []          # 孤立图片文件路径列表
        self.invalid_cg_refs = []        # 无效cg引用 (dialogue_id, cg_value)
        self.orphan_count = 0
        self.invalid_cg_count = 0

        # 控制线程标志
        self.loading_thread = None
        self.scan_thread = None
        self.image_scan_thread = None
        self.cancel_flag = False

        self.create_widgets()

    def setup_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.',
                        background='#1e1e1e',
                        foreground='#d4d4d4',
                        fieldbackground='#252526',
                        insertcolor='#d4d4d4',
                        selectbackground='#264f78',
                        selectforeground='#d4d4d4',
                        troughcolor='#3c3c3c')
        style.configure('TButton',
                        background='#333333',
                        foreground='#d4d4d4',
                        borderwidth=1)
        style.map('TButton',
                  background=[('active', '#555555')])
        style.configure('TLabel',
                        background='#1e1e1e',
                        foreground='#d4d4d4')
        style.configure('TLabelframe',
                        background='#1e1e1e',
                        foreground='#d4d4d4',
                        bordercolor='#555555')
        style.configure('TLabelframe.Label',
                        background='#1e1e1e',
                        foreground='#569cd6')
        style.configure('TEntry',
                        fieldbackground='#252526',
                        foreground='#d4d4d4',
                        bordercolor='#555555')
        style.configure('Vertical.TScrollbar',
                        background='#3c3c3c',
                        troughcolor='#1e1e1e')
        style.configure('TProgressbar', thickness=10)

    def create_widgets(self):
        # ========== 顶部：项目设置 ==========
        top_frame = ttk.LabelFrame(self.root, text="项目设置", padding="10")
        top_frame.pack(fill="x", padx=10, pady=5)

        # 脚本路径
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(fill="x", pady=2)
        ttk.Label(path_frame, text="脚本文件夹:").pack(side="left", padx=5)
        self.script_path_var = tk.StringVar()
        script_entry = ttk.Entry(path_frame, textvariable=self.script_path_var, width=50)
        script_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(path_frame, text="浏览...", command=self.select_script_folder).pack(side="right", padx=5)
        ttk.Button(path_frame, text="加载脚本", command=self.start_load_scripts).pack(side="right", padx=5)

        # 图片目录 (evig) - 自动设置，也可手动修改
        evig_frame = ttk.Frame(top_frame)
        evig_frame.pack(fill="x", pady=2)
        ttk.Label(evig_frame, text="CG图片目录:").pack(side="left", padx=5)
        self.evig_path_var = tk.StringVar()
        evig_entry = ttk.Entry(evig_frame, textvariable=self.evig_path_var, width=50)
        evig_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(evig_frame, text="浏览...", command=self.select_evig_folder).pack(side="right", padx=5)
        ttk.Button(evig_frame, text="刷新路径", command=self.refresh_evig_path).pack(side="right", padx=5)

        # 进度条
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(top_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.pack(fill="x", pady=5)

        # 状态栏
        status_frame = ttk.Frame(top_frame)
        status_frame.pack(fill="x", pady=2)
        self.status_label = ttk.Label(status_frame, text="未加载脚本", foreground="#6a9955")
        self.status_label.pack(side="left", padx=5)
        self.stats_label = ttk.Label(status_frame, text="")
        self.stats_label.pack(side="right", padx=5)

        # ========== 日志区域 ==========
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding="10")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='#d4d4d4',
            selectbackground='#264f78',
            relief='flat',
            height=20
        )
        self.log_text.pack(fill="both", expand=True)

        # ========== 按钮区域 ==========
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=5)

        # 第一行：原有功能
        ttk.Button(button_frame, text="扫描并预览修改", command=self.start_scan_preview).pack(side="left", padx=5)
        ttk.Button(button_frame, text="执行修复", command=self.execute_fix).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消操作", command=self.cancel_operation).pack(side="left", padx=5)

        # 第二行：新增图片清理
        img_button_frame = ttk.Frame(self.root)
        img_button_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(img_button_frame, text="扫描图片引用", command=self.start_image_scan).pack(side="left", padx=5)
        ttk.Button(img_button_frame, text="清理图片引用", command=self.start_clean_images).pack(side="left", padx=5)
        ttk.Button(img_button_frame, text="退出", command=self.root.quit).pack(side="right", padx=5)

        # 初始化evig路径
        self.refresh_evig_path()

    # ---------- 辅助方法 ----------
    def refresh_evig_path(self):
        """根据当前脚本路径自动设置evig目录"""
        if self.script_path and os.path.isdir(self.script_path):
            evig = os.path.join(self.script_path, "evig")
            if os.path.isdir(evig):
                self.evig_path = evig
                self.evig_path_var.set(evig)
                return
        # 如果不存在，清空但保留显示
        self.evig_path = ""
        self.evig_path_var.set("")

    def select_script_folder(self):
        folder = filedialog.askdirectory(title="选择script文件夹")
        if folder:
            self.script_path = folder
            self.script_path_var.set(folder)
            self.log(f"脚本目录: {folder}", "#858585")
            self.refresh_evig_path()
            self.update_status("脚本文件夹已选择，请点击“加载脚本”")

    def select_evig_folder(self):
        folder = filedialog.askdirectory(title="选择CG图片目录(evig)")
        if folder:
            self.evig_path = folder
            self.evig_path_var.set(folder)
            self.log(f"CG图片目录: {folder}", "#858585")

    # ---------- 日志与状态 ----------
    def log(self, message, color="#d4d4d4"):
        def _log():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            tag = f"color_{color.replace('#', '')}"
            self.log_text.tag_add(tag, "end-1c linestart", "end-1c")
            self.log_text.tag_config(tag, foreground=color)
        self.root.after(0, _log)

    def update_status(self, text, color="#6a9955"):
        self.root.after(0, lambda: self.status_label.config(text=text, foreground=color))

    def update_stats(self, text):
        self.root.after(0, lambda: self.stats_label.config(text=text))

    def set_progress(self, value, max_val=100):
        self.root.after(0, lambda: self.progress_var.set(int(value * 100 / max_val)))

    # ---------- 加载脚本 (原有) ----------
    def start_load_scripts(self):
        if not self.script_path or not os.path.exists(self.script_path):
            messagebox.showwarning("警告", "请先选择有效的脚本文件夹！")
            return
        if self.loading_thread and self.loading_thread.is_alive():
            messagebox.showinfo("提示", "正在加载中，请稍候...")
            return
        self.cancel_flag = False
        self.loading_thread = threading.Thread(target=self.load_scripts_worker, daemon=True)
        self.loading_thread.start()

    def load_scripts_worker(self):
        self.update_status("正在扫描脚本文件...")
        self.log("开始加载脚本文件...", "#569cd6")
        try:
            script_files = [f for f in os.listdir(self.script_path)
                            if f.lower().startswith("scriptdata") and f.lower().endswith(".txt")]
        except Exception as e:
            self.log(f"扫描失败: {e}", "#ff6666")
            self.update_status("加载失败")
            return

        if not script_files:
            self.log("未找到任何 scriptData*.txt 文件！", "#ff6666")
            self.update_status("未找到脚本文件")
            return

        def extract_number(filename):
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else 0

        script_files.sort(key=extract_number)
        total_files = len(script_files)
        self.all_dialogues = {}
        total_entries = 0

        for idx, script_file in enumerate(script_files):
            if self.cancel_flag:
                self.log("加载已取消", "#ffcc00")
                self.update_status("已取消")
                return
            file_path = os.path.join(self.script_path, script_file)
            self.set_progress(idx, total_files)
            self.update_status(f"正在加载 {script_file}...")
            try:
                encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']
                chunk_data = None
                for enc in encodings:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            chunk_data = json.load(f)
                        break
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                if chunk_data:
                    for k, v in chunk_data.items():
                        self.all_dialogues[k] = v
                    total_entries += len(chunk_data)
                    self.log(f"已加载 {script_file} ({len(chunk_data)} 条)", "#858585")
            except Exception as e:
                self.log(f"加载 {script_file} 失败: {e}", "#ff6666")

        self.total_dialogues = total_entries
        self.set_progress(total_files, total_files)
        self.log(f"加载完成！共 {self.total_dialogues} 条对话", "#6a9955")
        self.update_status("脚本加载完成，可进行扫描预览")
        # 自动刷新evig路径
        self.refresh_evig_path()
        # 自动开始扫描预览（原行为）
        self.start_scan_preview()

    # ---------- 原有扫描与修复 ----------
    def start_scan_preview(self):
        if not self.all_dialogues:
            messagebox.showwarning("警告", "请先加载脚本！")
            return
        if self.scan_thread and self.scan_thread.is_alive():
            messagebox.showinfo("提示", "正在扫描中，请稍候...")
            return
        self.cancel_flag = False
        self.scan_thread = threading.Thread(target=self.scan_preview_worker, daemon=True)
        self.scan_thread.start()

    def scan_preview_worker(self):
        self.update_status("正在扫描预览...")
        self.log("\n" + "=" * 70, "#858585")
        self.log("开始扫描需要修改的字段...", "#569cd6")

        self.cg_fix_list.clear()
        self.c_remove_list.clear()
        self.cg_modified_count = 0
        self.c_removed_count = 0

        total = len(self.all_dialogues)
        processed = 0

        for dia_id, script in self.all_dialogues.items():
            if self.cancel_flag:
                self.log("扫描已取消", "#ffcc00")
                self.update_status("已取消")
                return
            processed += 1
            if processed % 500 == 0:
                self.set_progress(processed, total)
                self.update_status(f"扫描中... {processed}/{total}")

            # 处理 cg 字段
            if 'cg' in script and script['cg']:
                old_cg = script['cg']
                new_cg = self.process_cg_value(old_cg)
                if new_cg != old_cg:
                    self.cg_fix_list.append((dia_id, old_cg, new_cg))
                    self.cg_modified_count += 1
                    if self.cg_modified_count <= 100:
                        self.log(f"[CG修改] {dia_id}:", "#ffcc00")
                        self.log(f"  旧: {old_cg}", "#858585")
                        self.log(f"  新: {new_cg}", "#6a9955")

            # 处理 c 字段（立绘）
            if 'c' in script and script['c'] and isinstance(script['c'], str):
                c_val = script['c']
                if self.contains_cjk_jp(c_val):
                    self.c_remove_list.append((dia_id, c_val))
                    self.c_removed_count += 1
                    if self.c_removed_count <= 100:
                        self.log(f"[立绘移除] {dia_id}:", "#ff6666")
                        self.log(f"  值: {c_val[:60]}{'...' if len(c_val) > 60 else ''}", "#858585")

        self.set_progress(total, total)
        if self.cg_modified_count == 0 and self.c_removed_count == 0:
            self.log("没有发现需要修改的项。", "#6a9955")
        else:
            if self.cg_modified_count > 100:
                self.log(f"... 还有 {self.cg_modified_count - 100} 个 CG 修改未显示详情", "#858585")
            if self.c_removed_count > 100:
                self.log(f"... 还有 {self.c_removed_count - 100} 个立绘移除未显示详情", "#858585")
            self.log(f"统计: CG字段需修改 {self.cg_modified_count} 处, 立绘字段需移除 {self.c_removed_count} 处", "#ffcc00")
        self.log("=" * 70, "#858585")
        self.update_stats(f"CG修改: {self.cg_modified_count} | 立绘移除: {self.c_removed_count}")
        self.update_status("扫描完成")

    @staticmethod
    def contains_cjk_jp(text):
        if not isinstance(text, str):
            return False
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff' or '\u3040' <= ch <= '\u309f' or '\u30a0' <= ch <= '\u30ff':
                return True
        return False

    @staticmethod
    def remove_existing_extension(filename):
        if not isinstance(filename, str):
            return filename
        return re.sub(r'\.(jpg|jpeg|png|gif)$', '', filename, flags=re.I)

    def process_cg_value(self, cg_value):
        if not isinstance(cg_value, str):
            return cg_value
        base = self.remove_existing_extension(cg_value)
        if base.lower().startswith('sd'):
            return base + '.png'
        else:
            return base + '.jpg'

    def cancel_operation(self):
        self.cancel_flag = True
        self.log("正在取消当前操作...", "#ffcc00")
        self.update_status("取消请求已发送")

    def execute_fix(self):
        if not self.all_dialogues:
            messagebox.showwarning("警告", "没有加载任何数据，请先加载脚本。")
            return
        if self.cg_modified_count == 0 and self.c_removed_count == 0:
            messagebox.showinfo("提示", "没有需要修改的项，请先执行“扫描并预览修改”。")
            return
        msg = f"即将执行以下操作：\n- 修改 {self.cg_modified_count} 个 CG 字段（添加正确后缀）\n- 移除 {self.c_removed_count} 个含中日文的立绘字段\n\n是否继续？"
        if not messagebox.askyesno("确认修改", msg):
            return

        self.log("\n开始执行修改...", "#569cd6")
        self.update_status("正在修改并保存...")

        # 修改内存数据
        for dia_id, old_cg, new_cg in self.cg_fix_list:
            self.all_dialogues[dia_id]['cg'] = new_cg
        for dia_id, old_c_val in self.c_remove_list:
            if dia_id in self.all_dialogues and 'c' in self.all_dialogues[dia_id]:
                del self.all_dialogues[dia_id]['c']

        # 保存回文件
        self.save_all_chunks()
        self.update_status("修复完成")
        self.update_stats(f"已修改: CG {self.cg_modified_count} | 立绘移除 {self.c_removed_count}")

    def save_all_chunks(self):
        """将self.all_dialogues按chunk保存到文件"""
        chunk_files = {}
        for dia_id, script in self.all_dialogues.items():
            try:
                id_num = int(dia_id)
                chunk_num = (id_num - 1) // 500 + 1
                if chunk_num not in chunk_files:
                    chunk_files[chunk_num] = {}
                chunk_files[chunk_num][dia_id] = script
            except ValueError:
                continue

        total_chunks = len(chunk_files)
        saved_chunks = 0
        failed_chunks = []

        for chunk_num, chunk_data in chunk_files.items():
            chunk_file = os.path.join(self.script_path, f"scriptData{chunk_num}.txt")
            try:
                sorted_data = {k: chunk_data[k] for k in sorted(chunk_data.keys(), key=lambda x: int(x))}
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    json.dump(sorted_data, f, ensure_ascii=False, indent=2)
                saved_chunks += 1
                self.log(f"已保存块 {chunk_num}", "#6a9955")
            except Exception as e:
                failed_chunks.append(chunk_num)
                self.log(f"保存块 {chunk_num} 失败: {e}", "#ff6666")

        if failed_chunks:
            self.log(f"部分保存失败: {failed_chunks}", "#ff6666")
            messagebox.showwarning("保存警告", f"成功保存 {saved_chunks}/{total_chunks} 个文件。\n失败块: {failed_chunks}")
        else:
            self.log(f"所有更改已保存！共 {saved_chunks} 个文件", "#6a9955")

    # ==================== 新增：图片引用扫描与清理 ====================
    def start_image_scan(self):
        if not self.all_dialogues:
            messagebox.showwarning("警告", "请先加载脚本！")
            return
        if not self.evig_path or not os.path.isdir(self.evig_path):
            messagebox.showwarning("警告", "CG图片目录不存在或未设置！请检查 ./evig 文件夹。")
            return
        if self.image_scan_thread and self.image_scan_thread.is_alive():
            messagebox.showinfo("提示", "正在扫描中，请稍候...")
            return
        self.cancel_flag = False
        self.image_scan_thread = threading.Thread(target=self.image_scan_worker, daemon=True)
        self.image_scan_thread.start()

    def image_scan_worker(self):
        self.update_status("正在扫描图片引用...")
        self.log("\n" + "=" * 70, "#858585")
        self.log("开始扫描CG图片引用一致性...", "#569cd6")

        self.orphan_images.clear()
        self.invalid_cg_refs.clear()
        self.orphan_count = 0
        self.invalid_cg_count = 0

        # 1. 获取所有脚本中引用的cg文件名（标准化后）
        referenced_files = set()
        for dia_id, script in self.all_dialogues.items():
            if 'cg' in script and script['cg']:
                std_name = self.process_cg_value(script['cg']).lower()
                referenced_files.add(std_name)

        # 2. 扫描evig目录下所有图片文件
        try:
            all_image_files = []
            for f in os.listdir(self.evig_path):
                if re.search(r'\.(png|jpg|jpeg|gif|webp|bmp)$', f, re.I):
                    all_image_files.append(f)
        except Exception as e:
            self.log(f"扫描evig目录失败: {e}", "#ff6666")
            self.update_status("扫描失败")
            return

        total_images = len(all_image_files)
        self.log(f"evig目录下共 {total_images} 个图片文件", "#858585")
        self.log(f"脚本中共引用 {len(referenced_files)} 个唯一CG文件名", "#858585")

        # 3. 找出孤立图片（文件存在但未被任何cg引用）
        # 这里使用小写比对
        for img_file in all_image_files:
            if self.cancel_flag:
                self.log("扫描已取消", "#ffcc00")
                self.update_status("已取消")
                return
            img_lower = img_file.lower()
            if img_lower not in referenced_files:
                self.orphan_images.append(os.path.join(self.evig_path, img_file))
                self.orphan_count += 1
                if self.orphan_count <= 100:
                    self.log(f"[孤立图片] {img_file}", "#ff6666")

        # 4. 找出无效cg引用（脚本引用了但文件中不存在）
        # 获取evig中的文件小写集合
        evig_files_lower = {f.lower() for f in all_image_files}
        for dia_id, script in self.all_dialogues.items():
            if self.cancel_flag:
                self.log("扫描已取消", "#ffcc00")
                self.update_status("已取消")
                return
            if 'cg' in script and script['cg']:
                std_name = self.process_cg_value(script['cg']).lower()
                if std_name not in evig_files_lower:
                    self.invalid_cg_refs.append((dia_id, script['cg']))
                    self.invalid_cg_count += 1
                    if self.invalid_cg_count <= 100:
                        self.log(f"[无效CG引用] {dia_id}: {script['cg']}", "#ffcc00")

        # 报告
        if self.orphan_count == 0 and self.invalid_cg_count == 0:
            self.log("图片引用完全一致，无需要清理的项。", "#6a9955")
        else:
            if self.orphan_count > 100:
                self.log(f"... 还有 {self.orphan_count - 100} 个孤立图片未显示详情", "#858585")
            if self.invalid_cg_count > 100:
                self.log(f"... 还有 {self.invalid_cg_count - 100} 个无效CG引用未显示详情", "#858585")
            self.log(f"统计: 孤立图片 {self.orphan_count} 个, 无效CG引用 {self.invalid_cg_count} 处", "#ffcc00")
        self.log("=" * 70, "#858585")
        self.update_stats(f"孤立图片: {self.orphan_count} | 无效CG: {self.invalid_cg_count}")
        self.update_status("图片引用扫描完成")

    def start_clean_images(self):
        if not self.orphan_images and not self.invalid_cg_refs:
            messagebox.showinfo("提示", "没有可清理的孤立图片或无效CG引用，请先执行“扫描图片引用”。")
            return
        msg = f"即将执行以下操作：\n" \
              f"- 移动 {self.orphan_count} 个孤立图片到 _cg_backup 文件夹\n" \
              f"- 删除 {self.invalid_cg_count} 个无效CG字段（从对话数据中移除）\n\n" \
              f"是否继续？"
        if not messagebox.askyesno("确认清理", msg):
            return

        self.cancel_flag = False
        # 在后台线程中执行清理，避免界面卡死
        clean_thread = threading.Thread(target=self.clean_images_worker, daemon=True)
        clean_thread.start()

    def clean_images_worker(self):
        self.update_status("正在清理图片引用...")
        self.log("\n开始清理...", "#569cd6")

        # ---- 1. 移动孤立图片 ----
        if self.orphan_images:
            backup_dir = os.path.join(self.script_path, "_cg_backup")
            try:
                os.makedirs(backup_dir, exist_ok=True)
            except Exception as e:
                self.log(f"创建备份目录失败: {e}", "#ff6666")
                # 继续尝试直接删除？为安全，停止
                messagebox.showerror("错误", f"无法创建备份目录 {backup_dir}，清理终止。")
                return

            moved = 0
            for img_path in self.orphan_images:
                if self.cancel_flag:
                    self.log("清理已取消", "#ffcc00")
                    break
                try:
                    shutil.move(img_path, backup_dir)
                    moved += 1
                    self.log(f"[移动] {os.path.basename(img_path)} -> _cg_backup", "#6a9955")
                except Exception as e:
                    self.log(f"[移动失败] {os.path.basename(img_path)}: {e}", "#ff6666")
            self.log(f"已移动 {moved}/{len(self.orphan_images)} 个孤立图片到备份目录", "#6a9955")
            self.orphan_count = 0
            self.orphan_images.clear()
        else:
            self.log("没有孤立图片需要移动。", "#858585")

        # ---- 2. 删除无效CG引用 ----
        if self.invalid_cg_refs:
            removed = 0
            for dia_id, old_cg in self.invalid_cg_refs:
                if self.cancel_flag:
                    self.log("清理已取消", "#ffcc00")
                    break
                if dia_id in self.all_dialogues and 'cg' in self.all_dialogues[dia_id]:
                    del self.all_dialogues[dia_id]['cg']
                    removed += 1
                    self.log(f"[删除cg] {dia_id}: 原值 '{old_cg}'", "#ffcc00")
                else:
                    self.log(f"[跳过] {dia_id}: cg字段已不存在", "#858585")
            self.log(f"已删除 {removed}/{len(self.invalid_cg_refs)} 个无效CG引用", "#6a9955")
            self.invalid_cg_count = 0
            self.invalid_cg_refs.clear()
        else:
            self.log("没有无效CG引用需要删除。", "#858585")

        # ---- 3. 保存更改到文件 ----
        if hasattr(self, 'all_dialogues') and self.all_dialogues:
            self.log("正在保存修改后的脚本文件...", "#569cd6")
            self.save_all_chunks()
        else:
            self.log("没有对话数据需要保存。", "#858585")

        self.update_stats(f"孤立图片: 0 | 无效CG: 0")
        self.update_status("清理完成")
        self.log("清理操作全部完成。", "#6a9955")


def main():
    root = tk.Tk()
    app = CgPostfixTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()