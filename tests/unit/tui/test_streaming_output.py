#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for StreamingText widget and streaming output.

Tests cover:
- Streaming text rendering
- Thinking process display
- Large output performance
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import time
import asyncio


class TestStreamingTextBasics:
    """Test StreamingText basic functionality."""

    def test_streaming_text_creation(self):
        """Test creating a StreamingText instance."""
        from tui.widgets.streaming_text import StreamingText, TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        widget = StreamingText()
        
        assert widget.show_thinking is True
        assert widget.thinking_expanded is False
        assert widget.throttle_ms == 50
        assert widget.buffer_size == 100

    def test_streaming_text_custom_params(self):
        """Test creating StreamingText with custom parameters."""
        from tui.widgets.streaming_text import StreamingText, TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        widget = StreamingText(
            show_thinking=False,
            thinking_expanded=True,
            throttle_ms=100,
            buffer_size=200,
        )
        
        assert widget.show_thinking is False
        assert widget.thinking_expanded is True
        assert widget.throttle_ms == 100
        assert widget.buffer_size == 200

    def test_streaming_text_initial_state(self):
        """Test StreamingText initial state."""
        from tui.widgets.streaming_text import StreamingText, TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        widget = StreamingText()
        
        # Initial text should be empty
        assert widget.get_output() == ""
        assert widget.get_thinking() == ""
        assert widget.get_tool_output() == ""


class TestTextType:
    """Test TextType enum."""

    def test_text_type_values(self):
        """Test TextType enum values."""
        from tui.widgets.streaming_text import TextType
        
        assert TextType.OUTPUT.value == "output"
        assert TextType.THINKING.value == "thinking"
        assert TextType.TOOL.value == "tool"
        assert TextType.ERROR.value == "error"


class TestStreamingState:
    """Test StreamingState dataclass."""

    def test_streaming_state_defaults(self):
        """Test StreamingState default values."""
        from tui.widgets.streaming_text import StreamingState, TextType
        
        state = StreamingState()
        
        assert state.text == ""
        assert state.text_type == TextType.OUTPUT
        assert state.is_streaming is False
        assert state.start_time > 0
        assert state.last_update > 0

    def test_streaming_state_custom_values(self):
        """Test StreamingState with custom values."""
        from tui.widgets.streaming_text import StreamingState, TextType
        
        timestamp = time.time()
        state = StreamingState(
            text="Hello",
            text_type=TextType.THINKING,
            is_streaming=True,
            start_time=timestamp,
            last_update=timestamp,
        )
        
        assert state.text == "Hello"
        assert state.text_type == TextType.THINKING
        assert state.is_streaming is True


class TestStartStreaming:
    """Test starting streaming."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_start_streaming_output(self):
        """Test starting output streaming."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        widget.start_streaming(TextType.OUTPUT)
        
        assert widget._output_state.is_streaming is True
        assert widget._cache_dirty is True

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_start_streaming_with_initial_text(self):
        """Test starting streaming with initial text."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        widget.start_streaming(TextType.OUTPUT, "Initial text")
        
        assert widget._output_state.text == "Initial text"

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_start_streaming_with_string_type(self):
        """Test starting streaming with string type."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        widget.start_streaming("thinking")
        
        assert widget._thinking_state.is_streaming is True

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_start_streaming_posts_message(self):
        """Test that starting streaming posts a message."""
        from tui.widgets.streaming_text import StreamingText, TextType, StreamingStarted
        
        widget = StreamingText()
        
        with patch.object(widget, 'post_message') as mock_post:
            widget.start_streaming(TextType.OUTPUT)
            
            # Should post StreamingStarted message
            mock_post.assert_called_once()
            args = mock_post.call_args[0][0]
            assert isinstance(args, StreamingStarted)


