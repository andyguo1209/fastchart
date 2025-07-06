"""
Chatbot Arena (battle) tab.
Users chat with two anonymous models.
"""

import json
import time
import re
import os
from glob import glob
import subprocess

import gradio as gr
import numpy as np
import matplotlib.pyplot as plt

from fastchat.constants import (
    MODERATION_MSG,
    CONVERSATION_LIMIT_MSG,
    SLOW_MODEL_MSG,
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    CONVERSATION_TURN_LIMIT,
    SURVEY_LINK,
)
from fastchat.model.model_adapter import get_conversation_template
from fastchat.serve.gradio_block_arena_named import flash_buttons
from fastchat.serve.gradio_web_server import (
    State,
    bot_response,
    get_conv_log_filename,
    no_change_btn,
    enable_btn,
    disable_btn,
    invisible_btn,
    enable_text,
    disable_text,
    acknowledgment_md,
    get_ip,
    get_model_description_md,
)
from fastchat.serve.remote_logger import get_remote_logger
from fastchat.utils import (
    build_logger,
    moderation_filter,
)

logger = build_logger("gradio_web_server_multi", "logs/gradio_web_server_multi.log")

num_sides = 2
enable_moderation = False
anony_names = ["", ""]
models = []


def set_global_vars_anony(enable_moderation_):
    global enable_moderation
    enable_moderation = enable_moderation_


def load_demo_side_by_side_anony(models_, url_params):
    global models
    models = models_

    states = [None] * num_sides
    selector_updates = [
        gr.Markdown(visible=True),
        gr.Markdown(visible=True),
    ]

    return states + selector_updates


def vote_last_response(states, vote_type, model_selectors, request: gr.Request):
    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "type": vote_type,
            "models": [x for x in model_selectors],
            "states": [x.dict() for x in states],
            "ip": get_ip(request),
        }
        fout.write(json.dumps(data) + "\n")
    get_remote_logger().log(data)

    gr.Info(
        "🎉 Thanks for voting! Your vote shapes the leaderboard, please vote RESPONSIBLY."
    )
    if ":" not in model_selectors[0]:
        for i in range(5):
            names = (
                "### Model A: " + states[0].model_name,
                "### Model B: " + states[1].model_name,
            )
            # yield names + ("",) + (disable_btn,) * 4
            yield names + (disable_text,) + (disable_btn,) * 5
            time.sleep(0.1)
    else:
        names = (
            "### Model A: " + states[0].model_name,
            "### Model B: " + states[1].model_name,
        )
        # yield names + ("",) + (disable_btn,) * 4
        yield names + (disable_text,) + (disable_btn,) * 5


def leftvote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"leftvote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "leftvote", [model_selector0, model_selector1], request
    ):
        yield x


def rightvote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"rightvote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "rightvote", [model_selector0, model_selector1], request
    ):
        yield x


def tievote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"tievote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "tievote", [model_selector0, model_selector1], request
    ):
        yield x


def bothbad_vote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"bothbad_vote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "bothbad_vote", [model_selector0, model_selector1], request
    ):
        yield x


def regenerate(state0, state1, request: gr.Request):
    logger.info(f"regenerate (anony). ip: {get_ip(request)}")
    states = [state0, state1]
    if state0.regen_support and state1.regen_support:
        for i in range(num_sides):
            states[i].conv.update_last_message(None)
        return (
            states + [x.to_gradio_chatbot() for x in states] + [""] + [disable_btn] * 6
        )
    states[0].skip_next = True
    states[1].skip_next = True
    return states + [x.to_gradio_chatbot() for x in states] + [""] + [no_change_btn] * 6


def clear_history(request: gr.Request):
    logger.info(f"clear_history (anony). ip: {get_ip(request)}")
    return (
        [None] * num_sides
        + [None] * num_sides
        + anony_names
        + [enable_text]
        + [invisible_btn] * 4
        + [disable_btn] * 2
        + [""]
        + [enable_btn]
    )


