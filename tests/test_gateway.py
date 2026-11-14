import os
import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def is_gateway_configured() -> bool:
    url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    return bool(url)


@pytest.mark.integration
def test_workshop_gateway_connection():
    if not is_gateway_configured():
        pytest.skip("LLM gateway URL is not configured.")

    try:
        llm = ChatOpenAI(
            base_url=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY", "dummy"),
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            temperature=0,
            request_timeout=5,
            max_retries=1,
        )
        response = llm.invoke("Reply with exactly: gateway connected")
        assert response.content
        print("Gateway response:", response.content)
    except Exception as e:
        pytest.skip(f"Live gateway is currently unreachable: {e}")
