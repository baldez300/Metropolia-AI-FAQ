"""
Unit tests for the FAQ Assistant Flask application.

Run tests with: pytest tests/test_app.py -v
Or with coverage: pytest tests/test_app.py --cov=app
"""

import pytest
import json
import sys
import os

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock OpenAI before importing app to avoid needing a real API key during tests
from unittest.mock import patch, MagicMock

# Set a dummy API key for testing
os.environ['OPENAI_API_KEY'] = 'test-key-123'

from app import app, TEXT_MAX_LENGTH, QUESTION_MAX_LENGTH


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_openai():
    """Mock the OpenAI client to avoid real API calls."""
    with patch('app.client') as mock:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a mocked answer."
        mock.chat.completions.create.return_value = mock_response
        yield mock


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check(self, client):
        """Should return ok status."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'


class TestIndexRoute:
    """Tests for the / (index) endpoint."""

    def test_index_returns_html(self, client):
        """Should return the HTML page."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Metropolia Course FAQ Assistant' in response.data


class TestAskEndpoint:
    """Tests for the /ask endpoint (main functionality)."""

    def test_ask_with_valid_inputs(self, client, mock_openai):
        """Should successfully process valid text and question."""
        response = client.post('/ask', json={
            'text': 'This is a detailed lecture about machine learning basics and neural networks.',
            'question': 'What is machine learning?'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data
        assert data['answer'] == 'This is a mocked answer.'

    def test_ask_without_text(self, client):
        """Should return error when text is missing."""
        response = client.post('/ask', json={
            'text': '',
            'question': 'What is this?'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'lecture text' in data['error'].lower()

    def test_ask_without_question(self, client):
        """Should return error when question is missing."""
        response = client.post('/ask', json={
            'text': 'This is a lecture with plenty of content about various topics.',
            'question': ''
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'question' in data['error'].lower()

    def test_ask_with_text_too_short(self, client):
        """Should return error when text is shorter than minimum."""
        response = client.post('/ask', json={
            'text': 'Short',
            'question': 'What is this?'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'too short' in data['error'].lower()

    def test_ask_with_question_too_short(self, client):
        """Should return error when question is shorter than minimum."""
        response = client.post('/ask', json={
            'text': 'This is a valid lecture with enough content.',
            'question': 'OK'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'too short' in data['error'].lower()

    def test_ask_with_text_too_long(self, client):
        """Should return error when text exceeds maximum length."""
        long_text = 'a' * (TEXT_MAX_LENGTH + 1)
        response = client.post('/ask', json={
            'text': long_text,
            'question': 'What is this?'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'exceeds maximum length' in data['error'].lower()
        assert str(TEXT_MAX_LENGTH) in data['error']

    def test_ask_with_question_too_long(self, client):
        """Should return error when question exceeds maximum length."""
        long_question = 'q' * (QUESTION_MAX_LENGTH + 1)
        response = client.post('/ask', json={
            'text': 'This is a valid lecture with enough content.',
            'question': long_question
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'exceeds maximum length' in data['error'].lower()
        assert str(QUESTION_MAX_LENGTH) in data['error']

    def test_ask_with_whitespace_trimming(self, client, mock_openai):
        """Should trim whitespace and still validate correctly."""
        response = client.post('/ask', json={
            'text': '  ' + 'This is valid content with spaces.  ',
            'question': '  What is this?  '
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data

    def test_ask_at_max_limits(self, client, mock_openai):
        """Should accept inputs at exactly the maximum limits."""
        response = client.post('/ask', json={
            'text': 'x' * TEXT_MAX_LENGTH,
            'question': 'y' * QUESTION_MAX_LENGTH
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data

    def test_ask_with_null_inputs(self, client):
        """Should handle None/null inputs gracefully."""
        response = client.post('/ask', json={
            'text': None,
            'question': None
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_ask_with_missing_json(self, client):
        """Should handle missing JSON body."""
        response = client.post('/ask', data='not json', content_type='application/json')
        # Flask will return 400 for invalid JSON
        assert response.status_code in [400, 500]

    def test_ask_with_api_error(self, client):
        """Should handle OpenAI API errors gracefully."""
        with patch('app.client') as mock:
            mock.chat.completions.create.side_effect = Exception('API Error')
            response = client.post('/ask', json={
                'text': 'Valid lecture content for testing.',
                'question': 'What is this?'
            })
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            # Should not expose internal error details
            assert 'API Error' not in data['error']


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_ask_with_special_characters(self, client, mock_openai):
        """Should handle special characters in input."""
        response = client.post('/ask', json={
            'text': 'Content with special chars: !@#$%^&*()_+-=[]{};":\',<>?/\\|`~',
            'question': 'Can you handle special chars?'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data

    def test_ask_with_unicode_characters(self, client, mock_openai):
        """Should handle Unicode characters (emoji, accents, etc.)."""
        response = client.post('/ask', json={
            'text': 'This is content with émojis 🎓 and Unicode chars åäö.',
            'question': 'What about Unicode? 📚'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data

    def test_ask_with_multiline_text(self, client, mock_openai):
        """Should handle multiline input."""
        response = client.post('/ask', json={
            'text': 'Line 1: Introduction to Python\nLine 2: Variables and types\nLine 3: Functions',
            'question': 'Summarize this lecture.'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'answer' in data
