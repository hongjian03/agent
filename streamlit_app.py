__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# 在所有其他导入之前，先初始化环境变量
import streamlit as st
import os

# 立即设置所有需要的API keys
try:
    os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']
    os.environ['OPENAI_API_BASE'] = "https://openrouter.ai/api/v1"
    os.environ['OPENAI_MODEL_NAME'] = "openrouter/google/gemini-2.0-flash-001"
    
    # 如果有其他key，也在这里设置
    if 'GROQ_API_KEY' in st.secrets:
        os.environ['GROQ_API_KEY'] = st.secrets['GROQ_API_KEY']
    if 'DEEPSEEK_API_KEY' in st.secrets:
        os.environ['DEEPSEEK_API_KEY'] = st.secrets['DEEPSEEK_API_KEY']
except Exception as e:
    st.error(f"API密钥配置失败: {str(e)}")
    st.stop()

# 其他导入
import pandas as pd
from agent_case_match3 import (
    TAG_SYSTEM,
    process_student_case,
    PromptTemplates
)
import json
import io

def convert_to_student_info(row):
    """将Excel行数据转换为标准的student_info格式"""
    return {
        "basic_info": {
            "name": str(row.get("序号", "")),  # 用序号作为标识
            "education": {
                "school": row.get("毕业院校", ""),
                "major": row.get("专业名称", ""),
            }
        },
        "application_intent": {
            "target_countries": [row.get("签约国家", "")],
            "degree_level": row.get("办理类型", ""),
            "target_schools": {
                "has_top_schools": "是" if row.get("是否包含名校") == "是" else "否"
            }
        },
        "special_requirements": {
            "special_notes": row.get("备注信息", ""),
            "study_type": row.get("留学类别唯一", "")
        }
    }

