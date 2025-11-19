import json
import re
import logging
import requests
from typing import List, Dict, Any, Optional
from config import load_config
from tools import tool_kit

logger = logging.getLogger(__name__)


class QwenClient:
    """Qwen API客户端"""

    def __init__(self):
        config = load_config()
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.model = config["model"]

    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """调用Qwen聊天补全API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2000
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"调用Qwen API失败: {e}")
            return f"调用大模型失败: {e}"


class SimpleAgent:
    """简化的Agent实现"""

    def __init__(self):
        self.llm = QwenClient()
        self.tools = {
            "create_ecs_instance": {
                "function": tool_kit.create_ecs_instance,
                "description": "创建ECS实例。输入应该是JSON格式，包含instance_type, image_id, instance_name, security_group_id, vswitch_id, system_disk_size, password等参数"
            },
            "create_oss_bucket": {
                "function": tool_kit.create_oss_bucket,
                "description": "创建OSS Bucket。输入应该是JSON格式，包含bucket_name, storage_class, acl等参数"
            },
            "check_ecs_status": {
                "function": tool_kit.check_ecs_status,
                "description": "检查ECS实例状态。输入应该是实例ID字符串"
            }
        }

    def _extract_action(self, text: str) -> Dict[str, Any]:
        """从文本中提取Action"""
        text = text.strip()

        # 检查是否有最终答案
        if "Final Answer:" in text:
            return {
                "type": "final",
                "content": text.split("Final Answer:")[-1].strip()
            }

        # 解析Action和Action Input
        action_match = re.search(r"Action:\s*(.+?)\s*Action Input:\s*(.+)", text, re.DOTALL)
        if action_match:
            action = action_match.group(1).strip()
            action_input = action_match.group(2).strip()

            try:
                action_input = json.loads(action_input)
            except json.JSONDecodeError:
                # 如果不是JSON，保持原样
                pass

            return {
                "type": "action",
                "action": action,
                "action_input": action_input
            }

        # 如果没有明确的action，认为是最终答案
        return {
            "type": "final",
            "content": text
        }

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_desc = "\n".join([f"- {name}: {desc['description']}" for name, desc in self.tools.items()])

        return f"""你是一个专业的云基础设施运维AI助手，专门负责阿里云资源的申请和自动化交付。

你的能力包括：
1. 创建ECS实例（弹性计算服务）
2. 创建OSS Bucket（对象存储服务）
3. 检查资源状态

可用工具：
{tools_desc}

工作流程：
1. 理解用户的需求，明确要创建的资源类型和配置
2. 收集必要的参数信息，如果用户没有提供完整信息，需要主动询问
3. 调用相应的工具函数创建资源
4. 返回创建结果和资源信息

重要规则：
- 在创建资源前，必须确认所有必要参数都已获得
- 对于ECS实例，必须的参数包括：实例类型、镜像ID、实例名称
- 对于OSS Bucket，必须的参数是Bucket名称，且必须全局唯一
- 使用JSON格式传递参数给工具函数
- 如果用户的需求不明确，要主动询问澄清
- 返回结果时要包含资源ID、状态和有用的信息

请按照以下格式思考：

Question: 用户输入的问题
Thought: 分析用户需求，思考需要做什么
Action: 工具名称
Action Input: 工具的输入（必须是JSON格式）
Observation: 工具执行结果
...（这个循环可以重复多次）
Thought: 现在我有足够信息回答用户
Final Answer: 最终的回答，包含资源创建结果和后续操作建议

现在开始处理用户请求："""

    def process_request(self, user_input: str, max_iterations: int = 5) -> str:
        """处理用户请求"""
        conversation = []
        system_prompt = self._build_system_prompt()

        # 初始消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {user_input}"}
        ]

        for i in range(max_iterations):
            # 调用LLM
            response = self.llm.chat_completion(messages)
            conversation.append(f"Thought: {response}")

            # 解析响应
            action_info = self._extract_action(response)

            if action_info["type"] == "final":
                return action_info["content"]

            elif action_info["type"] == "action":
                action = action_info["action"]
                action_input = action_info["action_input"]

                # 执行工具
                if action in self.tools:
                    try:
                        # 准备工具输入
                        if isinstance(action_input, dict):
                            tool_input = action_input
                        else:
                            tool_input = action_input

                        # 调用工具
                        tool_func = self.tools[action]["function"]
                        observation = tool_func(tool_input)

                        # 记录到对话历史
                        observation_str = json.dumps(observation, ensure_ascii=False, indent=2)
                        conversation.append(f"Action: {action}")
                        conversation.append(f"Observation: {observation_str}")

                        # 更新消息
                        messages.extend([
                            {"role": "assistant", "content": response},
                            {"role": "user", "content": f"Observation: {observation_str}"}
                        ])

                    except Exception as e:
                        error_msg = f"执行工具 {action} 时出错: {str(e)}"
                        conversation.append(f"Error: {error_msg}")
                        messages.append({"role": "user", "content": f"Error: {error_msg}"})
                else:
                    error_msg = f"未知工具: {action}"
                    conversation.append(f"Error: {error_msg}")
                    messages.append({"role": "user", "content": f"Error: {error_msg}"})
            else:
                # 无法解析，返回原始响应
                return response

        return "达到最大迭代次数，未能完成请求。请检查您的请求是否明确。"


# 全局Agent实例
infra_agent = SimpleAgent()