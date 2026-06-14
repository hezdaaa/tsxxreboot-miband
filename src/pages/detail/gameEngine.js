import file from '@system.file'

export default class GameEngine {
  constructor() {
    this.scripts = {};                    // 脚本存储，使用稀疏数组模式
    this.isLoaded = false;               
    this.loadPromise = null;             
    this.chunkSize = 500;                
    this.maxRetries = 2;                 
    this.retryDelay = 150;               // 进一步降低延迟
    
    // 极简内存管理
    this.loadedChunks = {};              // 只标记已加载的块
    this.currentChunk = 1;               
    this.pendingLoads = {};              // 正在加载的块 {chunkNumber: true}
    
    // 内存监控
    this.totalScriptsCount = 0;
    this.lastMemoryCheck = 0;
  }

  // 异步加载游戏脚本（极简版）
  async loadGameScript() {
    if (this.loadPromise) {
      return this.loadPromise;
    }

    if (this.isLoaded) {
      return true;
    }

    this.loadPromise = new Promise(async (resolve) => {
      try {
        console.log('启动游戏脚本加载...');
        this.scripts = {};
        this.loadedChunks = {};
        
        // 只加载第一个块的最小版本
        await this.loadMinimalChunk(1);
        
        this.isLoaded = true;
        console.log('游戏脚本极简加载完成');
        resolve(true);
      } catch (error) {
        console.error('游戏脚本加载失败，使用备用脚本:', error);
        this.scripts = this.getEssentialScripts();
        this.isLoaded = true;
        console.log('使用备用脚本数据');
        resolve(true);
      } finally {
        this.loadPromise = null;
      }
    });

    return this.loadPromise;
  }

  // 加载最小化块（只解析当前需要的脚本）
  async loadMinimalChunk(chunkNumber) {
    if (this.loadedChunks[chunkNumber]) {
      return true;
    }

    // 避免重复加载
    if (this.pendingLoads[chunkNumber]) {
      return new Promise((resolve) => {
        const checkInterval = setInterval(() => {
          if (this.loadedChunks[chunkNumber]) {
            clearInterval(checkInterval);
            resolve(true);
          }
        }, 50);
      });
    }

    this.pendingLoads[chunkNumber] = true;
    
    return new Promise((resolve) => {
      const fileName = `/common/script/scriptData${chunkNumber}.txt`;
      
      file.readText({
        uri: fileName,
        success: (data) => {
          try {
            const jsonText = typeof data === 'string' ? data : (data.text || '');
            const chunkScripts = this.parseChunkMinimal(jsonText, chunkNumber);
            
            // 只添加必要的脚本，不保存整个对象
            this.addScriptsSparse(chunkScripts);
            this.loadedChunks[chunkNumber] = true;
            this.totalScriptsCount += Object.keys(chunkScripts).length;
            
            console.log(`块 ${chunkNumber} 精简加载完成，新增 ${Object.keys(chunkScripts).length} 个脚本`);
            
            // 立即清理不再需要的块
            this.cleanupOldChunks(chunkNumber);
            
            resolve(true);
          } catch (error) {
            console.error(`处理块 ${chunkNumber} 失败:`, error);
            // 加载失败也标记，避免重复尝试
            this.loadedChunks[chunkNumber] = true;
            resolve(false);
          } finally {
            delete this.pendingLoads[chunkNumber];
          }
        },
        fail: (error) => {
          console.error(`加载块 ${chunkNumber} 失败:`, error);
          this.loadedChunks[chunkNumber] = true;
          delete this.pendingLoads[chunkNumber];
          resolve(false);
        }
      });
    });
  }

  // 极简JSON解析
  parseChunkMinimal(jsonText, chunkNumber) {
    if (!jsonText || jsonText.trim() === '') {
      return {};
    }
    
    let text = jsonText.trim();
    
    // 移除BOM头
    if (text.charCodeAt(0) === 0xFEFF) {
      text = text.substring(1);
    }
    
    // 快速解析（不使用try-catch，减少开销）
    if (text.startsWith('{') && text.endsWith('}')) {
      try {
        return JSON.parse(text);
      } catch (e) {
        console.error(`解析块 ${chunkNumber} JSON失败:`, e);
        return {};
      }
    }
    
    return {};
  }

