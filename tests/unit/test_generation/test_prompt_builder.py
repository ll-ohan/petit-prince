"""Tests for PromptBuilder."""

import pytest

from src.core.interfaces.reranker import RankedDocument
from src.generation.prompt_builder import PromptBuilder


class TestPromptBuilder:
    """Test prompt construction."""

    def test_all_documents_relevant_system_prompt(self):
        """All docs above threshold use 'hautement pertinents' system prompt."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="High relevance text 1", score=0.9, original_rank=0),
            RankedDocument(text="High relevance text 2", score=0.85, original_rank=1),
        ]
        conversation = [{"role": "user", "content": "Qui est le renard?"}]

        messages = builder.build(conversation, docs, threshold=0.7)

        system = messages[0]["content"]
        assert "hautement pertinent" in system.lower() or "tous" in system.lower()

    def test_partial_relevance_system_prompt(self):
        """Mixed scores use 'pertinence variables' system prompt."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="High relevance", score=0.9, original_rank=0),
            RankedDocument(text="Low relevance", score=0.5, original_rank=1),
        ]
        conversation = [{"role": "user", "content": "Question?"}]

        messages = builder.build(conversation, docs, threshold=0.7)

        system = messages[0]["content"]
        assert "variable" in system.lower() or "haute" in system

    def test_no_relevant_documents_system_prompt(self):
        """All docs below threshold use 'pertinence limitée' system prompt."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="Low relevance 1", score=0.3, original_rank=0),
            RankedDocument(text="Low relevance 2", score=0.2, original_rank=1),
        ]
        conversation = [{"role": "user", "content": "Question?"}]

        messages = builder.build(conversation, docs, threshold=0.7)

        system = messages[0]["content"]
        assert "limitée" in system.lower() or "connaissance générale" in system.lower()

    def test_all_documents_always_in_context(self):
        """ALL documents appear in context regardless of score."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="High relevance text", score=0.9, original_rank=0),
            RankedDocument(text="Low relevance text", score=0.3, original_rank=1),
        ]
        conversation = [{"role": "user", "content": "Question?"}]

        messages = builder.build(conversation, docs, threshold=0.7)

        last_user_msg = messages[-1]["content"]
        assert "High relevance text" in last_user_msg
        assert "Low relevance text" in last_user_msg

    def test_relevance_tags_in_context(self):
        """Documents are tagged [HAUTE] or [MODÉRÉE] based on threshold."""
        builder = PromptBuilder()
        docs = [
            RankedDocument(text="Above threshold", score=0.8, original_rank=0),
            RankedDocument(text="Below threshold", score=0.5, original_rank=1),
        ]
        conversation = [{"role": "user", "content": "Question?"}]

        messages = builder.build(conversation, docs, threshold=0.7)

        last_user_msg = messages[-1]["content"]
        assert "[PERTINENCE: HAUTE]" in last_user_msg
        assert "[PERTINENCE: MODÉRÉE]" in last_user_msg

    def test_conversation_history_preserved(self):
        """Full conversation history appears before augmented user message."""
        builder = PromptBuilder()
        conversation = [
            {"role": "user", "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour !"},
            {"role": "user", "content": "Qui est le renard?"},
        ]
        docs = [RankedDocument(text="Le renard...", score=0.9, original_rank=0)]

        messages = builder.build(conversation, docs, threshold=0.7)

        assert messages[1]["content"] == "Bonjour"
        assert messages[2]["content"] == "Bonjour !"
        assert "Qui est le renard?" in messages[3]["content"]
        assert "EXTRAITS DU PETIT PRINCE" in messages[3]["content"]

    def test_original_query_before_context(self):
        """Original query appears before the context block."""
        builder = PromptBuilder()
        conversation = [{"role": "user", "content": "Ma question originale"}]
        docs = [RankedDocument(text="Extrait", score=0.9, original_rank=0)]

        messages = builder.build(conversation, docs, threshold=0.7)

        last_msg = messages[-1]["content"]
        query_pos = last_msg.index("Ma question originale")
        context_pos = last_msg.index("EXTRAITS DU PETIT PRINCE")
        assert query_pos < context_pos

    @pytest.mark.edge_case
    def test_empty_documents_list(self):
        """Empty doc list uses no-context prompt variant."""
        builder = PromptBuilder()
        conversation = [{"role": "user", "content": "Question?"}]

        messages = builder.build(conversation, [], threshold=0.7)

        system = messages[0]["content"]
        assert "limitée" in system.lower() or "connaissance générale" in system.lower()

    def test_system_prompt_contains_required_sections(self):
        """System prompt includes RÔLE, SOURCES, CONTRAINTES sections."""
        builder = PromptBuilder()
        docs = [RankedDocument(text="...", score=0.9, original_rank=0)]
        conversation = [{"role": "user", "content": "Question?"}]

        messages = builder.build(conversation, docs, threshold=0.7)

        system = messages[0]["content"]
        assert "RÔLE" in system or "rôle" in system.lower()
        assert "SOURCES" in system or "sources" in system.lower()
        assert "CONTRAINTES" in system or "contraintes" in system.lower()
        assert "TON" in system.upper() or "STYLE" in system.upper()
