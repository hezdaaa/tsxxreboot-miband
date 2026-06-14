import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import threading

class ImageBatchProcessor:
    """图片批量处理工具 - 缩放裁剪（504×720） + 专业6色压缩"""

    def __init__(self, root):
        self.root = root
        self.root.title("图片批量处理工具 - 缩放裁剪 & 6色压缩")
        self.root.geometry("750x680")
        self.root.resizable(True, True)

        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.processing = False

        # 目标尺寸：宽504px，高720px（比例 7:10）
        self.target_width = 504
        self.target_height = 720

        self.setup_ui()

    def setup_ui(self):
        """构建图形界面"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)

        title_label = ttk.Label(main_frame, text="图片批量处理工具", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 15))

        info_frame = ttk.LabelFrame(main_frame, text="处理参数", padding="10")
        info_frame.pack(fill="x", pady=(0, 15))

        params_text = (
            f"• 目标尺寸：{self.target_width} × {self.target_height} px (宽高比 7:10)\n"
            "• 缩放裁剪：保持比例覆盖 + 居中裁剪（不拉伸、不模糊）\n"
            "• 压缩参数：6 色调色板 + 5% 抖动强度\n"
            "• 压缩引擎：imagequant（若不可用则回退 Pillow）\n"
            "• 支持格式：PNG、JPG、BMP、GIF 等"
        )

        ttk.Label(info_frame, text=params_text, justify="left").pack(anchor="w")

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(input_frame, text="输入文件夹：", width=12).pack(side="left")
        ttk.Entry(input_frame, textvariable=self.input_folder).pack(
            side="left", fill="x", expand=True, padx=(5, 5)
        )
        ttk.Button(input_frame, text="浏览", command=self.browse_input).pack(side="right")

        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(output_frame, text="输出文件夹：", width=12).pack(side="left")
        ttk.Entry(output_frame, textvariable=self.output_folder).pack(
            side="left", fill="x", expand=True, padx=(5, 5)
        )
        ttk.Button(output_frame, text="浏览", command=self.browse_output).pack(side="right")

        func_frame = ttk.LabelFrame(main_frame, text="选择功能", padding="10")
        func_frame.pack(fill="x", pady=(0, 15))
        self.resize_var = tk.BooleanVar(value=True)
        self.compress_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(func_frame, text="缩放裁剪（输出 504×720）", variable=self.resize_var).pack(anchor="w", pady=2)
        ttk.Checkbutton(func_frame, text="一键压缩（6色 + 5%抖动）", variable=self.compress_var).pack(anchor="w", pady=2)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        self.process_btn = ttk.Button(btn_frame, text="开始处理", command=self.start_processing)
        self.process_btn.pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame, text="打开输出文件夹", command=self.open_output_folder).pack(side="left")

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(5, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", side="left", expand=True)
        self.progress_label = ttk.Label(progress_frame, text="0/0", width=8)
        self.progress_label.pack(side="right", padx=(5, 0))

        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="5")
        log_frame.pack(fill="both", expand=True)
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(text_frame, height=10, wrap="word", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        ttk.Button(log_frame, text="清空日志", command=self.clear_log).pack(anchor="e", pady=(5, 0))

    def browse_input(self):
        folder = filedialog.askdirectory(title="选择图片所在的输入文件夹")
        if folder:
            self.input_folder.set(folder)
            self.log(f"已选择输入文件夹：{folder}")

    def browse_output(self):
        folder = filedialog.askdirectory(title="选择处理后图片的输出文件夹")
        if folder:
            self.output_folder.set(folder)
            self.log(f"已选择输出文件夹：{folder}")

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def open_output_folder(self):
        out = self.output_folder.get()
        if out and os.path.exists(out):
            os.startfile(out) if os.name == 'nt' else os.system(f'open "{out}"')
        else:
            messagebox.showwarning("提示", "输出文件夹不存在或未选择")

    def start_processing(self):
        if self.processing:
            messagebox.showinfo("提示", "正在处理中，请稍候...")
            return

        in_folder = self.input_folder.get()
        out_folder = self.output_folder.get()
        if not in_folder or not out_folder:
            messagebox.showerror("错误", "请先选择输入和输出文件夹")
            return
        if not os.path.exists(in_folder):
            messagebox.showerror("错误", "输入文件夹不存在")
            return
        if not self.resize_var.get() and not self.compress_var.get():
            messagebox.showerror("错误", "请至少选择一项处理功能")
            return

        os.makedirs(out_folder, exist_ok=True)
        self.processing = True
        self.process_btn.configure(state="disabled")
        threading.Thread(target=self.process_images, daemon=True).start()

    def process_images(self):
        in_folder = self.input_folder.get()
        out_folder = self.output_folder.get()
        do_resize = self.resize_var.get()
        do_compress = self.compress_var.get()

        extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.webp')
        image_files = [f for f in os.listdir(in_folder) if f.lower().endswith(extensions)]
        total = len(image_files)
        if total == 0:
            self.log("未找到任何图片文件")
            self.finish_processing()
            return

        self.log(f"\n开始处理，共找到 {total} 张图片...")
        self.log("=" * 50)
        self.progress_bar["maximum"] = total
        success_count = 0

        for i, filename in enumerate(image_files):
            src_path = os.path.join(in_folder, filename)
            base_name = os.path.splitext(filename)[0]
            dst_path = os.path.join(out_folder, base_name + ".png")

            try:
                self.log(f"[{i+1}/{total}] 处理：{filename}")
                with Image.open(src_path) as img:
                    # 统一转为 RGB
                    if img.mode in ('RGBA', 'LA', 'P'):
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = rgb_img
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')

                    if do_resize:
                        img = self.resize_and_crop(img)
                    if do_compress:
                        img = self.compress_to_6_colors(img)

                    img.save(dst_path, 'PNG', optimize=True)
                    size_kb = os.path.getsize(dst_path) / 1024
                    self.log(f"  ✓ 已保存：{dst_path} ({size_kb:.1f} KB)")
                    success_count += 1

            except Exception as e:
                self.log(f"  ✗ 处理失败：{e}")

            self.progress_bar["value"] = i + 1
            self.progress_label["text"] = f"{i+1}/{total}"
            self.root.update_idletasks()

        self.log("=" * 50)
        self.log(f"处理完成！成功：{success_count}/{total}")
        self.finish_processing()

    def resize_and_crop(self, img):
        """
        保持原图比例，缩放到完全覆盖目标尺寸（504×720），然后居中裁剪。
        使用高质量 LANCZOS 重采样，尽量减少信息丢失。
        """
        orig_w, orig_h = img.size
        target_w, target_h = self.target_width, self.target_height

        # 计算缩放比例（取较大的比例，确保覆盖目标区域）
        ratio = max(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)

        # 高质量缩放
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 居中裁剪
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img_cropped = img_resized.crop((left, top, left + target_w, top + target_h))

        return img_cropped

    def compress_to_6_colors(self, img):
        """使用 imagequant 进行 6 色压缩 + 5% 抖动，若不可用则回退 Pillow"""
        dither_strength = 0.05

        # 尝试使用 imagequant
        try:
            import imagequant
            self.log("    (使用 imagequant 压缩)")
            # 移除质量限制，只指定颜色数和抖动，让库自动平衡
            return imagequant.quantize_pil_image(
                img,
                dithering_level=dither_strength,
                max_colors=6
                # 不设置 min_quality 和 max_quality，避免 "Quality too low" 错误
            )
        except ImportError:
            self.log("    ⚠ 未安装 imagequant，回退到 Pillow 原生压缩")
        except Exception as e:
            self.log(f"    imagequant 执行失败: {e}，回退到 Pillow")

        # 回退方案：Pillow 原生量化
        img_quantized = img.quantize(
            colors=6,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.FLOYDSTEINBERG
        )
        return img_quantized.convert('RGB')

    def finish_processing(self):
        self.processing = False
        self.process_btn.configure(state="normal")
        self.progress_bar["value"] = 0
        self.progress_label["text"] = "0/0"
        messagebox.showinfo("完成", "图片处理完成！")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageBatchProcessor(root)
    root.mainloop()