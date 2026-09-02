from unittest.mock import patch
from django.test import TestCase
from django.core.files.base import ContentFile

from core.applications.documents.tts import GttsProvider, get_tts_provider


class TTSTestCase(TestCase):
    def test_get_tts_provider(self):
        """get_tts_provider should return an instance of GttsProvider."""
        provider = get_tts_provider()
        self.assertIsInstance(provider, GttsProvider)

    @patch("core.applications.documents.tts.gTTS")
    def test_gtts_provider_generate_audio(self, mock_gtts_class):
        """GttsProvider should correctly generate audio and return a ContentFile."""
        # Mock the instance returned by gTTS()
        mock_tts_instance = mock_gtts_class.return_value
        
        # We need to mock the save method to actually write something to the temp file
        # because the provider reads it back
        def mock_save(filepath):
            with open(filepath, 'wb') as f:
                f.write(b"mock_audio_data")
                
        mock_tts_instance.save.side_effect = mock_save
        
        provider = GttsProvider()
        result = provider.generate_audio("Hello world")
        
        # Verify gTTS was initialized correctly
        mock_gtts_class.assert_called_once_with(text="Hello world", lang="en", slow=False)
        mock_tts_instance.save.assert_called_once()
        
        # Verify the result is a ContentFile with the correct data
        self.assertIsInstance(result, ContentFile)
        self.assertEqual(result.read(), b"mock_audio_data")
