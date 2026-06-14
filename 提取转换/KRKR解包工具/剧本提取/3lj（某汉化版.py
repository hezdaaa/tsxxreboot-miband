#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from pathlib import Path

OUT_DIR = Path('parsed')
OUT_DIR.mkdir(exist_ok=True)

def extract(json_file: Path):
    data = json.loads(json_file.read_text(encoding='utf-8'))
    out_file = OUT_DIR / f'{json_file.stem}_cn.txt'

    with out_file.open('w', encoding='utf-8') as f:
        for scene in data.get('scenes', []):
            for entry in scene.get('texts', []):
                if isinstance(entry, list) and len(entry) >= 2:
                    block = entry[1]
                    if isinstance(block, list) and len(block) >= 1:
                        inner = block[0]
                        if isinstance(inner, list) and len(inner) >= 2:
                            chinese = inner[1]
                            if chinese and str(chinese).strip():
                                name = entry[0] if isinstance(entry[0], str) else ''
                                # 旁白处理 + 格式调整
                                if not name:
                                    name = 'none'
                                f.write(f'{name}:{chinese}\n')
    print(f'saved -> {out_file}')

def main():
    for jf in Path('.').glob('*.json'):
        extract(jf)
    print('All finished!')

if __name__ == '__main__':
    main()