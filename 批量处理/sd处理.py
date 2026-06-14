import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import threading


class ImageResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG 批量比例转换工具")
        self.root.geometry("1000x800")
        self.root.resizable(True, True)

        self.input_files = []
        self.output_dir = ""

        self.create_widgets()

    def create_widgets(self):
        frame_input = tk.LabelFrame(self.root, text="输入图像", padx=10, pady=10)
        frame_input.pack(fill="x", padx=10, pady=5)

        btn_add_files = tk.Button(frame_input, text="添加 PNG 文件", command=self.add_files, width=15)
        btn_add_files.grid(row=0, column=0, padx=5, pady=5)

        self.lbl_file_count = tk.Label(frame_input, text="已选择 0 个文件", fg="blue")
        self.lbl_file_count.grid(row=0, column=1, padx=5, pady=5)

        btn_clear_files = tk.Button(frame_input, text="清空列表", command=self.clear_files, width=10)
        btn_clear_files.grid(row=0, column=2, padx=5, pady=5)

        frame_list = tk.Frame(frame_input)
        frame_list.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=5)
        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_files = tk.Listbox(frame_list, yscrollcommand=scrollbar.set, height=8)
        self.listbox_files.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox_files.yview)

        frame_output = tk.LabelFrame(self.root, text="输出目录", padx=10, pady=10)
        frame_output.pack(fill="x", padx=10, pady=5)

        btn_output = tk.Button(frame_output, text="选择输出文件夹", command=self.select_output_dir, width=15)
        btn_output.grid(row=0, column=0, padx=5, pady=5)

        self.lbl_output_dir = tk.Label(frame_output, text="未选择", fg="gray")
        self.lbl_output_dir.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        frame_bg = tk.LabelFrame(self.root, text="背景颜色", padx=10, pady=10)
        frame_bg.pack(fill="x", padx=10, pady=5)

        self.bg_var = tk.StringVar(value="white")
        rb_white = tk.Radiobutton(frame_bg, text="白色", variable=self.bg_var, value="white")
        rb_white.pack(side=tk.LEFT, padx=10)
        rb_transparent = tk.Radiobutton(frame_bg, text="透明", variable=self.bg_var, value="transparent")
        rb_transparent.pack(side=tk.LEFT, padx=10)

        frame_progress = tk.LabelFrame(self.root, text="转换进度", padx=10, pady=10)
        frame_progress.pack(fill="x", padx=10, pady=5)

        self.progress_bar = ttk.Progressbar(frame_progress, mode='determinate')
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        self.lbl_status = tk.Label(frame_progress, text="就绪", fg="green")
        self.lbl_status.pack(pady=5)

        btn_convert = tk.Button(self.root, text="开始转换", command=self.start_conversion, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), height=2)
        btn_convert.pack(fill="x", padx=10, pady=10)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="选择 PNG 图片",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if files:
            for f in files:
                if f not in self.input_files:
                    self.input_files.append(f)
                    self.listbox_files.insert(tk.END, os.path.basename(f))
            self.lbl_file_count.config(text=f"已选择 {len(self.input_files)} 个文件")

    def clear_files(self):
        self.input_files.clear()
        self.listbox_files.delete(0, tk.END)
        self.lbl_file_count.config(text="已选择 0 个文件")

    def select_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出文件夹")
        if directory:
            self.output_dir = directory
            self.lbl_output_dir.config(text=directory, fg="black")

    def start_conversion(self):
        if not self.input_files:
            messagebox.showerror("错误", "请至少添加一个 PNG 文件")
            return
        if not self.output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return

        self.lbl_status.config(text="转换中...", fg="orange")
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = len(self.input_files)
        self.root.update()

        thread = threading.Thread(target=self.convert_images, daemon=True)
        thread.start()

    def convert_images(self):
        target_width = 336
        target_height = 480
        ratio = 7 / 10
        offset_y = 15

        bg_color = self.bg_var.get()
        if bg_color == "white":
            background = (255, 255, 255, 255)
        else:
            background = (0, 0, 0, 0)

        success_count = 0
        for idx, input_path in enumerate(self.input_files):
            try:
                img = Image.open(input_path).convert("RGBA")
                w0, h0 = img.size

                # 计算中间画布
                if w0 / h0 > ratio:
                    W_mid = w0
                    H_mid = int(w0 / ratio)
                else:
                    H_mid = h0
                    W_mid = int(h0 * ratio)

                x_mid = (W_mid - w0) // 2
                y_mid = (H_mid - h0) // 2 - offset_y
                if y_mid < 0:
                    y_mid = 0
                    print(f"警告: {os.path.basename(input_path)} 向上偏移后超出画布，已修正为顶部对齐")

                scale = target_width / W_mid
                x_final = int(x_mid * scale)
                y_final = int(y_mid * scale)
                w_final = int(w0 * scale)
                h_final = int(h0 * scale)

                final_img = Image.new("RGBA", (target_width, target_height), background)
                resized_img = img.resize((w_final, h_final), Image.Resampling.LANCZOS)
                final_img.paste(resized_img, (x_final, y_final), resized_img)

                # ***** 彻底清除元数据 *****
                # 方法：通过字节数据重建一张全新的图像
                clean_img = Image.frombytes("RGBA", final_img.size, final_img.tobytes())

                out_name = os.path.basename(input_path)
                out_path = os.path.join(self.output_dir, out_name)
                clean_img.save(out_path, "PNG")

                success_count += 1

            except Exception as e:
                print(f"处理失败 {input_path}: {str(e)}")

            self.root.after(0, self.update_progress, idx + 1)

        self.root.after(0, self.conversion_finished, success_count)

    def update_progress(self, value):
        self.progress_bar['value'] = value
        self.lbl_status.config(text=f"正在处理... {value}/{len(self.input_files)}")
        self.root.update_idletasks()

    def conversion_finished(self, success_count):
        self.progress_bar['value'] = len(self.input_files)
        self.lbl_status.config(text=f"转换完成！成功 {success_count} / {len(self.input_files)}", fg="green")
        messagebox.showinfo("完成", f"批量转换结束，成功处理 {success_count} 个文件。\n输出目录：{self.output_dir}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResizerApp(root)
    root.mainloop()