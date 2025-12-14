"""Unit tests for PromptBuilder."""

import pytest

from src.core.interfaces.reranker import RankedDocument
from src.generation.prompt_builder import (
    SYSTEM_PROMPT_ALL_RELEVANT,
    SYSTEM_PROMPT_LOW_RELEVANCE,
    SYSTEM_PROMPT_PARTIAL,
    PromptBuilder,
)


@pytest.mark.unit
class TestPromptBuilder:

    def test_build_system_prompt_all_relevant(self):
        """Test system prompt selection when all docs are relevant."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="A", score=0.9, original_rank=0),
            RankedDocument(text="B", score=0.8, original_rank=1),
        ]

        msgs = builder.build(
            conversation=[{"role": "user", "content": "Hi"}],
            documents=docs,
            threshold=0.7,
        )

        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == SYSTEM_PROMPT_ALL_RELEVANT

    def test_build_system_prompt_mixed_relevance(self):
        """Test system prompt when some docs are relevant and others not."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="A", score=0.8, original_rank=0),  # > 0.7
            RankedDocument(text="B", score=0.4, original_rank=1),  # < 0.7
        ]

        msgs = builder.build(
            conversation=[{"role": "user", "content": "Hi"}],
            documents=docs,
            threshold=0.7,
        )

        assert msgs[0]["content"] == SYSTEM_PROMPT_PARTIAL

    def test_build_system_prompt_low_relevance(self):
        """Test system prompt selection when no docs are relevant."""
        builder = PromptBuilder()
        docs = [RankedDocument(text="A", score=0.1, original_rank=0)]

        msgs = builder.build(
            conversation=[{"role": "user", "content": "Hi"}],
            documents=docs,
            threshold=0.7,
        )

        assert msgs[0]["content"] == SYSTEM_PROMPT_LOW_RELEVANCE

    def test_build_prompt_no_documents(self):
        """Test builder behavior with empty document list."""
        builder = PromptBuilder()
        msgs = builder.build(
            conversation=[{"role": "user", "content": "Hi"}],
            documents=[],
            threshold=0.7,
        )

        assert msgs[0]["content"] == SYSTEM_PROMPT_LOW_RELEVANCE
        assert "Hi" in msgs[-1]["content"]

    def test_build_prompt_history_preservation(self):
        """Test that conversation history is preserved."""
        builder = PromptBuilder()
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
        ]

        msgs = builder.build(conversation=history, documents=[], threshold=0.5)

        # System + Q1 + A1 + Augmented Q2 = 4 messages
        assert len(msgs) == 4
        assert msgs[1]["content"] == "Q1"
        assert msgs[2]["content"] == "A1"
        assert "Q2" in msgs[3]["content"]

    def test_context_injection_format(self):
        """Test that documents are injected into user message with tags."""
        builder = PromptBuilder()
        docs = [RankedDocument(text="Contenu secret", score=0.9, original_rank=0)]

        msgs = builder.build(
            conversation=[{"role": "user", "content": "Question"}],
            documents=docs,
            threshold=0.5,
        )

        last_msg = msgs[-1]["content"]
        assert "Question" in last_msg
        assert "EXTRAITS DU PETIT PRINCE" in last_msg
        assert "[PERTINENCE: HAUTE]" in last_msg
        assert "Contenu secret" in last_msg
