import json
import uuid
import logging
from typing import Dict, Any
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
import oss2
from oss2.exceptions import NoSuchBucket, OssError

from config import load_config

logger = logging.getLogger(__name__)


class AliyunToolKit:
    def __init__(self):
        config = load_config()
        self.region_id = config["region_id"]
        self.access_key_id = config["access_key_id"]
        self.access_key_secret = config["access_key_secret"]

        # 初始化ECS客户端
        ecs_config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            endpoint=f'ecs.{self.region_id}.aliyuncs.com'
        )
        self.ecs_client = EcsClient(ecs_config)

        # 初始化OSS认证 - 使用更稳定的方式
        self.oss_auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        # 使用外部Endpoint，避免内网问题
        self.oss_endpoint = f"https://oss-{self.region_id}.aliyuncs.com"

    def create_ecs_instance(self, ecs_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建ECS实例"""
        request_id = str(uuid.uuid4())
        try:
            logger.info(f"开始创建ECS实例: {ecs_config.get('instance_name', 'unknown')}")

            # 构建创建实例请求
            create_request = ecs_models.CreateInstanceRequest(
                region_id=self.region_id,
                instance_type=ecs_config.get("instance_type", "ecs.g6.large"),
                image_id=ecs_config.get("image_id", "centos_7_9_x64_20G_alibase_20231219.vhd"),
                instance_name=ecs_config.get("instance_name", "agent-created-ecs"),
                system_disk_size=ecs_config.get("system_disk_size", 40),
            )

            # 可选参数
            if ecs_config.get("security_group_id"):
                create_request.security_group_id = ecs_config["security_group_id"]
            if ecs_config.get("vswitch_id"):
                create_request.vswitch_id = ecs_config["vswitch_id"]
            if ecs_config.get("password"):
                create_request.password = ecs_config["password"]

            runtime = util_models.RuntimeOptions()
            response = self.ecs_client.create_instance_with_options(create_request, runtime)

            logger.info(f"ECS实例创建成功: {response.body.instance_id}")

            return {
                "request_id": request_id,
                "resource_type": "ecs",
                "resource_id": response.body.instance_id,
                "status": "success",
                "message": "ECS实例创建成功",
                "details": {
                    "instance_id": response.body.instance_id,
                    "instance_name": ecs_config.get("instance_name", "agent-created-ecs"),
                    "instance_type": ecs_config.get("instance_type", "ecs.g6.large"),
                    "region": self.region_id
                }
            }

        except Exception as e:
            logger.error(f"创建ECS实例失败: {str(e)}")
            return {
                "request_id": request_id,
                "resource_type": "ecs",
                "status": "failed",
                "message": f"ECS实例创建失败: {str(e)}"
            }

    def create_oss_bucket(self, oss_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建OSS Bucket - 简化且可靠的版本"""
        request_id = str(uuid.uuid4())
        bucket_name = oss_config.get("bucket_name", "").strip()

        if not bucket_name:
            return {
                "request_id": request_id,
                "resource_type": "oss",
                "status": "failed",
                "message": "Bucket名称不能为空"
            }

        # 验证bucket名称格式
        if not self._is_valid_bucket_name(bucket_name):
            return {
                "request_id": request_id,
                "resource_type": "oss",
                "status": "failed",
                "message": "Bucket名称格式无效。只能包含小写字母、数字和短横线，且必须以字母或数字开头结尾，长度3-63字符"
            }

        logger.info(f"开始创建OSS Bucket: {bucket_name}")

        try:
            # 创建Bucket实例
            bucket = oss2.Bucket(self.oss_auth, self.oss_endpoint, bucket_name)

            # 首先检查是否已存在
            if self._check_bucket_exists(bucket_name):
                logger.info(f"OSS Bucket已存在: {bucket_name}")
                return {
                    "request_id": request_id,
                    "resource_type": "oss",
                    "resource_id": bucket_name,
                    "status": "success",
                    "message": "OSS Bucket已存在",
                    "details": {
                        "bucket_name": bucket_name,
                        "region": self.region_id,
                        "existed": True
                    }
                }

            # 创建Bucket - 使用最简单的创建方式
            # 注意：某些region可能不支持存储类型设置，我们先创建基础bucket
            create_result = bucket.create_bucket(
                permission=oss_config.get("acl", "private")
            )

            # 检查HTTP状态码确认创建成功
            if create_result.status != 200:
                return {
                    "request_id": request_id,
                    "resource_type": "oss",
                    "status": "failed",
                    "message": f"创建请求失败，HTTP状态码: {create_result.status}"
                }

            logger.info(f"OSS Bucket创建请求已发送: {bucket_name}")

            # 等待并验证Bucket是否真正创建成功
            import time
            max_retries = 5
            for i in range(max_retries):
                time.sleep(2)  # 等待2秒
                if self._check_bucket_exists(bucket_name):
                    logger.info(f"OSS Bucket验证成功: {bucket_name}")
                    return {
                        "request_id": request_id,
                        "resource_type": "oss",
                        "resource_id": bucket_name,
                        "status": "success",
                        "message": "OSS Bucket创建并验证成功",
                        "details": {
                            "bucket_name": bucket_name,
                            "acl": oss_config.get("acl", "private"),
                            "region": self.region_id,
                            "endpoint": self.oss_endpoint,
                            "verification_retries": i + 1
                        }
                    }
                logger.info(f"第 {i + 1} 次验证Bucket存在性失败，等待重试...")

            # 如果验证失败
            return {
                "request_id": request_id,
                "resource_type": "oss",
                "status": "failed",
                "message": "Bucket创建请求已发送，但验证存在性失败。请稍后在OSS控制台检查",
                "details": {
                    "bucket_name": bucket_name,
                    "region": self.region_id,
                    "verification_attempts": max_retries
                }
            }

        except OssError as e:
            error_msg = f"OSS操作失败: {e}"
            logger.error(f"{error_msg}, 错误代码: {e.code}")
            return {
                "request_id": request_id,
                "resource_type": "oss",
                "status": "failed",
                "message": error_msg,
                "error_code": getattr(e, 'code', 'Unknown')
            }
        except Exception as e:
            error_msg = f"创建OSS Bucket时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return {
                "request_id": request_id,
                "resource_type": "oss",
                "status": "failed",
                "message": error_msg
            }
    def _is_valid_bucket_name(self, bucket_name: str) -> bool:
        """验证Bucket名称格式"""
        import re
        # OSS bucket命名规则：3-63字符，小写字母数字和短横线，不能以短横线开头或结尾
        pattern = r'^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$'
        return bool(re.match(pattern, bucket_name)) and len(bucket_name) >= 3 and len(bucket_name) <= 63

    def _check_bucket_exists(self, bucket_name: str) -> bool:
        """检查Bucket是否存在 - 更健壮的版本"""
        try:
            bucket = oss2.Bucket(self.oss_auth, self.oss_endpoint, bucket_name)
            # 尝试获取Bucket信息
            bucket_info = bucket.get_bucket_info()
            logger.debug(f"Bucket存在: {bucket_name}, 创建时间: {bucket_info.creation_date}")
            return True
        except NoSuchBucket:
            return False
        except OssError as e:
            logger.warning(f"检查Bucket存在性时OSS错误: {e}")
            return False
        except Exception as e:
            logger.warning(f"检查Bucket存在性时异常: {e}")
            return False

    def check_ecs_status(self, instance_id: str) -> Dict[str, Any]:
        """检查ECS实例状态"""
        try:
            logger.info(f"检查ECS实例状态: {instance_id}")
            describe_request = ecs_models.DescribeInstancesRequest(
                region_id=self.region_id,
                instance_ids=json.dumps([instance_id])
            )
            runtime = util_models.RuntimeOptions()
            response = self.ecs_client.describe_instances_with_options(describe_request, runtime)

            if response.body.instances and response.body.instances.instance:
                instance = response.body.instances.instance[0]
                return {
                    "status": instance.status,
                    "instance_id": instance.instance_id,
                    "instance_name": instance.instance_name,
                    "public_ip": instance.public_ip_address.ip_address if instance.public_ip_address else None
                }
            return {"status": "unknown"}

        except Exception as e:
            logger.error(f"检查ECS状态失败: {str(e)}")
            return {"status": "error", "message": str(e)}


# 工具实例
tool_kit = AliyunToolKit()


