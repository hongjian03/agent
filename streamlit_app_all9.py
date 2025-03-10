import sys
import streamlit as st
import os
import logging
import re

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 记录程序启动
logger.info("程序开始运行")

# 只在第一次运行时替换 sqlite3
if 'sqlite_setup_done' not in st.session_state:
    try:
        logger.info("尝试设置 SQLite")
        __import__('pysqlite3')
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
        st.session_state.sqlite_setup_done = True
        logger.info("SQLite 设置成功")
    except Exception as e:
        logger.error(f"SQLite 设置错误: {str(e)}")
        st.session_state.sqlite_setup_done = True

# 在所有其他导入之前，先初始化环境变量

# 立即设置所有需要的API keys
try:
    logger.info("开始设置 API keys")
    os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']
    os.environ['OPENAI_API_BASE'] = "https://openrouter.ai/api/v1"
    os.environ['OPENAI_MODEL_NAME'] = st.secrets['OPENAI_MODEL_NAME']
    
    # 如果有其他key，也在这里设置
    if 'GROQ_API_KEY' in st.secrets:
        os.environ['GROQ_API_KEY'] = st.secrets['GROQ_API_KEY']
    if 'DEEPSEEK_API_KEY' in st.secrets:
        os.environ['DEEPSEEK_API_KEY'] = st.secrets['DEEPSEEK_API_KEY']
    logger.info("API keys 设置成功")
except Exception as e:
    logger.error(f"API 密钥配置失败: {str(e)}")
    st.error(f"API密钥配置失败: {str(e)}")
    st.stop()

# 其他导入
import pandas as pd
from agent_case_match13 import (
    TAG_SYSTEM,
    process_student_case,
    process_student_case2,
    PromptTemplates
)
import json
import io

st.set_page_config(
    layout="wide",  # 使用宽布局
    initial_sidebar_state="collapsed"  # 默认折叠侧边栏
)

def load_config():
    """加载配置文件"""
    try:
        # 首先尝试从 Streamlit secrets 获取配置
        if not st.secrets.get("OPENAI_API_KEY"):
            raise ValueError("未在 Streamlit secrets 中找到 OPENAI_API_KEY")
            
        config = {
            "OPENAI_API_KEY": st.secrets["OPENAI_API_KEY"],
            "OPENAI_API_BASE": "https://openrouter.ai/api/v1",
            "OPENAI_MODEL_NAME": "openrouter/google/gemini-2.0-flash-001"
        }
        return config
        
    except Exception as e:
        st.error(f"从 Streamlit secrets 获取配置失败: {str(e)}")
        return None

def initialize_config():
    """初始化配置"""
    try:
        config = load_config()
        if not config:
            raise ValueError("无法加载配置")
            
        
        
        return config
        
    except Exception as e:
        raise Exception(f"配置初始化失败: {str(e)}")