def process_excel_custom(df, tag_system, output_tags, progress_bar, status_text, current_prompt):
    """处理Excel数据并返回结果DataFrame"""
    df['序号'] = range(1, len(df) + 1)
    results = []
    
    total_rows = len(df)
    for idx, row in df.iterrows():
        try:
            # 更新进度条和状态文本
            current_progress = (idx + 1) / total_rows
            progress_bar.progress(current_progress)
            status_text.text(f"正在处理第 {idx + 1}/{total_rows} 条数据：{row['毕业院校']} - {row['专业名称']}")
            
            # 转换数据格式
            student_info = {
                "basic_info": {
                    "name": str(row['序号']),
                    "education": {
                        "school": row['毕业院校'],
                        "major": row['专业名称'],
                    }
                },
                "application_intent": {
                    "target_countries": [country.strip() for country in row['签约国家'].split(',')],
                    "degree_level": row['办理类型'],
                    "target_schools": {
                        "has_top_schools": "是" if row['是否包含名校'].lower() in ['yes', 'true', '是'] else "否"
                    }
                },
                "special_requirements": {
                    "special_notes": str(row.get('备注信息', '')),
                    "study_type": row['留学类别唯一']
                }
            }
            
            # 处理单个学生案例
            with st.expander(f"第 {idx + 1} 条：{row['毕业院校']} - {row['专业名称']}", expanded=False):
                st.write("正在分析需求...")
                result = process_student_case(student_info, tag_system, current_prompt)
                
                if result["status"] == "success":
                    st.write("✅ 需求分析完成")
                    st.write("🏷️ 标签匹配结果：")
                    tags = result["recommended_tags"]["recommended_tags"]
                    
                    # 简化标签显示
                    st.write("国家标签：", ", ".join(tags.get("countries", [])))
                    st.write("专业标签：", ", ".join(tags.get("majors", [])))
                    
                    # 其他标签直接显示存在的标签
                    business_tags = []
                    if "名校专家" in tags.get("businessCapabilities", []):
                        business_tags.append("名校专家")
                    if "博士专家" in tags.get("businessCapabilities", []):
                        business_tags.append("博士专家")
                    if "低龄留学专家" in tags.get("businessCapabilities", []):
                        business_tags.append("低龄留学专家")
                    
                    service_tags = []
                    if "offer猎手" in tags.get("serviceQualities", []):
                        service_tags.append("offer猎手")
                    if "获签能手" in tags.get("serviceQualities", []):
                        service_tags.append("获签能手")
                    if "高效文案" in tags.get("serviceQualities", []):
                        service_tags.append("高效文案")
                    if "口碑文案" in tags.get("serviceQualities", []):
                        service_tags.append("口碑文案")
                    
                    # 显示存在的标签
                    if business_tags:
                        st.write("业务标签：", ", ".join(business_tags))
                    if service_tags:
                        st.write("服务标签：", ", ".join(service_tags))
                    
                    # 显示行业经验
                    stability = tags.get("stability", [])
                    if stability:
                        st.write("行业经验：", stability[0])
                    
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
                        result_row["名校专家"] = "名校专家" if "名校专家" in tags.get("businessCapabilities", []) else ""
                    if "博士专家" in output_tags:
                        result_row["博士专家"] = "博士专家" if "博士专家" in tags.get("businessCapabilities", []) else ""
                    if "低龄留学专家" in output_tags:
                        result_row["低龄留学专家"] = "低龄留学专家" if "低龄留学专家" in tags.get("businessCapabilities", []) else ""
                    if "获签能手" in output_tags:
                        result_row["获签能手"] = "获签能手" if "获签能手" in tags.get("serviceQualities", []) else ""
                    if "offer猎手" in output_tags:
                        result_row["offer猎手"] = "offer猎手" if "offer猎手" in tags.get("serviceQualities", []) else ""
                    if "高效文案" in output_tags:
                        result_row["高效文案"] = "高效文案" if "高效文案" in tags.get("serviceQualities", []) else ""
                    if "口碑文案" in output_tags:
                        result_row["口碑文案"] = "口碑文案" if "口碑文案" in tags.get("serviceQualities", []) else ""
                    if "行业经验" in output_tags:
                        result_row["行业经验"] = "专家Lv. 6+" if "专家Lv. 6+" in tags.get("stability", []) else "资深Lv. 3+" if "资深Lv. 3+" in tags.get("stability", []) else "熟练Lv. 1+"
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
    st.title("留学申请需求分析系统")
    
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
            st.success("✅ API配置成功")
        
        # 创建提示词模板实例
        prompt_templates = PromptTemplates()
        
        # 侧边栏：配置部分
        st.sidebar.header("系统配置")
        
        # 提示词配置
        st.sidebar.subheader("1. 提示词配置")
        
        # 分析结果示例展示
        with st.sidebar.expander("查看分析结果示例"):
            st.markdown("""
            **1. 需求分析报告示例：**
            ```json
            {
              "申请需求分析": {
                "申请背景": {
                  "院校水平": "985高校",
                  "专业情况": "计算机科学，跨专业申请AI",
                  "学术表现": "GPA 3.8/4.0，有研究经历",
                  "语言成绩": "TOEFL 100，GRE 320"
                },
                "申请目标": {
                  "国家倾向": "主要申请美国，备选英国",
                  "院校定位": "80%为Top50院校",
                  "专业选择": "CS与AI专业",
                  "申请类型": "硕士申请"
                },
                "时间需求": {
                  "时间紧迫度": "高",
                  "准备充分度": "材料准备充分",
                  "沟通需求": "需要每周沟通"
                },
                "特殊要求": {
                  "名校需求": "强烈要求名校",
                  "签证考虑": "需要特别考虑签证",
                  "文书要求": "要求高质量文书",
                  "其他需求": "需要全程高频指导"
                }
              }
            }
            ```

            **2. 标签提取结果示例：**
            ```json
            {
              "标签推荐": {
                "必选标签": {
                  "countries": ["美国", "英国"],
                  "majors": ["计算机与信息系统"]
                },
                "业务能力": {
                  "selected": ["名校专家"],
                  "reason": "申请Top50院校为主，需要名校申请经验"
                },
                "服务质量": {
                  "selected": ["offer猎手", "高效文案", "获签能手"],
                  "reason": "高标准申请要求，时间紧迫，需要签证支持"
                },
                "行业经验": {
                  "level": "专家Lv. 6+",
                  "reason": "高难度综合案例，需要丰富经验"
                }
              },
              "匹配说明": {
                "核心标签": "名校专家+高效文案",
                "匹配理由": "基于申请难度和时间要求",
                "特别建议": "建议安排每周固定沟通"
              }
            }
            ```
            """)
        
        # 需求分析报告提取要求
        new_prompt = st.sidebar.text_area(
            "需求分析报告提取要求",
            value=prompt_templates.get_template('requirement_analyst'),
            height=300
        )
        
        # 添加生效按钮
        if st.sidebar.button("更新提示词"):
            # 更新提示词模板
            prompt_templates.update_template('requirement_analyst', new_prompt)
            st.sidebar.success("✅ 提示词已更新！")
            # 显示当前生效的提示词
            with st.sidebar.expander("当前生效的提示词"):
                st.write(prompt_templates.get_template('requirement_analyst'))
        
        # 标签系统配置
        
        
        # 选择输出标签
        st.sidebar.subheader("2. 输出标签选择")
        output_tags = st.sidebar.multiselect(
            "选择需要输出的标签",
            options=[
                "国家标签", "专业标签", "名校专家", "博士专家", 
                "低龄留学专家", "获签能手", "offer猎手", 
                "高效文案", "口碑文案", "行业经验"
            ],
            default=["国家标签", "专业标签", "名校专家", "博士专家", "低龄留学专家","offer猎手", "获签能手", "高效文案", "口碑文案", "行业经验"]
        )
        
        # 文件上传和处理部分
        uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
        
        if uploaded_file is not None:
            try:
                # 读取Excel文件
                df = pd.read_excel(uploaded_file)
                st.write("原始数据预览：")
                st.dataframe(df.head())
                
                # 添加数据范围选择
                total_rows = len(df)
                st.write(f"总数据条数：{total_rows}")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_idx = st.number_input("从第几条开始", 
                                              min_value=1, 
                                              max_value=total_rows,
                                              value=1)
                with col2:
                    end_idx = st.number_input("到第几条结束", 
                                            min_value=start_idx, 
                                            max_value=total_rows,
                                            value=min(start_idx + 9, total_rows))
                
                # 添加分析按钮
                analyze_button = st.button("开始分析")
                
                if analyze_button:
                    # 验证选择范围
                    if start_idx > end_idx:
                        st.error("起始位置不能大于结束位置")
                        return
                    
                    # 创建进度条和状态文本
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    with st.spinner(f"正在处理第 {start_idx} 到第 {end_idx} 条数据..."):
                        # 获取当前生效的提示词
                        current_prompt = prompt_templates.get_template('requirement_analyst')
                        
                        # 选择指定范围的数据进行处理
                        selected_df = df.iloc[start_idx-1:end_idx]
                        
                        # 处理选中的数据，传入当前生效的提示词
                        results_df = process_excel_custom(
                            selected_df, 
                            TAG_SYSTEM, 
                            output_tags, 
                            progress_bar, 
                            status_text,
                            current_prompt  # 传入当前生效的提示词
                        )
                        
                        # 清除进度条和状态文本
                        progress_bar.empty()
                        status_text.empty()
                        
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
                st.error(f"处理文件时出错: {str(e)}")

    except Exception as e:
        st.error(f"配置初始化失败: {str(e)}")
        return

if __name__ == "__main__":
    main() 

#streamlit run agent/streamlit_app.py