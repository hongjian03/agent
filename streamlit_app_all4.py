import sys
import streamlit as st
import os
import logging

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
from agent_case_match10 import (
    TAG_SYSTEM,
    process_student_case,
    process_student_case2,
    PromptTemplates
)
import json
import io

def convert_to_student_info(row):
    """将Excel行数据转换为标准的student_info格式"""
    student_info = {
        "basic_info": {
            "name": str(row['序号']),
            "education": {
                "school": row['毕业院校'],
                "major_name": row['专业名称'],
                "major_orientation": row['专业方向'],
                "gpa": row['GPA成绩'],
                "language_score": row['语言考试成绩'],
                "Standardized_exam_scores": row['标化考试成绩'],
                
            }
        },
        "application_intent": {
            "target_countries": [country.strip() for country in row['签约国家'].split(',')],
            "degree_level": row['留学类别唯一'],
            "target_schools": {
                "has_top_schools": "是" if str(row['是否包含名校']).lower().strip() in [
                    'yes', 'true', '是', '1', 'y', 't', 'true', '包含',
                    'include', 'included', '需要', 'need', 'needed',
                    '要', '对', '好', 'ok', '√', '✓', '有'
                ] else "否"
            }
        },
        "special_requirements": {
            "special_notes": str(row.get('备注信息', '')),
        }
    }
    return student_info

