import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
import queue
import time

class ImageRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图片批量重命名工具")
        self.root.geometry("900x700")
        
        # 存储图片文件路径和原始名称
        self.image_files = []
        self.preview_queue = queue.Queue()
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
        # 开始预览更新线程
        self.running = True
        self.preview_thread = threading.Thread(target=self.update_preview_thread)
        self.preview_thread.daemon = True
        self.preview_thread.start()
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置颜色
        self.bg_color = "#f0f0f0"
        self.frame_bg = "#ffffff"
        self.accent_color = "#4a6fa5"
        self.highlight_color = "#e6f2ff"
        
        self.root.configure(bg=self.bg_color)
        
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = tk.Label(
            main_frame, 
            text="图片批量重命名工具", 
            font=("Arial", 18, "bold"),
            bg=self.bg_color,
            fg=self.accent_color
        )
        title_label.pack(pady=(0, 20))
        
        # 说明标签
        desc_label = tk.Label(
            main_frame,
            text="重命名格式: hcg_输入内容_序号(1,2,3...)\n例如: hcg_vacation_1.jpg, hcg_vacation_2.jpg",
            font=("Arial", 10),
            bg=self.bg_color,
            justify=tk.LEFT
        )
        desc_label.pack(pady=(0, 20))
        
        # 控制框架
        control_frame = tk.Frame(main_frame, bg=self.frame_bg, relief=tk.RAISED, bd=1)
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 输入内容区域
        input_frame = tk.Frame(control_frame, bg=self.frame_bg)
        input_frame.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(
            input_frame, 
            text="输入内容:", 
            font=("Arial", 11, "bold"),
            bg=self.frame_bg
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_frame, 
            textvariable=self.input_var,
            font=("Arial", 11),
            width=30
        )
        self.input_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # 绑定输入事件，实时更新预览
        self.input_var.trace_add("write", self.on_input_change)
        
        # 按钮区域
        button_frame = tk.Frame(control_frame, bg=self.frame_bg)
        button_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        self.select_btn = ttk.Button(
            button_frame,
            text="选择图片文件夹",
            command=self.select_folder,
            width=20
        )
        self.select_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.select_files_btn = ttk.Button(
            button_frame,
            text="选择图片文件",
            command=self.select_files,
            width=20
        )
        self.select_files_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.apply_btn = ttk.Button(
            button_frame,
            text="应用重命名",
            command=self.apply_renaming,
            width=20,
            state=tk.DISABLED
        )
        self.apply_btn.pack(side=tk.LEFT)
        
        # 图片列表和预览区域
        list_preview_frame = tk.Frame(main_frame, bg=self.bg_color)
        list_preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧 - 图片列表
        list_frame = tk.Frame(list_preview_frame, bg=self.frame_bg, relief=tk.RAISED, bd=1)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(
            list_frame, 
            text="图片列表 (原始 → 新名称)", 
            font=("Arial", 11, "bold"),
            bg=self.frame_bg
        ).pack(pady=10)
        
        # 滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 列表框
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Courier", 10),
            height=20,
            selectbackground=self.highlight_color
        )
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        scrollbar.config(command=self.listbox.yview)
        
        # 右侧 - 图片预览
        preview_frame = tk.Frame(list_preview_frame, bg=self.frame_bg, relief=tk.RAISED, bd=1)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(10, 0))
        
        tk.Label(
            preview_frame, 
            text="图片预览", 
            font=("Arial", 11, "bold"),
            bg=self.frame_bg
        ).pack(pady=10)
        
        # 预览画布
        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg="white",
            width=300,
            height=300,
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.preview_canvas.pack(padx=10, pady=(0, 10))
        
        self.preview_label = tk.Label(
            preview_frame,
            text="选择图片查看预览",
            font=("Arial", 10),
            bg=self.frame_bg,
            wraplength=280
        )
        self.preview_label.pack(padx=10, pady=(0, 10))
        
        # 绑定列表框选择事件
        self.listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = tk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg=self.frame_bg,
            font=("Arial", 9)
        )
        status_bar.pack(fill=tk.X, pady=(15, 0))
        
    def select_folder(self):
        """选择图片文件夹"""
        folder_path = filedialog.askdirectory(title="选择包含图片的文件夹")
        if folder_path:
            self.load_images_from_folder(folder_path)
    
    def select_files(self):
        """选择图片文件"""
        file_paths = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.gif *.bmp *.tiff"),
                ("所有文件", "*.*")
            ]
        )
        if file_paths:
            self.image_files = []
            for file_path in file_paths:
                self.image_files.append(file_path)
            self.update_listbox()
    
    def load_images_from_folder(self, folder_path):
        """从文件夹加载图片"""
        self.image_files = []
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')
        
        for file in os.listdir(folder_path):
            if file.lower().endswith(image_extensions):
                self.image_files.append(os.path.join(folder_path, file))
        
        if self.image_files:
            self.update_listbox()
            self.status_var.set(f"已加载 {len(self.image_files)} 张图片")
        else:
            messagebox.showwarning("无图片", "所选文件夹中没有找到图片文件")
    
    def update_listbox(self):
        """更新列表框内容"""
        self.listbox.delete(0, tk.END)
        
        if not self.image_files:
            return
        
        # 获取输入内容
        input_text = self.input_var.get().strip()
        
        # 更新列表框
        for i, file_path in enumerate(self.image_files):
            filename = os.path.basename(file_path)
            if input_text:
                # 获取文件扩展名
                name, ext = os.path.splitext(filename)
                new_name = f"hcg_{input_text}_{i+1}{ext}"
                display_text = f"{filename}  →  {new_name}"
            else:
                display_text = filename
            
            self.listbox.insert(tk.END, display_text)
        
        # 启用应用按钮
        self.apply_btn.config(state=tk.NORMAL if input_text and self.image_files else tk.DISABLED)
    
    def on_input_change(self, *args):
        """输入内容变化时更新预览"""
        # 避免频繁更新，使用队列机制
        self.preview_queue.put("update")
    
    def update_preview_thread(self):
        """在单独线程中更新预览，避免界面卡顿"""
        while self.running:
            try:
                # 从队列获取更新请求
                self.preview_queue.get(timeout=0.1)
                self.root.after(100, self.update_listbox)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"预览更新错误: {e}")
    
    def on_image_select(self, event):
        """列表框选择事件 - 显示图片预览"""
        selection = self.listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index < len(self.image_files):
            file_path = self.image_files[index]
            self.show_image_preview(file_path)
    
    def show_image_preview(self, file_path):
        """显示图片预览"""
        try:
            # 打开图片并调整大小
            img = Image.open(file_path)
            
            # 获取图片尺寸
            width, height = img.size
            
            # 调整大小以适应预览区域
            max_size = 280
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # 清除画布并显示新图片
            self.preview_canvas.delete("all")
            
            # 计算居中位置
            x_pos = (300 - new_width) // 2
            y_pos = (300 - new_height) // 2
            
            self.preview_canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=photo)
            self.preview_canvas.image = photo  # 保持引用
            
            # 更新标签
            filename = os.path.basename(file_path)
            self.preview_label.config(text=f"{filename}\n尺寸: {width}x{height}")
            
        except Exception as e:
            self.preview_canvas.delete("all")
            self.preview_label.config(text=f"无法预览图片\n{str(e)}")
    
    def apply_renaming(self):
        """应用重命名"""
        input_text = self.input_var.get().strip()
        if not input_text:
            messagebox.showwarning("输入错误", "请输入内容")
            return
        
        if not self.image_files:
            messagebox.showwarning("无图片", "请先选择图片")
            return
        
        # 确认对话框
        confirm = messagebox.askyesno(
            "确认重命名",
            f"即将重命名 {len(self.image_files)} 张图片\n"
            f"新名称格式: hcg_{input_text}_序号\n"
            f"此操作不可逆，请确认是否继续？"
        )
        
        if not confirm:
            return
        
        # 执行重命名
        success_count = 0
        error_messages = []
        
        for i, old_path in enumerate(self.image_files):
            try:
                # 获取目录和扩展名
                directory = os.path.dirname(old_path)
                name, ext = os.path.splitext(os.path.basename(old_path))
                
                # 创建新文件名
                new_name = f"hcg_{input_text}_{i+1}{ext}"
                new_path = os.path.join(directory, new_name)
                
                # 如果新文件名已存在，添加后缀避免冲突
                counter = 1
                while os.path.exists(new_path):
                    new_name = f"hcg_{input_text}_{i+1}_{counter}{ext}"
                    new_path = os.path.join(directory, new_name)
                    counter += 1
                
                # 重命名文件
                os.rename(old_path, new_path)
                success_count += 1
                
                # 更新文件列表中的路径
                self.image_files[i] = new_path
                
            except Exception as e:
                error_messages.append(f"文件 {os.path.basename(old_path)}: {str(e)}")
        
        # 显示结果
        if success_count == len(self.image_files):
            messagebox.showinfo("成功", f"所有 {success_count} 张图片重命名成功！")
            self.status_var.set(f"重命名完成: {success_count} 张图片")
        else:
            messagebox.showwarning(
                "部分成功",
                f"成功重命名 {success_count} 张图片，失败 {len(error_messages)} 张\n\n"
                f"错误详情:\n" + "\n".join(error_messages[:5]) + 
                ("\n..." if len(error_messages) > 5 else "")
            )
            self.status_var.set(f"重命名完成: {success_count} 成功, {len(error_messages)} 失败")
        
        # 更新列表框显示新文件名
        self.update_listbox()
    
    def on_closing(self):
        """程序关闭时的清理工作"""
        self.running = False
        if hasattr(self, 'preview_thread'):
            self.preview_thread.join(timeout=1)
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ImageRenamerApp(root)
    
    # 设置关闭事件处理
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()