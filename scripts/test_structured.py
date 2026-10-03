#!/usr/bin/env -S uv run python
from ollama import chat
from pydantic import BaseModel

# 1. Define the schema
class CountryInfo(BaseModel):
    name: str
    capital: str
    population_millions: float

# 2. Stream the response
stream = chat(
    model='llama3.1',
    messages=[{'role': 'user', 'content': 'Tell me about Japan.'}],
    format=CountryInfo.model_json_schema(), # Enforces the structure
    stream=True
)

# 3. Consume the chunks
for chunk in stream:
    # Print the raw text tokens as they stream out in proper JSON syntax
    print(chunk['message']['content'], end='', flush=True)
