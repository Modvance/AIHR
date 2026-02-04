"""
面试逻辑服务
处理面试追问、评估、结束等核心逻辑
"""

import json
import logging
import re
import time
from http import HTTPStatus
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from dashscope import Generation
import dashscope

from config import settings

logger = logging.getLogger(__name__)


class InterviewAction(Enum):
    """面试决策动作"""
    CONTINUE = "CONTINUE"
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass
class InterviewState:
    """面试状态"""
    topic: str = ""                          # 考察主题
    job_position: str = ""                   # 应聘岗位
    resume_summary: str = ""                 # 简历摘要
    conversation_history: List[Dict] = field(default_factory=list)  # 对话历史
    followup_count: int = 0                  # 追问次数
    current_score: int = 50                  # 当前评分
    is_started: bool = False                 # 是否已开始
    is_finished: bool = False                # 是否已结束
    final_result: str = ""                   # 最终结果（PASS/FAIL）
    final_assessment: str = ""               # 最终评估说明


@dataclass
class EvaluationResult:
    """评估结果"""
    action: InterviewAction
    current_score: int
    assessment: str


class InterviewService:
    """面试逻辑服务"""
    
    def __init__(self):
        self._setup_dashscope()
        self.state = InterviewState()
        
    def _setup_dashscope(self):
        """配置 DashScope API"""
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        
    def _get_followup_prompt(self) -> str:
        """获取面试官追问的 System Prompt"""
        return f"""你是一个经验丰富的技术面试官，正在进行一场真实的面试对话。
当前考察主题：{self.state.topic}
应聘岗位：{self.state.job_position}

【语音输出规范】
你的回复将通过语音合成播放，请遵循以下规范让语音更自然：
1. 使用自然口语化的表达
2. 适当使用逗号分隔长句，让语音有呼吸感
3. 不要使用表情符号、特殊符号、Markdown格式
4. 列举内容时用"第一、第二"或"首先、其次"，而不是数字列表
5. 语气要亲切自然，可以适当使用语气词如"嗯"、"那"、"好的"

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

    def _get_conclusion_prompt(self) -> str:
        """获取面试官结束语的 System Prompt"""
        return f"""你是一个技术面试官，现在需要结束这场面试，对候选人说一段简短的结束语。
当前考察主题：{self.state.topic}

【语音输出规范】
你的回复将通过语音合成播放，请遵循以下规范：
1. 使用自然口语化的表达
2. 适当使用逗号分隔，让语音有呼吸感
3. 不要使用表情符号、特殊符号
4. 语气亲切自然

【结束语要求】
- 如果是 PASS：简单肯定表现，告知通过，像正常聊天结束一样
- 如果是 FAIL：委婉指出不足，感谢参与，告知未通过
- 说话要自然，像真人一样
- 不要太客套，不要说"非常出色"、"非常感谢"这类过度客气的话

【示例风格】
- PASS："行，这块你掌握得挺扎实的，本轮面试通过了。"
- FAIL："嗯，这块基础还需要再加强一下，本轮先到这里吧。"

【重要提示】
- 直接输出结束语，不要输出 JSON 或标记
- 不要透露具体分数
"""

    def _get_evaluator_prompt(self) -> str:
        """获取评估候选人的 System Prompt"""
        return f"""你是一个面试评估专家，需要根据面试对话评估候选人的能力水平。
