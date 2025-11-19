1. 概述
云基础设施自动化 Agent
基于 Qwen 大模型的阿里云资源自动化交付系统，支持 ECS 实例和 OSS Bucket 的标准化申请与自动化交付。

2. 系统设计思路
核心概念

用户输入 → 通过 API 接收请求，例如：“帮我创建一个 ECS 和 OSS bucket”

Agent → 解析意图，判断需要调用哪些工具

工具 (Tools) → 封装阿里云 SDK 接口，如创建 ECS、OSS

LLM 决策 → 使用 ReAct 机制，逐步推理，调用工具执行操作

返回结果 → 将资源创建状态返回给用户

3. 功能特性
🤖 智能对话：基于 Qwen 大模型的自然语言交互

🚀 自动化交付：一键创建 ECS 实例和 OSS Bucket

🔧 标准化流程：遵循阿里云最佳实践的资源配置

📊 状态监控：实时查看资源创建状态

🌐 多接口支持：支持 Web API 和命令行交互

## 快速开始

### 环境要求

环境要求
Python 3.8+

阿里云账号及访问密钥

Qwen API Key
# 代码结构

infra-agent/
│
├── app.py                # FastAPI Web 服务入口
├── config.py             # 配置加载模块
├── agent_core.py         # Agent 核心逻辑
├── tools.py              # 阿里云工具函数
├── interaction.py        # 命令行交互界面
├── setup.py              # 依赖安装脚本
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量模板
└── README.md             # 项目文档

### 安装步骤

1. 克隆项目
bash
git clone https://github.com/JaciCao-123/qwen-agent-provision/tree/main/agent_infra
cd infra-agent

2. 环境配置
cp .env.example .env
# 编辑 .env 文件，填入您的配置

3. 安装依赖
pip install -r requirements.txt

4. 运行方式
python interaction.py

5. API使用示例
import requests
