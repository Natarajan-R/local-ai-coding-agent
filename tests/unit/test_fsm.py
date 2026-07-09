import pytest

from agent.fsm import FSM, AgentState, InvalidTransition


def test_happy_path():
    fsm = FSM()
    assert fsm.state == AgentState.IDLE
    fsm.transition("start")
    assert fsm.state == AgentState.PLANNING
    fsm.transition("plan_ready")
    assert fsm.state == AgentState.EXECUTING
    fsm.transition("execution_done")
    assert fsm.state == AgentState.EVALUATING
    fsm.transition("passed")
    assert fsm.state == AgentState.DONE
    assert fsm.is_terminal()


def test_failure_and_retry():
    fsm = FSM()
    fsm.transition("start")
    fsm.transition("plan_ready")
    fsm.transition("execution_done")
    fsm.transition("failed")
    assert fsm.state == AgentState.REFLEXING
    fsm.transition("retry")
    assert fsm.state == AgentState.EXECUTING


def test_give_up_leads_to_error():
    fsm = FSM(AgentState.REFLEXING)
    fsm.transition("give_up")
    assert fsm.state == AgentState.ERROR
    assert fsm.is_terminal()


def test_invalid_transition_raises():
    fsm = FSM()
    with pytest.raises(InvalidTransition):
        fsm.transition("plan_ready")


def test_can_reports_validity():
    fsm = FSM()
    assert fsm.can("start")
    assert not fsm.can("passed")


def test_history_is_recorded():
    fsm = FSM()
    fsm.transition("start")
    assert len(fsm.history) == 1
    assert fsm.history[0].event == "start"
