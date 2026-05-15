import asyncio
import io

_FALLBACK_EDGE_VOICE = "en-US-GuyNeural"
_CACHE_TTL = 3600  # 1 hour


def _format_ticket_number(ticket_number: str) -> str:
    return " ".join(list(ticket_number))


def _get_voice_config(branch):
    from configuration.models import BranchVoiceConfig, SystemVoiceConfig
    try:
        return branch.voice_config
    except Exception:
        return SystemVoiceConfig.get_solo()


def _run_async(coro, timeout=20):
    """Run a coroutine safely whether or not an event loop is already running."""
    try:
        asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=timeout)
    except RuntimeError:
        return asyncio.run(coro)


def _edge_tts_stream(text: str, voice: str, rate: str = "+0%") -> bytes:
    import edge_tts

    async def _run():
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        if not audio:
            raise RuntimeError(f"edge-tts returned no audio (voice='{voice}')")
        return audio

    return _run_async(_run())


def _generate_edge_tts(text: str, voice: str, rate: str = "+0%") -> bytes:
    try:
        return _edge_tts_stream(text, voice, rate)
    except Exception as e:
        if voice == _FALLBACK_EDGE_VOICE:
            raise
        print(f"[tts] voice '{voice}' failed ({e}), retrying with {_FALLBACK_EDGE_VOICE}")
        return _edge_tts_stream(text, _FALLBACK_EDGE_VOICE, rate)


def _generate_gtts(text: str, language: str, tld: str, slow: bool) -> bytes:
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text, lang=language, tld=tld, slow=slow).write_to_fp(buf)
    return buf.getvalue()


def generate_announcement_audio(ticket, counter) -> bytes | None:
    """
    Generate (or retrieve from cache) TTS audio for a ticket announcement.
    Returns raw MP3 bytes, or None on failure.
    Audio is cached in Redis so re-announcing the same ticket from the same
    counter is instant with no TTS call.
    """
    from django.core.cache import cache
    from configuration.models import TTSEngine

    cache_key = f"ticket_audio:{ticket.uuid}:{counter.uuid}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        config = _get_voice_config(ticket.branch)
        ticket_spoken = _format_ticket_number(ticket.ticket_number)
        counter_name = counter.counter_name if counter else "the counter"
        branch_name = ticket.branch.name

        text = config.announcement_template.format(
            ticket_number=ticket_spoken,
            counter_name=counter_name,
            branch_name=branch_name,
        )

        if config.engine == TTSEngine.EDGE_TTS:
            rate = getattr(config, "rate", "+0%") or "+0%"
            audio_bytes = _generate_edge_tts(text, config.voice, rate)
        else:
            audio_bytes = _generate_gtts(text, config.language, config.tld, config.slow)

        if not audio_bytes:
            print("[tts] no audio bytes produced")
            return None

        cache.set(cache_key, audio_bytes, _CACHE_TTL)
        return audio_bytes

    except Exception as e:
        print(f"[tts] error generating audio: {e}")
        return None
