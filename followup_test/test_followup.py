import os
import time
import json
from http import HTTPStatus
from dashscope import Generation
import dashscope
from dotenv import load_dotenv
import ssl

# 加载 .env 里的 Key
load_dotenv()

# 配置 API Key（参考 llm_stream_test.py 的方式）
try:
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("未找到 API Key，请在 .env 文件中设置API_KEY")
    dashscope.api_key = api_key
except KeyError:
    raise ValueError("请设置环境变量API_KEY")

# ==================== 配置参数 ====================
MIN_FOLLOWUP_QUESTIONS = 3  # 单个问题最少追问次数
MAX_FOLLOWUP_QUESTIONS = 5  # 单个问题最大追问次数
INTERVIEW_TOPIC = "Transformer架构理解"  # 当前考察主题
MODEL_NAME = "qwen-plus"  # 使用的模型

# --- 面试官追问的 System Prompt（流式输出，自然语言） ---
INTERVIEWER_FOLLOWUP_PROMPT = f"""你是一个经验丰富的技术面试官，正在进行一场真实的面试对话。
当前考察主题：{INTERVIEW_TOPIC}

【对话风格要求】
你必须像一个真实的人类面试官那样自然地交流，而不是机械地"追问"。

禁止使用的表达方式：
- "我来追问一个关键点"
- "我再深入追问"
- "期待你从XXX层面的拆解"
- "让我们聊聊"
- 任何显得刻意、生硬的过渡语

推荐的自然表达方式：
- "嗯嗯，那你刚才说的XXX，具体是怎么实现的呢？"
- "好的，这块我了解了。那XXX呢？"
- "你提到XXX，能展开说说吗？"
- "嗯，回答的不错。那如果遇到XXX情况，你会怎么处理呢？"
- "行，那我想再问一下..."
- 直接抛出问题，不需要铺垫

【追问策略】
1. 回答太笼统 -> 追问具体细节
2. 回答有漏洞 -> 直接指出并追问
3. 回答很好 -> 顺着往深处问，或者换个角度

【重要提示】
- 直接输出你要说的话，像正常聊天一样
- 简洁有力，不要啰嗦
- 可以简短肯定对方的回答，但不要过度夸奖
"""

# --- 面试官结束语的 System Prompt（根据评估结果生成结束语） ---
INTERVIEWER_CONCLUSION_PROMPT = f"""你是一个技术面试官，现在需要结束这场面试，对候选人说一段简短的结束语。
当前考察主题：{INTERVIEW_TOPIC}

【结束语要求】
- 如果是 PASS：简单肯定表现，告知通过，像正常聊天结束一样
- 如果是 FAIL：委婉指出不足，感谢参与，告知未通过
- 说话要自然，像真人一样，2-3句话即可
- 不要太客套，不要说"非常出色"、"非常感谢"这类过度客气的话

【示例风格】
- PASS："行，这块你掌握得挺扎实的，本轮面试通过了。"
- FAIL："嗯，这块基础还需要再加强一下，本轮先到这里吧。"

【重要提示】
- 直接输出结束语，不要输出 JSON 或标记
- 不要透露具体分数
"""

# --- 评估候选人的 System Prompt（JSON 输出） ---
EVALUATOR_PROMPT = f"""你是一个面试评估专家，需要根据面试对话评估候选人的能力水平。
当前考察主题：{INTERVIEW_TOPIC}

【评估维度】
1. **基础概念**：是否理解核心概念和原理
2. **技术细节**：能否说出具体的实现细节、参数、配置等
3. **实践经验**：是否有真实的项目经验，而非纸上谈兵
4. **逻辑能力**：回答是否逻辑自洽，能否应对追问

【能力评级标准】
- 优秀(90-100)：回答全面、有深度，有真实经验，能应对深入追问
- 良好(70-89)：基本概念清晰，有一定经验，但某些细节不够深入
- 及格(60-69)：了解基础知识，但缺乏深度和实践经验
- 不及格(0-59)：概念模糊、逻辑混乱、或明显在编造

【决策规则】
- **PASS**（合格）：候选人展示出扎实的知识和经验，能力评分 >= 70
- **FAIL**（不合格）：以下任一情况立即判定FAIL：
  - 候选人明确表示"不知道"、"不了解"、"没用过"等
  - 连续2次回答都很空洞、抓不住重点
  - 逻辑明显矛盾或在编造
  - 能力评分 < 60
- **CONTINUE**（继续追问）：还需要更多信息来判断

【重要提示】
- 不要无限追问！一旦能够做出判断，立即给出 PASS 或 FAIL
- 如果候选人已经展示出足够的能力，不必追问到最大次数

【输出格式】
你必须严格按照以下JSON格式输出，不要输出任何其他内容：
{{
    "action": "CONTINUE 或 PASS 或 FAIL",
    "current_score": 0-100的能力评分,
    "assessment": "简短的评估说明（为什么做出这个决策）"
}}
"""

