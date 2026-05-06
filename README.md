# tnote

`tnote` 用来保存 Obsidian 原始笔记，`docs-site` 用来生成并发布到 GitHub / Cloudflare Pages 的文档站点。

## 目录说明

- `tnote/`: Obsidian 内容源，当前主要是 `课程讲义/`
- `docs-site/`: Astro + Starlight 站点
- `docs-site/src/content/docs/`: 站点最终使用的 Markdown 内容
- `docs-site/mapping.json`: Obsidian 文件到站点路由文件名的映射

## 本地使用

1. 进入站点目录：

```bash
cd /mnt/c/Users/admin/Documents/tnote/docs-site
```

2. 安装依赖：

```bash
cd /mnt/c/Users/admin/Documents/tnote/docs-site
pnpm install
```

3. 从 `tnote/课程讲义` 同步到站点内容：

```bash
pnpm sync
```

4. 本地预览：

```bash
pnpm dev
```

## 发布说明

`docs-site` 目录可以单独推送到 GitHub 仓库，再由 Cloudflare Pages 拉取构建。

运行 `docs-site` 需要 `Node.js >= 22.12.0`。

- Build command: `pnpm install --frozen-lockfile && pnpm build`
- Output directory: `dist`

如果希望本地同步后再构建，可以执行：

```bash
pnpm build:local
```
