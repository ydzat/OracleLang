import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from filelock import FileLock


class HexagramInterpreter:
    """
    卦象解释器，负责提供卦象的名称、爻辞、解释等内容
    """

    def __init__(self, config: Dict, base_dir=None, plugin=None, logger: Optional[logging.Logger] = None):
        self.config = config
        self.base_dir = base_dir if base_dir else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugin = plugin  # Plugin instance for accessing LangBot APIs
        self.hexagrams_data = {}  # 卦象静态数据
        self.data_loaded = False
        self.logger = logger or logging.getLogger(__name__)
    
    async def load_data(self):
        """加载卦象静态数据"""
        try:
            # 确保data目录存在
            data_dir = os.path.join(self.base_dir, "data/static")
            os.makedirs(data_dir, exist_ok=True)

            data_file = os.path.join(data_dir, "hexagrams.json")

            # 检查数据文件是否存在，不存在则创建基础数据
            if not os.path.exists(data_file):
                self.logger.info(f"Hexagram data file not found, creating default data: {data_file}")
                await self._create_default_data(data_file)

            self.logger.debug(f"Loading hexagram data from: {data_file}")

            # 加载数据（使用跨平台文件锁）
            lock_file = data_file + ".lock"
            lock = FileLock(lock_file, timeout=10)

            with lock:
                with open(data_file, "r", encoding="utf-8") as f:
                    self.hexagrams_data = json.load(f)

            self.data_loaded = True
            self.logger.info(f"Loaded {len(self.hexagrams_data)} hexagrams data")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse hexagram data JSON: {str(e)}", exc_info=True)
            self.hexagrams_data = {}
            raise

        except Exception as e:
            self.logger.error(f"Failed to load hexagram data: {str(e)}", exc_info=True)
            self.hexagrams_data = {}
            raise
            
    async def _create_default_data(self, file_path: str):
        """创建默认的卦象数据文件 - 包含完整的64卦数据"""
        # 完整的64卦数据
        default_data = self._get_complete_hexagram_data()

        # 写入文件（使用跨平台文件锁）
        try:
            lock_file = file_path + ".lock"
            lock = FileLock(lock_file, timeout=10)

            with lock:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Created default hexagram data file with {len(default_data)} hexagrams")
        except Exception as e:
            self.logger.error(f"Failed to create default hexagram data: {str(e)}", exc_info=True)
            raise

    def _get_complete_hexagram_data(self) -> Dict:
        """获取完整的64卦数据"""
        # 尝试从hexagrams_complete.json读取完整数据
        complete_data_file = os.path.join(self.base_dir, "data/static/hexagrams_complete.json")

        if os.path.exists(complete_data_file):
            try:
                with open(complete_data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if len(data) == 64:
                        self.logger.info("Loaded complete hexagram data from hexagrams_complete.json")
                        return data
            except Exception as e:
                self.logger.warning(f"Failed to load complete data file: {str(e)}")

        # 如果无法读取完整数据文件，返回基础的64卦框架
        # 这确保即使在最坏的情况下，系统也能正常运行
        self.logger.warning("Using minimal hexagram data structure")
        return self._get_minimal_hexagram_data()

    def _get_minimal_hexagram_data(self) -> Dict:
        """获取最小的64卦数据框架（用于备用）"""
        from .data_constants import HEXAGRAM_NAMES

        minimal_data = {}
        for i in range(1, 65):
            hexagram_name = HEXAGRAM_NAMES.get(i, f"第{i}卦")
            minimal_data[str(i)] = {
                "name": hexagram_name,
                "gua_ci": "卦辞待补充。",
                "description": f"{hexagram_name}的详细解释待补充。",
                "lines": [
                    "初爻：爻辞待补充。",
                    "二爻：爻辞待补充。",
                    "三爻：爻辞待补充。",
                    "四爻：爻辞待补充。",
                    "五爻：爻辞待补充。",
                    "上爻：爻辞待补充。"
                ]
            }

        return minimal_data
            
    async def interpret(self, hexagram_original: int, hexagram_changed: int, 
                       moving: List[int], question: str, use_llm: bool = False) -> Dict[str, Any]:
        """
        解释卦象
        
        参数:
            hexagram_original: 原卦编号(1-64)
            hexagram_changed: 变卦编号(1-64)
            moving: 动爻列表
            question: 用户原始问题
            use_llm: 是否使用大语言模型
            
        返回:
            卦象解释信息的字典
        """
        # 确保数据已加载
        if not self.data_loaded:
            await self.load_data()
            
        # 转换为字符串键
        orig_key = str(hexagram_original)
        changed_key = str(hexagram_changed)
        
        # 获取原卦信息
        original_data = self.hexagrams_data.get(orig_key, {
            "name": f"未知卦象({hexagram_original})",
            "gua_ci": "无卦辞。",
            "description": "暂无描述。",
            "lines": ["无爻辞。"] * 7
        })
        
        # 获取变卦信息
        changed_data = self.hexagrams_data.get(changed_key, {
            "name": f"未知卦象({hexagram_changed})",
            "gua_ci": "无卦辞。",
            "description": "暂无描述。",
            "lines": ["无爻辞。"] * 7
        })
        
        # 获取动爻的爻辞
        moving_lines_meaning = []
        has_moving = False
        for i in range(6):
            if moving[i] == 1:
                has_moving = True
                # 爻辞从下往上排列，第一爻为初爻
                line_index = i
                if line_index < len(original_data["lines"]):
                    moving_lines_meaning.append(original_data["lines"][line_index])
                else:
                    moving_lines_meaning.append("无爻辞。")
            else:
                moving_lines_meaning.append("")
                
        # 生成综合解释
        overall_meaning = self._generate_overall_meaning(original_data, changed_data if has_moving else None)
        
        # 如果配置了使用大语言模型，则调用API获取更详细的解释
        llm_interpretation = {}

        if use_llm and question:
            
            llm_interpretation = await self._get_llm_interpretation(
                question, original_data["name"], changed_data["name"] if has_moving else None, 
                moving_lines_meaning
            )

            
        # 组合解释
        result = {
            "original": original_data,
            "changed": changed_data if has_moving else original_data,
            "moving_lines_meaning": moving_lines_meaning,
            "overall_meaning": llm_interpretation.get("overall_meaning", overall_meaning),
            "fortune": llm_interpretation.get("fortune", self._determine_fortune(original_data, changed_data if has_moving else None)),
            "advice": llm_interpretation.get("advice", self._generate_advice(original_data, changed_data if has_moving else None))
        }
        
        return result
    
    def _generate_overall_meaning(self, original_data: Dict, changed_data: Optional[Dict]) -> str:
        """生成综合解释文字"""
        if not changed_data:
            return f"{original_data['name']}：{original_data.get('description', '代表着一种状态或情境。')}"\
                   f"卦辞：{original_data.get('gua_ci', '无')}"
        else:
            return f"{original_data['name']}变{changed_data['name']}：从{original_data.get('description', '一种状态')}"\
                   f"变化为{changed_data.get('description', '另一种状态')}。这表示情况正在发生转变。"
    
    def _determine_fortune(self, original_data: Dict, changed_data: Optional[Dict]) -> str:
        """确定吉凶"""
        # 简单实现，实际可能需要更复杂的规则
        if "吉" in original_data.get("gua_ci", ""):
            return "吉"
        elif changed_data and "吉" in changed_data.get("gua_ci", ""):
            return "吉"
        elif "凶" in original_data.get("gua_ci", ""):
            return "凶"
        else:
            return "平"
            
    def _generate_advice(self, original_data: Dict, changed_data: Optional[Dict]) -> str:
        """生成建议"""
        # 简单实现，实际可能需要更复杂的规则
        if not changed_data:
            return f"请参考{original_data['name']}卦的卦辞进行决策。"
        else:
            return f"正处于从{original_data['name']}到{changed_data['name']}的变化过程中，建议关注变化的动向，顺势而为。"
            
    async def _get_llm_interpretation(self, question: str, original_name: str,
                                    changed_name: Optional[str], moving_lines: List[str]) -> Dict[str, str]:
        """
        使用 LangBot 的 LLM API 生成更个性化的卦象解释
        """
        if not self.config["llm"]["enabled"]:
            return {}

        if not self.plugin:
            self.logger.warning("Plugin instance not available, cannot call LLM")
            return {}

        try:
            # 获取可用的 LLM 模型列表
            # 注意：get_llm_models() 实际返回 list[dict]，每个 dict 包含模型信息（包括 uuid 字段）
            llm_models = await self.plugin.get_llm_models()
            if not llm_models:
                self.logger.warning("No LLM models configured in LangBot")
                return {}

            # 使用第一个可用模型的 UUID
            model_uuid = llm_models[0]['uuid']
            self.logger.debug(f"Using LLM model: {model_uuid}")

            # 构建提示词
            prompt = self._build_llm_prompt(question, original_name, changed_name, moving_lines)

            # 导入 LangBot 消息类型
            from langbot_plugin.api.entities.builtin.provider import message as provider_message

            # 调用 LangBot LLM API
            llm_message = await self.plugin.invoke_llm(
                llm_model_uuid=model_uuid,
                messages=[provider_message.Message(role="user", content=prompt)],
                funcs=[],
                extra_args={},
            )

            # 获取响应文本
            response_text = llm_message.content

            # 解析响应
            return self._parse_llm_response(response_text)

        except Exception as e:
            self.logger.error(f"LLM API call failed: {str(e)}", exc_info=True)
            return {}

    def _build_llm_prompt(self, question: str, original_name: str,
                         changed_name: Optional[str], moving_lines: List[str]) -> str:
        """构建LLM提示词，要求返回JSON格式"""
        prompt = f"""请根据易经卦象为用户提供解读。

用户问题：{question}

卦象信息：
- 本卦：{original_name}
"""

        if changed_name and changed_name != original_name:
            prompt += f"- 变卦：{changed_name}\n"

        if any(moving_lines):
            prompt += "- 动爻：\n"
            for i, line in enumerate(moving_lines):
                if line:
                    prompt += f"  {line}\n"

        prompt += """
请以JSON格式返回解读结果，格式如下：

{
  "overall_meaning": "结合卦象和用户问题的整体解读（不超过150字）",
  "fortune": "吉凶判断（只能是：吉、凶、平 三者之一）",
  "advice": "具体的行动建议（不超过100字）"
}

请确保返回的是有效的JSON格式，不要包含其他文字说明。
"""
        return prompt

    def _parse_llm_response(self, response_text: str) -> Dict[str, str]:
        """
        统一解析LLM响应

        优先尝试JSON解析，失败则回退到文本解析
        """
        if not response_text:
            return {}

        # 尝试JSON解析
        try:
            # 清理可能的markdown代码块标记
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            # 尝试解析JSON
            data = json.loads(cleaned_text)

            # 验证必需字段
            if "overall_meaning" in data and "fortune" in data and "advice" in data:
                # 规范化fortune字段
                fortune = data["fortune"].strip()
                if "吉" in fortune and "凶" not in fortune:
                    fortune = "吉"
                elif "凶" in fortune:
                    fortune = "凶"
                else:
                    fortune = "平"

                self.logger.info("Successfully parsed LLM response as JSON")
                return {
                    "overall_meaning": data["overall_meaning"].strip(),
                    "fortune": fortune,
                    "advice": data["advice"].strip()
                }
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"JSON parsing failed, falling back to text parsing: {str(e)}")

        # 回退到文本解析
        return self._parse_text_response(response_text)

    def _parse_text_response(self, content: str) -> Dict[str, str]:
        """
        文本解析方法（作为JSON解析失败时的备用方案）

        支持多种格式：
        - 1. 2. 3. 格式
        - 一、二、三、格式
        - 整体意义：吉凶判断：建议：格式
        """
        overall_meaning = ""
        fortune = "平"
        advice = ""

        lines = content.split("\n")
        section = ""
        section_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 识别新的部分标题
            new_section = None
            line_content = None  # 标题行中可能包含的内容

            if line.startswith("1.") or line.startswith("一、") or "整体意义" in line or "解读" in line:
                new_section = "meaning"
                # 尝试从标题行提取内容
                parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                if len(parts) > 1:
                    line_content = parts[1].strip()
            elif line.startswith("2.") or line.startswith("二、") or "吉凶判断" in line or "吉凶" in line:
                new_section = "fortune"
                parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                if len(parts) > 1:
                    line_content = parts[1].strip()
            elif line.startswith("3.") or line.startswith("三、") or "建议" in line or "行动建议" in line:
                new_section = "advice"
                parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                if len(parts) > 1:
                    line_content = parts[1].strip()

            # 处理之前收集的内容
            if new_section:
                if section == "meaning" and section_content:
                    overall_meaning = "\n".join(section_content).strip()
                elif section == "fortune" and section_content:
                    fortune_text = "\n".join(section_content).strip()
                    if "吉" in fortune_text and "凶" not in fortune_text:
                        fortune = "吉"
                    elif "凶" in fortune_text:
                        fortune = "凶"
                elif section == "advice" and section_content:
                    advice = "\n".join(section_content).strip()

                section = new_section
                section_content = []

                # 如果标题行包含内容，添加到新section
                if line_content:
                    section_content.append(line_content)

            # 收集内容（非标题行）
            elif section:
                section_content.append(line)

        # 处理最后一个部分
        if section == "meaning" and section_content:
            overall_meaning = "\n".join(section_content).strip()
        elif section == "fortune" and section_content:
            fortune_text = "\n".join(section_content).strip()
            if "吉" in fortune_text and "凶" not in fortune_text:
                fortune = "吉"
            elif "凶" in fortune_text:
                fortune = "凶"
        elif section == "advice" and section_content:
            advice = "\n".join(section_content).strip()

        self.logger.info("Parsed LLM response using text parsing fallback")
        return {
            "overall_meaning": overall_meaning or "解释生成失败",
            "fortune": fortune,
            "advice": advice or "暂无具体建议"
        }