def process_excel_custom(df, tag_system, output_tags, progress_bar, status_text, current_prompt):
    """处理Excel数据并返回结果DataFrame"""
    df['序号'] = range(1, len(df) + 1)
    results = []
    
    total_rows = len(df)
    for idx, row in df.iterrows():
        try:
            # 更新进度条和状态文本
            current_progress = (idx - df.index[0] + 1) / total_rows  # 修正进度计算
            progress_bar.progress(current_progress)
            status_text.text(f"正在处理第 {idx + 1}/{df.index[-1] + 1} 条数据：{row['毕业院校']} - {row['专业名称']}")
            
            # 转换数据格式
            student_info = convert_to_student_info(row)
            print(student_info)
            # 处理单个学生案例
            with st.expander(f"第 {idx + 1} 条：{row['毕业院校']} - {row['专业名称']}", expanded=False):
                st.write("正在分析标签...")
                result = process_student_case(student_info, tag_system, current_prompt)
                
                if result["status"] == "success":
                    st.write("✅ 标签匹配完成")
                    st.write("🏷️ 标签匹配结果：")
                    tags = result["recommended_tags"]["recommended_tags"]
                    
                    # 展示所有标签类别
                    st.write("🌏 国家标签：", ", ".join(tags.get("countries", [])))
                    st.write("📚 专业标签：", ", ".join(tags.get("majors", [])))
                    st.write("🏫 院校层次：", ", ".join(tags.get("schoolLevel", [])))
                    st.write("🎯 特殊项目标签：", ", ".join(tags.get("SpecialProjects", [])))
                    st.write("📋 行业经验标签：", ", ".join(tags.get("Industryexperience", [])))
                    st.write("📋 顾问背景标签：", ", ".join(tags.get("Consultantbackground", [])))
                    st.write("📋 业务所在地：", ", ".join(tags.get("businessLocation", [])))
                    
                    # 构建结果行
                    result_row = {
                        "序号": row['序号'],
                        "毕业院校": row['毕业院校'],
                        "专业名称": row['专业名称'],
                        "签约国家": row['签约国家'],
                        "办理类型": row['办理类型']
                    }
                    
                    # 添加选中的输出标签
                    if "国家标签" in output_tags:
                        result_row["国家标签"] = ", ".join(tags.get("countries", []))
                    if "专业标签" in output_tags:
                        result_row["专业标签"] = ", ".join(tags.get("majors", []))
                    if "名校申请经验丰富" in output_tags:
                        # 使用列表推导式找出所有包含"名校申请经验丰富"的标签
                        matching_tags = [tag for tag in tags.get("schoolLevel", []) if "名校申请经验丰富" in tag]
                        result_row["名校申请经验丰富"] = "、".join(matching_tags) if matching_tags else ""
                    if "顶级名校成功案例" in output_tags:
                        matching_tags = [tag for tag in tags.get("schoolLevel", []) if "顶级名校成功案例" in tag]
                        result_row["顶级名校成功案例"] = "、".join(matching_tags) if matching_tags else ""
                    if "博士成功案例" in output_tags:
                        matching_tags = [tag for tag in tags.get("SpecialProjects", []) if "博士成功案例" in tag]
                        result_row["博士成功案例"] = "、".join(matching_tags) if matching_tags else ""
                    if "博士申请经验" in output_tags:
                        matching_tags = [tag for tag in tags.get("SpecialProjects", []) if "博士申请经验" in tag]
                        result_row["博士申请经验"] = "、".join(matching_tags) if matching_tags else ""
                    if "低龄留学成功案例" in output_tags:
                        matching_tags = [tag for tag in tags.get("SpecialProjects", []) if "低龄留学成功案例" in tag]
                        result_row["低龄留学成功案例"] = "、".join(matching_tags) if matching_tags else ""
                    if "低龄留学申请经验" in output_tags:
                        matching_tags = [tag for tag in tags.get("SpecialProjects", []) if "低龄留学申请经验" in tag]
                        result_row["低龄留学申请经验"] = "、".join(matching_tags) if matching_tags else ""
                    if "行业经验" in output_tags:
                        result_row["行业经验"] = "专家Lv. 6+" if "专家Lv. 6+" in tags.get("Industryexperience", []) else "资深Lv. 3+" if "资深Lv. 3+" in tags.get("Industryexperience", []) else "熟练Lv. 1+"
                    if "文案背景" in output_tags:
                        result_row["文案背景"] = "海归" if "海归" in tags.get("Consultantbackground", [])  else ""
                    if "业务单位所在地" in output_tags:
                        result_row["业务单位所在地"] = tags.get("businessLocation", [])
                    if "做过该生所在院校的客户" in output_tags:
                        result_row["做过该生所在院校的客户"] = ""

                else:
                    st.write("❌ 处理失败")
                    st.error(result["error_message"])
                    result_row = {
                        "序号": row['序号'],
                        "毕业院校": row['毕业院校'],
                        "专业名称": row['专业名称'],
                        "签约国家": row['签约国家'],
                        "办理类型": row['办理类型'],
                        "处理状态": "失败",
                        "错误信息": result["error_message"]
                    }
            
            results.append(result_row)
            
        except Exception as e:
            st.error(f"处理第 {idx + 1} 条数据时出错: {str(e)}")
            results.append({
                "序号": row.get('序号', idx + 1),
                "毕业院校": row.get('毕业院校', ''),
                "专业名称": row.get('专业名称', ''),
                "签约国家": row.get('签约国家', ''),
                "办理类型": row.get('办理类型', ''),
                "处理状态": "失败",
                "错误信息": str(e)
            })
    
    return pd.DataFrame(results)

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
    
    # 在系统配置部分添加模型选择
    st.sidebar.subheader("模型配置")
    model_options = [
        "google/gemini-2.0-flash-001",
        "deepseek/deepseek-r1-distill-llama-70b:free",
        "deepseek/deepseek-r1-distill-llama-70b",
        "deepseek/deepseek-r1:free",
        "deepseek/deepseek-r1",
        "anthropic/claude-3.5-haiku",
        "openai/gpt-4o-mini",
        ""
    ]
    
    selected_model = st.sidebar.selectbox(
        "选择模型",
        options=model_options,
        index=model_options.index(st.session_state.current_model) if st.session_state.current_model in model_options else 0
    )
    
    # 添加应用按钮
    if st.sidebar.button("应用模型设置"):
        st.session_state.current_model = selected_model
        os.environ['OPENAI_MODEL_NAME'] = selected_model
        st.sidebar.success(f"✅ 已切换到模型: {selected_model}")
        st.rerun()  # 重新运行应用以应用新设置
    
    # 显示当前使用的模型
    st.sidebar.info(f"当前使用模型: {st.session_state.current_model}")
    
    # 创建两个标签页
    system_tab1, system_tab2 = st.tabs(["标签匹配系统", "顾问匹配系统"])
    
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
            
            # 侧边栏配置部分
            st.sidebar.header("系统配置")
            
            # 标签提取配置
            st.sidebar.subheader("标签提取配置")

            # Agent backstory
            with st.sidebar.expander("标签专家角色设定", expanded=False):
                tag_backstory = st.text_area(
                    "角色设定",
                    value=prompt_templates.get_template('tag_specialist'),
                    height=200
                )

            # Task description
            with st.sidebar.expander("标签提取任务说明", expanded=False):
                tag_task = st.text_area(
                    "任务说明",
                    value=prompt_templates.get_template('tag_task'),
                    height=200
                )

            with st.sidebar.expander("标签输出结构"):
                tag_recommendation_structure = st.text_area(
                    "标签输出结构",
                    value=prompt_templates.get_template('tag_recommendation_structure'),
                    height=200
                )

            # 更新按钮
            if st.sidebar.button("更新提示词", key="update_prompts"):
                prompt_templates.update_template('tag_specialist', tag_backstory)
                prompt_templates.update_template('tag_task', tag_task)
                prompt_templates.update_template('tag_recommendation_structure', tag_recommendation_structure)
                st.session_state.prompt_templates = prompt_templates
                st.write("更新后的提示词：", st.session_state.prompt_templates.get_template('tag_specialist'))
                st.write("更新后的标签提取任务说明：", st.session_state.prompt_templates.get_template('tag_task'))
                st.write("更新后的标签输出结构：", st.session_state.prompt_templates.get_template('tag_recommendation_structure'))
                st.sidebar.success("✅ 提示词已更新！")
            
            # 分析结果示例展示
            with st.sidebar.expander("查看分析结果示例"):
                st.markdown("""
                **1. 输入数据格式示例：**
                ```json
                student_info = {
                        "basic_info": {
                            "name": str(row['序号']),
                            "education": {
                                "school": row['毕业院校'],
                                "major_name": row['专业名称'],
                                "major_orientation": row['专业方向'],
                                "gpa": row['GPA成绩'],
                                "language_score": row['语言考试成绩'],
                                "Standardized_exam_scores": row['标化考试成绩'],
                                
                            }
                        },
                        "application_intent": {
                            "target_countries": [country.strip() for country in row['签约国家'].split(',')],
                            "degree_level": row['留学类别唯一'],
                            "target_schools": {
                                "has_top_schools": "是" if str(row['是否包含名校']).lower().strip() in [
                                    'yes', 'true', '是', '1', 'y', 't', 'true', '包含',
                                    'include', 'included', '需要', 'need', 'needed',
                                    '要', '对', '好', 'ok', '√', '✓', '有'
                                ] else "否"
                            }
                        },
                        "special_requirements": {
                            "special_notes": str(row.get('备注信息', '')),
                        }
                    }
                ```
                **2. 标签体系示例：**
                ```json
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
                        "熟练Lv. 1+", "资深Lv. 3+", "专家Lv. 6+"
                    ],
                    "Consultantbackground": [
                        "海归"
                    ],
                    "businessLocation": [
                        "业务单位所在地"
                    ]
                }
                **3. 标签提取结果示例：**
                ```json
                {
                  "recommended_tags": {
                    "countries": ["string, 国家标签"],
                    "majors": ["string, 专业标签"],
                    "schoolLevel": ["string, 院校层次"],
                    "SpecialProjects": ["string, 特殊项目标签"],
                    "Industryexperience": ["string, 行业经验标签"],
                    "Consultantbackground  ": ["string, 顾问背景标签"],
                    "businessLocation": ["string, 业务所在地"],
                  }
                }
                ```
                """)
            
            # 选择输出标签
            st.sidebar.subheader("输出标签选择")
            output_tags = st.sidebar.multiselect(
                "选择需要输出的标签",
                options=[
                    "国家标签", "专业标签", "名校申请经验丰富", "顶级名校成功案例", "博士成功案例", "博士申请经验",
                    "低龄留学成功案例", "低龄留学申请经验", "行业经验","文案背景", "业务单位所在地",'做过该生所在院校的客户'
                ],
                default=["国家标签","专业标签", "名校申请经验丰富", "顶级名校成功案例", "博士成功案例", "博士申请经验",
                    "低龄留学成功案例", "低龄留学申请经验", "行业经验","文案背景", "业务单位所在地","做过该生所在院校的客户"]
            )
            
            # 添加选项卡来切换输入方式
            input_tab1, input_tab2 = st.tabs(["Excel文件上传", "手动输入"])
            
            with input_tab1:
                # 文件上传和处理部分
                uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
                
                if uploaded_file is not None:
                    try:
                        logger.info(f"开始处理上传的文件: {uploaded_file.name}")
                        # 读取Excel文件
                        df = pd.read_excel(uploaded_file)
                        st.write("原始数据预览：")
                        st.dataframe(df.head())

                        # 显示数据总条数
                        total_rows = len(df)
                        st.info(f"📊 成功加载数据：共 {total_rows} 条记录")

                        
                        # 选择数据范围
                        start_idx = st.number_input("起始索引", min_value=1, max_value=len(df), value=1)
                        end_idx = st.number_input("结束索引", min_value=start_idx, max_value=len(df), value=min(len(df), start_idx+9))
                        
                        # 创建进度条
                        progress_bar = st.progress(0)
                        
                        # 添加分析按钮
                        analyze_button = st.button("开始分析")
                        
                        if analyze_button:
                            # 验证选择范围
                            if start_idx > end_idx:
                                st.error("起始位置不能大于结束位置")
                                return
                            
                            # 验证提示词是否正确传递
                            st.write("当前使用的提示词：")
                            st.write("标签专家角色设定：", st.session_state.prompt_templates.get_template('tag_specialist'))
                            st.write("标签提取任务说明：", st.session_state.prompt_templates.get_template('tag_task'))
                            
                            with st.spinner(f"正在处理第 {start_idx} 到第 {end_idx} 条数据..."):
                                # 使用session_state中的prompt_templates
                                current_prompt = st.session_state.prompt_templates
                                
                                # 选择指定范围的数据进行处理
                                selected_df = df.iloc[start_idx-1:end_idx]
                                
                                # 处理选中的数据
                                results_df = process_excel_custom(
                                    selected_df, 
                                    TAG_SYSTEM, 
                                    output_tags, 
                                    progress_bar, 
                                    st.empty(),
                                    current_prompt  # 传递当前的prompt_templates
                                )
                                
                                # 清除进度条和状态文本
                                progress_bar.empty()
                                st.empty().empty()
                                
                                # 显示完成消息
                                st.success("✅ 分析完成！")
                                
                                # 显示结果预览
                                st.subheader("分析结果预览")
                                st.dataframe(results_df)
                                
                                # 处理完成后，保存带标签的数据
                                st.session_state.tagged_data = results_df  # 保存处理后的数据
                                
                                # 保存Excel文件
                                output_filename = f'标签分析结果_{start_idx}-{end_idx}.xlsx'
                                
                                # 使用BytesIO避免保存到磁盘
                                buffer = io.BytesIO()
                                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                    results_df.to_excel(writer, index=False, sheet_name='分析结果')
                                    # 获取workbook和worksheet对象
                                    workbook = writer.book
                                    worksheet = writer.sheets['分析结果']
                                    
                                    # 调整列宽
                                    for idx, col in enumerate(results_df.columns):
                                        max_length = max(
                                            results_df[col].astype(str).apply(len).max(),
                                            len(str(col))
                                        )
                                        worksheet.set_column(idx, idx, max_length)
                                
                                # 下载按钮
                                st.download_button(
                                    label="下载Excel格式结果",
                                    data=buffer.getvalue(),
                                    file_name=output_filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                    
                    except Exception as e:
                        logger.error(f"处理文件时出错: {str(e)}")
                        st.error(f"处理文件时出错: {str(e)}")

            with input_tab2:
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
                
                # 添加示例按钮
                
                #if st.button("加载示例案例", key="load_example"):
                #    example_case = """这是一位来自浙江大学的大四学生，就读于计算机科学与技术专业，专业方向是人工智能。
                #        学术表现优秀，GPA达到3.8/4.0，托福成绩100分，GRE总分320分。

                #        申请意向：
                #        - 目标国家：美国
                #        - 申请项目：计算机科学硕士
                #        - 申请数量：计划申请12所学校
                #        - 包含名校：希望申请TOP30院校
                #        - 入学时间：2025年秋季入学

                #        特殊说明：
                #        - 有机器学习相关研究经历
                #        - 曾在字节跳动实习3个月
                #        - 希望能申请到好的学校，对结果有较高期望
                #        - 需要详细的申请规划和指导"""
                    
                #    st.session_state.student_case = example_case
                #    st.rerun()
                
                # 添加处理按钮
                if st.button("开始分析", key="start_analysis") and student_case:
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
                                
                                
                                # 显示原始输出
                                st.subheader("模型输出结果")
                                st.code(result["raw_output"], language="json")
                                
                                # 处理模型输出
                            try:
                                # 清理JSON字符串
                                json_str = result["raw_output"].replace('```json', '').replace('```', '').strip()
                                # 解析JSON
                                output_dict = json.loads(json_str)

                                
                                # 创建DataFrame
                                df = pd.DataFrame({
                                    "序号": [', '.join(output_dict["recommended_tags"]["index"])],
                                    "国家标签": [', '.join(output_dict["recommended_tags"]["countries"])],  # 直接join整个列表
                                    "专业标签": [', '.join(output_dict["recommended_tags"]["majors"])],
                                    "院校层次": [', '.join(output_dict["recommended_tags"]["schoolLevel"])],
                                    "特殊项目标签": [', '.join(output_dict["recommended_tags"]["SpecialProjects"])],
                                    "行业经验": [', '.join(output_dict["recommended_tags"]["Industryexperience"])],
                                    "文案背景": [', '.join(output_dict["recommended_tags"]["Consultantbackground"])],
                                    "业务单位所在地": [', '.join(output_dict["recommended_tags"]["businessLocation"])],
                                })
                                
                                # 存入session_state
                                st.session_state.tagged_data = df
                                
                                # 显示处理后的数据
                                st.subheader("处理后的标签数据")
                                st.dataframe(df)
                                
                                st.success("✅ 数据已处理并保存到内存中，可用于后续匹配")
                                
                            except Exception as e:
                                st.error(f"处理模型输出时出错: {str(e)}")
                                st.error("请检查模型输出格式是否符合预期")
                        
                        except Exception as e:
                            st.error(f"处理过程中出错: {str(e)}")
                    
                elif not student_case and st.button("开始分析"):
                    st.warning("请先输入学生案例信息")
        except Exception as e:
            logger.error(f"配置初始化失败: {str(e)}")
            st.error(f"配置初始化失败: {str(e)}")
            return

    with system_tab2:
        from match2 import (
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
                        matching_results = Consultant_matching(
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
                                        st.subheader("顾问原始标签")
                                        st.write(f"**顾问业务单位:** {consultant['businessunits']}")
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
                                            ('名校申请经验丰富', '名校申请经验丰富'), 
                                            ('顶级名校成功案例', '顶级名校成功案例'),
                                            ('博士成功案例', '博士成功案例'), 
                                            ('博士申请经验', '博士申请经验'),
                                            ('低龄留学成功案例', '低龄留学成功案例'), 
                                            ('低龄留学申请经验', '低龄留学申请经验')
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
                                                target_columns = ['国家标签', '专业标签', '名校申请经验丰富', 
                                                                '顶级名校成功案例', '博士成功案例', '博士申请经验',
                                                                '低龄留学成功案例', '低龄留学申请经验', '行业经验']
                                                
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
                                            adjusted_country_score = consultant.get('adjusted_country_score', 0)
                                            adjusted_special_score = consultant.get('adjusted_special_score', 0)
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
                                            st.markdown(f"标签匹配小计: {total_score}分")
                                            st.markdown(f"**匹配率与覆盖率:**")
                                            st.markdown(f"- 国家标签: 匹配率 {country_match_ratio:.2f} (匹配/总量: {country_count_need}/{country_count_total}), 覆盖率 {consultant['country_coverage_ratio']:.2f}")
                                            st.markdown(f"- 特殊标签: 匹配率 {special_match_ratio:.2f} (匹配/总量: {special_count_need}/{special_count_total}), 覆盖率 {consultant['special_coverage_ratio']:.2f}")
                                            
                                            # 计算最终得分并显示计算公式
                                            tag_weighted = adjusted_country_score * country_match_ratio * country_coverage_ratio * 0.5 + adjusted_special_score * special_match_ratio * special_coverage_ratio * 0.5 + other_tags_score
                                            workload_score = consultant.get('workload_score', 0)
                                            personal_score = consultant.get('personal_score', 0)
                                            
                                            # 显示工作量和个人意愿评分
                                            st.write(f"**工作量评分:** {workload_score}分")
                                            st.write(f"**个人意愿评分:** {personal_score}分")
                                            
                                            # 计算最终得分并显示计算公式
                                            final_score = tag_weighted + workload_score * 0.3 + personal_score * 0.2
                                            st.write(f"""({adjusted_country_score}) × ({country_match_ratio}) × ({country_coverage_ratio}) × 0.5 + 
                                                      ({adjusted_special_score}) × ({special_match_ratio}) × ({special_coverage_ratio}) × 0.5 + 
                                                      ({other_tags_score}) + ({workload_score}) × 0.3 + ({personal_score}) × 0.2 = {final_score:.1f}分""")
                                            
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