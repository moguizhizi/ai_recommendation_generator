# test_chat_api.py

import time

from configs.loader import load_config
from llm.api_llm import ApiLLM, LLMError
from utils.logger import setup_logging, get_logger

# 初始化日志
setup_logging()
logger = get_logger(__name__)


def create_llm_from_config(config: dict) -> ApiLLM:
    llm_config = config["llm"]
    runtime_config = config.get("runtime", {})

    timeout = runtime_config.get("timeout", 60)
    max_retries = runtime_config.get("max_retries", 3)

    logger.info(f"Initializing LLM | type={llm_config['type']}")

    if llm_config["type"] == "api":
        api_cfg = llm_config["api"]

        logger.debug(f"API model={api_cfg['model']} " f"base_url={api_cfg['base_url']}")

        return ApiLLM(
            base_url=api_cfg["base_url"],
            model=api_cfg["model"],
            api_key=api_cfg.get("api_key"),
            timeout=timeout,
            max_retries=max_retries,
        )

    elif llm_config["type"] == "local":
        local_cfg = llm_config["local"]

        logger.debug(f"Local model server at {local_cfg['base_url']}")

        return ApiLLM(
            base_url=local_cfg["base_url"],
            model="local-model",
            timeout=timeout,
            max_retries=max_retries,
        )

    else:
        raise ValueError(f"Unsupported llm type: {llm_config['type']}")


def run_once(llm: ApiLLM, prompt: str) -> str:
    start_time = time.time()
    response = llm.chat(prompt)
    duration = time.time() - start_time

    logger.info(f"LLM request finished | time_cost={duration:.3f}s")
    logger.debug(f"Response: {response}")

    return response



def run_stream_once(llm, prompt: str) -> str:
    logger.info("Starting stream_chat request")

    start_time = time.time()
    response_chunks = []

    try:
        for chunk in llm.stream_chat(prompt):
            response_chunks.append(chunk)

        full_response = "".join(response_chunks)

        duration = time.time() - start_time

        logger.info(
            f"Stream request succeeded | "
            f"time_cost={duration:.3f}s | "
            f"chars={len(full_response)}"
        )

        return full_response

    except LLMError:
        raise

    except Exception as e:
        logger.exception("Stream execution failed")
        raise


def main():
    logger.info("==== Test Chat API Started ====")

    config = load_config()
    llm = create_llm_from_config(config)

    prompt = "请用一句话介绍人工智能。"

    logger.info("Sending non-stream request")
    logger.debug(f"Prompt: {prompt}")

    try:
        # ===== 普通 chat =====
        response = run_once(llm, prompt)

        print("\n=== Chat Response ===")
        print(response)

        # ===== Stream chat =====
        logger.info("Sending stream request")

        stream_response = run_stream_once(
            llm,
            prompt,
        )

        print("\n=== Stream Response ===")
        print(stream_response)

    except LLMError as e:
        logger.error(
            f"LLMError occurred | code={e.code} | retryable={e.retryable}"
        )
        logger.exception(e)
        raise

    except Exception:
        logger.exception("Unexpected error")
        raise


if __name__ == "__main__":
    main()
