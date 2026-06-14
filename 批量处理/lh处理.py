import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image


class ImageProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG图片批量处理器 - 统一缩放版")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        # 变量
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.scale_ratio = tk.DoubleVar(value=1.0)
        self.avg_ratio = 1.0          # 存储计算出的平均比例
        self.image_data = []           # 存储每张图片的(原路径, 去除边框后的宽, 高, 文件名)

        # 界面布局
        self.create_widgets()

    def create_widgets(self):
        # 输入文件夹选择
        frame_in = tk.Frame(self.root, padx=10, pady=5)
        frame_in.pack(fill=tk.X)
        tk.Label(frame_in, text="输入文件夹:").pack(side=tk.LEFT)
        tk.Entry(frame_in, textvariable=self.input_folder, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_in, text="浏览", command=self.browse_input).pack(side=tk.LEFT)

        # 输出文件夹选择
        frame_out = tk.Frame(self.root, padx=10, pady=5)
        frame_out.pack(fill=tk.X)
        tk.Label(frame_out, text="输出文件夹:").pack(side=tk.LEFT)
        tk.Entry(frame_out, textvariable=self.output_folder, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_out, text="浏览", command=self.browse_output).pack(side=tk.LEFT)

        # 分析按钮
        self.analyze_btn = tk.Button(self.root, text="1. 分析图片并计算平均缩放比例", command=self.analyze_images,
                                     width=30, height=1)
        self.analyze_btn.pack(pady=10)

        # 比例调整区域（初始禁用）
        frame_ratio = tk.Frame(self.root, padx=10, pady=5)
        frame_ratio.pack(fill=tk.X)
        tk.Label(frame_ratio, text="2. 最终缩放比例:").pack(side=tk.LEFT)
        self.scale_slider = tk.Scale(frame_ratio, from_=0.1, to=1.0, resolution=0.01,
                                     orient=tk.HORIZONTAL, length=300, variable=self.scale_ratio,
                                     state=tk.DISABLED, command=self.on_scale_changed)
        self.scale_slider.pack(side=tk.LEFT, padx=5)
        self.ratio_label = tk.Label(frame_ratio, text="(平均比例: --)")
        self.ratio_label.pack(side=tk.LEFT, padx=10)

        # 平均缩放后尺寸预览
        self.size_preview_label = tk.Label(self.root, text="平均缩放后宽高: -- x --", fg="blue")
        self.size_preview_label.pack(pady=5)

        # 处理按钮（初始禁用）
        self.process_btn = tk.Button(self.root, text="3. 开始统一缩放并保存", command=self.process_images,
                                     width=30, height=2, state=tk.DISABLED)
        self.process_btn.pack(pady=10)

        # 进度条
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=500, mode='determinate')
        self.progress.pack(pady=10)

        # 状态标签
        self.status_label = tk.Label(self.root, text="请选择输入文件夹并点击【分析图片】", fg="gray")
        self.status_label.pack(pady=5)

    def browse_input(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_folder.set(folder)
            self.status_label.config(text=f"输入文件夹: {folder}", fg="green")
            # 重置后续状态
            self.image_data.clear()
            self.analyze_btn.config(state=tk.NORMAL)
            self.process_btn.config(state=tk.DISABLED)
            self.scale_slider.config(state=tk.DISABLED)
            self.ratio_label.config(text="(平均比例: --)")
            self.size_preview_label.config(text="平均缩放后宽高: -- x --")

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
            self.status_label.config(text=f"输出文件夹: {folder}", fg="green")

    def trim_transparent_border(self, img):
        """去除四周透明像素（仅对RGBA模式有效）"""
        if img.mode == 'RGBA':
            alpha = img.split()[-1]
            bbox = alpha.getbbox()
            if bbox:
                return img.crop(bbox)
        return img

    def analyze_images(self):
        """第一阶段：分析所有图片，计算平均预期缩放比例"""
        input_dir = self.input_folder.get()
        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showerror("错误", "请先选择一个有效的输入文件夹！")
            return

        # 获取所有PNG文件
        png_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.png')]
        if not png_files:
            messagebox.showinfo("提示", "该文件夹中没有PNG图片文件。")
            return

        self.status_label.config(text="正在分析图片，请稍候...")
        self.root.update_idletasks()

        self.image_data.clear()
        ratios = []
        total_width = 0
        total_height = 0
        max_width = 310
        max_height = 1000

        for filename in png_files:
            filepath = os.path.join(input_dir, filename)
            try:
                with Image.open(filepath) as img:
                    # 去除透明边框
                    trimmed = self.trim_transparent_border(img)
                    w, h = trimmed.size
                    # 计算该图片的预期缩放比例（若已小于限制则比例为1）
                    if w <= max_width and h <= max_height:
                        ratio = 1.0
                    else:
                        ratio = min(max_width / w, max_height / h)
                    ratios.append(ratio)
                    self.image_data.append((filepath, w, h, filename))
                    total_width += w
                    total_height += h
            except Exception as e:
                print(f"读取失败: {filename}, 错误: {e}")
                messagebox.showwarning("警告", f"无法读取图片 {filename}，已跳过。\n错误: {e}")

        if not self.image_data:
            messagebox.showerror("错误", "没有成功读取任何PNG图片。")
            return

        # 计算平均比例
        self.avg_ratio = sum(ratios) / len(ratios)
        # 将平均比例限制在[0.1, 1.0]区间（避免超出滑块范围）
        self.avg_ratio = max(0.1, min(1.0, self.avg_ratio))
        self.scale_ratio.set(self.avg_ratio)

        # 启用滑块并显示平均比例
        self.scale_slider.config(state=tk.NORMAL)
        self.ratio_label.config(text=f"(平均比例: {self.avg_ratio:.3f})")

        # 计算并显示按当前比例缩放后的平均宽高
        self.update_preview_size()

        # 启用处理按钮
        self.process_btn.config(state=tk.NORMAL)
        self.status_label.config(text="分析完成，可调整缩放比例，然后点击【开始统一缩放】", fg="blue")

    def on_scale_changed(self, event=None):
        """滑块值变化时更新预览尺寸"""
        self.update_preview_size()

    def update_preview_size(self):
        """根据当前最终缩放比例，计算并显示所有图片缩放后的平均宽高"""
        if not self.image_data:
            return
        ratio = self.scale_ratio.get()
        total_w = sum(w * ratio for _, w, h, _ in self.image_data)
        total_h = sum(h * ratio for _, w, h, _ in self.image_data)
        count = len(self.image_data)
        avg_w = total_w / count
        avg_h = total_h / count
        self.size_preview_label.config(text=f"平均缩放后宽高: {avg_w:.1f} x {avg_h:.1f}")

    def process_images(self):
        """第二阶段：按统一比例缩放所有图片并保存到输出文件夹"""
        input_dir = self.input_folder.get()
        output_dir = self.output_folder.get()
        if not output_dir:
            messagebox.showerror("错误", "请先选择输出文件夹！")
            return
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出文件夹：{e}")
                return

        if not self.image_data:
            messagebox.showerror("错误", "没有图片数据，请先点击【分析图片】。")
            return

        final_ratio = self.scale_ratio.get()
        # 确认对话框
        confirm = messagebox.askyesno(
            "确认",
            f"将使用统一缩放比例 {final_ratio:.3f}\n"
            f"处理 {len(self.image_data)} 张图片，并保存到：\n{output_dir}\n\n是否继续？"
        )
        if not confirm:
            return

        self.progress['maximum'] = len(self.image_data)
        self.progress['value'] = 0
        success_count = 0
        error_count = 0

        for idx, (src_path, orig_w, orig_h, filename) in enumerate(self.image_data, 1):
            self.status_label.config(text=f"正在处理: {filename}")
            self.root.update_idletasks()

            out_path = os.path.join(output_dir, filename)
            try:
                with Image.open(src_path) as img:
                    # 去除透明边框
                    trimmed = self.trim_transparent_border(img)
                    # 统一缩放
                    if final_ratio != 1.0:
                        new_w = int(orig_w * final_ratio)
                        new_h = int(orig_h * final_ratio)
                        # 使用高质量重采样
                        trimmed = trimmed.resize((new_w, new_h), Image.LANCZOS)
                    # 保存为PNG
                    trimmed.save(out_path, format='PNG')
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"处理失败: {filename}, 错误: {e}")

            self.progress['value'] = idx
            self.root.update_idletasks()

        self.status_label.config(text="处理完成")
        messagebox.showinfo("完成", f"处理完成！\n成功: {success_count} 个\n失败: {error_count} 个")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessor(root)
    root.mainloop()