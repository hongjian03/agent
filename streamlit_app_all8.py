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

def main():
    """主函数"""
    logger.info("进入主函数")
    
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
    

    # 显示当前使用的模型
    st.sidebar.info(f"当前使用模型: {st.session_state.current_model}")
    
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
            
            # 创建提示词模板实例并存储在session_state中
            if 'prompt_templates' not in st.session_state:
                logger.info("初始化提示词模板")
                st.session_state.prompt_templates = PromptTemplates()
            
            # 使用session_state中的prompt_templates
            prompt_templates = st.session_state.prompt_templates
            
            # 选择输出标签
            st.sidebar.subheader("输出标签选择")
            output_tags = st.sidebar.multiselect(
                "选择需要输出的标签",
                options=[
                    "国家标签", "专业标签", "名校专家", "博士成功案例", "低龄留学成功案例", "行业经验","文案背景", "业务单位所在地","文案顾问业务单位",'做过该生所在院校的客户'
                ],
                default=["国家标签","专业标签", "名校专家", "博士成功案例", "低龄留学成功案例", "行业经验","文案背景", "业务单位所在地","文案顾问业务单位","做过该生所在院校的客户"]
            )
            
            # 添加选项卡来切换输入方式
            input_tab1, = st.tabs(["手动输入"])
            

            with input_tab1:
                st.subheader("手动输入学生案例")
                
                # 添加文本输入区域
                student_case = st.text_area(
                    "请输入学生案例信息",
                    height=300,
                    placeholder="""请用自然语言描述学生的基本情况，例如：
                        这是一位来自浙江大学的学生，计算机专业，GPA 3.8/4.0。托福成绩100分，GRE 320分。
                        希望申请美国的硕士项目，目标院校包含TOP30名校。计划2025年秋季入学。
                        学生有相关实习经历和研究经验..."""
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
                                        # 清理JSON字符串
                                        json_str = result["raw_output"]
                                        
                                        # 1. 移除所有代码块标记
                                        json_str = json_str.replace('```json', '').replace('```', '').strip()
                                        
                                        # 2. 查找第一个 { 和最后一个 } 之间的内容
                                        start_idx = json_str.find('{')
                                        end_idx = json_str.rfind('}')
                                        if start_idx != -1 and end_idx != -1:
                                            json_str = json_str[start_idx:end_idx + 1]
                                        
                                        # 3. 移除可能的前导和尾随文本说明
                                        json_str = re.sub(r'^[^{]*', '', json_str)  # 移除第一个 { 之前的所有内容
                                        json_str = re.sub(r'[^}]*$', '', json_str)  # 移除最后一个 } 之后的所有内容
                                        
                                        # 4. 尝试解析JSON
                                        try:
                                            output_dict = json.loads(json_str)
                                        except json.JSONDecodeError as e:
                                            st.error(f"JSON解析失败: {str(e)}")
                                            st.write("原始输出:", result["raw_output"])
                                            st.write("清理后的JSON字符串:", json_str)
                                            raise Exception("JSON解析失败，请检查输出格式")

                                        
                                        # 显示处理后的数据
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
                                                    
                                                if tags.get("consultant_unit"):
                                                    st.write("**业务单位：**", ", ".join(tags["consultant_unit"]))

                                        # 如果有服务指南，显示在标签下方
                                        if "service_guide" in output_dict:
                                            st.markdown("---")
                                            st.subheader("🎓 申请服务指南")
                                            
                                            with st.expander("📊 申请者深度分析", expanded=True):
                                                st.write(output_dict["service_guide"]["applicant_analysis"])
                                                
                                            with st.expander("📝 文书策略重点", expanded=True):
                                                st.write(output_dict["service_guide"]["writing_strategy"])
                                            
                                            with st.expander("🤝 沟通要点指南", expanded=True):
                                                st.write(output_dict["service_guide"]["communication_guide"])

                                        # 创建DataFrame显示（如果需要的话）
                                        df = pd.DataFrame({
                                            "文案顾问业务单位": [', '.join(output_dict["recommended_tags"]["consultant_unit"])],
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
                        st.write("匹配结果：")
                        for case, consultants in matching_results.items():
                            st.write(f"\n{case}:")
                            for consultant in consultants:
                                # 显示基本信息
                                st.write(f"- {consultant['display']}")
                                # 展开显示标签匹配详情
                                with st.expander(f"查看 {consultant['name']} 的详细匹配信息"):
                                    # 创建三列布局
                                    col1, col2 = st.columns(2)
                                    
                                    # 第一列：顾问原始标签
                                    with col1:
                                        businessunits = consultant.get('businessunits', '')
                                        area = consultant.get('area', '')
                                        area_local = "在本地匹配" if area else "在全国大池里匹配"
                                        st.subheader("顾问原始标签")
                                        st.write(f"**顾问业务单位:** {businessunits}")
                                        st.write(f"**匹配范围:** {area_local}")
                                        st.write("**国家标签:**")
                                        st.write(f"- 绝对高频国家：{consultant['绝对高频国家']}")
                                        st.write(f"- 相对高频国家：{consultant['相对高频国家']}")
                                        
                                        st.write("**专业标签:**")
                                        st.write(f"- 绝对高频专业：{consultant['绝对高频专业']}")
                                        st.write(f"- 相对高频专业：{consultant['相对高频专业']}")
                                        
                                        st.write("**其他标签:**")
                                        st.write(f"- 行业经验：{consultant['行业经验']}")
                                        st.write(f"- 业务单位所在地：{consultant['业务单位所在地']}")
                                        st.write(f"- 学年负荷：{consultant['学年负荷']}")
                                        st.write(f"- 近两周负荷：{consultant['近两周负荷']}")
                                        st.write(f"- 个人意愿：{consultant['个人意愿']}")
                                        
                                        st.write("**特殊标签:**")
                                        special_tags = [
                                            ('名校专家', '名校专家'), 
                                            ('博士成功案例', '博士成功案例'), 
                                            ('低龄留学成功案例', '低龄留学成功案例')
                                        ]
                                        
                                        for tag_name, tag_key in special_tags:
                                            if tag_key in consultant and consultant[tag_key]:
                                                st.write(f"- {tag_name}：{consultant[tag_key]}")
                                    
                                    # 第二列：匹配详情与计算过程
                                    with col2:
                                        st.subheader("匹配得分详情")
                                        # 显示案例要求
                                        st.write("**案例需求:**")
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
                                                        st.write(f"- {col}: {case_data[col]}")
                                            except Exception as e:
                                                st.error(f"获取案例数据时出错: {str(e)}")
                                        else:
                                            st.warning("没有可用的案例标签数据")
                                        
                                        # 显示匹配详情
                                        st.write("**标签匹配得分:**")
                                        total_score = 0
                                        
                                        # 检查是否有tag_score_dict
                                        if 'tag_score_dict' in consultant:
                                            tag_details = consultant['tag_score_dict']
                                            
                                            # 获取已计算好的匹配标签比例数据
                                            country_count_need = consultant.get('country_count_need', 0)
                                            special_count_need = consultant.get('special_count_need', 0)
                                            other_count_need = consultant.get('other_count_need', 0)
                                            country_count_total = consultant.get('country_count_total', 1)  # 避免除零错误
                                            special_count_total = consultant.get('special_count_total', 1)
                                            other_count_total = consultant.get('other_count_total', 1)
                                            country_match_ratio = consultant.get('country_match_ratio', 0)
                                            special_match_ratio = consultant.get('special_match_ratio', 0)
                                            country_tags_score = consultant.get('country_tags_score', 0)
                                            special_tags_score = consultant.get('special_tags_score', 0)
                                            other_tags_score = consultant.get('other_tags_score', 0)
                                            country_coverage_ratio = consultant.get('country_coverage_ratio', 0)
                                            special_coverage_ratio = consultant.get('special_coverage_ratio', 0)
                                            # 显示标签匹配详情
                                            for tag, score in tag_details.items():
                                                tag_status = "✅ 匹配" if score > 0 else "❌ 未匹配"
                                                tag_color = "green" if score > 0 else "red"
                                                st.markdown(f"- {tag}: <span style='color:{tag_color}'>{tag_status}</span> ({score}分)", unsafe_allow_html=True)
                                                total_score += score
                                            
                                            # 标签得分小计
                                            st.markdown(f"**匹配率与覆盖率:**")
                                            st.markdown(f"- 国家标签: 匹配率 {country_match_ratio:.2f} (匹配/总量: {country_count_need}/{country_count_total}), 覆盖率 {consultant['country_coverage_ratio']:.2f}")
                                            st.markdown(f"- 特殊标签: 匹配率 {special_match_ratio:.2f} (匹配/总量: {special_count_need}/{special_count_total}), 覆盖率 {consultant['special_coverage_ratio']:.2f}")
                                            
                                            # 计算最终得分并显示计算公式

                                            tag_weighted = country_tags_score * country_match_ratio * country_coverage_ratio * 0.5 + special_tags_score * special_match_ratio * special_coverage_ratio * 0.5 + other_tags_score*0.5
                                            workload_score = consultant.get('workload_score', 0)
                                            personal_score = consultant.get('personal_score', 0)
                                            
                                            # 显示工作量和个人意愿评分
                                            st.write(f"**工作量评分:** {workload_score}分")
                                            st.write(f"**个人意愿评分:** {personal_score}分")
                                            # 计算最终得分并显示计算公式
                                            final_score = tag_weighted + workload_score * 0.3 + personal_score * 0.2
                                            st.write("计算公式：国家得分 x 国家匹配率 x 国家覆盖率 x 0.5 + 特殊得分 x 特殊匹配率 x 特殊覆盖率 x 0.5 + 其他标签得分 x 0.5 + 工作量得分 x 0.3 + 个人意愿得分 x 0.2")
                                            st.write(f"""({country_tags_score}) × ({country_match_ratio}) × ({country_coverage_ratio}) × 0.5 + 
                                                      ({special_tags_score}) × ({special_match_ratio}) × ({special_coverage_ratio}) × 0.5 + 
                                                      ({other_tags_score}) × 0.5+ ({workload_score}) × 0.3 + ({personal_score}) × 0.2 = {final_score:.1f}分""")
                                            
                                            # 显示总分（确保与consultant['score']一致）
                                            st.markdown(f"**最终得分: {consultant['score']:.1f}分**")
                        
                        # 保存匹配结果到 session_state
                        st.session_state.matching_results = matching_results
                        
                    except Exception as e:
                        st.error(f"顾问匹配出错: {str(e)}")
                else:
                    st.warning("请先上传顾问标签汇总并完成标签处理")

            # 显示处理状态
            st.markdown("---")  # 添加分隔线
            st.subheader("处理状态")
            st.write("标签处理状态:", "✅ 完成" if st.session_state.merged_df is not None else "⏳ 待处理")
            st.write("顾问匹配状态:", "✅ 完成" if 'matching_results' in st.session_state else "⏳ 待处理")

            

if __name__ == "__main__":
    logger.info("开始运行应用")
    main()
    logger.info("应用运行结束")

#streamlit run agent/streamlit_app.py