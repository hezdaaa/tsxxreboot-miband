import os
import shutil
from pathlib import Path

from config import Config
from plain_dict import PlainDict
from utils.file_utils import get_unique_name, merge_dir
from utils.krkr_hxv4_hash import set_hashlib, get_file_hash, get_path_hash

current_config = Config(
    project_dir=Path(__file__).resolve().parent,
# 在这里更改目录配置：
    rename_dir=Path(r"C:\Users\MLChinoo\Desktop\3lj_data_full")
# 结束
)
set_hashlib(current_config)

dictionary = (PlainDict(
    config=current_config,
    pathnames=[
        "/"
    ],
    filenames=[
        "base.stage",
        "cglist.csv",
        "soundlist.csv",
        "charvoice.csv",
        "imagediffmap.csv",
        "savelist.csv",
        "scenelist.csv",
        "replay.ks",
        "_chthum_index.pbd"
    ]
)
# 在这里添加明文字典来源：
              #.from_unobfuscated_directory(r"C:\Users\MLChinoo\Desktop\3lj_data")
              .scan_psb_and_decompile(r"C:\Users\MLChinoo\Desktop\3lj_data_full\scn")
              #.from_base_stage(r"C:\Users\MLChinoo\Desktop\3lj_data_full\patch\base.stage")
              #.from_cglist_csv(r"C:\Users\MLChinoo\Desktop\3lj_data_full\patch\cglist.csv")
              #.from_soundlist_csv(r"C:\Users\MLChinoo\Desktop\3lj_data_full\data\main\soundlist.csv")
              #.add_char_sys_voices(r"C:\Users\MLChinoo\Desktop\3lj_data_full\data\main\charvoice.csv")
              #.from_imagediffmap_csv(r"C:\Users\MLChinoo\Desktop\3lj_data_full\patch\imagediffmap.csv")
              #.from_bgv_csv(r"C:\Users\MLChinoo\Desktop\3lj_data_full\voice")
              #.from_savelist_csv(r"C:\Users\MLChinoo\Desktop\3lj_data_full\data\main\savelist.csv")
              #.from_scenelist_csv(r"C:\Users\MLChinoo\Desktop\3lj_data_full\data\main\scenelist.csv")
              #.from_krkrdump_logs(r"Z:\游戏存档\lllj krkrdump")
              #.find_missing_voices([
              #    r"C:\Users\MLChinoo\Desktop\3lj_data_full\voice",
              #    r"C:\Users\MLChinoo\Desktop\3lj_data_full\voice2",
              #    r"C:\Users\MLChinoo\Desktop\3lj_data_full\patch"
              #])
              #.add_movies(r"C:\Users\MLChinoo\Desktop\3lj_data_full\data\scenario\replay.ks")
              #.from_stand_files(r"C:\Users\MLChinoo\Desktop\3lj_data_full\fgimage")
              #.from_pbd_files(r"C:\Users\MLChinoo\Desktop\3lj_data_full\fgimage")
              #.from_chthum_index_pbd(r"C:\Users\MLChinoo\Desktop\3lj_data_full\data\thum\chthum\_chthum_index.pbd")
# 结束
              .duplicate_lower()
              )

path_hash_map = {}
file_hash_map = {}
if not os.path.exists("HxNames.lst"):
    open("HxNames.lst", mode="w", encoding="UTF-8")
with open("HxNames.lst", mode="r", encoding="UTF-8") as h:
    h_lines = h.readlines()
    for line in h_lines:
        if line.strip() == "":
            continue
        assert len(splitted := line.replace("\n", "").split(":")) == 2, line
        hx_hash, hx_name = splitted
        if len(hx_hash) == 16:  # path
            path_hash_map[hx_name] = hx_hash
        elif len(hx_hash) == 64:  # file
            file_hash_map[hx_name] = hx_hash
        else:
            raise Exception(hx_hash)

path_to_hash: set = dictionary.pathname_plaintexts - set(path_hash_map.keys())
file_to_hash: set = dictionary.filename_plaintexts - set(file_hash_map.keys())
print(f"新增hash：")
for to_hash in (path_to_hash, file_to_hash):
    for t in to_hash:
        print(t)
print()

