"""Render the researcher PDF from the participant and response fields selected by the portal."""
import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ART = Path(__file__).parent / 'social_media' / 'report_art'
KINDS = ('report', 'iq_report', 'global_report')
COMMENTS = {'realism_feedback': 'Experience of sending and receiving messages',
            'realism_behavior': 'Effects on behavior and decisions about sharing', 'comments': 'Additional comments'}
FIELDS = ['round_number', 'age', 'gender', 'display_name', *COMMENTS,
          *(f'{kind}_{suffix}' for kind in KINDS for suffix in ('message', 'emoji', 'shared'))]
EMOJIS = {'👍': ('like', 'Like'), '❤️': ('love', 'Love'), '🤗': ('care', 'Care'),
          '😆': ('haha', 'Haha'), '😢': ('sad', 'Sad'), '😡': ('angry', 'Angry')}
GROUPS = [('qualitative_social', 'selfie'), ('qualitative_social', 'avatar'),
          ('quantitative_social', 'selfie'), ('quantitative_social', 'avatar')]
TASKS = {'sequences': 'Numerical reasoning', 'working_memory': 'Working memory',
         'shape_rotation': 'Spatial reasoning', 'ravens': 'Abstract reasoning'}
GENDERS = {'man': 'Man', 'woman': 'Woman', 'other_prefer_not_say': 'Other / prefer not to answer'}


def clean(value):
    return escape(''.join(ch for ch in str(value) if ch >= ' ' or ch in '\n\t')).replace('\n', '<br/>')


def line(markup, size=10, gap=0, color='#223144', leading=None, keep=False):
    return Paragraph(markup, ParagraphStyle('report', fontName='Helvetica', fontSize=size,
                     leading=leading or size*1.33, textColor=colors.HexColor(color),
                     spaceAfter=gap, keepWithNext=keep, splitLongWords=True, alignment=TA_LEFT))


def emoji(value):
    if value not in EMOJIS:
        return clean(value) if value else ''
    asset, label = EMOJIS[value]
    return f'<img src="{(ART/(asset+".png")).as_posix()}" height="12" width="12" valign="-2"/> {label}'


def profile_section(p):
    story = []
    rows = p['rows']
    social_type, image = p['social_type'], p['image_treatment']
    group = f'{(social_type or "Unrecorded").split("_")[0].title()} / '+{
        'selfie':'Selfie','avatar':'No selfie (avatar)'}.get(image,'Image assignment unrecorded')
    def recorded(key):
        return next((r[key] for r in reversed(rows) if r.get(key) not in (None, '')), None)

    name = p.get('display_name') or recorded('display_name') or 'Username not recorded'
    gender = recorded('gender')
    age = recorded('age')
    icons = list(dict.fromkeys(r[f'{k}_emoji'] for r in rows for k in KINDS
                               if r.get(f'{k}_message') and r.get(f'{k}_emoji')))
    avatar = p.get('avatar_choice')
    pictures = [Image(io.BytesIO(p['photo']), 44, 44)]
    if image == 'avatar' and avatar in {f'{g}-v2-{i}' for g in ('feminine','masculine') for i in range(1,6)}:
        pictures.append(Image(str(ART/(avatar+'.png')), 44, 44))
    identity = [line(f'<b>PARTICIPANT {p["slot"]}   /   {group.upper()}</b>', 8.5, 4, '#286764'),
                line(f'<b>{clean(name)}</b>', 20, 5),
                line(f'Age: {age if age is not None else "Not recorded"} &nbsp; | &nbsp; '
                     f'Gender: {clean(GENDERS.get(gender, gender or "Not recorded"))}', 9)]
    header = Table([[*pictures, identity],
                    [line('Selfie', 8), *([line('Avatar', 8)] if len(pictures)==2 else []), '']],
                   colWidths=[54]*len(pictures)+[None])
    header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),
                                ('BOTTOMPADDING',(0,0),(-1,-1),1)]))
    story += [header, Spacer(1,7)]
    def flag(key, yes, no):
        if p.get(key) is None:
            return None
        return yes if p[key] else no
    tags = [flag('like_treatment','Emoji reactions','No emoji reactions'),
            flag('iq_reference_asked','Initial IQ elicited','No initial IQ elicitation'),
            flag('reveal_truth','Correction assigned','No correction assigned'), 'No ranked feed']
    story.append(line(' &nbsp;·&nbsp; '.join(clean(t) for t in tags if t), 9, 4, '#285b61'))
    for i, task in enumerate(p.get('period_tasks') or [], 1):
        if i == 3 and not p.get('third_period_accepted'):
            continue
        cond = p.get(f'period_{i}_condition')
        condition = {'control':'Private', 'qualitative_social':'Social', 'quantitative_social':'Social'}.get(cond)
        half = {1:'Lower comparison half', 2:'Upper comparison half'}.get(p['groups'].get(str(i)))
        story.append(line(' &nbsp;·&nbsp; '.join(clean(s) for s in [
            f'Period {i}', TASKS.get(task,task), condition, half] if s),9,1))
    if icons:
        story.append(line('Message emojis: &nbsp; '+' &nbsp; '.join(map(emoji,icons)),9,1))
    story += [Spacer(1,8), line('<b>Messages</b>',13,4,keep=True)]
    count = 0
    for r in rows:
        period, n = divmod(r['round_number']-1,15)
        for k, label in zip(KINDS,(f'Block {n//5+1}','Task IQ','Overall IQ')):
            text = r.get(f'{k}_message')
            if not text:
                continue
            count += 1
            shared = r.get(f'{k}_shared')
            status, tint = {True:('Sent','#176044'), False:('Not sent','#8d4934'),
                            None:('Decision not recorded','#535f70')}[shared]
            mark = emoji(r.get(f'{k}_emoji'))
            story.append(KeepTogether([
                line(f'<b>Period {period+1} · {label}</b> &nbsp; '
                     f'<font color="{tint}"><b>{status}</b></font>'
                     + (' &nbsp; '+mark if mark else ''), 8.5,1,'#4c5e70'),
                line(clean(text),10,5)]))
    if not count:
        story.append(line('No message recorded.',10,5,'#626f7c'))
    story += [Spacer(1,5),line('<b>Comments</b>',13,4,keep=True)]
    entries = [(label,r[k]) for r in rows for k,label in COMMENTS.items() if r.get(k)]
    for label, text in entries:
        story += [line(f'<b>{label}</b>',8.5,2,'#4c5e70',keep=True),line(clean(text),10,6)]
    if not entries:
        story.append(line('No comment recorded.',10,0,'#626f7c'))
    return story


def build_pdf(profiles):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=46, rightMargin=46,
                            topMargin=47, bottomMargin=45, title='Wave 1 participant report')
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor('#c7d4d7'))
        canvas.line(46,32,A4[0]-46,32)
        canvas.setFillColor(colors.HexColor('#566671'))
        canvas.setFont('Helvetica',8)
        canvas.drawString(46,20,'Wave 1  /  Internal research team')
        canvas.drawRightString(A4[0]-46,20,str(doc.page))
    story=[]
    order = {group: i for i, group in enumerate(GROUPS)}
    for profile in sorted(profiles, key=lambda p:(order.get((p['social_type'],p['image_treatment']),4), p['slot'])):
        if story:
            story.append(PageBreak())
        story.extend(profile_section(profile))
    story.append(line('Emoji graphics: <a href="https://github.com/twitter/twemoji">Twemoji</a> '
                      '(<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>).',7,0,'#667782'))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
