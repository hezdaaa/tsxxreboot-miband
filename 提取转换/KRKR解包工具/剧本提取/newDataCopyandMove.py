import os
import shutil
import sys

def organize_files(pattern, mode):
    """
    将当前目录下符合文件名模式的文件复制到以模式命名的文件夹中
    
    参数:
        pattern: 文件名模式，使用=作为分隔符 (例如: '月望=tlg')
        mode: 操作模式 (1: 仅当前目录, 2: 包含子目录)
    """
    # 获取当前工作目录
    current_dir = os.getcwd()
    
    # 解析模式，分割多个关键词
    keywords = pattern.split('=')
    print(f"匹配关键词: {keywords}")
    
    # 创建目标文件夹 (用下划线连接关键词)
    target_dir_name = '_'.join(keywords)
    target_dir = os.path.join(current_dir, target_dir_name)
    
    try:
        os.makedirs(target_dir, exist_ok=True)
        print(f"创建目标文件夹: {target_dir_name}")
    except Exception as e:
        print(f"创建文件夹失败: {e}")
        return 0
    
    moved_count = 0
    
    def should_copy_file(filename):
        """检查文件名是否包含所有关键词（不区分大小写）"""
        filename_lower = filename.lower()
        for keyword in keywords:
            if keyword.lower() not in filename_lower:
                return False
        return True
    
    if mode == 1:
        # 模式1: 仅处理当前目录下的文件
        print("扫描当前目录...")
        file_list = os.listdir(current_dir)
        print(f"找到 {len(file_list)} 个文件和文件夹")
        
        for filename in file_list:
            src_path = os.path.join(current_dir, filename)
            
            # 跳过目录
            if os.path.isdir(src_path):
                continue
                
            # 检查文件名是否匹配所有关键词
            if should_copy_file(filename):
                dest_path = os.path.join(target_dir, filename)
                
                try:
                    # 复制文件
                    shutil.copy2(src_path, dest_path)
                    print(f"已复制: {filename} -> {target_dir_name}/")
                    moved_count += 1
                except Exception as e:
                    print(f"复制文件 {filename} 失败: {e}")
            else:
                print(f"跳过: {filename} (不匹配模式)")
                
    elif mode == 2:
        # 模式2: 递归处理所有子目录
        print("递归扫描所有子目录...")
        for root, dirs, files in os.walk(current_dir):
            # 跳过目标文件夹本身
            if os.path.abspath(root) == os.path.abspath(target_dir):
                continue
                
            for filename in files:
                # 检查文件名是否匹配所有关键词
                if should_copy_file(filename):
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
                    
                    try:
                        # 复制文件
                        shutil.copy2(src_path, dest_path)
                        rel_path = os.path.relpath(src_path, current_dir)
                        print(f"已复制: {rel_path} -> {target_dir_name}/{dest_filename}")
                        moved_count += 1
                    except Exception as e:
                        print(f"复制文件 {filename} 失败: {e}")
                else:
                    print(f"跳过: {os.path.join(root, filename)} (不匹配模式)")
                    
    return moved_count

if __name__ == "__main__":
    # 检查参数数量
    if len(sys.argv) < 3:
        print("请提供文件名模式和操作模式作为参数")
        print("示例: python dataCopyandMove.py 月望=tlg 1")
        print("模式: 1-仅当前目录, 2-包含子目录")
        sys.exit(1)
    
    # 获取模式参数
    pattern = sys.argv[1].strip()
    mode_str = sys.argv[2].strip()
    
    if not pattern:
        print("错误: 无效的文件名模式")
        sys.exit(1)
    
    # 验证模式参数
    if mode_str not in ('1', '2'):
        print("错误: 无效的操作模式，必须是 '1' 或 '2'")
        print("模式: 1-仅当前目录, 2-包含子目录")
        sys.exit(1)
    
    mode = int(mode_str)
    print(f"整理包含 '{pattern}' 模式的文件 (模式 {mode})...")
    print(f"当前目录: {os.getcwd()}")
    
    # 检查当前目录中的文件
    print("\n当前目录中的文件:")
    for item in os.listdir('.'):
        if os.path.isfile(item):
            print(f"  {item}")
    
    moved_count = organize_files(pattern, mode)
    
    if moved_count > 0:
        print(f"\n操作完成! 共复制了 {moved_count} 个符合模式的文件")
        print(f"文件已复制到: {'_'.join(pattern.split('='))} 文件夹")
    else:
        print(f"\n未找到符合模式的文件")
        print("请确认文件名是否同时包含所有关键词")
