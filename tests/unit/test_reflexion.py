import pytest
from unittest.mock import AsyncMock
from agent.evaluation.reflexion import ReflexionEngine
from agent.evaluation.evaluator import EvalResult
from agent.perception.indexer import WorkspaceIndexer


def test_reflexion_no_indexer():
    model = AsyncMock()
    evaluator = AsyncMock()
    sandbox = AsyncMock()
    policy = AsyncMock()
    
    chat_response = AsyncMock()
    chat_response.content = "Diagnosed issue: test failed because x != y."
    chat_fn = AsyncMock(return_value=chat_response)
    
    engine = ReflexionEngine(model, evaluator, sandbox, policy, chat_fn=chat_fn)
    
    eval_result = EvalResult(passed=False, ran_tests=True, summary="Failed tests", details="Expected x but got y")
    
    import asyncio
    lesson = asyncio.run(engine.reflect("Add parameter", eval_result))
    
    assert lesson == "Diagnosed issue: test failed because x != y."
    args, kwargs = chat_fn.call_args
    messages = args[0]
    assert any("Add parameter" in m["content"] for m in messages)
    assert any("Expected x but got y" in m["content"] for m in messages)
    # Check that symbol structure is NOT present when indexer is not passed
    prompt_content = messages[1]["content"]
    assert "actual symbol structure" not in prompt_content


def test_reflexion_with_indexer(workspace):
    # Setup some dummy files in the workspace
    (workspace / "models.py").write_text("class OrderItem:\n    def __init__(self):\n        pass\n")
    (workspace / "cart.py").write_text("from models import OrderItem\n")
    
    indexer = WorkspaceIndexer(workspace)
    
    model = AsyncMock()
    evaluator = AsyncMock()
    sandbox = AsyncMock()
    policy = AsyncMock()
    
    chat_response = AsyncMock()
    chat_response.content = "Diagnosed issue."
    chat_fn = AsyncMock(return_value=chat_response)
    
    engine = ReflexionEngine(model, evaluator, sandbox, policy, indexer=indexer, chat_fn=chat_fn)
    
    eval_result = EvalResult(passed=False, ran_tests=True, summary="Failed tests", details="Expected cart changes")
    
    import asyncio
    lesson = asyncio.run(engine.reflect("Add parameter", eval_result))
    
    assert lesson == "Diagnosed issue."
    args, kwargs = chat_fn.call_args
    messages = args[0]
    prompt_content = messages[1]["content"]
    
    # Verify symbol structure is formatted and injected into prompt
    assert "actual symbol structure" in prompt_content
    assert "models.py" in prompt_content
    assert "class `OrderItem`" in prompt_content
    assert "cart.py" in prompt_content
    assert "`models`" in prompt_content or "`models.OrderItem`" in prompt_content