class TestAppendText:
    """Test appending text."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_append_text_basic(self):
        """Test basic text append."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        widget.start_streaming(TextType.OUTPUT)
        
        widget.append_text("Hello")
        widget.append_text(" ")
        widget.append_text("World")
        
        # Text should be accumulated
        assert "Hello" in widget._output_state.text
        assert "World" in widget._output_state.text

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_append_text_thinking(self):
        """Test appending thinking text."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        widget.start_streaming(TextType.THINKING)
        
        widget.append_text("Let me think...")
        
        assert widget._thinking_state.text == "Let me think..."

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_append_without_start(self):
        """Test appending without starting streaming."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        # Should not raise but should log warning
        widget.append_text("Some text")

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_append_posts_update_message(self):
        """Test that appending posts update message."""
        from tui.widgets.streaming_text import StreamingText, TextType, StreamingUpdate
        
        widget = StreamingText(throttle_ms=0)  # Disable throttling
        widget.start_streaming(TextType.OUTPUT)
        
        with patch.object(widget, 'post_message') as mock_post:
            widget.append_text("Hello")
            
            # Should post StreamingUpdate message
            assert mock_post.called


class TestEndStreaming:
    """Test ending streaming."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_end_streaming_output(self):
        """Test ending output streaming."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        widget.start_streaming(TextType.OUTPUT, "Test text")
        
        result = widget.end_streaming(TextType.OUTPUT)
        
        assert result == "Test text"
        assert widget._output_state.is_streaming is False

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_end_streaming_flushes_buffer(self):
        """Test that ending streaming flushes remaining buffer."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        widget.start_streaming(TextType.OUTPUT, "Part1")
        
        # Add to buffer without triggering flush
        widget._output_buffer = "Part2"
        
        widget.end_streaming(TextType.OUTPUT)
        
        # Buffer should be flushed
        assert widget._output_buffer == ""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_end_streaming_posts_message(self):
        """Test that ending streaming posts message."""
        from tui.widgets.streaming_text import StreamingText, TextType, StreamingEnded
        
        widget = StreamingText()
        widget.start_streaming(TextType.OUTPUT)
        
        with patch.object(widget, 'post_message') as mock_post:
            widget.end_streaming(TextType.OUTPUT)
            
            # Should post StreamingEnded message
            args = mock_post.call_args[0][0]
            assert isinstance(args, StreamingEnded)


class TestCompleteStreaming:
    """Test complete streaming."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_complete_streaming(self):
        """Test completing all streaming."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget.start_streaming("output")
        widget.append_text("Output text")
        widget.start_streaming("thinking")
        widget.append_text("Thinking text")
        
        output, thinking = widget.complete_streaming()
        
        assert output == "Output text"
        assert thinking == "Thinking text"
        assert widget._output_state.is_streaming is False
        assert widget._thinking_state.is_streaming is False


class TestContentAccess:
    """Test content access methods."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_get_output(self):
        """Test getting output text."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget._output_state.text = "Test output"
        
        assert widget.get_output() == "Test output"

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_get_thinking(self):
        """Test getting thinking text."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget._thinking_state.text = "Test thinking"
        
        assert widget.get_thinking() == "Test thinking"

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_get_tool_output(self):
        """Test getting tool output."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget._tool_state.text = "Tool result"
        
        assert widget.get_tool_output() == "Tool result"

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_get_all_text(self):
        """Test getting all text."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget._output_state.text = "Output"
        widget._thinking_state.text = "Thinking"
        widget._tool_state.text = "Tool"
        
        all_text = widget.get_all_text()
        
        assert "Output" in all_text
        assert "Thinking" in all_text
        assert "Tool" in all_text


class TestClear:
    """Test clearing content."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_clear_all_text(self):
        """Test clearing all text."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget._output_state.text = "Output"
        widget._thinking_state.text = "Thinking"
        widget._tool_state.text = "Tool"
        widget._output_buffer = "Buffer"
        widget._thinking_buffer = "Buffer"
        
        widget.clear()
        
        assert widget._output_state.text == ""
        assert widget._thinking_state.text == ""
        assert widget._tool_state.text == ""
        assert widget._output_buffer == ""
        assert widget._thinking_buffer == ""


