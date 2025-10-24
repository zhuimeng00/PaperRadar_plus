# -*- coding: utf-8 -*-
"""
PyQt5 桌面 UI：可视化配置 PaperRadar
- 编辑保存 config.yaml（sources/priority/conferences/journals_issn/rss/categories 等）
- 设置推送时间、间隔天数；一键安装/更新/删除 Windows 计划任务
- 立即运行一次（调用 run_daily.ps1），并提供打开 logs/digests 的按钮
- 首次运行若缺少 run_daily.ps1，会自动写入“纯 ASCII 版”，避免中文编码导致的 PowerShell 解析错误
"""
import sys, os, subprocess, json, datetime
from pathlib import Path
import yaml

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QCheckBox, QFileDialog,
    QMessageBox, QSpinBox, QTimeEdit, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTime

# ---------- 路径与默认 ----------
PROJECT_DIR = Path(__file__).resolve().parent
# 若当前目录不含 paper_radar_plus.py，则回退到上一级作为项目根
if not (PROJECT_DIR / "paper_radar_plus.py").exists():
    if (PROJECT_DIR.parent / "paper_radar_plus.py").exists():
        PROJECT_DIR = PROJECT_DIR.parent
CONFIG_PATH = PROJECT_DIR / "config.yaml"
RUNNER_PS1  = PROJECT_DIR / "run_daily.ps1"
TASK_NAME   = "PaperRadar_Daily_UI"

DEFAULT_CONFIG = {
    "sources": {
        "arxiv": True,
        "openalex_conferences": True,
        "openalex_journals": True,
        "openreview": True,
        "rss": False
    },
    "priority": {
        "prefer_top_venues": True,
        "allow_repeat_fill": True,
        "repeat_lookback_days": 7,
        "repeat_label": "（重复推荐：首次推送 {date}）"
    },
    "conferences": [
        "CVPR","ICCV","ECCV","NeurIPS","ICLR","ICML","3DV","ICRA","IROS","RSS","SIGGRAPH","SIGGRAPH Asia"
    ],
    "journals_issn": [
        # TPAMI, IJCV, TVCG, TOG, TIP, TMM, ISPRS JPRS, RAS
        "0162-8828","0920-5691","1077-2626","0730-0301","1057-7149","1520-9210","0924-2716","0921-8890"
    ],
    "rss_urls": [],
    "output_dir": "./digests",
    "cache_path": "./cache.json",
    "since_days": 5,
    "max_per_query": 80,
    "target_total": 5,
    "per_category_max": 3,
    "summary_sentences": 3,
    "min_daily": 5,
    "fallback_days": 21,
}

