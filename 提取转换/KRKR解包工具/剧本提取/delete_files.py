import os
import sys

def delete_files_containing(pattern):
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 列出目录下所有文件
    files = os.listdir(script_dir)
    deleted_count = 0
    
    for filename in files:
        file_path = os.path.join(script_dir, filename)
        
        # 跳过目录，只处理文件
        if os.path.isfile(file_path):
            # 检查文件名是否包含指定模式
            if pattern in filename:
                try:
                    os.remove(file_path)
                    print(f"已删除: {filename}")
                    deleted_count += 1
                except Exception as e:
                    print(f"删除失败 [{filename}]: {str(e)}")
    
    print(f"\n操作完成! 共删除 {deleted_count} 个文件")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("请提供需要匹配的文件名字符串")
        print("示例: python script.py ks.resx")
        sys.exit(1)
    
    target_pattern = sys.argv[1]
    print(f"即将删除当前目录下所有包含 '{target_pattern}' 的文件...")
    confirm = input("确定继续? (y/n): ").strip().lower()
    
    if confirm == 'y':
        delete_files_containing(target_pattern)
    else:
        print("操作已取消")