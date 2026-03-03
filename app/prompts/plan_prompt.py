from app.prompts.base_prompt import BasePrompt

class PlanPrompt(BasePrompt):

    template = """
你是一名专业的AI训练规划专家。

用户信息：
- 用户类型: {{ user_type }}
- 当前能力等级: {{ level }}
- 训练目标: {{ goal }}

请生成结构化 JSON 格式训练方案：
{
  "summary": "",
  "modules": [],
  "difficulty": ""
}
"""

class GoalSummaryPrompt(BasePrompt):
    """
    根据多个任务的 life_desc，总结生成整体训练目标
    """

    template = """
你是一名专业的认知训练规划专家。

下面是用户近期训练任务的生活场景描述：

{{ life_desc_text }}

请基于以上信息，总结一个：

- 高度概括
- 专业表达
- 面向成长提升
- 不超过100字

的整体训练目标。

只输出训练目标文本，不要输出其他解释。
"""