DEFAULT_CATEGORIES_YAML = """categories:
  - name: "宏量点云去噪与精简"
    highlight: ["denoise","denoising","outlier","robust","MLS","bilateral","graph","sparse","downsample","decimation","simplification","voxel","FPS","curvature","diffusion","score-based","normal estimation"]
    arxiv_queries:
      - '((ti:"point cloud" OR abs:"point cloud" OR abs:LiDAR) AND (abs:denoise OR abs:denoising OR abs:"outlier removal" OR abs:simplification OR abs:decimation OR abs:downsampling OR abs:"farthest point sampling" OR abs:"voxel grid" OR abs:curvature OR abs:"normal estimation" OR abs:"score-based") AND (cat:cs.CV OR cat:cs.GR OR cat:cs.RO OR cat:eess.IV))'

  - name: "几何特征/原始体拟合（法线/曲率/原始体/描述子）"
    highlight: ["RANSAC","primitive","plane","cylinder","sphere","cone","torus","curvature","normal","descriptor","FPFH","SHOT","ISS","keypoint","skeleton","medial axis","SDF","implicit","3DGS","Gaussian Splatting"]
    arxiv_queries:
      - '((ti:"point cloud" OR abs:"point cloud") AND (abs:descriptor OR abs:FPFH OR abs:ISS OR abs:SHOT OR abs:"keypoint" OR abs:"normal estimation" OR abs:curvature OR abs:RANSAC OR abs:"primitive fitting" OR abs:SDF OR abs:implicit OR abs:"Gaussian Splatting") AND (cat:cs.CV OR cat:cs.GR OR cat:cs.RO))'

  - name: "CAD 对齐与尺寸/公差测量（Scan-to-CAD/配准/偏差）"
    highlight: ["CAD","scan-to-CAD","registration","alignment","ICP","TEASER","FGR","4PCS","measurement","metrology","tolerance","GD&T","deviation map","datum","calibration"]
    arxiv_queries:
      - '((ti:"point cloud" OR abs:"point cloud") AND (abs:CAD OR abs:"scan-to-CAD" OR abs:metrology OR abs:measurement OR abs:tolerance OR abs:"GD&T" OR abs:deviation OR abs:registration OR abs:alignment OR abs:ICP OR abs:TEASER OR abs:FGR OR abs:4PCS) AND (cat:cs.CV OR cat:cs.RO OR cat:cs.GR))'

  - name: "工业缺陷检测（3D/表面/装配）"
    highlight: ["defect","anomaly","inspection","NDT","weld","scratch","dent","crack","burr","roughness","porosity","delamination","leak","industrial component"]
    arxiv_queries:
      - '(((ti:"point cloud" OR abs:"point cloud" OR abs:LiDAR) OR (ti:mesh OR abs:mesh)) AND (abs:defect OR abs:anomaly OR abs:inspection OR abs:NDT OR abs:crack OR abs:scratch OR abs:dent OR abs:weld OR abs:porosity OR abs:roughness) AND (cat:cs.CV OR cat:eess.IV))'

  - name: "大规模点云高效表示与加速（工程可落地）"
    highlight: ["sparse convolution","Minkowski","octree","hash","voxel","streaming","out-of-core","tiling","multi-resolution","quantization","CUDA","kernel","real-time","throughput","memory"]
    arxiv_queries:
      - '((ti:"point cloud" OR abs:"point cloud") AND (abs:"sparse convolution" OR abs:Minkowski OR abs:octree OR abs:"voxel hashing" OR abs:streaming OR abs:"out-of-core" OR abs:"multi-resolution" OR abs:quantization OR abs:"real-time") AND (cat:cs.CV OR cat:cs.GR OR cat:cs.RO OR cat:eess.IV))'

  - name: "语义分割驱动的测量/检测（大尺寸零部件）"
    highlight: ["semantic segmentation","instance segmentation","panoptic","part segmentation","industrial","manufacturing","assembly","pipeline","measurement","large part","deviation"]
    arxiv_queries:
      - '((ti:"point cloud" OR abs:"point cloud") AND (abs:"semantic segmentation" OR abs:"instance segmentation" OR abs:panoptic OR abs:"part segmentation") AND (abs:industrial OR abs:manufacturing OR abs:assembly OR abs:"large part" OR abs:measurement) AND (cat:cs.CV OR cat:cs.RO))'
"""