def share_click(state0, state1, model_selector0, model_selector1, request: gr.Request):
    logger.info(f"share (anony). ip: {get_ip(request)}")
    if state0 is not None and state1 is not None:
        vote_last_response(
            [state0, state1], "share", [model_selector0, model_selector1], request
        )


# 模型采样权重配置
# 格式: {"模型名称": 权重值}
# 权重值越大，该模型被选中的概率越高
SAMPLING_WEIGHTS = {
    # 配置你的模型权重
    "HKGAI-V1-Thinking": 1.0,
    "HKGAI-V1": 1.0,
}

# 目标模型采样权重会被提升
# 格式: {"模型名称": ["目标模型1", "目标模型2"]}
BATTLE_TARGETS = {
    # 示例配置:
    # "gpt-4": ["gpt-3.5-turbo", "claude-3-sonnet"],
}

# 严格的目标模型匹配模式
BATTLE_STRICT_TARGETS = {
    # 示例配置:
    # "gpt-4": ["gpt-*", "claude-*"],
}

# 匿名模型列表
ANON_MODELS = []

# 需要采样提升的模型（权重会乘以5）
SAMPLING_BOOST_MODELS = []

# 故障模型不会被采样
OUTAGE_MODELS = []


def get_sample_weight(model, outage_models, sampling_weights, sampling_boost_models=[]):
    if model in outage_models:
        return 0
    weight = sampling_weights.get(model, 0)
    if model in sampling_boost_models:
        weight *= 5
    return weight


def is_model_match_pattern(model, patterns):
    flag = False
    for pattern in patterns:
        pattern = pattern.replace("*", ".*")
        if re.match(pattern, model) is not None:
            flag = True
            break
    return flag


def get_battle_pair(
    models, battle_targets, outage_models, sampling_weights, sampling_boost_models
):
    if len(models) == 1:
        return models[0], models[0]

    model_weights = []
    for model in models:
        weight = get_sample_weight(
            model, outage_models, sampling_weights, sampling_boost_models
        )
        model_weights.append(weight)
    total_weight = np.sum(model_weights)
    model_weights = model_weights / total_weight
    # print(models)
    # print(model_weights)
    chosen_idx = np.random.choice(len(models), p=model_weights)
    chosen_model = models[chosen_idx]
    # for p, w in zip(models, model_weights):
    #     print(p, w)

    rival_models = []
    rival_weights = []
    for model in models:
        if model == chosen_model:
            continue
        if model in ANON_MODELS and chosen_model in ANON_MODELS:
            continue
        if chosen_model in BATTLE_STRICT_TARGETS:
            if not is_model_match_pattern(model, BATTLE_STRICT_TARGETS[chosen_model]):
                continue
        if model in BATTLE_STRICT_TARGETS:
            if not is_model_match_pattern(chosen_model, BATTLE_STRICT_TARGETS[model]):
                continue
        weight = get_sample_weight(model, outage_models, sampling_weights)
        if (
            weight != 0
            and chosen_model in battle_targets
            and model in battle_targets[chosen_model]
        ):
            # boost to 20% chance
            weight = 0.5 * total_weight / len(battle_targets[chosen_model])
        rival_models.append(model)
        rival_weights.append(weight)
    # for p, w in zip(rival_models, rival_weights):
    #     print(p, w)
    rival_weights = rival_weights / np.sum(rival_weights)
    rival_idx = np.random.choice(len(rival_models), p=rival_weights)
    rival_model = rival_models[rival_idx]

    swap = np.random.randint(2)
    if swap == 0:
        return chosen_model, rival_model
    else:
        return rival_model, chosen_model


