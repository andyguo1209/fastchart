"""
The gradio demo server with multiple tabs.
It supports chatting with a single model or chatting with two models side-by-side.
"""

import argparse
import gradio as gr

from fastchat.serve.gradio_block_arena_anony import (
    build_side_by_side_ui_anony,
    load_demo_side_by_side_anony,
    set_global_vars_anony,
)
from fastchat.serve.gradio_block_arena_named import (
    build_side_by_side_ui_named,
    load_demo_side_by_side_named,
    set_global_vars_named,
)
from fastchat.serve.gradio_block_arena_vision import (
    build_single_vision_language_model_ui,
)
from fastchat.serve.gradio_block_arena_vision_anony import (
    build_side_by_side_vision_ui_anony,
    load_demo_side_by_side_vision_anony,
)
from fastchat.serve.gradio_block_arena_vision_named import (
    build_side_by_side_vision_ui_named,
    load_demo_side_by_side_vision_named,
)
from fastchat.serve.gradio_block_reports import build_reports_tab
from fastchat.serve.gradio_global_state import Context

from fastchat.serve.gradio_web_server import (
    set_global_vars,
    block_css,
    build_single_model_ui,
    build_about,
    get_model_list,
    load_demo_single,
    get_ip,
)
from fastchat.serve.monitor.monitor import build_leaderboard_tab
from fastchat.utils import (
    build_logger,
    get_window_url_params_js,
    get_window_url_params_with_tos_js,
    alert_js,
    parse_gradio_auth_creds,
)

logger = build_logger("gradio_web_server_multi", "gradio_web_server_multi.log")


def build_visualizer():
    visualizer_markdown = """
    # 🔍 竞技场可视化
    竞技场可视化提供交互式工具来探索和分析我们的排行榜数据。
    """
    gr.Markdown(visualizer_markdown, elem_id="visualizer_markdown")
    with gr.Tabs():
        with gr.Tab("主题浏览器", id=0):
            topic_markdown = """ 
            这个工具提供了一个交互式的方式来探索人们如何使用聊天机器人竞技场。
            使用 *[主题聚类](https://github.com/MaartenGr/BERTopic)*，我们将用户在竞技场对战中提交的提示组织成广泛和具体的类别。
            深入探索以发现这些提示的分布和主题洞察！ """
            gr.Markdown(topic_markdown)
            expandText = (
                "👇 展开查看如何使用可视化器的详细说明"
            )
            with gr.Accordion(expandText, open=False):
                instructions = """
                - 悬停在分段上：查看类别名称、提示数量和百分比。
                    - *在移动设备上*：点击而不是悬停。
                - 点击探索： 
                    - 点击主类别查看其子类别。
                    - 点击子类别在侧边栏查看示例提示。
                - 撤销和重置：点击图表中心返回顶层。

                可视化器使用2024年6月至2024年8月收集的竞技场对战数据创建。
                """
                gr.Markdown(instructions)

            frame = """
                        <iframe class="visualizer" width="100%"
                                src="https://storage.googleapis.com/public-arena-no-cors/index.html">
                        </iframe>
                    """
            gr.HTML(frame)
        with gr.Tab("价格浏览器", id=1):
            price_markdown = """
            这个散点图展示了竞技场中的一些模型，绘制了它们的得分与成本的关系。只包含具有公开可用定价和参数信息的模型，这意味着像Gemini的实验模型等不会显示。请随时查看价格来源或在[此处](https://github.com/lmarena/arena-catalog/blob/main/data/scatterplot-data.json)添加定价信息。
            """
            gr.Markdown(price_markdown)
            expandText = (
                "👇 展开查看如何使用散点图的详细说明"
            )
            with gr.Accordion(expandText, open=False):
                instructions = """
                - 悬停在点上：查看模型的竞技场得分、成本、组织和许可证。
                - 点击点：点击一个点访问模型的网站。
                - 使用图例：点击右侧的组织名称显示其模型。要比较模型，请点击多个组织名称。
                - 选择类别：使用右上角的下拉菜单选择类别并查看该类别的竞技场得分。
                """
                gr.Markdown(instructions)

            frame = """<object type="text/html" data="https://storage.googleapis.com/public-arena-no-cors/scatterplot.html" width="100%" class="visualizer"></object>"""

            gr.HTML(frame)


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
});
</script>
"""

def load_demo(context: Context, request: gr.Request):
    ip = get_ip(request)
    logger.info(f"load_demo. ip: {ip}. params: {request.query_params}")

    inner_selected = 0
    if "arena" in request.query_params:
        inner_selected = 0
    elif "vision" in request.query_params:
        inner_selected = 0
    elif "compare" in request.query_params:
        inner_selected = 1
    elif "direct" in request.query_params or "model" in request.query_params:
        inner_selected = 2
    elif "leaderboard" in request.query_params:
        inner_selected = 3
    elif "about" in request.query_params:
        inner_selected = 4

    if args.model_list_mode == "reload":
        context.text_models, context.all_text_models = get_model_list(
            args.controller_url,
            args.register_api_endpoint_file,
            vision_arena=False,
        )

        context.vision_models, context.all_vision_models = get_model_list(
            args.controller_url,
            args.register_api_endpoint_file,
            vision_arena=True,
        )

    # Text models
    if args.vision_arena:
        side_by_side_anony_updates = load_demo_side_by_side_vision_anony()

        side_by_side_named_updates = load_demo_side_by_side_vision_named(
            context,
        )

        direct_chat_updates = load_demo_single(context, request.query_params)
    else:
        direct_chat_updates = load_demo_single(context, request.query_params)
        side_by_side_anony_updates = load_demo_side_by_side_anony(
            context.all_text_models, request.query_params
        )
        side_by_side_named_updates = load_demo_side_by_side_named(
            context.text_models, request.query_params
        )

    tabs_list = (
        [gr.Tabs(selected=inner_selected)]
        + side_by_side_anony_updates
        + side_by_side_named_updates
        + direct_chat_updates
    )

    return tabs_list


def build_demo(
    context: Context, elo_results_file: str, leaderboard_table_file, arena_hard_table
):
    if args.show_terms_of_use:
        load_js = get_window_url_params_with_tos_js
    else:
        load_js = get_window_url_params_js

    head_js = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
"""
    if args.ga_id is not None:
        head_js += f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={args.ga_id}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());

