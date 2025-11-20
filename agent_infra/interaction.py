import sys
import os
import logging

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


# def setup_logging():
#     """设置日志配置"""
#     logging.basicConfig(
#         level=logging.INFO,
#         format='%(asctime)s - %(levelname)s - %(message)s',
#         handlers=[
#             logging.StreamHandler(),
#             logging.FileHandler('interaction.log', encoding='utf-8')
#         ]
#     )


def main():
    """命令行交互入口"""
    # setup_logging()
    # logger = logging.getLogger(__name__)

    print("=== 云基础设施自动化Agent ===")
    print("支持的功能:")
    print("  - 创建ECS实例")
    print("  - 创建OSS Bucket")
    print("  - 检查资源状态")
    print("输入 'quit' 或 'exit' 退出程序")
    print("-" * 50)

    try:
        from agent_core import infra_agent
        #logger.info("Agent模块导入成功")
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保以下文件存在:")
        print("  - agent_core.py")
        print("  - tools.py")
        print("  - config.py")
        print("  - models.py")
        return
    except Exception as e:
        print(f"❌ 初始化Agent时出错: {e}")
        return

    print("✅ Agent初始化成功，可以开始对话")

    while True:
        try:
            user_input = input("\n👤 用户: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("👋 再见！")
                break

            if not user_input:
                continue

            # 处理用户请求
            print("🔄 处理中...")
            response = infra_agent.process_request(user_input)
            print(f"\n🤖 Agent: {response}")

        except KeyboardInterrupt:
            print("\n\n⏹️  程序被用户中断")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")
           # logger.error("处理用户请求时出错: %s", e)


if __name__ == "__main__":
    main()
