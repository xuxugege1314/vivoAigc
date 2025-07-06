import os
import uuid
import time
import re
import requests
import streamlit as st
from dotenv import load_dotenv
import json

# 加载环境变量
load_dotenv()
APP_ID = '2025955768'
APP_KEY = 'PuuEHYGErjQqgGyt'

# 扩展平台配置模板
PLATFORM_PROMPTS = {
    "小红书": {
        "template": """
        你是一个小红书博主，请根据主题「{topic}」生成一篇文案，要求：
        1. 包含1个吸引眼球的标题(带1-2个表情符号)
        2. 正文结构：
           - 痛点场景引发共鸣(2-3行)
           - 解决方案制造惊喜(3-5个要点，每个要点用✅/🌟等符号标注)
           - 使用效果对比(before/after体)
           - 行动号召+@官方账号
        3. 语言风格：口语化、活泼，使用网络流行语和表情符号
        4. 添加3-5个相关话题标签(以#开头)
        """,
        "format_rules": [
            (r"(\d+\.\s*)", r"✅ \1"),  # 给要点添加符号
            (r"(#\w+)", r"\n\1"),  # 话题标签换行
            (r"([^。！？])(\n|$)", r"\1✨\2"),  # 句尾添加表情
            (r"@([\w\u4e00-\u9fa5]+)", r"👑@\1")  # 官方账号装饰
        ],
        "example": {
            "input": "冬季护肤流程",
            "output": """
            ❄️冬日护肤秘籍｜干皮也能水润过冬！✨

            💔冬天皮肤干到起皮？上妆就卡粉？
            ✅ 晨间流程：
            1. 温和洁面(芙丽芳丝)
            2. 精华水湿敷3分钟(SK-II神仙水)
            3. 面霜锁水(科颜氏高保湿)

            ✅ 夜间加强：
            1. 精油按摩(林清轩山茶花油)
            2. 厚敷睡眠面膜(兰芝)
            3. 唇部护理(凡士林)

            🌟对比效果：
            之前：起皮卡粉→现在：水光肌质感！

            👉赶紧收藏这套流程@美妆薯 
            #干皮救星 #冬季护肤 #保湿秘籍
            """
        }
    },
    "知乎": {
        "template": """
        你是一个知乎答主，请针对主题「{topic}」生成一篇深度回答，要求：
        1. 标题采用「如何...?」或「为什么...?」的疑问句式
        2. 正文结构：
           - 引言：200字左右背景介绍
           - 核心论点(分3-5点，每点包含数据或案例支持)
           - 争议性观点(需标注「可能存在争议」)
           - 总结与建议
        3. 包含2-3个专业文献引用(格式：[作者, 年份])
        4. 语言风格：专业、理性、有深度
        5. 结尾添加「编辑于XXXX年XX月XX日」
        """,
        "format_rules": [
            (r"(\d+\.\s*)", r"• \1"),
            (r"^([^•].+)$", r"  \1"),
            (r"(\[.+\])", r"\n> 引用：\1")
        ],
        "example": {
            "input": "新能源汽车技术趋势",
            "output": """
            • 2025年新能源汽车会彻底取代燃油车吗？

              根据国际能源署(IEA)报告，2023年全球新能源车渗透率已达18%...

            • 技术突破点：
              1. 固态电池商业化：丰田计划2025年量产[张教授, 2023]
              2. 800V高压平台普及：小鹏G9充电5分钟续航200km
              3. 智能座舱AI化：GPT车机系统上线

            ⚠️可能存在争议：
              氢能源路线更适合商用车领域...

            • 总结：
              电动化趋势不可逆，但完全替代仍需10年...

            编辑于2023年12月15日
            """
        }
    },
    "短视频脚本": {
        "template": """
        你是一个短视频编导，请根据主题「{topic}」生成一个1-2分钟的短视频脚本，要求：
        1. 脚本结构：
           [开场：3-5秒吸引注意]
           [痛点：10秒引发共鸣]
           [解决方案：30秒核心内容]
           [效果展示：15秒对比]
           [行动号召：5秒]
        2. 包含分镜头描述(场景+人物+台词+时长)
        3. 添加3处以上字幕提示和特效建议
        4. 语言风格：简洁有力，有画面感
        """,
        "format_rules": [
            (r"\[(.*?)\]", r"🎬 \1"),  # 添加镜头符号
            (r"字幕：", "✏️字幕："),
            (r"特效：", "✨特效：")
        ],
        "example": {
            "input": "咖啡拉花教学",
            "output": """
            🎬开场：[特写：奶泡倒入咖啡，3秒]
            ✏️字幕：3步学会天鹅拉花！

            🎬痛点：[近景：失败拉花镜头，5秒]
            ✏️字幕：总是拉花失败？

            🎬解决方案：
            [镜头1：手部特写-打奶泡角度45°，8秒]
            ✏️字幕：温度控制在60℃
            [镜头2：俯拍-拉花手法慢动作，12秒]
            ✏️字幕：手腕匀速移动

            🎬效果展示：[对比镜头：失败vs成功，10秒]
            ✏️字幕：坚持练习一周！

            🎬结尾：[全景：完美天鹅拉花，5秒]
            ✏️字幕：关注学更多技巧！
            """
        }
    },
    "微博": {
        "template": """
        你是一个微博博主，请根据主题「{topic}」生成一条微博，要求：
        1. 140字以内
        2. 包含1-2个热点话题标签（如#今日热点#）
        3. 使用疑问句或感叹句开头引发互动
        4. 结尾引导粉丝互动（例如：你怎么看？）
        5. 添加1-2个表情符号
        """,
        "format_rules": [
            (r"#(\w+)#", r"\n#\1# "),  # 话题标签格式化
            (r"@(\w+)", r"@\1 ")  # 提及账号格式化
        ],
        "example": {
            "input": "暴雨天气安全提醒",
            "output": """
            ⚠️北京暴雨红色预警！你准备好了吗？

            • 尽量减少外出
            • 驾车避开积水路段
            • 遇险情拨12345

            #北京暴雨# 评论区报平安↓
            🙏愿所有人平安！
            """
        }
    },
    "电商文案": {
        "template": """
        你是一个电商文案写手，请为「{topic}」生成商品描述，要求：
        1. 突出3大核心卖点（用⭐️标注）
        2. 包含促销信息（限时折扣/买赠活动）
        3. 规格参数表格（产品参数：值）
        4. 使用场景描述（解决XX问题）
        5. 售后保障说明（7天无理由）
        6. 添加行动号召按钮（立即抢购）
        """,
        "format_rules": [
            (r"卖点\d：", "⭐️ "),  # 卖点符号
            (r"参数：", "\n| 参数 | 值 |\n| ---- | ---- |\n"),  # 生成表格
            (r"立即抢购", "🔥立即抢购🔥")
        ],
        "example": {
            "input": "无线蓝牙耳机",
            "output": """
            ⭐️ 超长续航：连续听歌12小时
            ⭐️ 主动降噪：沉浸式体验
            ⭐️ 防水防汗：运动无忧

            🚀限时特惠：原价399→券后299！

            | 参数 | 值 |
            | ---- | ---- |
            | 重量 | 5g/只 |
            | 蓝牙 | 5.2 |
            | 防水 | IPX5 |

            🎧通勤/运动/学习 全能伴侣！

            ✅7天无理由 ✅1年质保
            🔥立即抢购🔥
            """
        }
    }
}


