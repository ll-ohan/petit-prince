"""Unit tests for PromptBuilder."""

import pytest
from src.generation.prompt_builder import (
    PromptBuilder, 
    SYSTEM_PROMPT_ALL_RELEVANT, 
    SYSTEM_PROMPT_LOW_RELEVANCE
)
from src.core.interfaces.reranker import RankedDocument

@pytest.mark.unit
class TestPromptBuilder:
    
    def test_build_system_prompt_all_relevant(self):
        """Test system prompt selection when all docs are relevant."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="A", score=0.9, original_rank=0),
            RankedDocument(text="B", score=0.8, original_rank=1)
        ]
        
        msgs = builder.build(
            conversation=[{"role": "user", "content": "Hi"}],
            documents=docs,
            threshold=0.7
        )
        
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == SYSTEM_PROMPT_ALL_RELEVANT

    def test_build_system_prompt_low_relevance(self):
        """Test system prompt selection when no docs are relevant."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="A", score=0.1, original_rank=0)
        ]
        
        msgs = builder.build(
            conversation=[{"role": "user", "content": "Hi"}],
            documents=docs,
            threshold=0.7
        )
        
        assert msgs[0]["content"] == SYSTEM_PROMPT_LOW_RELEVANCE

    def test_context_injection_format(self):
        """Test that documents are injected into user message with tags."""
        builder = PromptBuilder()
        docs = [RankedDocument(text="Contenu secret", score=0.9, original_rank=0)]
        
        msgs = builder.build(
            conversation=[{"role": "user", "content": "Question"}],
            documents=docs,
            threshold=0.5
        )
        
        last_msg = msgs[-1]["content"]
        assert "Question" in last_msg
        assert "EXTRAITS DU PETIT PRINCE" in last_msg
        assert "[PERTINENCE: HAUTE]" in last_msg
        assert "Contenu secret" in last_msg