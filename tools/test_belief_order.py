import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['OTREE_IN_MEMORY']='1'
os.environ['EXPERIMENT_PILOT']='iq'
from otree.database import init_orm
init_orm()
from otree.session import create_session
import social_media as s
from tools.migrate_belief_order import migrate, remap, OLD, NEW, COUNT, MAXIMUM

assert NEW.index('OutcomeConcern') < NEW.index('AverageBeliefs')
assert NEW.index('AverageOutcomes') < NEW.index('PlatformUsage') < NEW.index('RealismQuestion')
for old in range(1, MAXIMUM+1):
    new=remap(old)
    assert (old-1)//COUNT==(new-1)//COUNT
    assert OLD[(old-1)%COUNT]==NEW[(new-1)%COUNT]
parts=create_session('cognitive_tasks',num_participants=4).get_participants()
for part,name in zip(parts,('PlatformUsage','AverageBeliefs','RealismQuestion','IQDebrief')):
    part.vars.pop('belief_before_platform')
    part._index_in_pages=44*COUNT+OLD.index(name)+1
    part._current_form_page_url=None
dry=migrate();assert dry['count']==4
applied=migrate(True);assert dry['records']==applied['records']
assert NEW[(parts[0]._index_in_pages-1)%COUNT]=='AverageBeliefs'
assert s.PlatformUsage.is_displayed(parts[0].get_player('social_media',45))
for part in parts[1:]:
    assert not s.PlatformUsage.is_displayed(part.get_player('social_media',45))
assert migrate(True)['count']==0
print('Passed new page order, all old page mappings, and no skipped beliefs or repeated platform questions for existing participants.')
