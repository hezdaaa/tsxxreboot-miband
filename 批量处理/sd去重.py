import os
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import defaultdict, Counter
import threading
import copy
import cv2
import numpy as np

# ------------------------------
# 稳定版：dHash 去重，兼容灰度图
# ------------------------------
def dhash(image, hash_size=8):
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    resized = cv2.resize(gray, (hash_size + 1, hash_size))
    diff = resized[:, 1:] > resized[:, :-1]
    return sum((1 << i) for i, v in enumerate(diff.flatten()) if v)

def hamming(a, b):
    return bin(a ^ b).count('1')

def load_image_fast(image_path):
    try:
        raw = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        return img
    except:
        return None

def find_duplicates_fast(image_paths, threshold_dist=3):
    hash_map = {}
    dup_map = {}
    valid = []
    for path in image_paths:
        img = load_image_fast(path)
        if img is None:
            continue
        h = dhash(img)
        hash_map[path] = h
        valid.append(path)
    for i, p1 in enumerate(valid):
        if p1 in dup_map:
            continue
        h1 = hash_map[p1]
        for p2 in valid[i+1:]:
            if p2 in dupMap:
                continue
            h2 = hash_map[p2]
            if hamming(h1, h2) <= threshold_dist:
                dup_map[p2] = p1
    return dup_map

