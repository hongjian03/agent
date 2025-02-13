import streamlit as st
import pandas as pd
from agent_case_match3 import (
    process_student_case,
    initialize_config, 
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

def process_excel_custom(df, tag_system, output_tags, progress_bar, status_text):
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
                result = process_student_case(student_info, tag_system)
                
                if result["status"] == "success":
                    st.write("✅ 需求分析完成")
                    st.write("🏷️ 标签匹配结果：")
                    tags = result["recommended_tags"]["recommended_tags"]
                    
                    # 显示分析结果
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("国家标签：", ", ".join(tags.get("countries", [])))
                        st.write("专业标签：", ", ".join(tags.get("majors", [])))
                    with col2:
                        st.write("业务能力：", ", ".join(tags.get("businessCapabilities", [])))
                        st.write("服务质量：", ", ".join(tags.get("serviceQualities", [])))
                    
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
                        result_row["名校专家"] = "是" if "名校专家" in tags.get("businessCapabilities", []) else "否"
                    if "博士专家" in output_tags:
                        result_row["博士专家"] = "是" if "博士专家" in tags.get("businessCapabilities", []) else "否"
                    if "低龄留学专家" in output_tags:
                        result_row["低龄留学专家"] = "是" if "低龄留学专家" in tags.get("businessCapabilities", []) else "否"
                    if "签证能手" in output_tags:
                        result_row["签证能手"] = "是" if "签证能手" in tags.get("serviceQualities", []) else "否"
                    if "offer猎手" in output_tags:
                        result_row["offer猎手"] = "是" if "offer猎手" in tags.get("serviceQualities", []) else "否"
                    if "高效文案" in output_tags:
                        result_row["高效文案"] = "是" if "高效文案" in tags.get("serviceQualities", []) else "否"
                    if "口碑文案" in output_tags:
                        result_row["口碑文案"] = "是" if "口碑文案" in tags.get("serviceQualities", []) else "否"
                    if "行业经验" in output_tags:
                        result_row["行业经验"] = "资深" if "资深" in tags.get("stability", []) else "新晋"
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

def main():
    st.title("留学申请需求分析系统")
    
    # 初始化配置
    initialize_config()
    
    # 创建提示词模板实例
    prompt_templates = PromptTemplates()
    
    # 侧边栏：配置部分
    st.sidebar.header("系统配置")
    
    # 提示词配置
    st.sidebar.subheader("1. 提示词配置")
    
    # 提示词示例展示
    with st.sidebar.expander("查看提示词示例"):
        st.markdown("""
        **需求分析报告提取要求示例：**
        ```
        请基于以下维度分析学生申请需求，并生成结构化报告：

        1. 申请背景分析
           - 学术背景：院校档次、专业情况、学历层次
           - 申请意向：目标国家、专业方向、院校定位
           - 特殊情况：跨专业申请、低龄留学等特殊要求

        2. 服务需求分析
           - 核心需求：名校需求、专业匹配度要求、时间要求
           - 特殊要求：地理位置、沟通方式、服务偏好
           - 时间规划：申请截止日期、入学时间、时间紧迫度

        3. 风险评估
           - 申请风险：背景匹配度、竞争情况、跨专业难度
           - 服务风险：时间风险、期望管理、特殊要求的可行性

        4. 顾问匹配建议
           - 优先考虑：最关键的匹配维度
           - 必要条件：必须具备的服务能力
           - 加分项：有助于提升服务质量的特长

        请确保分析全面、逻辑清晰，并突出关键信息。
        ```
        """)
    
    # 需求分析报告提取要求
    analysis_requirements = st.sidebar.text_area(
        "需求分析报告提取要求",
        value="""请基于以下维度分析学生申请需求，并生成结构化报告：

1. 申请背景分析
   - 学术背景：院校档次、专业情况、学历层次
   - 申请意向：目标国家、专业方向、院校定位
   - 特殊情况：跨专业申请、低龄留学等特殊要求

2. 服务需求分析
   - 核心需求：名校需求、专业匹配度要求、时间要求
   - 特殊要求：地理位置、沟通方式、服务偏好
   - 时间规划：申请截止日期、入学时间、时间紧迫度

3. 风险评估
   - 申请风险：背景匹配度、竞争情况、跨专业难度
   - 服务风险：时间风险、期望管理、特殊要求的可行性

4. 顾问匹配建议
   - 优先考虑：最关键的匹配维度
   - 必要条件：必须具备的服务能力
   - 加分项：有助于提升服务质量的特长""",
        height=300
    )
    
    # 标签系统配置
    st.sidebar.subheader("2. 标签系统配置")
    
    # 定义固定的标签池
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
        ]
    }
    
    # 选择输出标签
    st.sidebar.subheader("3. 输出标签选择")
    output_tags = st.sidebar.multiselect(
        "选择需要输出的标签",
        options=[
            "国家标签", "专业标签", "名校专家", "博士专家", 
            "低龄留学专家", "签证能手", "offer猎手", 
            "高效文案", "口碑文案", "行业经验"
        ],
        default=["国家标签", "专业标签", "名校专家", "签证能手", "行业经验"]
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
                    # 更新提示词
                    prompt_templates.update_template('requirement_analyst', analysis_requirements)
                    
                    # 选择指定范围的数据进行处理
                    selected_df = df.iloc[start_idx-1:end_idx]
                    
                    # 处理选中的数据，传入进度条和状态文本
                    results_df = process_excel_custom(selected_df, TAG_SYSTEM, output_tags, progress_bar, status_text)
                    
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

if __name__ == "__main__":
    main() 

#streamlit run agent/streamlit_app.py