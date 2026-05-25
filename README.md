# Research Workspace

这个仓库是一个 Git superproject，用来锁定三个相关项目的一组可复现版本。它不是 monorepo：代码、依赖、测试和发布仍然由各自的子项目维护。

## 子项目

- `cross-sectional-trees`：截面研究、特征工程、模型评估和回测。
- `market-data-platform`：市场数据平台、数据接入和数据服务。
- `rqdata-hk-depth-snapshots`：RQData 港股深度快照资产和相关工具。

## 克隆

新机器或新目录建议直接递归克隆：

```bash
git clone --recurse-submodules git@github.com:runchengxie/research-workspace.git
```

如果已经克隆了顶层仓库，再初始化子模块：

```bash
git submodule update --init --recursive
```

## 日常工作流

子项目仍然在各自目录里正常开发、提交和推送：

```bash
cd cross-sectional-trees
git status
git add <files>
git commit -m "..."
git push
```

子项目提交推送后，回到顶层仓库提交新的 submodule 指针：

```bash
cd ..
git status
git add cross-sectional-trees
git commit -m "Bump cross-sectional-trees"
git push
```

## 更新子模块

拉取顶层仓库后，让本地子模块切到顶层记录的 commit：

```bash
git pull
git submodule update --init --recursive
```

如果要把某个子项目更新到它远端 `main` 的最新 commit：

```bash
cd cross-sectional-trees
git checkout main
git pull
cd ..
git add cross-sectional-trees
git commit -m "Bump cross-sectional-trees"
```

## 注意事项

- 顶层仓库只提交 `.gitmodules`、README、少量 workspace 配置，以及 submodule 指针。
- 不要在顶层仓库里递归提交子项目文件；子项目文件改动应在对应子 repo 内提交。
- 不要把大型数据、缓存、运行产物提交到顶层仓库。
- 默认保持 submodule 锁定到具体 commit，这样顶层仓库能准确记录一组可复现实验环境。
