import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import sys
import io
import re
import threading
import time
import copy
from PIL import Image, ImageTk, ImageDraw


class GalGameScriptEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Galgame剧本编辑器 - 黑色主题增强版")
        self.root.geometry("1800x1000")

        # 设置黑色主题
        self.setup_dark_theme()

        # 当前编辑状态
        self.current_progress = 1
        self.script_data = {}
        self.total_dialogues = 0
        self.sorted_ids = []

        # 资源路径
        self.project_path = ""
        self.script_path = ""
        self.evig_path = ""
        self.cimg_path = ""
        self.bcgi_path = ""

        # 立绘分类数据
        self.persons = set()
        self.clothes = set()
        self.poses = set()
        self.character_map = {}

        # 缩放模板数据（存储模式值）
        self.xyz_templates = {}
        self.template_file = "xyz_templates.json"

        # 自动保存相关
        self.auto_save_enabled = True
        self.auto_save_interval = 60
        self.last_save_time = time.time()
        self.unsaved_changes = False
        self.auto_save_thread = None

        # 撤销/重做系统
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo_steps = 50
        self.current_state = None

        # 图片缓存
        self.image_cache = {}
        self.max_cache_size = 50

        # 性能优化
        self.update_preview_delay = 100
        self.preview_update_job = None
        self.json_update_job = None

        # 对话列表设置
        self.max_display_dialogues = 2000
        self.dialogue_list_loaded = False
        self.batch_size = 500
        self.all_dialogue_ids = None
        self.filtered_dialogues = []
        self.current_page = 1
        self.total_pages = 1
        self.performance_mode = False

        # 加载标记
        self.is_loading_dialogue = False
        self.is_applying_to_json = False

        # 快捷指令框数据
        self.nearby_characters = []

        # 预览图像缓存
        self.preview_images = {
            'bg': None,
            'char': None,
            'cg': None
        }

        # 块大小配置
        self.chunk_size = 500

        # 缩放模式配置（模式 → 实际倍数）
        self.zoom_modes = {1: 0.8, 2: 1.2}  # 1:小, 2:大

        # 记忆上次选中的资源
        self.last_selected_cg = ""
        self.last_selected_character = ""
        self.last_selected_background = ""

        # ---------- 新增：CG扩展名缓存 ----------
        self.cg_ext_cache = {}   # 缓存 {name_without_ext: full_name_with_ext}

        # ---------- 新增：选项字段变量（5个）----------
        self.co_var = tk.BooleanVar(value=False)
        self.c1_var = tk.StringVar()
        self.c2_var = tk.StringVar()
        self.c3_var = tk.StringVar()
        self.c4_var = tk.StringVar()
        self.c5_var = tk.StringVar()
        self.c1t_var = tk.StringVar()
        self.c2t_var = tk.StringVar()
        self.c3t_var = tk.StringVar()
        self.c4t_var = tk.StringVar()
        self.c5t_var = tk.StringVar()

        # 创建界面
        self.create_menu()
        self.create_widgets()

        # 加载缩放模板
        self.load_xyz_templates()

        # 绑定快捷键
        self.bind_shortcuts()

        # 启动自动保存线程
        self.start_auto_save()

    # ---------- 新增：为CG名自动添加正确的后缀 ----------
    def fix_background_suffixes(self):
        """一键移除所有背景字段中的文件扩展名（如 .jpg、.png）"""
        if not self.script_data:
            messagebox.showwarning("警告", "没有加载任何对话数据！")
            return

        extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        fixed_count = 0
        for key, script in self.script_data.items():
            if 'b' in script and script['b']:
                original = script['b']
                base = os.path.splitext(original)[0]
                if base != original:
                    script['b'] = base
                    fixed_count += 1

        if fixed_count == 0:
            messagebox.showinfo("修复完成", "没有发现需要修复的背景字段。")
            return

        self.load_dialogue()
        self.mark_unsaved_changes()

        if messagebox.askyesno("保存", f"已修复 {fixed_count} 个背景字段。\n是否立即保存所有更改？"):
            self.save_all_changes()
            self.status_label.config(text=f"已修复并保存 {fixed_count} 个背景后缀", foreground="#6a9955")
        else:
            self.status_label.config(text=f"已修复 {fixed_count} 个背景后缀（未保存）", foreground="#ffcc00")

    def ensure_cg_suffix(self, cg_name):
        if not cg_name:
            return cg_name
        if cg_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            return cg_name
        if cg_name in self.cg_ext_cache:
            return self.cg_ext_cache[cg_name]
        if not self.evig_path or not os.path.exists(self.evig_path):
            return cg_name
        png_path = os.path.join(self.evig_path, cg_name + '.png')
        if os.path.exists(png_path):
            result = cg_name + '.png'
            self.cg_ext_cache[cg_name] = result
            return result
        jpg_path = os.path.join(self.evig_path, cg_name + '.jpg')
        if os.path.exists(jpg_path):
            result = cg_name + '.jpg'
            self.cg_ext_cache[cg_name] = result
            return result
        for ext in ['.jpeg', '.gif', '.bmp']:
            test_path = os.path.join(self.evig_path, cg_name + ext)
            if os.path.exists(test_path):
                result = cg_name + ext
                self.cg_ext_cache[cg_name] = result
                return result
        return cg_name

    def setup_dark_theme(self):
        self.root.configure(bg='#1e1e1e')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#1e1e1e', foreground='#d4d4d4', fieldbackground='#252526',
                        insertcolor='#d4d4d4', selectbackground='#264f78', selectforeground='#d4d4d4',
                        troughcolor='#3c3c3c')
        style.configure('TButton', background='#333333', foreground='#d4d4d4', borderwidth=1,
                        focusthickness=3, focuscolor='none')
        style.map('TButton', background=[('active', '#555555'), ('pressed', '#444444')],
                  foreground=[('active', '#ffffff')])
        style.configure('TLabel', background='#1e1e1e', foreground='#d4d4d4')
        style.configure('TLabelframe', background='#1e1e1e', foreground='#d4d4d4',
                        bordercolor='#555555', borderwidth=1)
        style.configure('TLabelframe.Label', background='#1e1e1e', foreground='#569cd6')
        style.configure('TEntry', fieldbackground='#252526', foreground='#d4d4d4',
                        insertcolor='#d4d4d4', bordercolor='#555555')
        style.configure('TCombobox', fieldbackground='#252526', foreground='#d4d4d4',
                        selectbackground='#264f78', bordercolor='#555555')
        style.configure('Vertical.TScrollbar', background='#3c3c3c', troughcolor='#1e1e1e',
                        bordercolor='#1e1e1e', arrowcolor='#d4d4d4')
        style.configure('Horizontal.TScrollbar', background='#3c3c3c', troughcolor='#1e1e1e',
                        bordercolor='#1e1e1e', arrowcolor='#d4d4d4')
        style.configure('TNotebook', background='#1e1e1e', tabbackground='#333333',
                        tabforeground='#d4d4d4', bordercolor='#555555')
        style.configure('TNotebook.Tab', background='#333333', foreground='#d4d4d4',
                        padding=[10, 5], bordercolor='#555555')
        style.map('TNotebook.Tab', background=[('selected', '#1e1e1e'), ('active', '#555555')],
                  foreground=[('selected', '#569cd6')])
        style.configure('TSpinbox', fieldbackground='#252526', foreground='#d4d4d4',
                        bordercolor='#555555')

    def create_menu(self):
        menubar = tk.Menu(self.root, bg='#252526', fg='#d4d4d4', activebackground='#555555',
                          activeforeground='#ffffff')
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0, bg='#252526', fg='#d4d4d4',
                            activebackground='#555555', activeforeground='#ffffff')
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开项目文件夹", command=self.open_project_folder)
        file_menu.add_command(label="打开脚本文件夹", command=self.open_script_folder)
        file_menu.add_separator()
        file_menu.add_command(label="保存当前对话", command=self.save_current)
        file_menu.add_command(label="保存所有更改", command=self.save_all_changes)
        file_menu.add_separator()
        file_menu.add_command(label="性能模式", command=self.toggle_performance_mode)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_editor)
        edit_menu = tk.Menu(menubar, tearoff=0, bg='#252526', fg='#d4d4d4',
                            activebackground='#555555', activeforeground='#ffffff')
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="添加对话", command=self.add_dialogue)
        edit_menu.add_command(label="插入对话", command=self.insert_dialogue_before_current)
        edit_menu.add_command(label="删除当前对话", command=self.delete_dialogue)
        edit_menu.add_separator()
        edit_menu.add_command(label="撤销 (Ctrl+Z)", command=self.undo)
        edit_menu.add_command(label="重做 (Ctrl+Y)", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="解析立绘名", command=self.parse_character_name)
        edit_menu.add_command(label="拼接立绘名", command=self.generate_character_name)
        edit_menu.add_separator()
        edit_menu.add_command(label="复制上一页立绘和CG (Ctrl+P)", command=self.copy_previous_character_and_cg)
        tool_menu = tk.Menu(menubar, tearoff=0, bg='#252526', fg='#d4d4d4',
                            activebackground='#555555', activeforeground='#ffffff')
        menubar.add_cascade(label="工具", menu=tool_menu)
        tool_menu.add_command(label="一键优化储存", command=self.optimize_storage)
        tool_menu.add_command(label="批量重命名", command=self.batch_rename)
        tool_menu.add_command(label="修复背景后缀", command=self.fix_background_suffixes)
        tool_menu.add_command(label="导出脚本", command=self.export_script)
        tool_menu.add_command(label="导入脚本", command=self.import_script)
        tool_menu.add_separator()
        tool_menu.add_command(label="重新扫描资源", command=self.rescan_resources)
        tool_menu.add_command(label="清理图片缓存", command=self.clear_image_cache)
        # 新增：全局搜索菜单项
        tool_menu.add_command(label="全局搜索 (JSON内容)", command=self.open_global_search)

    def toggle_performance_mode(self):
        self.performance_mode = not self.performance_mode
        if self.performance_mode:
            self.max_display_dialogues = 1000
            self.batch_size = 200
            self.update_preview_delay = 200
            self.performance_indicator.config(text="[性能模式]", foreground="#ffcc00")
            messagebox.showinfo("性能模式", "已启用性能模式，减少内存使用和CPU占用")
        else:
            self.max_display_dialogues = 2000
            self.batch_size = 500
            self.update_preview_delay = 100
            self.performance_indicator.config(text="[正常模式]", foreground="#569cd6")
            messagebox.showinfo("性能模式", "已禁用性能模式")
        if hasattr(self, 'all_dialogue_ids') and self.all_dialogue_ids:
            self._update_pagination_and_display()

    def bind_shortcuts(self):
        self.root.bind('<Control-a>', lambda e: self.auto_save_and_prev())
        self.root.bind('<Control-A>', lambda e: self.auto_save_and_prev())
        self.root.bind('<Control-d>', lambda e: self.auto_save_and_next())
        self.root.bind('<Control-D>', lambda e: self.auto_save_and_next())
        self.root.bind('<Control-s>', lambda e: self.ctrl_s_save())
        self.root.bind('<Control-S>', lambda e: self.ctrl_s_save())
        self.root.bind('<Control-p>', lambda e: self.copy_previous_character_and_cg())
        self.root.bind('<Control-P>', lambda e: self.copy_previous_character_and_cg())
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-Z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-Y>', lambda e: self.redo())
        self.root.bind('<Control-Tab>', lambda e: self.next_tab())

    def next_tab(self):
        notebook = self.left_notebook
        current = notebook.index(notebook.select())
        next_tab = (current + 1) % notebook.index("end")
        notebook.select(next_tab)

    def create_widgets(self):
        control_frame = ttk.LabelFrame(self.root, text="控制面板", padding="10")
        control_frame.pack(fill="x", padx=10, pady=5)
        path_frame = ttk.Frame(control_frame)
        path_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(path_frame, text="项目路径:").pack(side="left", padx=5)
        self.project_label = ttk.Label(path_frame, text="未加载项目", foreground="#569cd6")
        self.project_label.pack(side="left", padx=5)
        self.status_label = ttk.Label(path_frame, text="就绪", foreground="#6a9955")
        self.status_label.pack(side="right", padx=10)
        self.performance_indicator = ttk.Label(path_frame, text="[正常模式]", foreground="#569cd6")
        self.performance_indicator.pack(side="right", padx=5)
        nav_frame = ttk.Frame(control_frame)
        nav_frame.pack(fill="x", pady=5)
        ttk.Label(nav_frame, text="对话编号:").pack(side="left", padx=5)
        self.progress_var = tk.IntVar(value=1)
        self.progress_spinbox = ttk.Spinbox(nav_frame, from_=1, to=1000000,
                                            textvariable=self.progress_var, width=10)
        self.progress_spinbox.pack(side="left", padx=5)
        self.progress_spinbox.bind('<Return>', lambda e: self.load_dialogue())
        ttk.Button(nav_frame, text="跳转", command=self.load_dialogue).pack(side="left", padx=5)
        ttk.Button(nav_frame, text="<< 上一个 (Ctrl+A)", command=self.auto_save_and_prev).pack(side="left", padx=2)
        ttk.Button(nav_frame, text="下一个 (Ctrl+D) >>", command=self.auto_save_and_next).pack(side="left", padx=2)
        ttk.Label(nav_frame,
                  text="快捷键: Ctrl+A/D=上下对话, Ctrl+S=保存, Ctrl+Z/Y=撤销重做, Ctrl+P=复制立绘CG").pack(side="left", padx=20)
        self.total_label = ttk.Label(nav_frame, text="总对话数: 0")
        self.total_label.pack(side="left", padx=20)
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill="x", pady=5)
        ttk.Button(button_frame, text="保存当前 (Ctrl+S)", command=self.save_current).pack(side="left", padx=5)
        ttk.Button(button_frame, text="保存并下一条", command=self.save_and_next).pack(side="left", padx=5)
        ttk.Button(button_frame, text="添加对话", command=self.add_dialogue).pack(side="left", padx=5)
        ttk.Button(button_frame, text="插入对话", command=self.insert_dialogue_before_current).pack(side="left", padx=5)
        ttk.Button(button_frame, text="删除对话", command=self.delete_dialogue).pack(side="left", padx=5)
        ttk.Button(button_frame, text="复制上一页 (Ctrl+P)", command=self.copy_previous_character_and_cg).pack(
            side="left", padx=5)
        ttk.Button(button_frame, text="优化储存", command=self.optimize_storage).pack(side="left", padx=5)
        ttk.Button(button_frame, text="重新加载", command=self.reload_project).pack(side="left", padx=5)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.left_notebook = ttk.Notebook(left_frame)
        self.left_notebook.pack(fill="both", expand=True)
        json_frame = ttk.Frame(self.left_notebook)
        self.left_notebook.add(json_frame, text="JSON源码编辑")
        # 为JSON源码区域添加自定义字段工具栏
        json_toolbar = ttk.Frame(json_frame)
        json_toolbar.pack(fill="x", padx=5, pady=5)
        ttk.Label(json_toolbar, text="自定义字段:").pack(side="left", padx=5)
        self.custom_key_var = tk.StringVar()
        custom_key_entry = ttk.Entry(json_toolbar, textvariable=self.custom_key_var, width=12)
        custom_key_entry.pack(side="left", padx=5)
        ttk.Label(json_toolbar, text="值:").pack(side="left", padx=5)
        self.custom_value_var = tk.StringVar()
        custom_value_entry = ttk.Entry(json_toolbar, textvariable=self.custom_value_var, width=20)
        custom_value_entry.pack(side="left", padx=5)
        ttk.Button(json_toolbar, text="添加/更新字段", command=self.add_custom_field).pack(side="left", padx=5)

        self.source_text = scrolledtext.ScrolledText(json_frame, font=("Consolas", 9), height=30,
                                                     bg='#1e1e1e', fg='#d4d4d4', insertbackground='#d4d4d4',
                                                     selectbackground='#264f78', relief='flat')
        self.source_text.pack(fill="both", expand=True)
        list_frame = ttk.Frame(self.left_notebook)
        self.left_notebook.add(list_frame, text="对话列表")
        self.create_dialogue_list_column(list_frame)

        middle_frame = ttk.LabelFrame(main_frame, text="字段编辑", padding="10")
        middle_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.create_field_form(middle_frame)

        quick_frame = ttk.LabelFrame(main_frame, text="快捷指令", padding="10")
        quick_frame.pack(side="left", fill="both", expand=False, padx=(0, 5))
        quick_frame.config(width=250)
        self.create_quick_commands(quick_frame)

        preview_frame = ttk.LabelFrame(main_frame, text="实时预览", padding="10")
        preview_frame.pack(side="left", fill="both", expand=True)
        preview_frame.config(width=350)
        self.create_enhanced_preview_area(preview_frame)

    def create_dialogue_list_column(self, parent):
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", pady=(0, 10), padx=5)
        ttk.Label(search_frame, text="搜索:").pack(side="left", padx=5)
        self.dialogue_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.dialogue_search_var, width=20)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.filter_dialogue_list())
        pagination_frame = ttk.Frame(search_frame)
        pagination_frame.pack(side="right", padx=5)
        ttk.Button(pagination_frame, text="<<", width=2, command=lambda: self.change_page(-1)).pack(side="left", padx=1)
        self.page_label = ttk.Label(pagination_frame, text="第1页")
        self.page_label.pack(side="left", padx=2)
        ttk.Button(pagination_frame, text=">>", width=2, command=lambda: self.change_page(1)).pack(side="left", padx=1)
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.dialogue_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("微软雅黑", 9),
                                           height=25, bg='#252526', fg='#d4d4d4', selectbackground='#264f78',
                                           selectforeground='#d4d4d4', relief='flat', borderwidth=1,
                                           selectmode=tk.EXTENDED)
        self.dialogue_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.dialogue_listbox.yview)
        self.listbox_menu = tk.Menu(self.dialogue_listbox, tearoff=0, bg='#252526', fg='#d4d4d4')
        bg_menu = tk.Menu(self.listbox_menu, tearoff=0, bg='#252526', fg='#d4d4d4')
        bg_menu.add_command(label="不覆盖已有背景", command=self.batch_fill_background_no_overwrite)
        bg_menu.add_command(label="覆盖已有背景", command=self.batch_fill_background_overwrite)
        self.listbox_menu.add_cascade(label="批量填充背景", menu=bg_menu)
        cg_menu = tk.Menu(self.listbox_menu, tearoff=0, bg='#252526', fg='#d4d4d4')
        cg_menu.add_command(label="不覆盖已有CG", command=self.batch_fill_cg_no_overwrite)
        cg_menu.add_command(label="覆盖已有CG", command=self.batch_fill_cg_overwrite)
        self.listbox_menu.add_cascade(label="批量填充CG", menu=cg_menu)
        self.listbox_menu.add_separator()
        self.listbox_menu.add_command(label="删除选中对话", command=self.delete_selected_dialogues)
        self.listbox_menu.add_command(label="导出选中对话", command=self.export_selected_dialogues)
        self.dialogue_listbox.bind("<Button-3>", self.show_listbox_menu)
        self.dialogue_listbox.bind('<<ListboxSelect>>', self.on_dialogue_selected)
        self.dialogue_listbox.bind('<Double-Button-1>', self.on_dialogue_double_click)
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(0, 5), padx=5)
        ttk.Button(button_frame, text="刷新列表", command=self.update_dialogue_list_lazy, width=10).pack(side="left",
                                                                                                        padx=2)
        ttk.Button(button_frame, text="跳转到选中", command=self.jump_to_selected_dialogue, width=12).pack(side="left",
                                                                                                         padx=2)
        ttk.Button(button_frame, text="删除选中", command=self.delete_selected_dialogues, width=10).pack(side="right",
                                                                                                       padx=2)
        self.current_page = 1
        self.total_pages = 1
        self.filtered_dialogues = []

    def show_listbox_menu(self, event):
        index = self.dialogue_listbox.nearest(event.y)
        if index >= 0:
            selection = self.dialogue_listbox.curselection()
            if index not in selection:
                self.dialogue_listbox.selection_clear(0, tk.END)
                self.dialogue_listbox.selection_set(index)
            selected_count = len(self.dialogue_listbox.curselection())
            if selected_count > 0:
                self.listbox_menu.post(event.x_root, event.y_root)

    def get_selected_dialogue_ids(self):
        selected_ids = []
        for idx in self.dialogue_listbox.curselection():
            text = self.dialogue_listbox.get(idx)
            try:
                dialogue_id = int(text.split('|')[0].strip())
                selected_ids.append(dialogue_id)
            except:
                pass
        return sorted(selected_ids)

    def batch_fill_background_no_overwrite(self):
        self._batch_fill_resource_from_selection(self.bcgi_path, 'b', ['.jpg', '.jpeg', '.png', '.bmp', '.gif'],
                                                 "背景", 'last_selected_background', overwrite=False)

    def batch_fill_background_overwrite(self):
        self._batch_fill_resource_from_selection(self.bcgi_path, 'b', ['.jpg', '.jpeg', '.png', '.bmp', '.gif'],
                                                 "背景", 'last_selected_background', overwrite=True)

    def batch_fill_cg_no_overwrite(self):
        self._batch_fill_resource_from_selection(self.evig_path, 'cg', ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
                                                 "CG", 'last_selected_cg', overwrite=False)

    def batch_fill_cg_overwrite(self):
        self._batch_fill_resource_from_selection(self.evig_path, 'cg', ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
                                                 "CG", 'last_selected_cg', overwrite=True)

    def _batch_fill_resource_from_selection(self, resource_path, field_name, extensions,
                                            resource_type, memory_attr, overwrite):
        selected_ids = self.get_selected_dialogue_ids()
        if not selected_ids:
            messagebox.showwarning("警告", "请先选中要填充的对话！")
            return
        selected = self._select_resource(resource_type, resource_path, extensions, memory_attr)
        if not selected:
            return
        self.save_state(f"批量填充{resource_type} ({'覆盖' if overwrite else '不覆盖'})")
        count = 0
        for dialogue_id in selected_ids:
            key = str(dialogue_id)
            if key not in self.script_data:
                continue
            script = self.script_data[key]
            if overwrite or field_name not in script:
                script[field_name] = selected
                count += 1
        self.load_dialogue()
        self.mark_unsaved_changes()
        messagebox.showinfo("完成", f"已更新 {count} 个对话的{resource_type}字段")
        if messagebox.askyesno("保存", "是否立即保存这些更改？"):
            self.save_all_changes()

    def delete_selected_dialogues(self):
        selected_ids = self.get_selected_dialogue_ids()
        if not selected_ids:
            return
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected_ids)} 个对话吗？\n此操作不可撤销！"):
            return
        self.save_state("删除选中对话前")
        for dialogue_id in reversed(selected_ids):
            key = str(dialogue_id)
            if key in self.script_data:
                del self.script_data[key]
        if messagebox.askyesno("ID整理", "是否重新整理对话ID使其连续？"):
            existing_ids = []
            for key in self.script_data.keys():
                try:
                    existing_ids.append(int(key))
                except:
                    pass
            existing_ids.sort()
            new_script_data = {}
            new_id = 1
            for old_id in existing_ids:
                new_script_data[str(new_id)] = self.script_data[str(old_id)]
                new_id += 1
            self.script_data = new_script_data
            self.total_dialogues = len(self.script_data)
            self.current_progress = 1
        else:
            max_id = 0
            for key in self.script_data.keys():
                try:
                    id_num = int(key)
                    if id_num > max_id:
                        max_id = id_num
                except:
                    pass
            self.total_dialogues = max_id
            if self.current_progress > self.total_dialogues:
                self.current_progress = max(1, self.total_dialogues)
        self.progress_spinbox.config(to=max(1, self.total_dialogues))
        self.total_label.config(text=f"总对话数: {self.total_dialogues}")
        self.progress_var.set(self.current_progress)
        self.load_dialogue()
        self.all_dialogue_ids = None
        self.update_dialogue_list_lazy()
        self.mark_unsaved_changes()
        messagebox.showinfo("完成", f"已删除 {len(selected_ids)} 个对话")

    def export_selected_dialogues(self):
        selected_ids = self.get_selected_dialogue_ids()
        if not selected_ids:
            messagebox.showwarning("警告", "请先选中要导出的对话！")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"),
                                                            ("所有文件", "*.*")])
        if file_path:
            try:
                export_data = {}
                for dialogue_id in selected_ids:
                    key = str(dialogue_id)
                    if key in self.script_data:
                        export_data[key] = self.script_data[key]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("导出成功", f"成功导出 {len(export_data)} 个对话到文件！")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出时出错: {str(e)}")

    def create_quick_commands(self, parent):
        ttk.Label(parent, text="当前对话附近500条内的立绘:", font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=5, pady=(5, 0))
        ttk.Label(parent, text="点击立绘名称可快速应用到当前对话", font=("微软雅黑", 8), foreground="#858585").pack(anchor="w", padx=5,
                                                                                                pady=(0, 5))
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Label(search_frame, text="搜索:").pack(side="left", padx=5)
        self.quick_search_var = tk.StringVar()
        quick_search_entry = ttk.Entry(search_frame, textvariable=self.quick_search_var, width=15)
        quick_search_entry.pack(side="left", fill="x", expand=True, padx=5)
        quick_search_entry.bind('<KeyRelease>', lambda e: self.filter_quick_commands())
        ttk.Button(search_frame, text="刷新", command=self.update_nearby_characters, width=6).pack(side="right", padx=5)
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.quick_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("微软雅黑", 10),
                                        height=15, bg='#252526', fg='#d4d4d4', selectbackground='#264f78',
                                        selectforeground='#d4d4d4', relief='flat')
        self.quick_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.quick_listbox.yview)
        self.quick_listbox.bind('<<ListboxSelect>>', self.on_quick_command_selected)
        self.quick_count_label = ttk.Label(parent, text="共找到 0 个立绘")
        self.quick_count_label.pack(anchor="w", padx=5, pady=(0, 5))
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Button(button_frame, text="应用到立绘字段", command=self.apply_quick_character, width=15).pack(side="left", padx=2)
        ttk.Button(button_frame, text="清除筛选", command=self.clear_quick_filter, width=15).pack(side="right", padx=2)

    def create_enhanced_preview_area(self, parent):
        preview_header = ttk.Frame(parent)
        preview_header.pack(fill="x", pady=(0, 10))
        ttk.Label(preview_header, text="实时预览", font=("微软雅黑", 12, "bold")).pack(side="left")
        ttk.Button(preview_header, text="刷新预览", command=self.update_realtime_preview, width=10).pack(side="right",
                                                                                                        padx=5)
        self.composite_canvas = tk.Canvas(parent, bg="#0d0d0d", width=336, height=480,
                                          highlightthickness=1, highlightbackground="#555555")
        self.composite_canvas.pack()
        self.composite_canvas.create_text(168, 240, text="预览区域\n图像将在这里叠加显示",
                                          fill="#555555", font=("微软雅黑", 11), justify="center")
        self.xyz_display_label = ttk.Label(parent, text="缩放模式: 0 (正常大小)", font=("微软雅黑", 9))
        self.xyz_display_label.pack(pady=5)
        explanation_frame = ttk.Frame(parent)
        explanation_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(explanation_frame, text="图层顺序:", font=("微软雅黑", 9, "bold")).pack(anchor="w")
        ttk.Label(explanation_frame, text="底层: 背景 (bcgi文件夹)", font=("微软雅黑", 8), foreground="#858585").pack(anchor="w")
        ttk.Label(explanation_frame, text="中层: 立绘 (cimg文件夹) - 受缩放影响，顶部距离预览区域顶端50px",
                  font=("微软雅黑", 8), foreground="#858585").pack(anchor="w")
        ttk.Label(explanation_frame, text="上层: CG (evig文件夹)", font=("微软雅黑", 8), foreground="#858585").pack(anchor="w")
        preview_status_frame = ttk.Frame(parent)
        preview_status_frame.pack(fill="x", pady=(10, 0))
        self.preview_status_label = ttk.Label(preview_status_frame, text="预览就绪",
                                              font=("微软雅黑", 9), foreground="#858585")
        self.preview_status_label.pack(anchor="w")

    # ---------- 重写字段编辑区域，使用Notebook ----------
    def create_field_form(self, parent):
        """创建字段编辑表单（基础 + 选项）"""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True)

        # 基础字段标签页（带滚动）
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="基础字段")
        canvas = tk.Canvas(basic_frame, highlightthickness=0, bg='#1e1e1e')
        scrollbar = ttk.Scrollbar(basic_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set, bg='#1e1e1e')
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._create_basic_field_form(scrollable_frame)

        # 选项标签页（5个选项）
        option_frame = ttk.Frame(notebook)
        notebook.add(option_frame, text="选项设置")
        self._create_option_field_form(option_frame)

        self.field_notebook = notebook

    def _create_basic_field_form(self, parent):
        """基础字段内容（原来的 _create_field_form_content 内容）"""
        row = 0
        ttk.Label(parent, text="背景 (b):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.bg_var = tk.StringVar()
        bg_frame = ttk.Frame(parent)
        bg_frame.grid(row=row, column=1, pady=5, padx=5, sticky="ew")
        bg_entry = ttk.Entry(bg_frame, textvariable=self.bg_var, width=20)
        bg_entry.pack(side="left", fill="x", expand=True)
        bg_copy_btn = ttk.Button(bg_frame, text="↑", command=self.copy_previous_background, width=3)
        bg_copy_btn.pack(side="right", padx=1)
        bg_select_btn = ttk.Button(bg_frame, text="选择", command=self.choose_background, width=6)
        bg_select_btn.pack(side="right", padx=1)
        row += 1

        ttk.Label(parent, text="立绘 (c):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.char_var = tk.StringVar()
        char_frame = ttk.Frame(parent)
        char_frame.grid(row=row, column=1, pady=5, padx=5, sticky="ew")
        char_entry = ttk.Entry(char_frame, textvariable=self.char_var, width=20)
        char_entry.pack(side="left", fill="x", expand=True)
        char_copy_btn = ttk.Button(char_frame, text="↑", command=self.copy_previous_character, width=3)
        char_copy_btn.pack(side="right", padx=1)
        char_select_btn = ttk.Button(char_frame, text="选择", command=self.choose_character, width=6)
        char_select_btn.pack(side="right", padx=1)
        row += 1

        ttk.Label(parent, text="人物:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.person_var = tk.StringVar()
        self.person_combo = ttk.Combobox(parent, textvariable=self.person_var, width=12)
        self.person_combo.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(parent, text="服装:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.clothes_var = tk.StringVar()
        self.clothes_combo = ttk.Combobox(parent, textvariable=self.clothes_var, width=12)
        self.clothes_combo.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        ttk.Label(parent, text="姿势:").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.pose_var = tk.StringVar()
        self.pose_combo = ttk.Combobox(parent, textvariable=self.pose_var, width=12)
        self.pose_combo.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        row += 1

        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=5)
        ttk.Button(button_frame, text="解析立绘名", command=self.parse_character_name, width=12).pack(side="left", padx=2)
        ttk.Button(button_frame, text="拼接立绘名", command=self.generate_character_name, width=12).pack(side="left", padx=2)
        row += 1

        ttk.Label(parent, text="CG (cg):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.cg_var = tk.StringVar()
        cg_frame = ttk.Frame(parent)
        cg_frame.grid(row=row, column=1, pady=5, padx=5, sticky="ew")
        cg_entry = ttk.Entry(cg_frame, textvariable=self.cg_var, width=20)
        cg_entry.pack(side="left", fill="x", expand=True)
        cg_copy_btn = ttk.Button(cg_frame, text="↑", command=self.copy_previous_cg, width=3)
        cg_copy_btn.pack(side="right", padx=1)
        cg_select_btn = ttk.Button(cg_frame, text="选择", command=self.choose_cg, width=6)
        cg_select_btn.pack(side="right", padx=1)
        row += 1

        ttk.Label(parent, text="说话人 (s):").grid(row=row, column=0, sticky="w", pady=5, padx=5)
        self.speaker_var = tk.StringVar()
        speaker_entry = ttk.Entry(parent, textvariable=self.speaker_var, width=25)
        speaker_entry.grid(row=row, column=1, pady=5, padx=5, sticky="w")
        row += 1

        ttk.Label(parent, text="文本 (t):").grid(row=row, column=0, sticky="nw", pady=5, padx=5)
        text_frame = ttk.Frame(parent)
        text_frame.grid(row=row, column=1, pady=5, sticky="w", padx=5)
        self.text_text = scrolledtext.ScrolledText(text_frame, width=30, height=6,
                                                   bg='#252526', fg='#d4d4d4', insertbackground='#d4d4d4',
                                                   selectbackground='#264f78', relief='flat')
        self.text_text.pack()
        row += 1

        # 缩放模式
        zoom_frame = ttk.LabelFrame(parent, text="缩放模式", padding="5")
        zoom_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="ew", padx=5)
        ttk.Label(zoom_frame, text="缩放模式:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.z_var = tk.IntVar(value=0)
        zoom_combo = ttk.Combobox(zoom_frame, textvariable=self.z_var, width=12, state="readonly")
        zoom_combo['values'] = (0, 1, 2)
        zoom_combo.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        zoom_combo.bind('<<ComboboxSelected>>', lambda e: self.on_zoom_changed())
        self.zoom_info_label = ttk.Label(zoom_frame, text="(无缩放)", foreground="#858585")
        self.zoom_info_label.grid(row=0, column=2, padx=5, pady=2, sticky="w")
        info_label = ttk.Label(zoom_frame, text="0: 无缩放  1: 小(0.8倍)  2: 大(1.2倍)",
                               foreground="#858585", font=("微软雅黑", 8))
        info_label.grid(row=1, column=0, columnspan=3, pady=5)
        row += 1

        # 缩放模板
        template_frame = ttk.LabelFrame(parent, text="缩放模板管理", padding="5")
        template_frame.grid(row=row, column=0, columnspan=2, pady=10, sticky="ew", padx=5)
        template_input_frame = ttk.Frame(template_frame)
        template_input_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(template_input_frame, text="模板名称:").pack(side="left", padx=5)
        self.template_name_var = tk.StringVar()
        template_name_entry = ttk.Entry(template_input_frame, textvariable=self.template_name_var, width=15)
        template_name_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(template_input_frame, text="保存模板", command=self.save_xyz_template, width=10).pack(side="right",
                                                                                                         padx=2)
        zoom_copy_btn = ttk.Button(template_input_frame, text="↑复制缩放", command=self.copy_previous_zoom, width=10)
        zoom_copy_btn.pack(side="right", padx=2)
        template_buttons_container = ttk.Frame(template_frame)
        template_buttons_container.pack(fill="both", expand=True)
        self.template_buttons_frame = ttk.Frame(template_buttons_container)
        self.template_buttons_frame.pack(fill="both", expand=True)
        row += 1

        self.zoom_status_label = ttk.Label(parent, text="缩放模式: 无缩放")
        self.zoom_status_label.grid(row=row, column=0, columnspan=2, pady=5, padx=5)
        row += 1

        # 操作按钮
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=15, padx=5)
        ttk.Button(button_frame, text="应用到JSON", command=self.apply_to_json, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="从JSON加载", command=self.load_from_json, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text="清除所有", command=self.clear_fields, width=15).pack(side="left", padx=5)

        # 绑定变量变化
        def safe_update_json(event=None):
            if self.json_update_job:
                self.root.after_cancel(self.json_update_job)
            self.json_update_job = self.root.after(100, self.delayed_update_json)
            self.mark_unsaved_changes()

        self.bg_var.trace_add('write', lambda *args: safe_update_json())
        self.char_var.trace_add('write', lambda *args: safe_update_json())
        self.cg_var.trace_add('write', lambda *args: safe_update_json())
        self.speaker_var.trace_add('write', lambda *args: safe_update_json())
        self.z_var.trace_add('write', lambda *args: safe_update_json())
        self.person_var.trace_add('write', lambda *args: self.on_person_updated())
        self.clothes_var.trace_add('write', lambda *args: self.on_clothes_updated())
        self.pose_var.trace_add('write', lambda *args: self.on_pose_updated())
        self.text_text.bind('<KeyRelease>', lambda e: safe_update_json())

    def _create_option_field_form(self, parent):
        """创建选项设置标签页内容（5个选项）"""
        # 是否有选项
        co_frame = ttk.Frame(parent)
        co_frame.pack(fill="x", pady=10, padx=10)
        self.co_check = ttk.Checkbutton(co_frame, text="该页包含选项", variable=self.co_var,
                                        command=self.on_co_changed)
        self.co_check.pack(side="left")

        # 选项容器
        options_container = ttk.LabelFrame(parent, text="选项内容", padding="10")
        options_container.pack(fill="both", expand=True, padx=10, pady=5)

        # 选项1
        row1 = ttk.Frame(options_container)
        row1.pack(fill="x", pady=5)
        ttk.Label(row1, text="选项1:").pack(side="left")
        self.c1_entry = ttk.Entry(row1, textvariable=self.c1_var, width=30)
        self.c1_entry.pack(side="left", padx=5)
        ttk.Label(row1, text="跳转到ID:").pack(side="left", padx=(10, 0))
        self.c1t_entry = ttk.Entry(row1, textvariable=self.c1t_var, width=8)
        self.c1t_entry.pack(side="left", padx=5)

        # 选项2
        row2 = ttk.Frame(options_container)
        row2.pack(fill="x", pady=5)
        ttk.Label(row2, text="选项2:").pack(side="left")
        self.c2_entry = ttk.Entry(row2, textvariable=self.c2_var, width=30)
        self.c2_entry.pack(side="left", padx=5)
        ttk.Label(row2, text="跳转到ID:").pack(side="left", padx=(10, 0))
        self.c2t_entry = ttk.Entry(row2, textvariable=self.c2t_var, width=8)
        self.c2t_entry.pack(side="left", padx=5)

        # 选项3
        row3 = ttk.Frame(options_container)
        row3.pack(fill="x", pady=5)
        ttk.Label(row3, text="选项3:").pack(side="left")
        self.c3_entry = ttk.Entry(row3, textvariable=self.c3_var, width=30)
        self.c3_entry.pack(side="left", padx=5)
        ttk.Label(row3, text="跳转到ID:").pack(side="left", padx=(10, 0))
        self.c3t_entry = ttk.Entry(row3, textvariable=self.c3t_var, width=8)
        self.c3t_entry.pack(side="left", padx=5)

        # 选项4
        row4 = ttk.Frame(options_container)
        row4.pack(fill="x", pady=5)
        ttk.Label(row4, text="选项4:").pack(side="left")
        self.c4_entry = ttk.Entry(row4, textvariable=self.c4_var, width=30)
        self.c4_entry.pack(side="left", padx=5)
        ttk.Label(row4, text="跳转到ID:").pack(side="left", padx=(10, 0))
        self.c4t_entry = ttk.Entry(row4, textvariable=self.c4t_var, width=8)
        self.c4t_entry.pack(side="left", padx=5)

        # 选项5
        row5 = ttk.Frame(options_container)
        row5.pack(fill="x", pady=5)
        ttk.Label(row5, text="选项5:").pack(side="left")
        self.c5_entry = ttk.Entry(row5, textvariable=self.c5_var, width=30)
        self.c5_entry.pack(side="left", padx=5)
        ttk.Label(row5, text="跳转到ID:").pack(side="left", padx=(10, 0))
        self.c5t_entry = ttk.Entry(row5, textvariable=self.c5t_var, width=8)
        self.c5t_entry.pack(side="left", padx=5)

        self.on_co_changed()  # 初始禁用状态

    def on_co_changed(self):
        """根据‘是否有选项’复选框的状态启用或禁用选项输入框（5个）"""
        state = 'normal' if self.co_var.get() else 'disabled'
        for entry in [self.c1_entry, self.c2_entry, self.c3_entry, self.c4_entry, self.c5_entry,
                      self.c1t_entry, self.c2t_entry, self.c3t_entry, self.c4t_entry, self.c5t_entry]:
            entry.config(state=state)

    def on_zoom_changed(self):
        """缩放模式改变时更新显示"""
        zoom_value = self.z_var.get()
        if zoom_value == 0:
            self.zoom_info_label.config(text="(无缩放)")
            self.zoom_status_label.config(text="缩放模式: 无缩放")
            self.xyz_display_label.config(text="缩放模式: 0 (正常大小)")
        elif zoom_value == 1:
            self.zoom_info_label.config(text="(小: 0.8倍)")
            self.zoom_status_label.config(text="缩放模式: 小(0.8倍)")
            self.xyz_display_label.config(text="缩放模式: 1 (0.8倍)")
        else:  # 2
            self.zoom_info_label.config(text="(大: 1.2倍)")
            self.zoom_status_label.config(text="缩放模式: 大(1.2倍)")
            self.xyz_display_label.config(text="缩放模式: 2 (1.2倍)")
        self.update_realtime_preview()

    # ---------- 通用资源选择器 ----------
    def _select_resource(self, resource_type, resource_path, extensions, memory_attr):
        if not resource_path or not os.path.exists(resource_path):
            messagebox.showwarning("警告", f"{resource_type}文件夹不存在！")
            return None
        select_window = tk.Toplevel(self.root)
        select_window.title(f"选择{resource_type}")
        select_window.geometry("500x600")
        select_window.configure(bg='#1e1e1e')
        select_window.transient(self.root)
        select_window.grab_set()
        resource_files = []
        try:
            for f in os.listdir(resource_path):
                if any(f.lower().endswith(ext) for ext in extensions):
                    resource_files.append(f)
        except Exception as e:
            print(f"加载{resource_type}文件列表失败: {e}")
        resource_files.sort(key=lambda x: x.lower())
        search_frame = ttk.Frame(select_window)
        search_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(search_frame, text="搜索:").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=25)
        search_entry.pack(side="left", padx=5, fill="x", expand=True)
        list_frame = ttk.Frame(select_window)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("微软雅黑", 10),
                             bg='#252526', fg='#d4d4d4', selectbackground='#264f78',
                             selectforeground='#d4d4d4')
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        preview_frame = ttk.LabelFrame(select_window, text="预览", padding="5")
        preview_frame.pack(fill="x", padx=10, pady=(0, 10))
        preview_label = ttk.Label(preview_frame, text="请选择一个文件", foreground="#858585")
        preview_label.pack(pady=5)
        preview_canvas = tk.Canvas(preview_frame, width=200, height=200, bg="#0d0d0d", highlightthickness=1)
        preview_canvas.pack(pady=5)
        preview_canvas.create_text(100, 100, text="预览区域", fill="#858585")
        result = None

        def update_listbox(filter_text=""):
            listbox.delete(0, tk.END)
            filter_text = filter_text.lower()
            for f in resource_files:
                if not filter_text or filter_text in f.lower():
                    name = os.path.splitext(f)[0]
                    listbox.insert(tk.END, name)
            last_selected = getattr(self, memory_attr, '')
            if last_selected:
                last_base = os.path.splitext(last_selected)[0] if last_selected else ''
                try:
                    for i in range(listbox.size()):
                        if listbox.get(i) == last_base:
                            listbox.selection_set(i)
                            listbox.see(i)
                            on_select(None)
                            break
                except:
                    pass

        update_listbox()

        def on_select(event=None):
            selection = listbox.curselection()
            if selection:
                selected_name = listbox.get(selection[0])
                preview_label.config(text=selected_name)
                selected_file = None
                for f in resource_files:
                    if os.path.splitext(f)[0] == selected_name:
                        selected_file = f
                        break
                if selected_file:
                    file_path = os.path.join(resource_path, selected_file)
                    if os.path.exists(file_path):
                        try:
                            pil_image = Image.open(file_path)
                            pil_image.thumbnail((180, 180), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(pil_image)
                            preview_canvas.delete("all")
                            x = (200 - photo.width()) // 2
                            y = (200 - photo.height()) // 2
                            preview_canvas.create_image(x, y, anchor="nw", image=photo)
                            preview_canvas.image = photo
                        except Exception as e:
                            preview_canvas.delete("all")
                            preview_canvas.create_text(100, 100, text="预览失败", fill="#ff6666")

        def on_ok():
            nonlocal result
            selection = listbox.curselection()
            if selection:
                selected_name = listbox.get(selection[0])
                for f in resource_files:
                    if os.path.splitext(f)[0] == selected_name:
                        result = f
                        break
                if memory_attr:
                    setattr(self, memory_attr, result)
                select_window.destroy()
            else:
                messagebox.showinfo("提示", f"请先选择一个{resource_type}")

        def on_cancel():
            select_window.destroy()

        def on_search():
            update_listbox(search_var.get())

        listbox.bind('<<ListboxSelect>>', on_select)
        listbox.bind('<Double-Button-1>', lambda e: on_ok())
        search_entry.bind('<KeyRelease>', lambda e: on_search())
        button_frame = ttk.Frame(select_window)
        button_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(button_frame, text="确定", command=on_ok).pack(side="left", padx=5)
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side="left", padx=5)
        ttk.Button(button_frame, text="搜索", command=on_search).pack(side="right", padx=5)
        select_window.wait_window()
        return result

    def choose_background(self):
        selected = self._select_resource("背景", self.bcgi_path, ['.jpg', '.jpeg', '.png', '.bmp', '.gif'],
                                         'last_selected_background')
        if selected:
            base_name = os.path.splitext(selected)[0]
            self.bg_var.set(base_name)
            self.delayed_update_json()

    def choose_character(self):
        selected = self._select_resource("立绘", self.cimg_path, ['.png', '.jpg', '.jpeg'],
                                         'last_selected_character')
        if selected:
            base_name = os.path.splitext(selected)[0]
            self.char_var.set(base_name)
            self.parse_character_name()
            self.delayed_update_json()

    def choose_cg(self):
        selected = self._select_resource("CG", self.evig_path, ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
                                         'last_selected_cg')
        if selected:
            self.cg_var.set(selected)
            self.delayed_update_json()

    def load_xyz_templates(self):
        try:
            if os.path.exists(self.template_file):
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    self.xyz_templates = json.load(f)
                print(f"已加载 {len(self.xyz_templates)} 个缩放模板")
                self.update_template_buttons()
            else:
                self.xyz_templates = {}
        except Exception as e:
            print(f"加载缩放模板失败: {e}")
            self.xyz_templates = {}

    def save_xyz_templates(self):
        try:
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(self.xyz_templates, f, ensure_ascii=False, indent=2)
            print(f"已保存 {len(self.xyz_templates)} 个缩放模板")
        except Exception as e:
            print(f"保存缩放模板失败: {e}")

    def update_template_buttons(self):
        for widget in self.template_buttons_frame.winfo_children():
            widget.destroy()
        if not self.xyz_templates:
            label = ttk.Label(self.template_buttons_frame, text="暂无模板", foreground="#858585")
            label.pack(pady=5)
            return
        row = 0
        col = 0
        max_cols = 2
        for template_name in self.xyz_templates.keys():
            btn_frame = ttk.Frame(self.template_buttons_frame)
            btn_frame.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            apply_btn = ttk.Button(btn_frame, text=template_name,
                                   command=lambda name=template_name: self.apply_template_button(name), width=12)
            apply_btn.pack(side="left", fill="x", expand=True)
            delete_btn = ttk.Button(btn_frame, text="×",
                                    command=lambda name=template_name: self.delete_template_button(name), width=3)
            delete_btn.pack(side="right")
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        for i in range(max_cols):
            self.template_buttons_frame.grid_columnconfigure(i, weight=1)

    def apply_template_button(self, template_name):
        if template_name in self.xyz_templates:
            template = self.xyz_templates[template_name]
            self.z_var.set(template['z'])
            self.on_zoom_changed()
            self.apply_to_json()
            self.status_label.config(text=f"已应用模板 '{template_name}'", foreground="#6a9955")
            self.template_name_var.set(template_name)

    def delete_template_button(self, template_name):
        if messagebox.askyesno("确认", f"确定要删除模板 '{template_name}' 吗？"):
            del self.xyz_templates[template_name]
            self.save_xyz_templates()
            self.update_template_buttons()
            self.template_name_var.set("")
            self.status_label.config(text=f"已删除模板 '{template_name}'", foreground="#6a9955")

    def save_xyz_template(self):
        template_name = self.template_name_var.get().strip()
        if not template_name:
            messagebox.showwarning("警告", "请输入模板名称！")
            return
        if template_name in self.xyz_templates:
            if not messagebox.askyesno("确认", f"模板 '{template_name}' 已存在，是否覆盖？"):
                return
        self.xyz_templates[template_name] = {'z': self.z_var.get()}
        self.save_xyz_templates()
        self.update_template_buttons()
        self.template_name_var.set("")
        self.status_label.config(text=f"已保存模板 '{template_name}'", foreground="#6a9955")

    def copy_previous_zoom(self):
        if self.current_progress <= 1:
            messagebox.showinfo("提示", "已经是第一页，没有上一页可以复制")
            return
        prev_key = str(self.current_progress - 1)
        if prev_key in self.script_data:
            prev_script = self.script_data[prev_key]
            self.save_state("复制缩放前")
            z_value = prev_script.get('z')
            if z_value is None:
                self.z_var.set(0)
            elif z_value in (1, 2):
                self.z_var.set(z_value)
            elif abs(z_value - 0.8) < 0.1:
                self.z_var.set(1)
            elif abs(z_value - 1.2) < 0.1:
                self.z_var.set(2)
            else:
                self.z_var.set(0)
            self.apply_to_json()
            self.status_label.config(text="已复制上一页的缩放设置", foreground="#6a9955")
        else:
            messagebox.showwarning("警告", f"第{self.current_progress - 1}页不存在")

    # ---------- 项目加载 ----------
    def open_project_folder(self):
        folder_path = filedialog.askdirectory(title="选择游戏根目录")
        if not folder_path:
            return
        common_path = os.path.join(folder_path, "common")
        if not os.path.exists(common_path):
            messagebox.showerror("错误", "未找到common文件夹！请选择正确的游戏根目录。")
            return
        self.project_path = folder_path
        self.script_path = os.path.join(common_path, "script")
        self.evig_path = os.path.join(common_path, "evig")
        self.cimg_path = os.path.join(common_path, "cimg")
        self.bcgi_path = os.path.join(common_path, "bcgi")
        self.load_script_data()
        self.load_resources()
        project_name = os.path.basename(self.project_path)
        self.project_label.config(text=f"项目: {project_name}")
        if self.total_dialogues > 0:
            self.progress_var.set(1)
            self.load_dialogue()
        self.update_dialogue_list_lazy()
        self.update_nearby_characters()
        self.update_realtime_preview()
        messagebox.showinfo("成功", f"项目已加载！\n总对话数: {self.total_dialogues}")

    def open_script_folder(self):
        folder_path = filedialog.askdirectory(title="选择脚本文件夹")
        if not folder_path:
            return
        self.script_path = folder_path
        self.project_path = os.path.dirname(os.path.dirname(folder_path))
        common_path = os.path.dirname(folder_path)
        self.bcgi_path = os.path.join(common_path, "bcgi")
        self.cimg_path = os.path.join(common_path, "cimg")
        self.evig_path = os.path.join(common_path, "evig")
        self.load_script_data()
        try:
            self.load_resources()
        except Exception as e:
            print(f"加载资源列表失败: {e}")
        project_name = os.path.basename(self.project_path)
        self.project_label.config(text=f"项目: {project_name}")
        if self.total_dialogues > 0:
            self.progress_var.set(1)
            self.load_dialogue()
        self.update_dialogue_list_lazy()
        self.update_nearby_characters()
        self.update_realtime_preview()
        messagebox.showinfo("成功", f"脚本已加载！\n总对话数: {self.total_dialogues}")

    def load_script_data(self):
        self.script_data = {}
        if not os.path.exists(self.script_path):
            messagebox.showerror("错误", f"脚本文件夹不存在: {self.script_path}")
            return
        script_files = []
        try:
            for f in os.listdir(self.script_path):
                if f.lower().startswith("scriptdata") and f.lower().endswith(".txt"):
                    script_files.append(f)
        except Exception as e:
            print(f"获取文件列表失败: {e}")
            script_files = []
        if not script_files:
            messagebox.showwarning("警告", "没有找到脚本文件！")
            self.total_dialogues = 0
            self.total_label.config(text="总对话数: 0")
            return

        def extract_number(filename):
            match = re.search(r'(\d+)', filename)
            return int(match.group(1)) if match else 0

        script_files.sort(key=extract_number)
        total_loaded = 0
        for script_file in script_files:
            try:
                file_path = os.path.join(self.script_path, script_file)
                encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']
                chunk_data = None
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                            chunk_data = json.loads(content)
                        print(f"  成功使用编码: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                    except json.JSONDecodeError:
                        continue
                if chunk_data:
                    for k, v in chunk_data.items():
                        self.script_data[str(k)] = v
                    total_loaded += len(chunk_data)
            except Exception as e:
                print(f"加载脚本文件 {script_file} 失败: {e}")
        self.sorted_ids = []
        for key in self.script_data.keys():
            try:
                self.sorted_ids.append(int(key))
            except:
                pass
        self.sorted_ids.sort()
        if self.sorted_ids:
            self.total_dialogues = max(self.sorted_ids)
        else:
            self.total_dialogues = 0
        self.total_label.config(text=f"总对话数: {self.total_dialogues}")
        self.progress_spinbox.config(to=max(1, self.total_dialogues))
        # 清理CG字段
        converted_count = 0
        for key, script in self.script_data.items():
            if 'cg' in script and script['cg']:
                original = script['cg']
                normalized = self.ensure_cg_suffix(original)
                if normalized != original:
                    script['cg'] = normalized
                    converted_count += 1
        if converted_count > 0:
            print(f"已转换 {converted_count} 个CG字段，添加了后缀")
        char_converted = 0
        for key, script in self.script_data.items():
            if 'c' in script and script['c']:
                original = script['c']
                base = os.path.splitext(original)[0]
                if base != original:
                    script['c'] = base
                    char_converted += 1
        if char_converted > 0:
            print(f"已清理 {char_converted} 个立绘字段，移除了后缀")
        print(f"脚本加载完成，共加载 {len(self.script_data)} 个对话，最大ID: {self.total_dialogues}")
        self.status_label.config(text="脚本加载完成", foreground="#6a9955")

    def load_resources(self):
        self.analyze_character_names()
        self.update_character_comboboxes()

    def analyze_character_names(self):
        self.persons = set()
        self.clothes = set()
        self.poses = set()
        self.character_map = {}
        if not os.path.exists(self.cimg_path):
            return
        try:
            char_files = [f for f in os.listdir(self.cimg_path) if f.lower().endswith('.png')]
        except Exception as e:
            print(f"获取立绘文件列表失败: {e}")
            return
        for filename in char_files:
            name = os.path.splitext(filename)[0]
            if '_' in name:
                person_clothes, pose = name.split('_', 1)
                match = re.match(r'^([a-zA-Z]+)(\d+)$', person_clothes)
                if match:
                    person = match.group(1)
                    clothes = match.group(2)
                else:
                    person = person_clothes
                    clothes = ""
                self.character_map[name] = {'person': person, 'clothes': clothes, 'pose': pose, 'filename': filename}
                self.persons.add(person)
                if clothes:
                    self.clothes.add(clothes)
                self.poses.add(pose)

    def update_character_comboboxes(self):
        self.person_combo['values'] = sorted(self.persons)
        self.clothes_combo['values'] = sorted(self.clothes)
        self.pose_combo['values'] = sorted(self.poses)

    def parse_character_name(self):
        if self.is_loading_dialogue:
            return
        char_name = self.char_var.get().strip()
        if not char_name:
            return
        base_name = os.path.splitext(char_name)[0]
        if base_name in self.character_map:
            data = self.character_map[base_name]
            self.person_var.set(data['person'])
            self.clothes_var.set(data['clothes'])
            self.pose_var.set(data['pose'])
        else:
            if '_' in base_name:
                person_clothes, pose = base_name.split('_', 1)
                match = re.match(r'^([a-zA-Z]+)(\d+)$', person_clothes)
                if match:
                    person = match.group(1)
                    clothes = match.group(2)
                else:
                    person = person_clothes
                    clothes = ""
                self.person_var.set(person)
                self.clothes_var.set(clothes)
                self.pose_var.set(pose)
            else:
                self.person_var.set(base_name)
                self.clothes_var.set("")
                self.pose_var.set("")

    def generate_character_name(self):
        if self.is_loading_dialogue:
            return
        person = self.person_var.get().strip()
        clothes = self.clothes_var.get().strip()
        pose = self.pose_var.get().strip()
        if person and pose:
            if clothes:
                char_name = f"{person}{clothes}_{pose}"
            else:
                char_name = f"{person}_{pose}"
            self.char_var.set(char_name)

    def on_person_updated(self):
        if not self.is_loading_dialogue:
            self.generate_character_name()

    def on_clothes_updated(self):
        if not self.is_loading_dialogue:
            self.generate_character_name()

    def on_pose_updated(self):
        if not self.is_loading_dialogue:
            self.generate_character_name()

    # ---------- 自定义字段 ----------
    def add_custom_field(self):
        """在JSON源码中添加自定义字段"""
        key = self.custom_key_var.get().strip()
        value = self.custom_value_var.get().strip()
        if not key:
            messagebox.showwarning("警告", "请输入字段名")
            return
        try:
            # 获取当前源码内容
            json_text = self.source_text.get(1.0, tk.END).strip()
            if not json_text:
                script = {}
            else:
                script = json.loads(json_text)
            # 尝试将值转换为合适的JSON类型
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.lower() == "null":
                value = None
            else:
                # 尝试转换为数字
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass  # 保持字符串
            script[key] = value
            # 更新源码显示
            self.source_text.delete(1.0, tk.END)
            self.source_text.insert(1.0, json.dumps(script, ensure_ascii=False, indent=2))
            # 可选：立即应用到JSON
            self.apply_to_json()
            self.status_label.config(text=f"已添加字段 '{key}'", foreground="#6a9955")
        except Exception as e:
            messagebox.showerror("错误", f"添加字段失败: {str(e)}")

    # ---------- 加载对话（已扩展选项5）----------
    def load_dialogue(self):
        try:
            self.is_loading_dialogue = True
            progress_id = self.progress_var.get()
            progress_key = str(progress_id)
            if progress_key in self.script_data:
                script = self.script_data[progress_key]
                self.source_text.delete(1.0, tk.END)
                formatted = json.dumps(script, ensure_ascii=False, indent=2)
                self.source_text.insert(1.0, formatted)
                self.bg_var.set(script.get('b', ''))
                self.char_var.set(os.path.splitext(script.get('c', ''))[0])
                self.cg_var.set(script.get('cg', ''))
                self.speaker_var.set(script.get('s', ''))
                z_value = script.get('z', None)
                if z_value is None:
                    self.z_var.set(0)
                elif z_value in (1, 2):
                    self.z_var.set(z_value)
                elif abs(z_value - 0.8) < 0.1:
                    self.z_var.set(1)
                elif abs(z_value - 1.2) < 0.1:
                    self.z_var.set(2)
                else:
                    self.z_var.set(0)
                self.text_text.delete(1.0, tk.END)
                text_content = script.get('t', '')
                self.text_text.insert(1.0, text_content)
                self.parse_character_name()
                self.current_progress = progress_id
                # 加载选项字段（5个）
                self.co_var.set(script.get('co', False))
                self.c1_var.set(script.get('c1', ''))
                self.c2_var.set(script.get('c2', ''))
                self.c3_var.set(script.get('c3', ''))
                self.c4_var.set(script.get('c4', ''))
                self.c5_var.set(script.get('c5', ''))
                self.c1t_var.set(str(script.get('c1t', '')))
                self.c2t_var.set(str(script.get('c2t', '')))
                self.c3t_var.set(str(script.get('c3t', '')))
                self.c4t_var.set(str(script.get('c4t', '')))
                self.c5t_var.set(str(script.get('c5t', '')))
                self.on_co_changed()
                self.template_name_var.set("")
                self.on_zoom_changed()
                self.update_realtime_preview()
                self.update_nearby_characters()
                self.update_dialogue_list_selection()
            else:
                self.source_text.delete(1.0, tk.END)
                self.source_text.insert(1.0, "{}")
                self.clear_fields()
                self.template_name_var.set("")
            # 自动定位对话列表到当前页并选中
            self.ensure_dialogue_visible_in_list(progress_id)
        except Exception as e:
            messagebox.showerror("错误", f"加载对话失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_loading_dialogue = False

    def ensure_dialogue_visible_in_list(self, dialogue_id):
        """确保对话列表翻到包含该ID的页面，并选中该行"""
        if not self.filtered_dialogues:
            return
        try:
            # 如果目标ID不在当前过滤列表中（可能被搜索隐藏），临时清空搜索
            if dialogue_id not in self.filtered_dialogues:
                self.dialogue_search_var.set("")
                self.update_dialogue_list_lazy()
            idx = self.filtered_dialogues.index(dialogue_id)
            page = idx // self.max_display_dialogues + 1
            if page != self.current_page:
                self.current_page = page
            self._update_pagination_and_display()
        except ValueError:
            pass

    def delayed_update_json(self):
        if not self.is_loading_dialogue:
            self.apply_to_json()

    # ---------- 应用到JSON（保留自定义字段，扩展选项5）----------
    def apply_to_json(self):
        if self.is_loading_dialogue or self.is_applying_to_json:
            return
        try:
            self.is_applying_to_json = True
            self.save_state("应用更改前")
            # 获取当前对话的现有数据（保留所有字段）
            script = self.script_data.get(str(self.current_progress), {}).copy()
            # 用表单中的已知字段覆盖
            bg_value = self.bg_var.get().strip()
            if bg_value:
                script['b'] = bg_value
            else:
                script.pop('b', None)
            char_value = self.char_var.get().strip()
            if char_value:
                script['c'] = char_value
            else:
                script.pop('c', None)
            cg_value = self.cg_var.get().strip()
            if cg_value:
                cg_value = self.ensure_cg_suffix(cg_value)
                script['cg'] = cg_value
            else:
                script.pop('cg', None)
            speaker_value = self.speaker_var.get().strip()
            if speaker_value:
                script['s'] = speaker_value
            else:
                script.pop('s', None)
            zoom_mode = self.z_var.get()
            if zoom_mode in (1, 2):
                script['z'] = zoom_mode
            else:
                script.pop('z', None)
            text_content = self.text_text.get(1.0, tk.END).strip()
            if text_content:
                script['t'] = text_content
            else:
                script.pop('t', None)
            # 选项字段（5个）
            if self.co_var.get():
                script['co'] = True
                # 选项1
                if self.c1_var.get().strip():
                    script['c1'] = self.c1_var.get().strip()
                    try:
                        script['c1t'] = int(self.c1t_var.get())
                    except:
                        pass
                else:
                    script.pop('c1', None)
                    script.pop('c1t', None)
                # 选项2
                if self.c2_var.get().strip():
                    script['c2'] = self.c2_var.get().strip()
                    try:
                        script['c2t'] = int(self.c2t_var.get())
                    except:
                        pass
                else:
                    script.pop('c2', None)
                    script.pop('c2t', None)
                # 选项3
                if self.c3_var.get().strip():
                    script['c3'] = self.c3_var.get().strip()
                    try:
                        script['c3t'] = int(self.c3t_var.get())
                    except:
                        pass
                else:
                    script.pop('c3', None)
                    script.pop('c3t', None)
                # 选项4
                if self.c4_var.get().strip():
                    script['c4'] = self.c4_var.get().strip()
                    try:
                        script['c4t'] = int(self.c4t_var.get())
                    except:
                        pass
                else:
                    script.pop('c4', None)
                    script.pop('c4t', None)
                # 选项5
                if self.c5_var.get().strip():
                    script['c5'] = self.c5_var.get().strip()
                    try:
                        script['c5t'] = int(self.c5t_var.get())
                    except:
                        pass
                else:
                    script.pop('c5', None)
                    script.pop('c5t', None)
            else:
                for key in ['co', 'c1', 'c1t', 'c2', 'c2t', 'c3', 'c3t', 'c4', 'c4t', 'c5', 'c5t']:
                    script.pop(key, None)
            self.script_data[str(self.current_progress)] = script
            self.source_text.delete(1.0, tk.END)
            formatted = json.dumps(script, ensure_ascii=False, indent=2)
            self.source_text.insert(1.0, formatted)
            self.update_zoom_status()
            self.update_realtime_preview()
            self.mark_unsaved_changes()
        except Exception as e:
            messagebox.showerror("错误", f"应用失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_applying_to_json = False

    def update_zoom_status(self):
        zoom_mode = self.z_var.get()
        if zoom_mode == 0:
            self.zoom_status_label.config(text="缩放模式: 无缩放", foreground="#6a9955")
        elif zoom_mode == 1:
            self.zoom_status_label.config(text="缩放模式: 小(0.8倍)", foreground="#6a9955")
        else:
            self.zoom_status_label.config(text="缩放模式: 大(1.2倍)", foreground="#ffcc00")

    # ---------- 从JSON加载（保留自定义字段）----------
    def load_from_json(self):
        try:
            json_text = self.source_text.get(1.0, tk.END).strip()
            if not json_text:
                return
            script = json.loads(json_text)
            self.bg_var.set(script.get('b', ''))
            self.char_var.set(script.get('c', ''))
            self.cg_var.set(script.get('cg', ''))
            self.speaker_var.set(script.get('s', ''))
            z_value = script.get('z', None)
            if z_value is None:
                self.z_var.set(0)
            elif z_value in (1, 2):
                self.z_var.set(z_value)
            elif abs(z_value - 0.8) < 0.1:
                self.z_var.set(1)
            elif abs(z_value - 1.2) < 0.1:
                self.z_var.set(2)
            else:
                self.z_var.set(0)
            self.text_text.delete(1.0, tk.END)
            text_content = script.get('t', '')
            self.text_text.insert(1.0, text_content)
            self.parse_character_name()
            # 加载选项（5个）
            self.co_var.set(script.get('co', False))
            self.c1_var.set(script.get('c1', ''))
            self.c2_var.set(script.get('c2', ''))
            self.c3_var.set(script.get('c3', ''))
            self.c4_var.set(script.get('c4', ''))
            self.c5_var.set(script.get('c5', ''))
            self.c1t_var.set(str(script.get('c1t', '')))
            self.c2t_var.set(str(script.get('c2t', '')))
            self.c3t_var.set(str(script.get('c3t', '')))
            self.c4t_var.set(str(script.get('c4t', '')))
            self.c5t_var.set(str(script.get('c5t', '')))
            self.on_co_changed()
            self.on_zoom_changed()
        except Exception as e:
            messagebox.showerror("错误", f"从JSON加载失败: {str(e)}")

    # ---------- 清空字段（含选项5）----------
    def clear_fields(self):
        self.bg_var.set('')
        self.char_var.set('')
        self.cg_var.set('')
        self.speaker_var.set('')
        self.z_var.set(0)
        self.person_var.set('')
        self.clothes_var.set('')
        self.pose_var.set('')
        self.text_text.delete(1.0, tk.END)
        self.template_name_var.set("")
        self.co_var.set(False)
        self.c1_var.set('')
        self.c2_var.set('')
        self.c3_var.set('')
        self.c4_var.set('')
        self.c5_var.set('')
        self.c1t_var.set('')
        self.c2t_var.set('')
        self.c3t_var.set('')
        self.c4t_var.set('')
        self.c5t_var.set('')
        self.on_co_changed()
        self.on_zoom_changed()

    def copy_previous_background(self):
        self._copy_previous_field('b')

    def copy_previous_character(self):
        self._copy_previous_field('c')

    def copy_previous_cg(self):
        self._copy_previous_field('cg')

    def copy_previous_character_and_cg(self):
        if self.current_progress <= 1:
            messagebox.showinfo("提示", "已经是第一页，没有上一页可以复制")
            return
        prev_key = str(self.current_progress - 1)
        if prev_key in self.script_data:
            prev_script = self.script_data[prev_key]
            self.save_state("复制上一页前")
            if 'c' in prev_script and prev_script['c']:
                self.char_var.set(os.path.splitext(prev_script['c'])[0])
                self.parse_character_name()
            if 'cg' in prev_script and prev_script['cg']:
                self.cg_var.set(prev_script['cg'])
            if 'b' in prev_script and prev_script['b']:
                self.bg_var.set(prev_script['b'])
            z_value = prev_script.get('z')
            if z_value is None:
                self.z_var.set(0)
            elif z_value in (1, 2):
                self.z_var.set(z_value)
            elif abs(z_value - 0.8) < 0.1:
                self.z_var.set(1)
            elif abs(z_value - 1.2) < 0.1:
                self.z_var.set(2)
            self.apply_to_json()
            self.status_label.config(text="已复制上一页的立绘和CG设置", foreground="#6a9955")
        else:
            messagebox.showwarning("警告", f"第{self.current_progress - 1}页不存在")

    def _copy_previous_field(self, field_name):
        if self.current_progress <= 1:
            messagebox.showinfo("提示", "已经是第一页，没有上一页可以复制")
            return
        prev_key = str(self.current_progress - 1)
        if prev_key in self.script_data:
            prev_script = self.script_data[prev_key]
            if field_name in prev_script and prev_script[field_name]:
                if field_name == 'c':
                    base = os.path.splitext(prev_script[field_name])[0]
                    self.char_var.set(base)
                    self.parse_character_name()
                elif field_name == 'cg':
                    self.cg_var.set(prev_script[field_name])
                elif field_name == 'b':
                    self.bg_var.set(prev_script[field_name])
                self.apply_to_json()
                self.status_label.config(text=f"已复制上一页的{field_name}设置", foreground="#6a9955")
            else:
                messagebox.showinfo("提示", f"上一页没有{field_name}字段")
        else:
            messagebox.showwarning("警告", f"第{self.current_progress - 1}页不存在")

    # ---------- 预览更新（立绘顶端距离顶部50px）----------
    def update_realtime_preview(self):
        try:
            bg_text = self.bg_var.get().strip()
            char_text = self.char_var.get().strip()
            cg_text = self.cg_var.get().strip()
            zoom_mode = self.z_var.get()
            z_value = self.get_zoom_value(zoom_mode)
            self.xyz_display_label.config(
                text=f"缩放模式: {zoom_mode} ({z_value}x)" if zoom_mode > 0 else f"缩放模式: 0 (正常大小)")

            def load_and_composite_images():
                try:
                    composite_image = Image.new('RGBA', (336, 480), (13, 13, 13, 255))
                    bg_loaded = False
                    if bg_text and self.bcgi_path:
                        bg_path = None
                        if os.path.splitext(bg_text)[1] == '':
                            for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                                test_path = os.path.join(self.bcgi_path, f"{bg_text}{ext}")
                                if os.path.exists(test_path):
                                    bg_path = test_path
                                    break
                        else:
                            bg_path = os.path.join(self.bcgi_path, bg_text)
                        if bg_path and os.path.exists(bg_path):
                            try:
                                bg_image = Image.open(bg_path).convert('RGBA')
                                bg_image = bg_image.resize((336, 480), Image.Resampling.LANCZOS)
                                composite_image.paste(bg_image, (0, 0))
                                bg_loaded = True
                            except Exception as e:
                                print(f"加载背景失败: {e}")
                    char_loaded = False
                    if char_text and self.cimg_path:
                        char_path = None
                        if os.path.splitext(char_text)[1] == '':
                            for ext in ['.png', '.jpg', '.jpeg']:
                                test_path = os.path.join(self.cimg_path, f"{char_text}{ext}")
                                if os.path.exists(test_path):
                                    char_path = test_path
                                    break
                        else:
                            char_path = os.path.join(self.cimg_path, char_text)
                        if char_path and os.path.exists(char_path):
                            try:
                                char_image = Image.open(char_path).convert('RGBA')
                                original_width, original_height = char_image.size
                                new_width = int(original_width * z_value)
                                new_height = int(original_height * z_value)
                                if new_width < 10 or new_height < 10:
                                    new_width = max(10, new_width)
                                    new_height = max(10, new_height)
                                char_image = char_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                # 修改：立绘顶端距离预览区域顶端50px，水平居中
                                pos_x = (336 - new_width) // 2
                                pos_y = 50
                                # 如果立绘超出底部，则向上调整
                                if pos_y + new_height > 480:
                                    pos_y = 480 - new_height
                                char_composite = Image.new('RGBA', (336, 480), (0, 0, 0, 0))
                                char_composite.paste(char_image, (pos_x, pos_y), char_image)
                                composite_image = Image.alpha_composite(composite_image, char_composite)
                                char_loaded = True
                            except Exception as e:
                                print(f"加载立绘失败: {e}")
                    cg_loaded = False
                    if cg_text and self.evig_path:
                        cg_path = os.path.join(self.evig_path, cg_text)
                        if os.path.exists(cg_path):
                            try:
                                cg_image = Image.open(cg_path).convert('RGBA')
                                cg_image = cg_image.resize((336, 480), Image.Resampling.LANCZOS)
                                composite_image = Image.alpha_composite(composite_image, cg_image)
                                cg_loaded = True
                            except Exception as e:
                                print(f"加载CG失败: {e}")
                    if not (bg_loaded or char_loaded or cg_loaded):
                        draw = ImageDraw.Draw(composite_image)
                        draw.text((168, 200), "无图像预览", fill=(136, 136, 136, 255), font=None, anchor="mm")
                        settings_text = f"背景: {bg_text or '无'}\n立绘: {char_text or '无'}\nCG: {cg_text or '无'}\n缩放: {zoom_mode}({z_value}x)" if zoom_mode > 0 else f"背景: {bg_text or '无'}\n立绘: {char_text or '无'}\nCG: {cg_text or '无'}\n缩放: 无缩放"
                        draw.multiline_text((168, 280), settings_text, fill=(136, 136, 136, 255), font=None,
                                            anchor="mm", align="center", spacing=5)
                    self.root.after(0, lambda: self.display_composite_image(composite_image, bg_loaded, char_loaded,
                                                                            cg_loaded))
                except Exception as e:
                    print(f"合成图像失败: {e}")
                    self.root.after(0, lambda: self.display_error())

            threading.Thread(target=load_and_composite_images, daemon=True).start()
            self.preview_status_label.config(text=f"预览更新中...")
        except Exception as e:
            print(f"更新预览失败: {e}")
            self.preview_status_label.config(text=f"预览更新失败: {str(e)[:50]}...", foreground="#ff6666")

    def display_composite_image(self, composite_image, bg_loaded, char_loaded, cg_loaded):
        try:
            self.composite_canvas.delete("all")
            photo = ImageTk.PhotoImage(composite_image)
            self.composite_canvas.create_image(0, 0, anchor="nw", image=photo)
            self.composite_canvas.image = photo
            status_parts = []
            if bg_loaded: status_parts.append("背景")
            if char_loaded: status_parts.append("立绘")
            if cg_loaded: status_parts.append("CG")
            if status_parts:
                self.preview_status_label.config(text=f"已显示: {', '.join(status_parts)} {time.strftime('%H:%M:%S')}")
            else:
                self.preview_status_label.config(text="无图像可显示")
        except Exception as e:
            print(f"显示合成图像失败: {e}")
            self.display_error()

    def display_error(self):
        self.composite_canvas.delete("all")
        self.composite_canvas.create_text(168, 240, text="图像加载失败", fill="#ff6666", font=("Arial", 12))
        self.preview_status_label.config(text="图像加载失败", foreground="#ff6666")

    def update_nearby_characters(self):
        if not self.script_data:
            return
        start_id = max(1, self.current_progress - 500)
        end_id = min(self.total_dialogues, self.current_progress + 500)
        characters_set = set()
        for i in range(start_id, end_id + 1):
            key = str(i)
            if key in self.script_data:
                script = self.script_data[key]
                if 'c' in script and script['c']:
                    base = os.path.splitext(script['c'])[0]
                    characters_set.add(base)
        self.nearby_characters = sorted(list(characters_set))
        self.filter_quick_commands()
        self.quick_count_label.config(text=f"共找到 {len(self.nearby_characters)} 个立绘")

    def filter_quick_commands(self):
        search_term = self.quick_search_var.get().lower().strip()
        self.quick_listbox.delete(0, tk.END)
        for char in self.nearby_characters:
            if not search_term or search_term in char.lower():
                self.quick_listbox.insert(tk.END, char)

    def clear_quick_filter(self):
        self.quick_search_var.set("")
        self.filter_quick_commands()

    def on_quick_command_selected(self, event):
        selection = self.quick_listbox.curselection()
        if selection:
            char_name = self.quick_listbox.get(selection[0])
            self.char_var.set(char_name)
            self.parse_character_name()
            self.delayed_update_json()

    def apply_quick_character(self):
        selection = self.quick_listbox.curselection()
        if selection:
            char_name = self.quick_listbox.get(selection[0])
            self.char_var.set(char_name)
            self.parse_character_name()
            self.delayed_update_json()
            self.status_label.config(text=f"已应用立绘: {char_name}", foreground="#6a9955")

    # ---------- 全局搜索 ----------
    def open_global_search(self):
        """打开全局搜索对话框，搜索所有对话的JSON字符串内容"""
        if not self.script_data:
            messagebox.showwarning("警告", "没有加载任何对话数据！")
            return
        search_window = tk.Toplevel(self.root)
        search_window.title("全局搜索 - JSON内容")
        search_window.geometry("600x500")
        search_window.configure(bg='#1e1e1e')
        search_window.transient(self.root)
        search_window.grab_set()

        # 搜索输入框
        search_frame = ttk.Frame(search_window)
        search_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(search_frame, text="搜索关键词:").pack(side="left", padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(search_frame, text="搜索", command=lambda: perform_search()).pack(side="left", padx=5)

        # 结果列表框
        list_frame = ttk.Frame(search_window)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.global_search_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                                font=("微软雅黑", 10),
                                                bg='#252526', fg='#d4d4d4',
                                                selectbackground='#264f78', selectforeground='#d4d4d4')
        self.global_search_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.global_search_listbox.yview)

        # 状态标签
        status_label = ttk.Label(search_window, text="输入关键词后点击搜索", foreground="#858585")
        status_label.pack(anchor="w", padx=10, pady=(0, 10))

        def perform_search():
            keyword = search_var.get().strip()
            if not keyword:
                messagebox.showinfo("提示", "请输入搜索关键词")
                return
            status_label.config(text="搜索中...", foreground="#ffcc00")
            search_window.update()
            results = []
            for did, script in self.script_data.items():
                json_str = json.dumps(script, ensure_ascii=False)
                if keyword.lower() in json_str.lower():
                    # 提取预览信息
                    speaker = script.get('s', '无')
                    text_preview = script.get('t', '')[:40]
                    results.append((int(did), speaker, text_preview))
            results.sort(key=lambda x: x[0])
            self.global_search_listbox.delete(0, tk.END)
            if results:
                for did, speaker, text_preview in results:
                    display = f"{did:6d} | {speaker[:20]:20s} | {text_preview}"
                    self.global_search_listbox.insert(tk.END, display)
                status_label.config(text=f"找到 {len(results)} 个结果", foreground="#6a9955")
            else:
                status_label.config(text="未找到匹配的结果", foreground="#ff6666")

        def on_double_click(event):
            selection = self.global_search_listbox.curselection()
            if selection:
                text = self.global_search_listbox.get(selection[0])
                try:
                    dialogue_id = int(text.split('|')[0].strip())
                    # 跳转
                    self.current_progress = dialogue_id
                    self.progress_var.set(dialogue_id)
                    self.load_dialogue()
                    # 自动翻页到该对话所在的列表页
                    self.ensure_dialogue_visible_in_list(dialogue_id)
                    search_window.destroy()
                except:
                    pass

        self.global_search_listbox.bind('<Double-Button-1>', on_double_click)
        search_entry.bind('<Return>', lambda e: perform_search())
        # 初始自动搜索空字符串？不，等待用户输入

    def get_chunk_number(self, dialogue_id):
        return (dialogue_id - 1) // self.chunk_size + 1

    def get_chunk_file_path(self, chunk_num):
        return os.path.join(self.script_path, f"scriptData{chunk_num}.txt")

    def load_chunk_data(self, chunk_num):
        chunk_file = self.get_chunk_file_path(chunk_num)
        if os.path.exists(chunk_file):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_chunk_data(self, chunk_num, chunk_data):
        chunk_file = self.get_chunk_file_path(chunk_num)
        try:
            sorted_data = {}
            for id_key in sorted(chunk_data.keys(), key=lambda x: int(x)):
                sorted_data[id_key] = chunk_data[id_key]
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(sorted_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存块 {chunk_num} 失败: {e}")
            return False

    def insert_dialogue_before_current(self):
        if not self.script_data:
            messagebox.showwarning("警告", "请先加载项目！")
            return
        insert_pos = self.current_progress
        self.save_state("插入对话前")
        existing_ids = []
        for key in self.script_data.keys():
            try:
                id_num = int(key)
                if id_num >= insert_pos:
                    existing_ids.append(id_num)
            except:
                pass
        existing_ids.sort(reverse=True)
        affected_chunks = set()
        moved_count = 0
        for old_id in existing_ids:
            new_id = old_id + 1
            old_chunk = self.get_chunk_number(old_id)
            new_chunk = self.get_chunk_number(new_id)
            affected_chunks.add(old_chunk)
            affected_chunks.add(new_chunk)
            self.script_data[str(new_id)] = self.script_data[str(old_id)]
            del self.script_data[str(old_id)]
            moved_count += 1
        new_chunk = self.get_chunk_number(insert_pos)
        affected_chunks.add(new_chunk)
        self.script_data[str(insert_pos)] = {}
        max_id = 0
        for key in self.script_data.keys():
            try:
                id_num = int(key)
                if id_num > max_id:
                    max_id = id_num
            except:
                pass
        self.total_dialogues = max_id
        self.progress_spinbox.config(to=self.total_dialogues)
        self.total_label.config(text=f"总对话数: {self.total_dialogues}")
        self.load_dialogue()
        self.all_dialogue_ids = None
        self.sorted_ids = None
        self.update_dialogue_list_lazy()
        if messagebox.askyesno("保存确认",
                               f"插入操作已完成，移动了 {moved_count} 条对话，影响了 {len(affected_chunks)} 个块文件。\n是否立即保存这些更改到文件？"):
            self.save_affected_chunks_after_insert(affected_chunks)
            self.status_label.config(text=f"已在位置 {insert_pos} 插入新对话（已保存）", foreground="#6a9955")
        else:
            self.mark_unsaved_changes()
            self.status_label.config(text=f"已在位置 {insert_pos} 插入新对话（未保存）", foreground="#ffcc00")
        messagebox.showinfo("插入成功",
                            f"已在位置 {insert_pos} 插入新对话\n移动了 {moved_count} 条对话\n影响了 {len(affected_chunks)} 个块文件")

    def save_affected_chunks_after_insert(self, affected_chunks):
        if not self.script_path:
            messagebox.showwarning("警告", "请先打开项目！")
            return
        try:
            self.status_label.config(text="正在保存受影响的块文件...", foreground="#569cd6")
            chunks_to_save = sorted(affected_chunks)
            total_chunks = len(chunks_to_save)
            saved_count = 0
            failed_chunks = []
            for chunk_num in chunks_to_save:
                chunk_data = {}
                start_id = (chunk_num - 1) * self.chunk_size + 1
                end_id = chunk_num * self.chunk_size
                for dialogue_id in range(start_id, end_id + 1):
                    key = str(dialogue_id)
                    if key in self.script_data:
                        chunk_data[key] = self.script_data[key]
                if self.save_chunk_data(chunk_num, chunk_data):
                    saved_count += 1
                else:
                    failed_chunks.append(chunk_num)
                self.status_label.config(text=f"正在保存文件... ({saved_count}/{total_chunks})")
                self.root.update()
            self.last_save_time = time.time()
            self.unsaved_changes = False
            if failed_chunks:
                self.status_label.config(text=f"部分保存失败", foreground="#ff6666")
                messagebox.showwarning("保存警告",
                                       f"成功保存了 {saved_count} 个块文件\n以下 {len(failed_chunks)} 个块保存失败: {failed_chunks}")
            else:
                self.status_label.config(text=f"已保存 {saved_count} 个受影响的块文件 {time.strftime('%H:%M:%S')}",
                                         foreground="#6a9955")
        except Exception as e:
            messagebox.showerror("错误", f"保存块文件失败: {str(e)}")

    def delete_dialogue(self):
        if not self.script_data:
            return
        if not messagebox.askyesno("确认删除", f"确定要删除对话 {self.current_progress} 吗？"):
            return
        self.save_state("删除对话前")
        current_id = self.current_progress
        affected_chunks = set()
        existing_ids = []
        for key in self.script_data.keys():
            try:
                id_num = int(key)
                if id_num > current_id:
                    existing_ids.append(id_num)
            except:
                pass
        existing_ids.sort()
        if str(current_id) in self.script_data:
            old_chunk = self.get_chunk_number(current_id)
            affected_chunks.add(old_chunk)
            del self.script_data[str(current_id)]
        moved_count = 0
        for old_id in existing_ids:
            new_id = old_id - 1
            old_chunk = self.get_chunk_number(old_id)
            new_chunk = self.get_chunk_number(new_id)
            affected_chunks.add(old_chunk)
            affected_chunks.add(new_chunk)
            self.script_data[str(new_id)] = self.script_data[str(old_id)]
            del self.script_data[str(old_id)]
            moved_count += 1
        max_id = 0
        for key in self.script_data.keys():
            try:
                id_num = int(key)
                if id_num > max_id:
                    max_id = id_num
            except:
                pass
        self.total_dialogues = max_id
        self.progress_spinbox.config(to=max(1, self.total_dialogues))
        if current_id > self.total_dialogues:
            self.current_progress = max(1, self.total_dialogues)
        else:
            self.current_progress = current_id
        self.progress_var.set(self.current_progress)
        self.total_label.config(text=f"总对话数: {self.total_dialogues}")
        self.load_dialogue()
        self.all_dialogue_ids = None
        self.sorted_ids = None
        self.update_dialogue_list_lazy()
        if messagebox.askyesno("保存确认",
                               f"删除操作已完成，移动了 {moved_count} 条对话，影响了 {len(affected_chunks)} 个块文件。\n是否立即保存这些更改到文件？"):
            self.save_affected_chunks_after_insert(affected_chunks)
            self.status_label.config(text=f"已删除对话 {current_id}（已保存）", foreground="#6a9955")
        else:
            self.mark_unsaved_changes()
            self.status_label.config(text=f"已删除对话 {current_id}（未保存）", foreground="#ffcc00")

    def save_and_next(self):
        self.save_current()
        self.next_dialogue()

    def mark_unsaved_changes(self):
        self.unsaved_changes = True
        if self.auto_save_enabled:
            self.status_label.config(text="有未保存的更改", foreground="#ffcc00")

    def start_auto_save(self):
        if self.auto_save_thread is None or not self.auto_save_thread.is_alive():
            self.auto_save_thread = threading.Thread(target=self.auto_save_worker, daemon=True)
            self.auto_save_thread.start()

    def auto_save_worker(self):
        while True:
            time.sleep(1)
            if not self.auto_save_enabled:
                continue
            if time.time() - self.last_save_time >= self.auto_save_interval:
                if self.unsaved_changes and self.script_path:
                    try:
                        self.root.after(0, self.auto_save_current)
                    except:
                        pass

    def auto_save_current(self):
        try:
            if self.unsaved_changes:
                self.save_to_file()
                self.unsaved_changes = False
                self.status_label.config(text=f"已自动保存 {time.strftime('%H:%M:%S')}", foreground="#6a9955")
        except Exception as e:
            print(f"自动保存失败: {e}")

    def save_current(self):
        try:
            self.apply_to_json()
            self.save_to_file()
            self.status_label.config(text=f"已保存 {time.strftime('%H:%M:%S')}", foreground="#6a9955")
            self.unsaved_changes = False
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def save_to_file(self):
        if not self.script_path:
            return
        try:
            script = self.script_data.get(str(self.current_progress), {})
            if not script:
                return
            chunk_num = self.get_chunk_number(self.current_progress)
            chunk_data = self.load_chunk_data(chunk_num)
            chunk_data[str(self.current_progress)] = script
            if self.save_chunk_data(chunk_num, chunk_data):
                self.last_save_time = time.time()
        except Exception as e:
            print(f"保存文件失败: {e}")

    def save_all_changes(self):
        if not self.script_path:
            messagebox.showwarning("警告", "请先打开项目！")
            return
        try:
            self.status_label.config(text="正在保存所有更改...", foreground="#569cd6")
            chunk_files = {}
            all_ids = []
            for key in self.script_data.keys():
                try:
                    all_ids.append(int(key))
                except:
                    pass
            all_ids.sort()
            for progress_id in all_ids:
                chunk_num = self.get_chunk_number(progress_id)
                if chunk_num not in chunk_files:
                    chunk_files[chunk_num] = {}
                chunk_files[chunk_num][str(progress_id)] = self.script_data[str(progress_id)]
            total_chunks = len(chunk_files)
            current_chunk = 0
            failed_chunks = []
            for chunk_num in sorted(chunk_files.keys()):
                chunk_data = chunk_files[chunk_num]
                if self.save_chunk_data(chunk_num, chunk_data):
                    pass
                else:
                    failed_chunks.append(chunk_num)
                current_chunk += 1
                self.status_label.config(text=f"正在保存文件... ({current_chunk}/{total_chunks})")
                self.root.update()
            self.last_save_time = time.time()
            self.unsaved_changes = False
            if failed_chunks:
                self.status_label.config(text=f"部分保存失败", foreground="#ff6666")
                messagebox.showwarning("保存警告",
                                       f"成功保存了 {total_chunks - len(failed_chunks)}/{total_chunks} 个文件\n以下 {len(failed_chunks)} 个块保存失败: {failed_chunks}")
            else:
                self.status_label.config(text=f"已保存所有更改 {time.strftime('%H:%M:%S')}", foreground="#6a9955")
                messagebox.showinfo("保存", f"所有更改已保存到文件！共 {total_chunks} 个文件")
            self.update_dialogue_list_lazy()
        except Exception as e:
            messagebox.showerror("错误", f"保存所有更改失败: {str(e)}")

    def prev_dialogue(self):
        if self.current_progress > 1:
            self.current_progress -= 1
            self.progress_var.set(self.current_progress)
            self.load_dialogue()

    def next_dialogue(self):
        if self.current_progress < self.total_dialogues:
            self.current_progress += 1
            self.progress_var.set(self.current_progress)
            self.load_dialogue()
        else:
            self.add_dialogue()

    def auto_save_and_prev(self):
        if self.unsaved_changes:
            self.save_current()
        self.prev_dialogue()

    def auto_save_and_next(self):
        if self.unsaved_changes:
            self.save_current()
        self.next_dialogue()

    def ctrl_s_save(self):
        self.save_current()

    def add_dialogue(self):
        self.save_state("添加对话前")
        new_id = self.total_dialogues + 1
        self.total_dialogues = new_id
        self.progress_var.set(new_id)
        self.progress_spinbox.config(to=new_id)
        self.source_text.delete(1.0, tk.END)
        self.source_text.insert(1.0, "{}")
        self.clear_fields()
        self.current_progress = new_id
        self.total_label.config(text=f"总对话数: {self.total_dialogues}")
        self.all_dialogue_ids = None
        self.sorted_ids = None
        self.update_dialogue_list_lazy()
        if messagebox.askyesno("保存确认", f"已添加新对话 ID: {new_id}，是否立即保存？"):
            self.save_current()
            self.status_label.config(text=f"已添加新对话 {new_id}（已保存）", foreground="#6a9955")
        else:
            self.mark_unsaved_changes()
            self.status_label.config(text=f"已添加新对话 {new_id}（未保存）", foreground="#ffcc00")

    def save_state(self, description):
        state = {
            'script_data': copy.deepcopy(self.script_data),
            'current_progress': self.current_progress,
            'total_dialogues': self.total_dialogues,
            'description': description
        }
        self.undo_stack.append(state)
        self.current_state = state
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) <= 1:
            messagebox.showinfo("提示", "无法撤销")
            return
        current_state = self.undo_stack.pop()
        self.redo_stack.append(current_state)
        prev_state = self.undo_stack[-1]
        self._restore_state(prev_state)
        self.status_label.config(text="已撤销", foreground="#569cd6")

    def redo(self):
        if not self.redo_stack:
            messagebox.showinfo("提示", "无法重做")
            return
        next_state = self.redo_stack.pop()
        self.undo_stack.append(next_state)
        self.current_state = next_state
        self._restore_state(next_state)
        self.status_label.config(text="已重做", foreground="#569cd6")

    def _restore_state(self, state):
        self.script_data = copy.deepcopy(state['script_data'])
        self.current_progress = state['current_progress']
        self.total_dialogues = state['total_dialogues']
        self.progress_var.set(self.current_progress)
        self.progress_spinbox.config(to=max(1, self.total_dialogues))
        self.total_label.config(text=f"总对话数: {self.total_dialogues}")
        self.load_dialogue()
        self.all_dialogue_ids = None
        self.sorted_ids = None
        self.update_dialogue_list_lazy()

    def optimize_storage(self):
        if not self.script_data:
            messagebox.showwarning("警告", "没有可优化的数据！")
            return
        self.save_state("优化储存前")
        before_count = len(self.script_data)
        dialogues_to_delete = []
        batch_keys = list(self.script_data.keys())
        for dialogue_id in batch_keys:
            script_data = self.script_data[dialogue_id]
            if not script_data:
                dialogues_to_delete.append(dialogue_id)
                continue
            keys_to_delete = []
            for key, value in script_data.items():
                if value == "" or (isinstance(value, str) and value.strip() == ""):
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del script_data[key]
            if not script_data:
                dialogues_to_delete.append(dialogue_id)
        for dialogue_id in dialogues_to_delete:
            del self.script_data[dialogue_id]
        if messagebox.askyesno("ID整理", "是否要重新整理对话ID，使其连续？"):
            existing_ids = []
            for key in self.script_data.keys():
                try:
                    existing_ids.append(int(key))
                except:
                    pass
            existing_ids.sort()
            if existing_ids:
                affected_chunks = set()
                new_script_data = {}
                new_id = 1
                moved_count = 0
                for old_id in existing_ids:
                    if old_id != new_id:
                        moved_count += 1
                        old_chunk = self.get_chunk_number(old_id)
                        new_chunk = self.get_chunk_number(new_id)
                        affected_chunks.add(old_chunk)
                        affected_chunks.add(new_chunk)
                    new_script_data[str(new_id)] = self.script_data[str(old_id)]
                    new_id += 1
                self.script_data = new_script_data
                if str(self.current_progress) not in self.script_data:
                    self.current_progress = 1
                    self.progress_var.set(1)
        max_id = 0
        for key in self.script_data.keys():
            try:
                id_num = int(key)
                if id_num > max_id:
                    max_id = id_num
            except:
                pass
        self.total_dialogues = max_id
        self.progress_spinbox.config(to=max(1, self.total_dialogues))
        self.total_label.config(text=f"总对话数: {self.total_dialogues}")
        self.load_dialogue()
        self.all_dialogue_ids = None
        self.sorted_ids = None
        self.update_dialogue_list_lazy()
        deleted_empty_dialogues = len(dialogues_to_delete)
        after_count = len(self.script_data)
        messagebox.showinfo("优化完成",
                            f"储存优化完成！\n优化前: {before_count} 个对话\n优化后: {after_count} 个对话\n删除了 {deleted_empty_dialogues} 个空对话")

    def batch_rename(self):
        rename_window = tk.Toplevel(self.root)
        rename_window.title("批量重命名")
        rename_window.geometry("400x300")
        rename_window.configure(bg='#1e1e1e')
        ttk.Label(rename_window, text="查找文本:").pack(pady=5)
        find_entry = ttk.Entry(rename_window, width=40)
        find_entry.pack(pady=5)
        ttk.Label(rename_window, text="替换为:").pack(pady=5)
        replace_entry = ttk.Entry(rename_window, width=40)
        replace_entry.pack(pady=5)

        def do_rename():
            find_text = find_entry.get()
            replace_text = replace_entry.get()
            if not find_text:
                messagebox.showerror("错误", "请输入要查找的文本")
                return
            count = 0
            for key, script in self.script_data.items():
                if 't' in script and find_text in script['t']:
                    script['t'] = script['t'].replace(find_text, replace_text)
                    count += 1
            messagebox.showinfo("完成", f"替换了 {count} 处文本")
            rename_window.destroy()

        ttk.Button(rename_window, text="执行替换", command=do_rename).pack(pady=20)

    def export_script(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json",
                                                 filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"),
                                                            ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.script_data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("导出", "脚本导出成功！")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出时出错: {str(e)}")

    def import_script(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                self.save_state("导入脚本前")
                self.script_data.update(imported_data)
                max_id = 0
                for key in self.script_data.keys():
                    try:
                        id_num = int(key)
                        if id_num > max_id:
                            max_id = id_num
                    except:
                        pass
                self.total_dialogues = max_id
                self.total_label.config(text=f"总对话数: {self.total_dialogues}")
                self.progress_spinbox.config(to=max(1, self.total_dialogues))
                self.all_dialogue_ids = None
                self.sorted_ids = None
                self.update_dialogue_list_lazy()
                self.load_dialogue()
                messagebox.showinfo("导入", f"成功导入 {len(imported_data)} 个对话！")
            except Exception as e:
                messagebox.showerror("导入失败", f"导入时出错: {str(e)}")

    def rescan_resources(self):
        if self.project_path:
            self.load_resources()
            messagebox.showinfo("成功", "资源已重新扫描！")
        else:
            messagebox.showwarning("警告", "请先打开项目！")

    def reload_project(self):
        if self.project_path:
            self.save_state("重新加载前")
            self.load_script_data()
            self.load_resources()
            if self.total_dialogues > 0:
                self.load_dialogue()
            self.all_dialogue_ids = None
            self.sorted_ids = None
            self.update_dialogue_list_lazy()
            messagebox.showinfo("成功", "项目已重新加载！")
        else:
            messagebox.showwarning("警告", "请先打开项目！")

    def clear_image_cache(self):
        self.image_cache.clear()
        messagebox.showinfo("成功", "图片缓存已清理")

    def quit_editor(self):
        if self.unsaved_changes:
            if messagebox.askyesno("未保存更改", "有未保存的更改，是否在退出前保存？"):
                self.save_all_changes()
        self.root.quit()

    def update_dialogue_list_lazy(self):
        if not self.script_data:
            return
        if not hasattr(self, 'all_dialogue_ids'):
            self.all_dialogue_ids = None
        if self.all_dialogue_ids is not None:
            dialogue_ids = self.all_dialogue_ids
        else:
            self.status_label.config(text="正在加载对话列表...", foreground="#569cd6")
            dialogue_ids = []
            for key in self.script_data.keys():
                try:
                    dialogue_ids.append(int(key))
                except:
                    pass
            dialogue_ids.sort()
            self.all_dialogue_ids = dialogue_ids
            self.status_label.config(text="对话列表加载完成", foreground="#6a9955")
        search_term = self.dialogue_search_var.get().lower().strip()
        if search_term:
            self.status_label.config(text="正在搜索...", foreground="#569cd6")
            self.filtered_dialogues = []
            for d_id in dialogue_ids:
                script = self.script_data[str(d_id)]
                speaker = script.get('s', '无')
                text_preview = script.get('t', '')[:30]
                if (search_term in str(d_id).lower() or search_term in speaker.lower() or search_term in text_preview.lower()):
                    self.filtered_dialogues.append(d_id)
            self.status_label.config(text=f"搜索完成，找到 {len(self.filtered_dialogues)} 个结果", foreground="#6a9955")
        else:
            self.filtered_dialogues = dialogue_ids.copy()
        self._update_pagination_and_display()

    def _update_pagination_and_display(self):
        self.dialogue_listbox.delete(0, tk.END)
        if len(self.filtered_dialogues) == 0:
            self.total_pages = 1
            self.current_page = 1
        else:
            self.total_pages = max(1, (len(self.filtered_dialogues) + self.max_display_dialogues - 1) // self.max_display_dialogues)
        self.current_page = min(self.current_page, self.total_pages)
        self.current_page = max(1, self.current_page)
        start_idx = (self.current_page - 1) * self.max_display_dialogues
        end_idx = min(start_idx + self.max_display_dialogues, len(self.filtered_dialogues))
        page_dialogues = self.filtered_dialogues[start_idx:end_idx]
        batch_items = []
        for d_id in page_dialogues:
            script = self.script_data[str(d_id)]
            speaker = script.get('s', '无')
            text_preview = script.get('t', '')[:50]
            display_text = f"{d_id:6d} | {speaker[:20]:20s} | {text_preview}"
            batch_items.append(display_text)
        for item in batch_items:
            self.dialogue_listbox.insert(tk.END, item)
        self.page_label.config(text=f"第{self.current_page}/{self.total_pages}页")
        self.update_dialogue_list_selection()
        if self.all_dialogue_ids:
            self.total_label.config(text=f"总对话数: {len(self.all_dialogue_ids)}")

    def update_dialogue_list_selection(self):
        if not hasattr(self, 'dialogue_listbox') or not self.dialogue_listbox:
            return
        for i in range(self.dialogue_listbox.size()):
            text = self.dialogue_listbox.get(i)
            try:
                dialogue_id = int(text.split('|')[0].strip())
                if dialogue_id == self.current_progress:
                    self.dialogue_listbox.selection_clear(0, tk.END)
                    self.dialogue_listbox.selection_set(i)
                    self.dialogue_listbox.see(i)
                    return
            except ValueError:
                continue
        self.dialogue_listbox.selection_clear(0, tk.END)

    def change_page(self, delta):
        new_page = self.current_page + delta
        if 1 <= new_page <= self.total_pages:
            self.current_page = new_page
            self._update_pagination_and_display()

    def filter_dialogue_list(self):
        self.current_page = 1
        self.update_dialogue_list_lazy()

    def on_dialogue_selected(self, event):
        pass

    def on_dialogue_double_click(self, event):
        try:
            index = self.dialogue_listbox.nearest(event.y)
            if index >= 0:
                text = self.dialogue_listbox.get(index)
                try:
                    dialogue_id = int(text.split('|')[0].strip())
                    self.current_progress = dialogue_id
                    self.progress_var.set(dialogue_id)
                    self.load_dialogue()
                    # 自动切换到选项页如果存在选项
                    if self.co_var.get():
                        self.field_notebook.select(1)
                    else:
                        self.field_notebook.select(0)
                except ValueError:
                    pass
        except:
            pass

    def jump_to_selected_dialogue(self):
        selection = self.dialogue_listbox.curselection()
        if selection:
            text = self.dialogue_listbox.get(selection[0])
            try:
                dialogue_id = int(text.split('|')[0].strip())
                self.current_progress = dialogue_id
                self.progress_var.set(dialogue_id)
                self.load_dialogue()
                if self.co_var.get():
                    self.field_notebook.select(1)
                else:
                    self.field_notebook.select(0)
            except ValueError:
                messagebox.showerror("错误", "无法解析对话ID")

    def delete_selected_dialogue(self):
        selection = self.dialogue_listbox.curselection()
        if selection:
            text = self.dialogue_listbox.get(selection[0])
            try:
                dialogue_id = int(text.split('|')[0].strip())
                self.current_progress = dialogue_id
                self.progress_var.set(dialogue_id)
                self.delete_dialogue()
            except:
                pass

    def get_zoom_value(self, zoom_mode):
        if zoom_mode == 0:
            return 1.0
        return self.zoom_modes.get(zoom_mode, 1.0)


def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    try:
        from PIL import Image, ImageTk, ImageDraw
        print("Pillow库可用，图片预览功能已启用")
    except ImportError:
        messagebox.showerror("缺少依赖", "需要安装Pillow库来显示图片预览。\n请运行: pip install Pillow")
        return
    root = tk.Tk()
    app = GalGameScriptEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()