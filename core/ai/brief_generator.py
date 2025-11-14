"""
AI简报生成服务
使用GLM API生成文章简报
"""
import os
import json
import re
from datetime import datetime
from typing import Dict, Optional, List, Any
import httpx
from core.config import cfg
from core.print import print_info, print_error, print_success, print_warning

class BriefGenerator:
    """AI简报生成器"""
    
    def __init__(self):
        self.api_key = os.getenv('GLM_API_KEY') or cfg.get('ai.glm_api_key', '')
        self.api_url = cfg.get('ai.glm_api_url', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')
        self.model = cfg.get('ai.glm_model', 'GLM-4.5-Flash')
        self.timeout = cfg.get('ai.timeout', 60)
        self.max_retries = cfg.get('ai.max_retries', 3)
        
        if not self.api_key:
            print_warning("GLM_API_KEY未配置，AI简报功能将无法使用")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一位专业的内容分析师，擅长以结构化方式总结中文文章，帮助读者快速理解价值。
生成内容需严格遵循指定 JSON Schema，不得输出额外解释或 Markdown。"""
    
    def _build_user_prompt(self, article: Dict[str, Any]) -> str:
        """构建用户提示词"""
        title = article.get('title', '未知标题')
        author = article.get('author') or article.get('mp_name', '未知')
        publish_time = article.get('publish_time') or article.get('created_at')
        content = article.get('content', '')
        
        # 处理发布时间
        if isinstance(publish_time, int):
            try:
                publish_date = datetime.fromtimestamp(publish_time)
                publish_iso = publish_date.isoformat()
            except:
                publish_iso = datetime.now().isoformat()
        elif isinstance(publish_time, str):
            publish_iso = publish_time
        else:
            publish_iso = datetime.now().isoformat()
        
        # 处理内容
        content_status = "完整" if content else "缺失"
        if not content:
            content_snippet = "正文缺失：无可用文字"
            truncate_notice = ""
        else:
            # 限制内容长度（24000字符）
            max_length = 24000
            if len(content) > max_length:
                content_snippet = content[:max_length]
                truncate_notice = f"\n\n[注意：正文已截断，原始长度{len(content)}字符，仅显示前{max_length}字符]"
            else:
                content_snippet = content
                truncate_notice = ""
        
        prompt = f"""请为以下文章生成结构化简报（AI Brief），输出 JSON，符合 Schema v3.0：

{{
  "meta": {{
    "version": "3.0",
    "language": "zh-CN",
    "generated_at": <ISO8601 时间戳，可选>,
    "tags": <可选的字符串数组>,
    "confidence": <可选，0-1 之间数值或 high/medium/low>
  }},
  "summary": "对全文的简介总结，长度不限，直接陈述文章主要观点",
  "highlights": [
    {{
      "title": "核心重点标题，简洁聚焦",
      "description": "对该重点的说明，解释具体内容、原因或影响"
    }}
  ]
}}

生成要求：
1. "summary" 段落需覆盖文章核心观点，不做字数限制。
2. "highlights" 至少 1 条，最多 6 条，每条描述需解释重点
3. 不得输出除上述 JSON 结构以外的内容，字段顺序和名称必须一致。
4. 保持客观、中立，不插入主观评价；若正文缺失或信息不足，请明确说明，不得虚构细节。
5. 仅根据提供的正文内容回答，不引用外部知识，不猜测或编造事实。

文章标题：{title}
文章作者：{author}
发布时间：{publish_iso}
正文完整度：{content_status}
文章内容：
{content_snippet}{truncate_notice}"""
        
        return prompt
    
    def _parse_confidence(self, value: Any) -> Optional[float]:
        """解析置信度值"""
        if isinstance(value, (int, float)):
            return float(value) if 0 <= float(value) <= 1 else None
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ['高', 'high']:
                return 0.9
            elif value_lower in ['中', 'medium']:
                return 0.7
            elif value_lower in ['低', 'low']:
                return 0.5
            else:
                try:
                    return float(value) if 0 <= float(value) <= 1 else None
                except:
                    return None
        return None
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """解析日期值"""
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value)
            except:
                return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                try:
                    return datetime.fromtimestamp(float(value))
                except:
                    return None
        return None
    
    def _parse_response(self, response_data: Dict, article_key: str) -> Dict[str, Any]:
        """解析GLM API响应"""
        try:
            content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not content:
                raise ValueError("API响应中未找到内容")
            
            # 清理JSON响应（移除可能的markdown代码块标记）
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            # 解析JSON
            data = json.loads(content)
            
            # 提取元数据
            meta = data.get('meta', {})
            
            # 处理highlights
            highlights = data.get('highlights', [])
            if not isinstance(highlights, list):
                highlights = []
            
            # 转换为标准格式
            highlights_list = []
            for h in highlights:
                if isinstance(h, dict):
                    highlights_list.append({
                        'title': h.get('title', ''),
                        'detail': h.get('description') or h.get('detail', '')
                    })
            
            # 构建返回数据
            result = {
                'article_key': article_key,
                'model': self.model,
                'summary': data.get('summary', ''),
                'highlights': highlights_list,
                'version': meta.get('version', '3.0'),
                'language': meta.get('language', 'zh-CN'),
                'tags': meta.get('tags', []),
                'confidence': self._parse_confidence(meta.get('confidence')),
                'generated_at': self._parse_date(meta.get('generated_at')) or datetime.utcnow(),
            }
            
            return result
            
        except json.JSONDecodeError as e:
            print_error(f"JSON解析失败: {e}")
            print_error(f"响应内容: {content[:500]}")
            raise ValueError(f"JSON解析失败: {str(e)}")
        except Exception as e:
            print_error(f"响应解析失败: {e}")
            raise
    
    async def generate(self, article: Dict[str, Any], article_key: str) -> Dict[str, Any]:
        """
        生成文章简报
        
        Args:
            article: 文章数据字典，包含title, content, author等字段
            article_key: 文章唯一标识
            
        Returns:
            简报数据字典
            
        Raises:
            ValueError: API调用失败或响应解析失败
            Exception: 网络错误或其他异常
        """
        if not self.api_key:
            raise ValueError("GLM_API_KEY未配置")
        
        # 构建请求
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(article)
        
        request_data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 重试机制
        last_error = None
        for attempt in range(self.max_retries):
            try:
                print_info(f"正在生成简报 (尝试 {attempt + 1}/{self.max_retries}): {article.get('title', '未知')[:50]}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.api_url,
                        json=request_data,
                        headers=headers
                    )
                    
                    # 处理HTTP错误
                    if response.status_code == 400:
                        error_msg = f"API请求参数错误: {response.text}"
                        print_error(error_msg)
                        raise ValueError(error_msg)
                    elif response.status_code == 429:
                        if attempt < self.max_retries - 1:
                            wait_time = (attempt + 1) * 2  # 指数退避
                            print_warning(f"速率限制，等待 {wait_time} 秒后重试...")
                            import asyncio
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise ValueError(f"速率限制，已达到最大重试次数")
                    elif response.status_code != 200:
                        error_msg = f"API调用失败: HTTP {response.status_code}, {response.text}"
                        print_error(error_msg)
                        raise ValueError(error_msg)
                    
                    # 解析响应
                    try:
                        response_data = response.json()
                    except json.JSONDecodeError as e:
                        error_msg = f"API响应JSON解析失败: {response.text[:200]}"
                        print_error(error_msg)
                        raise ValueError(error_msg)
                    
                    result = self._parse_response(response_data, article_key)
                    
                    print_success(f"简报生成成功: {article.get('title', '未知')[:50]}")
                    return result
                    
            except httpx.TimeoutException:
                last_error = f"请求超时 (超时时间: {self.timeout}秒)"
                print_warning(f"{last_error}，尝试 {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
            except httpx.RequestError as e:
                last_error = f"网络请求错误: {str(e)}"
                print_warning(f"{last_error}，尝试 {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
            except ValueError as e:
                # 业务逻辑错误，不重试
                raise
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                print_error(f"{last_error}，尝试 {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2)
                    continue
        
        # 所有重试都失败
        raise Exception(f"简报生成失败，已重试 {self.max_retries} 次: {last_error}")

