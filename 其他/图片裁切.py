import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import threading

class ImageBatchProcessor:
    """批量图片处理：Fit留白 / Crop裁切，支持手动宽高或按比例+单边计算"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量处理工具 (Fit & Crop)")
        self.root.geometry("700x600")
        self.file_paths = []
        self.output_dir = ""
        self.setup_ui()

    def setup_ui(self):
        # 文件选择
        frame1 = ttk.LabelFrame(self.root, text="选择图片", padding=10)
        frame1.pack(fill="x", padx=10, pady=5)
        btn_select = ttk.Button(frame1, text="选择图片文件", command=self.select_files)
        btn_select.pack(side="left", padx=5)
        self.label_file_count = ttk.Label(frame1, text="未选择文件")
        self.label_file_count.pack(side="left", padx=10)

        # 处理模式
        frame_mode = ttk.LabelFrame(self.root, text="处理模式", padding=10)
        frame_mode.pack(fill="x", padx=10, pady=5)
        self.mode_var = tk.StringVar(value="fit")
        ttk.Radiobutton(frame_mode, text="Fit 留白 (完整显示，背景填充)", 
                        variable=self.mode_var, value="fit", command=self.on_mode_change).pack(anchor="w", padx=10)
        ttk.Radiobutton(frame_mode, text="Crop 裁切 (居中裁剪后填满画面)", 
                        variable=self.mode_var, value="crop", command=self.on_mode_change).pack(anchor="w", padx=10)

        # 尺寸设置方式
        frame_size_mode = ttk.LabelFrame(self.root, text="尺寸设定方式", padding=10)
        frame_size_mode.pack(fill="x", padx=10, pady=5)
        self.size_mode_var = tk.StringVar(value="ratio")
        ttk.Radiobutton(frame_size_mode, text="按比例 + 单边自动计算", 
                        variable=self.size_mode_var, value="ratio", command=self.on_size_mode_change).pack(anchor="w", padx=10)
        ttk.Radiobutton(frame_size_mode, text="直接输入宽高", 
                        variable=self.size_mode_var, value="manual", command=self.on_size_mode_change).pack(anchor="w", padx=10)

        # 动态参数区域
        self.param_frame = ttk.Frame(self.root)
        self.param_frame.pack(fill="x", padx=10, pady=5)
        self.init_ratio_params()  # 默认按比例界面

        # 背景色（仅Fit模式下可用）
        self.bg_frame = ttk.Frame(self.root)
        self.bg_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(self.bg_frame, text="背景色:").pack(side="left")
        self.bg_color_var = tk.StringVar(value="white")
        self.combo_bg = ttk.Combobox(self.bg_frame, textvariable=self.bg_color_var,
                                     values=["white", "black", "transparent"], state="readonly", width=12)
        self.combo_bg.pack(side="left", padx=5)
        self.lbl_bg_note = ttk.Label(self.bg_frame, text="(仅Fit模式有效)")
        self.lbl_bg_note.pack(side="left", padx=5)

        # 输出目录
        frame_out = ttk.LabelFrame(self.root, text="输出目录", padding=10)
        frame_out.pack(fill="x", padx=10, pady=5)
        self.entry_output = ttk.Entry(frame_out, width=50)
        self.entry_output.pack(side="left", padx=5, expand=True, fill="x")
        btn_output = ttk.Button(frame_out, text="选择目录", command=self.select_output_dir)
        btn_output.pack(side="left", padx=5)

        # 进度与开始按钮
        frame_bottom = ttk.Frame(self.root)
        frame_bottom.pack(fill="x", padx=10, pady=10)
        self.btn_start = ttk.Button(frame_bottom, text="开始批量处理", command=self.start_processing)
        self.btn_start.pack(side="left", padx=5)
        self.progress = ttk.Progressbar(frame_bottom, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(side="left", padx=10, expand=True, fill="x")
        self.label_status = ttk.Label(self.root, text="就绪")
        self.label_status.pack(pady=5)

    # ---------- 参数界面切换 ----------
    def init_manual_params(self):
        """直接输入宽高的界面"""
        for widget in self.param_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.param_frame, text="宽度:").grid(row=0, column=0, padx=5, pady=5)
        self.entry_width = ttk.Entry(self.param_frame, width=10)
        self.entry_width.grid(row=0, column=1, padx=5)
        self.entry_width.insert(0, "800")
        ttk.Label(self.param_frame, text="高度:").grid(row=0, column=2, padx=5, pady=5)
        self.entry_height = ttk.Entry(self.param_frame, width=10)
        self.entry_height.grid(row=0, column=3, padx=5)
        self.entry_height.insert(0, "600")

    def init_ratio_params(self):
        """按比例+单边计算的界面"""
        for widget in self.param_frame.winfo_children():
            widget.destroy()

        # 比例选择
        ttk.Label(self.param_frame, text="目标比例:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ratio_var = tk.StringVar(value="16:9")
        ratios = ["1:1", "4:3", "16:9", "3:2", "2:3", "自定义"]
        self.combo_ratio = ttk.Combobox(self.param_frame, textvariable=self.ratio_var,
                                        values=ratios, state="readonly", width=8)
        self.combo_ratio.grid(row=0, column=1, padx=5)
        self.combo_ratio.bind("<<ComboboxSelected>>", self.on_ratio_select)

        # 自定义比例输入
        self.custom_frame = ttk.Frame(self.param_frame)
        self.custom_frame.grid(row=0, column=2, padx=5)
        ttk.Label(self.custom_frame, text="宽:").pack(side="left")
        self.entry_cw = ttk.Entry(self.custom_frame, width=4)
        self.entry_cw.pack(side="left")
        ttk.Label(self.custom_frame, text="高:").pack(side="left")
        self.entry_ch = ttk.Entry(self.custom_frame, width=4)
        self.entry_ch.pack(side="left")
        self.custom_frame.grid_remove()  # 默认隐藏

        # 已知边长输入
        ttk.Label(self.param_frame, text="已知宽度(像素):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_given_w = ttk.Entry(self.param_frame, width=10)
        self.entry_given_w.grid(row=1, column=1, padx=5)
        ttk.Label(self.param_frame, text="已知高度(像素):").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.entry_given_h = ttk.Entry(self.param_frame, width=10)
        self.entry_given_h.grid(row=1, column=3, padx=5)
        ttk.Label(self.param_frame, text="(填其一，另一个留空)").grid(row=1, column=4, padx=5)

    def on_ratio_select(self, event=None):
        if self.ratio_var.get() == "自定义":
            self.custom_frame.grid()
        else:
            self.custom_frame.grid_remove()

    def on_size_mode_change(self):
        if self.size_mode_var.get() == "manual":
            self.init_manual_params()
        else:
            self.init_ratio_params()

    def on_mode_change(self):
        """切换Fit/Crop时，调整背景色区域的可用性"""
        if self.mode_var.get() == "crop":
            self.combo_bg.config(state="disabled")
            self.lbl_bg_note.config(text="(Crop模式忽略背景)")
        else:
            self.combo_bg.config(state="readonly")
            self.lbl_bg_note.config(text="(仅Fit模式有效)")

    # ---------- 文件选择 ----------
    def select_files(self):
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"), ("所有文件", "*.*")]
        )
        if files:
            self.file_paths = list(files)
            self.label_file_count.config(text=f"已选择 {len(self.file_paths)} 个文件")

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出文件夹")
        if directory:
            self.output_dir = directory
            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, directory)

    # ---------- 处理逻辑 ----------
    def start_processing(self):
        if not self.file_paths:
            messagebox.showwarning("警告", "请先选择图片文件")
            return
        if not self.output_dir:
            messagebox.showwarning("警告", "请先选择输出目录")
            return

        # 获取目标尺寸
        try:
            if self.size_mode_var.get() == "manual":
                w = int(self.entry_width.get())
                h = int(self.entry_height.get())
                if w <= 0 or h <= 0:
                    raise ValueError("宽高必须为正整数")
                target_w, target_h = w, h
            else:
                # 解析比例
                ratio_str = self.ratio_var.get()
                if ratio_str == "自定义":
                    rw = int(self.entry_cw.get())
                    rh = int(self.entry_ch.get())
                else:
                    rw, rh = map(int, ratio_str.split(":"))
                ratio = rw / rh

                given_w = self.entry_given_w.get().strip()
                given_h = self.entry_given_h.get().strip()
                if given_w and given_h:
                    raise ValueError("请只填写宽度或高度中的一个")
                if not given_w and not given_h:
                    raise ValueError("请填写宽度或高度")
                if given_w:
                    target_w = int(given_w)
                    target_h = round(target_w / ratio)
                else:
                    target_h = int(given_h)
                    target_w = round(target_h * ratio)
                if target_w <= 0 or target_h <= 0:
                    raise ValueError("计算出的尺寸无效")
        except ValueError as e:
            messagebox.showerror("错误", f"输入有误：{e}")
            return

        mode = self.mode_var.get()
        bg_color = self.bg_color_var.get() if mode == "fit" else None

        self.btn_start.config(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.file_paths)
        self.label_status.config(text="处理中...")
        threading.Thread(target=self.process_images,
                         args=(mode, target_w, target_h, bg_color), daemon=True).start()

    def process_images(self, mode, target_w, target_h, bg_color):
        for i, file_path in enumerate(self.file_paths):
            try:
                # 打开图像（保留透明通道，统一用RGBA处理）
                img = Image.open(file_path).convert("RGBA")
                orig_w, orig_h = img.size
                if orig_w == 0 or orig_h == 0:
                    continue

                if mode == "fit":
                    # Fit模式：等比例缩放后居中放置，背景填充
                    scale = min(target_w / orig_w, target_h / orig_h)
                    new_w = int(orig_w * scale)
                    new_h = int(orig_h * scale)
                    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    if bg_color == "transparent":
                        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
                        canvas.paste(img_resized, ((target_w - new_w)//2, (target_h - new_h)//2), img_resized)
                    else:
                        # 转换为RGB以使用颜色背景
                        canvas = Image.new("RGB", (target_w, target_h), bg_color)
                        # 若原图有透明，需合成到白色上（这里为简单，直接粘贴，透明部分会显示背景色）
                        canvas.paste(img_resized.convert("RGB") if img.mode == "RGBA" else img_resized,
                                     ((target_w - new_w)//2, (target_h - new_h)//2))
                    final_img = canvas

                else:  # crop 模式
                    target_ratio = target_w / target_h
                    orig_ratio = orig_w / orig_h
                    if orig_ratio > target_ratio:
                        # 原图更宽，裁掉左右
                        new_w = int(orig_h * target_ratio)
                        new_h = orig_h
                        left = (orig_w - new_w) // 2
                        top = 0
                    else:
                        # 原图更高，裁掉上下
                        new_w = orig_w
                        new_h = int(orig_w / target_ratio)
                        left = 0
                        top = (orig_h - new_h) // 2
                    img_cropped = img.crop((left, top, left + new_w, top + new_h))
                    # 缩放到目标尺寸（正好填满）
                    final_img = img_cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

                # 保存文件
                base_name = os.path.basename(file_path)
                name, ext = os.path.splitext(base_name)
                # 输出格式：Fit透明或Crop时使用PNG（保留透明），否则默认用原扩展名，但为统一用PNG
                save_ext = ".png"  # 统一使用PNG确保质量及透明支持
                out_path = os.path.join(self.output_dir, f"{name}_{mode}{save_ext}")
                counter = 1
                while os.path.exists(out_path):
                    out_path = os.path.join(self.output_dir, f"{name}_{mode}_{counter}{save_ext}")
                    counter += 1
                final_img.save(out_path)

                self.root.after(0, self.update_progress, i + 1)
            except Exception as e:
                print(f"处理失败：{file_path}，错误：{e}")

        self.root.after(0, self.processing_done)

    def update_progress(self, value):
        self.progress["value"] = value
        self.label_status.config(text=f"处理中 {value}/{self.progress['maximum']}")

    def processing_done(self):
        self.btn_start.config(state="normal")
        self.label_status.config(text="处理完成")
        messagebox.showinfo("完成", "批量处理完成！")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBatchProcessor(root)
    root.mainloop()