  // 稀疏添加脚本（不复制整个对象）
  addScriptsSparse(newScripts) {
    // 直接引用，避免深拷贝
    for (const key in newScripts) {
      if (newScripts.hasOwnProperty(key)) {
        this.scripts[key] = newScripts[key];
      }
    }
  }

  // 清理旧的块
  cleanupOldChunks(currentChunk) {
    // 只保留当前块和最多1个相邻块
    const keepChunks = {
      [currentChunk]: true,
      [currentChunk - 1]: true,
      [currentChunk + 1]: true
    };
    
    // 找出并清理不需要的块
    for (const chunk in this.loadedChunks) {
      const chunkNum = parseInt(chunk);
      if (!keepChunks[chunkNum]) {
        this.removeChunkScripts(chunkNum);
        delete this.loadedChunks[chunk];
      }
    }
  }

  // 移除块的脚本
  removeChunkScripts(chunkNumber) {
    const startId = (chunkNumber - 1) * this.chunkSize + 1;
    const endId = chunkNumber * this.chunkSize;
    
    let removed = 0;
    for (let id = startId; id <= endId; id++) {
      const key = id.toString();
      if (this.scripts[key]) {
        delete this.scripts[key];
        removed++;
      }
    }
    
    if (removed > 0) {
      console.log(`清理块 ${chunkNumber}，释放 ${removed} 个脚本`);
    }
  }

  // 智能按需加载
  async smartLoadForProgress(progressId) {
    const targetChunk = Math.ceil(progressId / this.chunkSize);
    
    // 更新当前块
    if (targetChunk !== this.currentChunk) {
      this.currentChunk = targetChunk;
    }
    
    // 加载当前块（如果需要）
    if (!this.loadedChunks[targetChunk]) {
      await this.loadMinimalChunk(targetChunk);
    }
    
    // 计算是否需要预加载
    const positionInChunk = progressId % this.chunkSize || this.chunkSize;
    
    // 距离边界10条时预加载
    if (positionInChunk >= this.chunkSize - 10) {
      const nextChunk = targetChunk + 1;
      if (!this.loadedChunks[nextChunk] && !this.pendingLoads[nextChunk]) {
        setTimeout(() => {
          this.loadMinimalChunk(nextChunk).catch(() => {});
        }, 100);
      }
    } else if (positionInChunk <= 10 && targetChunk > 1) {
      const prevChunk = targetChunk - 1;
      if (!this.loadedChunks[prevChunk] && !this.pendingLoads[prevChunk]) {
        setTimeout(() => {
          this.loadMinimalChunk(prevChunk).catch(() => {});
        }, 100);
      }
    }
  }

  // 根据进度ID获取脚本（主入口）- 移除 x, y, z 字段，增加 c5, c5t 支持
  async getScript(progressId) {
    const id = progressId.toString();
    
    // 确保脚本已加载
    if (!this.isLoaded) {
      return this.getFallbackScript(progressId);
    }
    
    // 智能加载相关块
    await this.smartLoadForProgress(progressId);
    
    // 获取脚本
    const script = this.scripts[id];
    if (!script) {
      console.warn(`脚本 ${progressId} 不存在`);
      return this.getFallbackScript(progressId);
    }
    
    // 格式化输出（只返回页面需要的字段）
    return {
      id: progressId,
      background: script.b ? `/common/bcgi/${script.b}.jpg` : "",
      character: script.c ? `/common/cimg/${script.c}.png` : "",
      cg: script.cg ? `/common/evig/${script.cg}` : "",
      speaker: script.s || "",
      text: script.t || "",
      z: script.z || 0,
      choose: !!script.co,
      choose1: script.c1 || "",
      choose2: script.c2 || "",
      choose3: script.c3 || "",
      choose4: script.c4 || "",
      choose5: script.c5 || "",          // 第五个选项文本
      choose1To: script.c1t || progressId,
      choose2To: script.c2t || progressId,
      choose3To: script.c3t || progressId,
      choose4To: script.c4t || progressId,
      choose5To: script.c5t || progressId // 第五个选项跳转目标
    };
  }

