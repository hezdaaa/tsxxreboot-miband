from pathlib import Path

class Config:
    # game_dir = r"D:\gals\天使嚣嚣 hf"
    # game_exe = os.path.join(game_dir, "tenshi_sz.exe")
    
    project_dir: Path
    rename_dir: Path
    
    psbdecompile_exe = r"binaries/psb_decompile/PsbDecompile.exe"
    pbd2json_exe = r"binaries/pbd2json.exe"
    krkrhxv4hash_dll = r"binaries/KrkrHxv4Hash.dll"
    
    temp_dir = "temp/"
    psb_type_cache_pkl = "psb_type_cache.pkl"
    
    def __init__(self, project_dir, rename_dir):
        self.project_dir = Path(project_dir)
        self.rename_dir = Path(rename_dir)
        self.psbdecompile_exe = self.project_dir / self.psbdecompile_exe
        self.pbd2json_exe = self.project_dir / self.pbd2json_exe
        self.krkrhxv4hash_dll = self.project_dir / self.krkrhxv4hash_dll
        self.temp_dir = self.project_dir / self.temp_dir
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.psb_type_cache_pkl = self.temp_dir / self.psb_type_cache_pkl
