"""
Multimodal Chatbot Arena (side-by-side) tab.
Users chat with two chosen models.
"""

import json
import os
import time
from typing import List, Union

import gradio as gr
import numpy as np

from fastchat.constants import (
    TEXT_MODERATION_MSG,
    IMAGE_MODERATION_MSG,
    MODERATION_MSG,
    CONVERSATION_LIMIT_MSG,
    SLOW_MODEL_MSG,
    INPUT_CHAR_LEN_LIMIT,
    CONVERSATION_TURN_LIMIT,
    SURVEY_LINK,
)
from fastchat.model.model_adapter import get_conversation_template
from fastchat.serve.gradio_block_arena_named import (
    flash_buttons,
    share_click,
    bot_response_multi,
)
from fastchat.serve.gradio_block_arena_vision import (
    get_vqa_sample,
    set_invisible_image,
    set_visible_image,
    add_image,
    moderate_input,
    _prepare_text_with_image,
    convert_images_to_conversation_format,
    enable_multimodal,
    disable_multimodal,
    invisible_text,
    invisible_btn,
    visible_text,
)
from fastchat.serve.gradio_global_state import Context
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
    enable_text,
)
from fastchat.serve.remote_logger import get_remote_logger
from fastchat.utils import (
    build_logger,
    moderation_filter,
    image_moderation_filter,
)


logger = build_logger("gradio_web_server_multi", "logs/gradio_web_server_multi.log")

num_sides = 2
enable_moderation = False

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


def load_demo_side_by_side_vision_named(context: Context):
    states = [None] * num_sides

    # default to the text models
    models = context.text_models

    model_left = models[0] if len(models) > 0 else ""
    if len(models) > 1:
        weights = ([1] * 128)[: len(models) - 1]
        weights = weights / np.sum(weights)
        model_right = np.random.choice(models[1:], p=weights)
    else:
        model_right = model_left

    all_models = context.models
    selector_updates = [
        gr.Dropdown(choices=all_models, value=model_left, visible=True),
        gr.Dropdown(choices=all_models, value=model_right, visible=True),
    ]

    return states + selector_updates


def clear_history_example(request: gr.Request):
    logger.info(f"clear_history_example (named). ip: {get_ip(request)}")
    return (
        [None] * num_sides
        + [None] * num_sides
        + [enable_multimodal, invisible_text, invisible_btn]
        + [invisible_btn] * 4
        + [disable_btn] * 2
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


def leftvote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"leftvote (named). ip: {get_ip(request)}")
    vote_last_response(
        [state0, state1], "leftvote", [model_selector0, model_selector1], request
    )
    return (None,) + (disable_btn,) * 4


def rightvote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"rightvote (named). ip: {get_ip(request)}")
    vote_last_response(
        [state0, state1], "rightvote", [model_selector0, model_selector1], request
    )
    return (None,) + (disable_btn,) * 4


def tievote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"tievote (named). ip: {get_ip(request)}")
    vote_last_response(
        [state0, state1], "tievote", [model_selector0, model_selector1], request
    )
    return (None,) + (disable_btn,) * 4


def bothbad_vote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"bothbad_vote (named). ip: {get_ip(request)}")
    vote_last_response(
        [state0, state1], "bothbad_vote", [model_selector0, model_selector1], request
    )
    return (None,) + (disable_btn,) * 4


