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
from agent_case_match8 import (
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
                        exclude_tags = ["专家Lv. 6+", "资深Lv. 3+", "熟练Lv. 1+","海归", "名校","是","否"]
                        # 从DemandOriented中筛选出不在排除列表中的标签
                        business_locations = [
                            tag for tag in tags.get("DemandOriented", [])
                            if tag not in exclude_tags
                        ]
                        
                        result_row["业务单位所在地"] = ", ".join(business_locations)
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
                "低龄留学专家", "低龄留学攻坚手", "行业经验","文案背景", "业务单位所在地",'做过该生所在院校的客户'
            ],
            default=["国家标签","专业标签", "名校专家", "顶级名校猎手", "博士专家", "博士攻坚手",
                "低龄留学专家", "低龄留学攻坚手", "行业经验","文案背景", "业务单位所在地","做过该生所在院校的客户"]
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

            def generate_test_data():
                test_data = [
                    {
                        "毕业院校": "浙江大学",
                        "专业名称": "计算机科学与技术",
                        "专业方向": "人工智能",
                        "GPA成绩": "3.8",
                        "语言考试成绩": "托福100",
                        "标化考试成绩": "GRE320",
                        "签约国家": "美国",
                        "办理类型": "全套服务",
                        "留学类别唯一": "硕士",
                        "是否包含名校": "是",
                        "备注信息": "希望申请TOP30院校"
                    },
                    {
                        "毕业院校": "复旦大学",
                        "专业名称": "金融学",
                        "专业方向": "金融工程",
                        "GPA成绩": "3.9",
                        "语言考试成绩": "雅思7.5",
                        "标化考试成绩": "GMAT720",
                        "签约国家": "英国",
                        "办理类型": "文书服务",
                        "留学类别唯一": "MBA",
                        "是否包含名校": "是",
                        "备注信息": "目标伦敦商学院"
                    },
                    {
                        "毕业院校": "上海交通大学",
                        "专业名称": "机械工程",
                        "专业方向": "智能制造",
                        "GPA成绩": "3.7",
                        "语言考试成绩": "托福95",
                        "标化考试成绩": "GRE315",
                        "签约国家": "德国",
                        "办理类型": "全套服务",
                        "留学类别唯一": "硕士",
                        "是否包含名校": "否",
                        "备注信息": "想申请TU9高校"
                    },
                    {
                        "毕业院校": "武汉大学",
                        "专业名称": "生物技术",
                        "专业方向": "基因工程",
                        "GPA成绩": "3.6",
                        "语言考试成绩": "雅思7.0",
                        "标化考试成绩": "无",
                        "签约国家": "澳大利亚",
                        "办理类型": "申请服务",
                        "留学类别唯一": "博士",
                        "是否包含名校": "是",
                        "备注信息": "有研究经历和论文发表"
                    },
                    {
                        "毕业院校": "南京大学",
                        "专业名称": "环境科学",
                        "专业方向": "环境评估",
                        "GPA成绩": "3.5",
                        "语言考试成绩": "托福90",
                        "标化考试成绩": "GRE310",
                        "签约国家": "加拿大",
                        "办理类型": "全套服务",
                        "留学类别唯一": "硕士",
                        "是否包含名校": "否",
                        "备注信息": "希望同时申请CO-OP项目"
                    },
                    {
                        "毕业院校": "中山大学",
                        "专业名称": "市场营销",
                        "专业方向": "数字营销",
                        "GPA成绩": "3.4",
                        "语言考试成绩": "雅思6.5",
                        "标化考试成绩": "GMAT680",
                        "签约国家": "新加坡",
                        "办理类型": "文书服务",
                        "留学类别唯一": "硕士",
                        "是否包含名校": "是",
                        "备注信息": "想申请新加坡国立大学"
                    },
                    {
                        "毕业院校": "北京师范大学",
                        "专业名称": "教育学",
                        "专业方向": "教育技术",
                        "GPA成绩": "3.8",
                        "语言考试成绩": "托福98",
                        "标化考试成绩": "GRE318",
                        "签约国家": "美国",
                        "办理类型": "全套服务",
                        "留学类别唯一": "博士",
                        "是否包含名校": "是",
                        "备注信息": "有教学经验和研究成果"
                    },
                    {
                        "毕业院校": "四川大学",
                        "专业名称": "软件工程",
                        "专业方向": "云计算",
                        "GPA成绩": "3.6",
                        "语言考试成绩": "雅思7.0",
                        "标化考试成绩": "无",
                        "签约国家": "英国",
                        "办理类型": "申请服务",
                        "留学类别唯一": "硕士",
                        "是否包含名校": "否",
                        "备注信息": "有实习经验"
                    },
                    {
                        "毕业院校": "华东师范大学",
                        "专业名称": "心理学",
                        "专业方向": "认知心理学",
                        "GPA成绩": "3.9",
                        "语言考试成绩": "托福105",
                        "标化考试成绩": "GRE325",
                        "签约国家": "美国",
                        "办理类型": "全套服务",
                        "留学类别唯一": "博士",
                        "是否包含名校": "是",
                        "备注信息": "有多篇论文发表"
                    },
                    {
                        "毕业院校": "东南大学",
                        "专业名称": "电子工程",
                        "专业方向": "集成电路",
                        "GPA成绩": "3.7",
                        "语言考试成绩": "雅思7.5",
                        "标化考试成绩": "GRE315",
                        "签约国家": "香港",
                        "办理类型": "文书服务",
                        "留学类别唯一": "硕士",
                        "是否包含名校": "是",
                        "备注信息": "希望申请港大或港科大"
                    }
                ]
                return test_data

            st.markdown("""
                <style>
                    /* 确保列宽一致性 */
                    .stColumn {
                        padding: 0 5px !important;
                        margin: 0 !important;
                    }
                    
                    /* 输入框样式统一 */
                    .stTextInput input {
                        min-width: 100px !important;
                        width: 100px !important;
                        padding: 8px 12px;
                        font-size: 14px;
                        height: auto !important;
                        white-space: pre-wrap !important;
                    }
                    
                    /* 表单容器样式 */
                    [data-testid="stForm"] {
                        border: 1px solid #ddd;
                        padding: 20px;
                        margin: 10px 0;
                        width: 100%;
                        min-width: 1500px;  /* 设置一个合适的最小宽度 */
                        overflow-x: scroll !important;  /* 强制显示水平滚动条 */
                        display: block;  /* 确保容器正确显示 */
                    }
                    
                    /* 输入区域容器样式 */
                    .input-container {
                        width: 100%;
                        min-width: 1500px;
                        overflow-x: auto;
                        padding: 10px;
                    }
                    
                    /* 输入行样式 */
                    .input-row {
                        display: flex !important;
                        flex-wrap: nowrap !important;
                        gap: 10px;
                        margin-bottom: 10px;
                        min-width: max-content;
                    }

                    /* 调整不同字段的宽度 */
                    .stColumn:nth-child(1) { width: 150px !important; }  /* 毕业院校 */
                    .stColumn:nth-child(2) { width: 150px !important; }  /* 专业名称 */
                    .stColumn:nth-child(3) { width: 150px !important; }  /* 专业方向 */
                    .stColumn:nth-child(4) { width: 80px !important; }   /* GPA */
                    .stColumn:nth-child(5) { width: 120px !important; }  /* 语言成绩 */
                    .stColumn:nth-child(6) { width: 120px !important; }  /* 标化成绩 */
                    .stColumn:nth-child(7) { width: 120px !important; }  /* 签约国家 */
                    .stColumn:nth-child(8) { width: 120px !important; }  /* 办理类型 */
                    .stColumn:nth-child(9) { width: 120px !important; }  /* 留学类别 */
                    .stColumn:nth-child(10) { width: 100px !important; } /* 是否包含名校 */
                    .stColumn:nth-child(11) { width: 200px !important; } /* 备注信息 */
                    .stColumn:nth-child(12) { width: 60px !important; }  /* 删除按钮 */

                    /* 确保内容不会溢出 */
                    .stTextInput {
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }

                    /* 添加滚动条样式 */
                    [data-testid="stForm"]::-webkit-scrollbar {
                        height: 8px;
                    }

                    [data-testid="stForm"]::-webkit-scrollbar-track {
                        background: #f1f1f1;
                        border-radius: 4px;
                    }

                    [data-testid="stForm"]::-webkit-scrollbar-thumb {
                        background: #888;
                        border-radius: 4px;
                    }

                    [data-testid="stForm"]::-webkit-scrollbar-thumb:hover {
                        background: #555;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # 初始化session state
            if 'data_rows' not in st.session_state:
                st.session_state.data_rows = 1
            
            # 添加行按钮（在表单外部）
            col1, col2, col3, col4 = st.columns([6,2,2,2])
            with col2:
                if st.button("➕ 添加新行", type="primary"):
                    st.session_state.data_rows += 1
            with col3:
                if st.button("📥 导入测试数据"):
                    # 获取测试数据
                    test_data = generate_test_data()
                    # 设置行数
                    st.session_state.data_rows = len(test_data)
                    # 将测试数据存入session state，使用正确的key映射
                    key_mapping = {
                        "毕业院校": "school",
                        "专业名称": "major",
                        "专业方向": "major_direction",
                        "GPA成绩": "gpa",
                        "语言考试成绩": "language_score",
                        "标化考试成绩": "standardized_score",
                        "签约国家": "countries",
                        "办理类型": "type",
                        "留学类别唯一": "study_type",
                        "是否包含名校": "top_school",
                        "备注信息": "notes"
                    }
                    
                    for i, data in enumerate(test_data):
                        for zh_key, value in data.items():
                            if zh_key in key_mapping:
                                en_key = key_mapping[zh_key]
                                session_key = f"{en_key}_{i}"
                                st.session_state[session_key] = value
                    st.rerun()
            with col4:
                if st.button("🗑️ 清空数据"):
                    # 清空所有输入框的数据
                    for i in range(st.session_state.data_rows):
                        for key in ["school", "major", "major_direction", "gpa", 
                                  "language_score", "standardized_score", "countries", 
                                  "type", "study_type", "top_school", "notes"]:
                            session_key = f"{key}_{i}"
                            if session_key in st.session_state:
                                st.session_state[session_key] = ""
                    st.session_state.data_rows = 1
                    st.rerun()

            # 创建表单
            with st.form("manual_input_form"):
                # 调整列宽比例
                col_widths = [15, 15, 15, 8, 10, 10, 10, 8, 8, 8, 10, 5]  # 总和为122
                cols = st.columns(col_widths)
                
                headers = ["毕业院校", "专业名称", "专业方向", "GPA成绩", "语言考试成绩", 
                          "标化考试成绩", "签约国家", "办理类型", "留学类别唯一", 
                          "是否包含名校", "备注信息", "删除"]
                
                # 使用容器确保标题对齐
                with st.container():
                    # 标题行
                    for col, header in zip(cols, headers):
                        # 使用固定宽度的div包装标题文本
                        col.markdown(f"""
                            <div style='
                                width: 100%;
                                text-align: left;
                                overflow: hidden;
                                white-space: nowrap;
                                text-overflow: ellipsis;
                                font-weight: bold;
                                margin-bottom: 5px;
                            '>
                                {header}
                            </div>
                        """, unsafe_allow_html=True)
                
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
                            label_visibility="collapsed",
                            placeholder="输入学校名称"  # 添加占位符提示
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
                        row_data["是否包含名校"] = st.text_input(
                            f"是否包含名校_{i}", 
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