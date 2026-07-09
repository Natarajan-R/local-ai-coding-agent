import asyncio

from agent.orchestrator import Orchestrator


def test_host_and_audit_dir_are_wired(workspace, tmp_path):
    audit_dir = tmp_path / "aud"
    orch = Orchestrator(
        workspace=workspace,
        host="http://example:1234",
        sandbox_backend="local",
        log_dir=audit_dir,
    )
    try:
        assert orch.model.host == "http://example:1234"
        assert orch.policy.audit.path == audit_dir / "audit.jsonl"
        # Run id is a short correlation handle stamped on the audit context.
        assert orch.policy.audit.context["run_id"] == orch.run_id
    finally:
        asyncio.run(orch.model.close())