def stream_response(messages, prefix="面试官 (AI): ", max_retries=3):
    """
    流式获取 AI 回复的通用函数
    
    Args:
        messages: 对话消息列表
        prefix: 输出前缀
        max_retries: 最大重试次数，默认3次
    
    Returns:
        完整的回复内容
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # 发起流式请求
            responses = Generation.call(
                model=MODEL_NAME,
                messages=messages,
                result_format="message",
                temperature=0.3,
                stream=True,
                incremental_output=True,  # 增量输出，性能更佳
            )
            
            # 处理流式响应
            content_parts = []
            print(f"\n{prefix}", end="", flush=True)
            
            for resp in responses:
                if resp.status_code == HTTPStatus.OK:
                    content = resp.output.choices[0].message.content
                    print(content, end="", flush=True)
                    content_parts.append(content)
                    
                    # 检查是否是最后一个包
                    if resp.output.choices[0].finish_reason == "stop":
                        print()  # 换行
                        break
                else:
                    # 处理错误情况
                    raise Exception(f"请求失败: code={resp.code}, message={resp.message}")
            
            return "".join(content_parts)
            
        except (ssl.SSLError, ConnectionError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"\n⚠️  网络连接错误，{wait_time}秒后重试 (第 {attempt + 1}/{max_retries} 次)...")
                time.sleep(wait_time)
            else:
                raise Exception(f"网络连接失败（已重试 {max_retries} 次）: {str(e)}")
        except Exception as e:
            raise
    
    raise Exception(f"未知错误: {last_error}")


def get_followup_question(conversation_history):
    """
    获取面试官的追问
    """
    messages = [
        {"role": "system", "content": INTERVIEWER_FOLLOWUP_PROMPT},
    ] + conversation_history
    
    return stream_response(messages)


def get_conclusion(conversation_history, action, assessment):
    """
    获取面试官的结束语
    
    Args:
        conversation_history: 对话历史
        action: PASS 或 FAIL
        assessment: 评估说明
    """
    messages = [
        {"role": "system", "content": INTERVIEWER_CONCLUSION_PROMPT},
        {
            "role": "user",
            "content": f"""请根据以下信息生成面试结束语：

【评估结果】：{action}
【评估说明】：{assessment}

【对话回顾】
{format_conversation(conversation_history[-4:])}  # 只取最近几轮对话作为参考

请生成结束语："""
        }
    ]
    
    return stream_response(messages)


def get_evaluation(conversation_history, followup_count, max_retries=3):
    """
    获取对候选人的评估结果（JSON格式）
    
    Args:
        conversation_history: 完整的对话历史（不包含system prompt）
        followup_count: 当前追问次数
        max_retries: 最大重试次数
    
    Returns:
        评估结果字典，包含 action, current_score, assessment
    """
    # 构建评估请求的消息
    eval_messages = [
        {"role": "system", "content": EVALUATOR_PROMPT},
        {
            "role": "user", 
            "content": f"""请根据以下面试对话，评估候选人的能力水平。

【对话记录】
{format_conversation(conversation_history)}

【当前状态】
- 这是第 {followup_count}/{MAX_FOLLOWUP_QUESTIONS} 次追问
- {"已达到最大追问次数，请给出最终判定 PASS 或 FAIL" if followup_count >= MAX_FOLLOWUP_QUESTIONS else "请判断是继续追问还是给出最终判定"}

