```markdown
# PaperRadar — 3D 点云方向的「论文雷达」

> 🎯 每天自动抓取并推送与你的研究方向高度相关的 **顶会/顶刊** 与 **arXiv 预印本**，支持优先级策略、重复补齐、邮件推送与本地通知，并提供 **PyQt 图形化配置界面** 与 **Windows 计划任务**一键安装。

---

## ✨ 功能特性

- **多来源聚合**  
  - 顶会/顶刊：基于 **OpenAlex**（会议按名称解析 Source，期刊按 **ISSN**）  
  - 预印本：**arXiv**（空页容错）  
  - 评审期：**OpenReview**（ICLR/NeurIPS/ICML 等）  
  - 可选：**RSS**（如 Papers with Code 任务页）
- **研究领域定制**  
  - 预置 3D 点云/工业计量方向的 6 大类别；每类可自定义关键词高亮与 `arxiv_queries`
- **优先级与补齐**  
  - 「顶会/顶刊优先 → arXiv 补齐 → 历史重复补齐（标注首次推送日期）」  
  - 目标每日 3–5 篇（可配），每类上限可配
- **输出与通知**  
  - 每日生成 **Markdown 摘要**（`digests/YYYY-MM-DD.md`）  
  - **邮件发送**（支持 SSL/STARTTLS，主题模板与最小数量阈值）  
  - **Windows 本地通知**、自动打开摘要（可选）
- **图形界面（PyQt5）**  
  - 所有配置可视化输入：来源与优先级、类别 YAML、邮件/通知、计划任务一键安装/删除/立即运行
- **稳定性**  
  - UTF-8 日志、不破 BOM 的追加写入、arXiv 空页容错、网络/认证问题的清晰报错

---

## 📁 目录结构

```

PaperRadar/
├─ paper_radar_plus.py          # 主抓取与生成逻辑（优先级版）
├─ PaperRadar_UI/
│  └─ paper_radar_ui_qt.py      # PyQt 配置面板（首次运行自动生成 run_daily.ps1）
├─ run_daily.ps1                # 每日运行（UTF-8 日志、追加写入、本地时区）
├─ install_task.ps1             # （可选）命令行安装计划任务
├─ config.yaml                  # 主配置（首次可由 UI 生成）
├─ digests/                     # 每日 Markdown 摘要输出
├─ logs/                        # 每日日志（UTF-8；同日多次运行会追加）
└─ requirements.txt             # 依赖列表

````

> **说明**：第一次从 UI 启动会自动写入一个 ASCII/UTF-8 安全的 `run_daily.ps1`，避免 PowerShell 中文解析问题。

---

## 🧰 环境要求

- Python 3.9+（建议 3.11）
- Windows 10/11（计划任务与弹窗通知）；Linux/macOS 仅命令行 & 定时任务（cron）
- 依赖（`requirements.txt`，示例）：
  ```text
  PyYAML==6.0.2
  requests==2.31.0
  arxiv==2.1.0
  feedparser==6.0.10   # 仅启用 RSS 时需要
  PyQt5==5.15.11       # 仅使用 UI 时需要
````

> 注意：`arxiv==2.1.0` 依赖 `feedparser==6.0.10`，请避免装成 6.0.11 导致冲突。

---

## 🚀 快速开始（Windows）

1. **克隆与虚拟环境**

   ```powershell
   git clone https://github.com/<yourname>/PaperRadar.git
   cd PaperRadar
   py -m venv .venv
   .\.venv\Scripts\activate
   python -m pip install -U pip
   pip install -r requirements.txt
   ```

2. **第一次运行（命令行）**

   ```powershell
   python .\paper_radar_plus.py --since_days 5
   ```

   * 输出 `digests/YYYY-MM-DD.md`
   * 初始配置来自 `config.yaml`（可用 UI 生成与编辑）

3. **图形界面（推荐）**

   ```powershell
   python .\PaperRadar_UI\paper_radar_ui_qt.py
   ```

   * **计划与推送**：创建/删除计划任务、立即运行一次、打开日志与摘要目录
   * **来源与优先级**：勾选 arXiv/OpenAlex/OpenReview/RSS，设置顶会/顶刊列表、优先级与重复补齐
   * **参数**：目标篇数、每类上限、回溯天数、摘要句数、输出与缓存路径
   * **类别（YAML）**：编辑 6 大类（关键词高亮 + arXiv 查询）
   * **邮件/通知**：SMTP、收/发件人、SSL/STARTTLS、最小数量阈值、是否附今日 md、主题模板

4. **计划任务（Windows）**

   * 在 UI 里选择时间（例如 08:00），点击 **「创建/更新计划任务」**
   * 或命令行安装（可选）：

     ```powershell
     powershell -ExecutionPolicy Bypass -File .\install_task.ps1
     ```
   * 立即测试：

     ```powershell
     schtasks /Run /TN PaperRadar_Daily_0800
     ```
   * 查看日志：`logs/run_YYYY-MM-DD.log`（UTF-8，**同日多次运行自动追加**）

---

## ⚙️ 配置说明（`config.yaml`）

### 1）来源与优先级

```yaml
sources:
  arxiv: true
  openalex_conferences: true
  openalex_journals: true
  openreview: true
  rss: false

