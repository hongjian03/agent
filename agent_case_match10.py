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
import streamlit as st




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




#def load_config():
    """加载配置文件"""
    # 获取当前文件所在目录
#    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 配置文件路径
#    json_path = os.path.join(current_dir, 'api_config2.json')
    
#    try:
#        with open(json_path, 'r', encoding='utf-8') as config_file:
#            config = json.load(config_file)
#        return config
#    except FileNotFoundError:
#        raise FileNotFoundError(f"配置文件不存在: {json_path}\n请确保api_config2.json文件位于正确位置")
#    except json.JSONDecodeError:
#        raise ValueError(f"配置文件格式错误: {json_path}\n请确保是有效的JSON格式")

#def update_environment_variables(config):
    """更新环境变量"""
#    if config and isinstance(config, dict):
#        os.environ['OPENAI_API_KEY'] = config.get('OPENAI_API_KEY', '')
#        os.environ['OPENAI_API_BASE'] = config.get('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
#        os.environ['OPENAI_MODEL_NAME'] = config.get('OPENAI_MODEL_NAME', 'openrouter/google/gemini-2.0-flash-001')


#config = load_config()
#update_environment_variables(config)


#def initialize_config():
#    config = load_config()
#    update_environment_variables(config)






llm_search_professor = ChatOpenAI(
    model="google/gemini-flash-1.5-8b",
    api_key=os.environ.get('OPENAI_API_KEY'),
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
    model=st.session_state.current_model,
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
    "schoolLevel": [
        "名校申请经验丰富", "顶级名校成功案例"
    ],
    "SpecialProjects": [
        "博士申请经验", "博士成功案例", "低龄留学申请经验", "低龄留学成功案例"
    ],
    "Industryexperience": [
        "行业经验", "文案背景"
    ],
    "Consultantbackground": [
        "海归"
    ],
    "businessLocation": [
        "业务单位所在地"
    ]
}
# 添加新的配置类来管理提示词模板
class PromptTemplates:
    def __init__(self):
        self._templates = {
            'tag_specialist': """      
            我是 CaseMatch, 一个专门为留学机构设计的留学顾问匹配助手。我的主要工作是通过分析学生的基本申请需求,为他们匹配合适的留学申请顾问。
            我的工作原理建立在对留学申请关键要素的理解之上。通过分析学生选择的目标国家、专业方向、申请院校层次(普通/名校/顶尖名校)、申请项目类型(本科/硕士/博士/K12)等信息,我能够准确判断该案例对留学顾问的具体要求,包括顾问需要具备的行业经验水平、教育背景以及地域特征等要素。
            我的目标是通过系统化的分析,帮助留学机构更精准地进行顾问匹配,提升服务效率和学生满意度。

            """,
            
            'tag_task': """
            任务描述：
            1. 分析任务开始前，你需要仔细阅读：学生背景信息：{student_info}
            2. 充分了解和理解标签体系：{tag_system}

            作为CaseMatch，你的核心任务是分析客户信息，并输出相应的留学申请顾问画像标签。具体分析规则如下：

            1. 国家标签分析
            ● 仅将客户明确签约的国家作为国家标签，例如：美国、英国、加拿大等，无需添加'申请'字样。对于客户提及的潜在意向国家（如'可能'、'考虑'、'意向'等表述），不作为标签输出。

            2. 专业领域标签分析
            ● 优先分析客户提供的"专业方向"信息：
            ○ 将每个专业方向都必须独立归类到专业大类标签之一
            ○ 多个专业方向（包含"/"等分隔符）时：
                ■ 若属于同一专业大类，仅输出一次该专业大类标签
                ■ 若属于不同专业大类，分别输出对应标签
            ● 仅当"专业方向"信息缺失时，才分析"专业名称"：
            ○ 将专业名称归类到专业大类标签之一
            ○ 多个专业名称时，遵循同样的归类原则
            ● 专业大类标签列表：
            ○ 计算机与信息系统
            ○ 土木与环境
            ○ 机械与工程
            ○ 数学与统计
            ○ 生物与医学
            ○ 商科管理
            ○ 金融与会计
            ○ 经济学
            ○ 国际关系与政策
            ○ 教育学
            ○ 艺术学
            ○ 传媒与新闻
            ○ 语言与文学
            ○ 人文学科
            ○ 心理学
            ○ 法学

            3. 院校层次标签分析

            A. "名校申请经验丰富"标签判断：
            第一步：院校背景判断
            ○ 中国大陆院校分类:
            ■ 优质院校: 985/211/双一流/中外合作办学院校
            ■ 普通院校: 其他院校
            ○ 国外院校分类:
            ■ 优质院校: 全球TOP100
            ■ 普通院校: 非TOP100

            第二步：学术表现判断
            ○ 中外合作/国外优质院校学生:
            ■ GPA ≥ 85分或3.5/4.0
            ○ 其他学生要求:
            ■ GPA ≥ 87分或3.7/4.0
            ■ 雅思 ≥ 7.0或同等语言成绩

            第三步：标签输出条件(满足任一):
            ○ 优质院校 + 达到对应学术要求
            ○ 普通院校 + 达到对应学术要求 + 非澳新申请
            ○ 明确名校申请意向

            B. "XX国家顶级名校成功案例"标签判断：
            ○ 必须满足以下任一条件：
            ■ 申请目标院校在下列顶级名校列表中
            ■ 背景特别优秀 + 明确名校申请意向

            顶级名校列表：
            ■ 美国：Princeton University普林斯顿大学、Harvard University哈佛大学、Yale University耶鲁大学、Stanford University斯坦福大学、University of Chicago芝加哥大学、Massachusetts Institute of Technology麻省理工学院、University of Pennsylvania宾夕法尼亚大学、California Institute of Technology加州理工学院
            ■ 英国：Oxford University牛津大学、Cambridge University剑桥大学
            ■ 加拿大：Mcgill University麦吉尔大学、University of Toronto多伦多大学、University of British Columbia, UBC英属哥伦比亚大学
            ■ 法国：HEC 巴黎高等商学院、巴黎索邦大学（仅限专业直入）、巴黎萨克雷大学（仅限专业直入）、ESSEC高商、ESCP高商、巴黎政治学院
            ■ 瑞士：苏黎世联邦理工学院、洛桑联邦理工学院、苏黎世大学、洛桑酒店管理学院
            ■ 德国：海德堡大学、慕尼黑大学、柏林自由大学、曼海姆大学、慕尼黑工业大学、亚琛工业大学、卡尔斯鲁厄理工、弗莱堡大学、德累斯顿工业大学、图宾根大学
            ■ 荷兰：代尔夫特理工大学、阿姆斯特丹大学、伊拉斯姆斯大学、爱因霍芬理工
            ■ 丹麦：哥本哈根大学、丹麦科技大学
            ■ 芬兰：赫尔辛基大学、阿尔托大学
            ■ 挪威：挪威科技大学
            ■ 瑞典：斯德哥尔摩大学、卡罗琳斯卡医学院、隆德大学
            ■ 日本：东京大学、京都大学、大阪大学、东京工业大学
            ■ 韩国：首尔大学、延世大学

            4. 特殊项目标签分析
            ● "XX（国家）博士申请成功案例"标签判断标准(需同时满足)：
            ○ 优质院校背景
            ○ GPA达到85分以上或3.5+/4.0
            ○ 对于普通中国大陆学生（非中外合作办学院校的学生）：语言成绩高于平均水平（雅思6.5以上或其他同等语言考试成绩）
            不满足以上任一条件，则输出"XX（国家）博士申请经验"
            ● 根据留学/升学类别信息，分析是否需要输出：
            ○ XX（国家）博士申请经验/XX（国家）博士申请成功案例：适用于博士申请或研究型硕士申请
            ○ XX（国家）低龄留学申请经验/XX（国家）低龄留学申请成功案例：适用于K12申请
            ● "XX（国家）低龄留学申请经验"标签判断标准(满足以下任一条件即输出"XX（国家）低龄留学申请经验"而非"XX（国家）低龄留学申请成功案例")：
            ○ 学业成绩：学生平均成绩未达到85分
            ○ 语言水平：学生当前语言水平明显低于目标学校要求
            ○ 转学年级：高中阶段的跨年级转学(如高二转入国际高中)

            5. 需求导向标签分析：基于客户的补充需求信息，分析是否需要输出：
            ● 行业经验标签：
            ○ 同时输出熟练Lv.1+和资深Lv.3+和专家Lv.6+：适用于常规申请需求
            ○ 同时输出资深Lv.3+和专家Lv.6+：在满足以下情况时必须输出：
                ■ 判断需要"XX（国家）博士申请经验"、"XX（国家）博士申请成功案例"、"XX（国家）低龄留学申请经验"或"XX（国家）低龄留学申请成功案例"、“XX（国家）顶级名校成功案例”的案件
                ■ 案例涉及密集的家长关注和沟通
                ■ 客户表现出较强的沟通需求
                ■ 需要频繁解释和确认的情况
                ■ 客户本身毕业于除C9联盟以外的985/211/双一流/明确的中外合作办学院校或国外普通院校（美国U.S. News排名30名之后的美国院校以及其他国家及地区的普通院校）
            ○ 仅输出专家(Lv.6+)：仅在满足以下情况之一时输出：
                ■ 客户或家长表现出极高难度的沟通需求
                ■ 案例整体难度和复杂度特别高
                ■ 学生教育背景极好（例如毕业于美国U.S. News排名前30的美国院校，英国QS排名前50的院校等、GPA很高、有多段科研经历）
            ● 顾问背景标签：
            ○ 海归：仅在客户明确要求顾问具有海外留学背景时输出
            ● 地域标签：只有在客户对地域有要求的情况下，需要根据客户所在地及具体需求，输出相应的地域标签

            输出要求：
            ● 每个输出标签都需要有明确的分析依据
            ● 信息不充分时，应谨慎输出标签
            ● 如对院校身份存在疑问，默认按照普通院校处理


            """,

            'tag_recommendation_structure': """
            按以下固定格式和顺序输出标签分析结果：
            ```json
            {
              "recommended_tags": {
                "index": ["string, 序号"],
                "countries": ["string, 国家标签"],
                "majors": ["string, 专业标签"],
                "schoolLevel": ["string, 院校层次"],
                "SpecialProjects": ["string, 特殊项目标签"],
                "Industryexperience": ["string, 行业经验标签"],
                "Consultantbackground  ": ["string, 顾问背景标签"],
                "businessLocation": ["string, 业务所在地"],
              }
            }

            """
        }
    
    def get_template(self, key):
        return self._templates.get(key, "")
    
    def update_template(self, key, new_template):
        if key in self._templates:
            self._templates[key] = new_template
            return True
        return False






