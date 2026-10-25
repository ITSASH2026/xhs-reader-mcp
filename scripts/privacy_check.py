"""Inspect a prospective source tree without echoing any sensitive matches.

Optional private deny strings are read from a file outside the release tree.
This is a release aid, not proof of anonymity or a general secret detector.
"""
import argparse
import ipaddress
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

FORBIDDEN_DIRECTORIES={'.git','private','data','Volume','models','downloads','logs','.venv','__pycache__','.pytest_cache'}
FORBIDDEN_EXTENSIONS={'.db','.sqlite','.sqlite3','.key','.pem','.pfx','.mp4','.mov','.mp3','.wav','.jpg','.jpeg','.png','.zip','.pyc'}
PUBLIC_URL_DOMAINS={
    'github.com','api.github.com','huggingface.co','www.gnu.org','gnu.org',
    'ffmpeg.org','example.com','mcp.example.com','www.xiaohongshu.com',
    'xiaohongshu.com','xhslink.com','xhslink.cn','xhs.link','fsf.org',
    '127.0.0.1','0.0.0.0',
}


def inspect(root,deny=()):
    root=Path(root).resolve()
    problems=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if path.is_symlink():
            problems.append((str(relative),'symlink'));continue
        if path.is_dir():
            if path.name in FORBIDDEN_DIRECTORIES:
                problems.append((str(relative),'private/generated directory'))
            continue
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS or (path.name.startswith('.env') and path.name!='.env.example'):
            problems.append((str(relative),'private/generated file'))
        try:
            text=path.read_text(encoding='utf-8')
        except (UnicodeError,OSError):
            problems.append((str(relative),'non-text/unreadable file'));continue
        lowered=text.casefold()
        if any(value and value.casefold() in lowered for value in deny):
            problems.append((str(relative),'private deny-list match'))
        if re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text):
            problems.append((str(relative),'private key material'))
        if re.search(r'(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})',text):
            problems.append((str(relative),'credential pattern'))
        if re.search(r'[A-Za-z]:[\\/]Users[\\/][^\s\\/]+',text):
            problems.append((str(relative),'personal workstation path'))
        for match in re.finditer(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])',text):
            try:
                address=ipaddress.ip_address(match.group())
            except ValueError:
                continue
            if str(address) not in {'127.0.0.1','0.0.0.0'}:
                problems.append((str(relative),'non-local IPv4 address'))
        # Domain parsing excludes regex literals and code-only host fragments.
        for match in re.finditer(r'https?://[^\s\"\'<>`]+',text):
            host=(urlsplit(match.group()).hostname or '').lower().rstrip('.')
            if host not in PUBLIC_URL_DOMAINS and not host.endswith('.example'):
                problems.append((str(relative),'unreviewed URL host'))
    return sorted(set(problems))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',nargs='?',default='.')
    parser.add_argument('--deny-file',type=Path)
    args=parser.parse_args()
    root=Path(args.directory).resolve()
    deny=[]
    if args.deny_file:
        if args.deny_file.resolve().is_relative_to(root):
            raise SystemExit('Keep the private deny list outside the source tree.')
        deny=args.deny_file.read_text(encoding='utf-8').splitlines()
    problems=inspect(root,deny)
    for filename,category in problems:
        print(f'REVIEW: {filename}: {category}')
    if problems:
        print(f'Privacy check: {len(problems)} item(s) require review; matching values are not printed.')
        return 1
    print('Privacy check passed: no matches in the configured source-tree checks.')
    return 0


if __name__=='__main__':
    sys.exit(main())
