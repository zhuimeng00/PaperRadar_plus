
---

# PaperRadar_plus — 研究方向的「论文雷达」

> 🎯 每天自动抓取并推送与你研究方向高度相关的 **顶会/顶刊** 与 **arXiv 预印本**。支持优先级策略、重复补齐、邮件推送与本地通知，并提供 **PyQt 图形化配置界面** + **Windows 计划任务**一键安装。

---

## 目录（Table of Contents）

- [PaperRadar\_plus — 研究方向的「论文雷达」](#paperradar_plus--研究方向的论文雷达)
  - [目录（Table of Contents）](#目录table-of-contents)
  - [✨ 功能特性](#-功能特性)
  - [📁 目录结构](#-目录结构)
  - [🧰 环境要求](#-环境要求)
  - [🚀 快速开始（Windows）](#-快速开始windows)
  - [⚙️ 配置说明（`config.yaml`）](#️-配置说明configyaml)
    - [来源与优先级](#来源与优先级)
    - [运行参数](#运行参数)
    - [类别（YAML）](#类别yaml)
    - [邮件与通知](#邮件与通知)
  - [🖥️ 命令行用法](#️-命令行用法)
  - [🧪 日志与字符集](#-日志与字符集)
  - [⚠️ 常见问题（FAQ）](#️-常见问题faq)
  - [🧭 工作原理（简述）](#-工作原理简述)
  - [🔐 安全与隐私](#-安全与隐私)
  - [🤝 参与贡献](#-参与贡献)
  - [📝 许可与致谢](#-许可与致谢)

---

## ✨ 功能特性

* **多来源聚合**

  * 顶会/顶刊：基于 **OpenAlex**（会议按名称解析 Source，期刊按 **ISSN**）
  * 预印本：**arXiv**（带空页容错）
  * 评审期：**OpenReview**（ICLR / NeurIPS / ICML 等）
  * 可选：**RSS**（如 Papers with Code 任务页）
* **研究领域定制**

  * 预置 3D 点云/工业计量方向的 6 大类别；每类可自定义关键词高亮与 `arxiv_queries`
* **优先级与补齐**

  * 先抓 **顶会/顶刊** → 不足由 **arXiv** 补齐 → 再不足使用**历史重复补齐**（会标注首次推送日期）
  * 目标每日 3–5 篇（可配），每类上限可配
* **输出与通知**

  * 每日生成 **Markdown 摘要**：`digests/YYYY-MM-DD.md`
  * **邮件发送**（SSL/STARTTLS，主题模板、最小数量阈值）
  * **Windows 本地通知**、可自动打开当日摘要（可选）
* **图形界面（PyQt5）**

  * 可视化修改所有配置：来源与优先级、类别 YAML、邮件/通知、计划任务一键安装/删除/立即运行
* **稳定性**

  * UTF-8 日志、同日多次运行**追加写入**、arXiv 空页容错、清晰的网络/认证报错

---

## 📁 目录结构

```bash
PaperRadar/
├─ paper_radar_plus.py          # 主抓取与生成逻辑（优先级版）
├─ PaperRadar_UI/
│  └─ paper_radar_ui_qt.py      # PyQt 配置面板（首次运行自动生成 run_daily.ps1）
├─ run_daily.ps1                # 每日运行（UTF-8 日志、追加写入、本地时区）
├─ install_task.ps1             # （可选）命令行安装计划任务
├─ config.yaml                  # 主配置（可由 UI 生成/编辑）
├─ digests/                     # 每日 Markdown 摘要输出
├─ logs/                        # 每日日志（UTF-8；同日多次运行会追加）
└─ requirements.txt             # 依赖列表
```

> **说明**：首次从 UI 启动会自动写入一个 **ASCII/UTF-8 安全** 的 `run_daily.ps1`，避免 PowerShell 中文解析问题。

---

## 🧰 环境要求

* Python 3.9+（建议 3.11）
* Windows 10/11（计划任务与弹窗通知）；Linux/macOS 仅支持命令行与定时任务（cron）
* 依赖（`requirements.txt`）：

```text
PyYAML==6.0.2
requests==2.31.0
arxiv==2.1.0
feedparser==6.0.10   # 仅启用 RSS 时需要
PyQt5==5.15.11       # 仅使用 UI 时需要
```

> **注意**：`arxiv==2.1.0` 依赖 `feedparser==6.0.10`，请避免安装 6.0.11 以防冲突。

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

* 会在 `digests/YYYY-MM-DD.md` 生成当日摘要
* 初次配置来自 `config.yaml`（可用 UI 生成与编辑）

3. **图形界面（推荐）**

```powershell
python .\PaperRadar_UI\paper_radar_ui_qt.py
```

* **计划与推送**：创建/删除计划任务、立即运行一次、打开日志与摘要目录
* **来源与优先级**：勾选 arXiv / OpenAlex / OpenReview / RSS，设置顶会/顶刊列表、优先级和重复补齐
* **参数**：目标篇数、每类上限、回溯天数、摘要句数、输出/缓存路径
* **类别（YAML）**：编辑 6 大类（关键词高亮 + arXiv 查询）
* **邮件/通知**：SMTP、收/发件人、SSL/STARTTLS、最小数量阈值、是否附今日 md、主题模板

4. **计划任务（Windows）**

* 在 UI 中选择时间（如 08:00），点击 **创建/更新计划任务**
* 或命令行安装（可选）：

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install_task.ps1
  ```
* 立即测试：

  ```powershell
  schtasks /Run /TN PaperRadar_Daily_0800
  ```
* 查看日志：`logs/run_YYYY-MM-DD.log`（**UTF-8**，**同日多次运行自动追加**）

---

## ⚙️ 配置说明（`config.yaml`）

### 来源与优先级

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

**顶会/顶刊与 RSS 列表示例：**

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

### 运行参数

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

> 选择顺序：**顶会/顶刊（新作）** → **arXiv（新作）** → 顶会/顶刊回溯（新但较旧） → arXiv 回溯 → **历史重复补齐**（标注首次推送日期），直到 `target_total`。

### 类别（YAML）

```yaml
categories:
  - name: "宏量点云去噪与精简"
    highlight: ["denoise","denoising","outlier","robust","MLS","bilateral","graph","sparse","downsample","decimation","simplification","voxel","FPS","curvature","diffusion","score-based","normal estimation"]
    arxiv_queries:
      - '((ti:"point cloud" OR abs:"point cloud" OR abs:LiDAR) AND (abs:denoise OR abs:denoising ... ) AND (cat:cs.CV OR cat:cs.GR OR cat:cs.RO OR cat:eess.IV))'
  # 其余 5 类同理配置
```

> 评分/归类会综合 `highlight` 关键词、arXiv 类目（如 cs.CV/cs.RO）与新鲜度，决定排序与分类。

### 邮件与通知

```yaml
email:
  enabled: true
  only_journals: false            # 仅顶刊；若为 true，可配合 include_conferences
  include_conferences: true       # 在仅顶刊基础上并入顶会
  attach_digest: true             # 附当日 md 摘要
  min_count: 1                    # 少于该数量不发（日志会提示跳过原因）
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
> * **QQ 邮箱**：`smtp.qq.com`，**465 + SSL**（推荐）或 587 + STARTTLS；需启用「POP3/SMTP」并使用**授权码**
> * **Gmail**：`smtp.gmail.com`，587 + STARTTLS（需开 App Password）
> * **Outlook/Office365**：`smtp.office365.com`，587 + STARTTLS

---

## 🖥️ 命令行用法

```bash
python paper_radar_plus.py --since_days 5
# 其它参数通过 config.yaml 配置；修改后再次运行即可
```

---

## 🧪 日志与字符集

* 日志文件：`logs/run_YYYY-MM-DD.log`（**UTF-8 编码**，**同日多次运行自动追加**）
* 抬头时间：**本地时区**（例如 `+08:00`）

  ```
  [2025-10-24 08:00:02+08:00] RUN: PaperRadar --run --since_days 5
  ```
* 在命令行/VS Code/记事本中均应正确显示中文；如果出现乱码，请确认文件编码为 UTF-8。

---

## ⚠️ 常见问题（FAQ）

1. **arXiv 报 `UnexpectedEmptyPageError`**
   已内建容错与较小分页（page_size=50），通常为 arXiv 返回空页，脚本会自动跳过。

2. **`feedparser` 版本冲突**
   `arxiv==2.1.0` 需要 `feedparser==6.0.10`；不要装到 6.0.11。

3. **邮件报 `[SSL: WRONG_VERSION_NUMBER]`**
   端口/SSL 组合不匹配。QQ/大多数建议 **465+SSL** 或 **587+STARTTLS**（二选一，不能同开）。

4. **认证失败 `535 5.7.3 Authentication unsuccessful`**
   需使用邮箱**应用专用密码**，并确认发件人与用户名一致。

5. **删除计划任务时中文乱码**
   UI 已针对 `schtasks` 使用本地编码；若在命令行操作，建议切换控制台到 UTF-8 或直接在 UI 中删除。

6. **时间显示差 8 小时/结尾有 `Z`**
   旧版 `run_daily.ps1` 使用 UTC。当前脚本已改为**本地时区**，请覆盖旧脚本。

---

## 🧭 工作原理（简述）

1. **OpenAlex**：会议按名称解析 Source ID → `type=proceedings-article`；期刊按 ISSN 精确匹配 Source ID → `type=journal-article`；近 N 日文章，重构摘要（`abstract_inverted_index`）。
2. **OpenReview**：查询目标会议的 `notes`，取 `title/abstract/pdf` 等。
3. **arXiv**：按每类 `arxiv_queries` 搜索（按提交时间排序），抽取窗口内的新作。
4. **统一评分/分配**：关键词高亮 + 类别权重 + 学科类目 + 新鲜度 → 选出 3–5 篇，并按类别归档。
5. **重复补齐**：若当天新论文不足，则从近 `repeat_lookback_days` 的历史已推送中过筛并标注首次推送日期。
6. **输出**：生成 Markdown 摘要（多类分栏；AI 简报为抽取式摘要），可选邮件发送与本地通知。

---

## 🔐 安全与隐私

* `config.yaml` 中的 SMTP 密码为明文存储；**强烈建议**使用邮箱**应用专用密码**。
* 日志与摘要仅存本机；邮件仅发送当日摘要与（可选）md 附件。

---

## 🤝 参与贡献

欢迎提交 PR / Issue，尤其是：

* 新的类别模板与关键词集合
* 其它会议/期刊源的稳定抓取方式
* Linux/macOS 的定时启动样例（systemd / launchd）

---

## 📝 许可与致谢

* 许可证：MIT
* 数据源与生态：**arXiv**, **OpenAlex**, **OpenReview**, **Papers with Code** 等
* 感谢所有开源数据平台与贡献者！

---