def tag_specialist(step_callback, custom_prompt=None):
    """留学顾问匹配助手"""
    prompt = custom_prompt.get_template('tag_specialist')
    return Agent(
        role='留学顾问匹配助手',
        goal='分析学生背景并输出标准化标签',
        backstory=prompt,
        verbose=True,
        allow_delegation=False,
        llm=default_llm,
        step_callback=step_callback
    )


    
def extract_tags_task(step_callback, current_prompt=None):
    """标签提取任务"""
    # 定义预期输出格式
    tag_recommendation_structure = current_prompt.get_template('tag_recommendation_structure')
    
    if current_prompt is None:
        current_prompt = PromptTemplates()
    
    return Task(
        description=current_prompt.get_template('tag_task'),
        expected_output=tag_recommendation_structure,
        agent=tag_specialist(step_callback, current_prompt)
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
    """清理JSON字符串"""
    try:
        # 打印原始输入，用于调试
        print("原始JSON字符串:", repr(json_str))
        
        # 如果输入是空的或者不是字符串，返回一个默认的JSON结构
        if not json_str or not isinstance(json_str, str):
            return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'
        
        # 移除markdown代码块标记
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
        
        # 尝试找到一个完整的JSON对象
        match = re.search(r'\{[^{]*"recommended_tags".*\}', json_str)
        if match:
            json_str = match.group(0)
        else:
            # 如果找不到完整的JSON对象，尝试重构
            start_idx = json_str.find('{')
            end_idx = json_str.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = json_str[start_idx:end_idx+1]
            else:
                # 如果还是找不到，返回默认结构
                return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'
        
        # 清理字符串
        json_str = json_str.replace('\n', ' ')
        json_str = json_str.replace('\r', ' ')
        json_str = ' '.join(json_str.split())
        
        # 确保键名使用双引号
        json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)
        
        # 尝试解析JSON以验证其有效性
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            # 如果解析失败，返回默认结构
            return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'
            
    except Exception as e:
        print(f"清理JSON字符串时出错: {str(e)}")
        return '{"recommended_tags": {"countries": [], "majors": [], "businessCapabilities": [], "serviceQualities": [], "stability": [], "schoolLevel": [], "businessLocation": []}}'


