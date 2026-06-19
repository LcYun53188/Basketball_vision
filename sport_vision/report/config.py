from __future__ import annotations

# 报告生成模块本地配置
LLM_MODEL_NAME = "gemini-3.5-flash"
EXPORT_REPORT_FORMAT = "json"  # json, markdown
DEFAULT_COACHING_PROMPT = """
你是一位专业的篮球教练。基于以下结构化训练数据，生成一份详细的训练评估报告：
- 运动员: {athlete_name} (位置: {position}, 惯用手: {dominant_hand})
- 动作类型: {action_summary}
- 技术指标平均值与标准区间比对:
{metrics_comparison}
- 进球命中率与得分价值: {shooting_summary}

请生成包括以下部分的内容：
1. 训练表现总体评估；
2. 主要技术缺陷分析；
3. 个性化改进建议及针对性训练计划；
4. 运动损伤防范及风险提示。
"""
