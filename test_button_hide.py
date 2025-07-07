#!/usr/bin/env python3
"""
Test script to verify button hiding functionality
"""
import gradio as gr

# Test CSS for hiding buttons
test_css = """
/* Test CSS to hide clear buttons */
#clear_btn {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

.hidden-clear-btn {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

button[value*="清除历史"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

button[title*="清空对话"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
"""

# Test JavaScript
test_js = """
function hideButtons() {
    console.log('Hiding buttons...');
    document.querySelectorAll('button').forEach(btn => {
        if (btn.textContent.includes('清除历史') || 
            btn.textContent.includes('清空对话') ||
            btn.id === 'clear_btn') {
            btn.style.display = 'none';
            btn.style.visibility = 'hidden';
            btn.style.opacity = '0';
            console.log('Hidden button:', btn.textContent);
        }
    });
}

// Run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideButtons);
} else {
    hideButtons();
}

// Run periodically
setInterval(hideButtons, 1000);
"""

def test_interface():
    with gr.Blocks(css=test_css, head=f"<script>{test_js}</script>") as demo:
        gr.Markdown("# 测试按钮隐藏功能")
        
        with gr.Row():
            visible_btn = gr.Button(value="✅ 可见按钮", elem_id="visible_btn")
            clear_btn = gr.Button(value="🗑️ 清除历史", elem_id="clear_btn", visible=False, elem_classes=["hidden-clear-btn"])
            another_clear = gr.Button(value="清空对话", elem_id="another_clear")
        
        output = gr.Textbox(label="输出")
        
        visible_btn.click(lambda: "可见按钮被点击了！", outputs=output)
        clear_btn.click(lambda: "清除按钮被点击了！", outputs=output)
        another_clear.click(lambda: "另一个清除按钮被点击了！", outputs=output)
        
        demo.load(js=f"setTimeout(function() {{ {test_js} }}, 100);")
    
    return demo

if __name__ == "__main__":
    demo = test_interface()
    demo.launch(debug=True) 