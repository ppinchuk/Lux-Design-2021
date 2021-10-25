import pytest
from kaggle_environments import make
from agent import agent
from simple_agent import agent as simple_agent
import subprocess
import sys
import os
import getpass
import json

"""
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'rp 0 0' <- research points (player id, num)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'rp 1 0'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'r coal 0 3 419' <- resource (type, x, y, amount)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'r wood 0 9 314'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'r uranium 6 10 331'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'u 0 0 u_1 13 7 0 0 0 0'    <- unit (type, team, id, x, y, cooldown, wood, coal, uranium)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'u 0 1 u_2 13 16 0 0 0 0'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'c 0 c_1 0 23'  <- city (team, id, fuel, lightupkeep)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'c 1 c_2 0 23'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ct 0 c_1 13 7 0'   <- citytile (team, id, x, y, cooldown)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ct 1 c_2 13 16 0'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ccd 13 7 6'   <- road (x, y, level)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ccd 13 16 6'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'D_DONE'
"""

class TestNoRandomness:

    @pytest.mark.skip(reason="takes too long")
    @pytest.mark.skipif(getpass.getuser() != 'Paul', reason="requires Paul's computer for non-randomness")
    @pytest.mark.parametrize("seed", [
        183985976,
        # 69420, 562124210, 812865753, 759738969, 94876192
    ])
    def test_no_randomness_using_file(self, reset_agent_state, seed):

        for ind in range(3):
            try:
                subprocess.run(
                    ['lux-ai-2021', f'--seed={seed}', 'dev\\main.py', 'simple\\main.py']
                    + [f'--out=C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\debug\\replay_{ind}-{seed}.json'],
                    cwd='C:\\Users\\Paul\\PycharmProjects\\Lux-Design-2021\\kits\\python',
                    shell=True
                )

            except subprocess.CalledProcessError as err:
                print(
                    'Failed to run algos',
                    file=sys.stderr
                )
                raise err

        with open(f'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\debug\\replay_0-{seed}.json') as fh:
            data0 = json.load(fh)

        with open(f'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\debug\\replay_1-{seed}.json') as fh:
            data1 = json.load(fh)

        with open(f'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\debug\\replay_2-{seed}.json') as fh:
            data2 = json.load(fh)

        for ind, (l1, l2) in enumerate(zip(data0['allCommands'], data1['allCommands'])):
            for d in l1:
                assert any(d == x for x in l2), f"Turn {ind}, seed {seed}, {d} not in {l2}. First list: {l1}"

        for ind, (l1, l2) in enumerate(zip(data0['allCommands'], data2['allCommands'])):
            for d in l1:
                assert any(d == x for x in l2), f"Turn {ind}, seed {seed}, {d} not in {l2}. First list: {l1}"

        for ind, (l1, l2) in enumerate(zip(data1['allCommands'], data2['allCommands'])):
            for d in l1:
                assert any(d == x for x in l2), f"Turn {ind}, seed {seed}, {d} not in {l2}. First list: {l1}"

        os.remove(f'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\debug\\replay_0-{seed}.json')
        os.remove(f'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\debug\\replay_1-{seed}.json')
        os.remove(f'C:\\Users\\Paul\\OneDrive\\LuxAIReplays\\debug\\replay_2-{seed}.json')

    @pytest.mark.skip(reason="takes too long")
    @pytest.mark.parametrize("seed, min_score", [
        (69420, 20),  # could be as high as 26
        # (183985976, 10),
    ])
    def test_min_city_tiles(self, reset_agent_state, seed, min_score):

        conf = {
            "loglevel": 2,
            "annotations": True
        }

        if seed is not None:
            conf['seed'] = seed

        reset_agent_state()
        env = make("lux_ai_2021", configuration=conf, debug=True)
        out = env.run([agent, simple_agent])

        assert sum('ct 0' in x for x in out[-1][0]['observation']['updates']) >= min_score
        # for x in out[-1][0]['observation']['updates']:
        #     if 'ct 0' in x:
        #         print(x)

    @pytest.mark.skip(reason="does not test for randomness from CLI")
    def test_no_randomness(self, reset_agent_state):
        seed = 69420  # 562124210 # 812865753 # 759738969 # 94876192 # None

        conf = {
            "loglevel": 2,
            "annotations": True
        }

        if seed is not None:
            conf['seed'] = seed

        ground_truth_actions = []

        reset_agent_state()
        env = make("lux_ai_2021", configuration=conf, debug=True)
        step_info, __ = env.reset(2)
        while step_info['status'] != 'DONE':
            actions_1 = agent(step_info['observation'], None, include_debug_for_vis=False)
            ground_truth_actions.append(actions_1)
            step_info['observation'].player = step_info['observation']['player'] = 1
            actions_2 = simple_agent(step_info['observation'], None)
            step_info, __ = env.step([actions_1, actions_2])

        for __ in range(5):
            reset_agent_state()
            env = make("lux_ai_2021", configuration=conf, debug=True)
            step_info, __ = env.reset(2)
            ind = 0
            while step_info['status'] != 'DONE':
                actions_1 = agent(step_info['observation'], None, include_debug_for_vis=False)
                assert set(ground_truth_actions[ind]) == set(actions_1)
                step_info['observation'].player = step_info['observation']['player'] = 1
                actions_2 = simple_agent(step_info['observation'], None)
                step_info, __ = env.step([actions_1, actions_2])
                ind += 1




