#!/usr/bin/env python3
"""
小米Vela图片资源扫描器 - 轻量版（无需额外依赖）
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

class SimpleVelaScanner:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Vela图片扫描器-轻量版")
        self.root.geometry("550x400")
        
        # 支持的图片格式
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        
        # 目录路径变量
        self.cg_dir = tk.StringVar()
        self.char_dir = tk.StringVar()
        self.bg_dir = tk.StringVar()
        self.output_path = tk.StringVar(value=os.path.join(os.getcwd(), "image-config.json"))
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置简易界面"""
        # 标题
        tk.Label(self.root, text="小米Vela图片扫描器", font=("", 14, "bold")).pack(pady=10)
        tk.Label(self.root, text="选择图片文件夹，自动生成配置文件", font=("", 9)).pack(pady=5)
        
        # CG目录
        self.create_dir_selector("CG目录 (evig):", self.cg_dir, 0)
        # 立绘目录
        self.create_dir_selector("立绘目录 (cimg):", self.char_dir, 1)
        # 背景目录
        self.create_dir_selector("背景目录 (bcgi):", self.bg_dir, 2)
        
        # 输出路径
        tk.Label(self.root, text="输出文件:").pack(anchor='w', padx=30, pady=(10, 0))
        frame = tk.Frame(self.root)
        frame.pack(fill='x', padx=30, pady=5)
        
        tk.Entry(frame, textvariable=self.output_path, width=40).pack(side='left', fill='x', expand=True)
        tk.Button(frame, text="浏览", command=self.select_output, width=8).pack(side='right', padx=5)
        
        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="开始扫描", command=self.scan_images, 
                 bg='#4CAF50', fg='white', padx=30, pady=8).pack(side='left', padx=10)
        tk.Button(btn_frame, text="退出", command=self.root.quit,
                 padx=30, pady=8).pack(side='left', padx=10)
    
    def create_dir_selector(self, label, var, row):
        """创建目录选择器"""
        frame = tk.Frame(self.root)
        frame.pack(fill='x', padx=30, pady=5)
        
        tk.Label(frame, text=label, width=15, anchor='w').pack(side='left')
        tk.Entry(frame, textvariable=var, width=30).pack(side='left', padx=5, fill='x', expand=True)
        tk.Button(frame, text="选择", command=lambda v=var: self.select_dir(v), 
                 width=8).pack(side='right')
    
    def select_dir(self, var):
        """选择目录"""
        directory = filedialog.askdirectory()
        if directory:
            var.set(directory)
    
    def select_output(self):
        """选择输出文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")]
        )
        if file_path:
            self.output_path.set(file_path)
    
    def scan_images(self):
        """扫描图片并生成配置"""
        config = {
            "cg": self.scan_dir(self.cg_dir.get(), "evig"),
            "characters": self.scan_dir(self.char_dir.get(), "cimg"),
            "backgrounds": self.scan_dir(self.bg_dir.get(), "bcgi")
        }
        
        # 统计
        total = sum(len(v) for v in config.values())
        
        if total == 0:
            messagebox.showwarning("警告", "没有找到任何图片文件！")
            return
        
        # 保存文件
        try:
            with open(self.output_path.get(), 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", 
                f"配置文件生成成功！\n\n"
                f"CG图片: {len(config['cg'])} 个\n"
                f"立绘图片: {len(config['characters'])} 个\n"
                f"背景图片: {len(config['backgrounds'])} 个\n\n"
                f"文件保存到:\n{self.output_path.get()}")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败:\n{str(e)}")
    
    def scan_dir(self, directory, subdir_name):
        """扫描单个目录"""
        if not directory or not os.path.exists(directory):
            return []
        
        images = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                ext = Path(item).suffix.lower()
                if ext in self.supported_formats:
                    # 构建Vela路径格式
                    vela_path = f"/common/{subdir_name}/{item}"
                    images.append(vela_path)
        
        # 按文件名排序
        images.sort()
        return images
    
    def run(self):
        """运行程序"""
        self.root.mainloop()

# 主程序
if __name__ == "__main__":
    print("正在启动Vela图片扫描器...")
    try:
        app = SimpleVelaScanner()
        app.run()
    except Exception as e:
        print(f"启动失败: {e}")
        input("按回车键退出...")