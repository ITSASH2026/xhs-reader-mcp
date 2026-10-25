"""Apply explicit deployment-only changes to the pinned upstream image."""
from pathlib import Path


def patch(root=Path('/app')):
    path=root/'source/application/app.py'
    source=path.read_text()
    old='print(_("鉴权令牌: {}").format(generate_auth_token()))'
    if source.count(old)!=2:
        raise RuntimeError('Pinned upstream token-log locations changed; review before building.')
    source=source.replace(old,'print("Authentication enabled; use the local private configuration to connect.")')
    path.write_text(source)
    # Upstream disables certificate verification in these request helpers.
    # This public distribution enables it; no insecure fallback is attempted.
    for relative in ('source/application/request.py','source/module/manager.py'):
        path=root/relative
        source=path.read_text()
        if 'verify=False' not in source:
            raise RuntimeError('Pinned upstream TLS configuration changed; review before building.')
        path.write_text(source.replace('verify=False','verify=True'))


if __name__=='__main__':
    patch()
