// 简化的图表绘制实现
window.SimpleChart = {
    drawDoughnut: function(canvas, data, labels, colors) {
        const ctx = canvas.getContext('2d');
        if (canvas.width === 0 || canvas.height === 0) {
            canvas.width = 400;
            canvas.height = 300;
        }
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2 - 20;
        const radius = Math.min(centerX, centerY - 30) * 0.8;
        const innerRadius = radius * 0.5;
        let total = data.reduce((a, b) => a + b, 0);
        if (total === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('暂无数据', centerX, centerY);
            return;
        }
        let currentAngle = -Math.PI / 2;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        data.forEach((value, index) => {
            if (value === 0) return;
            const sliceAngle = (value / total) * 2 * Math.PI;
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.arc(centerX, centerY, innerRadius, currentAngle + sliceAngle, currentAngle, true);
            ctx.closePath();
            ctx.fillStyle = colors[index];
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 3;
            ctx.stroke();
            currentAngle += sliceAngle;
        });
        ctx.fillStyle = '#333';
        ctx.font = 'bold 18px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('总计', centerX, centerY - 8);
        ctx.font = 'bold 24px Arial';
        ctx.fillText(total.toString(), centerX, centerY + 15);
        const legendY = canvas.height - 40;
        const legendStartX = (canvas.width - this.calculateLegendWidth(labels, data, ctx)) / 2;
        let legendX = legendStartX;
        labels.forEach((label, index) => {
            if (data[index] === 0) return;
            ctx.fillStyle = colors[index];
            ctx.fillRect(legendX, legendY, 16, 16);
            ctx.fillStyle = '#333';
            ctx.font = '14px Arial';
            ctx.textAlign = 'left';
            const text = label + ': ' + data[index];
            ctx.fillText(text, legendX + 22, legendY + 12);
            legendX += ctx.measureText(text).width + 40;
        });
    },
    calculateLegendWidth: function(labels, data, ctx) {
        ctx.font = '14px Arial';
        let totalWidth = 0;
        labels.forEach((label, index) => {
            if (data[index] === 0) return;
            const text = label + ': ' + data[index];
            totalWidth += ctx.measureText(text).width + 40 + 22;
        });
        return totalWidth - 40;
    },
    drawBar: function(canvas, data, labels, colors) {
        const ctx = canvas.getContext('2d');
        if (canvas.width === 0 || canvas.height === 0) {
            canvas.width = 400;
            canvas.height = 300;
        }
        const padding = 60;
        const chartWidth = canvas.width - padding * 2;
        const chartHeight = canvas.height - padding * 2 - 40;
        const barWidth = Math.min(chartWidth / labels.length * 0.6, 80);
        const maxValue = Math.max(...data, 1);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (data.length === 0 || maxValue === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('暂无数据', canvas.width / 2, canvas.height / 2);
            return;
        }
        ctx.strokeStyle = '#f5f5f5';
        ctx.lineWidth = 1;
        for (let i = 0; i <= 5; i++) {
            const y = padding + (chartHeight / 5) * i;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(canvas.width - padding, y);
            ctx.stroke();
        }
        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, canvas.height - padding - 40);
        ctx.lineTo(canvas.width - padding, canvas.height - padding - 40);
        ctx.stroke();
        data.forEach((value, index) => {
            const barHeight = (value / maxValue) * chartHeight;
            const x = padding + (chartWidth / labels.length) * index + (chartWidth / labels.length - barWidth) / 2;
            const y = canvas.height - padding - 40 - barHeight;
            ctx.fillStyle = colors[index];
            ctx.fillRect(x, y, barWidth, barHeight);
            ctx.strokeStyle = colors[index].replace('0.8', '1');
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, barWidth, barHeight);
            ctx.fillStyle = '#333';
            ctx.font = 'bold 14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(value.toFixed(1) + '%', x + barWidth / 2, y - 8);
            ctx.font = '12px Arial';
            const label = labels[index];
            const maxLabelWidth = barWidth + 20;
            if (ctx.measureText(label).width > maxLabelWidth) {
                const words = label.split('-');
                if (words.length > 1) {
                    ctx.fillText(words[0], x + barWidth / 2, canvas.height - padding - 25);
                    ctx.fillText(words.slice(1).join('-'), x + barWidth / 2, canvas.height - padding - 10);
                } else {
                    let truncated = label;
                    while (ctx.measureText(truncated + '...').width > maxLabelWidth && truncated.length > 3) {
                        truncated = truncated.slice(0, -1);
                    }
                    ctx.fillText(truncated + (truncated.length < label.length ? '...' : ''), x + barWidth / 2, canvas.height - padding - 15);
                }
            } else {
                ctx.fillText(label, x + barWidth / 2, canvas.height - padding - 15);
            }
        });
        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 5; i++) {
            const value = (maxValue / 5) * (5 - i);
            const y = padding + (chartHeight / 5) * i;
            ctx.fillText(value.toFixed(0) + '%', padding - 10, y + 4);
        }
        ctx.save();
        ctx.translate(20, canvas.height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = '#333';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('胜率 (%)', 0, 0);
        ctx.restore();
    }
};
window.Chart = function(ctx, config) {
    const canvas = ctx.canvas;
    const type = config.type;
    if (type === 'doughnut') {
        const data = config.data.datasets[0].data;
        const labels = config.data.labels;
        const colors = config.data.datasets[0].backgroundColor;
        window.SimpleChart.drawDoughnut(canvas, data, labels, colors);
    } else if (type === 'bar') {
        const data = config.data.datasets[0].data;
        const labels = config.data.labels;
        const colors = config.data.datasets[0].backgroundColor;
        window.SimpleChart.drawBar(canvas, data, labels, colors);
    }
};
Chart.version = "SimpleChart-1.0";