class TestThinkingToggle:
    """Test thinking content toggle."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_toggle_thinking(self):
        """Test toggling thinking expanded state."""
        from tui.widgets.streaming_text import StreamingText, ThinkingToggled
        
        widget = StreamingText()
        initial_state = widget.thinking_expanded
        
        with patch.object(widget, 'post_message') as mock_post:
            widget.toggle_thinking()
            
            assert widget.thinking_expanded == (not initial_state)
            
            args = mock_post.call_args[0][0]
            assert isinstance(args, ThinkingToggled)
            assert args.is_expanded == widget.thinking_expanded

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_set_show_thinking(self):
        """Test setting show thinking."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        
        widget.set_show_thinking(False)
        assert widget.show_thinking is False
        
        widget.set_show_thinking(True)
        assert widget.show_thinking is True


class TestCallback:
    """Test callback functionality."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_set_on_streaming_end(self):
        """Test setting streaming end callback."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        
        callback_called = []
        def callback(text_type, text):
            callback_called.append((text_type, text))
        
        widget.set_on_streaming_end(callback)
        
        assert widget._on_streaming_end is not None

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_callback_triggered_on_end(self):
        """Test that callback is triggered on streaming end."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        
        callback_results = []
        def callback(text_type, text):
            callback_results.append((text_type, text))
        
        widget._on_streaming_end = callback
        widget.start_streaming("output", "Test")
        widget.end_streaming("output")
        
        assert len(callback_results) == 1
        assert callback_results[0][0] == "output"


class TestRender:
    """Test rendering."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_render_empty(self):
        """Test rendering empty content."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        
        result = widget.render()
        
        assert result == ""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_render_with_output(self):
        """Test rendering with output."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget._output_state.text = "Hello"
        widget._cache_dirty = True
        
        result = widget.render()
        
        assert "Hello" in result

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_render_streaming_indicator(self):
        """Test rendering includes streaming indicator."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText()
        widget._output_state.text = "Loading"
        widget._output_state.is_streaming = True
        widget._cache_dirty = True
        
        result = widget.render()
        
        # Should include cursor indicator
        assert "▌" in result

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_render_thinking_hidden(self):
        """Test rendering with thinking hidden."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText(show_thinking=False)
        widget._thinking_state.text = "Hidden thinking"
        widget._cache_dirty = True
        
        result = widget.render()
        
        # Thinking should not be in rendered output
        assert "Hidden thinking" not in result