priority:
  prefer_top_venues: true         # 顶会/顶刊优先
  allow_repeat_fill: true         # 不足时用历史重复补齐
  repeat_lookback_days: 7
  repeat_label: "（重复推荐：首次推送 {date}）"
```

* **conferences**：顶会名称（用于 OpenAlex Source 解析）
* **journals_issn**：期刊 ISSN（用于 OpenAlex Source 精确解析）

```yaml
conferences:
  - CVPR
  - ICCV
  - ECCV
  - NeurIPS
  - ICLR
  - ICML
  - 3DV
  - ICRA
  - IROS
  - RSS
  - SIGGRAPH
  - SIGGRAPH Asia

journals_issn: ["0162-8828","0920-5691","1077-2626","0730-0301","1057-7149","1520-9210","0924-2716","0921-8890"]
rss_urls: []
```

### 2）运行参数

```yaml
output_dir: "./digests"
cache_path: "./cache.json"
since_days: 5
target_total: 5
per_category_max: 3
summary_sentences: 3
min_daily: 5
fallback_days: 21
```

* 逻辑：顶会/顶刊（新作）→ arXiv（新作）→ 顶会/顶刊回溯（新但较旧）→ arXiv 回溯 → **历史重复补齐**（标注首次推送日期），直到 `target_total`。

### 3）类别（可在 UI 的「类别（YAML）」页编辑）

```yaml
categories:
  - name: "宏量点云去噪与精简"
    highlight: ["denoise","denoising","outlier","robust","MLS","bilateral","graph","sparse","downsample","decimation","simplification","voxel","FPS","curvature","diffusion","score-based","normal estimation"]
    arxiv_queries:
      - '((ti:"point cloud" OR abs:"point cloud" OR abs:LiDAR) AND (abs:denoise OR abs:denoising ... ) AND (cat:cs.CV OR cat:cs.GR OR cat:cs.RO OR cat:eess.IV))'
  # ... 其余 5 类略，同理配置
```

> 评分时会用到 `highlight` 关键词与类别权重，决定论文归属与排序。

### 4）邮件/通知（可在 UI 的「邮件/通知」页编辑）

```yaml
email:
  enabled: true
  only_journals: false            # 仅顶刊；若 true 可配合 include_conferences
  include_conferences: true       # 在仅顶刊基础上并入顶会
  attach_digest: true             # 附当日 md 摘要
  min_count: 1                    # 少于该数量则不发（并在日志中提示跳过原因）
  subject_tpl: "PaperRadar · {date} · {count} 篇"
  body_format: "html"             # 或 "text"
  to: ["your@domain.com"]
  from: "sender@domain.com"
  smtp:
    host: "smtp.qq.com"           # QQ: smtp.qq.com / 465(SSL) 或 587(STARTTLS)
    port: 465
    ssl: true
    starttls: false
    username: "sender@domain.com"
    password: "邮箱应用专用密码"
