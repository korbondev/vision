from core import Task
from models import base_models
import bittensor as bt
import aiohttp
import ujson as json
import traceback
from typing import AsyncGenerator
from mining.proxy.core_miner import miner_requests_stats
from models import utility_models
POST_ENDPOINT = "v1/chat/completions"


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

    if body.model == utility_models.ChatModels.mixtral.value:
        body.model = "TheBloke/Nous-Hermes-2-Mixtral-8x7B-DPO-GPTQ"
    elif body.model == utility_models.ChatModels.llama_3.value:
        body.model = "casperhansen/llama-3-70b-instruct-awq"
    elif body.model == utility_models.ChatModels.llama_3_1_8b.value:
        body.model = "unsloth/Meta-Llama-3.1-8B-Instruct"
    elif body.model == utility_models.ChatModels.llama_3_1_70b.value:
        body.model = "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4"
    else:
        raise NotImplementedError(f"Model {body.model} not implemented for chat operation")

    text_generator = stream_text_from_server(body, url, task)
    bt.logging.info(f"✅ About do some chatting, with model {body.model}✨")
    return text_generator
