"""
The gradio demo server for chatting with a single model.
"""

import argparse
from collections import defaultdict
import datetime
import hashlib
import json
import os
import random
import time
import uuid
from typing import List, Dict

import gradio as gr
import requests

from fastchat.constants import (
    LOGDIR,
    WORKER_API_TIMEOUT,
    ErrorCode,
    MODERATION_MSG,
    CONVERSATION_LIMIT_MSG,
    RATE_LIMIT_MSG,
    SERVER_ERROR_MSG,
    INPUT_CHAR_LEN_LIMIT,
    CONVERSATION_TURN_LIMIT,
    SESSION_EXPIRATION_TIME,
    SURVEY_LINK,
)
from fastchat.model.model_adapter import (
    get_conversation_template,
)
from fastchat.model.model_registry import get_model_info, model_info
from fastchat.serve.api_provider import get_api_provider_stream_iter
from fastchat.serve.gradio_global_state import Context
from fastchat.serve.remote_logger import get_remote_logger
from fastchat.utils import (
    build_logger,
    get_window_url_params_js,
    get_window_url_params_with_tos_js,
    moderation_filter,
    parse_gradio_auth_creds,
    load_image,
)

logger = build_logger("gradio_web_server", "logs/gradio_web_server.log")

headers = {"User-Agent": "FastChat Client"}

no_change_btn = gr.Button()
enable_btn = gr.Button(interactive=True, visible=True)
disable_btn = gr.Button(interactive=False)
invisible_btn = gr.Button(interactive=False, visible=False)
enable_text = gr.Textbox(
    interactive=True, visible=True, placeholder="👉 Enter your prompt and press ENTER"
)
disable_text = gr.Textbox(
    interactive=False,
    visible=True,
    placeholder='Press "🎲 New Round" to start over👇 (Note: Your vote shapes the leaderboard, please vote RESPONSIBLY!)',
)

controller_url = None
enable_moderation = False
use_remote_storage = False

acknowledgment_md = """
### Terms of Service

Users are required to agree to the following terms before using the service:

The service is a research preview. It only provides limited safety measures and may generate offensive content.
It must not be used for any illegal, harmful, violent, racist, or sexual purposes.
Please do not upload any private information.
The service collects user dialogue data, including both text and images, and reserves the right to distribute it under a Creative Commons Attribution (CC-BY) or a similar license.

#### Please report any bug or issue to our [Discord](https://discord.gg/6GXcFg3TH8)/arena-feedback.

### Acknowledgment
We thank [UC Berkeley SkyLab](https://sky.cs.berkeley.edu/), [Kaggle](https://www.kaggle.com/), [MBZUAI](https://mbzuai.ac.ae/), [a16z](https://www.a16z.com/), [Together AI](https://www.together.ai/), [Hyperbolic](https://hyperbolic.xyz/), [RunPod](https://runpod.io), [Anyscale](https://www.anyscale.com/), [HuggingFace](https://huggingface.co/) for their generous [sponsorship](https://lmsys.org/donations/).

<div class="sponsor-image-about">
    <img src="https://storage.googleapis.com/public-arena-asset/skylab.png" alt="SkyLab">
    <img src="https://storage.googleapis.com/public-arena-asset/kaggle.png" alt="Kaggle">
    <img src="https://storage.googleapis.com/public-arena-asset/mbzuai.jpeg" alt="MBZUAI">
    <img src="https://storage.googleapis.com/public-arena-asset/a16z.jpeg" alt="a16z">
    <img src="https://storage.googleapis.com/public-arena-asset/together.png" alt="Together AI">
    <img src="https://storage.googleapis.com/public-arena-asset/hyperbolic_logo.png" alt="Hyperbolic">
    <img src="https://storage.googleapis.com/public-arena-asset/runpod-logo.jpg" alt="RunPod">
    <img src="https://storage.googleapis.com/public-arena-asset/anyscale.png" alt="AnyScale">
    <img src="https://storage.googleapis.com/public-arena-asset/huggingface.png" alt="HuggingFace">
</div>
"""

# JSON file format of API-based models:
# {
#   "gpt-3.5-turbo": {
#     "model_name": "gpt-3.5-turbo",
#     "api_type": "openai",
#     "api_base": "https://api.openai.com/v1",
#     "api_key": "sk-******",
#     "anony_only": false
#   }
# }
#
#  - "api_type" can be one of the following: openai, anthropic, gemini, or mistral. For custom APIs, add a new type and implement it accordingly.
#  - "anony_only" indicates whether to display this model in anonymous mode only.

api_endpoint_info = {}