if True:
    for pathname in path_to_hash:
        pathname = pathname.strip().replace("\ufeff", "")  # remove bom
        if pathname != "":
            assert "/" in pathname
        path_hash_map[pathname] = get_path_hash(pathname)
    for filename in file_to_hash:
        filename = filename.strip().replace("\ufeff", "")  # remove bom
        file_hash_map[filename] = get_file_hash(filename)
else:
    # krkr_hxv4_dumphash在命令运行目录下生成文件，而不是游戏目录下
    with (open("files.txt", "w", encoding="utf-16le") as f,
          open("dirs.txt", "w", encoding="utf-16le") as d):
        for pathname_plaintext in path_to_hash:
            d.write(f"{pathname_plaintext}\n")
        for filename_plaintext in file_to_hash:
            f.write(f"{filename_plaintext}\n")
    
    os.startfile(config.game_exe)
    input("计算完成后手动按回车继续：")
    
    with (open("files_match.txt", "r", encoding="utf-16le") as fm,
          open("dirs_match.txt", "r", encoding="utf-16le") as dm):
    
        fm_lines = fm.readlines()
        for line in fm_lines:
            line = line.replace("\ufeff", "")  # remove bom
            if line.strip() == "":
                continue
            if len(splitted := line.replace("\n", "").split(",")) != 2:
                print(f"illegal line ignored: {line}")
                continue
            hx_name, hx_hash = splitted
            file_hash_map[hx_name] = hx_hash
    
        dm_lines = dm.readlines()
        for line in dm_lines:
            line = line.replace("\ufeff", "")  # remove bom
            if line.strip() == "":
                continue
            if len(splitted := line.replace("\n", "").split(",")) != 2:
                print(f"illegal line ignored: {line}")
                continue
            hx_name, hx_hash = splitted
            path_hash_map[hx_name] = hx_hash

with open("HxNames.lst", mode="w", encoding="UTF-8") as h:
    for hash_map in (path_hash_map, file_hash_map):
        for name, hash in hash_map.items():
            if name.strip() == "":
                continue
            h.write(f"{hash}:{name}\n")

if current_config.rename_dir != "":
    renamed_file_count = 0
    renamed_dir_count = 0
    hash_path_map = {value: key for key, value in path_hash_map.items()}
    hash_file_map = {value: key for key, value in file_hash_map.items()}
    for root, dirs, files in os.walk(current_config.rename_dir, topdown=False):
        for f in files:
            filepath = os.path.join(root, f)
            if f in hash_file_map.keys():
                new_name = hash_file_map[f]
                new_path = os.path.join(root, new_name)
                new_path = get_unique_name(new_path)
                try:
                    os.rename(filepath, new_path)
                    renamed_file_count += 1
                    print(f"文件重命名成功: {Path(filepath).relative_to(current_config.rename_dir)} -> {Path(new_path).relative_to(current_config.rename_dir)}")
                except Exception as e:
                    print(f"文件重命名失败: {Path(filepath).relative_to(current_config.rename_dir)} -> {Path(new_path).relative_to(current_config.rename_dir)}，原因: {e}")
        for d in dirs:
            dirpath = os.path.join(root, d)
            if d in hash_path_map.keys():
                assert hash_path_map[d][-1] == "/"
                target_rel_path = hash_path_map[d].rstrip("/\\")  # locale/jp
                dest_path = os.path.join(root, target_rel_path)  # .../locale/jp

                parent_dir = os.path.dirname(dest_path)  # .../locale
                os.makedirs(parent_dir, exist_ok=True)

                try:
                    if os.path.exists(dest_path):
                        merge_dir(dirpath, dest_path)
                    else:
                        shutil.move(dirpath, dest_path)
                    renamed_dir_count += 1
                    print(f"目录重命名成功: {Path(dirpath).relative_to(current_config.rename_dir)} -> {Path(dest_path).relative_to(current_config.rename_dir)}")
                except Exception as e:
                    print(f"目录重命名失败: {Path(dirpath).relative_to(current_config.rename_dir)} -> {Path(dest_path).relative_to(current_config.rename_dir)}，原因: {e}")
    print(f"重命名完成：共重命名文件 {renamed_file_count} 个，目录 {renamed_dir_count} 个")
