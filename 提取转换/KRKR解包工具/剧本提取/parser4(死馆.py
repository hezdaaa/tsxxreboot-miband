import json, os

# 设置输出目录
output_dir = os.path.join("parsed")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)  # 使用makedirs更安全

def parse_json_to_dialogue(filename):
    """解析JSON文件并提取人物对话"""
    output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.txt")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        with open(output_path, 'w', encoding='utf-8') as out_file:
            for scene in data.get('scenes', []):
                for text_entry in scene.get('texts', []):
                    # 提取人物和对话文本
                    character = text_entry[0] if text_entry and len(text_entry) > 0 else "null"
                    dialogue = text_entry[2] if text_entry and len(text_entry) > 2 else ""
                    
                    # 确保对话内容不为空才写入
                    if dialogue:
                        out_file.write(f"{character}: {dialogue}\n")
    
    except Exception as e:
        print(f"处理文件 {filename} 时出错: {str(e)}")

# 处理当前目录下所有JSON文件
for file in os.listdir():
    if file.endswith('.json'):
        parse_json_to_dialogue(file)

print("解析完成！")