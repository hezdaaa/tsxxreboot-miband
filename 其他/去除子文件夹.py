import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

class FileExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件提取工具 - 提取所有子文件到根目录")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        # 变量
        self.source_dir = tk.StringVar()

        # 创建界面组件
        self.create_widgets()

    def create_widgets(self):
        # 选择文件夹区域
        frame_select = tk.Frame(self.root, padx=10, pady=10)
        frame_select.pack(fill=tk.X)

        tk.Label(frame_select, text="目标大文件夹：").pack(side=tk.LEFT)
        tk.Entry(frame_select, textvariable=self.source_dir, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_select, text="浏览...", command=self.choose_directory).pack(side=tk.LEFT)

        # 操作按钮区域
        frame_buttons = tk.Frame(self.root, padx=10, pady=5)
        frame_buttons.pack(fill=tk.X)

        self.extract_btn = tk.Button(frame_buttons, text="开始提取并清理", command=self.start_extract,
                                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.extract_btn.pack(side=tk.LEFT, padx=5)

        self.clear_log_btn = tk.Button(frame_buttons, text="清空日志", command=self.clear_log,
                                       bg="#f44336", fg="white")
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)

        # 日志显示区域
        frame_log = tk.Frame(self.root, padx=10, pady=10)
        frame_log.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame_log, text="操作日志：", anchor="w").pack(fill=tk.X)
        self.log_area = scrolledtext.ScrolledText(frame_log, wrap=tk.WORD, height=20)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # 初始提示
        self.log("就绪。请选择一个大文件夹，工具将把其中所有子文件夹内的文件移动到根目录，并删除所有子文件夹。")

    def choose_directory(self):
        """选择源文件夹（大文件夹）"""
        dir_path = filedialog.askdirectory(title="请选择要处理的文件夹（大文件夹）")
        if dir_path:
            self.source_dir.set(dir_path)
            self.log(f"已选择文件夹：{dir_path}")

    def log(self, message):
        """在日志区域添加消息并自动滚动到底部"""
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """清空日志区域"""
        self.log_area.delete(1.0, tk.END)
        self.log("日志已清空。")

    def start_extract(self):
        """启动提取线程，防止界面卡死"""
        source = self.source_dir.get().strip()
        if not source:
            messagebox.showwarning("警告", "请先选择一个文件夹！")
            return
        if not os.path.isdir(source):
            messagebox.showerror("错误", "所选路径不是有效目录，请重新选择！")
            return

        # 二次确认
        if not messagebox.askyesno("确认操作",
                                   f"即将处理文件夹：\n{source}\n\n"
                                   "操作内容：\n"
                                   "1. 将【所有子文件夹】内的文件移动到根目录\n"
                                   "2. 重命名可能重复的文件（基于原相对路径）\n"
                                   "3. 删除所有空的子文件夹（包括嵌套）\n\n"
                                   "是否继续？"):
            return

        # 禁用按钮，防止重复操作
        self.extract_btn.config(state=tk.DISABLED)
        self.log("=" * 50)
        self.log("开始处理...")

        # 启动后台线程执行实际工作
        thread = threading.Thread(target=self.extract_and_clean, args=(source,), daemon=True)
        thread.start()

    def extract_and_clean(self, root_path):
        """
        核心功能：
        1. 遍历 root_path 下所有子文件夹中的文件
        2. 将文件移动到 root_path 根目录，自动处理重名
        3. 最后删除所有子文件夹（全部删除）
        """
        try:
            # 统计变量
            moved_count = 0
            skip_count = 0  # 根目录已有的文件（不移动）
            error_count = 0
            conflict_renamed_count = 0

            # 第一步：收集所有需要移动的文件（排除根目录下直接的文件）
            files_to_move = []  # 存储 (源文件路径, 相对路径)
            for dirpath, dirnames, filenames in os.walk(root_path):
                # 跳过根目录本身：如果 dirpath == root_path，说明是顶层，这些文件不需要移动（保留原位）
                if dirpath == root_path:
                    # 记录根目录下的文件数量（仅用于日志）
                    for file in filenames:
                        skip_count += 1
                    continue

                # 对于子文件夹内的文件，需要移动
                for file in filenames:
                    src_file = os.path.join(dirpath, file)
                    rel_path = os.path.relpath(src_file, root_path)  # 相对于根目录的路径
                    files_to_move.append((src_file, rel_path))

            total_files = len(files_to_move)
            self.log(f"共发现 {total_files} 个需要从子文件夹提取的文件，根目录原有 {skip_count} 个文件（保留）。")

            if total_files == 0:
                self.log("没有需要提取的文件。直接开始清理文件夹...")
            else:
                self.log("开始移动文件...")

            # 第二步：移动文件
            for idx, (src_file, rel_path) in enumerate(files_to_move, 1):
                # 计算目标文件名（先尝试直接使用原始文件名）
                base_name = os.path.basename(src_file)
                dest_path = os.path.join(root_path, base_name)

                # 处理重名：如果目标文件已存在，则使用基于相对路径的唯一命名
                if os.path.exists(dest_path):
                    # 将相对路径中的分隔符替换为下划线，构成新文件名
                    # 例如: sub1/sub2/file.txt -> sub1_sub2_file.txt
                    new_name = rel_path.replace(os.sep, '_')
                    dest_path = os.path.join(root_path, new_name)

                    # 如果仍然重名，则追加数字序号（防止极少数巧合冲突）
                    if os.path.exists(dest_path):
                        name_base, ext = os.path.splitext(new_name)
                        counter = 1
                        while True:
                            test_name = f"{name_base}_{counter}{ext}"
                            test_path = os.path.join(root_path, test_name)
                            if not os.path.exists(test_path):
                                dest_path = test_path
                                break
                            counter += 1
                        self.log(f"  [重命名] {rel_path} -> {os.path.basename(dest_path)} (已存在冲突)")
                        conflict_renamed_count += 1
                    else:
                        self.log(f"  [重命名] {rel_path} -> {os.path.basename(dest_path)} (文件名冲突)")
                        conflict_renamed_count += 1
                else:
                    # 无冲突，直接使用原名
                    self.log(f"  [移动] {rel_path} -> {base_name}")

                # 执行移动
                try:
                    shutil.move(src_file, dest_path)
                    moved_count += 1
                except Exception as e:
                    self.log(f"  [错误] 移动失败 {src_file} -> {dest_path}: {str(e)}")
                    error_count += 1

                # 每移动50个文件刷新一次日志显示
                if idx % 50 == 0:
                    self.log(f"进度: 已处理 {idx}/{total_files} 个文件...")

            self.log(f"文件移动完成。成功移动: {moved_count} 个, 重命名: {conflict_renamed_count} 个, 失败: {error_count} 个")

            # 第三步：删除所有子文件夹（包括嵌套的所有文件夹，但保留根目录）
            self.log("开始删除所有子文件夹...")
            deleted_folders = 0
            error_folders = 0

            # 从最深层开始删除，避免重复尝试，使用 topdown=False 的 walk
            for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
                # 跳过根目录本身
                if dirpath == root_path:
                    continue
                try:
                    # 如果目录还存在（移动过程中可能已经空），强制删除目录树
                    if os.path.exists(dirpath):
                        shutil.rmtree(dirpath, ignore_errors=False)
                        self.log(f"  [删除文件夹] {os.path.relpath(dirpath, root_path)}")
                        deleted_folders += 1
                except Exception as e:
                    self.log(f"  [错误] 删除文件夹失败 {dirpath}: {str(e)}")
                    error_folders += 1

            self.log(f"删除完成。成功删除子文件夹: {deleted_folders} 个, 失败: {error_folders} 个")

            # 最终总结
            self.log("=" * 50)
            self.log("处理完成！")
            self.log(f"总结：提取文件 {moved_count} 个，重命名 {conflict_renamed_count} 个，删除文件夹 {deleted_folders} 个。")
            if error_count > 0 or error_folders > 0:
                self.log("注意：部分操作发生错误，请检查日志。")
                messagebox.showwarning("完成但有错误", f"处理完成，但发生 {error_count} 个文件移动错误和 {error_folders} 个文件夹删除错误。\n请查看日志详情。")
            else:
                messagebox.showinfo("完成", f"处理成功！\n共提取 {moved_count} 个文件到根目录，删除了 {deleted_folders} 个子文件夹。")

        except Exception as e:
            self.log(f"程序运行出现严重错误: {str(e)}")
            messagebox.showerror("运行时错误", f"发生严重错误：{str(e)}")
        finally:
            # 恢复按钮状态
            self.extract_btn.config(state=tk.NORMAL)
            self.log("就绪。可继续选择其他文件夹进行操作。")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileExtractorApp(root)
    root.mainloop()