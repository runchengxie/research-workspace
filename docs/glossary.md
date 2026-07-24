# 术语表

本表说明文档里出现的英文缩写与中英混用术语，方便第一次接触工作区的人。代码标识符、专有名词（数据商、框架、股票代码）保持英文，不翻译。

## 缩写（每个文档首次出现时写中文全称）

| 缩写 | 中文全称 |
|------|----------|
| ADR | 架构决策记录 |
| CLI | 命令行 |
| CI/CD | 持续集成与持续部署 |
| PR | 拉取请求 |
| ETL | 数据抽取、转换与加载 |
| API | 应用程序接口 |
| TA | 技术分析 |
| LLM | 大语言模型 |
| ML | 机器学习 |
| OOS | 样本外 |
| PIT | 时间点（point-in-time） |
| CPCV | 组合对称交叉验证 |
| MDP | 市场数据平台 |
| OMS | 订单管理系统 |
| PBO | 回测过拟合概率 |
| OLS | 普通最小二乘 |
| IC | 信息系数 |
| PB | 市净率 |
| DAG | 有向无环图 |
| ROI | 投资回报 |
| SDK | 软件开发工具包 |
| CST | 中国标准时间 |
| ET | 美国东部时间 |
| UTC | 协调世界时 |

## 中英混用术语（统一用中文，英文只保留在代码标识符里）

| 英文 | 中文 |
|------|------|
| fallback | 兜底 |
| snapshot | 快照 |
| contract | 契约 |
| manifest | 清单 |
| token | 令牌 |
| hook | 钩子 |
| namespace | 命名空间 |
| submodule | 子模块 |
| pipeline | 流水线 |
| dashboard | 看板 |
| idempotency / idempotent | 幂等 |
| degraded | 降级 |
| handoff | 交接 |
| deploy / deployment | 部署 |
| preview | 预览 |
| delivery | 投递 |
| repo | 仓库 |
| cron | 定时任务 |

## 保留英文（专有名词，不翻译）

- 框架：Qlib、vn.py、LEAN、AFML
- 数据商与平台：TuShare、market-data-platform、GitHub、GitHub Actions、Feishu/lark、Hermes、systemd
- 金融代码：VIX、SPY、QQQ、SMH、GLD、SLV、BTC、XAU、A股、港股
- 数据格式：JSON、CSV、YAML

## 专有名称与内部代号

文档和代码里反复出现、但字面不好懂的名字都列在这里。它们大多对应真实的代码目录、飞书群或机器人，所以这里只解释、不改名。

| 名称 | 是什么 | 说明 |
|------|--------|------|
| hotsector | 热点板块研究（research-apps 下的研究包），也指 hot-sector-screener 子模块 | 英文是中文（热点板块）的拼接缩写 |
| Hermes | 消息投递层（基于 Feishu/lark 的推送框架），负责把报告发到飞书 | 专有名词，保留英文 |
| DailyWatch、DailyWatch20 | 本工作区通过 strategy-pipeline 产出并发布给 market-intel 的 20 只 A 股每日观察名单 | DailyWatch 意为每日观察，20 表示 20 只 |
| watchlist20 | 20 股观察名单的产出物与命令（strategy watchlist20 run），与 DailyWatch20 同义 | 策略层的叫法 |
| A4、B16 | DailyWatch20 的内部两袖结构：A 袖 4 只、B 袖 16 只，合计 20 只 | 选型与权重约束的内部叫法 |
| F-lite | 轻量因子研究应用（daily_watch20_flite_factors），用于 DailyWatch20 的因子构造 | F 指因子（factor），lite 表示轻量版 |
| slow-volume | 低成交量研究（slow-volume campaign），用低成交量因子筛选股票 | 也写作低换手 |
| 五臂（五臂稳定性实验） | 研究方法术语：在同一批冻结数据上跑 5 个实验臂，用拉丁方设计减少顺序偏差，检验模型输出是否稳定 | 不是产品名，是实验设计 |
| AI精选 | AI 选股器产出的 AI 精选股票列表 | 中文名，含义直白 |
| DeepSeek V4 | 深度求索的 V4 模型 | 模型名，专有名词，保留英文 |
| Numeric（Numeric 排名） | 一种用数值打分排序的方法 | 与五臂是两个不同概念 |

补充：项目里没有 Numeric Shadow 这个名称。容易混淆的两个真实术语是 Numeric 排名（一种排序方法）和五臂稳定性实验（一种实验设计），两者不是一回事。
