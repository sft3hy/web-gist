import requests


def parse_url(url: str):

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "link-parser",
            "stream": False,
            "messages": [
                {"role": "user", "content": url},
            ],
        },
    )

    return response.json()["message"]["content"]


# parse_url(
#     "https://www.reuters.com/world/middle-east/palestinian-teenager-with-us-citizenship-shot-dead-by-israeli-settler-2025-04-06/#:~:text=RAMALLAH%2C%20April%206%20(Reuters),near%2Ddaily%20confrontations%20between%20Israeli"
# )
