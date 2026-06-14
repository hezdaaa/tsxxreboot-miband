#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多功能图片处理工具
功能：超清放大、格式转换、压缩、裁切、扩图（增加无色背景）
依赖库自动安装：Pillow, opencv-python
"""

import subprocess
import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# ---------- 自动安装缺失库（带异常处理）----------
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except Exception as e:
        print(f"安装 {package} 失败: {e}")
        sys.exit(1)

try:
    from PIL import Image, ImageEnhance, ImageTk
except ImportError:
    print("正在安装 Pillow ...")
    install_package("Pillow")
    from PIL import Image, ImageEnhance, ImageTk

try:
    import cv2
except ImportError:
    print("正在安装 opencv-python ...")
    install_package("opencv-python")
    import cv2

import numpy as np

# ---------- 图片处理功能 ----------
class ImageProcessor:
    @staticmethod
    def super_resolution(image, scale=2, sharpness=1.5):
        if scale < 1:
            scale = 1
        new_size = (int(image.width * scale), int(image.height * scale))
        enlarged = image.resize(new_size, Image.Resampling.LANCZOS)
        enhancer = ImageEnhance.Sharpness(enlarged)
        sharpened = enhancer.enhance(sharpness)
        return sharpened

    @staticmethod
    def convert_format(image, output_format, quality=95):
        if output_format.upper() == 'JPEG' and image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        return image

    @staticmethod
    def compress_image(image, quality=75):
        return image

    @staticmethod
    def crop_image(image, x, y, w, h):
        box = (x, y, x + w, y + h)
        return image.crop(box)

    @staticmethod
    def expand_canvas(image, new_width, new_height, bg_color=(255,255,255,0), position='center'):
        if len(bg_color) == 3:
            bg_color = bg_color + (255,)
        new_im = Image.new('RGBA', (new_width, new_height), bg_color)
        if position == 'center':
            paste_x = (new_width - image.width) // 2
            paste_y = (new_height - image.height) // 2
        elif position == 'top-left':
            paste_x, paste_y = 0, 0
        elif position == 'top-right':
            paste_x = new_width - image.width
            paste_y = 0
        elif position == 'bottom-left':
            paste_x = 0
            paste_y = new_height - image.height
        elif position == 'bottom-right':
            paste_x = new_width - image.width
            paste_y = new_height - image.height
        else:
            paste_x, paste_y = 0, 0
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        new_im.paste(image, (paste_x, paste_y), image)
        return new_im

# ---------- GUI 应用 ----------
class ImageToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多功能图片处理工具")
        self.root.geometry("720x600")
        self.root.resizable(True, True)

        self.current_image = None
        self.current_image_path = None

        self.create_widgets()

    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="打开图片", command=self.open_image).pack(side=tk.LEFT, padx=5)
        self.info_label = ttk.Label(top_frame, text="未打开图片")
        self.info_label.pack(side=tk.LEFT, padx=10)

        # 将 notebook 保存为实例变量
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 功能1：超清
        self.page_sr = ttk.Frame(self.notebook)
        self.notebook.add(self.page_sr, text="超清放大")
        self.setup_sr_page()

        # 功能2：格式转换
        self.page_convert = ttk.Frame(self.notebook)
        self.notebook.add(self.page_convert, text="格式转换")
        self.setup_convert_page()

        # 功能3：压缩
        self.page_compress = ttk.Frame(self.notebook)
        self.notebook.add(self.page_compress, text="压缩")
        self.setup_compress_page()

        # 功能4：裁切
        self.page_crop = ttk.Frame(self.notebook)
        self.notebook.add(self.page_crop, text="裁切")
        self.setup_crop_page()

        # 功能5：扩图
        self.page_expand = ttk.Frame(self.notebook)
        self.notebook.add(self.page_expand, text="扩图（扩大背景）")
        self.setup_expand_page()

        bottom_frame = ttk.Frame(self.root, padding=5)
        bottom_frame.pack(fill=tk.X)

        self.save_btn = ttk.Button(bottom_frame, text="保存处理结果", command=self.save_image, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT, padx=5)

        self.log_text = ScrolledText(self.root, height=8, state=tk.NORMAL)
        self.log_text.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def open_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        try:
            self.current_image = Image.open(file_path)
            self.current_image_path = file_path
            info = f"已打开: {os.path.basename(file_path)}  |  尺寸: {self.current_image.width}x{self.current_image.height}  |  模式: {self.current_image.mode}"
            self.info_label.config(text=info)
            self.log(f"成功加载图片: {file_path}")
            self.save_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开图片:\n{str(e)}")
            self.log(f"打开失败: {str(e)}")

    def save_image(self):
        if self.current_image is None:
            messagebox.showwarning("警告", "请先打开图片")
            return

        # 直接使用 self.notebook 获取当前选中的标签页索引
        current_tab = self.notebook.index(self.notebook.select())
        processed = None
        try:
            if current_tab == 0:      # 超清
                scale = int(self.scale_var.get())
                sharp = float(self.sharp_var.get())
                processed = ImageProcessor.super_resolution(self.current_image, scale, sharp)
                self.log(f"执行超清放大: 倍数={scale}, 锐化={sharp}")
            elif current_tab == 1:    # 格式转换
                fmt = self.format_var.get()
                processed = ImageProcessor.convert_format(self.current_image, fmt)
                self.log(f"格式转换: 目标格式 {fmt}")
            elif current_tab == 2:    # 压缩
                quality = int(self.quality_var.get())
                processed = ImageProcessor.compress_image(self.current_image, quality)
                self.log(f"压缩质量: {quality}")
            elif current_tab == 3:    # 裁切
                x = int(self.crop_x_var.get())
                y = int(self.crop_y_var.get())
                w = int(self.crop_w_var.get())
                h = int(self.crop_h_var.get())
                if w <= 0 or h <= 0:
                    raise ValueError("裁切宽高必须大于0")
                processed = ImageProcessor.crop_image(self.current_image, x, y, w, h)
                self.log(f"裁切区域: ({x},{y}) 宽{w} 高{h}")
            elif current_tab == 4:    # 扩图
                nw = int(self.expand_w_var.get())
                nh = int(self.expand_h_var.get())
                if nw < self.current_image.width or nh < self.current_image.height:
                    if not messagebox.askyesno("确认", "新画布尺寸小于原图，可能被裁剪。是否继续？"):
                        return
                bg_r = int(self.bg_r_var.get())
                bg_g = int(self.bg_g_var.get())
                bg_b = int(self.bg_b_var.get())
                bg_a = int(self.bg_a_var.get())
                bg_color = (bg_r, bg_g, bg_b, bg_a)
                pos = self.position_var.get()
                processed = ImageProcessor.expand_canvas(self.current_image, nw, nh, bg_color, pos)
                self.log(f"扩图: 新尺寸 {nw}x{nh}, 背景RGBA({bg_r},{bg_g},{bg_b},{bg_a}), 位置={pos}")
            else:
                return

            save_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG图片", "*.png"), ("JPEG图片", "*.jpg"), ("所有文件", "*.*")]
            )
            if save_path:
                ext = os.path.splitext(save_path)[1].lower()
                save_kwargs = {}
                if ext in ['.jpg', '.jpeg']:
                    format = 'JPEG'
                    # 如果当前是压缩页面，使用压缩质量，否则默认95
                    if current_tab == 2:
                        save_kwargs['quality'] = int(self.quality_var.get())
                    else:
                        save_kwargs['quality'] = 95
                elif ext == '.png':
                    format = 'PNG'
                    save_kwargs['compress_level'] = 6
                elif ext == '.bmp':
                    format = 'BMP'
                else:
                    format = 'PNG'
                if format == 'JPEG' and processed.mode in ('RGBA', 'P'):
                    processed = processed.convert('RGB')
                processed.save(save_path, format=format, **save_kwargs)
                self.log(f"已保存至: {save_path}")
                messagebox.showinfo("成功", "图片处理并保存完成！")
        except Exception as e:
            messagebox.showerror("错误", f"处理失败:\n{str(e)}")
            self.log(f"错误: {str(e)}")

    # ---------- 各功能界面 ----------
    def setup_sr_page(self):
        frame = ttk.Frame(self.page_sr, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="放大倍数（整数）:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.scale_var = tk.StringVar(value="2")
        ttk.Spinbox(frame, from_=1, to=8, textvariable=self.scale_var, width=10).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(frame, text="锐化强度 (1.0 不变, >1增强):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sharp_var = tk.StringVar(value="1.5")
        ttk.Spinbox(frame, from_=0.5, to=3.0, increment=0.1, textvariable=self.sharp_var, width=10).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(frame, text="说明：基于高质量插值放大 + 锐化，模拟超清效果。").grid(row=2, column=0, columnspan=2, pady=20)

    def setup_convert_page(self):
        frame = ttk.Frame(self.page_convert, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="选择输出格式:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="PNG")
        formats = ["PNG", "JPEG", "BMP", "TIFF", "WEBP"]
        ttk.Combobox(frame, textvariable=self.format_var, values=formats, state="readonly", width=10).grid(row=0, column=1, sticky=tk.W)
        ttk.Label(frame, text="注意：JPEG 不支持透明背景。").grid(row=1, column=0, columnspan=2, pady=10)

    def setup_compress_page(self):
        frame = ttk.Frame(self.page_compress, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="压缩质量 (1~100, 数值越小文件越小):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.StringVar(value="75")
        quality_scale = ttk.Scale(frame, from_=1, to=100, orient=tk.HORIZONTAL, variable=self.quality_var, length=300)
        quality_scale.grid(row=0, column=1, padx=10)
        ttk.Label(frame, textvariable=self.quality_var).grid(row=0, column=2)
        ttk.Label(frame, text="说明：主要针对 JPEG 格式有效，保存时自动应用。").grid(row=1, column=0, columnspan=3, pady=10)

    def setup_crop_page(self):
        frame = ttk.Frame(self.page_crop, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="左上角 X:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.crop_x_var = tk.StringVar(value="0")
        ttk.Entry(frame, textvariable=self.crop_x_var, width=10).grid(row=0, column=1)
        ttk.Label(frame, text="Y:").grid(row=0, column=2, sticky=tk.W)
        self.crop_y_var = tk.StringVar(value="0")
        ttk.Entry(frame, textvariable=self.crop_y_var, width=10).grid(row=0, column=3)

        ttk.Label(frame, text="裁切宽度:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.crop_w_var = tk.StringVar(value="100")
        ttk.Entry(frame, textvariable=self.crop_w_var, width=10).grid(row=1, column=1)
        ttk.Label(frame, text="高度:").grid(row=1, column=2, sticky=tk.W)
        self.crop_h_var = tk.StringVar(value="100")
        ttk.Entry(frame, textvariable=self.crop_h_var, width=10).grid(row=1, column=3)

        ttk.Label(frame, text="提示：请确保坐标和尺寸在图片范围内。").grid(row=2, column=0, columnspan=4, pady=10)

    def setup_expand_page(self):
        frame = ttk.Frame(self.page_expand, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="新画布宽度:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.expand_w_var = tk.StringVar(value="800")
        ttk.Entry(frame, textvariable=self.expand_w_var, width=10).grid(row=0, column=1)
        ttk.Label(frame, text="高度:").grid(row=0, column=2, sticky=tk.W)
        self.expand_h_var = tk.StringVar(value="600")
        ttk.Entry(frame, textvariable=self.expand_h_var, width=10).grid(row=0, column=3)

        ttk.Label(frame, text="背景色 (RGBA):").grid(row=1, column=0, sticky=tk.W, pady=2)
        bg_frame = ttk.Frame(frame)
        bg_frame.grid(row=1, column=1, columnspan=3, sticky=tk.W)
        self.bg_r_var = tk.StringVar(value="255")
        self.bg_g_var = tk.StringVar(value="255")
        self.bg_b_var = tk.StringVar(value="255")
        self.bg_a_var = tk.StringVar(value="0")
        ttk.Label(bg_frame, text="R:").pack(side=tk.LEFT)
        ttk.Entry(bg_frame, textvariable=self.bg_r_var, width=4).pack(side=tk.LEFT)
        ttk.Label(bg_frame, text="G:").pack(side=tk.LEFT)
        ttk.Entry(bg_frame, textvariable=self.bg_g_var, width=4).pack(side=tk.LEFT)
        ttk.Label(bg_frame, text="B:").pack(side=tk.LEFT)
        ttk.Entry(bg_frame, textvariable=self.bg_b_var, width=4).pack(side=tk.LEFT)
        ttk.Label(bg_frame, text="A(0透明):").pack(side=tk.LEFT)
        ttk.Entry(bg_frame, textvariable=self.bg_a_var, width=4).pack(side=tk.LEFT)

        ttk.Label(frame, text="原图放置位置:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.position_var = tk.StringVar(value="center")
        pos_combo = ttk.Combobox(frame, textvariable=self.position_var, values=["center", "top-left", "top-right", "bottom-left", "bottom-right"], state="readonly")
        pos_combo.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(frame, text="说明：扩图不改变原图分辨率，只增加周围空白/透明区域。").grid(row=3, column=0, columnspan=4, pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToolApp(root)
    root.mainloop()