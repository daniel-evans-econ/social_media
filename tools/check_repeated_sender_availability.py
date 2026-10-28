"""Check the current stratum-wide selector against archived sender restrictions."""
import json
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import simulate_stratified_feedback as sim


def main():
    out = sim.ROOT / 'analysis/strata_comparison'
    pools = sim.reference('initial')
    results = []
    for design, strata in [('quintiles', 5), ('terciles', 3), ('halves', 2)]:
        old = json.loads((out / design / 'results.json').read_text())
        profiles = old['message_results'][0]['profiles']
        rng = sim.np.random.default_rng(sim.SEED + 1)
        for fmt in sim.FORMATS:
            counts = [[], []]
            task_counts = defaultdict(list)
            repeated_sender_profiles = 0
            for i in range(profiles):
                order = list(rng.permutation(sim.TASKS))
                p = sim.fake_player(f'stratified-{sim.SEED}-{fmt}-{i}', order, fmt)
                fingerprints, names = set(), []
                for slot, period in enumerate((1, 3)):
                    group = sim.stratified_group(p, period, pools, strata)
                    received = 0
                    for block in range(1, 4):
                        p.round_number = (period - 1) * 15 + block * 5
                        msg = sim.message_for(p, fmt)
                        if msg:
                            assert msg['fingerprint'] not in fingerprints
                            assert msg['id'].split('-')[0] in {r['id'] for r in sim.stratum_records_for(p, period)}
                            fingerprints.add(msg['fingerprint'])
                            names.append(msg['name'].strip().casefold())
                            received += 1
                    counts[slot].append(received)
                    task_counts[(slot, order[period - 1])].append(received)
                repeated_sender_profiles += len(names) > len(set(names))
            for slot in range(2):
                prior = next(r for r in old['message_results'] if r['format'] == fmt and r['social_period_number'] == slot + 1)
                row = dict(design=design, format=fmt, social_period_number=slot + 1,
                           profiles=profiles, previous_all_three=prior['probability_all_three'],
                           all_three=sum(n == 3 for n in counts[slot]) / profiles,
                           probabilities_0_1_2_3=[counts[slot].count(n) / profiles for n in range(4)],
                           task_results=[dict(task=task, profiles=len(v), all_three=sum(n == 3 for n in v) / len(v))
                                         for (s, task), v in task_counts.items() if s == slot],
                           profiles_with_repeated_sender_either_period=repeated_sender_profiles)
                results.append(row)
                print(json.dumps(row), flush=True)
    result = dict(seed=sim.SEED, task_order_seed=sim.SEED + 1, group_size=sim.N,
                  rule='Whole-stratum message pool; repeated senders allowed; repeated sender/content pairs prohibited across periods.',
                  setup='Actual pilot pools; matched task orders and peer draws; social/control/social; all tasks completed.',
                  source_hashes=old['source_hashes'], results=results)
    target = sim.ROOT / 'analysis/stratum_message_sampling'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'message_availability_details.json').write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
