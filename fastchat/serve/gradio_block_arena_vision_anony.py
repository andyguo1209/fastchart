"""
Chatbot Arena (battle) tab.
Users chat with two anonymous models.
"""

import json
import time

import gradio as gr
import numpy as np
from typing import Union

from fastchat.constants import (
    TEXT_MODERATION_MSG,
    IMAGE_MODERATION_MSG,
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
    acknowledgment_md,
    get_ip,
    get_model_description_md,
    disable_text,
    enable_text,
)
from fastchat.serve.gradio_block_arena_anony import (
    flash_buttons,
    vote_last_response,
    leftvote_last_response,
    rightvote_last_response,
    tievote_last_response,
    bothbad_vote_last_response,
    regenerate,
    clear_history,
    share_click,
    bot_response_multi,
    set_global_vars_anony,
    load_demo_side_by_side_anony,
    get_sample_weight,
    get_battle_pair,
    SAMPLING_WEIGHTS,
    BATTLE_TARGETS,
    SAMPLING_BOOST_MODELS,
    OUTAGE_MODELS,
)
from fastchat.serve.gradio_block_arena_vision import (
    set_invisible_image,
    set_visible_image,
    add_image,
    moderate_input,
    enable_multimodal,
    _prepare_text_with_image,
    convert_images_to_conversation_format,
    invisible_text,
    visible_text,
    disable_multimodal,
)
from fastchat.serve.gradio_global_state import Context
from fastchat.serve.remote_logger import get_remote_logger
from fastchat.utils import (
    build_logger,
    moderation_filter,
    image_moderation_filter,
)

logger = build_logger("gradio_web_server_multi", "logs/gradio_web_server_multi.log")

num_sides = 2
enable_moderation = False
anony_names = ["", ""]
text_models = []
vl_models = []

# TODO(chris): fix sampling weights
VISION_SAMPLING_WEIGHTS = {}

# TODO(chris): Find battle targets that make sense
VISION_BATTLE_TARGETS = {}

# TODO(chris): Fill out models that require sampling boost
VISION_SAMPLING_BOOST_MODELS = []

# outage models won't be sampled.
VISION_OUTAGE_MODELS = []


def get_vqa_sample():
    random_sample = np.random.choice(vqa_samples)
    question, path = random_sample["question"], random_sample["path"]
    res = {"text": "", "files": [path]}
    return (res, path)


def load_demo_side_by_side_vision_anony():
    states = [None] * num_sides
    selector_updates = [
        gr.Markdown(visible=True),
        gr.Markdown(visible=True),
    ]

    return states + selector_updates


def clear_history_example(request: gr.Request):
    logger.info(f"clear_history_example (anony). ip: {get_ip(request)}")
    return (
        [None] * num_sides
        + [None] * num_sides
        + anony_names
        + [enable_multimodal, invisible_text, invisible_btn]
        + [invisible_btn] * 4
        + [disable_btn] * 2
        + [enable_btn]
    )


def vote_last_response(states, vote_type, model_selectors, request: gr.Request):
    filename = get_conv_log_filename(states[0].is_vision, states[0].has_csam_image)

    with open(filename, "a") as fout:
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

    model_name_1 = states[0].model_name
    model_name_2 = states[1].model_name
    model_name_map = {}

    if model_name_1 in model_name_map:
        model_name_1 = model_name_map[model_name_1]
    if model_name_2 in model_name_map:
        model_name_2 = model_name_map[model_name_2]

    if ":" not in model_selectors[0]:
        for i in range(5):
            names = (
                "### Model A: " + model_name_1,
                "### Model B: " + model_name_2,
            )
            yield names + (disable_text,) + (disable_btn,) * 4
            time.sleep(0.1)
    else:
        names = (
            "### Model A: " + model_name_1,
            "### Model B: " + model_name_2,
        )
        yield names + (disable_text,) + (disable_btn,) * 4


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
            states
            + [x.to_gradio_chatbot() for x in states]
            + [None]
            + [disable_btn] * 6
        )
    states[0].skip_next = True
    states[1].skip_next = True
    return (
        states + [x.to_gradio_chatbot() for x in states] + [None] + [no_change_btn] * 6
    )


