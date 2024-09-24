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
        try:
            async with session.post(text_endpoint, json=body.dict()) as resp:
                resp.raise_for_status()  # Handle bad status codes
                
                buffer = ""  # Initialize a buffer to accumulate chunks
                
                async for line in resp.content:
                    if line:
                        buffer += line.decode('utf-8').strip()  # Accumulate and clean each line
                        received_event_chunks = buffer.split("\n\n")  # Process only complete events
                        
                        # Process each event and leave the last one in case it's incomplete
                        for event in received_event_chunks[:-1]:
                            if not event.strip():
                                continue
                            prefix, _, data = event.partition(":")
                            if data.strip() == "[DONE]":
                                break
                            
                            try:
                                loaded_chunk = json.loads(data.strip())  # Safely load the JSON data
                                text = loaded_chunk.get("text", "")
                                logprob = loaded_chunk.get("logprobs", [{}])[0].get("logprob", None)
                                
                                # Yield only if valid data is found
                                if text and logprob is not None:
                                    data_to_yield = json.dumps({"text": text, "logprob": logprob})
                                    yield f"data: {data_to_yield}\n\n"
                            except json.JSONDecodeError as decode_err:
                                bt.logging.error(f"JSONDecodeError: {decode_err}. Problem chunk: {event}")
                        
                        # Keep the last incomplete event in the buffer for the next iteration
                        buffer = received_event_chunks[-1]

        except Exception as e:
            bt.logging.error(f"Error in streaming text from the server: {e}. Traceback: {traceback.format_exc()}")
        finally:
            miner_requests_stats.decrement_concurrency_group_from_task(task)


async def chat_logic(body: base_models.ChatIncoming, url: str, task: Task) -> AsyncGenerator:
    """Add GPU potential"""
    
    # Model selection logic
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
    
    # Streaming text generator
    text_generator = stream_text_from_server(body, url, task)
    bt.logging.info(f"✅ Chatting with model {body.model}✨")
    return text_generator
