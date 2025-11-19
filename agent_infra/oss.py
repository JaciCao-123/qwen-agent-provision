import os
import oss2
from pathlib import Path
from dotenv import load_dotenv
from config import load_config
from typing import Optional


cfg = load_config()

def create_oss_bucket(
        region: str,
        bucket_name: str,
        storage_class='Standard',  # 可选值：'Standard'|'IA'|'Archive'
        public_access=False,  # 是否允许公共读取，默认私有
):
    """
    在阿里云上创建一个新的OSS存储空间（Bucket）。

    参数:
    - region: 字符串，例如 'cn-hangzhou'，表示OSS所在的区域。
    - bucket_name: 字符串，新创建的bucket的名字。
    - storage_class: 字符串，存储类型，默认为标准存储('Standard')。
    - public_access: 布尔值，是否开启公共读取权限，默认关闭。

    返回:
    - 新创建bucket的名称。

    异常:
    - ValueError: 当AK或SK未设置时抛出。
    - oss2.exceptions.OssError: 当创建过程中发生错误时抛出。
    """
    access_key_id = cfg["access_key_id"]
    access_key_secret = cfg["access_key_secret"]

    if not (access_key_id and access_key_secret):
        raise ValueError("请设置环境变量 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET")

    auth = oss2.Auth(access_key_id, access_key_secret)
    endpoint = f"oss-{region}.aliyuncs.com"
    service = oss2.Service(auth, endpoint)

    print(f"正在连接到 {endpoint}...")

    try:
        # 创建bucket
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        bucket.create_bucket(oss2.BUCKET_ACL_PUBLIC_READ if public_access else oss2.BUCKET_ACL_PRIVATE,
                             oss2.models.BucketCreateConfig(storage_class))

        print(f"✅ 成功创建bucket '{bucket_name}'.")

        return bucket_name

    except oss2.exceptions.OssError as e:
        print(f"❌ 创建bucket失败: {e}")
        raise


# 使用示例
if __name__ == '__main__':
    created_bucket = create_oss_bucket(
        region="cn-hangzhou",
        bucket_name="jaci-new-bucket-2025",  # 确保此名字在全球范围内唯一
        storage_class='Standard',
        public_access=False
    )
    print(f"已创建bucket: {created_bucket}")