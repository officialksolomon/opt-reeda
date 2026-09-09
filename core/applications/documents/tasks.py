from celery import shared_task
from core.applications.documents.models import Document, DocumentChunk
from django.contrib.auth import get_user_model


@shared_task
def process_document_task(document_id: int):
    """
    Background task to process a document (chunking, LLM optimization, etc).
    
    Runs asynchronously via Celery worker.
    """
    from core.applications.documents.services import PipelineService
    document = Document.objects.get(id=document_id)
    PipelineService.process_document(document)


@shared_task
def generate_regex_rule_task(raw_text: str, edited_text: str, user_id: int, domain_type: str):
    """
    Background task to generate a regex rule from a user's manual edit.
    
    Runs asynchronously via Celery worker.
    """
    from core.applications.documents.services import LLMOptimizerService
    user = get_user_model().objects.get(id=user_id)
    LLMOptimizerService.generate_regex_rule(raw_text, edited_text, user, domain_type)


@shared_task
def generate_chunk_audio_task(chunk_id: int):
    """
    Background task to generate TTS audio for a document chunk using OpenAI's API.
    
    Runs asynchronously via Celery worker.
    """
    from core.applications.documents.models import ChunkAudioRecording
    from core.applications.documents.tts import get_tts_provider
    
    chunk = DocumentChunk.objects.get(id=chunk_id)
    provider = get_tts_provider()
    
    try:
        # Generate the audio stream via the API
        audio_content = provider.generate_audio(chunk.optimized_text)
        audio_content.name = f"document_{chunk.document.pk}_chunk_{chunk.chunk_index}.mp3"
        
        # Save the audio file to the chunk
        recording, _ = ChunkAudioRecording.objects.get_or_create(chunk=chunk)
        recording.audio_file.save(audio_content.name, audio_content, save=True)
    finally:
        chunk.is_recording = False
        chunk.save(update_fields=["is_recording"])
