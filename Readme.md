# Chatbot with Chainlit and local LLM

This is a simple chatbot that uses Chainlit and a local LLM.

## Install dependencies

```bash
pip install pipenv
pipenv install
```

## Download the model

```bash
curl -L -o models/7B/llama-2-7b-chat.Q2_K.gguf https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q2_K.gguf?download=true
```

you can find other models on [HuggingFace](https://huggingface.co/TheBloke/)

## Running the app

```bash
pipenv run python -m main
```