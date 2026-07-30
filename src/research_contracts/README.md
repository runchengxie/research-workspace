# research-contracts

`research-contracts` 是 `research-workspace` 与下游产品仓库共享的轻量契约包。它只包含
artifact envelope、schema、SHA-256、lineage 和文件清单校验，不包含研究算法、数据访问或运行时
凭证。

从 Git 仓库子目录安装时应锁定不可变提交：

```text
research-contracts @ git+https://github.com/runchengxie/research-workspace.git@<commit>#subdirectory=src/research_contracts
```
