# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a monorepo that syncs Obsidian course notes (`tnote/`) into a static documentation site (`docs-site/`) built with Astro + Starlight, deployed to Cloudflare Pages at `https://teaching-docs.pages.dev`.

- `tnote/课程讲义/` — Obsidian vault source (Chinese course lecture notes)
- `docs-site/` — Astro + Starlight site that serves the published docs
- `docs-site/sync.py` — Python sync script that copies and transforms notes from the vault into the site content directory
- `docs-site/mapping.json` — Maps Obsidian source file paths to ASCII site filenames

## Common Commands

All site commands run from `docs-site/`:

```bash
cd docs-site
pnpm install          # Install dependencies
pnpm sync             # Sync tnote/课程讲义 -> src/content/docs/ (requires Python 3)
pnpm sync:show        # Show current file mapping table
pnpm dev              # Local dev server
pnpm build            # Build static site
pnpm build:local      # Sync + build in one step
pnpm check            # Run Astro content checker
```

**Build deployment:** `pnpm install --frozen-lockfile && pnpm build`, output in `dist/`.

Requires Node.js >= 22.12.0, pnpm 10.x, Python 3 (for sync).

## Architecture

### Sync Pipeline (`sync.py`)

The sync script is the key piece of tooling. It:
1. Reads `.md` files from `tnote/课程讲义/` (the Obsidian vault)
2. Maps Chinese filenames to ASCII slugs using `mapping.json` (auto-extends on new files)
3. Translates Chinese directory names via `DIR_MAP` (e.g., `Windows 服务器安全配置` -> `windows-server-security`)
4. Rewrites Obsidian `[[wikilinks]]` and markdown `[text](relative.md)` links to site routes
5. Injects Starlight frontmatter (`title:`) extracted from the first `#` heading
6. Writes to `docs-site/src/content/docs/`

New files in the vault are auto-mapped and `mapping.json` is updated. Existing mappings in `mapping.json` take precedence.

### Site Structure (Astro + Starlight)

- `astro.config.mjs` — Defines sidebar: `windows-server-security` and `database-admin` directories
- `src/content/docs/` — Generated content (do not edit directly; edits are overwritten on next sync)
- `src/content.config.ts` — Standard Starlight content config

### Root-Level Python Scripts

`restructure.py`, `fix_links2.py`, `fix_slugs.py`, `set_slugs.py`, `add_slugs.py`, `restore_all.py` — One-time migration scripts used during initial setup. Not part of the regular workflow.

## Key Conventions

- Edit source notes in `tnote/课程讲义/`, not in `docs-site/src/content/docs/`
- The `docs-site/` directory has its own `.git` and can be pushed independently to its own GitHub repo for Cloudflare Pages deployment
- Sidebar navigation is auto-generated from the directory structure inside `src/content/docs/`
- File names in `docs-site/src/content/docs/` must be ASCII slugs (the sync script handles this)
