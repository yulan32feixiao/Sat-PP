# SAT Self Test · v2.0

数字 SAT 定向刷题工具。3,311 道 College Board 官方真题，Bluebook 式答题界面，带官方逐选项解析、错因自动归类和间隔复习。

**纯静态，没有后端。打开就能用，不用注册。**

> 在线：<https://yulan32feixiao.github.io/Sat-PP/>
> 仓库：<https://github.com/yulan32feixiao/Sat-PP>

---

## 打开就能练

打开网页 → 选一个专项 → 选题数 → 开始。不需要登录、不需要配置、不需要先做测评。

所有记录（做过的题、错题、生词）存在**你这台浏览器的 localStorage** 里，不上传任何服务器。

⚠️ **清浏览器数据、换电脑、Safari 长期不打开（约 7 天）都会让记录消失。**
顶栏「💾 数据」可以导出备份成 JSON、也可以导入恢复。
导入按时间戳合并，两台设备各练各的也能并到一起，不会互相覆盖、重复导入不翻倍。
攒够 50 条作答又超过 7 天没导出，按钮上会出现红点提醒。

**默认状态**：全新打开时没有任何记录 —— 错题、生词、标记都是空的，统计全是 0，
「水平评估」页显示「还没有做题记录」而不是任何预设分数。
题目难度默认覆盖全部 7 个官方分数段（Easy / Medium / Hard 三档都勾着），
练一阵之后各专项的掌握度才会长出来。

## 私人版 / 离线版

所有依赖（Tailwind、FontAwesome、KaTeX、字体）都在仓库里本地化了，页面加载**零外网请求**。
两种私人用法：

- **本机私人版**：双击 `启动.command`（或 `./start.sh`）—— 数据全在这台电脑的浏览器里，
  断网照常刷题。唯一需要联网的是图形计算器 Desmos 标签（点开才加载，不用它就全程离线）。
- **公开网址**：https://yulan32feixiao.github.io/Sat-PP/ —— 同一套功能，记录跟浏览器走。

## 我的题库（第三个来源）

首页题库来源切换器有第三个选项 **「我的题库」**：92 道英语题（词汇 37 / 阅读 37 / 语法 17），
来自本人复盘截图的 OCR 转录（`sat训练题库` 文件夹 110 张复盘页），已与官方/2026 两库去重。
判分只按复盘页显示的标准答案字母。数学 35 题按要求未收（截图 OCR 对数学公式不可靠）。
来源限制照例摆在明处：转录文本可能有少量 OCR 痕迹，考点为自动推断。
重新生成：`python3 tools/ocr_mybank.py && python3 tools/build_mybank.py && python3 tools/build_mybank_data.py`

本地和网页的作答记录互相独立；换设备用顶栏「💾 数据」导出/导入合并。

## 五大专项

首页按 College Board 官方 8 大 Domain 归并成五类，点卡片展开二级考点（共 29 项细分技能）：

| 专项 | 题数 | 对应官方 Domain |
|---|---|---|
| 01 词汇单项 | 261 | Craft and Structure（Words in Context） |
| 02 阅读单项 | 765 | Information and Ideas / Craft and Structure |
| 03 语法单项 | 819 | Standard English Conventions / Expression of Ideas |
| 04 数学单项 | 1,466 | Algebra / Advanced Math / Problem-Solving / Geometry |
| 05 个人单项 | — | 错题集、标记题、AI 推荐 |

## 2026 真题模考（mock2026.bin）

「全真模考」页新增 **2026 真题区**：38 套（阅读语法 20 + 数学 18，共 1,739 题），
按场次月份**新者优先**，每套可整场连考（Module 1 → 中场休息屏 → Module 2），
模块限时按官方标准（RW 32 分/模块、Math 35 分/模块），残卷按题数等比缩短并在标签里说明。
R&W 模块按官方标准隐藏计算器与公式表；数学全程可用（本地计算器 + Desmos 官方考试版）。

**每套的不确定性直接摆在界面上**：完整性（缺题套不当完整模考）、来源（考后回忆·第三方重排，
非 CB 官方发布）、答案可信度（非官方答案键；26年10月第1套经 25 题人工验算全对，其余标未抽查）、
低清配图数量、难度/考点标签为自动推断。每套的「不确定性说明」有完整文字版。

**「2026真题回顾」页**独立统计：按场次完成度、正确率、按月正确率条、逐套/全部错题重做。
与官方题库的练习记录分开统计，互不掺和。

数据细节：
- 题干/选项/解析是从 PDF 文字层提取的**真文本**（可划词高亮、收生词），不是截图；
  只有原卷里本来就是图片的几何图/统计图/频率表存成 PNG（253 张，`fig2026/`）
- 16 道「四个选项各是一张频率表」的题做成了图片选项
- 数学上标按符号规则还原（源 PDF 的 Word 排版把 x² 压成了 x2）；分数线保持原卷线性写法
- 2026 题目只注册进 BYID（错题本/生词/AI/复盘可用），**不混入**官方题库的专项练习池
- 重新生成：`python3 tools/import_mock2026.py`（依赖 pymupdf；读取来源是本地
  `SAT dl/更新到26年10月SAT最新真题题库+答案` 的 26 年卷 PDF）

**2026 真题也能按分类练**：首页右上「题库来源」切换 官方题库 / 2026真题 ——
切到 2026 后五大专项卡片计数、二级考点、出题池、正确率进度条全部切到 2026 数据
（考点为导入时自动推断，界面明确标注"非官方标注"）。2026 的 R&W 专项练习同样
按官方规则隐藏计算器；2026 题没有 Easy 档（M1=Medium、M2=Hard），只勾 Easy 会提示。

