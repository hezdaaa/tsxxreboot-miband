import json, os

output_dir = "parsed"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def parse(filename):
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(output_dir, f"{base_name}.txt")
    
    with open(filename, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
    
    with open(output_path, 'w', encoding='utf-8') as output_file:
        for scene in data['scenes']:
            if 'texts' in scene:
                for text_block in scene['texts']:
                    # 确保是有效的文本块结构
                    if isinstance(text_block, list) and len(text_block) > 2 and isinstance(text_block[2], list):
                        lang_texts = text_block[2]
                        # 简体中文是第三个元素 [角色名/null, 文本]
                        if len(lang_texts) >= 3 and isinstance(lang_texts[2], list):
                            chinese_text = lang_texts[2]
                            if chinese_text[0] is not None:  # 有角色名
                                output_file.write(f"{chinese_text[0]}：{chinese_text[1]}\n")
                            else:  # 无角色名的叙述文本
                                output_file.write(f"{chinese_text[1]}\n")

# 处理当前目录所有JSON文件
for filename in os.listdir('.'):
    if filename.endswith('.json'):
        parse(filename)

print("解析完成！")