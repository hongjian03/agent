 # -*- coding: utf-8 -*-
import pandas as pd
import re
import logging
import os
from typing import List, Dict, Tuple, Any, Optional
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('operation_points_extractor')

class OperationPointsExtractor:
    """
    从用户输入中提取国家、留学类别和专业标签，然后从Excel表格中查询对应的操作要点
    """
    
    def __init__(self, excel_file_path: str):
        """
        初始化提取器
        
        Args:
            excel_file_path: Excel表格文件路径
        """
        self.excel_file_path = excel_file_path
        self._load_excel()
        self._initialize_tag_dictionaries()
        
    def _load_excel(self):
        """加载Excel表格数据"""
        try:
            self._df = pd.read_excel(self.excel_file_path)
            logger.info(f"成功加载Excel文件: {self.excel_file_path}")
        except Exception as e:
            logger.error(f"加载Excel文件出错: {str(e)}")
            self._df = None
            
    def _initialize_tag_dictionaries(self):
        """初始化标签字典"""
        # 国家标签
        self.country_tags = {
            "中国大陆", "中国澳门", "中国香港", "丹麦", "俄罗斯", "加拿大",
            "匈牙利", "奥地利", "德国", "意大利", "挪威", "新加坡", 
            "新西兰", "日本", "比利时", "法国", "泰国", "澳大利亚",
            "爱尔兰", "瑞典", "瑞士", "美国", "芬兰", "英国",
            "荷兰", "西班牙", "韩国", "马来西亚"
        }
        
        # 留学类别标签
        self.study_level_tags = {
            "预科/语言/文凭课程", "K12", "学士学位", "硕士学位（授课/研究型）", "博士学位"
        }
        
        # 专业标签 (精简版)
        self.major_tags = {
            "计算机科学/工程", "电气/电子工程", "数据科学", "信息科学/信息学",
            "土木工程", "环境工程", "机械工程", "航空航天工程", "船舶及石油工程", "材料工程",
            "工业工程", "化学/化工", "物理", "地球科学", "数学/统计", "金融数学/精算",
            "生物科学", "医学", "公共卫生", "药学与制药", "农业与动物科学",
            "经济学", "金融", "会计", "商业管理", "市场营销",
            "法学", "政策管理", "教育学", "心理学", "社会学", 
            "哲学", "历史", "语言与文学", "传媒", "艺术", "设计",
            "音乐", "表演艺术", "建筑学"
        }
        
        # 同义词映射
        self.country_synonyms = {
            "中国": "中国大陆",
            "澳门": "中国澳门",
            "香港": "中国香港",
            "美": "美国",
            "英": "英国",
            "澳": "澳大利亚",
            "加": "加拿大",
            "新": "新加坡",  # 可能需要区分新加坡和新西兰
        }
        
        self.study_level_synonyms = {
            "预科": "预科/语言/文凭课程",
            "语言课程": "预科/语言/文凭课程",
            "文凭课程": "预科/语言/文凭课程",
            "中小学": "K12",
            "高中": "K12",
            "初中": "K12",
            "小学": "K12",
            "本科": "学士学位",
            "学士": "学士学位",
            "硕士": "硕士学位（授课/研究型）",
            "研究生": "硕士学位（授课/研究型）",
            "博士": "博士学位",
            "PhD": "博士学位"
        }
            
    def extract_tags_from_text(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        从文本中提取国家、留学类别和专业标签
        
        Args:
            text: 输入文本
            
        Returns:
            包含国家、留学类别和专业标签的元组
        """
        country_tag = None
        study_level_tag = None
        major_tag = None
        
        # 查找国家标签
        for country in self.country_tags:
            if country in text:
                country_tag = country
                break
                
        # 如果没有找到精确匹配，尝试同义词
        if not country_tag:
            for synonym, country in self.country_synonyms.items():
                if synonym in text:
                    country_tag = country
                    break
        
        # 查找留学类别标签
        for study_level in self.study_level_tags:
            if study_level in text:
                study_level_tag = study_level
                break
                
        # 如果没有找到精确匹配，尝试同义词
        if not study_level_tag:
            for synonym, study_level in self.study_level_synonyms.items():
                if synonym in text:
                    study_level_tag = study_level
                    break
        
        # 查找专业标签
        for major in self.major_tags:
            if major in text:
                major_tag = major
                break
                
        logger.info(f"从文本中提取的标签: 国家={country_tag}, 留学类别={study_level_tag}, 专业={major_tag}")
        return country_tag, study_level_tag, major_tag
            
    def get_operation_points(self, text: str) -> str:
        """
        从文本中提取标签并查询对应的操作要点
        
        Args:
            text: 输入文本
            
        Returns:
            操作要点
        """
        try:
            # 从文本中提取标签
            country_tag, study_level_tag, major_tag = self.extract_tags_from_text(text)
            
            if self._df is None:
                return "Excel文件未成功加载，无法查询操作要点"
            
            # 创建结果列表
            matched_rows = []
            
            # 遍历DataFrame的每一行
            for idx, row in self._df.iterrows():
                match_country = self._is_match(row['国家标签'], country_tag)
                match_study_level = self._is_match(row['留学类别标签'], study_level_tag)
                match_major = self._is_match(row['专业标签'], major_tag)
                
                # 记录每行的匹配结果
                logger.debug(f"行 {idx}: 国家匹配={match_country}, 留学类别匹配={match_study_level}, 专业匹配={match_major}")
                
                # 如果三个标签都匹配，则添加到结果中
                if match_country and match_study_level and match_major:
                    matched_rows.append(row)
                    logger.info(f"找到匹配行: {idx}, 内容类型: {row.get('输出内容类型', 'N/A')}")
            
            # 记录匹配结果
            logger.info(f"匹配到 {len(matched_rows)} 条记录")
            
            # 如果没有匹配的行，返回提示信息
            if not matched_rows:
                no_match_msg = f"未找到匹配的操作要点：国家={country_tag}, 留学类别={study_level_tag}, 专业={major_tag}"
                logger.warning(no_match_msg)
                return no_match_msg
            
            # 按输出内容类型分类结果
            content_by_type = {}
            for idx, row in enumerate(matched_rows):
                content_type = row['输出内容类型']
                content = row['输出内容']
                
                # 记录内容值，帮助调试
                is_na_content = pd.isna(content)
                content_str = str(content) if not is_na_content else "NaN"
                logger.debug(f"处理内容: idx={idx}, 类型={content_type}, 内容={content_str[:50]}{'...' if len(content_str) > 50 else ''}, 是否为NaN={is_na_content}")
                
                # 跳过NaN值或空内容
                if pd.isna(content) or content == "" or content == "nan":
                    logger.info(f"跳过空内容: idx={idx}, 类型={content_type}")
                    continue
                
                # 确保content_type不是NaN
                if pd.isna(content_type):
                    logger.info(f"内容类型为NaN，使用默认类型: idx={idx}")
                    content_type = "未分类内容"
                
                if content_type not in content_by_type:
                    content_by_type[content_type] = []
                
                content_by_type[content_type].append(content)
            
            # 记录分类结果
            logger.info(f"内容分类: {list(content_by_type.keys())}")
            
            # 格式化输出
            result = []
            for content_type, contents in content_by_type.items():
                # 跳过空列表
                if not contents:
                    continue
                
                result.append(f"**{content_type}**：")
                for i, content in enumerate(contents, 1):
                    # 再次检查确保不输出NaN值
                    if not pd.isna(content) and content != "nan" and content.strip() != "":
                        result.append(f"{i}. {content}")
                
                # 只有在添加了内容后才添加空行
                if len(result) > 0 and result[-1].startswith(f"{len(contents)}. "):
                    result.append("")  # 添加空行分隔不同类型
            
            response = "\n".join(result)
            
            # 如果没有有效内容，提供明确的反馈
            if not response.strip():
                response = "找到匹配的记录，但所有内容均为空值。请检查Excel文件中的数据。"
            
            # 记录输出结果摘要
            logger.info(f"输出结果摘要: {response[:100]}...")
            
            return response
            
        except Exception as e:
            error_msg = f"查询过程中出错: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return error_msg
    
    def _is_match(self, table_value, input_value):
        """
        检查输入值是否与表格中的值匹配
        
        Args:
            table_value: 表格中的值
            input_value: 输入的值
            
        Returns:
            是否匹配
        """
        # 如果表格中的值为空，则默认匹配
        if pd.isna(table_value) or table_value == "":
            return True
        
        # 如果输入值为空或NaN，但表格值不为空，不匹配
        if input_value is None or (isinstance(input_value, str) and (input_value.strip() == "" or input_value.lower() == "nan")):
            return False
        
        # 确保输入值是字符串
        input_value_str = str(input_value).strip()
        
        # 将表格值按逗号分割成列表，并确保每个值都被清理
        table_values = [v.strip() for v in str(table_value).split(',') if v.strip() and v.strip().lower() != "nan"]
        
        # 如果表格值列表为空（可能全是NaN或空字符串），默认匹配
        if not table_values:
            return True
        
        # 记录匹配过程
        logger.debug(f"匹配检查: 表格值={table_values}, 输入值={input_value_str}")
        
        # 检查输入值是否在表格值列表中，忽略大小写
        return any(v.lower() == input_value_str.lower() for v in table_values)