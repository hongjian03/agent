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
from agent_case_match7 import (
    TAG_SYSTEM,
    process_student_case,
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
                    st.write("📋 需求导向标签：", ", ".join(tags.get("DemandOriented", [])))
                    
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
                    if "名校专家" in output_tags:
                        result_row["名校专家"] = "名校专家" if "名校专家" in tags.get("schoolLevel", []) else ""
                    if "顶级名校猎手" in output_tags:
                        result_row["顶级名校猎手"] = "顶级名校猎手" if "顶级名校猎手" in tags.get("schoolLevel", []) else ""
                    if "博士专家" in output_tags:
                        result_row["博士专家"] = "博士专家" if "博士专家" in tags.get("SpecialProjects", []) else ""
                    if "博士攻坚手" in output_tags:
                        result_row["博士攻坚手"] = "博士攻坚手" if "博士攻坚手" in tags.get("SpecialProjects", []) else ""
                    if "低龄留学专家" in output_tags:
                        result_row["低龄留学专家"] = "低龄留学专家" if "低龄留学专家" in tags.get("SpecialProjects", []) else ""
                    if "低龄留学攻坚手" in output_tags:
                        result_row["低龄留学攻坚手"] = "低龄留学攻坚手" if "低龄留学攻坚手" in tags.get("SpecialProjects", []) else ""
                    if "行业经验" in output_tags:
                        result_row["行业经验"] = "专家Lv. 6+" if "专家Lv. 6+" in tags.get("DemandOriented", []) else "资深Lv. 3+" if "资深Lv. 3+" in tags.get("stability", []) else "熟练Lv. 1+"
                    if "文案背景" in output_tags:
                        result_row["文案背景"] = "海归" if "海归" in tags.get("DemandOriented", []) else "名校" if "名校" in tags.get("DemandOriented", []) else ""
                    if "业务单位所在地" in output_tags:
                        # 先定义需要排除的标签
                        exclude_tags = ["专家Lv. 6+", "资深Lv. 3+", "熟练Lv. 1+","海归", "名校"]
                        # 从DemandOriented中筛选出不在排除列表中的标签
                        business_locations = [
                            tag for tag in tags.get("DemandOriented", [])
                            if tag not in exclude_tags
                        ]
                        
                        result_row["业务单位所在地"] = ", ".join(business_locations)

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

        # 更新按钮
        if st.sidebar.button("更新提示词"):
            st.write("更新前的提示词：", st.session_state.prompt_templates.get_template('tag_specialist'))
            prompt_templates.update_template('tag_specialist', tag_backstory)
            prompt_templates.update_template('tag_task', tag_task)
            st.session_state.prompt_templates = prompt_templates
            st.write("更新后的提示词：", st.session_state.prompt_templates.get_template('tag_specialist'))
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

            **2. 标签提取结果示例：**
            ```json
            {
              "recommended_tags": {
                "countries": ["string, 国家标签"],
                "majors": ["string, 专业标签"],
                "schoolLevel": ["string, 院校层次"],
                "SpecialProjects": ["string, 特殊项目标签"],
                "DemandOriented": ["string, 需求导向标签"],
                }
            }
            ```
            """)
        
        # 选择输出标签
        st.sidebar.subheader("输出标签选择")
        output_tags = st.sidebar.multiselect(
            "选择需要输出的标签",
            options=[
                "国家标签", "专业标签", "名校专家", "顶级名校猎手", "博士专家", "博士攻坚手",
                "低龄留学专家", "低龄留学攻坚手", "行业经验","文案背景", "业务单位所在地"
            ],
            default=["国家标签","专业标签", "名校专家", "顶级名校猎手", "博士专家", "博士攻坚手",
                "低龄留学专家", "低龄留学攻坚手", "行业经验","文案背景", "业务单位所在地"]
        )
        
        # 添加选项卡来切换输入方式
        tab1, tab2 = st.tabs(["Excel文件上传", "手动输入"])
        
        with tab1:
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
                                    ) + 2
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

        with tab2:
            # 添加自定义CSS来调整输入框宽度和样式
            st.markdown("""
                <style>
                    /* 调整整体容器的宽度和可调整性 */
                    .main .block-container {
                        max-width: 100%;
                        padding: 2rem;
                        resize: horizontal;  /* 允许水平方向调整大小 */
                        overflow: auto;
                        min-width: 50%;
                    }
                    
                    /* 调整输入框样式 */
                    .stTextInput input {
                        min-width: 180px !important;  /* 设置最小宽度 */
                        width: 100% !important;
                        padding: 8px 12px;
                        font-size: 14px;
                        height: auto !important;
                        white-space: normal;  /* 允许文本换行 */
                        overflow-wrap: break-word;  /* 长单词换行 */
                        resize: both;  /* 允许双向调整大小 */
                        min-height: 40px;
                    }
                    
                    /* 调整下拉框样式 */
                    .stSelectbox select {
                        min-width: 180px !important;
                        width: 100% !important;
                        padding: 8px 12px;
                        font-size: 14px;
                    }
                    
                    /* 调整复选框容器样式 */
                    .stCheckbox {
                        min-width: 100px;
                    }
                    
                    /* 调整列间距和列容器 */
                    .stColumn {
                        padding: 0 5px;
                        min-width: fit-content;
                    }
                    
                    /* 添加滚动样式 */
                    [data-testid="stForm"] {
                        max-height: 800px;
                        overflow: auto;
                        resize: both;  /* 允许表单区域调整大小 */
                        min-height: 400px;
                        border: 1px solid #ddd;
                        padding: 10px;
                    }
                    
                    /* 确保输入框文字可见 */
                    .stTextInput input:focus {
                        min-height: 40px;
                        height: auto !important;
                    }
                    
                    /* 调整表单网格布局 */
                    .stForm > div {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                        gap: 10px;
                    }
                    
                    /* 输入框hover效果 */
                    .stTextInput input:hover {
                        border-color: #09f;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # 初始化session state
            if 'data_rows' not in st.session_state:
                st.session_state.data_rows = 1
            
            # 添加行按钮（在表单外部）
            col1, col2 = st.columns([8,2])
            with col2:
                if st.button("➕ 添加新行", type="primary"):
                    st.session_state.data_rows += 1
            
            # 创建表单
            with st.form("manual_input_form"):
                # 调整列宽比例
                col_widths = [15, 15, 15, 8, 10, 10, 10, 8, 8, 8, 10, 5]  # 总和为122
                cols = st.columns(col_widths)
                
                headers = ["毕业院校", "专业名称", "专业方向", "GPA成绩", "语言考试成绩", 
                          "标化考试成绩", "签约国家", "办理类型", "留学类别唯一", 
                          "是否包含名校", "备注信息", "删除"]
                
                for col, header in zip(cols, headers):
                    col.markdown(f"**{header}**")
                
                # 输入字段部分也使用相同的列宽比例
                manual_data_list = []
                rows_to_delete = []
                
                for i in range(st.session_state.data_rows):
                    cols = st.columns(col_widths)
                    row_data = {}
                    
                    with cols[0]:
                        row_data["毕业院校"] = st.text_input(
                            f"毕业院校_{i}", 
                            key=f"school_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[1]:
                        row_data["专业名称"] = st.text_input(
                            f"专业名称_{i}", 
                            key=f"major_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[2]:
                        row_data["专业方向"] = st.text_input(
                            f"专业方向_{i}", 
                            key=f"major_direction_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[3]:
                        row_data["GPA成绩"] = st.text_input(
                            f"GPA成绩_{i}", 
                            key=f"gpa_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[4]:
                        row_data["语言考试成绩"] = st.text_input(
                            f"语言考试成绩_{i}", 
                            key=f"language_score_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[5]:
                        row_data["标化考试成绩"] = st.text_input(
                            f"标化考试成绩_{i}", 
                            key=f"standardized_score_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[6]:
                        row_data["签约国家"] = st.text_input(
                            f"签约国家_{i}", 
                            key=f"countries_{i}", 
                            placeholder="用逗号分隔",
                            label_visibility="collapsed"
                        )
                    with cols[7]:
                        row_data["办理类型"] = st.text_input(
                            f"办理类型_{i}", 
                            key=f"type_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[8]:
                        row_data["留学类别唯一"] = st.text_input(
                            f"留学类别_{i}", 
                            key=f"study_type_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[9]:
                        row_data["是否包含名校"] = st.selectbox(
                            f"名校_{i}", 
                            ["是", "否"], 
                            key=f"top_school_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[10]:
                        row_data["备注信息"] = st.text_input(
                            f"备注_{i}", 
                            key=f"notes_{i}", 
                            label_visibility="collapsed"
                        )
                    with cols[11]:
                        # 使用 checkbox 替代 button
                        if st.checkbox("删除", key=f"delete_{i}", label_visibility="collapsed"):
                            rows_to_delete.append(i)
                    
                    if i not in rows_to_delete:
                        manual_data_list.append(row_data)
                
                # 提交按钮
                submit_button = st.form_submit_button("分析输入数据")
            
            # 在表单外处理删除操作
            if rows_to_delete:
                st.session_state.data_rows -= len(rows_to_delete)
                # 重新组织数据...

            # 处理提交的数据
            if submit_button:
                try:
                    # 过滤掉空行（至少要有毕业院校和专业名称）
                    valid_data = [
                        {**data, "序号": i+1} 
                        for i, data in enumerate(manual_data_list) 
                        if data["毕业院校"].strip() and data["专业名称"].strip()
                    ]
                    
                    if not valid_data:
                        st.error("请至少输入一行有效数据（必须包含毕业院校和专业名称）")
                        return
                    
                    # 创建DataFrame
                    manual_data = pd.DataFrame(valid_data)
                    
                    st.write("输入数据预览：")
                    st.dataframe(manual_data)
                    
                    # 处理数据
                    with st.spinner("正在分析数据..."):
                        current_prompt = st.session_state.prompt_templates
                        progress_bar = st.empty()
                        status_text = st.empty()
                        
                        results_df = process_excel_custom(
                            manual_data,
                            TAG_SYSTEM,
                            output_tags,
                            progress_bar,
                            status_text,
                            current_prompt
                        )
                        
                        # 显示结果
                        st.success("✅ 分析完成！")
                        st.subheader("分析结果")
                        st.dataframe(results_df)
                        
                        # 提供下载选项
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            results_df.to_excel(writer, index=False, sheet_name='分析结果')
                            workbook = writer.book
                            worksheet = writer.sheets['分析结果']
                            
                            for idx, col in enumerate(results_df.columns):
                                max_length = max(
                                    results_df[col].astype(str).apply(len).max(),
                                    len(str(col))
                                ) + 2
                                worksheet.set_column(idx, idx, max_length)
                        
                        st.download_button(
                            label="下载Excel格式结果",
                            data=buffer.getvalue(),
                            file_name="手动输入分析结果.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                except Exception as e:
                    logger.error(f"处理手动输入数据时出错: {str(e)}")
                    st.error(f"处理数据时出错: {str(e)}")

    except Exception as e:
        logger.error(f"配置初始化失败: {str(e)}")
        st.error(f"配置初始化失败: {str(e)}")
        return

if __name__ == "__main__":
    logger.info("开始运行应用")
    main()
    logger.info("应用运行结束")

#streamlit run agent/streamlit_app.py