class State:
    def __init__(self, model_name, is_vision=False):
        self.conv = get_conversation_template(model_name)
        self.conv_id = uuid.uuid4().hex
        self.skip_next = False
        self.model_name = model_name
        self.oai_thread_id = None
        self.is_vision = is_vision
        self.ans_models = []
        self.router_outputs = []

        # NOTE(chris): This could be sort of a hack since it assumes the user only uploads one image. If they can upload multiple, we should store a list of image hashes.
        self.has_csam_image = False

        self.regen_support = True
        if "browsing" in model_name:
            self.regen_support = False
        self.init_system_prompt(self.conv, is_vision)

    def update_ans_models(self, ans: str) -> None:
        self.ans_models.append(ans)

    def update_router_outputs(self, outputs: Dict[str, float]) -> None:
        self.router_outputs.append(outputs)

    def init_system_prompt(self, conv, is_vision):
        system_prompt = conv.get_system_message(is_vision)
        if len(system_prompt) == 0:
            return
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        system_prompt = system_prompt.replace("{{currentDateTime}}", current_date)

        current_date_v2 = datetime.datetime.now().strftime("%d %b %Y")
        system_prompt = system_prompt.replace("{{currentDateTimev2}}", current_date_v2)

        current_date_v3 = datetime.datetime.now().strftime("%B %Y")
        system_prompt = system_prompt.replace("{{currentDateTimev3}}", current_date_v3)
        conv.set_system_message(system_prompt)

    def to_gradio_chatbot(self):
        return self.conv.to_gradio_chatbot()

    def dict(self):
        base = self.conv.dict()
        base.update(
            {
                "conv_id": self.conv_id,
                "model_name": self.model_name,
            }
        )

        if self.ans_models:
            base.update(
                {
                    "ans_models": self.ans_models,
                }
            )

        if self.router_outputs:
            base.update(
                {
                    "router_outputs": self.router_outputs,
                }
            )

        if self.is_vision:
            base.update({"has_csam_image": self.has_csam_image})
        return base


def set_global_vars(
    controller_url_,
    enable_moderation_,
    use_remote_storage_,
):
    global controller_url, enable_moderation, use_remote_storage
    controller_url = controller_url_
    enable_moderation = enable_moderation_
    use_remote_storage = use_remote_storage_


def get_conv_log_filename(is_vision=False, has_csam_image=False):
    t = datetime.datetime.now()
    conv_log_filename = f"{t.year}-{t.month:02d}-{t.day:02d}-conv.json"
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../logs_archive')
    log_dir = os.path.abspath(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    if is_vision and not has_csam_image:
        name = os.path.join(log_dir, f"vision-tmp-{conv_log_filename}")
    elif is_vision and has_csam_image:
        name = os.path.join(log_dir, f"vision-csam-{conv_log_filename}")
    else:
        name = os.path.join(log_dir, conv_log_filename)
    return name


def get_model_list(controller_url, register_api_endpoint_file, vision_arena):
    global api_endpoint_info

    # Add models from the controller
    if controller_url:
        ret = requests.post(controller_url + "/refresh_all_workers")
        assert ret.status_code == 200

        if vision_arena:
            ret = requests.post(controller_url + "/list_multimodal_models")
            models = ret.json()["models"]
        else:
            ret = requests.post(controller_url + "/list_language_models")
            models = ret.json()["models"]
    else:
        models = []

    # Add models from the API providers
    if register_api_endpoint_file:
        api_endpoint_info = json.load(open(register_api_endpoint_file))
        for mdl, mdl_dict in api_endpoint_info.items():
            mdl_vision = mdl_dict.get("vision-arena", False)
            mdl_text = mdl_dict.get("text-arena", True)
            if vision_arena and mdl_vision:
                models.append(mdl)
            if not vision_arena and mdl_text:
                models.append(mdl)

    # Remove anonymous models
    models = list(set(models))
    visible_models = models.copy()
    for mdl in models:
        if mdl not in api_endpoint_info:
            continue
        mdl_dict = api_endpoint_info[mdl]
        if mdl_dict["anony_only"]:
            visible_models.remove(mdl)

    # Sort models and add descriptions
    priority = {k: f"___{i:03d}" for i, k in enumerate(model_info)}
    models.sort(key=lambda x: priority.get(x, x))
    visible_models.sort(key=lambda x: priority.get(x, x))
    logger.info(f"All models: {models}")
    logger.info(f"Visible models: {visible_models}")
    return visible_models, models


def load_demo_single(context: Context, query_params):
    # default to text models
    models = context.text_models

    selected_model = models[0] if len(models) > 0 else ""
    if "model" in query_params:
        model = query_params["model"]
        if model in models:
            selected_model = model

    all_models = context.models

    dropdown_update = gr.Dropdown(
        choices=all_models, value=selected_model, visible=True
    )
    state = None
    return [state, dropdown_update]


def load_demo(url_params, request: gr.Request):
    global models

    ip = get_ip(request)
    logger.info(f"load_demo. ip: {ip}. params: {url_params}")

    if args.model_list_mode == "reload":
        models, all_models = get_model_list(
            controller_url, args.register_api_endpoint_file, vision_arena=False
        )

    return load_demo_single(models, url_params)


def vote_last_response(state, vote_type, model_selector, request: gr.Request):
    filename = get_conv_log_filename()
    if "llava" in model_selector:
        filename = filename.replace("2024", "vision-tmp-2024")

    with open(filename, "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "type": vote_type,
            "model": model_selector,
            "state": state.dict(),
            "ip": get_ip(request),
        }
        fout.write(json.dumps(data) + "\n")
    get_remote_logger().log(data)


def upvote_last_response(state, model_selector, request: gr.Request):
    ip = get_ip(request)
    logger.info(f"upvote. ip: {ip}")
    vote_last_response(state, "upvote", model_selector, request)
    return ("",) + (disable_btn,) * 3


def downvote_last_response(state, model_selector, request: gr.Request):
    ip = get_ip(request)
    logger.info(f"downvote. ip: {ip}")
    vote_last_response(state, "downvote", model_selector, request)
    return ("",) + (disable_btn,) * 3


def flag_last_response(state, model_selector, request: gr.Request):
    ip = get_ip(request)
    logger.info(f"flag. ip: {ip}")
    vote_last_response(state, "flag", model_selector, request)
    return ("",) + (disable_btn,) * 3


def regenerate(state, request: gr.Request):
    ip = get_ip(request)
    logger.info(f"regenerate. ip: {ip}")
    if not state.regen_support:
        state.skip_next = True
        return (state, state.to_gradio_chatbot(), "", None) + (no_change_btn,) * 5
    state.conv.update_last_message(None)
    return (state, state.to_gradio_chatbot(), "") + (disable_btn,) * 5


def clear_history(request: gr.Request):
    ip = get_ip(request)
    logger.info(f"clear_history. ip: {ip}")
    state = None
    return (state, [], "") + (disable_btn,) * 5


def get_ip(request: gr.Request):
    if "cf-connecting-ip" in request.headers:
        ip = request.headers["cf-connecting-ip"]
    elif "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"]
        if "," in ip:
            ip = ip.split(",")[0]
    else:
        ip = request.client.host
    return ip


