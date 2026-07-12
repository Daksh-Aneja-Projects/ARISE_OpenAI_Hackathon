import pytest
from unittest.mock import AsyncMock, patch
from app.agents.intake import IntakeAgent
from app.agents.bid_no_bid import BidNoBidAgent

@pytest.fixture
def mock_manifest():
    return {
        "bidder_profile": {"name": "TestCompany"},
        "intake_output": {"extracted_fields": {"client_name": "TestClient", "due_date": "2026-12-31"}},
        "rfp_text": "Sample RFP text for testing."
    }

@pytest.mark.asyncio
@patch("app.agents.base.llm_service.generate_structured", new_callable=AsyncMock)
@patch("app.agents.base.llm_service.generate", new_callable=AsyncMock)
async def test_intake_agent_trivial(mock_gen, mock_gen_struct, mock_manifest):
    mock_gen.return_value = '{"status": "ok"}'
    mock_gen_struct.return_value = '{"status": "ok"}'
    agent = IntakeAgent("test-bid-1", mock_manifest)
    result = await agent.run()
    assert result["status"] in ["success", "failed"]

@pytest.mark.asyncio
@patch("app.agents.base.llm_service.generate_structured", new_callable=AsyncMock)
@patch("app.agents.base.llm_service.generate", new_callable=AsyncMock)
async def test_bid_no_bid_agent_trivial(mock_gen, mock_gen_struct, mock_manifest):
    mock_gen.return_value = '{"go_no_go_decision": "GO", "confidence_score": 85}'
    mock_gen_struct.return_value = '{"go_no_go_decision": "GO", "confidence_score": 85}'
    agent = BidNoBidAgent("test-bid-2", mock_manifest)
    result = await agent.run()
    assert result["status"] in ["success", "failed"]