gtag('config', '{args.ga_id}');
window.__gradio_mode__ = "app";
</script>
        """
    text_size = gr.themes.sizes.text_lg
    with gr.Blocks(
        title="HKGAI 智能对话平台",
        theme=gr.themes.Soft(text_size=text_size).set(
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
        head=head_js + dark_mode_js,
    ) as demo:
        with gr.Tabs() as inner_tabs:
            if args.vision_arena:
                with gr.Tab("⚔️ 竞技场 (对战)", id=0) as arena_tab:
                    arena_tab.select(None, None, None, js=load_js)
                    side_by_side_anony_list = build_side_by_side_vision_ui_anony(
                        context,
                        random_questions=args.random_questions,
                    )
                with gr.Tab("⚔️ 竞技场 (并排)", id=1) as side_by_side_tab:
                    side_by_side_tab.select(None, None, None, js=alert_js)
                    side_by_side_named_list = build_side_by_side_vision_ui_named(
                        context, random_questions=args.random_questions
                    )

                with gr.Tab("💬 直接对话", id=2) as direct_tab:
                    direct_tab.select(None, None, None, js=alert_js)
                    single_model_list = build_single_vision_language_model_ui(
                        context,
                        add_promotion_links=True,
                        random_questions=args.random_questions,
                    )

            else:
                with gr.Tab("⚔️ 竞技场 (对战)", id=0) as arena_tab:
                    arena_tab.select(None, None, None, js=load_js)
                    side_by_side_anony_list = build_side_by_side_ui_anony(
                        context.all_text_models
                    )

                with gr.Tab("⚔️ 竞技场 (并排)", id=1) as side_by_side_tab:
                    side_by_side_tab.select(None, None, None, js=alert_js)
                    side_by_side_named_list = build_side_by_side_ui_named(
                        context.text_models
                    )

                with gr.Tab("💬 直接对话", id=2) as direct_tab:
                    direct_tab.select(None, None, None, js=alert_js)
                    single_model_list = build_single_model_ui(
                        context.text_models, add_promotion_links=True
                    )

            demo_tabs = (
                [inner_tabs]
                + side_by_side_anony_list
                + side_by_side_named_list
                + single_model_list
            )

            if elo_results_file:
                with gr.Tab("🏆 排行榜", id=3):
                    build_leaderboard_tab(
                        elo_results_file,
                        leaderboard_table_file,
                        arena_hard_table,
                        show_plot=True,
                    )

            with gr.Tab("📊 报告", id=4):
                build_reports_tab()

            if args.show_visualizer:
                with gr.Tab("🔍 竞技场可视化", id=5):
                    build_visualizer()

        context_state = gr.State(context)

        if args.model_list_mode not in ["once", "reload"]:
            raise ValueError(f"Unknown model list mode: {args.model_list_mode}")

        demo.load(
            load_demo,
            [context_state],
            demo_tabs,
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
        help="Whether to load the model list once or reload the model list every time.",
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
        "--vision-arena", action="store_true", help="Show tabs for vision arena."
    )
    parser.add_argument(
        "--random-questions", type=str, help="Load random questions from a JSON file"
    )
    parser.add_argument(
        "--register-api-endpoint-file",
        type=str,
        help="Register API-based model endpoints from a JSON file",
    )
    parser.add_argument(
        "--gradio-auth-path",
        type=str,
        help='Set the gradio authentication file path. The file should contain one or \
              more user:password pairs in this format: "u1:p1,u2:p2,u3:p3"',
        default=None,
    )
    parser.add_argument(
        "--elo-results-file", type=str, help="Load leaderboard results and plots"
    )
    parser.add_argument(
        "--leaderboard-table-file", type=str, help="Load leaderboard results and plots"
    )
    parser.add_argument(
        "--arena-hard-table", type=str, help="Load leaderboard results and plots"
    )
    parser.add_argument(
        "--gradio-root-path",
        type=str,
        help="Sets the gradio root path, eg /abc/def. Useful when running behind a \
              reverse-proxy or at a custom URL path prefix",
    )
    parser.add_argument(
        "--ga-id",
        type=str,
        help="the Google Analytics ID",
        default=None,
    )
    parser.add_argument(
        "--use-remote-storage",
        action="store_true",
        default=False,
        help="Uploads image files to google cloud storage if set to true",
    )
    parser.add_argument(
        "--password",
        type=str,
        help="Set the password for the gradio web server",
    )
    parser.add_argument(
        "--show-visualizer",
        action="store_true",
        default=False,
        help="Show the Data Visualizer tab",
    )
    args = parser.parse_args()
    logger.info(f"args: {args}")

    # Set global variables
    set_global_vars(args.controller_url, args.moderate, args.use_remote_storage)
    set_global_vars_named(args.moderate)
    set_global_vars_anony(args.moderate)
    text_models, all_text_models = get_model_list(
        args.controller_url,
        args.register_api_endpoint_file,
        vision_arena=False,
    )

    vision_models, all_vision_models = get_model_list(
        args.controller_url,
        args.register_api_endpoint_file,
        vision_arena=True,
    )

    models = text_models + [
        model for model in vision_models if model not in text_models
    ]
    all_models = all_text_models + [
        model for model in all_vision_models if model not in all_text_models
    ]
    context = Context(
        text_models,
        all_text_models,
        vision_models,
        all_vision_models,
        models,
        all_models,
    )

    # Set authorization credentials
    auth = None
    if args.gradio_auth_path is not None:
        auth = parse_gradio_auth_creds(args.gradio_auth_path)

    # Launch the demo
    demo = build_demo(
        context,
        args.elo_results_file,
        args.leaderboard_table_file,
        args.arena_hard_table,
    )
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
        show_api=False,
    )
