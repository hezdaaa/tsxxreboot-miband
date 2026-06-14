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
        # 查找所有texts数组
        def find_texts(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "texts" and isinstance(value, list):
                        process_texts(value, output_file)
                    else:
                        find_texts(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_texts(item)
        
        def process_texts(texts_list, file):
            for text_block in texts_list:
                # 文本块结构: [speaker, [translations], ...]
                if isinstance(text_block, list) and len(text_block) > 1:
                    # 简体中文是第二个翻译块 (索引1)
                    translations = text_block[1]
                    if isinstance(translations, list) and len(translations) > 1:
                        chinese_translation = translations[1]
                        if isinstance(chinese_translation, list) and len(chinese_translation) > 1:
                            speaker = chinese_translation[0]
                            text = chinese_translation[1]
                            
                            # 处理带数字的文本 (如"「恭喜！真是件大喜事，嗯嗯」",14)
                            if isinstance(text, str) and ',' in text:
                                clean_text = text.split(',')[0].strip('"')
                            else:
                                clean_text = text
                            
                            if speaker:
                                file.write(f"{speaker}：{clean_text}\n")
                            else:
                                file.write(f"{clean_text}\n")
        
        find_texts(data)

# 处理当前目录所有JSON文件
for filename in os.listdir('.'):
    if filename.endswith('.json'):
        parse(filename)

print("解析完成！提取了角色名和简体中文文本")