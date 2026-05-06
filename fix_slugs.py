import os, re, sys

docs_root = sys.argv[1]

def to_ascii_slug(text):
    """Convert Chinese text to ASCII slug using pinyin-like mapping."""
    mapping = {
        "项目": "project", "项目一": "01-project", "项目二": "02-project",
        "项目三": "03-project", "项目四": "04-project", "项目五": "05-project",
        "项目六": "06-project", "项目七": "07-project", "项目八": "08-project",
        "走进": "intro", "Windows服务器": "windows-server",
        "Windows": "windows", "服务器": "server",
        "用户管理": "user-mgmt", "共享管理": "share-mgmt",
        "网站管理": "website-mgmt", "远程管理": "remote-mgmt",
        "域管理": "domain-mgmt", "应用安全": "app-security",
        "内网安全": "intranet-security",
        "SQL Server 2008基础": "sql-server-2008-basics",
        "SQL Server 2008安全管理": "sql-server-2008-security",
        "数据库维护": "db-maintenance", "数据加密": "data-encryption",
        "MySQL数据库安全基础": "mysql-security-basics",
        "MySQL数据库高级安全维护": "mysql-advanced-security",
        "SQL 基础语法讲义": "sql-basics",
        "实验三 数据": "lab3-data", "实验": "lab",
        "实验一：服务器信息收集与SNMP枚举渗透": "lab1-snmp-recon",
        "实验二：用户账户暴力破解与凭据提取渗透": "lab2-bruteforce-creds",
        "实验三：SMB与FTP共享服务渗透": "lab3-smb-ftp",
        "实验四：IIS Web服务安全审计与渗透": "lab4-iis-web",
        "实验五：RDP远程桌面安全渗透": "lab5-rdp",
        "实验六：Windows域环境渗透与提权": "lab6-domain-privesc",
        "实验七：后门持久化与WebShell攻防": "lab7-backdoor-webshell",
        "实验八：内网横向移动与域控攻陷": "lab8-lateral-dc",
        "实验：初识渗透测试——Nmap信息收集与RDP弱口令演示": "lab-nmap-rdp-intro",
    }
    result = text
    # Sort by length descending to match longer phrases first
    for key in sorted(mapping.keys(), key=len, reverse=True):
        result = result.replace(key, mapping[key])
    # Clean remaining non-ASCII and special chars
    result = re.sub(r'[^\w\-/]', '-', result)
    result = re.sub(r'-+', '-', result).strip('-')
    return result.lower()

dir_slug_map = {
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

        # Extract title for slug generation
        title_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else fn

        rel_dir = os.path.relpath(dirpath, docs_root).replace(os.sep, '/')
        parts = [dir_slug_map.get(p, p) for p in rel_dir.split('/')]
        file_slug = to_ascii_slug(title)

        full_slug = '/'.join(parts + [file_slug])

        # Replace existing slug or add new one
        if 'slug:' in content[:300]:
            content = re.sub(r'^slug:.*$', f'slug: /{full_slug}', content, count=1, flags=re.MULTILINE)
        else:
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
        print(f"/{full_slug}")

print("Done!")