def clear_history(request: gr.Request):
    logger.info(f"clear_history (anony). ip: {get_ip(request)}")
    return (
        [None] * num_sides
        + [None] * num_sides
        + anony_names
        + [enable_multimodal, invisible_text, invisible_btn]
        + [invisible_btn] * 4
        + [disable_btn] * 2
        + [enable_btn]
        + [""]
    )


def add_text(
    state0,
    state1,
    model_selector0,
    model_selector1,
    chat_input: Union[str, dict],
    context: Context,
    request: gr.Request,
):
    if isinstance(chat_input, dict):
        text, images = chat_input["text"], chat_input["files"]
    else:
        text = chat_input
        images = []

    ip = get_ip(request)
    logger.info(f"add_text (anony). ip: {ip}. len: {len(text)}")
    states = [state0, state1]
    model_selectors = [model_selector0, model_selector1]

    # Init states if necessary
    if states[0] is None:
        assert states[1] is None

        if len(images) > 0:
            model_left, model_right = get_battle_pair(
                context.all_vision_models,
                VISION_BATTLE_TARGETS,
                VISION_OUTAGE_MODELS,
                VISION_SAMPLING_WEIGHTS,
                VISION_SAMPLING_BOOST_MODELS,
            )
            states = [
                State(model_left, is_vision=True),
                State(model_right, is_vision=True),
            ]
        else:
            model_left, model_right = get_battle_pair(
                context.all_text_models,
                BATTLE_TARGETS,
                OUTAGE_MODELS,
                SAMPLING_WEIGHTS,
                SAMPLING_BOOST_MODELS,
            )

            states = [
                State(model_left, is_vision=False),
                State(model_right, is_vision=False),
            ]

    if len(text) <= 0:
        for i in range(num_sides):
            states[i].skip_next = True
        return (
            states
            + [x.to_gradio_chatbot() for x in states]
            + [None, "", no_change_btn]
            + [
                no_change_btn,
            ]
            * 6
            + [no_change_btn]
            + [""]
        )

    model_list = [states[i].model_name for i in range(num_sides)]

    images = convert_images_to_conversation_format(images)

    text, image_flagged, csam_flag = moderate_input(
        state0, text, text, model_list, images, ip
    )

    conv = states[0].conv
    if (len(conv.messages) - conv.offset) // 2 >= CONVERSATION_TURN_LIMIT:
        logger.info(f"conversation turn limit. ip: {get_ip(request)}. text: {text}")
        for i in range(num_sides):
            states[i].skip_next = True
        return (
            states
            + [x.to_gradio_chatbot() for x in states]
            + [{"text": CONVERSATION_LIMIT_MSG}, "", no_change_btn]
            + [
                no_change_btn,
            ]
            * 6
            + [no_change_btn]
            + [""]
        )

    if image_flagged:
        logger.info(f"image flagged. ip: {ip}. text: {text}")
        for i in range(num_sides):
            states[i].skip_next = True
        return (
            states
            + [x.to_gradio_chatbot() for x in states]
            + [
                {
                    "text": IMAGE_MODERATION_MSG
                    + " PLEASE CLICK 🎲 NEW ROUND TO START A NEW CONVERSATION."
                },
                "",
                no_change_btn,
            ]
            + [no_change_btn] * 6
            + [no_change_btn]
            + [""]
        )

    text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
    for i in range(num_sides):
        post_processed_text = _prepare_text_with_image(
            states[i], text, images, csam_flag=csam_flag
        )
        states[i].conv.append_message(states[i].conv.roles[0], post_processed_text)
        states[i].conv.append_message(states[i].conv.roles[1], None)
        states[i].skip_next = False

    hint_msg = ""
    for i in range(num_sides):
        if "deluxe" in states[i].model_name:
            hint_msg = SLOW_MODEL_MSG
    return (
        states
        + [x.to_gradio_chatbot() for x in states]
        + [disable_multimodal, visible_text, enable_btn]
        + [
            disable_btn,
        ]
        * 6
        + [disable_btn]
        + [hint_msg]
    )


