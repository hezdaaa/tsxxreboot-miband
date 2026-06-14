import os
import shutil
import sys

def organize_files_by_extension(extension):
    """
    将当前目录下指定后缀的文件移动到以该后缀命名的文件夹中
    
    参数:
        extension: 文件后缀名 (例如: 'scn', 'txt', 'json')
    """
    # 获取当前工作目录
    current_dir = os.getcwd()
    
    # 创建目标文件夹 (后缀名小写)
    target_dir = os.path.join(current_dir, extension.lower())
    os.makedirs(target_dir, exist_ok=True)
    
    # 遍历当前目录所有文件
    moved_count = 0
    for filename in os.listdir(current_dir):
        # 跳过目录
        if os.path.isdir(filename):
            continue
            
        # 检查文件后缀匹配
        if filename.lower().endswith(f".{extension.lower()}"):
            src_path = os.path.join(current_dir, filename)
            dest_path = os.path.join(target_dir, filename)
            
            # 移动文件
            shutil.move(src_path, dest_path)
            print(f"已移动: {filename} -> {target_dir}/")
            moved_count += 1
    
    return moved_count

if __name__ == "__main__":
    # 检查是否提供了后缀参数
    if len(sys.argv) < 2:
        print("请提供文件后缀作为参数")
        print("示例: python organizer.py scn")
        sys.exit(1)
    
    # 获取后缀参数
    extension = sys.argv[1].strip().lstrip('.')
    
    if not extension:
        print("错误: 无效的文件后缀")
        sys.exit(1)
    
    print(f"整理 {extension} 文件...")
    moved_count = organize_files_by_extension(extension)
    
    if moved_count > 0:
        print(f"\n操作完成! 共移动了 {moved_count} 个 .{extension} 文件")
    else:
        print(f"\n未找到 .{extension} 文件")