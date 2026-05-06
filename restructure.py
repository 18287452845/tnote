import os, shutil, re, sys

docs_root = sys.argv[1]

# Full mapping: old relative path -> new relative path
rename_map = {
    "Windows 服务器安全配置": "windows-server-security",
    "数据库系统管理和运维": "database-admin",
}

file_rename_map = {
    "01 项目一 走进Windows服务器.md": "01-intro.md",
    "02 项目二 Windows服务器用户管理.md": "02-user-management.md",
    "03 项目三 Windows服务器共享管理.md": "03-share-management.md",
    "04 项目四 Windows服务器网站管理.md": "04-website-management.md",
    "05 项目五 Windows服务器远程管理.md": "05-remote-management.md",
    "06 项目六 Windows域管理.md": "06-domain-management.md",
    "07 项目七 Windows应用安全.md": "07-app-security.md",
    "08 项目八 Windows内网安全.md": "08-intranet-security.md",
    "实验一：服务器信息收集与SNMP枚举渗透.md": "lab1-snmp-recon.md",
    "实验二：用户账户暴力破解与凭据提取渗透.md": "lab2-bruteforce-creds.md",
    "实验三：SMB与FTP共享服务渗透.md": "lab3-smb-ftp.md",
    "实验四：IIS Web服务安全审计与渗透.md": "lab4-iis-web.md",
    "实验五：RDP远程桌面安全渗透.md": "lab5-rdp.md",
    "实验六：Windows域环境渗透与提权.md": "lab6-domain-privesc.md",
    "实验七：后门持久化与WebShell攻防.md": "lab7-backdoor-webshell.md",
    "实验八：内网横向移动与域控攻陷.md": "lab8-lateral-dc.md",
    "01 项目一 SQL Server 2008基础.md": "01-sql-server-basics.md",
    "02 项目二 SQL Server 2008安全管理.md": "02-sql-server-security.md",
    "03 项目三 数据库维护.md": "03-db-maintenance.md",
    "04 项目四 数据加密.md": "04-data-encryption.md",
    "05 项目五 MySQL数据库安全基础.md": "05-mysql-basics.md",
    "06 项目六 MySQL数据库高级安全维护.md": "06-mysql-advanced.md",
    "SQL 基础语法讲义.md": "sql-basics.md",
    "实验三 数据.md": "lab3-data.md",
}

# Step 1: Copy from original vault with ASCII names
src_base = 'C:/Users/admin/Documents/tnote/tnote/课程讲义'
tmp_dir = os.path.join(docs_root, '_tmp')
if os.path.exists(tmp_dir):
    shutil.rmtree(tmp_dir)
os.makedirs(tmp_dir)

for old_dir, new_dir in rename_map.items():
    src_dir = os.path.join(src_base, old_dir)
    dst_dir = os.path.join(tmp_dir, new_dir)
    os.makedirs(dst_dir, exist_ok=True)

    for fn in os.listdir(src_dir):
        if fn.endswith('.md'):
            new_fn = file_rename_map.get(fn, fn)
            shutil.copy2(os.path.join(src_dir, fn), os.path.join(dst_dir, new_fn))

# Handle subdirectories
for old_dir, new_dir in rename_map.items():
    src_dir = os.path.join(src_base, old_dir)
    dst_dir = os.path.join(tmp_dir, new_dir)
    for subdir in os.listdir(src_dir):
        sub_src = os.path.join(src_dir, subdir)
        if os.path.isdir(sub_src):
            new_subdir = rename_map.get(subdir, subdir)
            # For subdirectory like "01 项目一 走进Windows服务器"
            sub_map = {
                "01 项目一 走进Windows服务器": "01-intro",
            }
            new_subdir = sub_map.get(subdir, subdir)
            os.makedirs(os.path.join(dst_dir, new_subdir), exist_ok=True)
            for fn in os.listdir(sub_src):
                if fn.endswith('.md'):
                    new_fn = file_rename_map.get(fn, fn)
                    shutil.copy2(os.path.join(sub_src, fn), os.path.join(dst_dir, new_subdir, new_fn))

# Step 2: Remove old Chinese-named directories
for old_dir in rename_map:
    old_path = os.path.join(docs_root, old_dir)
    if os.path.exists(old_path):
        shutil.rmtree(old_path)

# Step 3: Move temp to final
for item in os.listdir(tmp_dir):
    shutil.move(os.path.join(tmp_dir, item), os.path.join(docs_root, item))
shutil.rmtree(tmp_dir)

# Step 4: Add frontmatter with title (keep Chinese titles for display)
count = 0
title_map = {
    "01-intro.md": "01.项目一 走进Windows服务器",
    "02-user-management.md": "02.项目二 Windows服务器用户管理",
    "03-share-management.md": "03.项目三 Windows服务器共享管理",
    "04-website-management.md": "04.项目四 Windows服务器网站管理",
    "05-remote-management.md": "05.项目五 Windows服务器远程管理",
    "06-domain-management.md": "06.项目六 Windows域管理",
    "07-app-security.md": "07.项目七 Windows应用安全",
    "08-intranet-security.md": "08.项目八 Windows内网安全",
    "lab1-snmp-recon.md": "实验一：服务器信息收集与SNMP枚举渗透",
    "lab2-bruteforce-creds.md": "实验二：用户账户暴力破解与凭据提取渗透",
    "lab3-smb-ftp.md": "实验三：SMB与FTP共享服务渗透",
    "lab4-iis-web.md": "实验四：IIS Web服务安全审计与渗透",
    "lab5-rdp.md": "实验五：RDP远程桌面安全渗透",
    "lab6-domain-privesc.md": "实验六：Windows域环境渗透与提权",
    "lab7-backdoor-webshell.md": "实验七：后门持久化与WebShell攻防",
    "lab8-lateral-dc.md": "实验八：内网横向移动与域控攻陷",
    "lab-nmap-rdp.md": "实验：初识渗透测试——Nmap信息收集与RDP弱口令演示",
    "01-sql-server-basics.md": "01.项目一 SQL Server 2008基础",
    "02-sql-server-security.md": "02.项目二 SQL Server 2008安全管理",
    "03-db-maintenance.md": "03.项目三 数据库维护",
    "04-data-encryption.md": "04.项目四 数据加密",
    "05-mysql-basics.md": "05.项目五 MySQL数据库安全基础",
    "06-mysql-advanced.md": "06.项目六 MySQL数据库高级安全维护",
    "sql-basics.md": "SQL 基础语法讲义",
    "lab3-data.md": "实验三 数据",
    "readme.md": "实验三 数据",
}

for dirpath, dirnames, filenames in os.walk(docs_root):
    for fn in filenames:
        if not fn.endswith('.md'):
            continue
        if fn == 'index.mdx':
            continue
        fpath = os.path.join(dirpath, fn)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract title from first # heading if no title in frontmatter
        title = title_map.get(fn)
        if not title:
            m = re.match(r'^#\s+(.+)', content, re.MULTILINE)
            title = m.group(1).strip() if m else fn

        if not content.startswith('---'):
            frontmatter = f'---\ntitle: {title}\n---\n\n'
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(frontmatter + content)
            count += 1

# Step 5: List final structure
print("Final structure:")
for dirpath, dirnames, filenames in os.walk(docs_root):
    level = dirpath.replace(docs_root, '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(dirpath)}/')
    sub_indent = ' ' * 2 * (level + 1)
    for fn in filenames:
        print(f'{sub_indent}{fn}')

print(f"\nFrontmatter added to {count} files")