```

> 常见 SMTP：
>
> * **QQ 邮箱**：`smtp.qq.com`，**465 + SSL**（推荐）或 587 + STARTTLS，需启用「**POP3/SMTP**」并使用**授权码**
> * **Gmail**：`smtp.gmail.com`，587 + STARTTLS（需开启安全设置或使用 App Password）
> * **Outlook/Office365**：`smtp.office365.com`，587 + STARTTLS

---

## 🖥️ 命令行用法

```bash
python paper_radar_plus.py --since_days 5
# 其它参数通过 config.yaml 配置；或直接编辑后再运行
```

---

## 🧪 日志与字符集

* 日志文件：`logs/run_YYYY-MM-DD.log`（**UTF-8 编码**，**同日多次运行会追加**）
* 抬头时间：本地时区（如 `+08:00`），示例：

  ```
  [2025-10-24 08:00:02+08:00] RUN: PaperRadar --run --since_days 5
  ```
* 若在命令行手动运行，终端显示与日志内容一致；VS Code/记事本会正确识别 UTF-8

---

## ⚠️ 常见问题（FAQ）

1. **arXiv 报 `UnexpectedEmptyPageError`**

   * 已内建容错与较小分页（page_size=50）。通常是 arXiv API 分页返回空页，自动跳过。
2. **`feedparser` 版本冲突**

   * 使用 `arxiv==2.1.0` 时请安装 `feedparser==6.0.10`；不要装到 6.0.11。
3. **邮件报 `[SSL: WRONG_VERSION_NUMBER]`**

   * 端口/SSL 组合不匹配。QQ/大多数建议 **465+SSL** 或 **587+STARTTLS**（二选一，不能同开）。
4. **认证失败 `535 5.7.3 Authentication unsuccessful`**

   * 需使用邮箱的**应用专用密码**，并确认发件人与用户名一致。
5. **删除计划任务时中文乱码**

   * UI 已针对 `schtasks` 输出使用本地编码（mbcs）；若命令行使用请切换控制台到 UTF-8 或直接在 UI 中删除。
6. **时间显示差 8 小时/结尾有 `Z`**

   * 旧版 `run_daily.ps1` 使用 UTC。当前脚本已改为本地时区（`+08:00`），请覆盖旧脚本。

---

## 🧭 工作原理（简述）

1. **OpenAlex**

   * 会议：按名称检索 Source ID → `type=proceedings-article`
   * 期刊：按 ISSN 精确匹配 Source ID → `type=journal-article`
   * 取近 N 日文章，重构摘要（`abstract_inverted_index`）
2. **OpenReview**

   * 查询目标会议的 `notes`，取 `title/abstract/pdf` 等
3. **arXiv**

   * 按每类 `arxiv_queries` 搜索（排序：提交时间），窗口内的抽取
4. **统一评分/分配**

   * 关键词高亮 + 类别权重 + 类目（cs.CV/cs.RO/...）+ 新鲜度 → 选 3–5 篇
5. **重复补齐**

   * 若当天新论文不足，则在近 `repeat_lookback_days` 内从历史已推送中过筛并标注首次推送日期
6. **输出**

   * Markdown 摘要（多类分栏、AI 简报为抽取式摘要），可选**邮件发送**与**本地通知**

---

## 🔐 安全与隐私

* `config.yaml` 中的 SMTP 密码为明文存储；**建议使用应用专用密码**而不是邮箱主密码。
* 日志与摘要仅存本机；邮件发送内容为当日日报与（可选）md 附件。

---

## 🤝 参与贡献

欢迎提交 PR 与 Issue，特别是：

* 新的类别模板与关键词集合
* 其它会议/期刊源的稳定抓取方式
* Linux/macOS 的定时启动脚本样例（systemd/launchd）

---

## 📝 许可与致谢

* 许可证：MIT
* 数据源与生态：**arXiv**, **OpenAlex**, **OpenReview**, **Papers with Code** 等
* 感谢所有开源数据平台！

---