  // 备用脚本（极简）
  getFallbackScript(progressId = 0) {
    return {
      id: progressId,
      background: "/common/bcgi/画面_白.jpg",
      character: "",
      cg: "",
      speaker: "",
      text: "（脚本加载失败，显示备用内容）",
      z: 0,
      choose: false,
      choose1: "",
      choose2: "",
      choose3: "",
      choose4: "",
      choose5: "",
      choose1To: progressId || 0,
      choose2To: progressId || 0,
      choose3To: progressId || 0,
      choose4To: progressId || 0,
      choose5To: progressId || 0
    };
  }

  // 必要脚本（仅用于启动）
  getEssentialScripts() {
    return {
      "1": { b: "異世界_前景a", s: "系统", t: "游戏启动中..." },
      "2": { b: "異世界_前景a", s: "", t: "请稍候..." },
      "3": { b: "異世界_前景a", s: "", t: "正在初始化..." }
    };
  }

  // 检查是否存在下一个脚本
  hasNext(progressId) {
    const nextId = (parseInt(progressId) + 1).toString();
    return this.scripts.hasOwnProperty(nextId);
  }

  // 获取下一个进度ID
  getNextProgressId(progressId) {
    const nextId = parseInt(progressId) + 1;
    return this.scripts.hasOwnProperty(nextId.toString()) ? nextId : null;
  }

  // 获取总进度数
  getTotalProgress() {
    return this.totalScriptsCount;
  }

  // 强制内存清理
  forceCleanup() {
    const currentChunk = this.currentChunk;
    
    // 只保留当前块的脚本
    const keepStart = (currentChunk - 1) * this.chunkSize + 1;
    const keepEnd = currentChunk * this.chunkSize;
    
    const newScripts = {};
    let kept = 0;
    
    for (let id = keepStart; id <= keepEnd; id++) {
      const key = id.toString();
      if (this.scripts[key]) {
        newScripts[key] = this.scripts[key];
        kept++;
      }
    }
    
    this.scripts = newScripts;
    this.loadedChunks = { [currentChunk]: true };
    this.totalScriptsCount = kept;
    
    console.log(`强制内存清理完成，保留 ${kept} 个脚本`);
  }

  // 获取内存状态
  getMemoryStatus() {
    const loadedChunksList = [];
    for (const chunk in this.loadedChunks) {
      loadedChunksList.push(parseInt(chunk));
    }
    
    return {
      loadedChunks: loadedChunksList.length,
      totalScripts: this.totalScriptsCount,
      currentChunk: this.currentChunk,
      memory: `${Math.round(this.totalScriptsCount * 0.3)}KB` // 更保守的估计
    };
  }
  
  // 预加载范围（用于快进快退）
  async preloadRange(startId, endId) {
    const startChunk = Math.ceil(startId / this.chunkSize);
    const endChunk = Math.ceil(endId / this.chunkSize);
    
    // 限制预加载范围
    const maxPreload = 3; // 最多预加载3个块
    let loaded = 0;
    
    for (let chunk = startChunk; chunk <= endChunk && loaded < maxPreload; chunk++) {
      if (!this.loadedChunks[chunk]) {
        await this.loadMinimalChunk(chunk);
        loaded++;
      }
    }
    
    if (loaded > 0) {
      console.log(`预加载完成，加载了 ${loaded} 个块`);
    }
  }
  
  // 清空所有内存
  clearAll() {
    this.scripts = {};
    this.loadedChunks = {};
    this.pendingLoads = {};
    this.totalScriptsCount = 0;
    console.log('所有内存已清空');
  }
}