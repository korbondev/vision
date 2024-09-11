from core import Task
from models import base_models
import bittensor as bt
import aiohttp
import ujson as json
import traceback
from typing import AsyncGenerator
from mining.proxy.core_miner import miner_requests_stats

POST_ENDPOINT = "generate_text"


async def stream_text_from_server(body: base_models.ChatIncoming, url: str, task: Task) -> AsyncGenerator:
    text_endpoint = url + POST_ENDPOINT
    async with aiohttp.ClientSession() as session:
        async with session.post(text_endpoint, json=body.dict()) as resp:
            async for chunk_enc in resp.content:
                try:
                    chunk = chunk_enc.decode()
                    received_event_chunks = chunk.split("\n\n")
                    for event in received_event_chunks:
                        if not event.strip():
                            continue
                        prefix, _, data = event.partition(":")
                        if data.strip() == "[DONE]":
                            break
                        loaded_chunk = json.loads(data)
                        text = loaded_chunk["text"]
                        logprob = loaded_chunk["logprobs"][0]["logprob"]
                        data = json.dumps({"text": text, "logprob": logprob})

                        yield f"data: {data}\n\n"
                except Exception as e:
                    bt.logging.error(f"Error in streaming text from the server: {e}. Original chunk: {chunk}\n{traceback.format_exc()}")
        miner_requests_stats.decrement_concurrency_group_from_task(task)


async def chat_logic(body: base_models.ChatIncoming, url: str, task: Task) -> AsyncGenerator:
    """Add gpu potential"""

    text_generator = stream_text_from_server(body, url, task)
    bt.logging.info(f"✅ About do some chatting, with model {body.model}✨")
    return text_generator
