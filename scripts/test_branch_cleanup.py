"""Exercise destructive-workflow boundaries without any Git or network writes."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

WORKFLOW = Path(__file__).resolve().parent.parent / '.github/workflows/cleanup-merged-branch.yml'
SOURCE = '\n'.join(line[10:] for line in WORKFLOW.read_text().split('        run: |\n', 1)[1].splitlines())
SHA = 'a' * 40
BASE = {'repository': {'default_branch': 'main'}, 'pull_request': {'merged': True, 'base': {'ref': 'main'}, 'head': {'ref': 'docs/task', 'sha': SHA, 'repo': {'full_name': 'denius89/polymarket-copy-trading'}}}}

class CleanupBoundaries(unittest.TestCase):
    def exercise(self, event, remote=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'event.json').write_text(json.dumps(event))
            env = {'GITHUB_EVENT_PATH': str(path / 'event.json'), 'GITHUB_REPOSITORY': 'denius89/polymarket-copy-trading', 'GITHUB_STEP_SUMMARY': str(path / 'summary.md'), 'CLEANUP_TOKEN': 'test-token'}
            with patch.dict(os.environ, env), patch('subprocess.run') as run, patch('subprocess.check_output', return_value=remote or SHA + '\trefs/heads/docs/task\n') as read:
                try:
                    exec(compile(SOURCE, str(WORKFLOW), 'exec'), {})
                except SystemExit as error:
                    self.assertEqual(error.code, 0)
                return run.call_args_list, read.call_args_list

    def test_eligible_branch_uses_exact_lease_and_only_one_delete(self):
        writes, reads = self.exercise(copy.deepcopy(BASE))
        self.assertEqual(len(reads), 1)
        self.assertEqual(len(writes), 2)  # empty temporary repository + one guarded push
        command = writes[-1].args[0]
        self.assertIn('--force-with-lease=refs/heads/docs/task:' + SHA, command)
        self.assertEqual(command[-1], ':refs/heads/docs/task')
        self.assertNotIn(':refs/heads/main', command)
        self.assertNotIn('shell', writes[-1].kwargs)

    def test_main_and_base_are_never_deleted(self):
        for branch, base in [('main', 'other'), ('docs/task', 'docs/task')]:
            event = copy.deepcopy(BASE); event['pull_request']['head']['ref'] = branch; event['pull_request']['base']['ref'] = base
            writes, reads = self.exercise(event); self.assertEqual((writes, reads), ([], []))

    def test_fork_or_unmerged_pr_does_not_touch_git(self):
        fork = copy.deepcopy(BASE); fork['pull_request']['head']['repo']['full_name'] = 'someone/fork'
        unmerged = copy.deepcopy(BASE); unmerged['pull_request']['merged'] = False
        for event in [fork, unmerged]:
            writes, reads = self.exercise(event); self.assertEqual((writes, reads), ([], []))

    def test_advanced_head_is_preserved(self):
        writes, reads = self.exercise(copy.deepcopy(BASE), 'b' * 40 + '\trefs/heads/docs/task\n')
        self.assertEqual(writes, []); self.assertEqual(len(reads), 1)

    def test_non_task_branch_is_preserved(self):
        event = copy.deepcopy(BASE); event['pull_request']['head']['ref'] = 'release/stable'
        writes, reads = self.exercise(event); self.assertEqual((writes, reads), ([], []))

if __name__ == '__main__':
    unittest.main()
