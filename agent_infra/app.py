from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging

from agent_core import infra_agent

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="云基础设施自动化Agent",
    description="基于Qwen大模型的阿里云资源自动化交付系统",
    version="1.0.0"
)

class UserRequest(BaseModel):
    message: str
    user_id: str = "default"

class AgentResponse(BaseModel):
    response: str
    status: str = "success"

@app.post("/chat", response_model=AgentResponse)
async def chat_with_agent(request: UserRequest):
    """与基础设施Agent对话"""
    try:
        logger.info(f"收到用户 {request.user_id} 的请求: {request.message}")
        response = infra_agent.process_request(request.message)
        return AgentResponse(response=response)
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "infra-agent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)