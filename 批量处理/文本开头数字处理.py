import os
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

class TextNumberRemover:
    def __init__(self, root):
        self.root = root
        self.root.title("文本开头半角数字移除工具")
        self.root.geometry("800x600")
        self.root.configure(bg='#1e1e1e')
        
        # 设置主题
        self.setup_dark_theme()
        
        # 数据
        self.project_path = ""
        self.script_path = ""
        self.script_files = []
        self.all_dialogues = {}  # key: dialogue_id, value: script data
        self.total_dialogues = 0
        self.need_fix_count = 0
        self.fixed_count = 0
        
        # 创建界面
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
        
        style.configure('TCombobox',
                       fieldbackground='#252526',
                       foreground='#d4d4d4')
        
        style.configure('Vertical.TScrollbar',
                       background='#3c3c3c',
                       troughcolor='#1e1e1e')
        
    def create_widgets(self):
        # 顶部框架
        top_frame = ttk.LabelFrame(self.root, text="项目设置", padding="10")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        # 项目路径选择
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(fill="x", pady=5)
        
        ttk.Label(path_frame, text="脚本文件夹:").pack(side="left", padx=5)
        self.script_path_var = tk.StringVar()
        script_entry = ttk.Entry(path_frame, textvariable=self.script_path_var, width=50)
        script_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Button(path_frame, text="浏览...", command=self.select_script_folder).pack(side="right", padx=5)
        ttk.Button(path_frame, text="加载脚本", command=self.load_scripts).pack(side="right", padx=5)
        
        # 状态显示
        status_frame = ttk.Frame(top_frame)
        status_frame.pack(fill="x", pady=5)
        
        self.status_label = ttk.Label(status_frame, text="未加载脚本", foreground="#6a9955")
        self.status_label.pack(side="left", padx=5)
        
        # 统计信息
        self.stats_label = ttk.Label(status_frame, text="")
        self.stats_label.pack(side="right", padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="修复日志", padding="10")
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
        
        # 按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="扫描并预览修复项", command=self.scan_and_preview).pack(side="left", padx=5)
        ttk.Button(button_frame, text="执行修复", command=self.execute_fix).pack(side="left", padx=5)
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side="right", padx=5)
        
    def log(self, message, color="#d4d4d4"):
        """在日志区域添加一条消息"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.tag_add(f"color_{color}", "end-1c linestart", "end-1c")
        self.log_text.tag_config(f"color_{color}", foreground=color)
        
    def select_script_folder(self):
        folder = filedialog.askdirectory(title="选择script文件夹")
        if folder:
            self.script_path = folder
            self.script_path_var.set(folder)
            # 尝试自动获取项目路径（脚本文件夹的上级目录为common，再上级为项目根目录）
            common_path = os.path.dirname(folder)
            project_path = os.path.dirname(common_path)
            self.log(f"脚本目录: {folder}", "#858585")
            self.log(f"项目根目录: {project_path}", "#858585")
            self.status_label.config(text="脚本文件夹已选择，请点击“加载脚本”")
            
    def load_scripts(self):
        """加载所有脚本文件"""
        if not self.script_path or not os.path.exists(self.script_path):
            messagebox.showwarning("警告", "请先选择有效的脚本文件夹！")
            return
            
        self.log("正在扫描脚本文件...", "#569cd6")
        self.script_files = []
        try:
            for f in os.listdir(self.script_path):
                if f.lower().startswith("scriptdata") and f.lower().endswith(".txt"):
                    self.script_files.append(f)
        except Exception as e:
            self.log(f"扫描脚本文件失败: {e}", "#ff6666")
            return
            
        if not self.script_files:
            self.log("未找到任何脚本文件！", "#ff6666")
            return
            
        self.log(f"找到 {len(self.script_files)} 个脚本文件", "#6a9955")
        
        # 加载所有对话数据
        self.all_dialogues = {}
        self.total_dialogues = 0
        
        def extract_number(filename):
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else 0
            
        self.script_files.sort(key=extract_number)
        
        for script_file in self.script_files:
            file_path = os.path.join(self.script_path, script_file)
            try:
                encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']
                chunk_data = None
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                            chunk_data = json.loads(content)
                        break
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                if chunk_data:
                    for k, v in chunk_data.items():
                        self.all_dialogues[k] = v
                    self.total_dialogues += len(chunk_data)
            except Exception as e:
                self.log(f"加载 {script_file} 失败: {e}", "#ff6666")
                
        self.log(f"共加载 {self.total_dialogues} 条对话", "#6a9955")
        self.status_label.config(text="脚本加载完成")
        
        # 可选：立即扫描
        self.scan_and_preview()
        
    def remove_leading_number(self, text):
        """移除文本开头的半角数字（包括整数和浮点数）"""
        if not text:
            return text
        # 匹配开头的半角数字（0-9）和半角点号，以及后续可能的空格
        match = re.match(r'^[0-9\.]+\s*', text)
        if match:
            # 去除匹配的部分
            new_text = text[match.end():]
            return new_text
        return text
        
    def scan_and_preview(self):
        """扫描需要修复的文本字段，并显示在日志中"""
        if not self.all_dialogues:
            messagebox.showwarning("警告", "请先加载脚本！")
            return
            
        self.log("\n" + "="*60, "#858585")
        self.log("开始扫描需要修复的文本字段（开头半角数字）...", "#569cd6")
        
        self.need_fix_count = 0
        self.fix_candidates = []  # 存储 (dialogue_id, old_text, new_text)
        
        for dialogue_id, script in self.all_dialogues.items():
            if 't' in script and script['t']:
                old_text = script['t']
                new_text = self.remove_leading_number(old_text)
                if new_text != old_text:
                    self.need_fix_count += 1
                    self.fix_candidates.append((dialogue_id, old_text, new_text))
                    # 显示前50个字符，避免日志过长
                    preview_old = old_text[:50] + "..." if len(old_text) > 50 else old_text
                    preview_new = new_text[:50] + "..." if len(new_text) > 50 else new_text
                    self.log(f"对话 {dialogue_id}:", "#ffcc00")
                    self.log(f"  旧: {preview_old}", "#858585")
                    self.log(f"  新: {preview_new}", "#6a9955")
                    
        if self.need_fix_count == 0:
            self.log("没有发现需要修复的文本字段！", "#6a9955")
        else:
            self.log(f"共发现 {self.need_fix_count} 个需要修复的文本字段", "#ffcc00")
        self.log("="*60, "#858585")
        self.stats_label.config(text=f"需修复: {self.need_fix_count}")
        
    def execute_fix(self):
        """执行修复：更新内存中的数据并保存回文件"""
        if not self.fix_candidates:
            messagebox.showinfo("提示", "没有需要修复的项，请先扫描。")
            return
            
        if not messagebox.askyesno("确认修复", f"将修复 {self.need_fix_count} 个文本字段。\n是否继续？"):
            return
            
        self.log("\n开始修复...", "#569cd6")
        
        # 应用修复到内存数据
        for dialogue_id, old_text, new_text in self.fix_candidates:
            self.all_dialogues[dialogue_id]['t'] = new_text
            
        # 保存回文件（分块保存）
        chunk_files = {}
        for dialogue_id, script in self.all_dialogues.items():
            try:
                id_num = int(dialogue_id)
                chunk_num = (id_num - 1) // 500 + 1
                if chunk_num not in chunk_files:
                    chunk_files[chunk_num] = {}
                chunk_files[chunk_num][dialogue_id] = script
            except ValueError:
                continue
                
        total_chunks = len(chunk_files)
        saved_chunks = 0
        failed_chunks = []
        
        for chunk_num, chunk_data in chunk_files.items():
            chunk_file = os.path.join(self.script_path, f"scriptData{chunk_num}.txt")
            try:
                # 按ID排序后保存
                sorted_data = {}
                for id_key in sorted(chunk_data.keys(), key=lambda x: int(x)):
                    sorted_data[id_key] = chunk_data[id_key]
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    json.dump(sorted_data, f, ensure_ascii=False, indent=2)
                saved_chunks += 1
                self.log(f"已保存块 {chunk_num}", "#6a9955")
            except Exception as e:
                failed_chunks.append(chunk_num)
                self.log(f"保存块 {chunk_num} 失败: {e}", "#ff6666")
                
        if failed_chunks:
            self.log(f"部分保存失败：{failed_chunks}", "#ff6666")
            messagebox.showwarning("保存警告", f"成功保存 {saved_chunks}/{total_chunks} 个文件。\n失败块: {failed_chunks}")
        else:
            self.log(f"所有更改已保存！共 {saved_chunks} 个文件", "#6a9955")
            messagebox.showinfo("修复完成", f"成功修复 {self.need_fix_count} 个文本字段。")
            
        self.stats_label.config(text=f"已修复: {self.need_fix_count}")
        self.status_label.config(text="修复完成")

def main():
    root = tk.Tk()
    app = TextNumberRemover(root)
    root.mainloop()

if __name__ == "__main__":
    main()