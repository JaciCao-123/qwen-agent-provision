from typing import Optional, Dict, Any
from enum import Enum

class ResourceType(str, Enum):
    ECS = "ecs"
    OSS = "oss"

class ResourceStatus(str, Enum):
    PENDING = "pending"
    CREATING = "creating"
    SUCCESS = "success"
    FAILED = "failed"

# 使用简单的字典而不是Pydantic模型来避免兼容性问题
ECS_DEFAULT_CONFIG = {
    "instance_type": "ecs.g6.large",
    "image_id": "centos_7_9_x64_20G_alibase_20231219.vhd",
    "instance_name": "agent-created-ecs",
    "system_disk_size": 40
}

OSS_DEFAULT_CONFIG = {
    "storage_class": "Standard",
    "acl": "private"
}