ASCII_RUNNER_PS1_TEMPLATE = r'''# PaperRadar daily runner (UTF-8 logging; WinPS 5.1 compatible)
param(
  [int]$SinceDays = 2,
  [switch]$OpenDigest = $true
)

$ErrorActionPreference = "Stop"

# --- Project & Python ---
$ProjectDir = $PSScriptRoot
if (-not (Test-Path $ProjectDir)) { throw "Project directory not found: $ProjectDir" }
Set-Location $ProjectDir

$Py = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  if (Get-Command py.exe -ErrorAction SilentlyContinue)      { $Py = "py.exe" }
  elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { $Py = "python.exe" }
  else { throw "Python not found. Create venv and install deps first." }
}

# --- Log (force UTF-8; ensure BOM so VS Code/Notepad auto-detect) ---
$LogDir = Join-Path $ProjectDir "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$today = Get-Date -Format "yyyy-MM-dd"
$LogFile = Join-Path $LogDir ("run_" + $today + ".log")

# 先写一个 UTF-8（带 BOM）的头行，后续都以 UTF-8 追加
$CmdShow = "PaperRadar --run --since_days $SinceDays"
$now = Get-Date
$Header = "[{0:yyyy-MM-dd HH:mm:ss}{1}] RUN: {2}" -f $now, $now.ToString("zzz"), $CmdShow
if (Test-Path $LogFile) {
  # 已有当日日志：空一行后追加抬头（UTF-8）
  "`r`n$Header" | Add-Content -Path $LogFile -Encoding utf8
} else {
  # 首次生成当天日志：创建 UTF-8（带 BOM）文件
  $Header | Out-File -FilePath $LogFile -Encoding utf8
}
Write-Host $Header

# 控制台输出也切到 UTF-8
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom

# --- Run python (WinPS 5.1 用 Arguments；强制子进程走 UTF-8) ---
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName               = $Py
$psi.Arguments              = "`"$ProjectDir\paper_radar_plus.py`" --since_days $SinceDays"
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute        = $false
$psi.CreateNoWindow         = $true

# 让 .NET 以 UTF-8 解码子进程输出
$psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi.StandardErrorEncoding  = [System.Text.Encoding]::UTF8
# 让 Python 强制 UTF-8 输出
$psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
$psi.EnvironmentVariables["PYTHONUTF8"]       = "1"

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

# 交替读取 stdout/stderr，手动 tee 到控制台 + UTF-8 日志（追加）
$stdOut = $proc.StandardOutput
$stdErr = $proc.StandardError
while(-not $proc.HasExited -or -not $stdOut.EndOfStream -or -not $stdErr.EndOfStream) {
  if(-not $stdOut.EndOfStream) {
    $line = $stdOut.ReadLine()
    if($null -ne $line) { Write-Host $line; $line | Out-File -FilePath $LogFile -Append -Encoding utf8 }
  }
  if(-not $stdErr.EndOfStream) {
    $eline = $stdErr.ReadLine()
    if($null -ne $eline) { Write-Host $eline; $eline | Out-File -FilePath $LogFile -Append -Encoding utf8 }
  }
  Start-Sleep -Milliseconds 10
}
$ExitCode = $proc.ExitCode

# --- Summary / popup / open digest ---
$digest = Join-Path (Join-Path $ProjectDir "digests") ($today + ".md")
if (Test-Path $digest) { $msg = "Digest generated: " + $digest } else { $msg = "No digest. See log: " + $LogFile }
try { $wshell = New-Object -ComObject Wscript.Shell; $wshell.Popup($msg, 8, "PaperRadar", 64) | Out-Null } catch {}

if ($OpenDigest -and (Test-Path $digest)) {
  try {
    if (Get-Command code -ErrorAction SilentlyContinue)      { & code --reuse-window "$digest" }
    elseif (Get-Command typora.exe -ErrorAction SilentlyContinue) { & typora.exe "$digest" }
    elseif (Get-Command notepad.exe -ErrorAction SilentlyContinue){ & notepad.exe "$digest" }
    else { Invoke-Item "$digest" }
  } catch {}
}

exit $ExitCode
'''

# ---------- 工具函数 ----------
def ensure_runner_ps1():
    # 直接每次覆盖，确保升级到新脚本
    RUNNER_PS1.write_text(ASCII_RUNNER_PS1_TEMPLATE, encoding="utf-8")

def load_config():
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            cfg = {}
    # merge defaults（不覆盖已有）
    def merge(a,b):
        for k,v in b.items():
            if k not in a: a[k]=v
            elif isinstance(a[k], dict) and isinstance(v, dict):
                merge(a[k], v)
    merge(cfg, DEFAULT_CONFIG)
    if "categories" not in cfg:
        try:
            cats = yaml.safe_load(DEFAULT_CATEGORIES_YAML) or {}
            if "categories" in cats:
                cfg["categories"] = cats["categories"]
        except Exception:
            pass
    return cfg

def save_config(cfg):
    CONFIG_PATH.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

def parse_lines_to_list(text):
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

def run_cmd(cmd):
    """
    在 Windows 上：
    - 对 schtasks 等系统命令，用本地编码 (mbcs) 解码，避免中文提示乱码
    - 其它保持 UTF-8
    """
    enc = "utf-8"
    if os.name == "nt":
        low = (cmd or "").lower()
        if "schtasks" in low or low.strip().startswith("schtasks"):
            enc = "mbcs"   # 关键：用系统本地编码解码中文输出
    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True,
        encoding=enc,
        errors="replace"
    )
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out

def install_task(push_time:str, interval_days:int, since_for_task:int, interactive:bool=True, ru:str=None, rp:str=None):
    ensure_runner_ps1()
    runner = str(RUNNER_PS1).replace('"','`"')
    tr = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{runner}" -SinceDays {since_for_task}'
    base = f'schtasks /Create /TN "{TASK_NAME}" /TR "{tr}" /SC DAILY /MO {interval_days} /ST {push_time} /F'
    if ru and rp:
        # 不弹窗（非交互），但可在未登录时运行
        cmd = base + f' /RU "{ru}" /RP "{rp}"'
    else:
        # 交互模式，只有登录状态下可弹窗
        cmd = base + ' /IT'
    return run_cmd(cmd)

