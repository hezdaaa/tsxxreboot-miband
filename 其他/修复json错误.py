import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import re
import os
from collections import OrderedDict
import copy

class JSONChecker:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON脚本检查修复工具 v2.0")
        self.root.geometry("1400x1000")
        
        # 颜色定义
        self.colors = {
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "info": "#2196F3"
        }
        
        # 标准字段顺序（与你的JSON匹配）
        self.standard_order = ["b", "c", "s", "t"]
        
        self.setup_ui()
        
    def setup_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="游戏脚本JSON检查修复工具", 
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # 控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 左侧按钮组
        left_btn_frame = ttk.Frame(control_frame)
        left_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 右侧按钮组
        right_btn_frame = ttk.Frame(control_frame)
        right_btn_frame.pack(side=tk.RIGHT, fill=tk.X)
        
        # 文件操作按钮
        ttk.Button(left_btn_frame, text="打开文件", command=self.open_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_btn_frame, text="保存结果", command=self.save_file).pack(side=tk.LEFT, padx=(0, 5))
        
        # 检查按钮
        ttk.Button(left_btn_frame, text="详细检查", command=self.detailed_check,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 5))
        
        # 修复按钮
        ttk.Button(left_btn_frame, text="自动修复", command=self.auto_fix).pack(side=tk.LEFT, padx=(0, 5))
        
        # 统计信息
        self.stats_var = tk.StringVar(value="就绪 - 0 条目")
        stats_label = ttk.Label(right_btn_frame, textvariable=self.stats_var)
        stats_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 检查选项框架
        options_frame = ttk.LabelFrame(main_frame, text="检查选项", padding="10")
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 检查选项
        self.var_fix_commas = tk.BooleanVar(value=True)
        self.var_fix_order = tk.BooleanVar(value=True)
        self.var_fix_quotes = tk.BooleanVar(value=True)
        self.var_fix_missing = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(options_frame, text="修复逗号问题", variable=self.var_fix_commas).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Checkbutton(options_frame, text="统一字段顺序", variable=self.var_fix_order).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Checkbutton(options_frame, text="修复引号问题", variable=self.var_fix_quotes).grid(row=0, column=2, sticky=tk.W, padx=(0, 20))
        ttk.Checkbutton(options_frame, text="修复缺失字段", variable=self.var_fix_missing).grid(row=0, column=3, sticky=tk.W)
        
        # 创建Notebook（选项卡）
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 输入标签页
        input_frame = ttk.Frame(notebook)
        notebook.add(input_frame, text="原始内容")
        
        # 输出标签页
        output_frame = ttk.Frame(notebook)
        notebook.add(output_frame, text="修复后内容")
        
        # 输入文本框
        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.NONE, 
                                                   font=("Consolas", 10))
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 输出文本框
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.NONE,
                                                    font=("Consolas", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 错误信息区域
        error_frame = ttk.LabelFrame(main_frame, text="检查结果", padding="10")
        error_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 错误信息文本框
        self.error_text = scrolledtext.ScrolledText(error_frame, height=10, wrap=tk.WORD,
                                                   font=("Arial", 9))
        self.error_text.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 配置标签页权重
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # 加载示例数据
        self.load_example()
        
        # 配置文本高亮标签
        self.setup_highlight_tags()
    
    def setup_highlight_tags(self):
        """设置文本高亮标签"""
        self.input_text.tag_config("error", background="#ffdddd", foreground="#cc0000")
        self.input_text.tag_config("warning", background="#fff3cd", foreground="#856404")
        self.input_text.tag_config("info", background="#d1ecf1", foreground="#0c5460")
        self.input_text.tag_config("success", background="#d4edda", foreground="#155724")
        
        self.output_text.tag_config("modified", background="#e7f3fe", foreground="#0d6efd")
    
    def clear_all(self):
        """清除所有文本框内容"""
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.error_text.delete("1.0", tk.END)
        self.status_var.set("已清除所有内容")
        self.stats_var.set("就绪 - 0 条目")
        
        # 清除高亮
        self.input_text.tag_remove("error", "1.0", tk.END)
        self.input_text.tag_remove("warning", "1.0", tk.END)
        self.input_text.tag_remove("info", "1.0", tk.END)
    
    def load_example(self):
        """加载示例数据"""
        try:
            with open("scriptData12(2).txt", "r", encoding="utf-8") as f:
                example_data = f.read()
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", example_data)
                self.status_var.set("已加载示例文件")
                self.update_stats()
        except FileNotFoundError:
            # 如果没有文件，加载内置示例
            example_data = '''{
  "5501": {
    "b": "bcgi/画面_黒",
    "s": "",
    "t": "那优花负责的是吉他。同时也负责作曲。"
  },
  "5502": {
    "b": "bcgi/画面_黒",
    "s": "",
    "t": "从我妈那里听说，她从学校毕业后，在服装行业工作……但不知什么时候，她辞职了。"
  }
}'''
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", example_data)
            self.status_var.set("已加载内置示例")
            self.update_stats()
    
    def open_file(self):
        """打开文件"""
        file_path = filedialog.askopenfilename(
            title="选择JSON文件",
            filetypes=[
                ("JSON文件", "*.json"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.input_text.delete("1.0", tk.END)
                    self.input_text.insert("1.0", content)
                    self.status_var.set(f"已加载: {os.path.basename(file_path)}")
                    self.update_stats()
            except Exception as e:
                messagebox.showerror("打开错误", f"无法打开文件:\n{str(e)}")
    
    def save_file(self):
        """保存结果"""
        content = self.output_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("保存警告", "输出内容为空")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="保存修复后的文件",
            defaultextension=".json",
            filetypes=[
                ("JSON文件", "*.json"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("保存成功", f"文件已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("保存错误", f"无法保存文件:\n{str(e)}")
    
    def update_stats(self):
        """更新统计信息"""
        content = self.input_text.get("1.0", tk.END).strip()
        if not content:
            self.stats_var.set("就绪 - 0 条目")
            return
            
        try:
            data = json.loads(content)
            count = len(data)
            self.stats_var.set(f"就绪 - {count} 条目")
        except:
            self.stats_var.set("就绪 - 格式错误")
    
    def validate_json(self, text):
        """验证JSON格式"""
        try:
            data = json.loads(text)
            return True, data, None
        except json.JSONDecodeError as e:
            return False, None, e
    
    def detailed_check(self):
        """详细检查JSON内容"""
        input_data = self.input_text.get("1.0", tk.END).strip()
        
        if not input_data:
            messagebox.showwarning("警告", "请输入要检查的内容")
            return
        
        # 清空输出和错误区域
        self.output_text.delete("1.0", tk.END)
        self.error_text.delete("1.0", tk.END)
        
        # 清除高亮
        self.input_text.tag_remove("error", "1.0", tk.END)
        self.input_text.tag_remove("warning", "1.0", tk.END)
        self.input_text.tag_remove("info", "1.0", tk.END)
        
        # 验证JSON格式
        is_valid, data, json_error = self.validate_json(input_data)
        
        if not is_valid:
            self.display_json_error(json_error, input_data)
            return
        
        # 执行详细检查
        results = self.perform_detailed_checks(data, input_data)
        
        # 显示检查结果
        self.display_check_results(results)
        
        # 在输入文本中高亮问题
        self.highlight_issues_in_input(results, input_data)
    
    def perform_detailed_checks(self, data, original_text):
        """执行详细的JSON检查"""
        results = {
            "errors": [],
            "warnings": [],
            "infos": [],
            "stats": {
                "total_entries": len(data),
                "with_background": 0,
                "with_character": 0,
                "with_speaker": 0,
                "with_text": 0,
                "field_order_issues": 0,
                "empty_fields": 0
            }
        }
        
        lines = original_text.split('\n')
        
        # 检查每个条目
        for key, value in data.items():
            # 统计字段存在情况
            if "b" in value and value["b"]:
                results["stats"]["with_background"] += 1
            if "c" in value:
                results["stats"]["with_character"] += 1
            if "s" in value:
                results["stats"]["with_speaker"] += 1
            if "t" in value:
                results["stats"]["with_text"] += 1
            
            # 检查字段顺序
            if list(value.keys()) != self.standard_order:
                results["stats"]["field_order_issues"] += 1
                results["warnings"].append({
                    "type": "field_order",
                    "key": key,
                    "description": f"条目 {key}: 字段顺序不正确",
                    "current_order": list(value.keys()),
                    "suggested_order": self.standard_order
                })
            
            # 检查空字段
            for field, field_value in value.items():
                if field_value == "":
                    results["stats"]["empty_fields"] += 1
                    results["infos"].append({
                        "type": "empty_field",
                        "key": key,
                        "field": field,
                        "description": f"条目 {key}: 字段 '{field}' 为空"
                    })
            
            # 检查路径格式
            if "b" in value and value["b"]:
                bg_path = value["b"]
                if not (bg_path.startswith("bcgi/") or bg_path == ""):
                    results["warnings"].append({
                        "type": "path_format",
                        "key": key,
                        "field": "b",
                        "value": bg_path,
                        "description": f"条目 {key}: 背景路径格式异常: {bg_path}",
                        "suggestion": "应为 bcgi/ 开头或为空"
                    })
            
            if "c" in value and value["c"]:
                char_path = value["c"]
                if not (char_path.startswith("cimg/") or char_path.startswith("evig/")):
                    results["warnings"].append({
                        "type": "path_format",
                        "key": key,
                        "field": "c",
                        "value": char_path,
                        "description": f"条目 {key}: 角色图片路径格式异常: {char_path}",
                        "suggestion": "应为 cimg/ 或 evig/ 开头"
                    })
        
        # 检查键的连续性
        keys = list(data.keys())
        if keys:
            try:
                numeric_keys = [int(k) for k in keys]
                numeric_keys.sort()
                expected_keys = list(range(numeric_keys[0], numeric_keys[-1] + 1))
                missing_keys = [k for k in expected_keys if str(k) not in keys]
                
                if missing_keys:
                    results["warnings"].append({
                        "type": "missing_keys",
                        "description": f"发现 {len(missing_keys)} 个缺失的键",
                        "missing_keys": missing_keys[:10],  # 只显示前10个
                        "total_missing": len(missing_keys)
                    })
            except ValueError:
                pass
        
        return results
    
    def display_json_error(self, error, text):
        """显示JSON格式错误"""
        error_msg = f"❌ JSON格式错误:\n\n"
        error_msg += f"错误位置: 第 {error.lineno} 行, 第 {error.colno} 列\n"
        error_msg += f"错误信息: {error.msg}\n\n"
        
        # 显示错误上下文
        lines = text.split('\n')
        start_line = max(0, error.lineno - 3)
        end_line = min(len(lines), error.lineno + 2)
        
        error_msg += "错误上下文:\n"
        for i in range(start_line, end_line):
            line_num = i + 1
            prefix = ">>> " if line_num == error.lineno else "    "
            error_msg += f"{prefix}{line_num:4d}: {lines[i]}\n"
        
        self.error_text.delete("1.0", tk.END)
        self.error_text.insert("1.0", error_msg)
        
        # 高亮错误行
        self.highlight_error_line(error.lineno - 1)
        
        self.status_var.set("JSON格式错误")
        self.stats_var.set("格式错误")
    
    def highlight_error_line(self, line_index):
        """高亮错误行"""
        start_pos = f"{line_index + 1}.0"
        end_pos = f"{line_index + 2}.0"
        self.input_text.tag_add("error", start_pos, end_pos)
        self.input_text.see(start_pos)
    
    def highlight_issues_in_input(self, results, text):
        """在输入文本中高亮问题"""
        lines = text.split('\n')
        
        # 高亮警告
        for warning in results["warnings"]:
            if "key" in warning:
                key = warning["key"]
                # 查找键所在行
                for i, line in enumerate(lines):
                    if f'"{key}"' in line:
                        start_pos = f"{i + 1}.0"
                        end_pos = f"{i + 2}.0"
                        self.input_text.tag_add("warning", start_pos, end_pos)
                        break
        
        # 高亮信息
        for info in results["infos"]:
            if "key" in info:
                key = info["key"]
                for i, line in enumerate(lines):
                    if f'"{key}"' in line:
                        start_pos = f"{i + 1}.0"
                        end_pos = f"{i + 2}.0"
                        self.input_text.tag_add("info", start_pos, end_pos)
                        break
    
    def display_check_results(self, results):
        """显示检查结果"""
        output = "🔍 JSON详细检查报告\n"
        output += "=" * 50 + "\n\n"
        
        # 统计信息
        stats = results["stats"]
        output += "📊 统计信息:\n"
        output += f"  总条目数: {stats['total_entries']}\n"
        output += f"  有背景图的条目: {stats['with_background']}\n"
        output += f"  有角色图片的条目: {stats['with_character']}\n"
        output += f"  有说话者的条目: {stats['with_speaker']}\n"
        output += f"  有文本的条目: {stats['with_text']}\n"
        output += f"  字段顺序问题: {stats['field_order_issues']}\n"
        output += f"  空字段数: {stats['empty_fields']}\n\n"
        
        # 错误
        if results["errors"]:
            output += "❌ 错误:\n"
            for error in results["errors"]:
                output += f"  • {error['description']}\n"
            output += "\n"
        
        # 警告
        if results["warnings"]:
            output += "⚠️ 警告:\n"
            for warning in results["warnings"]:
                output += f"  • {warning['description']}\n"
                if "suggestion" in warning:
                    output += f"    建议: {warning['suggestion']}\n"
            output += "\n"
        
        # 信息
        if results["infos"]:
            output += "ℹ️ 信息:\n"
            for info in results["infos"]:
                output += f"  • {info['description']}\n"
            output += "\n"
        
        # 总体评估
        if not results["errors"] and not results["warnings"]:
            output += "✅ JSON格式良好，未发现问题！\n"
            self.status_var.set("检查完成 - 无问题")
        elif not results["errors"]:
            output += "⚠️ 发现一些警告，但JSON格式正确\n"
            self.status_var.set(f"检查完成 - {len(results['warnings'])} 个警告")
        else:
            output += "❌ 发现错误，需要修复\n"
            self.status_var.set(f"检查完成 - {len(results['errors'])} 个错误")
        
        self.error_text.delete("1.0", tk.END)
        self.error_text.insert("1.0", output)
        
        # 复制原始数据到输出框（未修复）
        input_data = self.input_text.get("1.0", tk.END).strip()
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", input_data)
        
        # 更新统计
        total_issues = len(results["errors"]) + len(results["warnings"])
        self.stats_var.set(f"检查完成 - {total_issues} 个问题")
    
    def auto_fix(self):
        """自动修复JSON问题"""
        input_data = self.input_text.get("1.0", tk.END).strip()
        
        if not input_data:
            messagebox.showwarning("警告", "请输入要修复的内容")
            return
        
        # 清空输出和错误区域
        self.output_text.delete("1.0", tk.END)
        self.error_text.delete("1.0", tk.END)
        
        # 验证JSON格式
        is_valid, data, json_error = self.validate_json(input_data)
        
        if not is_valid:
            # 先尝试修复JSON语法
            fixed_text = self.fix_json_syntax(input_data)
            try:
                data = json.loads(fixed_text)
                is_valid = True
            except:
                messagebox.showerror("修复失败", "无法修复JSON语法错误")
                return
        
        if not is_valid:
            messagebox.showerror("JSON格式错误", f"JSON解析失败:\n{str(json_error)}")
            return
        
        # 执行修复
        fixed_data = self.perform_fixes(data)
        
        # 格式化输出
        formatted_output = json.dumps(fixed_data, ensure_ascii=False, indent=2)
        
        # 显示结果
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", formatted_output)
        
        # 显示修复报告
        self.show_fix_report(data, fixed_data)
        
        self.status_var.set("自动修复完成")
        self.stats_var.set("修复完成")
        
        # 高亮修改的部分（简单实现）
        self.highlight_changes_in_output(formatted_output, input_data)
    
    def fix_json_syntax(self, text):
        """修复JSON语法错误"""
        fixes_applied = []
        lines = text.split('\n')
        
        # 修复1: 缺少逗号的情况
        for i in range(len(lines)):
            line = lines[i]
            # 查找模式: 属性值后直接跟另一个属性（缺少逗号）
            pattern = r'("[^"]*"\s*:\s*"[^"]*")\s+"[^"]*"\s*:'
            match = re.search(pattern, line)
            if match:
                replacement = match.group(1) + ', "' + line[match.end():match.end()+line[match.end():].find('"')+1] + '"'
                new_line = line[:match.start()] + replacement + line[match.end()+line[match.end():].find('"')+1:]
                lines[i] = new_line
                fixes_applied.append(f"第{i+1}行: 修复缺少逗号")
        
        # 修复2: 多余逗号
        for i in range(len(lines)):
            if ',,' in lines[i]:
                lines[i] = lines[i].replace(',,', ',')
                fixes_applied.append(f"第{i+1}行: 移除多余逗号")
        
        fixed_text = '\n'.join(lines)
        
        # 记录修复
        if fixes_applied:
            self.error_text.insert("1.0", "🔧 语法修复:\n")
            for fix in fixes_applied:
                self.error_text.insert(tk.END, f"  • {fix}\n")
            self.error_text.insert(tk.END, "\n")
        
        return fixed_text
    
    def perform_fixes(self, data):
        """执行各种修复"""
        fixed_data = OrderedDict()
        fixes_applied = []
        
        # 按键排序
        try:
            sorted_keys = sorted(data.keys(), key=lambda x: int(x))
        except:
            sorted_keys = sorted(data.keys())
        
        for key in sorted_keys:
            original = data[key]
            fixed = copy.deepcopy(original)
            
            # 修复1: 统一字段顺序
            if self.var_fix_order.get():
                ordered_item = OrderedDict()
                # 按标准顺序添加字段
                for field in self.standard_order:
                    if field in fixed:
                        ordered_item[field] = fixed[field]
                # 添加其他字段
                for field in fixed:
                    if field not in self.standard_order:
                        ordered_item[field] = fixed[field]
                
                if list(original.keys()) != list(ordered_item.keys()):
                    fixed = ordered_item
                    fixes_applied.append(f"{key}: 统一字段顺序")
            
            # 修复2: 修复引号问题
            if self.var_fix_quotes.get():
                for field, value in fixed.items():
                    if isinstance(value, str):
                        # 修复不匹配的引号
                        if value.startswith('「') and not value.endswith('」'):
                            fixed[field] = value + '」'
                            fixes_applied.append(f"{key}.{field}: 修复引号")
                        elif value.startswith('"') and not value.endswith('"'):
                            fixed[field] = value + '"'
                            fixes_applied.append(f"{key}.{field}: 修复引号")
            
            # 修复3: 修复缺失字段（仅添加空字段）
            if self.var_fix_missing.get():
                for field in self.standard_order:
                    if field not in fixed:
                        fixed[field] = ""
                        fixes_applied.append(f"{key}: 添加缺失字段 '{field}'")
            
            fixed_data[key] = fixed
        
        # 显示修复报告
        if fixes_applied:
            report = "🔧 内容修复:\n"
            for fix in fixes_applied:
                report += f"  • {fix}\n"
            self.error_text.insert("1.0", report + "\n")
        
        return fixed_data
    
    def show_fix_report(self, original_data, fixed_data):
        """显示修复报告"""
        report = "📋 修复报告:\n"
        report += "=" * 40 + "\n\n"
        
        # 统计变化
        changes = 0
        for key in fixed_data:
            if key in original_data:
                if original_data[key] != fixed_data[key]:
                    changes += 1
        
        report += f"修复条目数: {changes}/{len(fixed_data)}\n"
        report += f"总条目数: {len(fixed_data)}\n"
        
        if changes == 0:
            report += "\n✅ 无需修复，数据已正确\n"
        else:
            report += f"\n🔧 已修复 {changes} 个条目\n"
        
        self.error_text.insert("1.0", report)
    
    def highlight_changes_in_output(self, fixed_text, original_text):
        """在输出中高亮修改的部分（简化版）"""
        # 简单的行比较
        original_lines = original_text.split('\n')
        fixed_lines = fixed_text.split('\n')
        
        self.output_text.tag_remove("modified", "1.0", tk.END)
        
        for i, (orig_line, fixed_line) in enumerate(zip(original_lines, fixed_lines)):
            if orig_line != fixed_line:
                start_pos = f"{i+1}.0"
                end_pos = f"{i+2}.0"
                self.output_text.tag_add("modified", start_pos, end_pos)

def main():
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    # 配置强调按钮样式
    style.configure('Accent.TButton', 
                   font=('Arial', 10, 'bold'),
                   padding=6)
    
    app = JSONChecker(root)
    root.mainloop()

if __name__ == "__main__":
    main()