def build_side_by_side_vision_ui_anony(context: Context, random_questions=None):
    notice_markdown = f"""
<div class="hkgai-header">
    <h1>🚀 HKGAI 智能对话平台</h1>
    <h2>👇 开始聊天！</h2>
</div>
"""

    states = [gr.State() for _ in range(num_sides)]
    model_selectors = [None] * num_sides
    chatbots = [None] * num_sides
    context_state = gr.State(context)
    gr.Markdown(notice_markdown, elem_id="notice_markdown")
    text_and_vision_models = context.models

    with gr.Row():
        with gr.Column(scale=2, visible=False) as image_column:
            imagebox = gr.Image(
                type="pil",
                show_label=False,
                interactive=False,
            )

        with gr.Column(scale=5):
            with gr.Group(elem_id="share-region-anony"):
                with gr.Accordion(
                    f"🔍 Expand to see the descriptions of {len(text_and_vision_models)} models",
                    open=False,
                ):
                    model_description_md = get_model_description_md(
                        text_and_vision_models
                    )
                    gr.Markdown(
                        model_description_md, elem_id="model_description_markdown"
                    )

                with gr.Row():
                    for i in range(num_sides):
                        label = "Model A" if i == 0 else "Model B"
                        with gr.Column():
                            chatbots[i] = gr.Chatbot(
                                label=label,
                                elem_id="chatbot",
                                height=650,
                                show_copy_button=False,
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
        slow_warning = gr.Markdown("", elem_id="notice_markdown")

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
            visible=False,
        )

        send_btn = gr.Button(
            value="发送", variant="primary", scale=0, visible=False, interactive=False
        )

        multimodal_textbox = gr.MultimodalTextbox(
            file_types=["image"],
            show_label=False,
            placeholder="请输入您的问题或上传图片",
            container=True,
            elem_id="input_box",
        )

    with gr.Row() as button_row:
        if random_questions:
            global vqa_samples
            with open(random_questions, "r") as f:
                vqa_samples = json.load(f)
            random_btn = gr.Button(value="🔮 Random Image", interactive=True)
        else:
            # Define random_btn even when random_questions is None to avoid UnboundLocalError
            random_btn = gr.Button(value="🔮 Random Image", interactive=False, visible=False)
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

    # gr.Markdown(acknowledgment_md, elem_id="ack_markdown")

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
        model_selectors + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
    )
    rightvote_btn.click(
        rightvote_last_response,
        states + model_selectors,
        model_selectors + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
    )
    tie_btn.click(
        tievote_last_response,
        states + model_selectors,
        model_selectors + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
    )
    bothbad_btn.click(
        bothbad_vote_last_response,
        states + model_selectors,
        model_selectors + [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
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
        + [multimodal_textbox, textbox, send_btn]
        + btn_list
        + [random_btn]
        + [slow_warning],
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

    multimodal_textbox.input(add_image, [multimodal_textbox], [imagebox]).then(
        set_visible_image, [multimodal_textbox], [image_column]
    ).then(
        clear_history_example,
        None,
        states
        + chatbots
        + model_selectors
        + [multimodal_textbox, textbox, send_btn]
        + btn_list,
    )

    multimodal_textbox.submit(
        add_text,
        states + model_selectors + [multimodal_textbox, context_state],
        states
        + chatbots
        + [multimodal_textbox, textbox, send_btn]
        + btn_list
        + [random_btn]
        + [slow_warning],
    ).then(set_invisible_image, [], [image_column]).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons,
        [],
        btn_list,
    )

    textbox.submit(
        add_text,
        states + model_selectors + [textbox, context_state],
        states
        + chatbots
        + [multimodal_textbox, textbox, send_btn]
        + btn_list
        + [random_btn]
        + [slow_warning],
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
        states + model_selectors + [textbox, context_state],
        states
        + chatbots
        + [multimodal_textbox, textbox, send_btn]
        + btn_list
        + [random_btn]
        + [slow_warning],
    ).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons,
        [],
        btn_list,
    )

    if random_questions:
        random_btn.click(
            get_vqa_sample,  # First, get the VQA sample
            [],  # Pass the path to the VQA samples
            [multimodal_textbox, imagebox],  # Outputs are textbox and imagebox
        ).then(set_visible_image, [multimodal_textbox], [image_column]).then(
            clear_history_example,
            None,
            states
            + chatbots
            + model_selectors
            + [multimodal_textbox, textbox, send_btn]
            + btn_list
            + [random_btn],
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

/* Hide or minimize only "清空对话" buttons in chatbot messages */
.chatbot button[title*="清空对话"],
.chatbot button[aria-label*="清空对话"],
div[data-testid="chatbot"] button[title*="清空对话"],
div[data-testid="chatbot"] button[aria-label*="清空对话"],
/* Target buttons by accessibility name */
.chatbot button[aria-describedby*="清空对话"],
.chatbot button[name*="清空对话"],
div[data-testid="chatbot"] button[aria-describedby*="清空对话"],
div[data-testid="chatbot"] button[name*="清空对话"],
/* Target by button content/text */
.chatbot button:has-text("清空对话"),
.chatbot button:contains("清空对话"),
div[data-testid="chatbot"] button:has-text("清空对话"),
div[data-testid="chatbot"] button:contains("清空对话") {
    /* Option 1: Make button smaller and less prominent */
    /* width: 20px !important;
    height: 20px !important;
    padding: 2px !important;
    font-size: 10px !important;
    opacity: 0.3 !important;
    transform: scale(0.6) !important;
    margin: 0 !important; */
    /* Option 2: Completely hide - uncomment below and comment above if you prefer */
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Hide image-related buttons in MultimodalTextbox */
/* Hide delete/remove buttons for uploaded images */
.multimodal-textbox button[title*="delete"],
.multimodal-textbox button[title*="Delete"],
.multimodal-textbox button[title*="remove"],
.multimodal-textbox button[title*="Remove"],
.multimodal-textbox button[title*="删除"],
.multimodal-textbox button[title*="清除"],
.multimodal-textbox button[aria-label*="delete"],
.multimodal-textbox button[aria-label*="Delete"],
.multimodal-textbox button[aria-label*="remove"],
.multimodal-textbox button[aria-label*="Remove"],
.multimodal-textbox button[aria-label*="删除"],
.multimodal-textbox button[aria-label*="清除"],
/* Target MultimodalTextbox by data-testid */
div[data-testid*="multimodal"] button[title*="delete"],
div[data-testid*="multimodal"] button[title*="Delete"],
div[data-testid*="multimodal"] button[title*="remove"],
div[data-testid*="multimodal"] button[title*="Remove"],
div[data-testid*="multimodal"] button[title*="删除"],
div[data-testid*="multimodal"] button[title*="清除"],
div[data-testid*="multimodal"] button[aria-label*="delete"],
div[data-testid*="multimodal"] button[aria-label*="Delete"],
div[data-testid*="multimodal"] button[aria-label*="remove"],
div[data-testid*="multimodal"] button[aria-label*="Remove"],
div[data-testid*="multimodal"] button[aria-label*="删除"],
div[data-testid*="multimodal"] button[aria-label*="清除"],
/* Target by element ID */
#input_box button[title*="delete"],
#input_box button[title*="Delete"],
#input_box button[title*="remove"],
#input_box button[title*="Remove"],
#input_box button[title*="删除"],
#input_box button[title*="清除"],
#input_box button[aria-label*="delete"],
#input_box button[aria-label*="Delete"],
#input_box button[aria-label*="remove"],
#input_box button[aria-label*="Remove"],
#input_box button[aria-label*="删除"],
#input_box button[aria-label*="清除"],
/* Target buttons with close/x icons */
.multimodal-textbox button svg[data-testid="close-icon"],
.multimodal-textbox button svg[data-testid="x-icon"],
div[data-testid*="multimodal"] button svg[data-testid="close-icon"],
div[data-testid*="multimodal"] button svg[data-testid="x-icon"],
#input_box button svg[data-testid="close-icon"],
#input_box button svg[data-testid="x-icon"],
/* Target buttons containing close/x icons */
.multimodal-textbox button:has(svg[data-testid="close-icon"]),
.multimodal-textbox button:has(svg[data-testid="x-icon"]),
div[data-testid*="multimodal"] button:has(svg[data-testid="close-icon"]),
div[data-testid*="multimodal"] button:has(svg[data-testid="x-icon"]),
#input_box button:has(svg[data-testid="close-icon"]),
#input_box button:has(svg[data-testid="x-icon"]) {
    /* Option 1: Make button smaller and less prominent */
    /* width: 20px !important;
    height: 20px !important;
    padding: 2px !important;
    font-size: 10px !important;
    opacity: 0.3 !important;
    transform: scale(0.6) !important;
    margin: 0 !important; */
    /* Option 2: Completely hide - uncomment below and comment above if you prefer */
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
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
