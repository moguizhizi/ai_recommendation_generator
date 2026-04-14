## 🗂️ 项目结构

```text
project_root/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── controllers/               # 🌐 对外 API（接口层）
│   │   ├── __init__.py
│   │   ├── billing_controller.py
│   │   ├── chat_controller.py
│   │   ├── chat_controller_v2.py
│   │   ├── evaluation_controller.py
│   │   └── health_controller.py
│   ├── services/                  # 🧠 核心业务逻辑
│   │   ├── auth_service.py
│   │   ├── chat_service.py
│   │   ├── evaluation_service.py
│   │   ├── modules_processor.py
│   │   ├── plan_rule_engine.py
│   │   ├── rate_limit_service.py
│   │   ├── task_processor.py
│   │   ├── usage_service.py
│   │   └── user_processor.py
│   ├── tasks/                     # ⏱️ 后台任务
│   │   ├── data_sync_task.py
│   │   └── sync_manager.py
│   ├── prompts/                   # 📝 Prompt 定义
│   │   ├── __init__.py
│   │   ├── base_prompt.py
│   │   └── plan_prompt.py
│   ├── clients/                   # 🔌 外部服务客户端
│   │   ├── email_client.py
│   │   ├── payment_client.py
│   │   ├── task_client.py
│   │   ├── user_profile_client.py
│   │   └── vector_client.py
│   ├── schemas/                   # 📄 请求 / 响应模型
│   │   ├── chat.py
│   │   ├── chat_v2.py
│   │   └── common.py
│   ├── middlewares/               # 🧱 中间件
│   │   ├── auth.py
│   │   └── rate_limit.py
│   ├── repositories/              # 🗄️ 数据访问层
│   │   ├── api_key_repo.py
│   │   ├── usage_repo.py
│   │   └── user_repo.py
│   ├── data/                      # 📥 数据加载与预处理
│   │   ├── loader.py
│   │   ├── preprocess.py
│   │   └── datasets/
│   └── core/                      # ⚙️ 基础常量与公共能力
│       ├── constants.py
│       ├── security.py
│       ├── sync_state.py
│       ├── cognitive_l1/
│       └── errors/
├── utils/                         # 🧰 通用工具库
│   ├── csv_utils.py
│   ├── dataframe_utils.py
│   ├── io_utils.py
│   ├── json_utils.py
│   ├── logger.py
│   ├── metrics_utils.py
│   ├── parquet_utils.py
│   ├── path_utils.py
│   ├── seed.py
│   ├── text_utils.py
│   └── xlsx_utils.py
├── llm/                           # 🤖 LLM 适配层
│   ├── __init__.py
│   ├── api_llm.py
│   ├── base.py
│   ├── factory.py
│   └── local_llm.py
├── models/                        # 📊 预测模型实现
│   ├── base_model.py
│   ├── least_square_model.py
│   ├── lightgbm_model.py
│   ├── mlp_model.py
│   ├── model_factory.py
│   └── xgboost_model.py
├── configs/                       # ⚙️ 配置管理
│   ├── __init__.py
│   ├── config.yaml
│   └── loader.py
├── checkpoints/                   # 🧠 模型权重与特征配置
│   └── cognitive_l1/
│       ├── attention_lightgbm.txt
│       ├── executive_function_lightgbm.txt
│       ├── feature_columns.json
│       ├── memory_lightgbm.txt
│       └── perception_lightgbm.txt
├── data/                          # 📂 项目数据目录
│   ├── external/
│   │   └── raw/
│   └── internal/
│       ├── processed/
│       └── raw/
├── scripts/                       # 🛠️ 启动脚本
│   ├── start_api.sh
│   └── start_worker.sh
├── tests/                         # 🧪 测试
│   ├── test_auth.py
│   ├── test_chat_api.py
│   └── test_rate_limit.py
├── docker/                        # 🐳 Docker 配置
│   ├── Dockerfile
│   └── docker-compose.yml
├── logs/                          # 🪵 运行日志
├── migrations/                    # 🧬 迁移目录（当前为空）
├── requirements.txt
└── README.md
```
