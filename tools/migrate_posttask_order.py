"""Preserve responses/progress when effort, credibility and beliefs move earlier.

Save dry-run JSON, then use --apply in maintenance mode. Completed old pages
are skipped if the participant must pass their new position again.
"""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from otree.database import init_orm, db
init_orm()
from otree.models import Participant
import social_media as s

OLD = '''BotCheck Consent SelfieCapture ProlificID IQReferencePoint Intro TaskIntro
QuestionPage BlockFeedback IQFeedback PerceivedPercentile PerceivedPercentileConfidence
MessageReactionFeedback EndOfPeriodSurvey GlobalIQFeedback WTACompare Results
BigFiveSurvey1 BigFiveSurvey2 SelfEsteemSurvey NarcissismSurvey Demographics TaskEffort
OutcomeConcern AverageBeliefs AverageTruth AverageOutcomes PlatformUsage RealismQuestion
ExperienceChecklist1 ExperienceChecklist2 ExperienceChecklist3 ToolsUsed SurveyReliabilityOverall
Comments FinalResults IQDebrief'''.split()
NEW = [page.__name__ for page in s.page_sequence]
OLD_MAX = len(OLD)*s.C.NUM_ROUNDS
NEW_MAX = len(NEW)*s.C.NUM_ROUNDS
MOVED = OLD[OLD.index('BigFiveSurvey1'):OLD.index('AverageOutcomes')+1]


def old_final_index(name):
    return 44*len(OLD)+OLD.index(name)+1


def remap(index, current=False):
    if index is None or index == 0:
        return index
    if index == OLD_MAX+1:
        return NEW_MAX+1
    if not 1 <= index <= OLD_MAX:
        raise ValueError(f'Unexpected index: {index}')
    rd, offset = divmod(index-1,len(OLD))
    name = OLD[offset]
    if current and rd == 44 and name in MOVED:
        name = 'TaskEffort'
    return rd*len(NEW)+NEW.index(name)+1


def migrate(apply=False):
    assert len(OLD)==37 and len(NEW)==38
    records, skipped = [], []
    for part in Participant.objects_filter():
        if part.session.config['app_sequence'] != ['social_media']:
            continue
        if part._max_page_index == NEW_MAX:
            continue
        if part._max_page_index != OLD_MAX or not part.vars.get('belief_before_platform'):
            skipped.append(part.code)
            continue
        fields=('_index_in_pages','_max_page_index','_timeout_page_index','_gbat_page_index','_current_form_page_url')
        before={key:getattr(part,key) for key in fields}
        after={key:remap(before[key],current=key=='_index_in_pages') for key in fields[:4]}
        after['_max_page_index']=NEW_MAX
        url=before['_current_form_page_url']
        after['_current_form_page_url']=re.sub(r'/(\d+)/?$',lambda m:'/'+str(remap(int(m[1]))),url) if url else url
        if old_final_index('BigFiveSurvey1') <= before['_index_in_pages'] <= old_final_index('AverageOutcomes'):
            after['_current_form_page_url']=None
        completed=[name for name in MOVED if old_final_index(name)<before['_index_in_pages']]
        if 'Demographics' in completed:
            completed.append('IQCredibility')
        record=dict(code=part.code,before=before,after=after,completed=completed)
        records.append(record)
        if apply:
            for key,value in after.items():setattr(part,key,value)
            part.vars['completed_before_posttask_reorder']=completed
            part.vars['posttask_order_version']=2
            part.vars['posttask_navigation_migration']=record
    if apply:db.commit()
    return dict(applied=apply,count=len(records),records=records,skipped=skipped)


if __name__=='__main__':
    print(json.dumps(migrate('--apply' in sys.argv)))
