import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# ---------- 图片处理函数（必须定义在全局，以便多进程调用） ----------
def process_one_image(src_path, dst_path, quality=90):
    """
    处理单张图片：
    - 若宽 > 高：向左旋转90度（逆时针）并保存
    - 否则：直接复制（不重新编码）
    返回：(status, filename, info)
    """
    try:
        # 先快速获取图片尺寸（不解码全部数据，仅读头）
        with Image.open(src_path) as img:
            w, h = img.size
            if w > h:
                # 横向图片 → 向左旋转90度（更快的方法）
                rotated = img.transpose(Image.ROTATE_90)
                # 保存参数优化
                save_kwargs = {}
                ext = os.path.splitext(src_path)[1].lower()
                if ext in ('.jpg', '.jpeg'):
                    save_kwargs = {'quality': quality, 'optimize': True, 'progressive': True}
                elif ext == '.png':
                    save_kwargs = {'compress_level': 6}  # 适中压缩
                rotated.save(dst_path, **save_kwargs)
                return ('rotated', os.path.basename(src_path), f"{w}x{h} → {h}x{w}")
            else:
                # 竖向或正方形 → 直接复制（不重新编码，极快）
                shutil.copy2(src_path, dst_path)
                return ('skipped', os.path.basename(src_path), f"{w}x{h}")
    except Exception as e:
        return ('error', os.path.basename(src_path), str(e))

