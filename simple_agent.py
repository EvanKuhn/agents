# Simple 'hello world' agent. This calls into llama 3.1 running
# locally via Ollama, prompts the model with a question, and
# prints the response.

import ollama

QUERY = "Why is the sky blue?"

print(f"User Prompt: {QUERY}")

stream = ollama.chat(
    model="llama3.1",
    messages=[
        {
            "role": "user",
            "content": QUERY,
        },
    ],
    stream=True,
)

print()
#print(response["message"]["content"])
assistant_response = ""
for chunk in stream:
    content = chunk['message']['content']
    print(content, end="", flush=True)
    assistant_response += content
print() # Print a newline at the end of the response
