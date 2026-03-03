# test_chat_api.py

import time
from configs.loader import load_config
from llm.api_llm import ApiLLM

from app.core.logging import setup_logging, get_logger

# 初始化日志
setup_logging()

logger = get_logger(__name__)


def create_llm_from_config(config: dict):
    llm_config = config["llm"]
    runtime_config = config.get("runtime", {})

    timeout = runtime_config.get("timeout", 60)

    logger.info(f"Initializing LLM, type={llm_config['type']}")

    if llm_config["type"] == "api":
        api_cfg = llm_config["api"]

        logger.debug(
            f"Using API model={api_cfg['model']} base_url={api_cfg['base_url']}"
        )

        return ApiLLM(
            base_url=api_cfg["base_url"],
            model=api_cfg["model"],
            api_key=api_cfg.get("api_key"),
            timeout=timeout,
        )

    elif llm_config["type"] == "local":
        local_cfg = llm_config["local"]

        logger.debug(
            f"Using local model server at {local_cfg['base_url']}"
        )

        return ApiLLM(
            base_url=local_cfg["base_url"],
            model="local-model",
            api_key=None,
            timeout=timeout,
        )

    else:
        logger.error(f"Unsupported llm type: {llm_config['type']}")
        raise ValueError(f"Unsupported llm type: {llm_config['type']}")


def main():
    logger.info("==== Test Chat API Started ====")

    config = load_config()
    runtime_config = config.get("runtime", {})
    max_retries = runtime_config.get("max_retries", 3)

    llm = create_llm_from_config(config)

    prompt = "请用一句话介绍人工智能。"

    logger.info("Sending request to LLM...")
    logger.debug(f"Prompt: {prompt}")

    for attempt in range(1, max_retries + 1):
        try:
            start_time = time.time()

            response = llm.chat(prompt)

            duration = time.time() - start_time

            logger.info(
                f"Request succeeded on attempt {attempt}, "
                f"time_cost={duration:.3f}s"
            )

            logger.debug(f"Response: {response}")

            print("\n=== LLM Response ===")
            print(response)
            return

        except Exception as e:
            logger.exception(
                f"Attempt {attempt} failed: {e}"
            )

            if attempt == max_retries:
                logger.error("All retries failed. Exiting.")
                raise

            time.sleep(1.5)


if __name__ == "__main__":
    main()