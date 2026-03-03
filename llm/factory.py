# llm/factory.py

from .local_llm import LocalLLM
from .api_llm import ApiLLM


def create_llm(config):
    llm_config = config["llm"]
    llm_type = llm_config["type"]

    if llm_type == "local":
        local_conf = llm_config["local"]

        return LocalLLM(
            model_path=local_conf["model_path"], base_url=local_conf.get("base_url")
        )

    elif llm_type == "api":
        api_conf = llm_config["api"]

        return ApiLLM(
            api_key=api_conf["api_key"],
            base_url=api_conf["base_url"],
            model=api_conf.get("model"),
        )

    else:
        raise ValueError(f"Unsupported LLM type: {llm_type}")