当前考察主题：{self.state.topic}

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
- **PASS**（合格）：候选人展示出扎实的知识和经验，能力评分 >= {settings.PASS_SCORE_THRESHOLD}
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

    def _format_conversation(self, messages: List[Dict]) -> str:
        """格式化对话历史，用于评估"""
        result = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "assistant":
                result.append(f"面试官: {content}")
            elif role == "user":
                result.append(f"候选人: {content}")
        return "\n".join(result)
        
    def start_interview(self, topic: str, job_position: str = "", resume_summary: str = "") -> str:
        """
        开始面试
        
        Args:
            topic: 考察主题
            job_position: 应聘岗位
            resume_summary: 简历摘要
            
        Returns:
            开场问题
        """
        self.state = InterviewState(
            topic=topic,
            job_position=job_position or "技术岗位",
            resume_summary=resume_summary,
            is_started=True
        )
        
        # 生成开场问题
        opening_question = f"你好，我们今天主要聊一下{topic}这块。请先简单介绍一下你对{topic}的理解和实际使用经验吧。"
        
        # 添加到对话历史
        self.state.conversation_history.append({
            "role": "assistant",
            "content": opening_question
        })
        
        logger.info(f"Interview started: topic={topic}, position={job_position}")
        return opening_question
        
    def evaluate_response(self, max_retries: int = 3) -> EvaluationResult:
        """
        评估候选人的回答
        
        Returns:
            评估结果
        """
        eval_messages = [
            {"role": "system", "content": self._get_evaluator_prompt()},
            {
                "role": "user", 
                "content": f"""请根据以下面试对话，评估候选人的能力水平。

【对话记录】
{self._format_conversation(self.state.conversation_history)}

【当前状态】
- 这是第 {self.state.followup_count}/{settings.MAX_FOLLOWUP_QUESTIONS} 次追问
- {"已达到最大追问次数，请给出最终判定 PASS 或 FAIL" if self.state.followup_count >= settings.MAX_FOLLOWUP_QUESTIONS else "请判断是继续追问还是给出最终判定"}

请给出你的评估结果（JSON格式）："""
            }
        ]
        
        for attempt in range(max_retries):
            try:
                response = Generation.call(
                    model=settings.LLM_MODEL,
                    messages=eval_messages,
                    result_format="message",
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                if response.status_code == 200:
                    content = response.output.choices[0].message.content
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group())
                        else:
                            raise
                    
                    action_str = data.get("action", "CONTINUE").upper()
                    action = InterviewAction[action_str] if action_str in InterviewAction.__members__ else InterviewAction.CONTINUE
                    
                    return EvaluationResult(
                        action=action,
                        current_score=data.get("current_score", 50),
                        assessment=data.get("assessment", "")
                    )
                else:
                    raise Exception(f"评估请求失败: code={response.code}, message={response.message}")
                    
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    return EvaluationResult(
                        action=InterviewAction.CONTINUE,
                        current_score=50,
                        assessment="评估失败，默认继续"
                    )
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Evaluation failed: {e}")
                    return EvaluationResult(
                        action=InterviewAction.CONTINUE,
                        current_score=50,
                        assessment="评估失败，默认继续"
                    )
        
        return EvaluationResult(
            action=InterviewAction.CONTINUE,
            current_score=50,
            assessment="评估失败，默认继续"
        )
        
    def generate_followup_stream(self, output_queue):
        """
        流式生成追问（同步方法，用于在线程池中执行）
        
        Args:
            output_queue: 输出队列，用于传递生成的文本片段
        """
        messages = [
            {"role": "system", "content": self._get_followup_prompt()},
        ] + self.state.conversation_history
        
        try:
            responses = Generation.call(
                model=settings.LLM_MODEL,
                messages=messages,
                result_format="message",
                temperature=0.3,
                stream=True,
                incremental_output=True,
            )
            
            content_parts = []
            for resp in responses:
                if resp.status_code == HTTPStatus.OK:
                    content = resp.output.choices[0].message.content
                    content_parts.append(content)
                    output_queue.put({'type': 'text', 'content': content})
                    
                    if resp.output.choices[0].finish_reason == "stop":
                        break
                else:
                    output_queue.put({
                        'type': 'error',
                        'content': f"请求失败: code={resp.code}, message={resp.message}"
                    })
                    return
            
            full_content = "".join(content_parts)
            self.state.conversation_history.append({
                "role": "assistant",
                "content": full_content
            })
            output_queue.put({'type': 'done'})
            
        except Exception as e:
            logger.error(f"Failed to generate followup: {e}")
            output_queue.put({'type': 'error', 'content': str(e)})
            
    def generate_conclusion_stream(self, action: str, assessment: str, output_queue):
        """
        流式生成结束语（同步方法，用于在线程池中执行）
        
        Args:
            action: PASS 或 FAIL
            assessment: 评估说明
            output_queue: 输出队列
        """
        messages = [
            {"role": "system", "content": self._get_conclusion_prompt()},
            {
                "role": "user",
                "content": f"""请根据以下信息生成面试结束语：

【评估结果】：{action}
【评估说明】：{assessment}

【对话回顾】
{self._format_conversation(self.state.conversation_history[-4:])}

请生成结束语："""
            }
        ]
        
        try:
            responses = Generation.call(
                model=settings.LLM_MODEL,
                messages=messages,
                result_format="message",
                temperature=0.3,
                stream=True,
                incremental_output=True,
            )
            
            content_parts = []
            for resp in responses:
                if resp.status_code == HTTPStatus.OK:
                    content = resp.output.choices[0].message.content
                    content_parts.append(content)
                    output_queue.put({'type': 'text', 'content': content})
                    
                    if resp.output.choices[0].finish_reason == "stop":
                        break
                else:
                    output_queue.put({
                        'type': 'error',
                        'content': f"请求失败: code={resp.code}, message={resp.message}"
                    })
                    return
            
            full_content = "".join(content_parts)
            self.state.conversation_history.append({
                "role": "assistant",
                "content": full_content
            })
            output_queue.put({'type': 'done'})
            
        except Exception as e:
            logger.error(f"Failed to generate conclusion: {e}")
            output_queue.put({'type': 'error', 'content': str(e)})
            
    def process_candidate_response(self, response: str) -> Tuple[str, Optional[EvaluationResult]]:
        """
        处理候选人的回答，决定下一步动作
        
        Args:
            response: 候选人的回答
            
        Returns:
            (action, evaluation_result)
            action: "followup" | "pass" | "fail"
            evaluation_result: 评估结果（仅当面试结束时返回）
        """
        if not self.state.is_started or self.state.is_finished:
            return "error", None
            
        # 添加候选人回答到对话历史
        self.state.conversation_history.append({
            "role": "user",
            "content": response
        })
        self.state.followup_count += 1
        
        # 评估
        evaluation = self.evaluate_response()
        self.state.current_score = evaluation.current_score
        
        logger.info(f"Evaluation: score={evaluation.current_score}, action={evaluation.action.value}, count={self.state.followup_count}")
        
        # 决策逻辑
        reached_min = self.state.followup_count >= settings.MIN_FOLLOWUP_QUESTIONS
        reached_max = self.state.followup_count >= settings.MAX_FOLLOWUP_QUESTIONS
        
        if reached_min and (evaluation.action == InterviewAction.PASS or 
                           (reached_max and evaluation.current_score >= settings.PASS_SCORE_THRESHOLD)):
            # 通过
            self.state.is_finished = True
            self.state.final_result = "PASS"
            self.state.final_assessment = evaluation.assessment
            return "pass", evaluation
            
        elif evaluation.action == InterviewAction.FAIL or \
             (reached_max and evaluation.current_score < settings.PASS_SCORE_THRESHOLD):
            # 不通过
            self.state.is_finished = True
            self.state.final_result = "FAIL"
            self.state.final_assessment = evaluation.assessment
            return "fail", evaluation
            
        else:
            # 继续追问
            return "followup", evaluation
            
    def get_interview_result(self) -> Dict:
        """获取面试结果"""
        return {
            "is_finished": self.state.is_finished,
            "result": self.state.final_result,
            "score": self.state.current_score,
            "assessment": self.state.final_assessment,
            "topic": self.state.topic,
            "followup_count": self.state.followup_count
        }
        
    def reset(self):
        """重置面试状态"""
        self.state = InterviewState()
        logger.info("Interview state reset")
