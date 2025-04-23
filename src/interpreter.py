import os
import json
import fcntl
import asyncio
from typing import Dict, List, Any, Optional

class HexagramInterpreter:
    """
    卦象解释器，负责提供卦象的名称、爻辞、解释等内容
    """
    
    def __init__(self, config: Dict, base_dir=None):
        self.config = config
        self.base_dir = base_dir if base_dir else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.hexagrams_data = {}  # 卦象静态数据
        self.data_loaded = False
    
    async def load_data(self):
        """加载卦象静态数据"""
        # 确保data目录存在
        data_dir = os.path.join(self.base_dir, "data/static")
        os.makedirs(data_dir, exist_ok=True)
        
        data_file = os.path.join(data_dir, "hexagrams.json")
        
        # 检查数据文件是否存在，不存在则创建基础数据
        if not os.path.exists(data_file):
            await self._create_default_data(data_file)
            
        # 加载数据
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                # 获取文件锁
                fcntl.flock(f, fcntl.LOCK_SH)
                self.hexagrams_data = json.load(f)
                # 释放文件锁
                fcntl.flock(f, fcntl.LOCK_UN)
                
            self.data_loaded = True
        except Exception as e:
            print(f"加载卦象数据失败: {str(e)}")
            self.hexagrams_data = {}
            
    async def _create_default_data(self, file_path: str):
        """创建默认的卦象数据文件"""
        # 这里只提供几个示例卦象，完整实现需要所有64卦的数据
        default_data = {
            "1": {  # 乾为天
                "name": "乾为天",
                "gua_ci": "元亨利贞。",
                "description": "乾卦代表天，象征刚健、积极进取、自强不息。",
                "lines": [
                    "初九：潜龙勿用。",
                    "九二：见龙在田，利见大人。",
                    "九三：君子终日乾乾，夕惕若厉，无咎。",
                    "九四：或跃在渊，无咎。",
                    "九五：飞龙在天，利见大人。",
                    "上九：亢龙有悔。",
                    "用九：见群龙无首，吉。"
                ]
            },
            "2": {  # 坤为地
                "name": "坤为地",
                "gua_ci": "元亨，利牝马之贞。君子有攸往，先迷后得主，利西南得朋，东北丧朋。安贞吉。",
                "description": "坤卦代表地，象征包容、顺从、柔顺。",
                "lines": [
                    "初六：履霜，坚冰至。",
                    "六二：直、方、大，不习无不利。",
                    "六三：含章可贞。或从王事，无成有终。",
                    "六四：括囊，无咎无誉。",
                    "六五：黄裳，元吉。",
                    "上六：龙战于野，其血玄黄。",
                    "用六：利永贞。"
                ]
            },
            # ... 其他卦象数据
        }
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            # 获取文件锁
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(default_data, f, ensure_ascii=False, indent=2)
            # 释放文件锁
            fcntl.flock(f, fcntl.LOCK_UN)
            
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
        使用大语言模型生成更个性化的卦象解释
        """
        if not self.config["llm"]["enabled"] or not self.config["llm"]["api_key"]:
            return {}
            
        try:
            # 构建提示词
            prompt = self._build_llm_prompt(question, original_name, changed_name, moving_lines)
            
            api_type = self.config["llm"]["api_type"]
            
            if api_type == "openai":
                return await self._call_openai(prompt)
            elif api_type == "deepseek":
                return await self._call_deepseek(prompt)
            elif api_type == "qianfan":
                return await self._call_qianfan(prompt)
            elif api_type == "azure":
                return await self._call_azure(prompt)
            else:
                raise ValueError(f"不支持的API类型: {api_type}")
                
        except Exception as e:
            print(f"调用大语言模型API出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return {}
            
    async def _call_openai(self, prompt: str) -> Dict[str, str]:
        """调用OpenAI API"""
        import aiohttp
        
        api_key = self.config["llm"]["api_key"]
        api_base = self.config["llm"]["api_base"]
        model = self.config["llm"]["model"]
        
        if not api_base:
            api_base = "https://api.openai.com/v1"
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # 解析内容
                    overall_meaning = ""
                    fortune = "平"
                    advice = ""

                    # 更灵活的解析方法
                    lines = content.split("\n")
                    section = ""  # 记录当前解析的部分
                    section_content = []  # 收集当前部分的内容行

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # 识别新的部分标题
                        new_section = None
                        if line.startswith("1.") or line.startswith("一、") or "整体意义" in line or "解读" in line:
                            new_section = "meaning"
                        elif line.startswith("2.") or line.startswith("二、") or "吉凶判断" in line or "吉凶" in line:
                            new_section = "fortune"
                        elif line.startswith("3.") or line.startswith("三、") or "建议" in line or "行动建议" in line:
                            new_section = "advice"
                            
                        # 如果发现新部分标题，处理之前收集的内容
                        if new_section or (section and section_content and line.startswith("4.")):
                            if section == "meaning" and section_content:
                                overall_meaning = "\n".join(section_content).strip()
                            elif section == "fortune" and section_content:
                                fortune_text = "\n".join(section_content).strip()
                                # 更灵活地提取吉凶判断
                                if "吉" in fortune_text and "凶" not in fortune_text:
                                    fortune = "吉"
                                elif "凶" in fortune_text:
                                    fortune = "凶"
                                else:
                                    fortune = "平"
                            elif section == "advice" and section_content:
                                advice = "\n".join(section_content).strip()
                                
                            # 重置收集器，开始新部分
                            section = new_section
                            section_content = []
                            
                        # 如果已经确定了部分类型，且当前行不是部分标题，则收集内容
                        if section and (not new_section):
                            # 处理行内冒号
                            parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                            if len(parts) > 1 and (("整体意义" in parts[0]) or ("吉凶" in parts[0]) or ("建议" in parts[0])):
                                section_content.append(parts[1].strip())
                            else:
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
                        else:
                            fortune = "平"
                    elif section == "advice" and section_content:
                        advice = "\n".join(section_content).strip()

                    # 如果内容解析不成功，尝试直接从全文中提取
                    if not overall_meaning:
                        # 尝试直接分割整个内容
                        content_lower = content.lower()
                        if "整体意义" in content_lower or "解读" in content_lower:
                            overall_meaning = content.strip()[:200]  # 取前200字作为整体意义
                        
                    return {
                        "overall_meaning": overall_meaning or "解释生成失败",
                        "fortune": fortune,
                        "advice": advice or "暂无具体建议"
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"API调用失败: {response.status} - {error_text}")
                    
    async def _call_qianfan(self, prompt: str) -> Dict[str, str]:
        """调用百度千帆API"""
        try:
            from qianfan import ChatCompletion
            
            api_key = self.config["llm"]["api_key"]
            api_secret = self.config["llm"].get("api_secret", "")
            model = self.config["llm"]["model"]
            
            # 初始化客户端
            chat = ChatCompletion(api_key=api_key, secret_key=api_secret)
            
            # 调用API
            response = await chat.do(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response["result"]
            
            # 解析内容
            overall_meaning = ""
            fortune = "平"
            advice = ""
            
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("1.") or "整体意义" in line or "解读" in line:
                    parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                    if len(parts) > 1:
                        overall_meaning = parts[1].strip()
                elif line.startswith("2.") or "吉凶判断" in line:
                    parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                    if len(parts) > 1:
                        text = parts[1].strip()
                        if "吉" in text:
                            fortune = "吉"
                        elif "凶" in text:
                            fortune = "凶"
                        else:
                            fortune = "平"
                elif line.startswith("3.") or "建议" in line:
                    parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                    if len(parts) > 1:
                        advice = parts[1].strip()
            
            return {
                "overall_meaning": overall_meaning or "解释生成失败",
                "fortune": fortune,
                "advice": advice or "暂无具体建议"
            }
            
        except Exception as e:
            print(f"调用千帆API失败: {str(e)}")
            return {}

    async def _call_azure(self, prompt: str) -> Dict[str, str]:
        """调用Azure OpenAI API"""
        import aiohttp
        
        api_key = self.config["llm"]["api_key"]
        api_base = self.config["llm"]["api_base"]
        model = self.config["llm"]["model"]
        
        # Azure需要完整的API基础URL
        if not api_base or not api_base.startswith("https://"):
            raise ValueError("Azure OpenAI需要完整的API基础URL")
        
        deployment_name = model
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/openai/deployments/{deployment_name}/chat/completions?api-version=2023-05-15",
                json={
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                },
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # 解析内容
                    overall_meaning = ""
                    fortune = "平"
                    advice = ""
                    
                    lines = content.split("\n")
                    for line in lines:
                        line = line.strip()
                        if line.startswith("1.") or "整体意义" in line:
                            parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                            if len(parts) > 1:
                                overall_meaning = parts[1].strip()
                        elif line.startswith("2.") or "吉凶判断" in line:
                            parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                            if len(parts) > 1:
                                text = parts[1].strip()
                                if "吉" in text:
                                    fortune = "吉"
                                elif "凶" in text:
                                    fortune = "凶"
                                else:
                                    fortune = "平"
                        elif line.startswith("3.") or "建议" in line:
                            parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                            if len(parts) > 1:
                                advice = parts[1].strip()
                    
                    return {
                        "overall_meaning": overall_meaning or "解释生成失败",
                        "fortune": fortune,
                        "advice": advice or "暂无具体建议"
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"API调用失败: {response.status} - {error_text}")
                    
    async def _call_deepseek(self, prompt: str) -> Dict[str, str]:
        """调用DeepSeek API（与OpenAI API兼容）"""
        import aiohttp
        
        api_key = self.config["llm"]["api_key"]
        api_base = self.config["llm"]["api_base"]
        model = self.config["llm"]["model"]
        
        if not api_base:
            api_base = "https://api.deepseek.com/v1"
            
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_base}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # 记录原始返回内容以便调试
                    # print(f"DeepSeek API 返回内容: {content}")
                    
                    # 解析内容
                    overall_meaning = ""
                    fortune = "平"
                    advice = ""
                    
                    # 首先尝试按段落解析
                    paragraphs = content.split("\n\n")
                    
                    # 如果有多个段落，尝试按段落结构解析
                    if len(paragraphs) >= 3:
                        # 假设第一段是整体意义，第二段是吉凶，第三段是建议
                        overall_meaning = paragraphs[0].strip()
                        
                        # 第二段中查找吉凶关键词
                        if "吉" in paragraphs[1] and "凶" not in paragraphs[1]:
                            fortune = "吉"
                        elif "凶" in paragraphs[1]:
                            fortune = "凶"
                            
                        # 第三段作为建议
                        if len(paragraphs) >= 3:
                            advice = paragraphs[2].strip()
                    
                    # 如果按段落解析不成功，尝试按行解析
                    if not overall_meaning:
                        lines = content.split("\n")
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                                
                            # 查找包含整体意义/解读的行
                            if "整体意义" in line or "解读" in line or line.startswith("1."):
                                parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                                if len(parts) > 1:
                                    overall_meaning = parts[1].strip()
                                else:
                                    # 如果没有冒号，可能整行都是内容
                                    next_idx = lines.index(line) + 1 if line in lines else -1
                                    if next_idx > 0 and next_idx < len(lines) and not (
                                        lines[next_idx].startswith("2.") or "吉凶" in lines[next_idx]
                                    ):
                                        overall_meaning = lines[next_idx].strip()
                            
                            # 查找包含吉凶判断的行
                            if "吉凶" in line or line.startswith("2."):
                                parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                                if len(parts) > 1:
                                    text = parts[1].strip()
                                    if "吉" in text and "凶" not in text:
                                        fortune = "吉"
                                    elif "凶" in text:
                                        fortune = "凶"
                                else:
                                    # 如果没有冒号，查找下一行
                                    next_idx = lines.index(line) + 1 if line in lines else -1
                                    if next_idx > 0 and next_idx < len(lines):
                                        text = lines[next_idx].strip()
                                        if "吉" in text and "凶" not in text:
                                            fortune = "吉"
                                        elif "凶" in text:
                                            fortune = "凶"
                            
                            # 查找包含建议的行
                            if "建议" in line or line.startswith("3."):
                                parts = line.split(":", 1) if ":" in line else line.split("：", 1)
                                if len(parts) > 1:
                                    advice = parts[1].strip()
                                else:
                                    # 如果没有冒号，可能建议在下一行
                                    next_idx = lines.index(line) + 1 if line in lines else -1
                                    if next_idx > 0 and next_idx < len(lines):
                                        advice = lines[next_idx].strip()
                    
                    # 如果仍然无法解析，尝试从整个文本提取关键信息
                    if not overall_meaning:
                        # 尝试提取前200个字符作为整体意义
                        overall_meaning = content[:200].strip()
                        
                        # 检查整个文本中的吉凶关键词
                        if "吉" in content and "凶" not in content:
                            fortune = "吉"
                        elif "凶" in content:
                            fortune = "凶"
                    
                    # 最终返回结果
                    result = {
                        "overall_meaning": overall_meaning or "解释生成失败",
                        "fortune": fortune,
                        "advice": advice or "暂无具体建议"
                    }
                    
                    return result
                else:
                    error_text = await response.text()
                    print(f"DeepSeek API调用失败: 状态码 {response.status}")
                    raise Exception(f"API调用失败: {response.status} - {error_text}")
                    
    def _build_llm_prompt(self, question: str, original_name: str, 
                         changed_name: Optional[str], moving_lines: List[str]) -> str:
        """构建提示词"""
        prompt = [
            f"请基于以下易经卦象信息，对问题「{question}」进行解读:",
            f"原卦: {original_name}"
        ]
        
        if changed_name:
            prompt.append(f"变卦: {changed_name}")
            
        moving_text = [line for line in moving_lines if line]
        if moving_text:
            prompt.append("动爻:")
            for line in moving_text:
                prompt.append(f"- {line}")
                
        prompt.append("\n请提供:")
        prompt.append("1. 整体意义解读（200字以内）")
        prompt.append("2. 吉凶判断（用一个词：吉/凶/平）")
        prompt.append("3. 针对问题的具体建议（100字以内）")
        
        return "\n".join(prompt)
