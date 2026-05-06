import os, sys

docs_root = sys.argv[1]

slug_map = {
    "Windows 服务器安全配置": "windows-server-security",
    "数据库系统管理和运维": "database-admin",
}

for dirpath, dirnames, filenames in os.walk(docs_root):
    for fn in filenames:
        if not fn.endswith('.md') and not fn.endswith('.mdx'):
            continue
        fpath = os.path.join(dirpath, fn)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        if fn == 'index.mdx':
            continue

        has_slug = 'slug:' in content[:300]
        if has_slug:
            continue

        rel_dir = os.path.relpath(dirpath, docs_root)
        rel_dir = rel_dir.replace(os.sep, '/')
        parts = [slug_map.get(p, p) for p in rel_dir.split('/')]
        name = fn.replace('.md', '').replace('.mdx', '')
        full_slug = '/'.join(parts + [name])

        if content.startswith('---'):
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if line.startswith('title:'):
                    new_lines.append(f'slug: /{full_slug}')
                    break
            content = '\n'.join(new_lines)

        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"slug: /{full_slug} <- {os.path.relpath(fpath, docs_root)}")

print("Done!")