def add_text(state, model_selector, text, request: gr.Request):
    ip = get_ip(request)
    logger.info(f"add_text. ip: {ip}. len: {len(text)}")

    if state is None:
        state = State(model_selector)

    if len(text) <= 0:
        state.skip_next = True
        return (state, state.to_gradio_chatbot(), "", None) + (no_change_btn,) * 5

    all_conv_text = state.conv.get_prompt()
    all_conv_text = all_conv_text[-2000:] + "\nuser: " + text
    flagged = moderation_filter(all_conv_text, [state.model_name])
    # flagged = moderation_filter(text, [state.model_name])
    if flagged:
        logger.info(f"violate moderation. ip: {ip}. text: {text}")
        # overwrite the original text
        text = MODERATION_MSG

    if (len(state.conv.messages) - state.conv.offset) // 2 >= CONVERSATION_TURN_LIMIT:
        logger.info(f"conversation turn limit. ip: {ip}. text: {text}")
        state.skip_next = True
        return (state, state.to_gradio_chatbot(), CONVERSATION_LIMIT_MSG, None) + (
            no_change_btn,
        ) * 5

    text = text[:INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
    state.conv.append_message(state.conv.roles[0], text)
    state.conv.append_message(state.conv.roles[1], None)
    return (state, state.to_gradio_chatbot(), "") + (disable_btn,) * 5


def model_worker_stream_iter(
    conv,
    model_name,
    worker_addr,
    prompt,
    temperature,
    repetition_penalty,
    top_p,
    max_new_tokens,
    images,
):
    # Make requests
    gen_params = {
        "model": model_name,
        "prompt": prompt,
        "temperature": temperature,
        "repetition_penalty": repetition_penalty,
        "top_p": top_p,
        "max_new_tokens": max_new_tokens,
        "stop": conv.stop_str,
        "stop_token_ids": conv.stop_token_ids,
        "echo": False,
    }

    logger.info(f"==== request ====\n{gen_params}")

    if len(images) > 0:
        gen_params["images"] = images

    # Stream output
    response = requests.post(
        worker_addr + "/worker_generate_stream",
        headers=headers,
        json=gen_params,
        stream=True,
        timeout=WORKER_API_TIMEOUT,
    )
    for chunk in response.iter_lines(decode_unicode=False, delimiter=b"\0"):
        if chunk:
            data = json.loads(chunk.decode())
            yield data


def is_limit_reached(model_name, ip):
    monitor_url = "http://localhost:9090"
    try:
        ret = requests.get(
            f"{monitor_url}/is_limit_reached?model={model_name}&user_id={ip}", timeout=1
        )
        obj = ret.json()
        return obj
    except Exception as e:
        logger.info(f"monitor error: {e}")
        return None


def bot_response(
    state: State,
    temperature,
    top_p,
    max_new_tokens,
    request: gr.Request,
    apply_rate_limit=True,
    use_recommended_config=False,
):
    ip = get_ip(request)
    logger.info(f"bot_response. ip: {ip}")
    start_tstamp = time.time()
    temperature = float(temperature)
    top_p = float(top_p)
    max_new_tokens = int(max_new_tokens)

    if state.skip_next:
        # This generate call is skipped due to invalid inputs
        state.skip_next = False
        yield (state, state.to_gradio_chatbot()) + (no_change_btn,) * 5
        return

    if apply_rate_limit:
        ret = is_limit_reached(state.model_name, ip)
        if ret is not None and ret["is_limit_reached"]:
            error_msg = RATE_LIMIT_MSG + "\n\n" + ret["reason"]
            logger.info(f"rate limit reached. ip: {ip}. error_msg: {ret['reason']}")
            state.conv.update_last_message(error_msg)
            yield (state, state.to_gradio_chatbot()) + (no_change_btn,) * 5
            return

    conv, model_name = state.conv, state.model_name
    model_api_dict = (
        api_endpoint_info[model_name] if model_name in api_endpoint_info else None
    )
    images = conv.get_images()

    if model_api_dict is None:
        # Query worker address
        ret = requests.post(
            controller_url + "/get_worker_address", json={"model": model_name}
        )
        worker_addr = ret.json()["address"]
        logger.info(f"model_name: {model_name}, worker_addr: {worker_addr}")

        # No available worker
        if worker_addr == "":
            conv.update_last_message(SERVER_ERROR_MSG)
            yield (
                state,
                state.to_gradio_chatbot(),
                disable_btn,
                disable_btn,
                disable_btn,
                enable_btn,
                enable_btn,
            )
            return

        # Construct prompt.
        # We need to call it here, so it will not be affected by "▌".
        prompt = conv.get_prompt()
        # Set repetition_penalty
        if "t5" in model_name:
            repetition_penalty = 1.2
        else:
            repetition_penalty = 1.0

        stream_iter = model_worker_stream_iter(
            conv,
            model_name,
            worker_addr,
            prompt,
            temperature,
            repetition_penalty,
            top_p,
            max_new_tokens,
            images,
        )
    else:
        # Remove system prompt for API-based models unless specified
        custom_system_prompt = model_api_dict.get("custom_system_prompt", False)
        if not custom_system_prompt:
            conv.set_system_message("")

        extra_body = None

        if use_recommended_config:
            recommended_config = model_api_dict.get("recommended_config", None)
            if recommended_config is not None:
                temperature = recommended_config.get("temperature", temperature)
                top_p = recommended_config.get("top_p", top_p)
                max_new_tokens = recommended_config.get(
                    "max_new_tokens", max_new_tokens
                )
                extra_body = recommended_config.get("extra_body", None)

        stream_iter = get_api_provider_stream_iter(
            conv,
            model_name,
            model_api_dict,
            temperature,
            top_p,
            max_new_tokens,
            state,
            extra_body=extra_body,
        )

    html_code = ' <span class="cursor"></span> '

    # conv.update_last_message("▌")
    conv.update_last_message(html_code)
    yield (state, state.to_gradio_chatbot()) + (disable_btn,) * 5

    try:
        data = {"text": ""}
        for i, data in enumerate(stream_iter):
            # Change for P2L:
            if i == 0:
                if "ans_model" in data:
                    ans_model = data.get("ans_model")

                    state.update_ans_models(ans_model)

                if "router_outputs" in data:
                    router_outputs = data.get("router_outputs")

                    state.update_router_outputs(router_outputs)

            if data["error_code"] == 0:
                output = data["text"].strip()
                conv.update_last_message(output + "▌")
                # conv.update_last_message(output + html_code)
                yield (state, state.to_gradio_chatbot()) + (disable_btn,) * 5
            else:
                output = data["text"] + f"\n\n(error_code: {data['error_code']})"
                conv.update_last_message(output)
                yield (state, state.to_gradio_chatbot()) + (
                    disable_btn,
                    disable_btn,
                    disable_btn,
                    enable_btn,
                    enable_btn,
                )
                return
        output = data["text"].strip()
        conv.update_last_message(output)
        yield (state, state.to_gradio_chatbot()) + (enable_btn,) * 5
    except requests.exceptions.RequestException as e:
        conv.update_last_message(
            f"{SERVER_ERROR_MSG}\n\n"
            f"(error_code: {ErrorCode.GRADIO_REQUEST_ERROR}, {e})"
        )
        yield (state, state.to_gradio_chatbot()) + (
            disable_btn,
            disable_btn,
            disable_btn,
            enable_btn,
            enable_btn,
        )
        return
    except Exception as e:
        conv.update_last_message(
            f"{SERVER_ERROR_MSG}\n\n"
            f"(error_code: {ErrorCode.GRADIO_STREAM_UNKNOWN_ERROR}, {e})"
        )
        yield (state, state.to_gradio_chatbot()) + (
            disable_btn,
            disable_btn,
            disable_btn,
            enable_btn,
            enable_btn,
        )
        return

    finish_tstamp = time.time()
    logger.info(f"{output}")

    conv.save_new_images(
        has_csam_images=state.has_csam_image, use_remote_storage=use_remote_storage
    )

    filename = get_conv_log_filename(
        is_vision=state.is_vision, has_csam_image=state.has_csam_image
    )

    with open(filename, "a") as fout:
        data = {
            "tstamp": round(finish_tstamp, 4),
            "type": "chat",
            "model": model_name,
            "gen_params": {
                "temperature": temperature,
                "top_p": top_p,
                "max_new_tokens": max_new_tokens,
            },
            "start": round(start_tstamp, 4),
            "finish": round(finish_tstamp, 4),
            "state": state.dict(),
            "ip": get_ip(request),
        }
        fout.write(json.dumps(data) + "\n")
    get_remote_logger().log(data)


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
    width: 20px !important;
    height: 20px !important;
    padding: 2px !important;
    font-size: 10px !important;
    opacity: 0.3 !important;
    transform: scale(0.6) !important;
    margin: 0 !important;
    /* Option 2: Completely hide - uncomment below and comment above if you prefer */
    /* display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important; */
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
    width: 20px !important;
    height: 20px !important;
    padding: 2px !important;
    font-size: 10px !important;
    opacity: 0.3 !important;
    transform: scale(0.6) !important;
    margin: 0 !important;
    /* Option 2: Completely hide - uncomment below and comment above if you prefer */
    /* display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important; */
}