def uninstall_task():
    # 先检测是否存在；不存在就直接视为成功，避免报错弹乱码
    code_q, out_q = run_cmd(f'schtasks /Query /TN "{TASK_NAME}"')
    if code_q != 0:
        # 查询失败，多半是任务不存在；直接返回成功语义
        return 0, f'计划任务 "{TASK_NAME}" 不存在，无需删除。'
    # 确认存在再删
    return run_cmd(f'schtasks /Delete /TN "{TASK_NAME}" /F')

def run_once(since_days:int):
    ensure_runner_ps1()
    cmd = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{RUNNER_PS1}" -SinceDays {since_days}'
    return run_cmd(cmd)

def open_folder(p:Path):
    if p.exists():
        subprocess.Popen(f'explorer "{str(p)}"', shell=True)

# ---------- 主界面 ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PaperRadar 配置面板（PyQt）")
        self.resize(1024, 720)
        self.cfg = load_config()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_tab_plan()
        self._build_tab_sources()
        self._build_tab_params()
        self._build_tab_categories()
        self._build_tab_email()

        self.statusBar().showMessage("加载完成")
        ensure_runner_ps1()

    # --- Tab 1：计划/推送 ---
    def _build_tab_plan(self):
        w = QWidget(); lay = QVBoxLayout(w)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("推送时间（HH:MM）:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(8,0))
        row1.addWidget(self.time_edit)

        row1.addWidget(QLabel("间隔天数:"))
        self.interval_spin = QSpinBox(); self.interval_spin.setRange(1, 365); self.interval_spin.setValue(1)
        row1.addWidget(self.interval_spin)

        row1.addWidget(QLabel("SinceDays（计划任务传参）:"))
        self.since_task_spin = QSpinBox(); self.since_task_spin.setRange(1, 60); self.since_task_spin.setValue(self.cfg.get("since_days", 5))
        row1.addWidget(self.since_task_spin)
        row1.addStretch()
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_install = QPushButton("创建/更新计划任务")
        self.btn_runonce = QPushButton("立即运行一次")
        self.btn_uninstall = QPushButton("删除计划任务")
        row2.addWidget(self.btn_install); row2.addWidget(self.btn_runonce); row2.addWidget(self.btn_uninstall); row2.addStretch()
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        self.btn_open_logs = QPushButton("打开 logs 目录")
        self.btn_open_digests = QPushButton("打开 digests 目录")
        row3.addWidget(self.btn_open_logs); row3.addWidget(self.btn_open_digests); row3.addStretch()
        lay.addLayout(row3)

        # 可选的 /RU /RP（未登录也运行）
        grp = QGroupBox("可选：不登录也运行（会禁用弹窗）")
        g = QGridLayout(grp)
        g.addWidget(QLabel("运行账户（/RU）："), 0, 0)
        self.ru_edit = QLineEdit(); g.addWidget(self.ru_edit, 0, 1)
        g.addWidget(QLabel("密码（/RP）："), 1, 0)
        self.rp_edit = QLineEdit(); self.rp_edit.setEchoMode(QLineEdit.Password); g.addWidget(self.rp_edit, 1, 1)
        lay.addWidget(grp)

        # 事件
        self.btn_install.clicked.connect(self._on_install)
        self.btn_uninstall.clicked.connect(self._on_uninstall)
        self.btn_runonce.clicked.connect(self._on_runonce)
        self.btn_open_logs.clicked.connect(lambda: open_folder(PROJECT_DIR / "logs"))
        self.btn_open_digests.clicked.connect(lambda: open_folder(PROJECT_DIR / "digests"))

        self.tabs.addTab(w, "计划与推送")

    # --- Tab 2：来源/优先级 ---
    def _build_tab_sources(self):
        w = QWidget(); lay = QVBoxLayout(w)

        # sources
        src_box = QGroupBox("来源选择")
        g1 = QGridLayout(src_box)
        self.cb_conf = QCheckBox("顶会（OpenAlex）")
        self.cb_jour = QCheckBox("顶刊（OpenAlex）")
        self.cb_openr = QCheckBox("OpenReview")
        self.cb_arxiv = QCheckBox("arXiv")
        self.cb_rss = QCheckBox("RSS")
        self.cb_conf.setChecked(self.cfg["sources"].get("openalex_conferences", True))
        self.cb_jour.setChecked(self.cfg["sources"].get("openalex_journals", True))
        self.cb_openr.setChecked(self.cfg["sources"].get("openreview", True))
        self.cb_arxiv.setChecked(self.cfg["sources"].get("arxiv", True))
        self.cb_rss.setChecked(self.cfg["sources"].get("rss", False))
        for i, wgt in enumerate([self.cb_conf, self.cb_jour, self.cb_openr, self.cb_arxiv, self.cb_rss]):
            g1.addWidget(wgt, 0, i)
        lay.addWidget(src_box)

        # priority
        pr_box = QGroupBox("优先级与重复补齐")
        g2 = QGridLayout(pr_box)
        self.cb_prefer = QCheckBox("顶会/顶刊优先（不足再从 arXiv 补齐）")
        self.cb_prefer.setChecked(self.cfg["priority"].get("prefer_top_venues", True))
        self.cb_repeat = QCheckBox("允许重复补齐（配额不足时用历史）")
        self.cb_repeat.setChecked(self.cfg["priority"].get("allow_repeat_fill", True))
        g2.addWidget(self.cb_prefer, 0, 0, 1, 2)
        g2.addWidget(self.cb_repeat, 1, 0, 1, 2)

        g2.addWidget(QLabel("重复回溯天数"), 2, 0)
        self.spin_repeat_days = QSpinBox(); self.spin_repeat_days.setRange(1, 60)
        self.spin_repeat_days.setValue(self.cfg["priority"].get("repeat_lookback_days", 7))
        g2.addWidget(self.spin_repeat_days, 2, 1)

        g2.addWidget(QLabel("重复标注模板"), 3, 0)
        self.edit_repeat_label = QLineEdit(self.cfg["priority"].get("repeat_label","（重复推荐：首次推送 {date}）"))
        g2.addWidget(self.edit_repeat_label, 3, 1)
        lay.addWidget(pr_box)

        # conferences, journals_issn, rss
        list_box = QGroupBox("顶会 / 顶刊 ISSN / RSS（每行一个）")
        g3 = QGridLayout(list_box)
        self.txt_confs = QTextEdit("\n".join(self.cfg.get("conferences", [])))
        self.txt_jissn = QTextEdit("\n".join(self.cfg.get("journals_issn", [])))
        self.txt_rss   = QTextEdit("\n".join(self.cfg.get("rss_urls", [])))
        g3.addWidget(QLabel("Conferences"), 0, 0); g3.addWidget(self.txt_confs, 1, 0)
        g3.addWidget(QLabel("Journals ISSN"), 0, 1); g3.addWidget(self.txt_jissn, 1, 1)
        g3.addWidget(QLabel("RSS URLs"), 2, 0, 1, 2); g3.addWidget(self.txt_rss, 3, 0, 1, 2)
        lay.addWidget(list_box)

        btn = QPushButton("保存上述设置到 config.yaml")
        btn.clicked.connect(self._on_save_sources)
        lay.addWidget(btn)
        lay.addStretch()

        self.tabs.addTab(w, "来源与优先级")

    # --- Tab 3：参数 ---
    def _build_tab_params(self):
        w = QWidget(); lay = QVBoxLayout(w)
        grid = QGridLayout()
        row = 0

        def add_spin(label, key, mn, mx, default):
            nonlocal row
            spin = QSpinBox(); spin.setRange(mn, mx); spin.setValue(self.cfg.get(key, default))
            grid.addWidget(QLabel(label), row, 0); grid.addWidget(spin, row, 1); row += 1
            return spin

        self.spin_since = add_spin("since_days", "since_days", 1, 60, 5)
        self.spin_fallback = add_spin("fallback_days", "fallback_days", 1, 90, 21)
        self.spin_min_daily = add_spin("min_daily", "min_daily", 1, 20, 5)
        self.spin_target = add_spin("target_total", "target_total", 1, 20, 5)
        self.spin_percat = add_spin("per_category_max", "per_category_max", 1, 10, 3)
        self.spin_summary = add_spin("summary_sentences", "summary_sentences", 1, 6, 3)

        self.edit_output = QLineEdit(self.cfg.get("output_dir", "./digests"))
        self.edit_cache  = QLineEdit(self.cfg.get("cache_path", "./cache.json"))
        grid.addWidget(QLabel("output_dir"), row, 0); grid.addWidget(self.edit_output, row, 1); row += 1
        grid.addWidget(QLabel("cache_path"), row, 0); grid.addWidget(self.edit_cache, row, 1); row += 1

        lay.addLayout(grid)

        row2 = QHBoxLayout()
        btn_save = QPushButton("保存参数到 config.yaml"); row2.addWidget(btn_save); row2.addStretch()
        btn_out = QPushButton("选择输出目录…"); row2.addWidget(btn_out)
        lay.addLayout(row2)
        lay.addStretch()

        btn_save.clicked.connect(self._on_save_params)
        btn_out.clicked.connect(self._on_pick_output)

        self.tabs.addTab(w, "参数")

    # --- Tab 4：类别 YAML ---
    def _build_tab_categories(self):
        w = QWidget(); lay = QVBoxLayout(w)
        self.txt_yaml = QTextEdit()
        try:
            cats_text = yaml.safe_dump({"categories": self.cfg.get("categories", [])}, allow_unicode=True, sort_keys=False)
        except Exception:
            cats_text = DEFAULT_CATEGORIES_YAML
        self.txt_yaml.setText(cats_text)

        row = QHBoxLayout()
        btn_chk = QPushButton("校验 YAML 并保存")
        btn_reset = QPushButton("恢复为默认 YAML（带 6 大类）")
        row.addWidget(btn_chk); row.addWidget(btn_reset); row.addStretch()

        lay.addWidget(QLabel("直接编辑 categories（支持你给的高亮词与 arXiv_queries）；保存时会校验。"))
        lay.addWidget(self.txt_yaml)
        lay.addLayout(row)
        lay.addStretch()

        btn_chk.clicked.connect(self._on_save_categories)
        btn_reset.clicked.connect(lambda: self.txt_yaml.setText(DEFAULT_CATEGORIES_YAML))

        self.tabs.addTab(w, "类别（YAML）")

    def _build_tab_email(self):
        w = QWidget(); lay = QVBoxLayout(w)

        # 顶部开关与范围
        row0 = QHBoxLayout()
        self.cb_email_enabled = QCheckBox("启用邮件发送")
        self.cb_email_enabled.setChecked(bool((self.cfg.get("email") or {}).get("enabled", False)))
        self.cb_only_journal = QCheckBox("仅发送顶刊（OpenAlex 期刊）")
        self.cb_only_journal.setChecked(bool((self.cfg.get("email") or {}).get("only_journals", True)))
        self.cb_inc_conf = QCheckBox("在仅顶刊的基础上并入顶会")
        self.cb_inc_conf.setChecked(bool((self.cfg.get("email") or {}).get("include_conferences", False)))
        row0.addWidget(self.cb_email_enabled); row0.addWidget(self.cb_only_journal); row0.addWidget(self.cb_inc_conf); row0.addStretch()
        lay.addLayout(row0)

        # SMTP 与收件人
        g = QGridLayout()
        e = self.cfg.get("email") or {}
        smtp = e.get("smtp") or {}

        self.edit_to = QTextEdit("\n".join((e.get("to") or [])))
        self.edit_from = QLineEdit(e.get("from",""))
        self.edit_host = QLineEdit(smtp.get("host",""))
        self.spin_port = QSpinBox(); self.spin_port.setRange(1, 65535); self.spin_port.setValue(int(smtp.get("port",587)))
        self.cb_starttls = QCheckBox("STARTTLS"); self.cb_starttls.setChecked(bool(smtp.get("starttls", True)))
        self.cb_ssl = QCheckBox("SSL(465)"); self.cb_ssl.setChecked(bool(smtp.get("ssl", False)))
        self.edit_user = QLineEdit(smtp.get("username",""))
        self.edit_pass = QLineEdit(smtp.get("password","")); self.edit_pass.setEchoMode(QLineEdit.Password)

        g.addWidget(QLabel("收件人（每行一个）"), 0,0); g.addWidget(self.edit_to, 0,1)
        g.addWidget(QLabel("发件人 From"), 1,0); g.addWidget(self.edit_from, 1,1)
        g.addWidget(QLabel("SMTP Host"), 2,0); g.addWidget(self.edit_host, 2,1)
        g.addWidget(QLabel("SMTP Port"), 3,0); g.addWidget(self.spin_port, 3,1)
        g.addWidget(self.cb_starttls, 4,0); g.addWidget(self.cb_ssl, 4,1)
        g.addWidget(QLabel("SMTP 用户名"), 5,0); g.addWidget(self.edit_user, 5,1)
        g.addWidget(QLabel("SMTP 密码/应用专用密码"), 6,0); g.addWidget(self.edit_pass, 6,1)
        lay.addLayout(g)

        # 主题/模板/其它
        row1 = QGridLayout()
        self.edit_subject = QLineEdit((e.get("subject_tpl") or "PaperRadar · {date} · {count} 篇"))
        self.cb_attach = QCheckBox("附加今日 md 摘要为附件")
        self.cb_attach.setChecked(bool(e.get("attach_digest", False)))
        self.spin_min = QSpinBox(); self.spin_min.setRange(0,100); self.spin_min.setValue(int(e.get("min_count",1)))
        self.combo_format = QLineEdit((e.get("body_format") or "html"))

        row1.addWidget(QLabel("主题模板"), 0,0); row1.addWidget(self.edit_subject, 0,1)
        row1.addWidget(self.cb_attach, 1,0)
        row1.addWidget(QLabel("最少数量再发送"), 1,1); row1.addWidget(self.spin_min, 1,2)
        row1.addWidget(QLabel('正文格式（"html" 或 "text"）'), 2,0); row1.addWidget(self.combo_format, 2,1)
        lay.addLayout(row1)

        # 按钮
        row2 = QHBoxLayout()
        btn_save = QPushButton("保存邮件设置")
        btn_test = QPushButton("发送测试邮件")
        row2.addWidget(btn_save); row2.addWidget(btn_test); row2.addStretch()
        lay.addLayout(row2)
        lay.addStretch()
        self.tabs.addTab(w, "邮件/通知")

        btn_save.clicked.connect(self._on_save_email)
        btn_test.clicked.connect(self._on_send_test_email)

    def _on_save_email(self):
        e = self.cfg.get("email") or {}
        e["enabled"] = self.cb_email_enabled.isChecked()
        e["only_journals"] = self.cb_only_journal.isChecked()
        e["include_conferences"] = self.cb_inc_conf.isChecked()
        e["attach_digest"] = self.cb_attach.isChecked()
        e["min_count"] = int(self.spin_min.value())
        e["subject_tpl"] = self.edit_subject.text().strip() or "PaperRadar · {date} · {count} 篇"
        e["body_format"] = (self.combo_format.text().strip() or "html").lower()
        e["to"] = [ln.strip() for ln in self.edit_to.toPlainText().splitlines() if ln.strip()]
        e["from"] = self.edit_from.text().strip()
        smtp = e.get("smtp") or {}
        smtp["host"] = self.edit_host.text().strip()
        smtp["port"] = int(self.spin_port.value())
        smtp["starttls"] = self.cb_starttls.isChecked()
        smtp["ssl"] = self.cb_ssl.isChecked()
        smtp["username"] = self.edit_user.text().strip()
        smtp["password"] = self.edit_pass.text().strip()
        e["smtp"] = smtp
        self.cfg["email"] = e
        save_config(self.cfg)
        QMessageBox.information(self, "已保存", "邮件配置已写入 config.yaml。")

    def _on_send_test_email(self):
        # 直接用配置发一封“测试邮件”
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.utils import formataddr

        self._on_save_email()  # 先保存一遍
        e = self.cfg.get("email") or {}
        if not e.get("enabled"):
            QMessageBox.warning(self, "未启用", "请先勾选“启用邮件发送”。")
            return
        to_list = e.get("to") or []
        if not to_list:
            QMessageBox.warning(self, "缺少收件人", "请至少填写一个收件人。")
            return
        subject = f"[TEST] PaperRadar 邮件连通性 · {datetime.datetime.now():%Y-%m-%d %H:%M}"
        body = "这是一封测试邮件：验证 SMTP 配置是否正确。收到后代表配置有效。"

        mime = MIMEMultipart()
        mime['From'] = formataddr(("PaperRadar Bot", e.get("from") or e.get("smtp",{}).get("username","")))
        mime['To'] = ", ".join(to_list)
        mime['Subject'] = subject
        mime.attach(MIMEText(body, "plain", "utf-8"))

        smtp = e.get("smtp") or {}
        host = smtp.get("host"); port = int(smtp.get("port",587))
        use_ssl = bool(smtp.get("ssl", False)); use_starttls = bool(smtp.get("starttls", True))
        user = smtp.get("username"); pwd = smtp.get("password")

        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port, timeout=30)
            else:
                server = smtplib.SMTP(host, port, timeout=30)
            server.ehlo()
            if (not use_ssl) and use_starttls:
                server.starttls(); server.ehlo()
            server.login(user, pwd)
            server.sendmail(e.get("from") or user, to_list, mime.as_string())
            server.quit()
            QMessageBox.information(self, "成功", "测试邮件已发送，请查收。")
        except Exception as ex:
            QMessageBox.critical(self, "失败", f"发送失败：\n{ex}")

    # ---------- 事件处理 ----------
    def _collect_common(self):
        # 将当前 cfg 与 UI 的源/优先级项同步
        self.cfg["sources"]["openalex_conferences"] = self.cb_conf.isChecked()
        self.cfg["sources"]["openalex_journals"] = self.cb_jour.isChecked()
        self.cfg["sources"]["openreview"] = self.cb_openr.isChecked()
        self.cfg["sources"]["arxiv"] = self.cb_arxiv.isChecked()
        self.cfg["sources"]["rss"] = self.cb_rss.isChecked()
        self.cfg["priority"]["prefer_top_venues"] = self.cb_prefer.isChecked()
        self.cfg["priority"]["allow_repeat_fill"] = self.cb_repeat.isChecked()
        self.cfg["priority"]["repeat_lookback_days"] = int(self.spin_repeat_days.value())
        self.cfg["priority"]["repeat_label"] = self.edit_repeat_label.text().strip()
        self.cfg["conferences"] = parse_lines_to_list(self.txt_confs.toPlainText())
        self.cfg["journals_issn"] = parse_lines_to_list(self.txt_jissn.toPlainText())
        self.cfg["rss_urls"] = parse_lines_to_list(self.txt_rss.toPlainText())

    def _on_save_sources(self):
        self._collect_common()
        save_config(self.cfg)
        self.statusBar().showMessage("来源与优先级已保存到 config.yaml", 5000)
        QMessageBox.information(self, "已保存", "来源与优先级配置已写入 config.yaml。")

    def _on_save_params(self):
        self.cfg["since_days"] = int(self.spin_since.value())
        self.cfg["fallback_days"] = int(self.spin_fallback.value())
        self.cfg["min_daily"] = int(self.spin_min_daily.value())
        self.cfg["target_total"] = int(self.spin_target.value())
        self.cfg["per_category_max"] = int(self.spin_percat.value())
        self.cfg["summary_sentences"] = int(self.spin_summary.value())
        self.cfg["output_dir"] = self.edit_output.text().strip()
        self.cfg["cache_path"] = self.edit_cache.text().strip()
        save_config(self.cfg)
        self.statusBar().showMessage("参数已保存到 config.yaml", 5000)
        QMessageBox.information(self, "已保存", "参数配置已写入 config.yaml。")

    def _on_save_categories(self):
        text = self.txt_yaml.toPlainText()
        try:
            obj = yaml.safe_load(text) or {}
            if not isinstance(obj, dict) or "categories" not in obj or not isinstance(obj["categories"], list):
                raise ValueError('YAML 必须是 {"categories":[...]} 结构')
            self.cfg["categories"] = obj["categories"]
            save_config(self.cfg)
            self.statusBar().showMessage("categories 已保存到 config.yaml", 5000)
            QMessageBox.information(self, "已保存", "categories YAML 已写入 config.yaml。")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"YAML 解析错误：\n{e}")

    def _on_pick_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", str(PROJECT_DIR))
        if d:
            self.edit_output.setText(d)

    def _on_install(self):
        push_time = self.time_edit.time().toString("HH:mm")
        interval = int(self.interval_spin.value())
        since_task = int(self.since_task_spin.value())
        ru = self.ru_edit.text().strip()
        rp = self.rp_edit.text().strip()
        code, out = install_task(push_time, interval, since_task, interactive=(not (ru and rp)), ru=ru or None, rp=rp or None)
        if code == 0:
            QMessageBox.information(self, "成功", f"已创建/更新计划任务：{TASK_NAME}\n时间 {push_time}，每 {interval} 天一次。")
        else:
            QMessageBox.critical(self, "失败", f"计划任务创建/更新失败：\n{out}")

    def _on_uninstall(self):
        code, out = uninstall_task()
        if code == 0:
            QMessageBox.information(self, "已删除", f"已删除计划任务：{TASK_NAME}")
        else:
            QMessageBox.critical(self, "失败", f"删除计划任务失败：\n{out}")

    def _on_runonce(self):
        since_task = int(self.since_task_spin.value())
        code, out = run_once(since_task)

        # 优先从 UTF-8 日志读尾部，避免子进程输出解码差异
        try:
            log = PROJECT_DIR / "logs" / f"run_{datetime.date.today():%Y-%m-%d}.log"
            if log.exists():
                tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-15:])
            else:
                tail = "\n".join(out.strip().splitlines()[-15:])
        except Exception:
            tail = "\n".join(out.strip().splitlines()[-15:])

        if code == 0:
            QMessageBox.information(self, "已触发", f"已触发一次运行。\n（日志尾部）\n{tail}")
        else:
            QMessageBox.critical(self, "失败", f"运行失败（返回码 {code}）：\n{tail}")

# ---------- 入口 ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
