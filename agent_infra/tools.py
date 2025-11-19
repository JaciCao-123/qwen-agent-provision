import json
import uuid
import logging
from typing import Dict, Any
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_oss20190517.client import Client as OssClient
from alibabacloud_oss20190517 import models as oss_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

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

        # 初始化OSS客户端
        oss_config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            endpoint=f'oss.{self.region_id}.aliyuncs.com'
        )
        self.oss_client = OssClient(oss_config)

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
        """创建OSS Bucket"""
        request_id = str(uuid.uuid4())
        try:
            bucket_name = oss_config.get("bucket_name")
            if not bucket_name:
                return {
                    "request_id": request_id,
                    "resource_type": "oss",
                    "status": "failed",
                    "message": "Bucket名称是必填参数"
                }

            logger.info(f"开始创建OSS Bucket: {bucket_name}")

            # 构建创建Bucket请求
            create_request = oss_models.CreateBucketRequest(
                bucket=bucket_name,
                storage_class=oss_config.get("storage_class", "Standard"),
                acl=oss_config.get("acl", "private")
            )

            response = self.oss_client.create_bucket(create_request)

            logger.info(f"OSS Bucket创建成功: {bucket_name}")

            return {
                "request_id": request_id,
                "resource_type": "oss",
                "resource_id": bucket_name,
                "status": "success",
                "message": "OSS Bucket创建成功",
                "details": {
                    "bucket_name": bucket_name,
                    "storage_class": oss_config.get("storage_class", "Standard"),
                    "acl": oss_config.get("acl", "private"),
                    "region": self.region_id
                }
            }

        except Exception as e:
            logger.error(f"创建OSS Bucket失败: {str(e)}")
            return {
                "request_id": request_id,
                "resource_type": "oss",
                "status": "failed",
                "message": f"OSS Bucket创建失败: {str(e)}"
            }

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