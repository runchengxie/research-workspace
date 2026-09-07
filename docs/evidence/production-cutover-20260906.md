# 生产切换和回滚窗口

> 状态：回滚窗口进行中
> T0: 2026-09-06T19:30:33+08:00
> rollback window closes: 2026-09-20T19:30:33+08:00

## Production pointers

生产晋级使用远端 `main` 提交完成原子切换：

| Surface | Previous release | Active release |
| --- | --- | --- |
| `research-workspace` | `9267bbae5b03c092cc62b59d1d38f8e8158c5b55` | `b58831bcfaead16cdd3cafa08dd28139ba6e696f` |
| `market-intel` | `482cb31b5c1d8ac1681cebd28e96a31d808d12a0` | `89a35d97ca73f2533c74b487d16c785fab80d10e` |

旧版本仍然保留且可以访问。没有删除、归档、重命名或限制访问任何旧仓库。

## 切换后检查

- workspace doctor：0 个错误，6 个已有警告，均不阻断流程。
- contract smoke：0 个错误，0 个警告。
- `market-intel` 平台发布消费者测试：`5 passed`。
- 当前 `market-intel` 版本使用 `allow_internal=True` 重新验证了真实 DailyWatch20 发布包。
- Hermes 的早间、晚间和每周任务已重新指向当前 `market-intel` 版本。

## 回滚策略

窗口期间保留两个旧版本目录、所有旧仓库和生产发布包，不对它们做改动。如果消费者、新鲜度、发布、投递、输出漂移或恢复检查失败，就将受影响的 `current` 符号链接原子地重新指向对应旧版本，并恢复旧的 Hermes workdir。

两个计划中的生产周期完成、根据已记录的旧 manifest 成功完成回滚演练并批准明确的收尾记录后，窗口才能关闭。
