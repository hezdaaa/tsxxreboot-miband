import json, os

def reinsert_text(txt_file, json_file):
    # 读取处理后的文本
    with open(txt_file, 'r', encoding='utf-8') as f:
        # 过滤空行并移除换行符
        new_texts = [line.strip() for line in f.readlines() if line.strip()]
    
    # 读取原始JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    text_index = 0
    for scene in data['scenes']:
        if 'texts' in scene:
            for text_block in scene['texts']:
                # 只处理包含文本的区块
                if isinstance(text_block, list) and len(text_block) > 2 and isinstance(text_block[2], list):
                    lang_texts = text_block[2]
                    if len(lang_texts) >= 3 and isinstance(lang_texts[2], list) and text_index < len(new_texts):
                        # 分离角色名和内容
                        current_line = new_texts[text_index]
                        if '：' in current_line:
                            speaker, content = current_line.split('：', 1)
                            # 保持原始null结构
                            lang_texts[2][0] = speaker if speaker else None
                            lang_texts[2][1] = content
                        else:
                            # 无角色名的文本
                            lang_texts[2][0] = None
                            lang_texts[2][1] = current_line
                        text_index += 1
    
    # 保存更新后的JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# 用户交互
print("JSON文本重新插入工具")
mode = input("选择模式:\n1) 批量处理\n2) 单文件处理\n> ")

if mode == '1':
    for filename in os.listdir('.'):
        if filename.endswith('.json'):
            txt_file = f"parsed/{os.path.splitext(filename)[0]}.txt"
            if os.path.exists(txt_file):
                reinsert_text(txt_file, filename)
                print(f"已处理: {filename}")
            else:
                print(f"找不到匹配的文本文件: {txt_file}")
elif mode == '2':
    json_file = input("输入JSON文件名: ")
    txt_file = input("输入文本文件名: ")
    if os.path.exists(json_file) and os.path.exists(txt_file):
        reinsert_text(txt_file, json_file)
        print("文件处理完成!")
    else:
        print("错误: 文件不存在")
else:
    print("无效选择")

print("操作完成!")