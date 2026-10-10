"""Build the ten illustrated v2 portraits in the survey's existing SVG style.

Two presentations across five varied skin/face/hair combinations. Picker labels
are numbered, not ethnic categories. Keep old SVGs for historical selections.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / '_static/social/avatars'
PALETTES = [
    ('#f5d8c4', '#b36a3f', '#bd9553'),
    ('#cf9b76', '#593526', '#493026'),
    ('#e8bd97', '#242326', '#242326'),
    ('#79503b', '#211c1b', '#211c1b'),
    ('#b9825d', '#302421', '#302421'),
]


def portrait(style, number):
    skin, feminine_hair, masculine_hair = PALETTES[number - 1]
    hair = feminine_hair if style == 'feminine' else masculine_hair
    curly = number == 4
    straight = number == 3
    back = ''
    if style == 'feminine':
        back = f'<path d="M21 76V36C21 7 75 7 75 36v40l-16-3H37Z" fill="{hair}"/>'
        if curly:
            back = f'<path d="M19 76C9 63 16 52 13 40 9 27 18 15 29 16 33 5 47 9 50 10 63 4 71 14 73 20 88 24 80 38 82 46 90 59 77 66 77 76Z" fill="{hair}"/>'
    face = ('M28 34c0-25 40-25 40 0v13c-1 13-10 21-20 21S29 60 28 47Z'
            if style == 'feminine' else
            'M27 34c0-25 42-25 42 0v15c-1 10-11 19-21 19S28 59 27 49Z')
    if style == 'feminine':
        front = ('M26 41V30C25 10 69 10 70 30v15l-5-15-22-7-13 16Z' if straight else
                 'M28 38C22 12 68 5 70 34l-1 12-5-13c-15 2-21-7-23-10-1 9-8 12-13 15Z')
    else:
        front = ('M27 41l-3-14c0-18 48-20 48 1l-3 15-5-15-27-2-6 15Z' if straight else
                 'M28 42l-3-14C23 16 37 13 46 14c4-7 12-5 14-1 11 0 16 10 11 22l-3 8-3-16c-9 4-18 2-23-1l-10 7Z')
    if curly:
        front = 'M26 43l-4-12c-7-5-5-15 3-17 1-8 10-10 16-6 6-7 16-5 19 0 11-2 18 7 14 15 5 6 1 13-6 18l-2-15c-11 4-22 2-32 1Z'
    eyes = ('<path d="M35 43q4-3 8 0m10 0q4-3 8 0" fill="none" stroke-width="1.5"/>'
            '<path d="M39 42.5v1m18-1v1" stroke-width="2.2"/>' if straight else
            '<path d="M39 43v1m18-1v1" stroke-width="2.7"/>')
    nose = 'm47 45-2 7q3 2 6 0' if curly else 'm48 45-2 7h4'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><defs><clipPath id="circle"><circle cx="48" cy="48" r="47"/></clipPath></defs><g clip-path="url(#circle)"><path fill="#e8eef5" d="M0 0h96v96H0z"/>{back}<path d="M12 97c1-19 13-27 28-28h16c15 1 27 9 28 28" fill="#557b9e"/><path d="M39 57h18v16c-5 8-13 8-18 0Z" fill="{skin}"/><path d="M39 59h18v8c-6 4-12 3-18 0Z" fill="#33201b" opacity=".13"/><ellipse cx="28" cy="43" rx="4" ry="7" fill="{skin}"/><ellipse cx="68" cy="43" rx="4" ry="7" fill="{skin}"/><path d="{face}" fill="{skin}"/><path d="{front}" fill="{hair}"/><g stroke="#352a29" stroke-linecap="round"><path d="M35 38q5-3 9-1m9 0q5-2 9 1" fill="none" stroke-width="1.6"/>{eyes}<path d="{nose}" fill="none" stroke-width="1.3" opacity=".45"/><path d="M42 57q6 5 12 0" fill="none" stroke-width="1.7"/></g><path d="M30 96V84m36 12V84" stroke="#416681" stroke-width="1.5"/></g><circle cx="48" cy="48" r="47" fill="none" stroke="#d5dfe9"/></svg>
'''


if __name__ == '__main__':
    for style in ('feminine', 'masculine'):
        for number in range(1, 6):
            (OUT / f'{style}-v2-{number}.svg').write_text(portrait(style, number), encoding='utf-8')