请给出你的评估结果（JSON格式）："""
        }
    ]
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = Generation.call(
                model=MODEL_NAME,
                messages=eval_messages,
                result_format="message",
                temperature=0.1,  # 评估时用更低的温度，保证稳定性
                response_format={"type": "json_object"}
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # 尝试提取JSON
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                    raise
            else:
                raise Exception(f"评估请求失败: code={response.code}, message={response.message}")
                
        except (ssl.SSLError, ConnectionError, OSError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise Exception(f"网络连接失败: {str(e)}")
        except json.JSONDecodeError:
            last_error = "JSON解析错误"
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                # 返回默认的继续追问结果
                return {"action": "CONTINUE", "current_score": 50, "assessment": "评估失败，默认继续"}
        except Exception as e:
            raise
    
    raise Exception(f"未知错误: {last_error}")


def format_conversation(messages):
    """
    格式化对话历史，用于评估
    """
    result = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "assistant":
            result.append(f"面试官: {content}")
        elif role == "user":
            result.append(f"候选人: {content}")
    return "\n".join(result)

def print_result_banner(action, final_score, assessment):
    """
    打印面试结果横幅（面试结束后展示给面试者）
    
    Args:
        action: PASS 或 FAIL
        final_score: 最终评分
        assessment: 评估说明
    """
    print("\n" + "=" * 60)
    if action == "PASS":
        print("🎉 >>> 面试结束：本轮通过 <<< 🎉")
    else:
        print("📋 >>> 面试结束：本轮未通过 <<< 📋")
    
    print(f"📊 最终评分: {final_score}/100")
    print(f"📝 评估说明: {assessment}")
    print("=" * 60)


def start_simulation(debug=False):
    """
    开始模拟面试追问流程（流式输出版本）
    
    Args:
        debug: 是否显示调试信息（内部评分等），默认 False
    """
    # 开场问题
    opening_question = f"面试开始。关于{INTERVIEW_TOPIC}，请先介绍一下你对它的理解和实际使用经验。"
    
    # 对话历史记录（用于生成回复和评估）
    conversation_history = [
        {"role": "assistant", "content": opening_question}
    ]

    # 追问计数器
    followup_count = 0

    print("=" * 60)
    print("AI 面试官追问功能测试")
    print(f"考察主题: {INTERVIEW_TOPIC}")
    if debug:
        print(f"[调试模式] 追问次数: {MIN_FOLLOWUP_QUESTIONS}~{MAX_FOLLOWUP_QUESTIONS} 轮")
    print("=" * 60)
    print(f"\n面试官 (AI): {opening_question}")
    print("\n提示：输入 'exit' 或 'quit' 退出测试\n")

    while True:
        # 1. 获取用户回答
        user_input = input("\n求职者 (你): ")
        if user_input.lower() in ["exit", "quit"]:
            print("\n测试手动结束。")
            break

        # 2. 更新对话历史
        conversation_history.append({"role": "user", "content": user_input})
        followup_count += 1

        try:
            # 3. 【先评估】获取评估结果
            if debug:
                print("  [评估中...]", end="", flush=True)
            
            evaluation = get_evaluation(conversation_history, followup_count)
            
            action = evaluation.get("action", "CONTINUE").upper()
            current_score = evaluation.get("current_score", 50)
            assessment = evaluation.get("assessment", "")
            
            # 调试模式显示评估信息
            if debug:
                print(f"\r  [调试] 评分: {current_score}/100 | 决策: {action} | 追问: {followup_count}/{MAX_FOLLOWUP_QUESTIONS}")

            # 4. 【再决定回复】根据评估结果决定下一步
            # 注意：即使评估为 PASS，也要满足最少追问次数才能结束
            
            # 检查是否满足最少追问次数
            reached_min = followup_count >= MIN_FOLLOWUP_QUESTIONS
            reached_max = followup_count >= MAX_FOLLOWUP_QUESTIONS
            
            if reached_min and (action == "PASS" or (reached_max and current_score >= 70)):
                # 满足最少追问次数，且评估通过 -> 结束
                conclusion = get_conclusion(conversation_history, "PASS", assessment)
                conversation_history.append({"role": "assistant", "content": conclusion})
                print_result_banner("PASS", current_score, assessment)
                break
                
            elif action == "FAIL" or (reached_max and current_score < 70):
                # FAIL 可以提前结束（不受最少追问限制，因为明显不合格没必要继续）
                # 或者达到最大次数且分数不及格
                conclusion = get_conclusion(conversation_history, "FAIL", assessment)
                conversation_history.append({"role": "assistant", "content": conclusion})
                print_result_banner("FAIL", current_score, assessment)
                break
                
            else:
                # 继续追问（包括：未达到最少次数时的 PASS，或者 CONTINUE）
                if debug and action == "PASS" and not reached_min:
                    print(f"  [调试] 评估为 PASS 但未满足最少 {MIN_FOLLOWUP_QUESTIONS} 轮，继续追问")
                followup = get_followup_question(conversation_history)
                conversation_history.append({"role": "assistant", "content": followup})
                
        except ValueError as e:
            print(f"\n❌ 配置错误：{e}")
            break
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ 错误：{error_msg}")
            
            if "网络连接失败" in error_msg or "SSL" in error_msg or "Connection" in error_msg:
                retry = input("\n是否继续测试？(y/n): ").lower()
                if retry != 'y':
                    break
            else:
                # 非网络错误，回滚消息并允许重试
                conversation_history.pop()
                followup_count -= 1
                print("请重新输入您的回答。")


if __name__ == "__main__":
    import sys
    # 支持 --debug 或 -d 参数开启调试模式
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    start_simulation(debug=debug_mode)
