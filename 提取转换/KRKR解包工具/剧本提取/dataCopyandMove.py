import os
import shutil
import sys

def organize_files(extension, mode):
    """
    将当前目录下指定后缀的文件复制到以该后缀命名的文件夹中
    
    参数:
        extension: 文件后缀名 (例如: 'scn', 'txt', 'json')
        mode: 操作模式 (1: 仅当前目录, 2: 包含子目录)
    """
    # 获取当前工作目录
    current_dir = os.getcwd()
    
    # 创建目标文件夹 (后缀名小写)
    target_dir = os.path.join(current_dir, extension.lower())
    os.makedirs(target_dir, exist_ok=True)
    
    moved_count = 0
    
    if mode == 1:
        # 模式1: 仅处理当前目录下的文件
        for filename in os.listdir(current_dir):
            src_path = os.path.join(current_dir, filename)
            
            # 跳过目录
            if os.path.isdir(src_path):
                continue
                
            # 检查文件后缀匹配
            if filename.lower().endswith(f".{extension.lower()}"):
                dest_path = os.path.join(target_dir, filename)
                
                # 复制文件
                shutil.copy2(src_path, dest_path)
                print(f"已复制: {filename} -> {extension.lower()}/")
                moved_count += 1
                
    elif mode == 2:
        # 模式2: 递归处理所有子目录
        for root, dirs, files in os.walk(current_dir):
            # 跳过目标文件夹本身
            if os.path.abspath(root) == os.path.abspath(target_dir):
                continue
                
            for filename in files:
                # 检查文件后缀匹配
                if filename.lower().endswith(f".{extension.lower()}"):
                    src_path = os.path.join(root, filename)
                    
                    # 生成唯一的目标文件名
                    base, ext = os.path.splitext(filename)
                    dest_filename = filename
                    counter = 1
                    
                    # 处理文件名冲突
                    while os.path.exists(os.path.join(target_dir, dest_filename)):
                        dest_filename = f"{base}_{counter}{ext}"
                        counter += 1
                    
                    dest_path = os.path.join(target_dir, dest_filename)
                    
                    # 复制文件
                    shutil.copy2(src_path, dest_path)
                    rel_path = os.path.relpath(src_path, current_dir)
                    print(f"已复制: {rel_path} -> {extension.lower()}/{dest_filename}")
                    moved_count += 1
                    
    return moved_count

if __name__ == "__main__":
    # 检查参数数量
    if len(sys.argv) < 3:
        print("请提供文件后缀和操作模式作为参数")
        print("示例: python datamove.py scn 1")
        print("模式: 1-仅当前目录, 2-包含子目录")
        sys.exit(1)
    
    # 获取后缀参数
    extension = sys.argv[1].strip().lstrip('.')
    mode_str = sys.argv[2].strip()
    
    if not extension:
        print("错误: 无效的文件后缀")
        sys.exit(1)
    
    # 验证模式参数
    if mode_str not in ('1', '2'):
        print("错误: 无效的操作模式，必须是 '1' 或 '2'")
        print("模式: 1-仅当前目录, 2-包含子目录")
        sys.exit(1)
    
    mode = int(mode_str)
    print(f"整理 .{extension} 文件 (模式 {mode})...")
    moved_count = organize_files(extension, mode)
    
    if moved_count > 0:
        print(f"\n操作完成! 共复制了 {moved_count} 个 .{extension} 文件")
    else:
        print(f"\n未找到 .{extension} 文件")