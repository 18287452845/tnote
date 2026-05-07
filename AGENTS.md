## 项目概述

本工作区是 Obsidian 课程讲义同步系统的 monorepo，包含笔记源和文档发布两个部分。

- **tnote/**：Obsidian 笔记源（中文课程讲义）
- **docs-site/**：Astro + Starlight 静态文档站点（独立仓库，不在工作区）

工作流：编辑 `tnote/课程讲义/` 中的笔记，通过 `docs-site` 的 sync 脚本同步并发布到 Cloudflare Pages。

## 技术栈

- **内容源**：Obsidian + Markdown（中文）
- **文档框架**：Astro + Starlight
- **同步工具**：Python 3（sync.py）
- **包管理**：pnpm（docs-site）
- **部署**：Cloudflare Pages

## 目录结构

```
/workspace/projects/
├── .coze                    # 项目配置
├── AGENTS.md                # 本文件
├── CLAUDE.md                # Claude Code 指导文件
├── README.md                # 项目说明
├── *.py                     # 一次性迁移脚本（根目录）
└── tnote/
    ├── .coze                # 子项目配置
    └── 课程讲义/             # Obsidian 笔记源
        ├── Windows 服务器安全配置/
        └── 数据库系统管理和运维/
```

## 关键入口 / 核心模块

- **sync.py**（在 docs-site 中）：核心同步脚本，将 `tnote/课程讲义/` 同步到站点内容目录
- **mapping.json**（在 docs-site 中）：中文文件名到 ASCII slug 的映射表
- **astro.config.mjs**（在 docs-site 中）：Starlight 侧边栏配置

## 运行与预览

由于 Astro 站点 `docs-site/` 不在工作区，本地无法直接预览。

**正常开发流程（需要 docs-site）**：
```bash
cd docs-site
pnpm install
pnpm sync              # 同步笔记
pnpm dev               # 本地预览
pnpm build             # 构建静态站点
```

**docs-site 独立部署**：
- Build command: `pnpm install --frozen-lockfile && pnpm build`
- Output directory: `dist`
- 环境要求：Node.js >= 22.12.0

## 用户偏好与长期约束

- 编辑源笔记在 `tnote/课程讲义/`，不要直接编辑 `docs-site/src/content/docs/`（会被同步覆盖）
- `docs-site/` 有独立的 .git，可以单独推送部署
- 新增笔记文件会自动添加到 mapping.json

## 常见问题和预防

- **预览失败**：确认 docs-site 已克隆且 pnpm install 已执行
- **同步问题**：检查 mapping.json 是否包含目标文件，Python 3 是否可用
- **中文路径**：docs-site 会将中文目录名转换为 ASCII slug（见 slug_map）
