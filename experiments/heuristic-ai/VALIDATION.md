# 验证记录

日期：2026-10-30（Asia/Shanghai）。基线：`main` 的 `b18e7c3b83b9b9b1536b295ff4b33006d5f28b29`。

环境：Python 3.14.2、Node.js v25.9.0、pnpm 10.22.0、锁定依赖中的 Astro 5.17.1；实验没有第三方 Python 依赖。

## 实验与内容

- `python3 experiments/heuristic-ai/experiment.py`：通过。1,265 行联合概率结果，80 个评测状态；包含终止边界的 110 状态动态规划/合法序列枚举一致。
- `python3 experiments/heuristic-ai/figures.py`：生成四张 SVG、概率表、策略汇总表。
- 两条命令再次运行后，JSON、SVG、汇总表和正文的 SHA-256 均保持一致。
- 另行核对即时策略的 7 个首步失败状态：未蓄力，(HP,步数)=(5..10,2) 和 (10,4)。九血四步是首步并列最优、整局仍可能损失的例子。
- `node --check public/demos/heuristic-ai/demo.js`：通过。
- 正文经独立数学复核与文字审阅，区分截图里的经验判断和自制实验；明确单步 regret 与整局损失、并列最优、统计范围。

## 博客

- `pnpm install --frozen-lockfile`：通过，未修改锁文件。
- `ENABLE_CONTENT_SYNC=false pnpm build`：通过，包含 Astro、Pagefind、字体压缩。禁用同步防止远端内容覆盖本地文章。
- `ENABLE_CONTENT_SYNC=false pnpm check`：失败，2 个错误。添加文章前的基线检查与最终检查一致：
  - `src/config.ts:32`：`zh-CN` 不属于语言标识类型（类型要求 `zh_CN`）。
  - `src/pages/arknights-calc.astro:3`：导入名 `ArknightsCalc` 与本地声明冲突。
- 上述两个文件与基线完全相同；没有为本文修改全站配置或其他页面。

## 实际浏览器检查

使用生产构建的 `pnpm preview --host 127.0.0.1 --port 4321`，在桌面 1440×1000、手机 390×844 检查文章和 Demo，各覆盖深/浅外观。

- 文章六张图片全部加载；四张原创图还逐张查看了实际渲染。发现并修正 SVG 曲线误填充的问题。
- 手机公式已拆行；稳定布局下无整页横向溢出，宽表格由现有主题局部滚动；KaTeX 无错误节点。
- 两张用户提供的聊天截图原样收录，有文字转述与来源说明。
- Demo 实测独立一血 0.84、同源一血 0.6、同源两血 1.2；互斥切换自动限制为 50%，真实收益为 1；0%/100%、零血终止均通过。
- 蓄力页实测最后一步 2/0、三步最优续走 7/7，以及固定策略整局 5、末步修正策略整局 7。概率控制不改变确定性模型。
- Demo 控制台未见 warning/error。博客首页的主题运行脚本曾出现 `Cannot use 'in' operator to search for 'animation' in undefined`，未修改或深入排查主题动画；页面内容、主题切换与搜索可用。
- 首页文章列表包含新文章；搜索“评分函数”返回本文。
- 桌面/手机深浅色截图保存在本地任务交接目录，未把验证截图和日志加入公开文章素材。

结论只限公开的教学模型，未测真实游戏胜率或引擎性能。
