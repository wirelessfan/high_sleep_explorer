"""Update only the learning site block, preserving the blog and staging sites."""
from __future__ import annotations

import argparse
from pathlib import Path
import re


def render(source: str, domains: str, port: int = 8090) -> str:
    hosts = [host.strip() for host in domains.split(',') if host.strip()]
    if not hosts or any(not re.fullmatch(r'[a-zA-Z0-9.-]+', host) for host in hosts):
        raise ValueError('domains must be comma-separated hostnames')
    aliases = list(dict.fromkeys([hosts[0]] + [f'{host}:{port}' for host in hosts]))
    lines = source.splitlines(keepends=True)
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Known production hostnames/port; never match the bare :80/:8091 blocks.
        is_site = ('{' in line and not line.lstrip().startswith('#')
                   and (f':{port}' in line or any(host in line for host in hosts)))
        if is_site:
            depth = line.count('{') - line.count('}')
            i += 1
            while i < len(lines) and depth:
                depth += lines[i].count('{') - lines[i].count('}')
                i += 1
            continue
        if line.strip() == '# 高中理科学习助手':
            i += 1
            continue
        out.append(line)
        i += 1
    return ''.join(out).rstrip() + '\n\n# 高中理科学习助手\n' + ', '.join(aliases) + ''' {
    encode zstd gzip
    log {
        output file /var/log/caddy/learning.log
    }
    reverse_proxy 127.0.0.1:8000
}
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=Path)
    parser.add_argument('--domains', required=True)
    parser.add_argument('--port', type=int, default=8090)
    args = parser.parse_args()
    args.path.write_text(render(args.path.read_text(), args.domains, args.port))
