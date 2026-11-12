"""Integrate bounded downloads with the authenticated oTree 6.0.15 export views.

Run by the Heroku post_compile hook. Run in a local oTree environment to
install the same web interface there. Re-running on a cached build is safe.
"""
from importlib.util import find_spec
from pathlib import Path


def replace_once(path, old, new):
    text = path.read_text(encoding='utf-8')
    if new in text:
        return
    if text.count(old) != 1:
        raise RuntimeError(f'Unexpected oTree export integration point in {path}')
    path.write_text(text.replace(old, new), encoding='utf-8')


def install(root):
    views = root / 'views' / 'export.py'
    replace_once(views, '        buf = StringIO()', '''        # The normal login or REST-key check has already run here.
        from survey_exports import download
        if isinstance(self, ExportWideLogin):
            if not query_params.get('kind') and not query_params.get('session_code'):
                return Response('Please refresh the Data page and click the download again.', status_code=400)
            return download(request, query_params.get('kind', 'wide'))
        if isinstance(self, (ExportWide, ExportApp, ExportAppCustom)):
            kind = {ExportWide: 'wide', ExportApp: 'app', ExportAppCustom: 'custom'}[type(self)]
            return download(request, kind)
        buf = StringIO()''')
    # A tab opened before this release can still send an old websocket request.
    consumer = root / 'channels' / 'consumers.py'
    replace_once(consumer, "        app_name = content.get('app_name')\n        is_custom = content.get('is_custom')",
                 """        await self.send_json(dict(content, error='Refresh the Data page to use the updated CSV downloads.'))
        return
        app_name = content.get('app_name')
        is_custom = content.get('is_custom')""")
    template = root / 'templates' / 'otree' / 'SessionData.html'
    for excel in (False, True):
        suffix = '?format=csv_bom' if excel else ''
        name = 'Excel CSV' if excel else 'Regular CSV'
        url = '{% url \'ExportWideLogin\' %}?session_code={{ session.code }}'
        if excel:
            url += '&amp;format=csv_bom'
        replace_once(template, "{% url 'ExportWideLogin' session.code %}"+suffix+'">'+name,
                     url+'">'+name)
    index = template.with_name('ExportIndex.html')
    for line in index.read_text(encoding='utf-8').splitlines():
        if 'class="download-link"' not in line:
            continue
        kind = 'custom' if 'data-custom' in line else 'app' if 'data-app' in line else 'wide'
        url = "{% url 'ExportWideLogin' %}?kind=" + kind
        if 'data-excel' in line:
            url += '&amp;format=csv_bom'
        label = 'Excel CSV' if 'data-excel' in line else 'CSV'
        replace_once(index, line, '              <a href="'+url+'">'+label+'</a>')
    # All six downloads are now normal browser links; no export websocket is needed.
    replace_once(index, '      initWebSocket();', '      // Downloads stream over the authenticated HTTP connection.')


if __name__ == '__main__':
    install(Path(find_spec('otree').origin).parent)