/* Input box styling for better visual feedback */
#input_box {
    border: 2px solid #4f46e5 !important;
    border-radius: 16px !important;
    padding: 0 !important;
    font-size: 16px !important;
    background: linear-gradient(135deg, var(--input-background-fill) 0%, rgba(79, 70, 229, 0.05) 100%) !important;
    color: var(--body-text-color) !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15), 0 2px 4px rgba(0,0,0,0.1) !important;
    line-height: 1.5 !important;
    resize: none !important;
    overflow: hidden !important;
    position: relative !important;
    min-height: 64px !important;
    display: flex !important;
    align-items: center !important;
}

/* Add a subtle glow effect */
#input_box::before {
    content: '' !important;
    position: absolute !important;
    top: -2px !important;
    left: -2px !important;
    right: -2px !important;
    bottom: -2px !important;
    background: linear-gradient(45deg, #4f46e5, #7c3aed, #ec4899, #f59e0b) !important;
    border-radius: 18px !important;
    z-index: -1 !important;
    opacity: 0.6 !important;
    filter: blur(8px) !important;
    animation: rainbow-glow 3s ease-in-out infinite alternate !important;
}

@keyframes rainbow-glow {
    0% { opacity: 0.6; filter: blur(8px) hue-rotate(0deg); }
    100% { opacity: 0.8; filter: blur(12px) hue-rotate(30deg); }
}

