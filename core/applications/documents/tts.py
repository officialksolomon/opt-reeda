import abc
import tempfile
import os
from django.core.files.base import ContentFile
from gtts import gTTS

class TTSProvider(abc.ABC):
    """
    Abstract base class for Text-to-Speech engines.
    Follows the Dependency Inversion Principle (SOLID).
    """
    
    @abc.abstractmethod
    def generate_audio(self, text: str) -> ContentFile:
        """
        Takes text and returns a Django ContentFile containing the audio data.
        """
        pass

class GttsProvider(TTSProvider):
    """
    gTTS (Google Text-to-Speech) implementation of the TTSProvider.
    """
    
    def generate_audio(self, text: str) -> ContentFile:
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to a temporary file to extract bytes
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            tts.save(tmp_path)
            with open(tmp_path, "rb") as f:
                content = f.read()
            return ContentFile(content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


def get_tts_provider() -> TTSProvider:
    """
    Factory function to get the current TTS provider.
    This allows us to easily swap out the backend later by reading from settings.
    """
    return GttsProvider()
