#!/usr/bin/env python3
"""Fail-closed tests for trusted approval of generated state-sync PR checks."""
import copy
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import approve_bot_pr_run as gate

REPO = "arcticlore/candy-rpm"
SHA = "a" * 40
BRANCH = "bot/state-sync-44729473016-1"


def event():
    return {
        "action": "opened",
        "number": 81,
        "pull_request": {
            "number": 81,
            "user": {"login": "github-actions[bot]", "type": "Bot"},
            "base": {"ref": "master", "repo": {"full_name": REPO}},
            "head": {"ref": BRANCH, "sha": SHA, "repo": {"full_name": REPO}},
        },
    }


def workflow_event():
    return {
        "workflow_run": {
            **run(),
            "head_branch": BRANCH,
            "pull_requests": [{"number": 81}],
        }
    }


def run(*, status="completed", conclusion="action_required", sha=SHA,
        actor="github-actions[bot]", actor_type="Bot"):
    return {
        "id": 44728141222,
        "event": "pull_request",
        "status": status,
        "conclusion": conclusion,
        "head_sha": sha,
        "path": ".github/workflows/validate.yml",
        "actor": {"login": actor, "type": actor_type},
    }


class API:
    def __init__(self, files=None, runs=None):
        self.pr = event()["pull_request"]
        self.files = files or [
            {"filename": "state/state.json", "status": "modified"},
            {"filename": "SPECS/dua.spec", "status": "modified"},
        ]
        self.runs = runs if runs is not None else [run()]
        self.posts = []

    def get(self, path):
        if path.endswith("/pulls/81"):
            return self.pr
        if "/pulls/81/files" in path:
            return self.files
        if "/actions/workflows/validate.yml/runs?" in path:
            return {"workflow_runs": self.runs}
        raise AssertionError(path)

    def post(self, path):
        self.posts.append(path)
        return None


def test_approves_only_exact_bounded_action_required_run():
    api = API(runs=[run(sha="b" * 40), run()])
    message = gate.approve(event(), repo=REPO, api=api, timeout=0)
    assert api.posts == [f"/repos/{REPO}/actions/runs/44728141222/approve"]
    assert "approved bounded bot validation" in message


def test_workflow_run_normalizes_to_the_same_exact_pr_gate():
    api = API()
    message = gate.approve(workflow_event(), repo=REPO, api=api, timeout=0)
    assert api.posts == [f"/repos/{REPO}/actions/runs/44728141222/approve"]
    assert "approved bounded bot validation" in message


def test_workflow_run_head_mismatch_fails_closed():
    api = API()
    api.pr = copy.deepcopy(api.pr)
    api.pr["head"]["sha"] = "b" * 40
    with pytest.raises(gate.ApprovalError):
        gate.approve(workflow_event(), repo=REPO, api=api, timeout=0)
    assert api.posts == []


@pytest.mark.parametrize("mutate", [
    lambda e: e["pull_request"]["user"].update(login="attacker"),
    lambda e: e["pull_request"]["user"].update(type="User"),
    lambda e: e["pull_request"]["head"]["repo"].update(full_name="fork/repo"),
    lambda e: e["pull_request"]["head"].update(ref="feature/looks-like-state-sync"),
    lambda e: e["pull_request"]["base"].update(ref="unprotected"),
    lambda e: e.update(action="edited"),
])
def test_event_identity_and_shape_fail_closed(mutate):
    payload = copy.deepcopy(event())
    mutate(payload)
    with pytest.raises(gate.ApprovalError):
        gate.validate_event(payload, REPO)


@pytest.mark.parametrize("files", [
    [{"filename": "state/state.json", "status": "modified"}],
    [
        {"filename": "state/state.json", "status": "modified"},
        {"filename": ".github/workflows/validate.yml", "status": "modified"},
    ],
    [
        {"filename": "state/state.json", "status": "modified"},
        {"filename": "SPECS/new.spec", "status": "added"},
    ],
    [
        {"filename": "SPECS/dua.spec", "status": "modified"},
        {"filename": "SPECS/nb.spec", "status": "modified"},
    ],
])
def test_file_scope_fails_closed(files):
    with pytest.raises(gate.ApprovalError):
        gate.validate_files(files)


def test_active_exact_run_needs_no_approval_even_after_trusted_maintainer_push():
    api = API(runs=[run(status="in_progress", conclusion=None,
                        actor="arcticlore", actor_type="User")])
    message = gate.approve(event(), repo=REPO, api=api, timeout=0)
    assert api.posts == []
    assert "already active" in message


def test_wrong_workflow_or_action_required_actor_cannot_be_approved():
    bad_path = run()
    bad_path["path"] = ".github/workflows/evil.yml"
    with pytest.raises(gate.ApprovalError):
        gate.select_exact_run([bad_path], SHA)
    api = API(runs=[run(actor="someone", actor_type="User")])
    with pytest.raises(gate.ApprovalError):
        gate.approve(event(), repo=REPO, api=api, timeout=0)
    assert api.posts == []


def test_workflow_is_privileged_but_never_checks_out_pr_head():
    text = open(os.path.join(ROOT, ".github/workflows/approve-bot-pr.yml")).read()
    assert "pull_request_target:" in text
    assert "workflow_run:" in text
    assert 'workflows: ["validate (required PR/push CI)"]' in text
    assert "ref: master" in text
    assert "persist-credentials: false" in text
    assert "actions: write" in text
    assert "pull-requests: read" in text
    assert "pull_request.head.sha" not in text.split("steps:", 1)[1]