## 做题时有什么

- **Bluebook 式双栏**：左原文右题目，顶部计时，Mark for Review，Back / Next / Review & Submit
- **本地计算器**（默认）：白名单安全求值，支持 `2(3+1)`、`√9`、`3π`、`2^10`、`50%`、`sin/ln/log`。
  **不联网也能用** —— 需要作图再切 Desmos 标签（College Board 官方考试版 iframe）。
  30 键面板（数字/括号/`^√π%`/`ln log sin cos tan`/`Ans`）；**历史记录**：↑↓ 翻最近 30 条算式、
  点历史条目直接调回、`Ans` 引用上次结果做多步计算
- **公式表**：官方 Reference Sheet
- **填空题输入**：自带数字小键盘（只给官方允许的 `0-9 . / -` 和 ⌫，光标处插入），
  打开题目自动聚焦输入框，**回车直接进下一题**
- **快捷键**：`A/B/C/D` 或 `1/2/3/4` 选选项 · `←/→` 翻题 · `Alt+F` 标记 · `Esc` 暂停
- **划词**：选中原文可高亮、可收进生词本，自动保留原题上下文
- **填空题按官方规则判分**：`1/4` = `2/8` = `0.25`，截断与位数规则对齐真考（`tools/test-spr.cjs` 42 条断言）

## 做完之后

- **错因自动归类**：读官方解析里写你所选那个错项的那一段，归到 11 类之一
  （文中无依据 / 句子边界·标点 / 读错具体信息 / 主谓一致 / 动词时态 / 逻辑连接词 /
  说反了 / 过度推广 / 代词指代 / 张冠李戴 / 答成细节）。
  数学另外抽「算成了 X 而非 Y」的错步。
  *覆盖率实测：英语 59%，数学只有 7%（官方对数学干扰项多数只写一句套话），归不了类的标「未归类」，不猜。*
- **错因自述**：答错后先写一句「我当时怎么想的」，再看解析。数学的错因基本只能靠它。
- **用时四象限**：按官方配速（阅读 71 秒/题、数学 95 秒/题）分出
  慢而对（不熟练）/ 快而错（没读懂题）/ 慢而错（概念断层）/ 快而对（已掌握）
- **间隔复习**：错题进第 1 盒，答对升盒（1 → 3 → 7 → 16 天），**答错退回第 1 盒**，第 4 盒毕业

## 题目来源

全部来自 College Board 公开发布的
[SAT Suite Educator Question Bank](https://satsuiteeducatorquestionbank.collegeboard.org/)（无需登录）：

```
POST https://qbank-api.collegeboard.org/msreportingquestionbank-prod/questionbank/digital/get-questions
POST https://qbank-api.collegeboard.org/msreportingquestionbank-prod/questionbank/digital/get-question
```

题干、选项、正确答案、官方逐选项解析（rationale）**一字未改**。
分数段（band 1–7）取自官方 Skills Insight for the SAT Suite。

## 文件结构

```
index.html              整个应用（单文件，约 100 KB）
bank.bin                题库：3,311 题的 JSON，gzip 后 3.9 MB
                        打开网页时下载一次，在浏览器里解压，之后全程本地运算

tools/
  fetch_bank.py         从官方接口抓原始题库
  normalize.py          清洗：解析 HTML、剔除无题干的纸质遗留题、重写废弃 MathML 标签
  build_bank.py         gzip -9 打包成 bank.bin
  test-spr.cjs          填空题官方判分（42 条）
  test-calc-v2.cjs      本地计算器引擎（24 条，含安全白名单）
  test-standards-compliance.cjs  判分 / 归类 / 数据结构合规（6 条）
  test-custom-model.py  自定义模型接入
  legacy-v1/            v1 的 16 个测试，当前全部失败（架构已换）。
                        没删是因为它们是旧引擎的行为规格书，移植时要对照。详见该目录 README

docs/
  实施报告-2026-10-04.txt   教学机制的分阶段计划与实测数据
```

## 重新生成题库

```bash
python3 tools/fetch_bank.py      # 抓原始数据
python3 tools/normalize.py       # 清洗成统一 schema
python3 tools/build_bank.py      # 压成 bank.bin
```

## 跑测试

```bash
npm install jsdom --no-save
for t in tools/*.cjs; do node "$t" || echo "FAIL $t"; done
```

当前 **3 个测试全绿**（`test-spr` / `test-calc-v2` / `test-standards-compliance`）。
`tools/legacy-v1/` 下那 16 个对 v2.0 一定失败，这是预期的，别拿它们当回归信号。

## 已知缺口

按 `docs/实施报告-2026-10-04.txt` 的分阶段计划，还没做的：

- **复发识别**：错因标签打了，但没有跨时间累计，不会告诉你「这是你第 7 次犯同一个错」
- **难度自适应**：难度靠自己选，不会自动卡在 70–80% 正确率那个该待的区间
- **掌握判定**：练完只报正确率，「学会没有」没有可计算的定义
- **今日队列**：打开首页还是得自己想今天练什么
- **云同步**：没有。换设备靠顶栏「数据」手动导出/导入（已可用），但不会自动同步

## 版本

| 版本 | 架构 |
|---|---|
| v2.0（当前） | Bluebook 式界面，五大专项，约 2,070 行 |
| v1 | 单文件 6,365 行，见 git 历史 `dbdd9c1`。多档案、镜像站命名空间等机制已在 v2.0 取消 |