def add_text(
    state0, state1, model_selector0, model_selector1, text, request: gr.Request
):
    ip = get_ip(request)
    logger.info(f"add_text (anony). ip: {ip}. len: {len(text)}")
    states = [state0, state1]
    model_selectors = [model_selector0, model_selector1]

    # Init states if necessary
    if states[0] is None:
        assert states[1] is None

        model_left, model_right = get_battle_pair(
            models,
            BATTLE_TARGETS,
            OUTAGE_MODELS,
            SAMPLING_WEIGHTS,
            SAMPLING_BOOST_MODELS,
        )
        
        # 添加调试信息
        logger.info(f"Selected models: {model_left}, {model_right}")
        logger.info(f"Available models: {models}")
        
        # 添加错误处理
        try:
            states = [
                State(model_left),
                State(model_right),
            ]
            logger.info(f"States initialized successfully: {[s.model_name for s in states]}")
        except Exception as e:
            logger.error(f"Failed to initialize states: {e}")
            # 如果初始化失败，返回错误状态
            return (
                [None, None]
                + [None, None]
                + ["", None]
                + [no_change_btn] * 6
                + [f"Error: Failed to initialize models {model_left}, {model_right}"]
            )

    if len(text) <= 0:
        for i in range(num_sides):
            states[i].skip_next = True
        return (
            states
            + [x.to_gradio_chatbot() for x in states]
            + ["", None]
            + [
                no_change_btn,
            ]
            * 6
            + [""]
        )

    model_list = [states[i].model_name for i in range(num_sides)]
    # turn on moderation in battle mode
    all_conv_text_left = states[0].conv.get_prompt()
    all_conv_text_right = states[0].conv.get_prompt()
    all_conv_text = (
        all_conv_text_left[-1000:] + all_conv_text_right[-1000:] + "\nuser: " + text
    )
    # 暂时禁用内容审核，避免OPENAI_API_KEY错误
    flagged = False
    if flagged:
        logger.info(f"violate moderation (anony). ip: {ip}. text: {text}")
        # overwrite the original text
        text = MODERATION_MSG

    conv = states[0].conv
    if (len(conv.messages) - conv.offset) // 2 >= CONVERSATION_TURN_LIMIT:
        logger.info(f"conversation turn limit. ip: {get_ip(request)}. text: {text}")
        for i in range(num_sides):
            states[i].skip_next = True
        return (
            states
            + [x.to_gradio_chatbot() for x in states]
            + [CONVERSATION_LIMIT_MSG]
            + [
                no_change_btn,
            ]
            * 6
            + [""]
        )

    text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
    for i in range(num_sides):
        states[i].conv.append_message(states[i].conv.roles[0], text)
        states[i].conv.append_message(states[i].conv.roles[1], None)
        states[i].skip_next = False

    hint_msg = ""
    for i in range(num_sides):
        if "deluxe" in states[i].model_name:
            hint_msg = SLOW_MODEL_MSG
    return (
        states
        + [x.to_gradio_chatbot() for x in states]
        + [""]
        + [
            disable_btn,
        ]
        * 6
        + [hint_msg]
    )


def bot_response_multi(
    state0,
    state1,
    temperature,
    top_p,
    max_new_tokens,
    request: gr.Request,
):
    logger.info(f"bot_response_multi (anony). ip: {get_ip(request)}")

    if state0 is None or state0.skip_next:
        # This generate call is skipped due to invalid inputs
        state0_chatbot = state0.to_gradio_chatbot() if state0 is not None else None
        state1_chatbot = state1.to_gradio_chatbot() if state1 is not None else None
        yield (
            state0,
            state1,
            state0_chatbot,
            state1_chatbot,
        ) + (no_change_btn,) * 6
        return

    states = [state0, state1]
    gen = []
    for i in range(num_sides):
        gen.append(
            bot_response(
                states[i],
                temperature,
                top_p,
                max_new_tokens,
                request,
                apply_rate_limit=False,
                use_recommended_config=True,
            )
        )

    model_tpy = []
    for i in range(num_sides):
        token_per_yield = 1
        if states[i].model_name in [
            "gemini-pro",
            "gemma-1.1-2b-it",
            "gemma-1.1-7b-it",
            "phi-3-mini-4k-instruct",
            "phi-3-mini-128k-instruct",
            "snowflake-arctic-instruct",
        ]:
            token_per_yield = 30
        elif states[i].model_name in [
            "qwen-max-0428",
            "qwen-vl-max-0809",
            "qwen1.5-110b-chat",
            "llava-v1.6-34b",
        ]:
            token_per_yield = 7
        elif states[i].model_name in [
            "qwen2.5-72b-instruct",
            "qwen2-72b-instruct",
            "qwen-plus-0828",
            "qwen-max-0919",
            "llama-3.1-405b-instruct-bf16",
        ]:
            token_per_yield = 4
        model_tpy.append(token_per_yield)

    chatbots = [None] * num_sides
    iters = 0
    while True:
        stop = True
        iters += 1
        for i in range(num_sides):
            try:
                # yield fewer times if chunk size is larger
                if model_tpy[i] == 1 or (iters % model_tpy[i] == 1 or iters < 3):
                    ret = next(gen[i])
                    states[i], chatbots[i] = ret[0], ret[1]
                stop = False
            except StopIteration:
                pass
        yield states + chatbots + [disable_btn] * 6
        if stop:
            break