/* Target the actual input/textarea element inside the input box */
#input_box textarea, #input_box input {
    border: none !important;
    background: transparent !important;
    padding: 16px 20px !important;
    margin: 0 !important;
    box-shadow: none !important;
    outline: none !important;
    font-size: 16px !important;
    line-height: 1.5 !important;
    color: var(--body-text-color) !important;
    border-radius: 16px !important;
    resize: none !important;
    font-weight: 500 !important;
    min-height: 32px !important;
    height: auto !important;
    flex: 1 !important;
}

/* Hide the inner container that creates the double border */
#input_box > div {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
    border-radius: 16px !important;
}

/* Send button alignment */
button[value="发送"] {
    height: 64px !important;
    border-radius: 16px !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    padding: 0 32px !important;
    min-width: 120px !important;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    transition: all 0.3s ease !important;
    margin-left: 12px !important;
}

button[value="发送"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4) !important;
}

/* Button row styling - make buttons larger and centered */
#buttons, [id*="button"] {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 16px !important;
    margin: 20px 0 !important;
}

/* General button styling - make all buttons larger */
button {
    height: 48px !important;
    border-radius: 12px !important;
    font-size: 16px !important;
    font-weight: 500 !important;
    padding: 0 24px !important;
    min-width: 140px !important;
    transition: all 0.3s ease !important;
    border: 2px solid transparent !important;
}

/* Specific button styling for different types */
button[value*="重新生成"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
}

button[value*="重新生成"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4) !important;
}

button[value*="清除历史"] {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3) !important;
}

button[value*="清除历史"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4) !important;
}

/* File upload button styling (for multimodal versions) */
button[value*="上传"], button[value*="Upload"], .upload-button {
    height: 56px !important;
    border-radius: 16px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    padding: 0 28px !important;
    min-width: 160px !important;
    background: linear-gradient(135deg, #ec4899 0%, #be185d 100%) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3) !important;
    transition: all 0.3s ease !important;
}

button[value*="上传"]:hover, button[value*="Upload"]:hover, .upload-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(236, 72, 153, 0.4) !important;
}

/* Input and button container alignment */
.gradio-container .block.gradio-row {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    gap: 12px !important;
}

/* Multimodal textbox styling (for file upload versions) */
.multimodal-textbox, [id*="multimodal"] {
    border: 2px solid #4f46e5 !important;
    border-radius: 16px !important;
    padding: 12px 16px !important;
    font-size: 16px !important;
    background: linear-gradient(135deg, var(--input-background-fill) 0%, rgba(79, 70, 229, 0.05) 100%) !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15) !important;
}

.multimodal-textbox:focus-within, [id*="multimodal"]:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2), 0 6px 20px rgba(79, 70, 229, 0.25) !important;
    transform: translateY(-1px) !important;
}

/* Center the button rows */
div[id*="button"], .button-row {
    display: flex !important;
    justify-content: center !important;
    flex-wrap: wrap !important;
    gap: 16px !important;
    margin: 24px 0 !important;
}