# ---------- 主窗口类 ----------
class ImageRotatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("批量图片旋转工具 · 多进程高性能版")
        self.root.geometry("720x620")
        self.root.resizable(True, True)

        # 变量
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.progress_value = tk.IntVar()
        self.quality = tk.IntVar(value=85)          # 默认85，平衡速度与画质
        self.num_workers = tk.IntVar(value=multiprocessing.cpu_count())

        self.create_widgets()

    def create_widgets(self):
        # 源文件夹
        frame_src = tk.LabelFrame(self.root, text="源文件夹", padx=5, pady=5)
        frame_src.pack(fill="x", padx=10, pady=5)
        tk.Entry(frame_src, textvariable=self.source_dir, width=50).pack(side="left", fill="x", expand=True, padx=(0,5))
        tk.Button(frame_src, text="浏览...", command=self.select_source_dir).pack(side="right")

        # 目标文件夹
        frame_dst = tk.LabelFrame(self.root, text="目标文件夹", padx=5, pady=5)
        frame_dst.pack(fill="x", padx=10, pady=5)
        tk.Entry(frame_dst, textvariable=self.target_dir, width=50).pack(side="left", fill="x", expand=True, padx=(0,5))
        tk.Button(frame_dst, text="浏览...", command=self.select_target_dir).pack(side="right")

        # 提示
        self.info_label = tk.Label(self.root, text="提示：若目标文件夹与源相同，将覆盖原文件，建议选择不同目录。", fg="gray", font=("Arial", 9))
        self.info_label.pack(pady=(0,5))

        # 性能参数设置
        frame_perf = tk.LabelFrame(self.root, text="性能设置", padx=5, pady=5)
        frame_perf.pack(fill="x", padx=10, pady=5)

        # JPEG 质量滑块
        tk.Label(frame_perf, text="JPEG质量 (1-100，越低越快、文件越小)").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        scale = tk.Scale(frame_perf, from_=1, to=100, orient='horizontal', variable=self.quality, length=200)
        scale.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.quality_label = tk.Label(frame_perf, text="85")
        self.quality_label.grid(row=0, column=2, padx=5)
        self.quality.trace_add('write', lambda *a: self.quality_label.config(text=str(self.quality.get())))

        # 并行进程数
        cpu_count = multiprocessing.cpu_count()
        tk.Label(frame_perf, text=f"并行进程数 (1-{cpu_count*2})").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        spinbox = tk.Spinbox(frame_perf, from_=1, to=cpu_count*2, textvariable=self.num_workers, width=5)
        spinbox.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        tk.Label(frame_perf, text=f" (推荐 ≤ {cpu_count})").grid(row=1, column=2, sticky="w", padx=5)

        # 处理按钮
        self.process_btn = tk.Button(self.root, text="开始处理", command=self.start_processing, bg="#4CAF50", fg="white", font=("Arial", 12))
        self.process_btn.pack(pady=10)

        # 进度条
        self.progress_bar = ttk.Progressbar(self.root, orient="horizontal", variable=self.progress_value, maximum=100)
        self.progress_bar.pack(fill="x", padx=10, pady=5)

        # 日志区域
        frame_log = tk.LabelFrame(self.root, text="处理日志", padx=5, pady=5)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_text = tk.Text(frame_log, wrap="word", height=15)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(frame_log, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def select_source_dir(self):
        directory = filedialog.askdirectory(title="选择包含图片的文件夹")
        if directory:
            self.source_dir.set(directory)
            if not self.target_dir.get():
                default_target = os.path.join(directory, "rotated")
                self.target_dir.set(default_target)
                self.log(f"自动设置输出目录为: {default_target}")

    def select_target_dir(self):
        directory = filedialog.askdirectory(title="选择输出文件夹")
        if directory:
            self.target_dir.set(directory)

    def log(self, message):
        """线程安全地添加日志"""
        self.root.after(0, lambda: self._append_log(message))

    def _append_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def start_processing(self):
        source = self.source_dir.get().strip()
        target = self.target_dir.get().strip()

        if not source or not target:
            messagebox.showerror("错误", "请选择源文件夹和目标文件夹")
            return
        if not os.path.exists(source):
            messagebox.showerror("错误", "源文件夹不存在")
            return

        try:
            os.makedirs(target, exist_ok=True)
        except Exception as e:
            messagebox.showerror("错误", f"无法创建目标文件夹: {e}")
            return

        # 若源和目标相同，警告
        if os.path.samefile(source, target):
            answer = messagebox.askyesno("警告", "目标文件夹与源文件夹相同，处理将覆盖原文件！\n是否继续？")
            if not answer:
                return

        # 界面锁定
        self.process_btn.config(state=tk.DISABLED)
        self.progress_value.set(0)
        self.log_text.delete(1.0, tk.END)
        self.log("正在扫描图片文件...")

        # 启动处理线程
        thread = threading.Thread(target=self.process_images, args=(source, target), daemon=True)
        thread.start()

    def process_images(self, source_dir, target_dir):
        """多进程处理核心"""
        # 支持的扩展名
        exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif')
        try:
            all_files = [f for f in os.listdir(source_dir) if f.lower().endswith(exts)]
        except Exception as e:
            self.log(f"读取源文件夹失败: {e}")
            self.root.after(0, self.processing_finished)
            return

        total = len(all_files)
        if total == 0:
            self.log("未找到任何图片文件。")
            self.root.after(0, self.processing_finished)
            return

        self.log(f"找到 {total} 张图片，使用 {self.num_workers.get()} 个进程并行处理...")
        self.root.after(0, lambda: self.progress_bar.config(maximum=total))

        # 构建任务列表
        tasks = []
        for fname in all_files:
            src = os.path.join(source_dir, fname)
            dst = os.path.join(target_dir, fname)
            tasks.append((src, dst))

        processed = 0
        rotated = 0
        skipped = 0
        errors = 0

        # 控制界面更新频率（每1%或最多100次更新）
        update_step = max(1, total // 100)

        with ProcessPoolExecutor(max_workers=self.num_workers.get()) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(process_one_image, src, dst, self.quality.get()): (src, dst)
                for src, dst in tasks
            }
            for future in as_completed(future_to_task):
                processed += 1
                status, fname, info = future.result()
                if status == 'rotated':
                    rotated += 1
                    self.log(f"🔄 旋转: {fname} ({info})")
                elif status == 'skipped':
                    skipped += 1
                    self.log(f"✔️ 跳过: {fname} ({info})")
                else:
                    errors += 1
                    self.log(f"❌ 错误: {fname} - {info}")

                # 更新进度条（降低刷新频率）
                if processed % update_step == 0 or processed == total:
                    self.root.after(0, lambda v=processed: self.progress_value.set(v))

        # 最终统计
        self.log("\n========== 处理完成 ==========")
        self.log(f"总计图片: {total}")
        self.log(f"已旋转 (横向→竖向): {rotated}")
        self.log(f"已跳过 (已是竖向/正方形): {skipped}")
        self.log(f"处理错误: {errors}")
        self.log(f"输出目录: {target_dir}")

        self.root.after(0, self.processing_finished)

    def processing_finished(self):
        self.process_btn.config(state=tk.NORMAL)
        messagebox.showinfo("完成", "批量图片处理已完成！")

# ---------- 启动 ----------
if __name__ == "__main__":
    # 解决 Windows 下多进程无控制台时的潜在问题
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = ImageRotatorApp(root)
    root.mainloop()