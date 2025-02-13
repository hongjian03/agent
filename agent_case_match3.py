from crewai import Agent, Task, Crew
from crewai_tools import SerperDevTool, CSVSearchTool
#from JinaReaderTool import JinaReaderTool
from langchain_openai import ChatOpenAI
import os
import json
import warnings
warnings.filterwarnings("ignore")
import logging
import asyncio
import re
from typing import Any
logging.getLogger('streamlit.runtime.scriptrunner.magic_funcs').setLevel(logging.ERROR)
# 或者完全禁用所有警告
logging.getLogger('streamlit').setLevel(logging.ERROR)
import time
#from embedchain.models.data_type import DataType




from pathlib import Path
from crewai_tools import SerperDevTool
import json
import os
import requests
import traceback

class CustomSerperDevTool(SerperDevTool):
    n_results: int = 3  # 添加类型注解

    def _run(self, **kwargs: Any) -> Any:
        search_query = kwargs.get('search_query')
        if search_query is None:
            search_query = kwargs.get('query')

        payload = json.dumps({"q": search_query})
        headers = {
            'X-API-KEY': os.environ['SERPER_API_KEY'],
            'content-type': 'application/json'
        }
        response = requests.request("POST", self.search_url, headers=headers, data=payload)
        results = response.json()
        
        if 'organic' in results:
            # 只取前3个结果
            results = results['organic'][:self.n_results]  # 限制结果数量
            string = []
            for result in results:
                try:
                    string.append('\n'.join([
                        f"Title: {result['title']}",
                        f"Link: {result['link']}",
                        f"Snippet: {result['snippet']}",
                        "---"
                    ]))
                except KeyError:
                    next

            content = '\n'.join(string)
            return f"\nSearch results: {content}\n"
        else:
            return results