/* Disabled button styling */
button:disabled {
    opacity: 0.6 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

button:disabled:hover {
    transform: none !important;
    box-shadow: none !important;
}

/* Remove the problematic row alignment rules */
#input_box, button[value="发送"] {
    box-sizing: border-box !important;
}

/* Input row styling for proper alignment */
#input_row {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    margin: 20px 0 !important;
    padding: 0 20px !important;
    justify-content: center !important;
}

#input_box:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2), 0 6px 20px rgba(79, 70, 229, 0.25) !important;
    transform: translateY(-1px) !important;
}

#input_box::placeholder, #input_box textarea::placeholder, #input_box input::placeholder {
    color: rgba(156, 163, 175, 0.8) !important;
    font-weight: 400 !important;
    font-style: italic !important;
}

/* Input box ready state - subtle glow effect when ready for input */
#input_box.ready-for-input {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2), 0 2px 8px rgba(0,0,0,0.1) !important;
}

/* Input box sending state - subtle loading indicator */
#input_box.sending {
    border-color: #f59e0b !important;
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2), 0 2px 8px rgba(0,0,0,0.1) !important;
    opacity: 0.8 !important;
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

# JavaScript to force dark mode on page load
dark_mode_js = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Wait for Gradio to load
    setTimeout(function() {
        // Try to find and click the dark mode toggle button
        const darkModeButton = document.querySelector('button[aria-label="Dark mode"]') || 
                             document.querySelector('button[title="Dark mode"]') ||
                             document.querySelector('button[data-testid="theme-toggle"]') ||
                             document.querySelector('.theme-toggle') ||
                             document.querySelector('[data-theme-toggle]');
        
        if (darkModeButton) {
            // Check if we're not already in dark mode
            if (!document.documentElement.classList.contains('dark') && 
                !document.body.classList.contains('dark')) {
                darkModeButton.click();
            }
        } else {
            // Fallback: manually add dark mode class
            document.documentElement.classList.add('dark');
            document.body.classList.add('dark');
        }
    }, 1000);
    
    // Input box state management
    setTimeout(function() {
        const inputBox = document.getElementById('input_box');
        const sendBtn = document.querySelector('button[value="发送"]');
        
        if (inputBox) {
            // Add ready-for-input class by default
            inputBox.classList.add('ready-for-input');
            
            // Monitor for form submission or send button click
            const handleSending = function() {
                inputBox.classList.remove('ready-for-input');
                inputBox.classList.add('sending');
            };
            
            // Monitor for when input is ready again
            const handleReady = function() {
                setTimeout(function() {
                    inputBox.classList.remove('sending');
                    inputBox.classList.add('ready-for-input');
                }, 1000); // Small delay to show the sending state
            };
            
            // Listen for form submission
            const form = inputBox.closest('form');
            if (form) {
                form.addEventListener('submit', handleSending);
            }
            
            // Listen for send button click
            if (sendBtn) {
                sendBtn.addEventListener('click', handleSending);
            }
            
            // Listen for Enter key press
            inputBox.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    handleSending();
                }
            });
            
            // Monitor for chatbot updates (when response is received)
            const chatbot = document.getElementById('chatbot');
            if (chatbot) {
                const observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                            // Check if new content was added to chatbot
                            handleReady();
                        }
                    });
                });
                observer.observe(chatbot, { childList: true, subtree: true });
            }
            
            // Also monitor for input value changes (when input is cleared)
            const inputObserver = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                        if (inputBox.value === '') {
                            handleReady();
                        }
                    }
                });
            });
            inputObserver.observe(inputBox, { attributes: true });
        }
    }, 1500);
});
</script>
"""


def get_model_description_md(models):
    model_description_md = """
| | | |
| ---- | ---- | ---- |
"""
    ct = 0
    visited = set()
    for i, name in enumerate(models):
        minfo = get_model_info(name)
        if minfo.simple_name in visited:
            continue
        visited.add(minfo.simple_name)
        one_model_md = f"[{minfo.simple_name}]({minfo.link}): {minfo.description}"

        if ct % 3 == 0:
            model_description_md += "|"
        model_description_md += f" {one_model_md} |"
        if ct % 3 == 2:
            model_description_md += "\n"
        ct += 1
    return model_description_md


def build_about():
    about_markdown = """
