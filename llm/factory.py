# llm/factory.py
from .local_llm import LocalLLM
from .api_llm import ApiLLM

def create_llm(config):
    if config["llm"]["type"] == "local":
        return LocalLLM(config["llm"]["model_path"])
    elif config["llm"]["type"] == "api":
        return ApiLLM(config["llm"]["api_key"], config["llm"]["base_url"])
    else:
        raise ValueError("Unsupported LLM type")