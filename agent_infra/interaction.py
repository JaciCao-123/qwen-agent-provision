import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(__file__))


def main():
    """命令行交互入口"""
    print("=== 云基础设施自动化Agent ===")
    print("支持的功能: 创建ECS实例、创建OSS Bucket、检查资源状态")
    print("输入 'quit' 或 'exit' 退出程序")
    print("-" * 50)

    from agent_core import infra_agent

    while True:
        try:
            user_input = input("\n用户: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("再见！")
                break

            if not user_input:
                continue

            # 处理用户请求
            response = infra_agent.process_request(user_input)
            print(f"\nAgent: {response}")

        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n发生错误: {str(e)}")


if __name__ == "__main__":
    main()