# ------------------------------
# 主程序
# ------------------------------
class CGImageDedupTool:
    def __init__(self, root):
        self.root = root
        self.root.title("CG图片去重工具（稳定版）")
        self.root.geometry("1100x750")
        self.root.configure(bg='#1e1e1e')

        self.script_path = ""
        self.script_files = []
        self.all_data = {}
        self.cg_stats = Counter()
        self.cg_first_id = {}
        self.modified = False

        self.history = []
        self.history_limit = 20

        self.image_root = ""
        self.hash_threshold = tk.IntVar(value=3)

        self.create_widgets()
        self.setup_styles()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#1e1e1e', foreground='#d4d4d4', fieldbackground='#252526', selectbackground='#264f78')
        style.configure('TButton', background='#333333', foreground='#d4d4d4')
        style.map('TButton', background=[('active', '#555555')])

    def create_widgets(self):
        top_frame = ttk.LabelFrame(self.root, text="脚本文件夹（scriptData*.txt）", padding=10)
        top_frame.pack(fill="x", padx=10, pady=5)
        self.path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.path_var, width=60).pack(side="left", padx=(0,5), fill="x", expand=True)
        ttk.Button(top_frame, text="浏览", command=self.select_folder).pack(side="left", padx=2)
        ttk.Button(top_frame, text="加载脚本", command=self.load_scripts_thread).pack(side="left", padx=2)

        main_panel = ttk.Frame(self.root)
        main_panel.pack(fill="both", expand=True, padx=10, pady=5)

        left_frame = ttk.LabelFrame(main_panel, text="sd 开头 CG 统计", padding=5)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0,5))

        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill="x", pady=5)
        ttk.Label(search_frame, text="筛选:").pack(side="left")
        self.search_var = tk.StringVar()
        se = ttk.Entry(search_frame, textvariable=self.search_var)
        se.pack(side="left", fill="x", expand=True, padx=5)
        se.bind('<KeyRelease>', self.filter_list)

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame)
        sb.pack(side="right", fill="y")
        self.cg_listbox = tk.Listbox(
            list_frame, yscrollcommand=sb.set, font=("Consolas",10),
            bg='#252526', fg='#d4d4d4', selectbackground='#264f78', selectforeground='#fff'
        )
        self.cg_listbox.pack(side="left", fill="both", expand=True)
        sb.config(command=self.cg_listbox.yview)

        right_frame = ttk.LabelFrame(main_panel, text="图片管理", padding=10)
        right_frame.pack(side="right", fill="y", padx=(5,0))

        ttk.Label(right_frame, text="图片根目录:").grid(row=0, column=0, sticky="w", pady=5)
        self.image_root_var = tk.StringVar()
        ttk.Entry(right_frame, textvariable=self.image_root_var, width=25).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(right_frame, text="浏览", command=self.select_image_root).grid(row=0, column=2, padx=2)

        ttk.Label(right_frame, text="严格度(0最严):").grid(row=1, column=0, sticky="w", pady=5)
        scale = ttk.Scale(right_frame, from_=0, to=10, variable=self.hash_threshold, orient="h")
        scale.grid(row=1, column=1, pady=5, padx=5)
        self.thresh_lbl = ttk.Label(right_frame, text="3")
        self.thresh_lbl.grid(row=1, column=2)
        self.hash_threshold.trace_add('write', lambda *a: self.thresh_lbl.config(text=str(self.hash_threshold.get())))

        ttk.Button(right_frame, text="预览重复图片", command=self.preview_thread).grid(row=2, column=0, columnspan=3, pady=5)
        ttk.Button(right_frame, text="执行去重", command=self.execute_thread).grid(row=3, column=0, columnspan=3, pady=5)
        ttk.Button(right_frame, text="清理无效CG引用", command=self.clean_invalid).grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Label(right_frame, text="预览:", font=('',10,'bold')).grid(row=5, column=0, columnspan=3, sticky="w", pady=(15,0))
        self.preview = scrolledtext.ScrolledText(right_frame, width=40, height=12, bg='#252526', fg='#d4d4d4', font=("Consolas",9))
        self.preview.grid(row=6, column=0, columnspan=3, pady=5)
        self.preview.insert('1.0', "加载脚本 → 设置图片目录 → 预览 → 执行\n")
        self.preview.config(state='disabled')

        status = ttk.Frame(self.root)
        status.pack(side="bottom", fill="x", padx=10, pady=5)
        self.status_lbl = ttk.Label(status, text="就绪", foreground="#6a9955")
        self.status_lbl.pack(side="left")
        self.mod_lbl = ttk.Label(status, text="", foreground="#ffcc00")
        self.mod_lbl.pack(side="right")
        ttk.Button(status, text="保存", command=self.save_all).pack(side="right", padx=5)
        ttk.Button(status, text="撤销（CG）", command=self.undo).pack(side="right", padx=5)

        self.cg_listbox.insert(tk.END, "请先加载脚本")

    def cg_to_path(self, cg):
        if not cg:
            return None
        if cg.lower().endswith(('.png','.jpg','.jpeg')):
            return os.path.join(self.image_root, cg)
        else:
            return os.path.join(self.image_root, cg + ".png")

    def select_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.script_path = d
            self.path_var.set(d)

    def select_image_root(self):
        d = filedialog.askdirectory()
        if d:
            self.image_root = d
            self.image_root_var.set(d)

    def load_scripts_thread(self):
        if not self.script_path:
            messagebox.showwarning("提示", "请先选择脚本文件夹")
            return
        self.status_lbl.config(text="加载中...")
        self.cg_listbox.delete(0, tk.END)
        self.cg_listbox.insert(tk.END, "加载中...")
        threading.Thread(target=self.load_scripts, daemon=True).start()

    def load_scripts(self):
        try:
            files = sorted([
                os.path.join(self.script_path, f)
                for f in os.listdir(self.script_path)
                if f.lower().startswith("scriptdata") and f.lower().endswith(".txt")
            ])
            if not files:
                self.root.after(0, lambda: messagebox.showwarning("警告", "未找到 scriptData*.txt"))
                self.root.after(0, lambda: self.status_lbl.config(text="未找到文件"))
                return

            all_data = {}
            cg_counter = Counter()
            first_id = {}

            for f in files:
                for enc in ['utf-8-sig','utf-8','gbk','gb2312']:
                    try:
                        with open(f, encoding=enc) as fp:
                            data = json.load(fp)
                        break
                    except:
                        continue
                else:
                    continue

                for k, v in data.items():
                    all_data[k] = v
                    cg = v.get('cg','')
                    if cg and cg.lower().startswith('sd'):
                        cg_counter[cg] += 1
                        if cg not in first_id or int(k) < int(first_id[cg]):
                            first_id[cg] = k

            self.root.after(0, lambda: self._load_done(all_data, cg_counter, first_id, files))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("加载失败", str(e)))

    def _load_done(self, all_data, counter, first_id, files):
        self.all_data = all_data
        self.cg_stats = counter
        self.cg_first_id = first_id
        self.script_files = files
        self.filter_list()
        self.status_lbl.config(text=f"完成：{len(all_data)}条，{len(counter)}个CG")
        self.modified = False
        self.mod_lbl.config(text="")

    def filter_list(self, e=None):
        s = self.search_var.get().lower()
        self.cg_listbox.delete(0, tk.END)
        for name, cnt in sorted(self.cg_stats.items(), key=lambda x: (-x[1],x[0])):
            if s and s not in name.lower():
                continue
            fid = self.cg_first_id.get(name, '?')
            self.cg_listbox.insert(tk.END, f"[{fid}] {name} ({cnt}次)")

    def push_history(self):
        if len(self.history) >= self.history_limit:
            self.history.pop(0)
        self.history.append(copy.deepcopy(self.all_data))

    def undo(self):
        if not self.history:
            messagebox.showinfo("提示", "没有可撤销操作")
            return
        self.all_data = copy.deepcopy(self.history.pop())
        self.modified = True
        self.mod_lbl.config(text="未保存")
        self.rebuild_stats()

    def rebuild_stats(self):
        cnt = Counter()
        fid = {}
        for k, v in self.all_data.items():
            cg = v.get('cg','')
            if cg and cg.lower().startswith('sd'):
                cnt[cg] += 1
                if cg not in fid or int(k) < int(fid[cg]):
                    fid[cg] = k
        self.cg_stats = cnt
        self.cg_first_id = fid
        self.filter_list()

    def save_all(self):
        if not self.modified:
            messagebox.showinfo("提示", "无修改需要保存")
            return
        try:
            for path in self.script_files:
                base = os.path.basename(path)
                m = re.search(r'(\d+)', base)
                if not m:
                    continue
                n = int(m.group(1))
                start, end = (n-1)*500+1, n*500
                chunk = {str(i): self.all_data[str(i)] for i in range(start, end+1) if str(i) in self.all_data}
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, ensure_ascii=False, indent=2)
            self.modified = False
            self.mod_lbl.config(text="")
            self.history.clear()
            messagebox.showinfo("成功", "保存完成")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def clean_invalid(self):
        if not self.image_root or not self.all_data:
            messagebox.showwarning("提示", "先加载脚本与图片目录")
            return
        invalid = set()
        for cg in self.cg_stats:
            p = self.cg_to_path(cg)
            if not os.path.isfile(p):
                invalid.add(cg)
        if not invalid:
            messagebox.showinfo("提示", "无无效CG")
            return
        cnt = sum(1 for v in self.all_data.values() if v.get('cg') in invalid)
        if not messagebox.askyesno("确认", f"将删除 {len(invalid)} 个无效CG，影响 {cnt} 条数据？"):
            return
        self.push_history()
        for v in self.all_data.values():
            if v.get('cg') in invalid:
                del v['cg']
        self.modified = True
        self.mod_lbl.config(text="未保存")
        self.rebuild_stats()
        messagebox.showinfo("完成", "无效CG已清理")

    def get_valid_image_paths(self):
        cg_set = set()
        for v in self.all_data.values():
            cg = v.get('cg','')
            if cg and cg.lower().startswith('sd'):
                cg_set.add(cg)
        paths = []
        missing = []
        for cg in cg_set:
            p = self.cg_to_path(cg)
            if os.path.isfile(p):
                paths.append(p)
            else:
                missing.append(cg)
        return paths, missing

    def preview_thread(self):
        if not self.image_root or not self.all_data:
            messagebox.showwarning("提示", "先加载脚本与图片目录")
            return
        self.status_lbl.config(text="扫描重复图片...")
        threading.Thread(target=self.preview_duplicates, daemon=True).start()

    def preview_duplicates(self):
        paths, missing = self.get_valid_image_paths()
        if missing:
            msg = f"缺失 {len(missing)} 个文件:\n" + "\n".join(missing[:10])
            self.root.after(0, lambda: messagebox.showwarning("缺失文件", msg))
        if len(paths) < 2:
            self.root.after(0, lambda: messagebox.showinfo("提示", "有效图片不足2张"))
            self.root.after(0, lambda: self.status_lbl.config(text="就绪"))
            return

        threshold = self.hash_threshold.get()
        dup_map = find_duplicates_fast(paths, threshold)

        if not dup_map:
            txt = f"严格度 {threshold}：未发现重复图片"
        else:
            txt = f"【重复预览】严格度={threshold}\n共 {len(dup_map)} 个重复\n\n"
            for dup, master in list(dup_map.items())[:30]:
                d = os.path.splitext(os.path.basename(dup))[0]
                m = os.path.splitext(os.path.basename(master))[0]
                txt += f"{d} → {m}\n"
            if len(dup_map) > 30:
                txt += f"...等 {len(dup_map)} 个"

        self.root.after(0, lambda: self._update_preview(txt))

    def _update_preview(self, txt):
        self.preview.config(state='normal')
        self.preview.delete('1.0', tk.END)
        self.preview.insert('1.0', txt)
        self.preview.config(state='disabled')
        self.status_lbl.config(text="预览完成")

    def execute_thread(self):
        if not self.image_root or not self.all_data:
            messagebox.showwarning("提示", "先加载脚本与图片目录")
            return
        if not messagebox.askyesno("确认执行", "将修改CG并删除图片，不可恢复！\n建议先备份！\n是否继续？"):
            return
        self.status_lbl.config(text="执行去重中...")
        threading.Thread(target=self.execute_duplicates, daemon=True).start()

    def execute_duplicates(self):
        paths, _ = self.get_valid_image_paths()
        if len(paths) < 2:
            self.root.after(0, lambda: messagebox.showinfo("提示", "图片数量不足"))
            self.root.after(0, lambda: self.status_lbl.config(text="就绪"))
            return

        threshold = self.hash_threshold.get()
        dup_map = find_duplicates_fast(paths, threshold)
        if not dup_map:
            self.root.after(0, lambda: messagebox.showinfo("提示", "未找到重复"))
            self.root.after(0, lambda: self.status_lbl.config(text="就绪"))
            return

        rename = {}
        for dup, master in dup_map.items():
            d = os.path.splitext(os.path.basename(dup))[0]
            m = os.path.splitext(os.path.basename(master))[0]
            rename[d] = m

        self.push_history()
        cnt = 0
        for v in self.all_data.values():
            cg = v.get('cg','')
            if cg in rename:
                v['cg'] = rename[cg]
                cnt += 1

        del_cnt = 0
        for p in dup_map:
            try:
                os.remove(p)
                del_cnt += 1
            except:
                pass

        self.modified = True
        self.root.after(0, lambda: self._exec_done(cnt, del_cnt, len(dup_map)))

    def _exec_done(self, cnt, del_cnt, total):
        self.mod_lbl.config(text="未保存")
        self.rebuild_stats()
        self.status_lbl.config(text="执行完成")
        messagebox.showinfo("完成", f"修改CG：{cnt} 处\n删除图片：{del_cnt}/{total}")

def find_duplicates_fast(image_paths, threshold_dist=3):
    hash_map = {}
    dup_map = {}
    valid = []
    for path in image_paths:
        img = load_image_fast(path)
        if img is None:
            continue
        h = dhash(img)
        hash_map[path] = h
        valid.append(path)
    for i, p1 in enumerate(valid):
        if p1 in dup_map:
            continue
        h1 = hash_map[p1]
        for p2 in valid[i+1:]:
            if p2 in dup_map:
                continue
            h2 = hash_map[p2]
            if hamming(h1, h2) <= threshold_dist:
                dup_map[p2] = p1
    return dup_map

def main():
    root = tk.Tk()
    app = CGImageDedupTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()
