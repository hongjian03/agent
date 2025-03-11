import streamlit as st
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import StreamlitCallbackHandler
from langchain.chains import SequentialChain, LLMChain
import os
from typing import Dict, Any, List
import logging
import sys
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


class PromptTemplates:
    def __init__(self):
        # 初始化默认模板
        self.default_templates = {
            'consultant_role': """
            你是一位留学资深咨询顾问，擅长从与学生的聊天记录中提取留学申请的关键信息，提供专业的见解和建议。
            你的主要职责是仔细阅读提供的文档，提取关键信息，分析问题，并提供具体的解决方案和建议。
            
            """,
            
            'consultant_task': """
            我提供的是一份留学顾问老师与学生之间的语音聊天转成文字后的结果，你需要分析这份聊天记录，完成以下几个目标：
            1. 了解文档中学生的意向
            2. 分析此次留学申请服务成功的可能性
            3. 提供具体的解决方案和建议

            输出内容请分点陈述。
            """
        }
        
        # 初始化 session_state 中的模板
        if 'templates' not in st.session_state:
            st.session_state.templates = self.default_templates.copy()

    def get_template(self, template_name: str) -> str:
        return st.session_state.templates.get(template_name, "")

    def update_template(self, template_name: str, new_content: str) -> None:
        st.session_state.templates[template_name] = new_content

    def reset_to_default(self):
        st.session_state.templates = self.default_templates.copy()

class BrainstormingAgent:
    def __init__(self, api_key: str, prompt_templates: PromptTemplates):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model=st.secrets["OPENROUTER_MODEL"],
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.prompt_templates = prompt_templates
        self.setup_chain()

    def setup_chain(self):
        # 创建咨询分析链
        consultant_prompt = ChatPromptTemplate.from_template(
            system=self.prompt_templates.get_template('consultant_role'),
            human="{task}\n\n文档内容：{document_content}"
        )
        
        self.analysis_chain = LLMChain(
            llm=self.llm,
            prompt=consultant_prompt,
            output_key="analysis_result",
            verbose=True
        )

    def process(self, document_content: str, callback=None) -> Dict[str, Any]:
        try:
            # 添加日志记录以便调试
            logger.info(f"Processing document content: {document_content[:100]}...")  # 只记录前100个字符
            
            # 准备输入
            chain_input = {
                "document_content": document_content,
                "task": self.prompt_templates.get_template('consultant_task')
            }
            
            # 执行分析
            result = self.analysis_chain(
                chain_input,
                callbacks=[callback] if callback else None
            )
            
            logger.info("Analysis completed successfully")
            return {
                "status": "success",
                "analysis_result": result["analysis_result"]
            }
                
        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }


def add_custom_css():
    st.markdown("""
    <style>
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
    st.set_page_config(page_title="咨询脑暴平台", layout="wide")
    add_custom_css()
    st.markdown("<h1 class='page-title'>咨询脑暴平台</h1>", unsafe_allow_html=True)
    
    if 'prompt_templates' not in st.session_state:
        st.session_state.prompt_templates = PromptTemplates()
    
    tab1, tab2 = st.tabs(["咨询脑暴助理", "提示词设置"])
    
    with tab1:
        st.title("咨询脑暴助理")
        
        document_content = st.text_area(
            "请输入需要分析的文档内容",
            height=300,
            placeholder="请输入需要分析的文档内容..."
        )
        
        if st.button("开始分析", key="start_analysis"):
            if document_content:
                try:
                    agent = BrainstormingAgent(
                        api_key=st.secrets["OPENROUTER_API_KEY"],
                        prompt_templates=st.session_state.prompt_templates
                    )
                    
                    with st.spinner("正在分析文档..."):
                        st.subheader("🤔 分析过程")
                        with st.expander("查看详细分析过程", expanded=True):
                            callback = StreamlitCallbackHandler(st.container())
                            result = agent.process(document_content, callback=callback)
                            
                            if result["status"] == "success":
                                # 显示分析结果
                                st.markdown("### 📊 分析结果")
                                st.markdown(result["analysis_result"])
                            else:
                                st.error(f"处理失败: {result.get('message', '未知错误')}")
                            
                except Exception as e:
                    st.error(f"处理过程中出错: {str(e)}")
            else:
                st.warning("请先输入文档内容")
    
    with tab2:
        st.title("提示词设置")
        
        prompt_templates = st.session_state.prompt_templates
        
        # 咨询顾问设置
        st.subheader("咨询顾问设置")
        consultant_role = st.text_area(
            "角色设定",
            value=prompt_templates.get_template('consultant_role'),
            height=200,
            key="consultant_role"
        )
        consultant_task = st.text_area(
            "任务说明",
            value=prompt_templates.get_template('consultant_task'),
            height=200,
            key="consultant_task"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("更新提示词", key="update_prompts"):
                prompt_templates.update_template('consultant_role', consultant_role)
                prompt_templates.update_template('consultant_task', consultant_task)
                st.success("✅ 提示词已更新！")
        
        with col2:
            if st.button("重置为默认提示词", key="reset_prompts"):
                prompt_templates.reset_to_default()
                st.rerun()

if __name__ == "__main__":
    main()
