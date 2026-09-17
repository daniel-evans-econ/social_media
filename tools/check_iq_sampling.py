"""Check the survey's IQ comparison-group draw without initializing oTree/DB.

Run: python tools/check_iq_sampling.py
"""
import ast
from pathlib import Path
import random
from statistics import NormalDist
from types import SimpleNamespace
import unittest


class IQSamplingTests(unittest.TestCase):
    def setUp(self):
        source = ast.parse((Path(__file__).resolve().parents[1] / 'social_media' / '__init__.py').read_text(encoding='utf-8'))
        names = {'_percentile_iq', 'iq_noise_offset'}
        nodes = [node for node in source.body if
                 (isinstance(node, ast.FunctionDef) and node.name in names) or
                 (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'IQ_COMPARISON_GROUP' for t in node.targets))]
        self.env = {'random': random, 'NormalDist': NormalDist}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'survey_iq_helpers', 'exec'), self.env)
        self.pools = {task: list(range(82)) for task in ['working_memory', 'fluid', 'numerical']}
        self.env['iq_reference_scores'] = lambda: self.pools
        self.observed = []
        percentile_iq = self.env['_percentile_iq']

        def capture(sample, score):
            self.observed.append(list(sample))
            return percentile_iq(sample, score)

        self.env['_percentile_iq'] = capture

    def draw(self, code='participant-a', task='working_memory', score=40):
        self.observed.clear()
        player = SimpleNamespace(participant=SimpleNamespace(code=code))
        result = self.env['iq_noise_offset'](player, task, score)
        return result, self.observed[0] if self.observed else None

    def test_unique_observations_and_stable_independent_draws(self):
        self.assertEqual(self.env['IQ_COMPARISON_GROUP'], 20)
        for i in range(100):
            _, group = self.draw(code=f'participant-{i}')
            self.assertEqual(len(group), 20)
            self.assertEqual(len(set(group)), 20)
        first = self.draw()
        self.assertEqual(first, self.draw())
        self.assertNotEqual(first[1], self.draw(task='fluid')[1])
        self.assertNotEqual(first[1], self.draw(code='participant-b')[1])

    def test_tied_scores_are_retained_as_distinct_observations(self):
        self.pools['working_memory'] = [8] * 82
        offset, group = self.draw(score=8)
        self.assertEqual(group, [8] * 20)
        self.assertEqual(offset, 0)

    def test_full_pool_and_insufficient_pool(self):
        self.pools['working_memory'] = list(range(20))
        offset, group = self.draw(score=10)
        self.assertEqual(set(group), set(range(20)))
        self.assertEqual(offset, 0)
        self.pools['working_memory'] = list(range(19))
        self.assertEqual(self.draw(), (0, None))


if __name__ == '__main__':
    unittest.main()