class TestLargeOutputPerformance:
    """Test performance with large output."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_large_text_append(self):
        """Test appending large amounts of text."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText(throttle_ms=0)  # Disable throttling for speed
        widget.start_streaming("output")
        
        # Append large text in chunks
        large_text = "x" * 10000
        chunk_size = 100
        
        for i in range(0, len(large_text), chunk_size):
            widget.append_text(large_text[i:i + chunk_size])
        
        # All text should be accumulated
        assert len(widget._output_state.text) == 10000

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_many_small_appends(self):
        """Test many small text appends."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText(throttle_ms=0)
        widget.start_streaming("output")
        
        # Many single character appends
        for _ in range(1000):
            widget.append_text("a")
        
        # Text should be accumulated
        assert len(widget._output_state.text) == 1000

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_multiple_streaming_types(self):
        """Test multiple streaming types simultaneously."""
        from tui.widgets.streaming_text import StreamingText
        
        widget = StreamingText(throttle_ms=0)
        widget.start_streaming("output")
        widget.start_streaming("thinking")
        widget.start_streaming("tool")
        
        widget.append_text("Output", "output")
        widget.append_text("Thinking", "thinking")
        widget.append_text("Tool", "tool")
        
        assert widget._output_state.text == "Output"
        assert widget._thinking_state.text == "Thinking"
        assert widget._tool_state.text == "Tool"


class TestCreateStreamingText:
    """Test create_streaming_text convenience function."""

    def test_create_streaming_text_default(self):
        """Test create_streaming_text with defaults."""
        from tui.widgets.streaming_text import create_streaming_text, TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        widget = create_streaming_text()
        
        assert widget.show_thinking is True
        assert widget.thinking_expanded is False

    def test_create_streaming_text_custom(self):
        """Test create_streaming_text with custom params."""
        from tui.widgets.streaming_text import create_streaming_text, TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        widget = create_streaming_text(
            show_thinking=False,
            thinking_expanded=True,
        )
        
        assert widget.show_thinking is False
        assert widget.thinking_expanded is True


class TestStreamingEvents:
    """Test streaming events."""

    def test_streaming_started_event(self):
        """Test StreamingStarted event initialization."""
        from tui.widgets.streaming_text import StreamingStarted, TextType, Widget
        
        sender = Widget()
        event = StreamingStarted(sender, TextType.OUTPUT)
        
        assert event.text_type == TextType.OUTPUT

    def test_streaming_update_event(self):
        """Test StreamingUpdate event initialization."""
        from tui.widgets.streaming_text import StreamingUpdate, Widget
        
        sender = Widget()
        event = StreamingUpdate(sender, "full text", "delta")
        
        assert event.text == "full text"
        assert event.delta == "delta"

    def test_streaming_ended_event(self):
        """Test StreamingEnded event initialization."""
        from tui.widgets.streaming_text import StreamingEnded, TextType, Widget
        
        sender = Widget()
        event = StreamingEnded(sender, "final text", TextType.OUTPUT, 1.5)
        
        assert event.text == "final text"
        assert event.text_type == TextType.OUTPUT
        assert event.duration == 1.5

    def test_thinking_toggled_event(self):
        """Test ThinkingToggled event initialization."""
        from tui.widgets.streaming_text import ThinkingToggled, Widget
        
        sender = Widget()
        event = ThinkingToggled(sender, True)
        
        assert event.is_expanded is True


class TestColorConstants:
    """Test color constants."""

    def test_color_constants_exist(self):
        """Test that all color constants are defined."""
        from tui.widgets.streaming_text import (
            AVOCADO_PRIMARY,
            AVOCADO_BRIGHT,
            AVOCADO_DIM,
            AVOCADO_DARK,
            COLOR_SUCCESS,
            COLOR_WARNING,
            COLOR_DANGER,
            COLOR_INFO,
            WHITE,
            GRAY_DIM,
            GRAY_LIGHT,
            SURFACE,
        )
        
        assert isinstance(AVOCADO_PRIMARY, str)
        assert isinstance(COLOR_SUCCESS, str)
        assert isinstance(WHITE, str)


class TestInternalMethods:
    """Test internal helper methods."""

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_str_to_text_type(self):
        """Test string to TextType conversion."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        assert widget._str_to_text_type("output") == TextType.OUTPUT
        assert widget._str_to_text_type("thinking") == TextType.THINKING
        assert widget._str_to_text_type("think") == TextType.THINKING
        assert widget._str_to_text_type("tool") == TextType.TOOL
        assert widget._str_to_text_type("error") == TextType.ERROR
        assert widget._str_to_text_type("unknown") == TextType.OUTPUT

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_get_state(self):
        """Test getting state by text type."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        assert widget._get_state(TextType.OUTPUT) == widget._output_state
        assert widget._get_state(TextType.THINKING) == widget._thinking_state
        assert widget._get_state(TextType.TOOL) == widget._tool_state

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_get_buffer(self):
        """Test getting buffer by text type."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        assert widget._get_buffer(TextType.OUTPUT) == widget._output_buffer
        assert widget._get_buffer(TextType.THINKING) == widget._thinking_buffer

    @patch('tui.widgets.streaming_text.TEXTUAL_AVAILABLE', True)
    def test_set_buffer(self):
        """Test setting buffer by text type."""
        from tui.widgets.streaming_text import StreamingText, TextType
        
        widget = StreamingText()
        
        widget._set_buffer(TextType.OUTPUT, "test")
        assert widget._output_buffer == "test"
        
        widget._set_buffer(TextType.THINKING, "test2")
        assert widget._thinking_buffer == "test2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