def process_student_case2(student_case, callback=None):
    try:
        if callback:
            callback("🔍 开始分析学生案例...")
            callback("1️⃣ 提取关键信息...")
            callback("2️⃣ 创建分析专家...")
        
        # 创建专家代理
        expert = Agent(
            role='留学顾问匹配助手',
            goal='分析学生背景并输出标准化标签',
            backstory=st.session_state.prompt_templates.get_template('tag_specialist'),
            allow_delegation=False,
            llm=default_llm
        )
        
        if callback:
            callback("3️⃣ 开始深入分析学生背景...")
        
        # 创建任务
        task = Task(
            description=f"""
            {st.session_state.prompt_templates.get_template('tag_task')}
            
            学生案例信息：
            {student_case}

            标签体系：
            {st.session_state.prompt_templates.get_template('tag_system')}
            """,
            expected_output=st.session_state.prompt_templates.get_template('tag_recommendation_structure'),
            agent=expert
        )
        
        if callback:
            callback("4️⃣ 生成标签建议...")
        
        # 执行任务并直接返回结果
        result = task.execute()
        

        
        return {
            "status": "success",
            "raw_output": result  # 直接返回原始输出
        }
            
    except Exception as e:
        if callback:
            callback(f"❌ 处理过程出错: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }





def process_student_case(student_info, tag_system=None, current_prompt=None):
    """处理单个学生案例"""
    if tag_system is None:
        tag_system = TAG_SYSTEM
    
    if current_prompt is None:
        current_prompt = PromptTemplates()
        
    try:
        callback = create_step_callback()
        
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OpenAI API key not configured")
            
        tag_task = extract_tags_task(callback, current_prompt)
        
        crew_tags = Crew(
            agents=[tag_specialist(callback, current_prompt)],
            tasks=[tag_task],
            verbose=True
        )
        
        try:
            
            tag_result = crew_tags.kickoff(
                inputs={
                    "student_info": student_info,
                    "tag_system": tag_system
                }
            )
            
            # 打印原始结果，用于调试
            print("API返回的原始结果类型:", type(tag_result))
            print("API返回的原始结果:", tag_result)
            
            # 处理标签结果
            if hasattr(tag_result, 'raw_output'):
                result_str = tag_result.raw_output
            else:
                result_str = str(tag_result)
                
            print("转换后的结果字符串:", repr(result_str))
            
            # 清理JSON字符串
            cleaned_json = clean_json_string(result_str)
            print("清理后的JSON字符串:", repr(cleaned_json))
            
            try:
                recommended_tags = json.loads(cleaned_json)
                
                # 确保结果格式正确
                if isinstance(recommended_tags, dict):
                    if "recommended_tags" not in recommended_tags:
                        recommended_tags = {"recommended_tags": recommended_tags}
                    
                    # 确保所有必要的字段都存在
                    for category in ["majors", "businessCapabilities", "stability", "schoolLevel", "businessLocation"]:
                        if category not in recommended_tags["recommended_tags"]:
                            recommended_tags["recommended_tags"][category] = []
                        elif not isinstance(recommended_tags["recommended_tags"][category], list):
                            recommended_tags["recommended_tags"][category] = [recommended_tags["recommended_tags"][category]]
                
                return {
                    "status": "success",
                    "recommended_tags": recommended_tags,
                    "process_info": {
                        "tag_info": str(tag_result),  # 保存AI的原始响应
                        "cleaned_json": cleaned_json   # 保存清理后的JSON
                    }
                }
            
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")
                print(f"问题JSON字符串: {cleaned_json}")
                # 返回默认的空标签结构
                return {
                    "status": "success",
                    "recommended_tags": {
                        "recommended_tags": {
                            "countries": [],
                            "majors": [],
                            "businessCapabilities": [],
                            "serviceQualities": [],
                            "stability": [],
                            "schoolLevel": [],
                            "businessLocation": []
                        }
                    },
                    "process_info": {
                        "tag_info": "无原始响应",
                        "cleaned_json": cleaned_json
                    }
                }
                
        except Exception as api_error:
            print(f"API调用错误: {str(api_error)}")
            raise
            
    except Exception as e:
        error_info = {
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "error_details": {
                "traceback": traceback.format_exc()
            }
        }
        print(f"处理错误: {json.dumps(error_info, indent=2)}")
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
        print("\n=== 推荐标签 ===")
        print(json.dumps(result["recommended_tags"], 
                        ensure_ascii=False, indent=2))
    else:
        print(f"处理失败: {result['error_message']}")

if __name__ == "__main__":
    # 初始化配置
    #initialize_config()
    # 运行主函数
    main()