import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import os
import re
from datetime import datetime
from tkinter.font import Font
import threading

class TextReplacementTool:
    def __init__(self, root):
        self.root = root
        self.root.title("批量文本替换工具")
        self.root.geometry("1200x700")
        
        # 存储打开的文件
        self.open_files = {}  # 文件路径 -> 文件数据字典
        # 当前活动的文件
        self.current_file = None
        # 存储替换记录
        self.replacement_history = []
        
        # 设置样式
        self.setup_styles()
        # 创建UI
        self.create_widgets()
        
    def setup_styles(self):
        """设置UI样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置颜色
        self.bg_color = "#f5f5f5"
        self.sidebar_color = "#e8e8e8"
        self.button_color = "#4a6fa5"
        self.button_hover = "#3a5a8a"
        
        self.root.configure(bg=self.bg_color)
        
    def create_widgets(self):
        """创建UI组件"""
        # 主框架
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部工具栏
        toolbar = tk.Frame(main_frame, bg=self.bg_color, height=40)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        toolbar.pack_propagate(False)
        
        # 文件操作按钮
        btn_style = {
            'bg': self.button_color, 
            'fg': 'white', 
            'relief': tk.RAISED,
            'bd': 2,
            'padx': 15,
            'pady': 5
        }
        
        self.open_button = tk.Button(
            toolbar, text="打开文件", command=self.open_single_file,
            font=("Arial", 10), **btn_style
        )
        self.open_button.pack(side=tk.LEFT, padx=5)
        
        self.open_batch_button = tk.Button(
            toolbar, text="批量打开文件", command=self.open_batch_files,
            font=("Arial", 10), **btn_style
        )
        self.open_batch_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = tk.Button(
            toolbar, text="保存当前文件", command=self.save_current_file,
            font=("Arial", 10), **btn_style
        )
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.save_all_button = tk.Button(
            toolbar, text="保存所有文件", command=self.save_all_files,
            font=("Arial", 10), bg="#2e7d32", fg="white",
            relief=tk.RAISED, bd=2, padx=15, pady=5
        )
        self.save_all_button.pack(side=tk.LEFT, padx=5)
        
        # 文件列表标签
        tk.Label(toolbar, text="已打开文件:", bg=self.bg_color, 
                font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))
        
        # 文件选择下拉框
        self.file_var = tk.StringVar()
        self.file_dropdown = ttk.Combobox(
            toolbar, textvariable=self.file_var, 
            state="readonly", width=30
        )
        self.file_dropdown.pack(side=tk.LEFT, padx=5)
        self.file_dropdown.bind("<<ComboboxSelected>>", self.on_file_selected)
        
        # 关闭当前文件按钮
        self.close_button = tk.Button(
            toolbar, text="关闭当前文件", command=self.close_current_file,
            font=("Arial", 9), bg="#d32f2f", fg="white",
            relief=tk.RAISED, bd=1, padx=10, pady=3
        )
        self.close_button.pack(side=tk.LEFT, padx=5)
        
        # 主内容区域
        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧面板 - 文件内容预览/编辑
        left_frame = tk.Frame(content_frame, bg=self.sidebar_color, relief=tk.RAISED, bd=1)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 左侧标题栏
        left_header = tk.Frame(left_frame, bg=self.button_color, height=30)
        left_header.pack(fill=tk.X)
        left_header.pack_propagate(False)
        
        self.file_title = tk.Label(
            left_header, text="文本预览与编辑", 
            bg=self.button_color, fg="white", 
            font=("Arial", 10, "bold")
        )
        self.file_title.pack(side=tk.LEFT, padx=10)
        
        # 文件统计信息
        self.file_stats = tk.Label(
            left_header, text="未选择文件", 
            bg=self.button_color, fg="#e0e0e0",
            font=("Arial", 9)
        )
        self.file_stats.pack(side=tk.RIGHT, padx=10)
        
        # 文本编辑区域
        self.text_editor = scrolledtext.ScrolledText(
            left_frame, wrap=tk.WORD, font=("Consolas", 10),
            undo=True, maxundo=100, bg="white", fg="#333333"
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 绑定文本修改事件
        self.text_editor.bind("<<Modified>>", self.on_text_modified)
        
        # 中间悬浮面板 - 替换控制
        center_frame = tk.Frame(content_frame, bg=self.bg_color)
        center_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 替换控制面板
        control_panel = tk.Frame(center_frame, bg=self.bg_color, relief=tk.RAISED, bd=2)
        control_panel.pack(pady=10)
        
        # 替换标题
        tk.Label(control_panel, text="替换设置", bg=self.bg_color, 
                font=("Arial", 12, "bold")).pack(pady=(10, 5))
        
        # 查找文本
        tk.Label(control_panel, text="查找文本:", bg=self.bg_color, 
                anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))
        self.find_entry = tk.Entry(control_panel, width=25, font=("Arial", 10))
        self.find_entry.pack(padx=10, pady=(0, 10))
        self.find_entry.bind("<Return>", lambda e: self.perform_replace())
        
        # 替换为文本
        tk.Label(control_panel, text="替换为:", bg=self.bg_color, 
                anchor="w").pack(fill=tk.X, padx=10)
        self.replace_entry = tk.Entry(control_panel, width=25, font=("Arial", 10))
        self.replace_entry.pack(padx=10, pady=(0, 10))
        self.replace_entry.bind("<Return>", lambda e: self.perform_replace())
        
        # 替换范围选项
        range_frame = tk.Frame(control_panel, bg=self.bg_color)
        range_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.replace_scope_var = tk.StringVar(value="current")
        tk.Radiobutton(
            range_frame, text="当前文件", variable=self.replace_scope_var,
            value="current", bg=self.bg_color
        ).pack(anchor="w")
        
        tk.Radiobutton(
            range_frame, text="所有打开文件", variable=self.replace_scope_var,
            value="all", bg=self.bg_color
        ).pack(anchor="w")
        
        # 搜索选项
        options_frame = tk.Frame(control_panel, bg=self.bg_color)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.case_sensitive_var = tk.BooleanVar(value=False)
        self.case_check = tk.Checkbutton(
            options_frame, text="区分大小写", variable=self.case_sensitive_var,
            bg=self.bg_color
        )
        self.case_check.pack(anchor="w")
        
        self.whole_word_var = tk.BooleanVar(value=False)
        self.word_check = tk.Checkbutton(
            options_frame, text="全词匹配", variable=self.whole_word_var,
            bg=self.bg_color
        )
        self.word_check.pack(anchor="w")
        
        # 按钮
        button_frame = tk.Frame(control_panel, bg=self.bg_color)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.replace_button = tk.Button(
            button_frame, text="执行替换", command=self.perform_replace,
            bg=self.button_color, fg="white", font=("Arial", 10, "bold"),
            relief=tk.RAISED, bd=2, padx=15, pady=5
        )
        self.replace_button.pack(fill=tk.X, pady=5)
        
        self.replace_all_button = tk.Button(
            button_frame, text="全部替换", command=self.perform_replace_all,
            bg="#2e7d32", fg="white", font=("Arial", 10),
            relief=tk.RAISED, bd=2, padx=15, pady=5
        )
        self.replace_all_button.pack(fill=tk.X, pady=5)
        
        # 新增：替换半角空格按钮
        self.space_replace_button = tk.Button(
            button_frame, text="替换半角空格", command=self.replace_halfwidth_spaces,
            bg="#b85c00", fg="white", font=("Arial", 10),
            relief=tk.RAISED, bd=2, padx=15, pady=5
        )
        self.space_replace_button.pack(fill=tk.X, pady=5)
        
        # 批量操作按钮
        batch_frame = tk.Frame(center_frame, bg=self.bg_color)
        batch_frame.pack(fill=tk.X, pady=10)
        
        self.batch_replace_button = tk.Button(
            batch_frame, text="批量替换所有文件", command=self.batch_replace_all_files,
            bg="#5d6bb0", fg="white", font=("Arial", 10),
            relief=tk.RAISED, bd=2, padx=15, pady=5
        )
        self.batch_replace_button.pack(fill=tk.X, pady=5)
        
        # 右侧面板 - 替换记录
        right_frame = tk.Frame(content_frame, bg=self.sidebar_color, relief=tk.RAISED, bd=1)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 右侧标题栏
        right_header = tk.Frame(right_frame, bg=self.button_color, height=30)
        right_header.pack(fill=tk.X)
        right_header.pack_propagate(False)
        
        tk.Label(right_header, text="替换记录", 
                bg=self.button_color, fg="white", 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        
        # 记录操作按钮
        history_buttons = tk.Frame(right_header, bg=self.button_color)
        history_buttons.pack(side=tk.RIGHT, padx=5)
        
        self.clear_history_btn = tk.Button(
            history_buttons, text="清空记录", command=self.clear_history,
            bg="#d32f2f", fg="white", font=("Arial", 8),
            relief=tk.FLAT, padx=5
        )
        self.clear_history_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.export_history_btn = tk.Button(
            history_buttons, text="导出记录", command=self.export_history,
            bg="#5d6bb0", fg="white", font=("Arial", 8),
            relief=tk.FLAT, padx=5
        )
        self.export_history_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 替换记录列表
        history_frame = tk.Frame(right_frame, bg="white")
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建带滚动条的文本框显示记录
        self.history_text = scrolledtext.ScrolledText(
            history_frame, wrap=tk.WORD, font=("Arial", 9),
            bg="white", fg="#333333", height=10
        )
        self.history_text.pack(fill=tk.BOTH, expand=True)
        self.history_text.config(state=tk.DISABLED)
        
        # 状态栏
        self.status_bar = tk.Label(
            self.root, text="就绪", bg="#e0e0e0", fg="#333333",
            anchor=tk.W, relief=tk.SUNKEN, bd=1
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 初始化
        self.update_file_dropdown()
        
    def open_single_file(self):
        """打开单个文本文件"""
        file_path = filedialog.askopenfilename(
            title="选择文本文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.load_file(file_path)
    
    def open_batch_files(self):
        """批量打开多个文本文件"""
        file_paths = filedialog.askopenfilenames(
            title="选择多个文本文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_paths:
            # 统计成功打开的文件数
            success_count = 0
            total_count = len(file_paths)
            
            for file_path in file_paths:
                if self.load_file(file_path, show_error=False):
                    success_count += 1
            
            self.update_status(f"成功打开 {success_count}/{total_count} 个文件")
            
            # 如果有文件打开失败，显示警告
            if success_count < total_count:
                messagebox.showwarning(
                    "部分文件打开失败", 
                    f"成功打开 {success_count} 个文件，{total_count - success_count} 个文件打开失败"
                )
    
    def load_file(self, file_path, show_error=True):
        """加载文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # 存储文件数据
            self.open_files[file_path] = {
                'content': content,
                'original_content': content,
                'modified': False,
                'history': []
            }
            
            # 如果是第一个文件或当前没有活动文件，设置为当前文件
            if self.current_file is None:
                self.current_file = file_path
                self.display_file_content(file_path)
            
            # 更新UI
            self.update_file_dropdown()
            
            return True
            
        except Exception as e:
            if show_error:
                messagebox.showerror("错误", f"无法打开文件 {os.path.basename(file_path)}: {str(e)}")
            return False
    
    def display_file_content(self, file_path):
        """显示指定文件的内容"""
        if file_path in self.open_files:
            file_data = self.open_files[file_path]
            
            # 更新文本编辑器
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, file_data['content'])
            self.text_editor.edit_reset()  # 重置撤销历史
            
            # 更新标题
            filename = os.path.basename(file_path)
            modified_mark = " *" if file_data['modified'] else ""
            self.file_title.config(text=f"正在编辑: {filename}{modified_mark}")
            
            # 更新文件统计
            char_count = len(file_data['content'])
            line_count = file_data['content'].count('\n') + 1
            self.file_stats.config(text=f"字符数: {char_count}, 行数: {line_count}")
            
            # 更新替换记录显示
            self.update_history_display()
    
    def on_file_selected(self, event=None):
        """文件选择下拉框事件"""
        selected_text = self.file_var.get()
        if selected_text:
            # 从显示文本中提取文件名（去掉修改标记）
            clean_name = selected_text.replace(" *", "")
            
            # 查找对应的文件路径
            for file_path in self.open_files.keys():
                if os.path.basename(file_path) == clean_name:
                    self.current_file = file_path
                    self.display_file_content(file_path)
                    break
    
    def update_file_dropdown(self):
        """更新文件下拉框"""
        file_list = list(self.open_files.keys())
        display_list = []
        
        for file_path in file_list:
            filename = os.path.basename(file_path)
            modified_mark = " *" if self.open_files[file_path]['modified'] else ""
            display_list.append(f"{filename}{modified_mark}")
        
        self.file_dropdown['values'] = display_list
        
        # 设置当前选中的文件
        if self.current_file and self.current_file in self.open_files:
            filename = os.path.basename(self.current_file)
            modified_mark = " *" if self.open_files[self.current_file]['modified'] else ""
            self.file_var.set(f"{filename}{modified_mark}")
        elif file_list:
            self.current_file = file_list[0]
            self.display_file_content(self.current_file)
        else:
            self.current_file = None
            self.file_var.set("")
    
    def on_text_modified(self, event=None):
        """文本修改事件处理"""
        if self.text_editor.edit_modified() and self.current_file:
            # 重置修改标志
            self.text_editor.edit_modified(False)
            
            # 获取当前内容
            content = self.text_editor.get(1.0, tk.END)
            
            # 更新文件数据
            if self.current_file in self.open_files:
                self.open_files[self.current_file]['content'] = content
                self.open_files[self.current_file]['modified'] = True
                
                # 更新文件下拉框显示
                self.update_file_dropdown()
                
                # 更新标题
                filename = os.path.basename(self.current_file)
                self.file_title.config(text=f"正在编辑: {filename} *")
    
    def save_current_file(self):
        """保存当前文件"""
        if not self.current_file:
            messagebox.showwarning("警告", "没有打开的文件")
            return
            
        self.save_file(self.current_file)
    
    def save_all_files(self):
        """保存所有打开的文件"""
        if not self.open_files:
            messagebox.showwarning("警告", "没有打开的文件")
            return
            
        # 统计保存的文件数
        saved_count = 0
        modified_count = 0
        failed_files = []
        
        for file_path, file_data in self.open_files.items():
            if file_data['modified']:
                modified_count += 1
                if self.save_file(file_path, show_message=False):
                    saved_count += 1
                else:
                    failed_files.append(os.path.basename(file_path))
        
        # 显示结果
        if modified_count == 0:
            self.update_status("没有需要保存的修改")
        else:
            if failed_files:
                error_msg = "以下文件保存失败:\n" + "\n".join(failed_files)
                messagebox.showerror("部分文件保存失败", error_msg)
                self.update_status(f"已保存 {saved_count}/{modified_count} 个文件")
            else:
                self.update_status(f"已保存所有 {saved_count} 个文件")
                messagebox.showinfo("保存成功", f"已保存所有 {saved_count} 个文件")
    
    def save_file(self, file_path, show_message=True):
        """保存指定文件"""
        try:
            if file_path in self.open_files:
                content = self.open_files[file_path]['content']
                
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                # 更新文件状态
                self.open_files[file_path]['modified'] = False
                self.open_files[file_path]['original_content'] = content
                
                # 更新UI
                self.update_file_dropdown()
                
                if file_path == self.current_file:
                    filename = os.path.basename(file_path)
                    self.file_title.config(text=f"正在编辑: {filename}")
                
                if show_message:
                    self.update_status(f"文件已保存: {os.path.basename(file_path)}")
                    messagebox.showinfo("保存成功", "文件已保存成功！")
                
                return True
            return False
                
        except Exception as e:
            if show_message:
                messagebox.showerror("错误", f"无法保存文件: {str(e)}")
            return False
    
    def close_current_file(self):
        """关闭当前文件"""
        if not self.current_file:
            return
            
        # 检查是否有未保存的修改
        if self.open_files[self.current_file]['modified']:
            response = messagebox.askyesnocancel(
                "保存修改", 
                f"文件 {os.path.basename(self.current_file)} 有未保存的修改，是否保存？"
            )
            
            if response is None:  # 取消
                return
            elif response:  # 是，保存
                self.save_file(self.current_file)
        
        # 从打开文件列表中移除
        del self.open_files[self.current_file]
        
        # 更新当前文件
        if self.open_files:
            self.current_file = list(self.open_files.keys())[0]
            self.display_file_content(self.current_file)
        else:
            self.current_file = None
            self.text_editor.delete(1.0, tk.END)
            self.file_title.config(text="文本预览与编辑")
            self.file_stats.config(text="未选择文件")
            self.history_text.config(state=tk.NORMAL)
            self.history_text.delete(1.0, tk.END)
            self.history_text.config(state=tk.DISABLED)
        
        # 更新文件下拉框
        self.update_file_dropdown()
    
    def perform_replace(self, all_occurrences=False):
        """执行替换操作"""
        find_text = self.find_entry.get().strip()
        replace_text = self.replace_entry.get()
        
        if not find_text:
            messagebox.showwarning("警告", "请输入要查找的文本")
            return
        
        # 确定替换范围
        scope = self.replace_scope_var.get()
        
        if scope == "current":
            files_to_process = [self.current_file] if self.current_file else []
        else:  # "all"
            files_to_process = list(self.open_files.keys())
        
        if not files_to_process:
            messagebox.showwarning("警告", "没有打开的文件")
            return
        
        # 执行替换
        total_count = 0
        file_count = 0
        
        for file_path in files_to_process:
            if file_path in self.open_files:
                count = self.replace_in_file(file_path, find_text, replace_text, all_occurrences)
                if count > 0:
                    total_count += count
                    file_count += 1
        
        # 更新状态
        if total_count > 0:
            if scope == "current":
                self.update_status(f"已替换 {total_count} 处 '{find_text}' -> '{replace_text}'")
            else:
                self.update_status(f"已在 {file_count} 个文件中替换 {total_count} 处 '{find_text}' -> '{replace_text}'")
        else:
            self.update_status(f"未找到匹配项: '{find_text}'")
    
    def replace_in_file(self, file_path, find_text, replace_text, all_occurrences=False):
        """在指定文件中执行替换"""
        if file_path not in self.open_files:
            return 0
            
        file_data = self.open_files[file_path]
        content = file_data['content']
        
        # 构建正则表达式
        flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
        
        if self.whole_word_var.get():
            pattern = r'\b' + re.escape(find_text) + r'\b'
        else:
            pattern = re.escape(find_text)
        
        # 执行替换
        try:
            if all_occurrences:
                # 全部替换
                new_content, count = re.subn(pattern, replace_text, content, flags=flags)
            else:
                # 只替换第一个匹配项
                match = re.search(pattern, content, flags=flags)
                if match:
                    start, end = match.span()
                    new_content = content[:start] + replace_text + content[end:]
                    count = 1
                else:
                    new_content = content
                    count = 0
            
            if count == 0:
                return 0
                
            # 更新文件内容
            file_data['content'] = new_content
            file_data['modified'] = True
            
            # 记录替换操作
            timestamp = datetime.now().strftime("%H:%M:%S")
            filename = os.path.basename(file_path)
            
            if all_occurrences:
                record_text = f"{timestamp} | {filename} | 全部替换: '{find_text}' -> '{replace_text}' ({count}处)"
            else:
                record_text = f"{timestamp} | {filename} | 替换: '{find_text}' -> '{replace_text}'"
            
            # 添加到全局历史记录
            self.replacement_history.append({
                'timestamp': timestamp,
                'file': file_path,
                'filename': filename,
                'find': find_text,
                'replace': replace_text,
                'count': count,
                'all': all_occurrences,
                'content_before': content,
                'content_after': new_content,
                'record_text': record_text
            })
            
            # 添加到文件历史记录
            file_data['history'].append({
                'timestamp': timestamp,
                'find': find_text,
                'replace': replace_text,
                'count': count,
                'all': all_occurrences
            })
            
            # 如果是当前文件，更新显示
            if file_path == self.current_file:
                self.display_file_content(file_path)
            
            # 更新文件下拉框
            self.update_file_dropdown()
            
            # 更新替换记录显示
            self.update_history_display()
            
            return count
            
        except re.error as e:
            messagebox.showerror("正则表达式错误", f"无效的正则表达式: {str(e)}")
            return 0
    
    def perform_replace_all(self):
        """执行全部替换"""
        self.perform_replace(all_occurrences=True)
    
    def batch_replace_all_files(self):
        """批量替换所有文件"""
        find_text = self.find_entry.get().strip()
        replace_text = self.replace_entry.get()
        
        if not find_text:
            messagebox.showwarning("警告", "请输入要查找的文本")
            return
        
        if not self.open_files:
            messagebox.showwarning("警告", "没有打开的文件")
            return
        
        # 确认对话框
        file_count = len(self.open_files)
        confirm = messagebox.askyesno(
            "确认批量替换", 
            f"将在 {file_count} 个文件中执行替换操作\n"
            f"查找: '{find_text}'\n"
            f"替换为: '{replace_text}'\n\n"
            f"确定要继续吗？"
        )
        
        if not confirm:
            return
        
        # 执行批量替换
        total_count = 0
        success_files = 0
        
        # 禁用按钮避免重复点击
        self.batch_replace_button.config(state=tk.DISABLED, text="处理中...")
        self.root.update()
        
        try:
            for file_path in self.open_files:
                count = self.replace_in_file(file_path, find_text, replace_text, all_occurrences=True)
                if count > 0:
                    total_count += count
                    success_files += 1
            
            # 显示结果
            self.update_status(f"批量替换完成: {success_files}/{file_count} 个文件，共替换 {total_count} 处")
            
            result_message = (
                f"批量替换完成！\n\n"
                f"处理文件数: {file_count}\n"
                f"成功替换文件数: {success_files}\n"
                f"总替换次数: {total_count}\n"
                f"查找内容: '{find_text}'\n"
                f"替换内容: '{replace_text}'"
            )
            
            messagebox.showinfo("批量替换完成", result_message)
            
        finally:
            # 恢复按钮状态
            self.batch_replace_button.config(state=tk.NORMAL, text="批量替换所有文件")
    
    # ---------- 新增功能：替换半角空格 ----------
    def replace_halfwidth_spaces(self):
        """替换所有半角空格（ASCII 32）为用户指定的字符"""
        if not self.open_files:
            messagebox.showwarning("警告", "没有打开的文件")
            return
        
        # 确定替换范围
        scope = self.replace_scope_var.get()
        if scope == "current" and not self.current_file:
            messagebox.showwarning("警告", "没有当前文件")
            return
        
        # 弹出输入对话框，询问替换后的字符
        target_char = simpledialog.askstring(
            "替换半角空格",
            "请输入用于替换半角空格的字符（可留空表示删除所有半角空格）:\n\n例如：全角空格　 或 下划线 _ 等",
            initialvalue="　"  # 全角空格
        )
        
        if target_char is None:  # 用户取消
            return
        
        # 确定要处理的文件列表
        if scope == "current":
            files_to_process = [self.current_file]
        else:
            files_to_process = list(self.open_files.keys())
        
        # 执行替换
        total_count = 0
        success_files = 0
        
        for file_path in files_to_process:
            if file_path in self.open_files:
                count = self._replace_spaces_in_file(file_path, target_char)
                if count >= 0:  # -1 表示错误，0或正数表示替换次数
                    total_count += count
                    success_files += 1
        
        # 更新状态
        if total_count > 0:
            display_target = target_char if target_char else "(空)"
            self.update_status(f"已替换 {total_count} 个半角空格 -> '{display_target}'，影响 {success_files} 个文件")
            messagebox.showinfo("替换完成", 
                f"替换半角空格完成！\n\n"
                f"替换次数: {total_count}\n"
                f"影响文件数: {success_files}\n"
                f"替换为: '{display_target}'")
        else:
            self.update_status("未找到半角空格")
    
    def _replace_spaces_in_file(self, file_path, target_char):
        """在单个文件中将所有半角空格替换为目标字符，返回替换次数"""
        if file_path not in self.open_files:
            return 0
        
        file_data = self.open_files[file_path]
        content = file_data['content']
        
        # 统计半角空格数量
        count = content.count(' ')
        if count == 0:
            return 0
        
        # 执行替换
        new_content = content.replace(' ', target_char)
        
        # 更新文件内容
        file_data['content'] = new_content
        file_data['modified'] = True
        
        # 记录替换操作
        timestamp = datetime.now().strftime("%H:%M:%S")
        filename = os.path.basename(file_path)
        display_target = target_char if target_char else "(空)"
        record_text = f"{timestamp} | {filename} | 替换半角空格: ' ' -> '{display_target}' ({count}处)"
        
        # 添加到全局历史记录
        self.replacement_history.append({
            'timestamp': timestamp,
            'file': file_path,
            'filename': filename,
            'find': '半角空格',
            'replace': display_target,
            'count': count,
            'all': True,
            'content_before': content,
            'content_after': new_content,
            'record_text': record_text
        })
        
        # 添加到文件历史记录
        file_data['history'].append({
            'timestamp': timestamp,
            'find': '半角空格',
            'replace': display_target,
            'count': count,
            'all': True
        })
        
        # 如果是当前文件，更新显示
        if file_path == self.current_file:
            self.display_file_content(file_path)
        
        # 更新文件下拉框
        self.update_file_dropdown()
        
        # 更新替换记录显示
        self.update_history_display()
        
        return count
    # ---------- 新增功能结束 ----------
    
    def update_history_display(self):
        """更新替换记录显示"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete(1.0, tk.END)
        
        if not self.replacement_history:
            self.history_text.insert(tk.END, "暂无替换记录\n")
        else:
            # 显示所有替换记录，最新的在前面
            for record in reversed(self.replacement_history[-100:]):  # 限制显示最近100条记录
                self.history_text.insert(tk.END, record['record_text'] + "\n")
        
        self.history_text.config(state=tk.DISABLED)
        # 滚动到顶部
        self.history_text.see(1.0)
    
    def clear_history(self):
        """清空替换记录"""
        if not self.replacement_history:
            return
            
        if messagebox.askyesno("确认清空", "确定要清空所有替换记录吗？"):
            self.replacement_history = []
            self.update_history_display()
            self.update_status("替换记录已清空")
    
    def export_history(self):
        """导出替换记录"""
        if not self.replacement_history:
            messagebox.showwarning("警告", "没有替换记录可以导出")
            return
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            title="保存替换记录",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write("批量文本替换工具 - 替换记录\n")
                    file.write("=" * 50 + "\n\n")
                    
                    for record in self.replacement_history:
                        file.write(record['record_text'] + "\n")
                
                self.update_status(f"替换记录已导出到: {os.path.basename(file_path)}")
                messagebox.showinfo("导出成功", "替换记录已成功导出")
                
            except Exception as e:
                messagebox.showerror("错误", f"无法导出记录: {str(e)}")
    
    def update_status(self, message):
        """更新状态栏"""
        self.status_bar.config(text=message)
        
        # 5秒后恢复默认状态
        if self.open_files:
            file_count = len(self.open_files)
            modified_count = sum(1 for f in self.open_files.values() if f['modified'])
            default_status = f"已打开 {file_count} 个文件，{modified_count} 个有未保存的修改"
        else:
            default_status = "就绪"
            
        self.root.after(5000, lambda: self.status_bar.config(text=default_status))

def main():
    root = tk.Tk()
    app = TextReplacementTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()