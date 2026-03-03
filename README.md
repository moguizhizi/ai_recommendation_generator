## 🗂️ 项目结构

```text
project_root/
├── app/
│   ├── main.py                    # FastAPI 入口
│   │
│   ├── controllers/               # 🌐 对外 API（SaaS 接口层）
│   │   ├── chat_controller.py     # /v1/chat/completions（AI 训练方案生成接口）
│   │   ├── billing_controller.py  # /v1/billing（计费 / 账单）
│   │   └── health_controller.py   # /health（健康检查）
│   │
│   ├── services/                  # 🧠 业务编排层（核心业务逻辑）
│   │   ├── chat_service.py        # AI 训练方案主流程编排（规则引擎 + LLM + 响应组装）
│   │   ├── plan_rule_engine.py    # 🧩 训练方案规则引擎（用户类型判定 / 模块策略 / 难度规则）
│   │   ├── task_processor.py      # 🧠 外部 taskinfo 的本地加工处理（清洗 / 过滤 / 结构转换）
│   │   ├── modules_processor.py   # 🧩 训练模块拼装与加工（模块选取 / 排序 / 难度衔接 / 个性化推荐）
│   │   ├── auth_service.py        # Key / Token 校验
│   │   ├── rate_limit_service.py  # 限流 / 配额
│   │   └── usage_service.py       # 计量 / 计费
│   ├── prompts/                   # 📝 Prompt 层（极简版）
│   │   ├── __init__.py
│   │   ├── base_prompt.py         # Prompt 基类
│   │   └── plan_prompt.py         # 训练方案 Prompt
│   │
│   ├── clients/                   # 🔌 外部服务依赖（你调别人）
│   │   ├── payment_client.py      # 支付 / 账单服务客户端
│   │   ├── vector_client.py       # 向量库 / 知识库客户端
│   │   ├── email_client.py        # 邮件 / 短信通知客户端
│   │   └── task_client.py         # 📡 外部任务系统客户端（获取用户 taskinfo 原始数据）
│   │
│   ├── schemas/                   # 📄 请求 / 响应 DTO（Pydantic Models）
│   │   ├── chat.py                # AI 训练方案请求 / 响应结构
│   │   ├── auth.py                # 鉴权相关 DTO
│   │   └── billing.py             # 计费相关 DTO
│   │
│   ├── middlewares/               # 🧱 中间件（鉴权 / 限流 / 日志）
│   │   ├── auth.py
│   │   └── rate_limit.py
│   │
│   ├── repositories/              # 🗄️ 数据访问层（DB / Redis / ES 等）
│   │   ├── user_repo.py           # 用户信息
│   │   ├── api_key_repo.py        # API Key
│   │   └── usage_repo.py          # 调用计量 / 用量统计
│   │
│   └── core/                      # ⚙️ 全局基础能力
│       ├── logging.py             # 日志封装
│       ├── errors.py              # 统一异常定义
│       └── security.py            # 加解密 / 安全工具
│
├── llm/                           # 🤖 LLM 适配层（本地 / 云 API）
│   ├── base.py                    # LLM 抽象接口
│   ├── local_llm.py               # 本地模型实现（无 Key）
│   ├── api_llm.py                 # 云端 API 实现（有 Key）
│   └── factory.py                 # 按配置创建 LLM 实例
│
├── configs/                       # ⚙️ 配置管理
│   ├── config.yaml                # 环境配置（本地 / API / Key / 模型名）
│   └── loader.py                  # load_config()
│
├── migrations/                    # 🧬 数据库迁移（Alembic）
├── scripts/                       # 🛠️ 启动 / 运维脚本
│   ├── start_api.sh               # 启动 API 服务
│   └── start_worker.sh            # 启动异步任务（计费 / 日志 / 队列）
│
├── tests/                         # 🧪 单元测试 / 接口测试
├── docker/                        # 🐳 Docker / Compose
├── requirements.txt
└── README.md