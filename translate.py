import streamlit as st
import base64
import fitz  # PyMuPDF
import openai
from openai import OpenAI
import time
from typing import Dict, List
from pathlib import Path
import tempfile
from bs4 import BeautifulSoup
import markdown
import pandas as pd
# --------------------------
# 初始化设置
# --------------------------
st.set_page_config(layout="wide")
#openai.api_key = st.secrets["OPENAI_API_KEY"]  # 通过Secrets管理API密钥

model_select=st.selectbox('选择模型',['星火Ultra4','星火X1','硅基DeepseekV3'])
if model_select=='星火Ultra4':
    key="hIzyVkYVmiGvBehhJkBU:RdddcXKbqJqFqudYhLlg"
    base="https://spark-api-open.xf-yun.com/v1"
    modelID="4.0Ultra"
elif model_select=='星火X1':
    key="YQFYZsnrVytVHEtqZdGO:HnswhxkyGvCgyrObRDlP"
    base="https://spark-api-open.xf-yun.com/v2"
    modelID="x1"
elif model_select=="硅基DeepseekV3":
    key="sk-bdzavtijxudzetsrmecqowvsjajjdloogkuhvkvnlslffrcg"
    base="https://api.siliconflow.cn/v1"
    modelID="deepseek-ai/DeepSeek-V3"
client = OpenAI(api_key=key,
                        base_url=base)
modelID=modelID
#modelname="通义千问32B"
# --------------------------
# PDF处理模块
# --------------------------
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text=[]
st.session_state.pdf_text=[]

def pdf_to_base64(uploaded_file) -> str:
    """将PDF文件转换为Base64编码"""
    return base64.b64encode(uploaded_file.read()).decode('utf-8')

def extract_pdf_text(uploaded_file) -> Dict[int, str]:
    """提取PDF每页文本"""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    return {page_num: page.get_text() for page_num, page in enumerate(doc)}
def chat_with_history(msg,client,modelID):
    global st
    try:
        completion = client.chat.completions.create(
        model = modelID,  # your model endpoint ID
        messages = msg)
        #chain = prompt | llm
        resp=completion.choices[0].message.content
        resp=resp.split('</think>')[-1].strip()
        msg.append({"role": "assistant", "content": resp})
        #st.write(resp)
        return (resp,msg)
    except:
        #raise
        with st.chat_message("assistant"):
            tips='网络错误，请重试'
            st.markdown(tips)
            st.stop()

def chat_a_time(sys_prompt,user_prompt,client,modelID):
    spraw=sys_prompt[0]
    sp=sys_prompt[1]
    cmd=user_prompt

    global st
    print('len text=',len(user_prompt))
    try:
        if len(user_prompt)<4096:
            completion = client.chat.completions.create(
            model = modelID,  # your model endpoint ID
            messages = [
                {"role": "system", "content": spraw},
                {"role": "user", "content": cmd},],)
            #chain = prompt | llm
            resp=completion.choices[0].message.content
            resp=resp.split('</think>')[-1].strip()
            #st.write(resp)
            return resp
        else:
            
            cut=4096
            len_cut=len(user_prompt)// cut
            cut_list=[]
            for i in range(len_cut+1):
                #print([i*cut,(i+1)*cut])
                cut_list.append(user_prompt[i*cut:(i+1)*cut]  )
            messages = []
            messages.append({"role": "system", "content": spraw})
            tips0=f'共有{len(cut_list)}段文本，'
            print('len cut=',len(cut_list))
            for n,fragement in enumerate(cut_list):
                n=n+1
                if n==1:
                    tips=tips0+f'以下是第{n}段内容：'
                else:
                    messages[0]={"role": "system", "content": sp}
                    his=messages[-1]["content"]
                    tips=tips0+f"""以下是第{n}段内容，同时提供给你先前总结的历史信息和表格：
                    ```{his}```。
                    以下是新的文献内容，根据新内容继续思考，更新回答："""
                    messages=[messages[0]]
                with st.spinner(f'Running chunk {n} in prompt: {tips} '):
                    messages.append(
                    {"role": "user", "content": tips+fragement})
                    print((tips+fragement)[:200])
                    resp,messages=chat_with_history(messages,client,modelID)

                    with st.expander(f'总结{n}'):
                        st.markdown(resp)
                    messages=[messages[0],messages[-1]]
                print("CHAT with history",resp[:200])
            return resp
    except:
        raise
        with st.chat_message("assistant"):
            tips='网络错误，请重试'
            st.markdown(tips)
            
            st.stop()