def generate_signature(app_id, app_key, method, uri, params):
    """生成蓝心API签名"""
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex[:8]

    canonical_query = "&".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )

    signing_string = f"{method}\n{uri}\n{canonical_query}\n{app_id}\n{timestamp}\n" \
                     f"x-ai-gateway-app-id:{app_id}\nx-ai-gateway-timestamp:{timestamp}\n" \
                     f"x-ai-gateway-nonce:{nonce}"

    digest = hmac.new(
        app_key.encode('utf-8'),
        signing_string.encode('utf-8'),
        hashlib.sha256
    ).digest()

    return {
        "X-AI-GATEWAY-APP-ID": app_id,
        "X-AI-GATEWAY-TIMESTAMP": timestamp,
        "X-AI-GATEWAY-NONCE": nonce,
        "X-AI-GATEWAY-SIGNED-HEADERS": "x-ai-gateway-app-id;x-ai-gateway-timestamp;x-ai-gateway-nonce",
        "X-AI-GATEWAY-SIGNATURE": base64.b64encode(digest).decode(),
        "Content-Type": "application/json"
    }


def call_vivo_blueLM(prompt, model="vivo-BlueLM-TB-Pro", temperature=0.7, max_tokens=1024):
    """调用蓝心大模型API"""
    url = "https://api-ai.vivo.com.cn/vivogpt/completions"
    method = "POST"
    uri = "/vivogpt/completions"

    params = {"requestId": str(uuid.uuid4())}
    headers = generate_signature(APP_ID, APP_KEY, method, uri, params)

    payload = {
        "prompt": prompt,
        "model": model,
        "sessionId": str(uuid.uuid4()),
        "extra": {
            "temperature": temperature,
            "max_new_tokens": max_tokens,
            "top_p": 0.9
        }
    }

    try:
        response = requests.post(
            url,
            params=params,
            json=payload,
            headers=headers,
            timeout=45
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                return result["data"]["content"]
            else:
                error_msg = result.get("msg", "Unknown error")
                if "rate limit" in error_msg.lower():
                    return "⚠️ 请求过于频繁，请稍后再试"
                return f"API错误: {error_msg}"
        return f"HTTP错误: {response.status_code}"
    except Exception as e:
        return f"请求异常: {str(e)}"


def format_content(content, platform):
    """根据平台规则格式化内容"""
    if platform not in PLATFORM_PROMPTS:
        return content

    rules = PLATFORM_PROMPTS[platform].get("format_rules", [])
    for pattern, replacement in rules:
        try:
            content = re.sub(pattern, replacement, content)
        except:
            continue

    return content.strip()


def generate_content(topic, platform, style=None):
    """生成平台特定内容"""
    if platform not in PLATFORM_PROMPTS:
        return f"暂不支持{platform}平台"

    template = PLATFORM_PROMPTS[platform]["template"]
    prompt = template.format(topic=topic)

    # 添加风格要求
    if style:
        prompt += f"\n特别要求: {style}"

    # 调用大模型
    content = call_vivo_blueLM(prompt)

    # 格式化内容
    return format_content(content, platform)


def main():
    """Streamlit应用界面"""
    st.set_page_config(
        page_title="智能写作助手Pro",
        layout="wide",
        page_icon="✍️"
    )

    # 自定义CSS样式
    st.markdown("""
    <style>
    .platform-card {
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .platform-card:hover {
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        transform: translateY(-3px);
    }
    .stButton>button {
        background: linear-gradient(45deg, #6a11cb 0%, #2575fc 100%);
        border: none;
    }
    .stTextArea textarea {
        min-height: 300px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("✍️ 智能写作助手Pro")
    st.caption("基于蓝心大模型70B的专业内容创作工具")

    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 创作配置")
        platform = st.selectbox("选择平台", list(PLATFORM_PROMPTS.keys()))

        with st.expander("高级设置"):
            temperature = st.slider("创意度", 0.1, 1.0, 0.7)
            style = st.text_input("特殊风格要求", placeholder="如：加入网络流行语/使用专业术语")

            if platform == "知乎":
                st.checkbox("包含数据引用", value=True)
                st.checkbox("添加争议观点", value=True)
            elif platform == "电商文案":
                st.checkbox("生成参数表格", value=True)
                st.checkbox("添加促销信息", value=True)

        st.divider()
        st.write("### 平台案例展示")
        selected_example = st.selectbox(
            "查看案例",
            [f"{p} - {PLATFORM_PROMPTS[p]['example']['input']}" for p in PLATFORM_PROMPTS]
        )

        # 显示案例
        if selected_example:
            platform_name = selected_example.split(" - ")[0]
            example = PLATFORM_PROMPTS[platform_name]["example"]
            with st.expander(f"{platform_name}案例详情", expanded=True):
                st.write(f"**主题**: {example['input']}")
                st.text_area("生成内容",
                             value=example['output'],
                             height=250,
                             disabled=True)

    # 主内容区
    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("📝 输入主题/关键词", placeholder="例如：夏日防晒攻略、数码产品评测")
    with col2:
        st.write("\n")
        generate_btn = st.button("生成内容", type="primary", use_container_width=True)

    # 生成内容
    if generate_btn:
        if not topic.strip():
            st.warning("请输入主题内容")
            st.stop()

        with st.spinner(f"正在生成{platform}风格内容..."):
            start_time = time.time()
            content = generate_content(topic, platform, style)
            elapsed = time.time() - start_time

            # 显示结果
            st.success(f"生成成功！耗时: {elapsed:.1f}秒")
            st.subheader(f"🎯 {platform}风格内容预览")

            # 平台特定渲染
            if platform == "电商文案" and isinstance(content, tuple):
                st.markdown(content[0])
                st.markdown("**产品参数**")
                st.markdown(content[1])
            else:
                # 创建可编辑文本区域
                edited_content = st.text_area("内容预览", value=content, height=400)

            # 一键复制按钮
            if st.button("📋 一键复制内容", use_container_width=True):
                # 使用JavaScript实现复制功能
                js_code = f"""
                <script>
                function copyToClipboard() {{
                    const textArea = document.createElement('textarea');
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                }}
                copyToClipboard();
                </script>
                """
                st.components.v1.html(js_code, height=0)
                st.success("内容已复制到剪贴板！")
    # 添加平台能力说明
    st.divider()
    st.subheader("📚 平台创作能力说明")

    cols = st.columns(len(PLATFORM_PROMPTS))
    for i, (platform_name, config) in enumerate(PLATFORM_PROMPTS.items()):
        with cols[i]:
            with st.container():
                st.markdown(f"<div class='platform-card'>", unsafe_allow_html=True)
                st.markdown(f"### {platform_name}")
                st.caption(config["template"].split("\n")[2].strip())
                if "example" in config:
                    with st.expander("示例预览"):
                        st.text(config["example"]["output"][:150] + "...")
                st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    import random
    import base64
    import hashlib
    import hmac

    main()