# About Us
Chatbot Arena ([lmarena.ai](https://lmarena.ai)) is an open-source platform for evaluating AI through human preference, developed by researchers at UC Berkeley [SkyLab](https://sky.cs.berkeley.edu/) and [LMSYS](https://lmsys.org). We open-source the [FastChat](https://github.com/lm-sys/FastChat) project at GitHub and release open datasets. We always welcome contributions from the community. If you're interested in getting involved, we'd love to hear from you!

## Open-source contributors
- Leads: [Wei-Lin Chiang](https://infwinston.github.io/), [Anastasios Angelopoulos](https://people.eecs.berkeley.edu/~angelopoulos/)
- Contributors: [Lianmin Zheng](https://lmzheng.net/), [Ying Sheng](https://sites.google.com/view/yingsheng/home), [Lisa Dunlap](https://www.lisabdunlap.com/), [Christopher Chou](https://www.linkedin.com/in/chrisychou), [Tianle Li](https://codingwithtim.github.io/), [Evan Frick](https://efrick2002.github.io/), [Dacheng Li](https://dachengli1.github.io/), [Siyuan Zhuang](https://www.linkedin.com/in/siyuanzhuang)
- Advisors: [Ion Stoica](http://people.eecs.berkeley.edu/~istoica/), [Joseph E. Gonzalez](https://people.eecs.berkeley.edu/~jegonzal/), [Hao Zhang](https://cseweb.ucsd.edu/~haozhang/), [Trevor Darrell](https://people.eecs.berkeley.edu/~trevor/)

## Learn more
- Chatbot Arena [paper](https://arxiv.org/abs/2403.04132), [launch blog](https://blog.lmarena.ai/blog/2023/arena/), [dataset](https://github.com/lm-sys/FastChat/blob/main/docs/dataset_release.md), [policy](https://blog.lmarena.ai/blog/2024/policy/)
- LMSYS-Chat-1M dataset [paper](https://arxiv.org/abs/2309.11998), LLM Judge [paper](https://arxiv.org/abs/2306.05685)

## Contact Us
- Follow our [X](https://x.com/lmsysorg), [Discord](https://discord.gg/6GXcFg3TH8) or email us at `lmarena.ai@gmail.com`
- File issues on [GitHub](https://github.com/lm-sys/FastChat)
- Download our datasets and models on [HuggingFace](https://huggingface.co/lmsys)

## Acknowledgment
We thank [SkyPilot](https://github.com/skypilot-org/skypilot) and [Gradio](https://github.com/gradio-app/gradio) team for their system support.
We also thank [UC Berkeley SkyLab](https://sky.cs.berkeley.edu/), [Kaggle](https://www.kaggle.com/), [MBZUAI](https://mbzuai.ac.ae/), [a16z](https://www.a16z.com/), [Together AI](https://www.together.ai/), [Hyperbolic](https://hyperbolic.xyz/), [RunPod](https://runpod.io), [Anyscale](https://www.anyscale.com/), [HuggingFace](https://huggingface.co/) for their generous sponsorship. Learn more about partnership [here](https://lmsys.org/donations/).

<div class="sponsor-image-about">
    <img src="https://storage.googleapis.com/public-arena-asset/skylab.png" alt="SkyLab">
    <img src="https://storage.googleapis.com/public-arena-asset/kaggle.png" alt="Kaggle">
    <img src="https://storage.googleapis.com/public-arena-asset/mbzuai.jpeg" alt="MBZUAI">
    <img src="https://storage.googleapis.com/public-arena-asset/a16z.jpeg" alt="a16z">
    <img src="https://storage.googleapis.com/public-arena-asset/together.png" alt="Together AI">
    <img src="https://storage.googleapis.com/public-arena-asset/hyperbolic_logo.png" alt="Hyperbolic">
    <img src="https://storage.googleapis.com/public-arena-asset/runpod-logo.jpg" alt="RunPod">
    <img src="https://storage.googleapis.com/public-arena-asset/anyscale.png" alt="AnyScale">
    <img src="https://storage.googleapis.com/public-arena-asset/huggingface.png" alt="HuggingFace">
</div>
"""
    gr.Markdown(about_markdown, elem_id="about_markdown")


def build_single_model_ui(models, add_promotion_links=False):
    notice_markdown = f"""
<div class="hkgai-header">
    <h1>🚀 HKGAI 智能对话平台</h1>
    <h2>👇 开始聊天！</h2>
</div>
"""

    state = gr.State()
    gr.Markdown(notice_markdown, elem_id="notice_markdown")

    with gr.Group(elem_id="share-region-named"):
        with gr.Row(elem_id="model_selector_row"):
            model_selector = gr.Dropdown(
                choices=models,
                value=models[0] if len(models) > 0 else "",
                interactive=True,
                show_label=False,
                container=False,
            )

        chatbot = gr.Chatbot(
            elem_id="chatbot",
            label="Scroll down and start chatting",
            height=650,
            show_copy_button=True,
            latex_delimiters=[
                {"left": "$", "right": "$", "display": False},
                {"left": "$$", "right": "$$", "display": True},
                {"left": r"\(", "right": r"\)", "display": False},
                {"left": r"\[", "right": r"\]", "display": True},
            ],
        )
    with gr.Row(elem_id="input_row"):
        textbox = gr.Textbox(
            show_label=False,
            placeholder="👉 请输入您的问题并按回车键",
            elem_id="input_box",
        )
        send_btn = gr.Button(value="发送", variant="primary", scale=0, elem_id="send_btn")

    with gr.Row() as button_row:
        # Hide voting buttons to keep interface clean
        upvote_btn = gr.Button(value="👍  赞", interactive=False, visible=False)
        downvote_btn = gr.Button(value="👎  踩", interactive=False, visible=False)
        flag_btn = gr.Button(value="⚠️  举报", interactive=False, visible=False)
        regenerate_btn = gr.Button(value="🔄  重新生成", interactive=False, elem_id="regenerate_btn")
        clear_btn = gr.Button(value="🗑️  清除历史", interactive=False, elem_id="clear_btn")

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
            value=1024,
            step=64,
            interactive=True,
            label="最大输出长度",
        )

    # Register listeners
    btn_list = [upvote_btn, downvote_btn, flag_btn, regenerate_btn, clear_btn]
    upvote_btn.click(
        upvote_last_response,
        [state, model_selector],
        [textbox, upvote_btn, downvote_btn, flag_btn],
    )
    downvote_btn.click(
        downvote_last_response,
        [state, model_selector],
        [textbox, upvote_btn, downvote_btn, flag_btn],
    )
    flag_btn.click(
        flag_last_response,
        [state, model_selector],
        [textbox, upvote_btn, downvote_btn, flag_btn],
    )
    regenerate_btn.click(regenerate, state, [state, chatbot, textbox] + btn_list).then(
        bot_response,
        [state, temperature, top_p, max_output_tokens],
        [state, chatbot] + btn_list,
    )
    clear_btn.click(clear_history, None, [state, chatbot, textbox] + btn_list)

    model_selector.change(clear_history, None, [state, chatbot, textbox] + btn_list)

    textbox.submit(
        add_text,
        [state, model_selector, textbox],
        [state, chatbot, textbox] + btn_list,
    ).then(
        bot_response,
        [state, temperature, top_p, max_output_tokens],
        [state, chatbot] + btn_list,
    )
    send_btn.click(
        add_text,
        [state, model_selector, textbox],
        [state, chatbot, textbox] + btn_list,
    ).then(
        bot_response,
        [state, temperature, top_p, max_output_tokens],
        [state, chatbot] + btn_list,
    )

    return [state, model_selector]


def build_demo(models):
    with gr.Blocks(
        title="HKGAI 智能对话平台",
        theme=gr.themes.Soft(text_size=gr.themes.sizes.text_lg).set(
            body_background_fill="*neutral_950",
            body_text_color="*neutral_50",
            button_primary_background_fill="*primary_600",
            button_primary_text_color="white",
            button_secondary_background_fill="*neutral_800",
            button_secondary_text_color="*neutral_50",
            block_background_fill="*neutral_900",
            block_border_color="*neutral_700",
            input_background_fill="*neutral_800",
            panel_background_fill="*neutral_900",
            panel_border_color="*neutral_700",
        ),
        css=block_css,
        head=dark_mode_js,
    ) as demo:
        url_params = gr.JSON(visible=False)

        state, model_selector = build_single_model_ui(models)

        if args.model_list_mode not in ["once", "reload"]:
            raise ValueError(f"Unknown model list mode: {args.model_list_mode}")

        if args.show_terms_of_use:
            load_js = get_window_url_params_with_tos_js
        else:
            load_js = get_window_url_params_js

        demo.load(
            load_demo,
            [url_params],
            [
                state,
                model_selector,
            ],
            js=load_js,
        )

    return demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int)
    parser.add_argument(
        "--share",
        action="store_true",
        help="Whether to generate a public, shareable link",
    )
    parser.add_argument(
        "--controller-url",
        type=str,
        default="http://localhost:21001",
        help="The address of the controller",
    )
    parser.add_argument(
        "--concurrency-count",
        type=int,
        default=10,
        help="The concurrency count of the gradio queue",
    )
    parser.add_argument(
        "--model-list-mode",
        type=str,
        default="once",
        choices=["once", "reload"],
        help="Whether to load the model list once or reload the model list every time",
    )
    parser.add_argument(
        "--moderate",
        action="store_true",
        help="Enable content moderation to block unsafe inputs",
    )
    parser.add_argument(
        "--show-terms-of-use",
        action="store_true",
        help="Shows term of use before loading the demo",
    )
    parser.add_argument(
        "--register-api-endpoint-file",
        type=str,
        help="Register API-based model endpoints from a JSON file",
    )
    parser.add_argument(
        "--gradio-auth-path",
        type=str,
        help='Set the gradio authentication file path. The file should contain one or more user:password pairs in this format: "u1:p1,u2:p2,u3:p3"',
    )
    parser.add_argument(
        "--gradio-root-path",
        type=str,
        help="Sets the gradio root path, eg /abc/def. Useful when running behind a reverse-proxy or at a custom URL path prefix",
    )
    parser.add_argument(
        "--use-remote-storage",
        action="store_true",
        default=False,
        help="Uploads image files to google cloud storage if set to true",
    )
    args = parser.parse_args()
    logger.info(f"args: {args}")

    # Set global variables
    set_global_vars(args.controller_url, args.moderate, args.use_remote_storage)
    models, all_models = get_model_list(
        args.controller_url, args.register_api_endpoint_file, vision_arena=False
    )

    # Set authorization credentials
    auth = None
    if args.gradio_auth_path is not None:
        auth = parse_gradio_auth_creds(args.gradio_auth_path)

    # Launch the demo
    demo = build_demo(models)
    demo.queue(
        default_concurrency_limit=args.concurrency_count,
        status_update_rate=10,
        api_open=False,
    ).launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        max_threads=200,
        auth=auth,
        root_path=args.gradio_root_path,
    )