# --------------------------
# AI翻译模块
# --------------------------
#@st.cache_data(ttl=3600)
def translate_with_gpt(text: str, _progress_bar) -> str:
    global client
    """调用OpenAI进行翻译"""
    for i in range(3):
        time.sleep(0.1)
        _progress_bar.progress((i + 1) * 33)
    sp="你是一位专业翻译，请将以下内容精准翻译为中文，保留专业术语："
    cmd=text
    completion = client.chat.completions.create(
        model = modelID,  # your model endpoint ID
        messages = [
            {"role": "system", "content": sp},
            {"role": "user", "content": cmd},],)
    resp=completion.choices[0].message.content
    resp=resp.split('</think>')[-1].strip()
    return resp

# --------------------------
# 界面布局
# --------------------------
def main():
    st.title("智能PDF翻译器 📚⇄🌐")
    
    # 上传文件
    uploaded_file = st.file_uploader("选择待上传的PDF文件", type=['pdf'])
    
    if uploaded_file is not None:
        # 初始化会话状态
        st.session_state.pdf_text = extract_pdf_text(uploaded_file)
        
        # 双列布局
        col1, col2= st.columns([1, 5])
        
        with col1:
            # PDF预览
            st.subheader("PDF预览")
            #base64_pdf = pdf_to_base64(uploaded_file)
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                fp = Path(tmp_file.name)
                fp.write_bytes(uploaded_file.getvalue())
                with open(tmp_file.name, "rb") as f:
                    base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" ' \
                          f'width="100%" height="800" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)
        
        with col2:
            # 文本处理区
            st.subheader("工具列表")
            tools=st.selectbox('',['翻译工具','总结工具'])
            if tools=='翻译工具':
                # 页数选择
                selected_page = st.selectbox(
                    "选择页码",
                    options=list(st.session_state.pdf_text.keys()),
                    format_func=lambda x: f"第 {x + 1} 页"
                )
                
                # 显示当前页文本
                page_text = st.session_state.pdf_text[selected_page]
                selected_text = st.text_area(
                    "编辑/选择需要翻译的内容",
                    value=page_text,
                    height=300,
                    help="可直接在此框内选择部分文本进行翻译"
                )
                
                # 翻译功能
                if st.button("🚀 执行翻译"):
                    if len(selected_text) < 10:
                        st.warning("请选择至少10个字符的内容")
                    else:
                        progress_bar = st.progress(0)
                        try:
                            translated = translate_with_gpt(selected_text, progress_bar)
                            progress_bar.empty()
                            st.subheader("翻译结果")
                            st.markdown(f"{translated}")
                            st.success("翻译完成！")
                        except Exception as e:
                            st.error(f"翻译失败：{str(e)}")
            elif tools=='总结工具':
                spraw="""逐段阅读这篇文献，总结核心内容，理解在这篇文献中，PPI的使用怎样影响人体菌群。
                需要总结的关键点包括:
                ```干预药物类别	干预药物名称	样本类型	样本数量	测序方法	菌群名称	菌群丰度变化	变化方向	统计显著性（给出P值）  原文表述（具体到句子）````，

                给出受到影响的具体菌群名称（含英文原文）、变化方向、统计显著性（注意给出P值），给出原文中对于以上信息的英文原句，必须是**原文完整句子**，
                - 句子必须：
                - 直接复制原文，**不可删减、截断或改写**；
                同时从文本中寻找线索回答问题：干预药物名称、样本类型、样本数量、菌群的测序方法是什么（注意辨别是16S测序/宏基因组/还是其它测序方法），同样给出原文中对应的英文原句子。
                使用表格的形式进行总结。
                如果数据来自Figure或Table或本文中的研究结果，标注为“本研究”，如果来自对前人研究的引用，标注引用来源及“引用”，**必须在单独一列中标注来源，禁止省略来源标注**。
                
                回答尽量简洁精练。"""
                #**使用中文进行思考，表头必须是中文。但表格内容遵循原文英文表述。**。

                sp="""逐段阅读这篇文献，总结核心内容，理解在这篇文献中，PPI的使用怎样影响人体菌群。
                需要总结的关键点包括:
                ```干预药物类别	干预药物名称	样本类型	样本数量	测序方法	菌群名称	菌群丰度变化	变化方向	统计显著性（给出P值）  原文表述（具体到句子）````，

                给出受到影响的具体菌群名称（含英文原文）、变化方向、统计显著性（注意给出P值），给出原文中对于以上信息的英文原句，必须是**原文完整句子**，
                - 句子必须：
                - 直接复制原文，**不可删减、截断或改写**；
                同时从文本中寻找线索回答问题：干预药物名称、样本类型、样本数量、菌群的测序方法是什么（注意辨别是16S测序/宏基因组/还是其它测序方法），同样给出原文中对应的英文原句子。
                使用表格的形式进行总结。
                如果数据来自Figure或Table或本文中的研究结果，标注为“本研究”，如果来自对前人研究的引用，标注引用来源及“引用”，**必须在单独一列中标注来源，禁止省略来源标注**。
                回答尽量简洁精练。
                提供给你的信息包括：系统提示、上一段文献中总结的信息、当前文献。
                只根据提供给你的文本回答问题，不要联想和推测。
                注意保留历史表格并整合到新表格中输出，保留历史信息，并根据新文本的信息更新表格，
                不要丢失任何菌群和药物的历史信息。
                如果历史记录中已经提供了某个结论对应的P值等，不要丢失。
                更新信息时，遵循以下原则：
                对于同一个菌群来自同一个信息源的信息（如同为本文研究结果），优先级：使用具体的信息（如P值数值或方向）大于模糊的表述（未明确、不确定等文字表述）；
                对于同一个菌群来自不同信息源的信息（如本文研究结果、前人研究数据），应该保留所有信息，不要覆盖历史信息。
                如果当前文本中没有新的信息或部分信息没有更新，也保留历史信息中已经总结的表格并输出。
                检查对比输出的表格和历史表格，确保输出的表格中没有丢失历史信息。
                注意：历史表格中的所有内容必须全部包括在本次输出的表格中，不要省略。
                注意保留历史记录中搜索到的药物和菌群名称，尽量具体。
                要求：
                1. 仔细对比新旧信息，决定是否需要更新
                2. 无论是否需要更新，都必须输出完整表格
                3. 如果内容有更新，在表格中修改相应部分
                4. 如果内容无更新，保持原表格不变但仍需完整输出;
                5. **严格禁止省略任何内容**，包括未修改的部分;
                如果新内容与旧内容一致，**仍需完整保留旧内容**
                如果新内容有更新，修改对应部分，但**其他部分必须原样保留**;
                6. **禁止使用以下表述**：
                - "其余部分同上"
                - "历史数据保留，此处省略"
                - "未修改部分与之前一致"
                - 任何形式的省略说明
                7. 用Markdown格式输出完整表格；
                文献如下：
                """
                paper=''.join(list(st.session_state.pdf_text.values()))
                if st.button("🚀 执行总结"):
                    with st.spinner('正在总结文献内容'):
                        resp=chat_a_time([spraw,sp],paper,client,modelID)
                    with st.expander('总结'):
                        st.markdown(resp)
                    st.download_button(
                        label="Download report",
                        data=resp.encode('utf-8'),
                        file_name=f'{uploaded_file.name}.txt',
                        mime='text/txt',
                    )
                    

if __name__ == "__main__":
    main()