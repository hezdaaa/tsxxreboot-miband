import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import threading


class ImageBatchProcessor:
    """图片批量处理工具 - 可选PNG量化或JPG压缩，无尺寸裁切"""

    def __init__(self, root):
        self.root = root
        self.root.title("图片批量处理工具 - PNG/JPG 压缩")
        self.root.geometry("750x680")
        self.root.resizable(True, True)

        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.processing = False

        # 输出格式相关变量
        self.output_format = tk.StringVar(value="PNG")
        self.png_colors = tk.IntVar(value=6)
        self.png_dither = tk.DoubleVar(value=0.05)
        self.jpg_quality = tk.IntVar(value=85)

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
            "• 输入格式：PNG、JPG、BMP、GIF 等常见图片\n"
            "• 处理步骤：\n"
            "  1. 统一转为 RGB 色彩模式\n"
            "  2. 根据所选输出格式进行压缩：\n"
            "     - PNG：量化到指定颜色数 + 可调抖动强度（保留透明背景）\n"
            "     - JPG：设置固定压缩质量\n"
            "• 压缩引擎：优先使用 imagequant（PNG），否则回退 Pillow"
        )
        ttk.Label(info_frame, text=params_text, justify="left").pack(anchor="w")

        # 文件夹选择
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

        # 输出设置区域
        output_settings = ttk.LabelFrame(main_frame, text="输出设置", padding="10")
        output_settings.pack(fill="x", pady=(0, 15))

        # 格式选择
        format_frame = ttk.Frame(output_settings)
        format_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(format_frame, text="输出格式：").pack(side="left")
        ttk.Radiobutton(format_frame, text="PNG", variable=self.output_format,
                        value="PNG", command=self.on_format_change).pack(side="left", padx=5)
        ttk.Radiobutton(format_frame, text="JPEG", variable=self.output_format,
                        value="JPEG", command=self.on_format_change).pack(side="left", padx=5)

        # PNG 参数帧
        self.png_frame = ttk.Frame(output_settings)
        ttk.Label(self.png_frame, text="颜色数 (1~256):").pack(side="left", padx=(0, 5))
        self.png_colors_spin = ttk.Spinbox(self.png_frame, from_=1, to=256,
                                           textvariable=self.png_colors, width=6)
        self.png_colors_spin.pack(side="left", padx=(0, 15))
        ttk.Label(self.png_frame, text="抖动强度 (0~1):").pack(side="left", padx=(0, 5))
        self.png_dither_spin = ttk.Spinbox(self.png_frame, from_=0.0, to=1.0,
                                           increment=0.01, textvariable=self.png_dither, width=6)
        self.png_dither_spin.pack(side="left")
        self.png_frame.pack(fill="x", pady=5)

        # JPG 参数帧
        self.jpg_frame = ttk.Frame(output_settings)
        ttk.Label(self.jpg_frame, text="JPEG 质量 (1~100):").pack(side="left", padx=(0, 5))
        self.jpg_quality_spin = ttk.Spinbox(self.jpg_frame, from_=1, to=100,
                                            textvariable=self.jpg_quality, width=6)
        self.jpg_quality_spin.pack(side="left")
        # 初始隐藏 JPG 参数
        self.jpg_frame.pack_forget()

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        self.process_btn = ttk.Button(btn_frame, text="开始处理", command=self.start_processing)
        self.process_btn.pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame, text="打开输出文件夹", command=self.open_output_folder).pack(side="left")

        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(5, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", side="left", expand=True)
        self.progress_label = ttk.Label(progress_frame, text="0/0", width=8)
        self.progress_label.pack(side="right", padx=(5, 0))

        # 日志区域
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

    def on_format_change(self):
        """切换输出格式时显示/隐藏对应参数面板"""
        if self.output_format.get() == "PNG":
            self.jpg_frame.pack_forget()
            self.png_frame.pack(fill="x", pady=5)
        else:
            self.png_frame.pack_forget()
            self.jpg_frame.pack(fill="x", pady=5)

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
            if os.name == 'nt':
                os.startfile(out)
            else:
                os.system(f'open "{out}"')
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

        os.makedirs(out_folder, exist_ok=True)
        self.processing = True
        self.process_btn.configure(state="disabled")
        threading.Thread(target=self.process_images, daemon=True).start()

    def process_images(self):
        in_folder = self.input_folder.get()
        out_folder = self.output_folder.get()
        fmt = self.output_format.get()        # "PNG" 或 "JPEG"
        extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.webp')
        image_files = [f for f in os.listdir(in_folder) if f.lower().endswith(extensions)]
        total = len(image_files)
        if total == 0:
            self.log("未找到任何图片文件")
            self.finish_processing()
            return

        self.log(f"\n开始处理，共找到 {total} 张图片，输出格式：{fmt}")
        self.log("=" * 50)
        self.progress_bar["maximum"] = total
        success_count = 0

        for i, filename in enumerate(image_files):
            src_path = os.path.join(in_folder, filename)
            base_name = os.path.splitext(filename)[0]
            if fmt == "PNG":
                dst_path = os.path.join(out_folder, base_name + ".png")
            else:
                dst_path = os.path.join(out_folder, base_name + ".jpg")

            try:
                self.log(f"[{i+1}/{total}] 处理：{filename}")
                with Image.open(src_path) as img:
                    # ---- JPEG 输出：强制转为 RGB，透明区域填白 ----
                    if fmt == "JPEG":
                        # 处理透明 / 调色板模式
                        if img.mode in ('RGBA', 'LA', 'P'):
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            bg = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'RGBA':
                                bg.paste(img, mask=img.split()[-1])
                            elif img.mode == 'LA':
                                bg.paste(img, mask=img.split()[-1])
                            else:
                                bg.paste(img)
                            img = bg
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')

                        quality = self.jpg_quality.get()
                        img.save(dst_path, 'JPEG', quality=quality, optimize=True)

                    # ---- PNG 输出：保留透明背景 ----
                    else:
                        # 根据原图模式，统一为适合量化的模式
                        if img.mode == 'RGBA':
                            pass  # 直接使用
                        elif img.mode == 'LA':
                            img = img.convert('RGBA')
                        elif img.mode == 'P':
                            # 调色板模式：若有透明色，则恢复为 RGBA；否则转为普通 RGB
                            if img.info.get('transparency') is not None:
                                img = img.convert('RGBA')
                            else:
                                img = img.convert('RGB')
                        elif img.mode != 'RGB':
                            # 其他无透明模式（L、CMYK 等）统一转为 RGB
                            img = img.convert('RGB')

                        colors = self.png_colors.get()
                        dither = self.png_dither.get()

                        compressed = self.compress_for_png(img, colors, dither)
                        compressed.save(dst_path, 'PNG', optimize=True)

                    size_kb = os.path.getsize(dst_path) / 1024
                    self.log(f"  ✓ 已保存：{os.path.basename(dst_path)} ({size_kb:.1f} KB)")
                    success_count += 1

            except Exception as e:
                self.log(f"  ✗ 处理失败：{e}")

            self.progress_bar["value"] = i + 1
            self.progress_label["text"] = f"{i+1}/{total}"
            self.root.update_idletasks()

        self.log("=" * 50)
        self.log(f"处理完成！成功：{success_count}/{total}")
        self.finish_processing()

    def compress_for_png(self, img, max_colors, dither_level):
        """
        将图像量化到指定颜色数，保留透明背景。
        优先使用 imagequant（支持 RGBA 量化），
        否则回退到 Pillow 的调色板转换（自动处理透明索引）。
        """
        try:
            import imagequant
            self.log("    (使用 imagequant 压缩)")
            # imagequant 可直接处理 RGBA/RGB，返回的 P 模式图像会保留透明色索引
            return imagequant.quantize_pil_image(
                img,
                dithering_level=dither_level,
                max_colors=max_colors
            )
        except ImportError:
            self.log("    ⚠ 未安装 imagequant，回退到 Pillow 原生压缩")
        except Exception as e:
            self.log(f"    imagequant 执行失败: {e}，回退到 Pillow")

        # 回退方案：利用 Pillow 的 convert('P')，它会为 RGBA 图像自动设置透明索引
        dither = Image.Dither.FLOYDSTEINBERG if dither_level > 0 else Image.Dither.NONE
        return img.convert('P', palette=Image.ADAPTIVE, colors=max_colors, dither=dither)

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