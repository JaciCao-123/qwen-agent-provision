import json
import re
import logging
import requests
from typing import List, Dict, Any
from config import load_config
from tools import tool_kit

# 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(),
#         logging.FileHandler('agent.log', encoding='utf-8')
#     ]
# )
logger = logging.getLogger(__name__)


class QwenClient:
    """Qwen API客户端"""

    def __init__(self):
        config = load_config()
        self.api_key = config["api_key"]
        self.base_url = config["base_url"]
        self.model = config["model"]
        logger.info("Qwen客户端初始化完成")

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
    def __init__(self):
        self.llm = QwenClient()
        self.tools = {
            "create_ecs_instance": {
                "function": tool_kit.create_ecs_instance,
                "description": "创建ECS实例。需要参数: instance_type, image_id, instance_name等"
            },
            "create_oss_bucket": {
                "function": tool_kit.create_oss_bucket,
                "description": "创建OSS Bucket。需要参数: bucket_name, acl等"
            },
            "check_ecs_status": {
                "function": tool_kit.check_ecs_status,
                "description": "检查ECS实例状态。需要参数: 实例ID"
            }
        }
        logger.info("Agent初始化完成，可用工具: %s", list(self.tools.keys()))

    def _extract_action(self, text: str) -> Dict[str, Any]:
        """从文本中提取Action"""
        text = text.strip()

        # 先尝试解析Action和Action Input，优先于Final Answer
        action_match = re.search(r"Action:\s*(\w+)\s*Action Input:\s*(.+?)(?:\s+Observation:|$)", text, re.DOTALL)
        if action_match:
            action = action_match.group(1).strip()
            action_input = action_match.group(2).strip()
            #logger.debug("提取到动作: %s, 输入: %s", action, action_input)

            # 清理JSON格式
            action_input = action_input.replace('```json', '').replace('```', '').strip()

            # 解析JSON或处理文本
            if action_input.startswith('{'):
                try:
                    parsed_input = json.loads(action_input)
                    logger.debug("成功解析JSON参数")
                    return {
                        "type": "action",
                        "action": action,
                        "action_input": parsed_input
                    }
                except json.JSONDecodeError:
                    #logger.warning("JSON解析失败，尝试文本处理")
                    pass

            # 文本处理逻辑
            if action == "create_oss_bucket":
                bucket_name = self._extract_bucket_name(action_input)
                if bucket_name:
                    logger.debug("从文本提取到bucket名称: %s", bucket_name)
                    return {
                        "type": "action",
                        "action": action,
                        "action_input": {"bucket_name": bucket_name, "acl": "private"}
                    }

        # 检查最终答案 - 只有在没有Action时才返回Final Answer
        if "Final Answer:" in text:
            final_content = text.split("Final Answer:")[-1].strip()
            return {
                "type": "final",
                "content": final_content
            }

        # 推断OSS创建动作，但不再自动生成名称
        if "oss" in text.lower() and "bucket" in text.lower():
            return {
                "type": "final",
                "content": "请提供要创建的OSS Bucket名称。"
            }

        # 默认返回最终答案
        return {
            "type": "final",
            "content": text
        }

    def _extract_bucket_name(self, text: str) -> str:
        """从文本中提取bucket名称"""
        # 查找bucket名称模式
        patterns = [
            r'"bucket_name"\s*:\s*"([^"]+)"',
            r"'bucket_name'\s*:\s*'([^']+)'",
            r'名称[：:]\s*"([^"]+)"',
            r'名称[：:]\s*([a-z0-9][a-z0-9-]{1,61}[a-z0-9])',
            r'名称为?\s*"([^"]+)"',
            r'名称为?\s*([a-z0-9][a-z0-9-]{1,61}[a-z0-9])',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                bucket_name = match.group(1).strip()
                if self._is_valid_bucket_name(bucket_name):
                    return bucket_name

        # 查找符合命名规则的字符串
        bucket_match = re.search(r'([a-z0-9][a-z0-9-]{1,61}[a-z0-9])', text)
        if bucket_match:
            bucket_name = bucket_match.group(1)
            if self._is_valid_bucket_name(bucket_name):
                return bucket_name

        # 不再自动生成名称
        return None

    def _is_valid_bucket_name(self, bucket_name: str) -> bool:
        """验证Bucket名称格式"""
        pattern = r'^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$'
        return bool(re.match(pattern, bucket_name)) and 3 <= len(bucket_name) <= 63

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        tools_desc = "\n".join([f"- {name}: {desc['description']}" for name, desc in self.tools.items()])

        return f"""你是一个云基础设施运维AI助手，负责阿里云资源的自动化交付。

可用工具：
{tools_desc}

重要规则：
- 对于OSS Bucket创建，用户必须提供bucket_name参数
- bucket_name必须全局唯一，符合命名规范：小写字母、数字和短横线，3-63字符
- 使用JSON格式传递参数
- 不要假设操作结果，等待实际执行后的Observation

响应格式：
Question: 用户输入
Thought: 分析需求
Action: 工具名称
Action Input: {{"bucket_name": "bucket名称", "acl": "private"}}
Observation: [等待实际执行结果]
Final Answer: 基于实际执行结果的最终回答

现在开始处理用户请求："""

    def process_request(self, user_input: str, max_iterations: int = 3) -> str:
        """处理用户请求"""
        #logger.info("处理用户请求: %s", user_input)
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"Question: {user_input}"}
        ]

        for i in range(max_iterations):
           # logger.debug("第 %d 次迭代", i+1)
            # 调用LLM
            response = self.llm.chat_completion(messages)

            # 解析响应
            action_info = self._extract_action(response)

            if action_info["type"] == "final":
                logger.info("返回最终答案")
                return action_info["content"]

            elif action_info["type"] == "action":
                action = action_info["action"]
                action_input = action_info["action_input"]
                logger.info("执行动作: %s", action)

                if action in self.tools:
                    try:
                        # 调用工具
                        tool_func = self.tools[action]["function"]
                        #logger.info("调用工具函数: %s", action)
                        observation = tool_func(action_input)
                        #logger.info("工具执行完成，状态: %s", observation.get('status', 'unknown'))

                        # 更新对话
                        messages.extend([
                            {"role": "assistant", "content": response},
                            {"role": "user", "content": f"Observation: {json.dumps(observation, ensure_ascii=False)}"}
                        ])
                    except Exception as e:
                        error_msg = f"执行工具 {action} 时出错: {str(e)}"
                        #logger.error(error_msg)
                        messages.append({"role": "user", "content": f"Error: {error_msg}"})
                else:
                    error_msg = f"未知工具: {action}"
                    #logger.error(error_msg)
                    messages.append({"role": "user", "content": f"Error: {error_msg}"})

        #logger.warning("达到最大迭代次数，未能完成请求")
        return "达到最大迭代次数，未能完成请求。"


# 全局Agent实例
infra_agent = SimpleAgent()