def build_side_by_side_ui_anony(models):
    notice_markdown = f"""
<div class="hkgai-header">
    <h1>🚀 HKGAI 智能对话平台</h1>
    <h2>👇 开始聊天！</h2>
</div>
"""

    states = [gr.State() for _ in range(num_sides)]
    model_selectors = [None] * num_sides
    chatbots = [None] * num_sides

    gr.Markdown(notice_markdown, elem_id="notice_markdown")

    with gr.Group(elem_id="share-region-anony"):
        with gr.Row():
            for i in range(num_sides):
                label = "Model A" if i == 0 else "Model B"
                with gr.Column():
                    chatbots[i] = gr.Chatbot(
                        label=label,
                        elem_id="chatbot",
                        height=650,
                        show_copy_button=True,
                        latex_delimiters=[
                            {"left": "$", "right": "$", "display": False},
                            {"left": "$$", "right": "$$", "display": True},
                            {"left": r"\(", "right": r"\)", "display": False},
                            {"left": r"\[", "right": r"\]", "display": True},
                        ],
                    )

        with gr.Row():
            for i in range(num_sides):
                with gr.Column():
                    model_selectors[i] = gr.Markdown(
                        anony_names[i], elem_id="model_selector_md"
                    )
        with gr.Row():
            slow_warning = gr.Markdown("")

    with gr.Row():
        leftvote_btn = gr.Button(
            value="👈  A is better", visible=False, interactive=False
        )
        rightvote_btn = gr.Button(
            value="👉  B is better", visible=False, interactive=False
        )
        tie_btn = gr.Button(value="🤝  Tie", visible=False, interactive=False)
        bothbad_btn = gr.Button(
            value="👎  Both are bad", visible=False, interactive=False
        )

    with gr.Row():
        textbox = gr.Textbox(
            show_label=False,
            placeholder="👉 请输入您的问题并按回车键",
            elem_id="input_box",
        )
        send_btn = gr.Button(value="发送", variant="primary", scale=0)

    with gr.Row() as button_row:
        clear_btn = gr.Button(value="🎲 新一轮", interactive=False)
        regenerate_btn = gr.Button(value="🔄  重新生成", interactive=False)
        share_btn = gr.Button(value="📷  分享")

    with gr.Accordion("Parameters", open=False, visible=False) as parameter_row:
        temperature = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=0.7,
            step=0.1,
            interactive=True,
            label="温度",
        )
        top_p = gr.Slider(
            minimum=0.0,
            maximum=1.0,
            value=1.0,
            step=0.1,
            interactive=True,
            label="Top P",
        )
        max_output_tokens = gr.Slider(
            minimum=16,
            maximum=2048,
            value=2000,
            step=64,
            interactive=True,
            label="最大输出长度",
        )

    # Register listeners
    btn_list = [
        leftvote_btn,
        rightvote_btn,
        tie_btn,
        bothbad_btn,
        regenerate_btn,
        clear_btn,
    ]
    leftvote_btn.click(
        leftvote_last_response,
        states + model_selectors,
        model_selectors
        + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn, send_btn],
    )
    rightvote_btn.click(
        rightvote_last_response,
        states + model_selectors,
        model_selectors
        + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn, send_btn],
    )
    tie_btn.click(
        tievote_last_response,
        states + model_selectors,
        model_selectors
        + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn, send_btn],
    )
    bothbad_btn.click(
        bothbad_vote_last_response,
        states + model_selectors,
        model_selectors
        + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn, send_btn],
    )
    regenerate_btn.click(
        regenerate, states, states + chatbots + [textbox] + btn_list
    ).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons, [], btn_list
    )
    clear_btn.click(
        clear_history,
        None,
        states
        + chatbots
        + model_selectors
        + [textbox]
        + btn_list
        + [slow_warning]
        + [send_btn],
    )

    share_js = """
function (a, b, c, d) {
    const captureElement = document.querySelector('#share-region-anony');
    html2canvas(captureElement)
        .then(canvas => {
            canvas.style.display = 'none'
            document.body.appendChild(canvas)
            return canvas
        })
        .then(canvas => {
            const image = canvas.toDataURL('image/png')
            const a = document.createElement('a')
            a.setAttribute('download', 'chatbot-arena.png')
            a.setAttribute('href', image)
            a.click()
            canvas.remove()
        });
    return [a, b, c, d];
}
"""
    share_btn.click(share_click, states + model_selectors, [], js=share_js)

    textbox.submit(
        add_text,
        states + model_selectors + [textbox],
        states + chatbots + [textbox] + btn_list + [slow_warning],
    ).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons,
        [],
        btn_list,
    )

    send_btn.click(
        add_text,
        states + model_selectors + [textbox],
        states + chatbots + [textbox] + btn_list,
    ).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons, [], btn_list
    )

    return states + model_selectors