def regenerate(state0, state1, request: gr.Request):
    logger.info(f"regenerate (named). ip: {get_ip(request)}")
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
    logger.info(f"clear_history (named). ip: {get_ip(request)}")
    return (
        [None] * num_sides
        + [None] * num_sides
        + [enable_multimodal, invisible_text, invisible_btn]
        + [invisible_btn] * 4
        + [disable_btn] * 2
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
        text, images = chat_input, []

    if len(images) > 0:
        if (
            model_selector0 in context.text_models
            and model_selector0 not in context.vision_models
        ):
            gr.Warning(f"{model_selector0} is a text-only model. Image is ignored.")
            images = []
        if (
            model_selector1 in context.text_models
            and model_selector1 not in context.vision_models
        ):
            gr.Warning(f"{model_selector1} is a text-only model. Image is ignored.")
            images = []

    ip = get_ip(request)
    logger.info(f"add_text (named). ip: {ip}. len: {len(text)}")
    states = [state0, state1]
    model_selectors = [model_selector0, model_selector1]

    # Init states if necessary
    for i in range(num_sides):
        if states[i] is None and len(images) == 0:
            states[i] = State(model_selectors[i], is_vision=False)
        elif states[i] is None and len(images) > 0:
            states[i] = State(model_selectors[i], is_vision=True)

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
        )

    model_list = [states[i].model_name for i in range(num_sides)]
    all_conv_text_left = states[0].conv.get_prompt()
    all_conv_text_right = states[0].conv.get_prompt()
    all_conv_text = (
        all_conv_text_left[-1000:] + all_conv_text_right[-1000:] + "\nuser: " + text
    )

    images = convert_images_to_conversation_format(images)

    text, image_flagged, csam_flag = moderate_input(
        state0, text, all_conv_text, model_list, images, ip
    )

    conv = states[0].conv
    if (len(conv.messages) - conv.offset) // 2 >= CONVERSATION_TURN_LIMIT:
        logger.info(f"conversation turn limit. ip: {ip}. text: {text}")
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
        )

    if image_flagged:
        logger.info(f"image flagged. ip: {ip}. text: {text}")
        for i in range(num_sides):
            states[i].skip_next = True
        return (
            states
            + [x.to_gradio_chatbot() for x in states]
            + [{"text": IMAGE_MODERATION_MSG}, "", no_change_btn]
            + [
                no_change_btn,
            ]
            * 6
        )

    text = text[:INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
    for i in range(num_sides):
        post_processed_text = _prepare_text_with_image(
            states[i], text, images, csam_flag=csam_flag
        )
        states[i].conv.append_message(states[i].conv.roles[0], post_processed_text)
        states[i].conv.append_message(states[i].conv.roles[1], None)
        states[i].skip_next = False

    return (
        states
        + [x.to_gradio_chatbot() for x in states]
        + [disable_multimodal, visible_text, enable_btn]
        + [
            disable_btn,
        ]
        * 6
    )


def build_side_by_side_vision_ui_named(context: Context, random_questions=None):
    notice_markdown = f"""
<div class="hkgai-header">
    <h1>🚀 HKGAI 智能对话平台</h1>
    <h2>👇 开始聊天！</h2>
</div>
"""

    states = [gr.State() for _ in range(num_sides)]
    model_selectors = [None] * num_sides
    chatbots = [None] * num_sides

    notice = gr.Markdown(notice_markdown, elem_id="notice_markdown")

    text_and_vision_models = context.models
    context_state = gr.State(context)

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
                        with gr.Column():
                            model_selectors[i] = gr.Dropdown(
                                choices=text_and_vision_models,
                                value=text_and_vision_models[i]
                                if len(text_and_vision_models) > i
                                else "",
                                interactive=True,
                                show_label=False,
                                container=False,
                            )

                with gr.Row():
                    for i in range(num_sides):
                        label = "Model A" if i == 0 else "Model B"
                        with gr.Column():
                            chatbots[i] = gr.Chatbot(
                                label=label,
                                elem_id=f"chatbot",
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
            random_btn = gr.Button(value="🎲 Random Example", interactive=True)
        clear_btn = gr.Button(value="🗑️  清除历史", interactive=False, visible=False)
        regenerate_btn = gr.Button(value="🔄  重新生成", interactive=False)
        share_btn = gr.Button(value="📷  分享")

    with gr.Accordion("Parameters", open=False) as parameter_row:
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
            value=1024,
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
        [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
    )
    rightvote_btn.click(
        rightvote_last_response,
        states + model_selectors,
        [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
    )
    tie_btn.click(
        tievote_last_response,
        states + model_selectors,
        [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
    )
    bothbad_btn.click(
        bothbad_vote_last_response,
        states + model_selectors,
        [textbox, leftvote_btn, rightvote_btn, tie_btn, bothbad_btn],
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
        states + chatbots + [multimodal_textbox, textbox, send_btn] + btn_list,
    )

    share_js = """
function (a, b, c, d) {
    const captureElement = document.querySelector('#share-region-named');
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

    for i in range(num_sides):
        model_selectors[i].change(
            clear_history,
            None,
            states + chatbots + [multimodal_textbox, textbox, send_btn] + btn_list,
        ).then(set_visible_image, [multimodal_textbox], [image_column])

    multimodal_textbox.input(add_image, [multimodal_textbox], [imagebox]).then(
        set_visible_image, [multimodal_textbox], [image_column]
    ).then(
        clear_history_example,
        None,
        states + chatbots + [multimodal_textbox, textbox, send_btn] + btn_list,
    )

    multimodal_textbox.submit(
        add_text,
        states + model_selectors + [multimodal_textbox, context_state],
        states + chatbots + [multimodal_textbox, textbox, send_btn] + btn_list,
    ).then(set_invisible_image, [], [image_column]).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons, [], btn_list
    )

    textbox.submit(
        add_text,
        states + model_selectors + [textbox, context_state],
        states + chatbots + [multimodal_textbox, textbox, send_btn] + btn_list,
    ).then(set_invisible_image, [], [image_column]).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons, [], btn_list
    )

    send_btn.click(
        add_text,
        states + model_selectors + [textbox, context_state],
        states + chatbots + [multimodal_textbox, textbox, send_btn] + btn_list,
    ).then(set_invisible_image, [], [image_column]).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots + btn_list,
    ).then(
        flash_buttons, [], btn_list
    )

    if random_questions:
        random_btn.click(
            get_vqa_sample,  # First, get the VQA sample
            [],  # Pass the path to the VQA samples
            [multimodal_textbox, imagebox],  # Outputs are textbox and imagebox
        ).then(set_visible_image, [multimodal_textbox], [image_column]).then(
            clear_history_example,
            None,
            states + chatbots + [multimodal_textbox, textbox, send_btn] + btn_list,
        )

    return states + model_selectors