def add_custom_css():
    st.markdown("""
    <style>
    /* 强制扩展整个应用的宽度 */
    .appview-container {
        width: 100vw !important;
        max-width: 100% !important;
    }
    
    /* 扩展主容器宽度 */
    .main .block-container {
        max-width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        width: 100% !important;
    }
    
    /* 隐藏侧边栏 */
    .css-1d391kg, .css-12oz5g7, .css-eczf16, .css-jjjwou {
        display: none !important;
    }
    
    /* 移除所有边距和填充限制 */
    .reportview-container .main {
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* 确保内容使用全部可用空间 */
    .stTabs [data-baseweb="tab-panel"] {
        width: 100% !important;
    }
    
    /* 强制所有容器使用全宽 */
    .element-container, .stMarkdown, .stDataFrame, .stTable {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* 其他样式保持不变 */
    /* 标题样式 */
    h1, h2, h3 {
        color: #1e3a8a;
        font-weight: 600;
    }
    
    /* 卡片样式 */
    .stTabs [data-baseweb="tab-panel"] {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-top: 10px;
    }
    
    /* 按钮样式 */
    .stButton>button {
        background-color: #1e3a8a;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: 500;
        border: none;
        width: 100%;
    }
    
    .stButton>button:hover {
        background-color: #2e4a9a;
    }
    
    /* 输入框样式 */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 5px;
        border: 1px solid #ddd;
    }
    
    /* 文件上传区域样式 */
    .stFileUploader>div>button {
        background-color: #f1f3f9;
        color: #1e3a8a;
        border: 1px dashed #1e3a8a;
        border-radius: 5px;
    }
    
    /* 成功消息样式 */
    .stSuccess {
        background-color: #d1fae5;
        color: #065f46;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* 警告消息样式 */
    .stWarning {
        background-color: #fef3c7;
        color: #92400e;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* 错误消息样式 */
    .stError {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* 下拉选择框样式 */
    .stSelectbox>div>div {
        border-radius: 5px;
        border: 1px solid #ddd;
    }
    
    /* 页面标题样式 */
    .page-title {
        text-align: center;
        font-size: 2rem;
        margin-bottom: 20px;
        color: #1e3a8a;
        font-weight: bold;
    }
    
    /* 卡片容器样式 */
    .card-container {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 20px;
        width: 100%;
    }
    
    /* 分隔线样式 */
    hr {
        margin-top: 20px;
        margin-bottom: 20px;
        border: 0;
        border-top: 1px solid #eee;
    }
    
    /* 模型信息样式 */
    .model-info {
        background-color: #f0f7ff;
        padding: 8px 12px;
        border-radius: 5px;
        margin-top: 10px;
        margin-bottom: 15px;
        display: inline-block;
        font-size: 0.9rem;
    }
    
    /* 表格样式优化 */
    .dataframe {
        width: 100%;
        border-collapse: collapse;
    }
    
    .dataframe th {
        background-color: #f1f3f9;
        padding: 8px;
    }
    
    .dataframe td {
        padding: 8px;
        border-bottom: 1px solid #eee;
    }
    
    /* 匹配结果卡片样式 */
    .match-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: white;
    }
    
    .match-card-header {
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
        margin-bottom: 10px;
    }
    
    .match-score {
        color: #1e3a8a;
        font-weight: bold;
        font-size: 1.2rem;
    }
    
    /* 计算公式样式 */
    .formula-box {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        font-family: monospace;
    }
    
    /* 调整列宽度 */
    .column-adjust {
        padding: 0 5px !important;
    }
    
    /* 强制展开器内容宽度 */
    .streamlit-expanderContent {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)



def main():
    """主函数"""
    logger.info("进入主函数")

    add_custom_css()

     # 添加页面标题
    st.markdown("<h1 class='page-title'>留学文案匹配平台</h1>", unsafe_allow_html=True)
    
    
    # 初始化 session_state 变量
    if 'tagged_data' not in st.session_state:
        st.session_state.tagged_data = None
    if 'merged_df' not in st.session_state:
        st.session_state.merged_df = None
    if 'prompt_templates' not in st.session_state:
        st.session_state.prompt_templates = PromptTemplates()
    
    # 初始化模型选择的session state
    if 'current_model' not in st.session_state:
        st.session_state.current_model = st.secrets['OPENAI_MODEL_NAME']  # 默认值
    


    
    # 创建三个标签页
    system_tab1, system_tab2, system_tab3 = st.tabs(["标签匹配系统", "标签匹配AI提示词设置", "顾问匹配系统"])
    
    with system_tab1:
        st.title("留学申请标签匹配系统")
        # 初始化配置
        try:
            config = initialize_config()
            if not config:
                st.error("配置初始化失败：无法获取配置")
                return
            
            if not config.get("OPENAI_API_KEY"):
                st.error("未找到 OpenAI API 密钥，请检查配置")
                return
            
            # 验证 API 密钥是否有效
            if st.secrets.get("OPENAI_API_KEY"):
                logger.info("API 配置验证成功")
                st.success("✅ API配置成功")
            
            # 显示当前使用的模型（移到这里）
            st.markdown(f"<div class='model-info'>🤖 当前使用模型: <b>{st.session_state.current_model}</b></div>", unsafe_allow_html=True)
            
            # 创建提示词模板实例并存储在session_state中
            if 'prompt_templates' not in st.session_state:
                logger.info("初始化提示词模板")
                st.session_state.prompt_templates = PromptTemplates()
            
            # 使用session_state中的prompt_templates
            prompt_templates = st.session_state.prompt_templates
            
            
            
            # 添加选项卡来切换输入方式
            input_tab1, = st.tabs(["手动输入"])
            

            with input_tab1:
                st.subheader("客户基本信息")
                
                # 添加文本输入区域
                student_case = st.text_area(
                    "请输入学生案例信息",
                    height=300,
                    placeholder="""请用自然语言描述学生的基本情况，例如：
                        这是一位来自浙江大学的学生，计算机专业，GPA 3.8/4.0。托福成绩100分，GRE 320分。
                        希望申请美国的硕士项目，目标院校包含TOP30名校。计划2025年秋季入学。
                        学生有相关实习经历和研究经验..."""
                )
                
                # 添加业务单位选择框
                business_units = [
                    "新通国际", 
                    "北京中心", 
                    "成都", 
                    "福州", 
                    "广州", 
                    "杭州留学",
                    "合肥",
                    "济南",
                    "南昌",
                    "南京",
                    "宁波留学",
                    "厦门",
                    "山西",
                    "深圳",
                    "苏州",
                    "天津",
                    "温州",
                    "武汉",
                    "西安",
                    "新通温哥华",
                    "长春",
                    "郑州",
                    "重庆",
                    "舟山"
                ]

                selected_unit = st.selectbox(
                    "请选择业务单位",
                    options=business_units,
                    index=0  # 默认选择第一个选项
                )
                
                
                
                # 添加处理按钮
                if st.button("开始分析", key="start_analysis") :
                    if student_case:
                        with st.spinner("正在分析学生案例..."):
                            try:
                                # 创建一个展示区来显示处理过程
                                thinking_process = st.empty()
                                process_container = st.container()
                                
                                with process_container:
                                    st.subheader("🤔 分析过程")
                                    thinking_area = st.expander("查看详细分析过程", expanded=True)
                                    
                                    with thinking_area:
                                        process_placeholder = st.empty()
                                        messages = []  # 创建一个列表来存储所有消息
                                        
                                        def update_process(message):
                                            messages.append(message)  # 将新消息添加到列表中
                                            # 使用换行符连接所有消息并显示
                                            process_placeholder.markdown("\n\n".join(messages))
                                        
                                        # 在处理过程中更新状态
                                        update_process("🔍 开始分析学生案例...")
                                        update_process("1️⃣ 提取关键信息...")
                                        
                                        # 直接将文本传给大模型处理，并获取处理过程
                                        result = process_student_case2(student_case, callback=update_process)
                                        
                                        update_process("✅ 分析完成！")

                                if result["status"] == "success":
                                    
                                    
                                    # 显示原始输出（放在可展开的部分中）
                                    with st.expander("查看原始输出（调试用）", expanded=False):
                                        st.subheader("模型输出结果")
                                        st.code(result["raw_output"], language="json")
                                    
                                    # 处理模型输出
                                    try:
                                        # 清理和解析JSON部分
                                        json_str = result["raw_output"]
                                        
                                        # 1. 提取JSON部分（第一个 { 到对应的 } 之间的内容）
                                        start_idx = json_str.find('{')
                                        end_idx = json_str.rfind('}')
                                        if start_idx != -1 and end_idx != -1:
                                            json_part = json_str[start_idx:end_idx + 1]
                                            # 清理和解析JSON
                                            json_part = json_part.replace('```json', '').replace('```', '').strip()
                                            output_dict = json.loads(json_part)
                                            
                                            # 显示标签匹配结果
                                            st.subheader("📊 分析结果")
                                            
                                            # 创建两列布局
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                st.write("🎯 **匹配标签**")
                                                if "recommended_tags" in output_dict:
                                                    tags = output_dict["recommended_tags"]
                                                    
                                                    # 显示国家标签
                                                    if tags.get("countries"):
                                                        st.write("**国家标签：**", ", ".join(tags["countries"]))
                                                        
                                                    # 显示专业标签
                                                    if tags.get("majors"):
                                                        st.write("**专业标签：**", ", ".join(tags["majors"]))
                                                        
                                                    # 显示其他重要标签
                                                    if tags.get("schoolLevel"):
                                                        st.write("**院校层次：**", ", ".join(tags["schoolLevel"]))
                                                        
                                                    if tags.get("SpecialProjects"):
                                                        st.write("**特殊项目：**", ", ".join(tags["SpecialProjects"]))
                                            
                                            with col2:
                                                # 显示其他标签
                                                if "recommended_tags" in output_dict:
                                                    tags = output_dict["recommended_tags"]
                                                    
                                                    if tags.get("Industryexperience"):
                                                        st.write("**行业经验：**", ", ".join(tags["Industryexperience"]))
                                                        
                                                    if tags.get("Consultantbackground"):
                                                        st.write("**顾问背景：**", ", ".join(tags["Consultantbackground"]))
                                                        
                                                    if tags.get("businessLocation"):
                                                        st.write("**业务单位所在地：**", ", ".join(tags["businessLocation"]))
                                                        
                              

                                            # 2. 提取服务指南部分（在JSON之后的文本）
                                            service_guide_text = json_str[end_idx + 1:].strip()
                                            if service_guide_text:
                                                with st.expander("🎓 查看卓越服务指南", expanded=True):
                                                    # 移除可能的 markdown 代码块标记
                                                    service_guide_text = service_guide_text.replace('```', '').strip()
                                                    # 如果文本以"卓越服务指南："开头，移除这个标题
                                                    service_guide_text = re.sub(r'^卓越服务指南[：:]\s*', '', service_guide_text)
                                                    
                                                    # 显示服务指南内容
                                                    sections = service_guide_text.split('\n\n')  # 按空行分割各部分
                                                    for section in sections:
                                                        if section.strip():  # 确保部分不是空的
                                                            st.markdown(section.strip())
                                                            st.markdown("---")  # 添加分隔线
                                            
                                            # 修改创建DataFrame的部分
                                            df = pd.DataFrame({
                                                "文案顾问业务单位": [selected_unit],  # 使用选择的业务单位
                                                "国家标签": [', '.join(output_dict["recommended_tags"]["countries"])],
                                                "专业标签": [', '.join(output_dict["recommended_tags"]["majors"])],
                                                "名校专家": [', '.join(output_dict["recommended_tags"]["schoolLevel"])],
                                                "特殊项目标签": [', '.join(output_dict["recommended_tags"]["SpecialProjects"])],
                                                "行业经验": [', '.join(output_dict["recommended_tags"]["Industryexperience"])],
                                                "文案背景": [', '.join(output_dict["recommended_tags"]["Consultantbackground"])],
                                                "业务单位所在地": [', '.join(output_dict["recommended_tags"]["businessLocation"])],
                                            })
                                            
                                            # 存入session_state
                                            st.session_state.tagged_data = df
                                            
                                            # 将DataFrame显示放在可展开的部分中
                                            with st.expander("查看标签数据表格", expanded=False):
                                                st.dataframe(df)
                                            
                                            st.success("✅ 数据已处理并保存到内存中，可用于后续匹配")

                                    except Exception as e:
                                        st.error(f"处理模型输出时出错: {str(e)}")
                                        st.error("请检查模型输出格式是否符合预期")
                                        # 显示原始输出以便调试
                                        with st.expander("查看原始输出", expanded=False):
                                            st.code(result["raw_output"])
                            
                            except Exception as e:
                                st.error(f"处理过程中出错: {str(e)}")
                        
                    elif not student_case :
                        st.warning("请先输入学生案例信息")
        except Exception as e:
            logger.error(f"配置初始化失败: {str(e)}")
            st.error(f"配置初始化失败: {str(e)}")
            return

    with system_tab2:
        st.title("标签匹配AI提示词设置")
        
        # 使用session_state中的prompt_templates
        prompt_templates = st.session_state.prompt_templates
        
        # Agent backstory
        st.subheader("标签专家角色设定")
        tag_backstory = st.text_area(
            "角色设定",
            value=prompt_templates.get_template('tag_specialist'),
            height=400
        )

        # Task description
        st.subheader("标签提取任务说明")
        tag_task = st.text_area(
            "任务说明",
            value=prompt_templates.get_template('tag_task'),
            height=400
        )

        st.subheader("标签输出结构")
        tag_recommendation_structure = st.text_area(
            "标签输出结构",
            value=prompt_templates.get_template('tag_recommendation_structure'),
            height=400
        )

        # 更新按钮
        if st.button("更新提示词", key="update_prompts"):
            prompt_templates.update_template('tag_specialist', tag_backstory)
            prompt_templates.update_template('tag_task', tag_task)
            prompt_templates.update_template('tag_recommendation_structure', tag_recommendation_structure)
            st.session_state.prompt_templates = prompt_templates
            st.success("✅ 提示词已更新！")
            
            # 显示更新后的提示词
            with st.expander("查看更新后的提示词"):
                st.write("更新后的角色设定：", st.session_state.prompt_templates.get_template('tag_specialist'))
                st.write("更新后的任务说明：", st.session_state.prompt_templates.get_template('tag_task'))
                st.write("更新后的输出结构：", st.session_state.prompt_templates.get_template('tag_recommendation_structure'))

    with system_tab3:
        from match6 import (
            label_merge,
            Consultant_matching
        )
        st.title("顾问匹配系统")
        
        # 检查是否有必要的数据
        if st.session_state.tagged_data is None:
            st.warning("请先在标签匹配系统中处理数据")
            return
            
        # 文件上传区域
        with st.container():
            st.subheader("数据上传")
            uploaded_consultant_tags = st.file_uploader("请上传文案顾问标签汇总", type=['xlsx'], key='consultant')
                
            if uploaded_consultant_tags is not None:
                consultant_tags_file = pd.read_excel(uploaded_consultant_tags)
                st.success("顾问标签汇总上传成功")
            
        # 处理按钮区域
        with st.container():
            st.subheader("数据处理")
            
            # 标签转换处理按钮
            if st.button("开始标签转换处理"):
                if st.session_state.tagged_data is not None:  # 使用session中的标签数据
                    try:
                        st.session_state.merged_df = label_merge(st.session_state.tagged_data)
                        st.success("标签转换处理完成！")
                        # 显示合并后的数据预览
                        st.write("转换后数据预览：")
                        st.dataframe(st.session_state.merged_df.head())
                            
                        # 添加下载按钮
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            st.session_state.merged_df.to_excel(writer, index=False, sheet_name='标签转换结果')
                        st.download_button(
                            label="下载标签转换结果",
                            data=buffer.getvalue(),
                            file_name="标签转换结果.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.error(f"标签转换处理出错: {str(e)}")
                else:
                    st.warning("请先完成标签处理")
            
            st.markdown("---")  # 添加分隔线
            
            # 顾问匹配按钮
            if st.button("开始顾问匹配"):
                if uploaded_consultant_tags is not None and st.session_state.merged_df is not None:
                    try:
                        merge_df = st.session_state.merged_df
                        matching_results ,area = Consultant_matching(
                            consultant_tags_file,  # 顾问标签数据
                            merge_df  # 已处理的标签数据
                        )
                        st.success("顾问匹配完成！")
                        
                        # 显示匹配结果
                        st.markdown("<div class='card-container'>", unsafe_allow_html=True)
                        st.subheader("🔍 匹配结果")

                        for case, consultants in matching_results.items():
                            for i, consultant in enumerate(consultants):
                                # 创建一个漂亮的卡片来显示每个顾问的匹配结果
                                st.markdown(f"""
                                <div style="margin-bottom: 15px; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                                    <h3 style="color: #1e3a8a; margin-top: 0;">
                                        {consultant['name']} ({consultant['score']:.1f}分)
                                    </h3>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                        <span><strong>业务单位:</strong> {consultant.get('businessunits', '未知')}</span>
                                        <span><strong>匹配范围:</strong> {"本地匹配" if consultant.get('area', False) else "全国大池里匹配"}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # 添加一个展开按钮来查看详细信息
                                with st.expander(f"查看 {consultant['name']} 的详细匹配信息"):
                                    # 创建两列布局，调整列宽比例为4:6，让右侧有更多空间显示计算过程
                                    col1, col2 = st.columns([4, 6])
                                    
                                    # 第一列：顾问原始标签（简化显示）
                                    with col1:
                                        st.markdown("<h4 style='color: #1e3a8a;'>顾问原始标签</h4>", unsafe_allow_html=True)
                                        
                                        # 国家标签
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>国家标签:</strong>", unsafe_allow_html=True)
                                        if consultant['绝对高频国家']:
                                            st.markdown(f"<span>• 绝对高频国家: {consultant['绝对高频国家']}</span>", unsafe_allow_html=True)
                                        if consultant['相对高频国家']:
                                            st.markdown(f"<span>• 相对高频国家: {consultant['相对高频国家']}</span>", unsafe_allow_html=True)
                                        st.markdown("</div>", unsafe_allow_html=True)
                                        
                                        # 专业标签
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>专业标签:</strong>", unsafe_allow_html=True)
                                        if consultant['绝对高频专业']:
                                            st.markdown(f"<span>• 绝对高频专业: {consultant['绝对高频专业']}</span>", unsafe_allow_html=True)
                                        if consultant['相对高频专业']:
                                            st.markdown(f"<span>• 相对高频专业: {consultant['相对高频专业']}</span>", unsafe_allow_html=True)
                                        st.markdown("</div>", unsafe_allow_html=True)
                                        
                                        # 特殊标签
                                        special_tags = [
                                            ('名校专家', '名校专家'), 
                                            ('博士成功案例', '博士成功案例'), 
                                            ('低龄留学成功案例', '低龄留学成功案例')
                                        ]
                                        
                                        has_special_tags = any(tag_key in consultant and consultant[tag_key] for _, tag_key in special_tags)
                                        if has_special_tags:
                                            st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                            st.markdown("<strong>特殊标签:</strong>", unsafe_allow_html=True)
                                            for tag_name, tag_key in special_tags:
                                                if tag_key in consultant and consultant[tag_key]:
                                                    st.markdown(f"<span>• {tag_name}: {consultant[tag_key]}</span>", unsafe_allow_html=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                        
                                        # 其他标签
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>其他信息:</strong>", unsafe_allow_html=True)
                                        if consultant['行业经验']:
                                            st.markdown(f"<span>• 行业经验: {consultant['行业经验']}</span>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 学年负荷: {consultant['学年负荷']}</span>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 近两周负荷: {consultant['近两周负荷']}</span>", unsafe_allow_html=True)
                                        st.markdown(f"<span>• 个人意愿: {consultant['个人意愿']}</span>", unsafe_allow_html=True)
                                        st.markdown("</div>", unsafe_allow_html=True)

                                        st.markdown("<h4 style='color: #1e3a8a;'>案例需求详情</h4>", unsafe_allow_html=True)
                                        # 案例需求
                                        st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                        st.markdown("<strong>案例需求:</strong>", unsafe_allow_html=True)
                                        
                                        # 获取当前案例的标签数据
                                        case_id = list(matching_results.keys()).index(case) if case in matching_results else 0
                                        
                                        # 安全地尝试获取对应行的数据
                                        if 'merged_df' in st.session_state and not st.session_state.merged_df.empty:
                                            try:
                                                case_data = st.session_state.merged_df.iloc[case_id]
                                                
                                                # 显示指定列的数据
                                                target_columns = ['文案顾问业务单位','国家标签', '专业标签', '名校专家', 
                                                                '博士成功案例', '低龄留学成功案例', '行业经验','文案背景',
                                                                '业务单位所在地']
                                                
                                                for col in target_columns:
                                                    if col in case_data.index and pd.notna(case_data[col]) and case_data[col]:
                                                        st.markdown(f"<span>• {col}: {case_data[col]}</span>", unsafe_allow_html=True)
                                            except Exception as e:
                                                st.error(f"获取案例数据时出错: {str(e)}")
                                        else:
                                            st.warning("没有可用的案例标签数据")
                                        st.markdown("</div>", unsafe_allow_html=True)
                                    
                                    # 第二列：匹配详情
                                    with col2:
                                        st.markdown("<h4 style='color: #1e3a8a;'>匹配得分详情</h4>", unsafe_allow_html=True)
                                        
                                        # 标签匹配得分表格
                                        if 'tag_score_dict' in consultant:
                                            st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                            st.markdown("<strong>标签匹配得分:</strong>", unsafe_allow_html=True)
                                            
                                            # 创建一个表格来显示标签匹配情况
                                            tag_details = consultant['tag_score_dict']
                                            tag_data = []
                                            for tag, score in tag_details.items():
                                                tag_status = "✅" if score > 0 else "❌"
                                                tag_data.append({"标签": tag, "状态": tag_status, "得分": f"{score}分"})
                                            
                                            # 使用DataFrame显示表格
                                            tag_df = pd.DataFrame(tag_data)
                                            st.dataframe(tag_df, hide_index=True, use_container_width=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                            
                                            # 匹配率与覆盖率
                                            st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                            st.markdown("<strong>匹配率与覆盖率:</strong>", unsafe_allow_html=True)
                                            
                                            # 获取已计算好的匹配标签比例数据
                                            country_match_ratio = consultant.get('country_match_ratio', 0)
                                            special_match_ratio = consultant.get('special_match_ratio', 0)
                                            country_coverage_ratio = consultant.get('country_coverage_ratio', 0)
                                            special_coverage_ratio = consultant.get('special_coverage_ratio', 0)
                                            country_count_need = consultant.get('country_count_need', 0)
                                            country_count_total = consultant.get('country_count_total', 1)
                                            special_count_need = consultant.get('special_count_need', 0)
                                            special_count_total = consultant.get('special_count_total', 1)
                                            
                                            # 创建一个表格来显示匹配率和覆盖率
                                            ratio_data = [
                                                {"类别": "国家标签", "匹配率": f"{country_match_ratio:.2f} ({country_count_need}/{country_count_total})", "覆盖率": f"{country_coverage_ratio:.2f}"},
                                                {"类别": "特殊标签", "匹配率": f"{special_match_ratio:.2f} ({special_count_need}/{special_count_total})", "覆盖率": f"{special_coverage_ratio:.2f}"}
                                            ]
                                            ratio_df = pd.DataFrame(ratio_data)
                                            st.dataframe(ratio_df, hide_index=True, use_container_width=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                            
                                            # 最终得分计算
                                            st.markdown("<div style='margin-bottom: 15px;'>", unsafe_allow_html=True)
                                            st.markdown("<strong>得分计算:</strong>", unsafe_allow_html=True)
                                            
                                            # 获取各项得分
                                            country_tags_score = consultant.get('country_tags_score', 0)
                                            special_tags_score = consultant.get('special_tags_score', 0)
                                            other_tags_score = consultant.get('other_tags_score', 0)
                                            workload_score = consultant.get('workload_score', 0)
                                            personal_score = consultant.get('personal_score', 0)
                                            
                                            # 创建一个表格来显示各项得分
                                            score_data = [
                                                {"项目": "国家标签得分", "得分": f"{country_tags_score}分"},
                                                {"项目": "特殊标签得分", "得分": f"{special_tags_score}分"},
                                                {"项目": "其他标签得分", "得分": f"{other_tags_score}分"},
                                                {"项目": "工作量评分", "得分": f"{workload_score}分"},
                                                {"项目": "个人意愿评分", "得分": f"{personal_score}分"}
                                            ]
                                            score_df = pd.DataFrame(score_data)
                                            st.dataframe(score_df, hide_index=True, use_container_width=True)
                                            
                                            # 恢复详细计算公式
                                            st.markdown("<strong>计算公式:</strong>", unsafe_allow_html=True)
                                            st.markdown("<div class='formula-box'>", unsafe_allow_html=True)
                                            st.markdown("国家得分 × 国家匹配率 × 国家覆盖率 × 0.5 + 特殊得分 × 特殊匹配率 × 特殊覆盖率 × 0.5 + 其他标签得分 × 0.5 + 工作量得分 × 0.3 + 个人意愿得分 × 0.2", unsafe_allow_html=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                            
                                            # 详细计算过程
                                            tag_weighted = country_tags_score * country_match_ratio * country_coverage_ratio * 0.5 + special_tags_score * special_match_ratio * special_coverage_ratio * 0.5 + other_tags_score * 0.5
                                            
                                            st.markdown("<div class='formula-box'>", unsafe_allow_html=True)
                                            st.markdown(f"""
                                            ({country_tags_score:.1f}) × ({country_match_ratio:.2f}) × ({country_coverage_ratio:.2f}) × 0.5 + 
                                            ({special_tags_score:.1f}) × ({special_match_ratio:.2f}) × ({special_coverage_ratio:.2f}) × 0.5 + 
                                            ({other_tags_score:.1f}) × 0.5 + ({workload_score:.1f}) × 0.3 + ({personal_score:.1f}) × 0.2 = {consultant['score']:.1f}分
                                            """, unsafe_allow_html=True)
                                            st.markdown("</div>", unsafe_allow_html=True)
                                            
                                            # 显示最终得分
                                            final_score = consultant['score']
                                            st.markdown(f"""
                                            <div style="background-color: #f0f7ff; padding: 10px; border-radius: 5px; margin-top: 10px;">
                                                <strong>最终得分:</strong> <span style="color: #1e3a8a; font-size: 18px; font-weight: bold;">{final_score:.1f}分</span>
                                            </div>
                                            """, unsafe_allow_html=True)
                                            st.markdown("</div>", unsafe_allow_html=True)

                        st.markdown("</div>", unsafe_allow_html=True)
                        # 保存匹配结果到 session_state
                        st.session_state.matching_results = matching_results
                        
                    except Exception as e:
                        st.error(f"顾问匹配出错: {str(e)}")
                else:
                    st.warning("请先上传顾问标签汇总并完成标签处理")

            # 显示处理状态
            st.markdown("<div class='card-container'>", unsafe_allow_html=True)
            st.subheader("处理状态")
            
            # 使用更美观的状态指示器
            col1, col2 = st.columns(2)
            with col1:
                if st.session_state.merged_df is not None:
                    st.markdown("**标签处理状态:** <span style='color:green;'>✅ 完成</span>", unsafe_allow_html=True)
                else:
                    st.markdown("**标签处理状态:** <span style='color:orange;'>⏳ 待处理</span>", unsafe_allow_html=True)
            
            with col2:
                if 'matching_results' in st.session_state:
                    st.markdown("**顾问匹配状态:** <span style='color:green;'>✅ 完成</span>", unsafe_allow_html=True)
                else:
                    st.markdown("**顾问匹配状态:** <span style='color:orange;'>⏳ 待处理</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    logger.info("开始运行应用")
    main()
    logger.info("应用运行结束")

#streamlit run agent/streamlit_app.py