def load_config():
    """加载配置文件"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 配置文件路径
    json_path = os.path.join(current_dir, 'api_config2.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"配置文件不存在: {json_path}\n请确保api_config2.json文件位于正确位置")
    except json.JSONDecodeError:
        raise ValueError(f"配置文件格式错误: {json_path}\n请确保是有效的JSON格式")

def update_environment_variables(config):
    os.environ['SERPER_API_KEY'] = config['SERPER_API_KEY']
    os.environ['OPENAI_API_KEY'] = config['OPENAI_API_KEY']
    os.environ['OPENAI_API_BASE'] = config['OPENAI_API_BASE']
    os.environ['OPENAI_MODEL_NAME'] = config['OPENAI_MODEL_NAME']
    os.environ['DEEPSEEK_API_KEY'] = config['DEEPSEEK_API_KEY']
    os.environ['GROQ_API_KEY'] = config['GROQ_API_KEY']
    os.environ['COHERE_API_KEY'] = config['COHERE_API_KEY']


config = load_config()
update_environment_variables(config)


def initialize_config():
    config = load_config()
    update_environment_variables(config)






llm_search_professor = ChatOpenAI(
    model="google/gemini-flash-1.5-8b",
    api_key=config['OPENAI_API_KEY'],
    base_url="https://openrouter.ai/api/v1"
)

deepseek_api_key=os.getenv('DEEPSEEK_API_KEY')
groq_api_key=os.getenv('GROQ_API_KEY')

llm_groq = ChatOpenAI(
    model="llama3-groq-70b-8192-tool-use-preview",
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1"
)

llm_deepseek = ChatOpenAI(
    model="deepseek-chat",
    api_key=deepseek_api_key,
    base_url="https://api.deepseek.com"
)


openai_api_key=os.getenv('OPENAI_API_KEY')


# 创建 ChatOpenAI 实例
default_llm = ChatOpenAI(
    model=config['OPENAI_MODEL_NAME'],
    api_key=openai_api_key,
    base_url="https://openrouter.ai/api/v1",
    model_kwargs={
        "extra_headers": {
            "HTTP-Referer": "https://www.appadvisor.com",  # Optional, for including your app on openrouter.ai rankings.
            "X-Title": "application_advisor"  # Optional. Shows in rankings on openrouter.ai.
        }
    }
)


# 初始化工具
search_tool = CustomSerperDevTool()  # 使用自定义的工具类而不是直接使用 SerperDevTool
#jina_tool = JinaReaderTool()






TAG_SYSTEM = {
    "countries": [
        "中国大陆", "中国澳门", "中国香港", "丹麦", "俄罗斯", "加拿大",
        "匈牙利", "奥地利", "德国", "意大利", "挪威", "新加坡", 
        "新西兰", "日本", "比利时", "法国", "泰国", "澳大利亚",
        "爱尔兰", "瑞典", "瑞士", "美国", "芬兰", "英国",
        "荷兰", "西班牙", "韩国", "马来西亚"
    ],
    
    
    
    "majors": [
        "计算机与信息系统", "土木与环境", "生物与医学", "机械与工程",
        "数学与统计", "法学", "国际关系与政策", "心理学",
        "商科管理", "金融与会计", "经济学",
        "传媒与新闻", "语言与文学", "人文学科", "教育学", "艺术学"
    ],
    

}
# 添加新的配置类来管理提示词模板
class PromptTemplates:
    def __init__(self):
        self._templates = {
            'requirement_analyst': """
            你是一位经验丰富的留学需求分析专家，擅长：
            1. 深入理解学生的申请背景和目标
            2. 识别关键需求点和潜在挑战
            3. 系统性思维和结构化分析
            4. 准确把握服务重点和风险点
            """,
            'tag_specialist': """
            你是一位精通顾问标签体系的专家，擅长：
            1. 准确理解学生申请需求
            2. 掌握三大维度标签体系：
               - 业务专长（国家、专业）
               - 服务质量（名校专家、博士专家、低龄留学专家、offer猎手、获签能手、高效文案、口碑文案）
               - 行业经验（熟练Lv. 1+、资深Lv. 3+、专家Lv. 6+）
            3. 精准进行需求到标签的映射
            4. 确保标签选择的优先级合理
            """
        }
    
    def get_template(self, key):
        return self._templates.get(key, "")
    
    def update_template(self, key, new_template):
        if key in self._templates:
            self._templates[key] = new_template
            return True
        return False






def requirement_analyst(step_callback, custom_prompt=None):
    """需求分析专员"""
    prompt = custom_prompt or PromptTemplates().get_template('requirement_analyst')
    return Agent(
        role='需求分析专员',
        goal='深入分析学生申请需求并生成结构化分析报告',
        backstory=prompt,
        verbose=True,
        allow_delegation=False,
        llm=default_llm,
        step_callback=step_callback
    )



def analyze_requirements_task(step_callback):
    """需求分析任务"""
    requirement_analysis_structure = """
    {{  
      "申请需求分析": {{
        "基础背景": {{
          "申请目标": "string",
          "学术背景": {{
            "院校背景": "string",
            "专业背景": "string",
            "学术表现": "string",
            "语言标化": "string"
          }},
          "特殊情况": "string"
        }},
        "服务需求": {{
          "核心需求": "string",
          "特殊要求": "string",
          "时间要求": {{
            "入学时间": "string",
            "截止时间": "string",
            "时间紧迫度": "string"
          }},
          "服务偏好": {{
            "沟通期望": "string",
            "服务重点": "string"
          }}
        }},
        "风险评估": {{
          "申请风险": {{
            "院校匹配度": "string",
            "竞争情况": "string",
            "背景劣势": "string"
          }},
          "服务风险": {{
            "时间风险": "string",
            "期望管理": "string"
          }}
        }},
        "建议说明": {{
          "服务重点": "string",
          "匹配建议": "string",
          "风险管控": "string"
        }}
      }}
    }}
    """
    
    return Task(
        description="""
        基于学生背景信息，进行深入的需求分析，输出结构化报告。
        
        学生背景信息：
        {student_info}
        
        分析要求：
        1. 全面评估学生的申请背景和需求
           - 分析院校和专业背景
           - 评估语言和标化成绩
           - 考虑名校占比要求
           - 评估时间限制

        2. 识别关键服务需求点
           - 基于客户画像问卷分析服务偏好
           - 理解沟通需求和期望
           - 确定服务重点和特殊要求

        3. 评估潜在风险和挑战
           - 分析申请难度和竞争情况
           - 评估时间风险
           - 考虑背景劣势
           - 关注期望管理

        4. 提供明确的服务建议
           - 制定服务策略
           - 给出匹配建议
           - 提供风险管控方案
        
        注意事项：
        1. 确保信息的完整性和准确性
        2. 重点关注客户画像问卷反映的需求特点
        3. 考虑名校占比对服务难度的影响
        4. 评估时间限制的可行性
        5. 根据客户特点定制服务建议
        """,
        expected_output=requirement_analysis_structure,
        agent=requirement_analyst(step_callback)
    )




def tag_specialist(step_callback, custom_prompt=None):
    """标签映射专员"""
    prompt = custom_prompt or PromptTemplates().get_template('tag_specialist')
    return Agent(
        role='标签映射专员',
        goal='将需求分析转化为标准化顾问标签',
        backstory=prompt,
        verbose=True,
        allow_delegation=False,
        llm=default_llm,
        step_callback=step_callback
    )

# 添加Excel处理函数
def process_excel(df):
    """处理Excel数据并返回结果"""
    results = []
    for _, row in df.iterrows():
        try:
            # 将DataFrame行转换为字典格式
            student_info = {
                "basic_info": {
                    "name": row.get("name", ""),
                    "education": {
                        "current_degree": row.get("current_degree", ""),
                        "major": row.get("major", ""),
                        "gpa": row.get("gpa", ""),
                        "school": row.get("school", ""),
                        "expected_graduation": row.get("expected_graduation", "")
                    },
                    "language": {
                        "toefl": row.get("toefl"),
                        "ielts": row.get("ielts"),
                        "gre": row.get("gre"),
                        "gmat": row.get("gmat")
                    }
                },
                "application_intent": {
                    "target_countries": row.get("target_countries", "").split(","),
                    "target_majors": row.get("target_majors", "").split(","),
                    "degree_level": row.get("degree_level", ""),
                    "target_schools": {
                        "total_count": str(row.get("total_count", "")),
                        "top_school_ratio": str(row.get("top_school_ratio", ""))
                    },
                    "timeline": {
                        "target_enrollment": row.get("target_enrollment", ""),
                        "latest_submission_deadline": row.get("latest_submission_deadline", "")
                    }
                },
                "special_requirements": {
                    "timeline": row.get("timeline", ""),
                    "special_notes": row.get("special_notes", "")
                },
                "customer_survey": {
                    "咨询时是否准备详细的问题清单": row.get("问题清单", "否"),
                    "是否主动了解顾问背景和成功案例": row.get("了解背景", "否"),
                    "是否对申请结果有较高期望": row.get("高期望", "否"),
                    "咨询过程是否频繁记录信息": row.get("记录信息", "否"),
                    "是否详细询问服务期间的沟通方式": row.get("沟通方式", "否"),
                    "是否主动询问如何配合提高申请成功率": row.get("主动配合", "否"),
                    "是否期待尽快进入申请审理阶段": row.get("尽快审理", "否"),
                    "其他特殊要求": row.get("其他要求", "")
                }
            }
            
            # 处理单个学生案例
            result = process_student_case(student_info)
            results.append({
                "student_name": row.get("name", "未知"),
                "result": result
            })
            
        except Exception as e:
            results.append({
                "student_name": row.get("name", "未知"),
                "result": {
                    "status": "error",
                    "error_message": str(e)
                }
            })
    
    return results

    
def extract_tags_task(step_callback):
    """标签提取任务"""
    tag_recommendation_structure = """
    {{
      "requirement_analysis": {{
        "申请难度": "string",
        "时间紧迫度": "string",
        "特殊需求": "string",
        "风险点": "string"
      }},
      "recommended_tags": {{
        "countries": ["国家1", "国家2"],
        "majors": ["专业1", "专业2"],
        "businessCapabilities": ["能力1", "能力2"],
        "serviceQualities": ["质量1", "质量2"],
        "stability": ["经验水平1", "经验水平2"]
      }}
    }}
    """
    
    return Task(
        description="""      
        需求分析报告：
        {requirement_analysis}
        
        标签体系：
        {tag_system}
        
        提取要求：
        基于学生背景和标签体系，分析和输出必要的标签

        #案件分析及匹配标签原则如下：
        1. 国家标签 
        - 根据签约国家直接匹配对应的国家标签
        
        2. 专业标签 
        - 必须从 tag_system 中的 majors 列表中精确匹配专业标签
        - 如果申请专业在 tag_system.majors 中没有完全相同的，选择最接近的专业类别
        - 严禁输出不在 tag_system.majors 列表中的专业标签
        - 例如：
          * 申请"金融工程"，应选择"金融与会计"
          * 申请"人工智能"，应选择"计算机与信息系统"
          * 申请"机器人工程"，应选择"机械与工程"
        
        3. 名校专家标签
        - 申请者毕业院校为顶尖院校(C9/藤校/G5等)或者备注信息中提及希望申请名校，输出“名校专家”

        4.offer猎手标签
        - 备注中体现对申请结果的成功率很关注的输出“offer猎手”

        5.获签能手
        -申请国家签证比较难获得的，或者备注中有对签证有要求的输出“获签能手”

        6.博士专家标签
        -留学类别唯一为博士或者研究型硕士输出“博士专家”

        7.低龄留学专家标签
        -留学类别唯一为k12（指从幼儿园到12年级的教育阶段（K-12，即Kindergarten到12th Grade）的留学），输出“低龄留学专家”

        8.高效文案标签
        -备注中提及希望定期沟通的，或者希望尽快的，或者有时间要求的输出“高效文案”

        9.口碑文案标签
        -备注中对文书有特殊要求的，输出“口碑文案”

        10.行业经验标签
        -备注中提及稳定性/经验要求，仅输出"专家Lv. 6+"
        -申请者来自顶尖院校(C9/藤校/G5等)，仅输出"专家Lv. 6+"
        -综合分析难度，较简单的输出"熟练Lv. 1+"，中等难度的输出"资深Lv. 3+"，高难度申请的输出"专家Lv. 6+"

        """,
        expected_output=tag_recommendation_structure,
        agent=tag_specialist(step_callback)
    )



def create_step_callback():
    """创建更健壮的步骤回调函数"""
    def step_callback(step):
        try:
            # 检查step对象的类型和属性
            if hasattr(step, 'name'):
                print(f"Step: {step.name} - Status: {step.status}")
            elif hasattr(step, 'type'):
                print(f"Step Type: {step.type}")
            else:
                # 通用处理
                print(f"Processing step: {str(step)}")
        except Exception as e:
            print(f"Callback processing error: {str(e)}")
    
    return step_callback


def clean_json_string(json_str):
    """清理JSON字符串,移除markdown格式标记"""
    # 移除markdown代码块标记
    json_str = re.sub(r'```json\s*', '', json_str)
    json_str = re.sub(r'```\s*', '', json_str)
    
    # 确保JSON字符串的完整性
    json_str = json_str.strip()
    
    # 处理可能的转义字符
    json_str = json_str.replace('\\"', '"')
    json_str = json_str.replace('\\n', ' ')
    
    # 如果字符串不是以 { 开始，尝试找到第一个有效的 JSON 开始位置
    start_idx = json_str.find('{')
    if start_idx != -1:
        json_str = json_str[start_idx:]
    
    # 如果字符串不是以 } 结束，尝试找到最后一个有效的 JSON 结束位置
    end_idx = json_str.rfind('}')
    if end_idx != -1:
        json_str = json_str[:end_idx+1]
        
    return json_str

def process_student_case(student_info, tag_system=None):
    """处理单个学生案例"""
    # 如果没有传入tag_system，使用默认的TAG_SYSTEM
    if tag_system is None:
        tag_system = TAG_SYSTEM
        
    # Initialize result variables
    analysis_result = None
    requirement_analysis = None
    
    try:
        callback = create_step_callback()
        
        # Validate OpenAI configuration
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OpenAI API key not configured")
            
        # 创建任务
        analysis_task = analyze_requirements_task(callback)
        
        # 首先执行需求分析任务
        crew_analysis = Crew(
            agents=[requirement_analyst(callback)],
            tasks=[analysis_task],
            verbose=True
        )
        
        # 执行第一个任务并获取结果
        try:
            analysis_result = crew_analysis.kickoff(
                inputs={
                    "student_info": student_info
                }
            )
            
            # 将 CrewOutput 转换为字典
            if hasattr(analysis_result, 'raw_output'):
                cleaned_json = clean_json_string(analysis_result.raw_output)
            else:
                cleaned_json = clean_json_string(str(analysis_result))
                
            try:
                requirement_analysis = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")
                print(f"清理后的JSON字符串: {cleaned_json}")
                raise
                
        except Exception as api_error:
            print(f"API Error during analysis: {str(api_error)}")
            raise
        
        # 创建标签提取任务
        tag_task = extract_tags_task(callback)
        
        # 创建新的crew执行标签提取
        crew_tags = Crew(
            agents=[tag_specialist(callback)],
            tasks=[tag_task],
            verbose=True
        )
        
        # 执行标签提取任务，传入需求分析结果
        try:
            tag_result = crew_tags.kickoff(
                inputs={
                    "requirement_analysis": requirement_analysis,  # 现在传入的是字典
                    "tag_system": tag_system
                }
            )
            
            # 处理标签结果
            if hasattr(tag_result, 'raw_output'):
                cleaned_json = clean_json_string(tag_result.raw_output)
            else:
                cleaned_json = clean_json_string(str(tag_result))
                
            try:
                recommended_tags = json.loads(cleaned_json)
                
                # 添加结果验证
                if isinstance(recommended_tags, dict):
                    # 确保包含所有必要的标签类别
                    if "recommended_tags" not in recommended_tags:
                        recommended_tags = {"recommended_tags": recommended_tags}
                    
                    # 确保每个标签类别都是列表
                    for category in ["countries", "majors", "businessCapabilities", 
                                   "serviceQualities", "stability"]:
                        if category not in recommended_tags["recommended_tags"]:
                            recommended_tags["recommended_tags"][category] = []
                        elif not isinstance(recommended_tags["recommended_tags"][category], list):
                            recommended_tags["recommended_tags"][category] = [recommended_tags["recommended_tags"][category]]
            
            except json.JSONDecodeError as e:
                print(f"标签JSON解析错误: {str(e)}")
                print(f"清理后的标签JSON字符串: {cleaned_json}")
                raise
                
        except Exception as api_error:
            print(f"API Error during tag extraction: {str(api_error)}")
            raise
            
        # 在process_student_case函数中添加调试输出
        print(f"原始标签结果: {tag_result}")
        print(f"清理后的JSON: {cleaned_json}")
        print(f"解析后的标签: {recommended_tags}")
        
        return {
            "status": "success",
            "requirement_analysis": requirement_analysis,
            "recommended_tags": recommended_tags,
            "process_info": {
                "analysis_info": str(analysis_result),
                "tag_info": str(tag_result)
            }
        }
        
    except Exception as e:
        error_info = {
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "error_details": {
                "traceback": traceback.format_exc(),
                "analysis_result": str(analysis_result) if analysis_result else None,
                "requirement_analysis": str(requirement_analysis) if requirement_analysis else None
            }
        }
        print(f"Error processing case: {json.dumps(error_info, indent=2)}")
        return error_info



def main():
    """主函数，用于直接运行脚本时的测试"""
    # 示例学生信息
    test_student = {
        "basic_info": {
            "name": "张三",
            "education": {
                "current_degree": "本科",
                "major": "计算机科学",
                "gpa": "3.6/4.0",
                "school": "南京大学",
                "expected_graduation": "2024-06"
            },
            "language": {
                "toefl": "100",
                "ielts": None,
                "gre": "320",
                "gmat": None,
                "other_scores": {
                    "awa": "4.0"
                }
            }
        },
        "application_intent": {
            "target_countries": ["美国"],
            "target_majors": ["计算机科学"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "8",
                "top_school_ratio": "0.75"  # 名校占比：预计申请名校个数/合同数
            },
            "timeline": {
                "target_enrollment": "2025秋季入学",
                "latest_submission_deadline": "2024-12-15"  # 最晚递交时间
            }
        },
        "special_requirements": {
            "timeline": "2025秋季入学",
            "special_notes": "希望申请常春藤，时间比较紧，需要高效服务，无科研经历，需要突出项目经验"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "是",  # 咨询时是否准备详细的问题清单
            "是否主动了解顾问背景和成功案例": "是",            # 是否主动要求了解文案的背景和以往成功案例
            "是否对申请结果有较高期望": "是",           # 是否对申请结果有较高的预期目标
            "咨询过程是否频繁记录信息": "是",                # 咨询过程中是否频繁记录重要信息
            "是否详细询问服务期间的沟通方式": "是",       # 是否详细询问了服务期间的沟通方式和频率
            "是否主动询问如何配合提高申请成功率": "是",          # 是否主动询问如何配合文案工作以提高申请成功率
            "是否期待尽快进入申请审理阶段": "是",              # 是否期待尽快进入申请审理阶段
            "其他特殊要求": "需要定期进行申请进度同步，希望能有详细的时间规划"  # 是否有其他要求
        }
    }
    
    
    # 示例2：商科高标准申请
    test_student_2 = {
        "basic_info": {
            "name": "李四",
            "education": {
                "current_degree": "本科",
                "major": "金融学",
                "gpa": "3.8/4.0",
                "school": "上海交通大学",
                "expected_graduation": "2024-06"
            },
            "language": {
                "toefl": None,
                "ielts": "7.5",
                "gre": None,
                "gmat": "720",
                "other_scores": {
                    "awa": "5.0"
                }
            }
        },
        "application_intent": {
            "target_countries": ["美国", "英国"],
            "target_majors": ["金融工程", "金融数学"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "10",
                "top_school_ratio": "0.9"
            },
            "timeline": {
                "target_enrollment": "2024秋季入学",
                "latest_submission_deadline": "2023-12-01"
            }
        },
        "special_requirements": {
            "timeline": "2024秋季入学",
            "special_notes": "希望申请TOP金融项目，有量化交易实习经验，需要突出金融建模能力"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "是",
            "是否主动了解顾问背景和成功案例": "是",
            "是否对申请结果有较高期望": "是",
            "咨询过程是否频繁记录信息": "否",
            "是否详细询问服务期间的沟通方式": "是",
            "是否主动询问如何配合提高申请成功率": "是",
            "是否期待尽快进入申请审理阶段": "否",
            "其他特殊要求": "希望文案有金融背景，需要协助规划实习和竞赛"
        }
    }

    # 示例3：跨专业申请
    test_student_3 = {
        "basic_info": {
            "name": "王五",
            "education": {
                "current_degree": "本科",
                "major": "机械工程",
                "gpa": "3.4/4.0",
                "school": "哈尔滨工业大学",
                "expected_graduation": "2024-06"
            },
            "language": {
                "toefl": "95",
                "ielts": None,
                "gre": "310",
                "gmat": None,
                "other_scores": {
                    "awa": "3.5"
                }
            }
        },
        "application_intent": {
            "target_countries": ["德国", "美国"],
            "target_majors": ["数据科学", "人工智能"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "12",
                "top_school_ratio": "0.5"
            },
            "timeline": {
                "target_enrollment": "2024冬季入学",
                "latest_submission_deadline": "2024-03-15"
            }
        },
        "special_requirements": {
            "timeline": "2024冬季入学",
            "special_notes": "跨专业申请，有编程自学经历，需要突出转专业的准备和决心"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "否",
            "是否主动了解顾问背景和成功案例": "是",
            "是否对申请结果有较高期望": "否",
            "咨询过程是否频繁记录信息": "是",
            "是否详细询问服务期间的沟通方式": "是",
            "是否主动询问如何配合提高申请成功率": "是",
            "是否期待尽快进入申请审理阶段": "否",
            "其他特殊要求": "需要详细的跨专业规划建议，希望能有针对性的课程推荐"
        }
    }

    # 示例4：低龄留学
    test_student_4 = {
        "basic_info": {
            "name": "赵六",
            "education": {
                "current_degree": "高中",
                "major": "理科",
                "gpa": "90/100",
                "school": "北京市第四中学",
                "expected_graduation": "2025-06"
            },
            "language": {
                "toefl": "85",
                "ielts": None,
                "ssat": "1450",
                "other_scores": {
                    "ap": ["Calculus AB: 4", "Physics C: 4"]
                }
            }
        },
        "application_intent": {
            "target_countries": ["美国", "英国"],
            "target_majors": ["预科+本科直通"],
            "degree_level": "本科",
            "target_schools": {
                "total_count": "15",
                "top_school_ratio": "0.6"
            },
            "timeline": {
                "target_enrollment": "2025秋季入学",
                "latest_submission_deadline": "2025-01-15"
            }
        },
        "special_requirements": {
            "timeline": "2025秋季入学",
            "special_notes": "希望申请寄宿高中，有竞赛获奖经历，需要全面的升学规划"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "是",
            "是否主动了解顾问背景和成功案例": "是",
            "是否对申请结果有较高期望": "是",
            "咨询过程是否频繁记录信息": "否",
            "是否详细询问服务期间的沟通方式": "是",
            "是否主动询问如何配合提高申请成功率": "否",
            "是否期待尽快进入申请审理阶段": "否",
            "其他特殊要求": "需要协助规划课外活动和社会实践，家长希望有定期沟通机制"
        }
    }
    
    
        # 示例5：成绩偏弱的申请
    
    
    test_student_5 = {
        "basic_info": {
            "name": "孙七",
            "education": {
                "current_degree": "本科",
                "major": "市场营销",
                "gpa": "2.8/4.0",
                "school": "某省属重点大学",
                "expected_graduation": "2025-06"
            },
            "language": {
                "toefl": "80",
                "ielts": None,
                "gre": "295",
                "gmat": None,
                "other_scores": {
                    "awa": "3.0"
                }
            }
        },
        "application_intent": {
            "target_countries": ["英国", "澳大利亚", "新加坡"],
            "target_majors": ["商科管理", "传媒"],
            "degree_level": "硕士",
            "target_schools": {
                "total_count": "8",
                "top_school_ratio": "0.25"  # 名校占比较低
            },
            "timeline": {
                "target_enrollment": "2026春季入学",  # 较晚的入学时间
                "latest_submission_deadline": "2025-09-15"  # 充足的准备时间
            }
        },
        "special_requirements": {
            "timeline": "2026春季入学",
            "special_notes": "希望申请商科或传媒专业，GPA和语言成绩都需要提高，可能需要预科或语言项目，家长希望申请前三学校但学生倾向于稳妥选择"
        },
        "customer_survey": {
            "咨询时是否准备详细的问题清单": "否",  # 对申请准备不足
            "是否主动了解顾问背景和成功案例": "是",            # 关注顾问背景
            "是否对申请结果有较高期望": "是",           # 家长期望较高
            "咨询过程是否频繁记录信息": "否",                # 不够主动
            "是否详细询问服务期间的沟通方式": "是",       # 需要频繁沟通
            "是否主动询问如何配合提高申请成功率": "否",          # 被动性强
            "是否期待尽快进入申请审理阶段": "否",              # 时间充足
            "其他特殊要求": "需要详细的背景提升规划，包括实习和语言提高建议，希望能有定期的学习进度追踪，家长希望每周都有沟通反馈"
        }
    }
    
    # 处理测试案例
    result = process_student_case(test_student_4)
    
    # 打印结果
    if result["status"] == "success":
        print("\n=== 需求分析 ===")
        print(json.dumps(result["requirement_analysis"], 
                        ensure_ascii=False, indent=2))
        print("\n=== 推荐标签 ===")
        print(json.dumps(result["recommended_tags"], 
                        ensure_ascii=False, indent=2))
    else:
        print(f"处理失败: {result['error_message']}")

if __name__ == "__main__":
    # 初始化配置
    initialize_config()
    # 运行主函数
    main()