block_css = """
.prose {
    font-size: 105% !important;
}

#arena_leaderboard_dataframe table {
    font-size: 105%;
}
#full_leaderboard_dataframe table {
    font-size: 105%;
}

.tab-nav button {
    font-size: 18px;
}

.chatbot h1 {
    font-size: 130%;
}
.chatbot h2 {
    font-size: 120%;
}
.chatbot h3 {
    font-size: 110%;
}

#chatbot .prose {
    font-size: 90% !important;
}

/* HKGAI Branding Styles */
#notice_markdown h1 {
    color: #1976D2;
    text-align: center;
    font-weight: bold;
    margin-bottom: 20px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}

#notice_markdown h2 {
    color: var(--body-text-color);
    text-align: center;
    font-weight: 600;
}

.hkgai-header {
    background: var(--background-fill-primary);
    border: 1px solid var(--border-color-primary);
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.sponsor-image-about img {
    margin: 0 20px;
    margin-top: 20px;
    height: 40px;
    max-height: 100%;
    width: auto;
    float: left;
}

.cursor {
    display: inline-block;
    width: 7px;
    height: 1em;
    background-color: black;
    vertical-align: middle;
    animation: blink 1s infinite;
}

.dark .cursor {
    display: inline-block;
    width: 7px;
    height: 1em;
    background-color: white;
    vertical-align: middle;
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    50.1%, 100% { opacity: 0; }
}

.app {
  max-width: 100% !important;
  padding-left: 5% !important;
  padding-right: 5% !important;
}

a {
    color: #1976D2; /* Your current link color, a shade of blue */
    text-decoration: none; /* Removes underline from links */
}
a:hover {
    color: #63A4FF; /* This can be any color you choose for hover */
    text-decoration: underline; /* Adds underline on hover */
}

.block {
  overflow-y: hidden !important;
}

.visualizer {
    overflow: hidden;
    height: 60vw;
    border: 1px solid lightgrey; 
    border-radius: 10px;
}

@media screen and (max-width: 769px) {
    .visualizer {
        height: 180vw;
        overflow-y: scroll;
        width: 100%;
        overflow-x: hidden;
    }
}
"""
