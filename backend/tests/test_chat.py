import pytest
from unittest.mock import Mock, patch, AsyncMock
from functions.chat import build_prompt, ChatService


def test_build_prompt_includes_sources():
    sources = [
        Mock(
            source_ref='Rule 4-6-1',
            content='Basket interference occurs when...',
            penalty_text='PENALTY: Two points awarded.'
        ),
        Mock(
            source_ref='4.6.1',
            content='SITUATION: Player slaps backboard...',
            penalty_text=None
        )
    ]

    prompt = build_prompt("What is basket interference?", sources)

    assert '[1]' in prompt
    assert '[2]' in prompt
    assert 'Rule 4-6-1' in prompt
    assert 'Basket interference' in prompt
    assert 'PENALTY' in prompt


def test_build_prompt_instructs_citations():
    sources = [Mock(source_ref='Rule 1-1-1', content='Test', penalty_text=None)]
    prompt = build_prompt("Test question", sources)

    assert 'cite' in prompt.lower() or '[1]' in prompt
