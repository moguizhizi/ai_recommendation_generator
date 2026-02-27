project_root/
├── app/
│   ├── main.py                    # FastAPI 入口
│   │
│   ├── controllers/               # 🌐 对外 API（SaaS 接口层）
│   │   ├── chat_controller.py     # /v1/chat/completions
│   │   ├── billing_controller.py  # /v1/billing
│   │   └── health_controller.py   # /health
│   │
│   ├── services/                  # 🧠 业务编排层
│   │   ├── chat_service.py        # 聊天主逻辑
│   │   ├── auth_service.py        # Key / Token 校验
│   │   ├── rate_limit_service.py  # 限流 / 配额
│   │   └── usage_service.py       # 计量 / 计费
│   │
│   ├── clients/                   # 🔌 外部服务依赖（你调别人）
│   │   ├── payment_client.py      # 支付 / 账单
│   │   ├── vector_client.py       # 向量库
│   │   └── email_client.py        # 邮件 / 短信
│   │
│   ├── schemas/                   # 📄 请求 / 响应 DTO
│   │   ├── chat.py
│   │   ├── auth.py
│   │   └── billing.py
│   │
│   ├── middlewares/               # 🧱 中间件（鉴权 / 限流 / 日志）
│   │   ├── auth.py
│   │   └── rate_limit.py
│   │
│   ├── repositories/              # 🗄️ 数据访问层
│   │   ├── user_repo.py
│   │   ├── api_key_repo.py
│   │   └── usage_repo.py
│   │
│   └── core/                      # ⚙️ 全局能力
│       ├── logging.py
│       ├── errors.py
│       └── security.py
│
├── llm/                           # 🤖 LLM 适配层（本地 / 云 API）
│   ├── base.py
│   ├── local_llm.py
│   ├── api_llm.py
│   └── factory.py
│
├── configs/                       # ⚙️ 配置管理
│   ├── config.yaml
│   └── loader.py
│
├── migrations/                    # 🧬 数据库迁移（Alembic）
├── scripts/                       # 🛠️ 启动 / 运维脚本
│   ├── start_api.sh
│   └── start_worker.sh
│
├── tests/                         # 🧪 测试
├── docker/                        # 🐳 容器化部署
├── requirements.txt
└── README.md