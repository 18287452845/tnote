import os, shutil, re

src_base = 'C:/Users/admin/Documents/tnote/tnote/课程讲义'
dst_base = 'C:/Users/admin/Documents/tnote/docs-site/src/content/docs'

slug_map = {
    'Windows 服务器安全配置/01 项目一 走进Windows服务器': '/windows-server-security/01-intro',
    'Windows 服务器安全配置/01 项目一 走进Windows服务器/实验：初识渗透测试——Nmap信息收集与RDP弱口令演示': '/windows-server-security/01-intro/lab-nmap-rdp',
    'Windows 服务器安全配置/02 项目二 Windows服务器用户管理': '/windows-server-security/02-user-management',
    'Windows 服务器安全配置/03 项目三 Windows服务器共享管理': '/windows-server-security/03-share-management',
    'Windows 服务器安全配置/04 项目四 Windows服务器网站管理': '/windows-server-security/04-website-management',
    'Windows 服务器安全配置/05 项目五 Windows服务器远程管理': '/windows-server-security/05-remote-management',
    'Windows 服务器安全配置/06 项目六 Windows域管理': '/windows-server-security/06-domain-management',
    'Windows 服务器安全配置/07 项目七 Windows应用安全': '/windows-server-security/07-app-security',
    'Windows 服务器安全配置/08 项目八 Windows内网安全': '/windows-server-security/08-intranet-security',
    'Windows 服务器安全配置/实验一：服务器信息收集与SNMP枚举渗透': '/windows-server-security/lab1-snmp-recon',
    'Windows 服务器安全配置/实验二：用户账户暴力破解与凭据提取渗透': '/windows-server-security/lab2-bruteforce-creds',
    'Windows 服务器安全配置/实验三：SMB与FTP共享服务渗透': '/windows-server-security/lab3-smb-ftp',
    'Windows 服务器安全配置/实验四：IIS Web服务安全审计与渗透': '/windows-server-security/lab4-iis-web',
    'Windows 服务器安全配置/实验五：RDP远程桌面安全渗透': '/windows-server-security/lab5-rdp',
    'Windows 服务器安全配置/实验六：Windows域环境渗透与提权': '/windows-server-security/lab6-domain-privesc',
    'Windows 服务器安全配置/实验七：后门持久化与WebShell攻防': '/windows-server-security/lab7-backdoor-webshell',
    'Windows 服务器安全配置/实验八：内网横向移动与域控攻陷': '/windows-server-security/lab8-lateral-dc',
    '数据库系统管理和运维/01 项目一 SQL Server 2008基础': '/database-admin/01-sql-server-basics',
    '数据库系统管理和运维/02 项目二 SQL Server 2008安全管理': '/database-admin/02-sql-server-security',
    '数据库系统管理和运维/03 项目三 数据库维护': '/database-admin/03-db-maintenance',
    '数据库系统管理和运维/04 项目四 数据加密': '/database-admin/04-data-encryption',
    '数据库系统管理和运维/05 项目五 MySQL数据库安全基础': '/database-admin/05-mysql-basics',
    '数据库系统管理和运维/06 项目六 MySQL数据库高级安全维护': '/database-admin/06-mysql-advanced',
    '数据库系统管理和运维/SQL 基础语法讲义': '/database-admin/sql-basics',
    '数据库系统管理和运维/实验三 数据': '/database-admin/lab3-data',
    '数据库系统管理和运维/实验三 数据/README': '/database-admin/lab3-data/readme',
}

count = 0
for dirpath, dirnames, filenames in os.walk(src_base):
    for fn in filenames:
        if not fn.endswith('.md'):
            continue
        src_fpath = os.path.join(dirpath, fn)
        rel = os.path.relpath(src_fpath, src_base)
        rel_no_ext = os.path.splitext(rel)[0].replace(os.sep, '/')

        dst_fpath = os.path.join(dst_base, rel)
        os.makedirs(os.path.dirname(dst_fpath), exist_ok=True)
        shutil.copy2(src_fpath, dst_fpath)

        with open(dst_fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        title_m = re.match(r'^#\s+(.+)', content, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else fn.replace('.md', '')
        slug_val = slug_map.get(rel_no_ext, '')

        fm = f'---\ntitle: {title}\n'
        if slug_val:
            fm += f'slug: {slug_val}\n'
        fm += '---\n\n'

        with open(dst_fpath, 'w', encoding='utf-8') as f:
            f.write(fm + content)
        count += 1
        print(f'{"slug: " + slug_val if slug_val else "NO SLUG"} <- {rel}')

print(f'Done: {count} files')
