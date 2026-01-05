// ==========================================
// 1. 全局变量与工具准备
// ==========================================
let scatterDataCache = null; 
let tooltip; 

document.addEventListener("DOMContentLoaded", function() {
    // 初始化散点图 Tooltip
    tooltip = d3.select("body").append("div")
        .attr("id", "global-tooltip")
        .style("opacity", 0)
        .style("position", "absolute")
        .style("background", "rgba(0,0,0,0.8)")
        .style("color", "#fff")
        .style("padding", "10px")
        .style("border-radius", "5px")
        .style("font-size", "14px") // 增大字体
        .style("pointer-events", "none")
        .style("z-index", "9999");
});

// ==========================================
// 2. Tab 切换与数据读取逻辑
// ==========================================
window.switchTab = function(index) {
    // 1. 隐藏所有 Tab
    var tabs = document.getElementsByClassName('tab-content');
    for (var i = 0; i < tabs.length; i++) {
        tabs[i].style.display = 'none';
    }

    // 2. 显示当前 Tab
    var selected = document.getElementById('content-' + index);
    if (selected) {
        selected.style.display = 'block';
    }

    // 3. 模块 2 特殊逻辑：加载 CSV 并绘图
    if (index === 2) {
        setTimeout(() => {
            if (scatterDataCache) {
                drawScatterPlot(scatterDataCache);
            } else {
                // --- 加载 CSV ---
                d3.csv("final_data.csv").then(function(data) {
                    // ★★★ 核心修复：添加 source 字段判断 ★★★
                    data.forEach(d => {
                        d.year = +d.year;
                        d.similarity = +d.similarity;
                        // 这里判断学院名称是否包含 "MIT"，从而打上标签
                        d.source = (d.college && d.college.includes("MIT")) ? "MIT" : "Nankai";
                    });
                    
                    scatterDataCache = data;
                    drawScatterPlot(data);
                }).catch(function(error) {
                    console.error("CSV加载失败:", error);
                    const errDiv = document.getElementById('scatter-error');
                    if(errDiv) errDiv.innerText = "加载失败: " + error.message;
                });
            }
        }, 50); 
    }
}

// ==========================================
// 3. 核心绘图逻辑 (与上传的 HTML 完全一致)
// ==========================================

function kernelDensityEstimator(kernel, X) {
    return function(V) {
        return X.map(function(x) {
            return [x, d3.mean(V, function(v) { return kernel(x - v); })];
        });
    };
}

function kernelEpanechnikov(k) {
    return function(v) {
        return Math.abs(v /= k) <= 1 ? 0.75 * (1 - v * v) / k : 0;
    };
}

function drawScatterPlot(data) {
    const container = "#scatter-plot";
    const margin = {top: 20, right: 30, bottom: 40, left: 60};
    
    // 获取容器宽度 (自适应)
    const containerEl = document.querySelector(container);
    const clientWidth = containerEl ? containerEl.clientWidth : 1200;
    const width = clientWidth - margin.left - margin.right;
    const height = 500 - margin.top - margin.bottom;

    d3.select(container).html("");
    const svg = d3.select(container).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    if(data.length === 0) return;

    const years = Array.from(new Set(data.map(d => d.year))).sort((a,b)=>a-b);
    
    // --- 动态计算 Y 轴 ---
    const yMin = d3.min(data, d => d.similarity);
    const yMax = d3.max(data, d => d.similarity);
    const yPadding = (yMax - yMin) * 0.1; 
    const yDomain = [
        Math.max(0, yMin - yPadding), 
        Math.min(1.05, yMax + yPadding) 
    ];

    const x = d3.scaleBand().domain(years).range([0, width]).padding(0.05);
    const y = d3.scaleLinear().domain(yDomain).range([height, 0]);
    
    const sourceColor = d3.scaleOrdinal()
        .domain(["Nankai", "MIT"])
        .range(["#2c82c9", "#e74c3c"]);

    // --- KDE 计算 ---
    const dataByYear = d3.group(data, d => d.year);
    const kdeTicks = y.ticks(100); 
    const bandwidth = (yDomain[1] - yDomain[0]) / 25;
    const kde = kernelDensityEstimator(kernelEpanechnikov(bandwidth), kdeTicks);

    let maxDensity = 0;
    const denseDataStruct = {}; 

    years.forEach(year => {
        denseDataStruct[year] = { Nankai: null, MIT: null };
        const yearData = dataByYear.get(year) || [];
        
        // ★★★ 这里的筛选依赖于前面 d.source 的正确赋值 ★★★
        const nankaiSims = yearData.filter(d => d.source === "Nankai").map(d => d.similarity);
        const mitSims = yearData.filter(d => d.source === "MIT").map(d => d.similarity);

        if (nankaiSims.length > 1) {
            const d = kde(nankaiSims);
            denseDataStruct[year].Nankai = d;
            d.forEach(pt => { if(pt[1] > maxDensity) maxDensity = pt[1]; });
        }
        if (mitSims.length > 1) {
            const d = kde(mitSims);
            denseDataStruct[year].MIT = d;
            d.forEach(pt => { if(pt[1] > maxDensity) maxDensity = pt[1]; });
        }
    });

    const violinWidthScale = d3.scaleLinear()
        .domain([0, maxDensity])
        .range([0, x.bandwidth() / 2 * 0.9]);

    const rightHalfArea = d3.area()
        .x0(0)
        .x1(d => violinWidthScale(d[1]))
        .y(d => y(d[0]))
        .curve(d3.curveBasis);

    // --- 绘制 ---
    // 坐标轴
    svg.append("g").attr("transform", `translate(0,${height})`)
       .call(d3.axisBottom(x).tickFormat(d3.format("d")))
       .selectAll("text").style("fill", "#fff").style("font-size", "12px"); // 增大坐标轴字体
       
    svg.append("g").call(d3.axisLeft(y).ticks(5))
       .selectAll("text").style("fill", "#fff").style("font-size", "12px");

    years.forEach(year => {
        const xCenter = x(year) + x.bandwidth() / 2;
        
        svg.append("line")
            .attr("class", "year-separator-dashed")
            .attr("x1", xCenter).attr("x2", xCenter)
            .attr("y1", 0).attr("y2", height)
            .attr("stroke", "#555")
            .attr("stroke-dasharray", "4");

        const densities = denseDataStruct[year];
        if (densities.Nankai) {
            svg.append("path").datum(densities.Nankai).attr("class", "violin-path")
                .attr("transform", `translate(${xCenter},0)`)
                .attr("fill", sourceColor("Nankai")).attr("stroke", sourceColor("Nankai"))
                .style("fill-opacity", 0.3)
                .style("mix-blend-mode", "normal") // 修正混合模式以适应深色背景
                .attr("d", rightHalfArea);
        }
        if (densities.MIT) {
            svg.append("path").datum(densities.MIT).attr("class", "violin-path")
                .attr("transform", `translate(${xCenter},0)`)
                .attr("fill", sourceColor("MIT")).attr("stroke", sourceColor("MIT"))
                .style("fill-opacity", 0.3)
                .style("mix-blend-mode", "normal")
                .attr("d", rightHalfArea);
        }
    });

    // 绘制散点
    svg.selectAll(".dot")
        .data(data)
        .enter().append("circle")
        .attr("class", "dot")
        .attr("cx", d => {
            const bandStart = x(d.year);
            const bandWidth = x.bandwidth();
            const jitterWidth = bandWidth / 2 - 10;
            const jitter = Math.random() * jitterWidth + 5; 
            return bandStart + jitter;
        })
        .attr("cy", d => y(d.similarity))
        .attr("r", 4)
        .style("fill", d => sourceColor(d.source))
        .style("opacity", 0.7)
        .on("mouseover", function(event, d) {
            d3.select(this).attr("r", 8).style("opacity", 1).style("stroke", "#fff");
            
            let content = `<div style="font-weight:600; color:${sourceColor(d.source)}">${d.source === 'MIT' ? 'MIT CSAIL' : '南开大学'}</div>`;
            content += `<div style="margin:5px 0; font-weight:bold; color:#fff;">${d.title}</div>`;
            content += `<div style="font-size:12px; color:#ddd; line-height:1.5;">`;
            if (d.source !== 'MIT') {
                content += `作者: ${d.author || '-'}<br>导师: ${d.supervisor || '-'}<br>`;
            }
            content += `学院: ${d.college}<br>`;
            content += `相似度: <strong>${d.similarity.toFixed(4)}</strong>`;
            content += `</div>`;
            
            tooltip.style("opacity", 1).html(content)
                .style("left", (event.pageX + 15) + "px").style("top", (event.pageY + 15) + "px");
        })
        .on("mouseout", function() {
            d3.select(this).attr("r", 4).style("opacity", 0.7).style("stroke", "none");
            tooltip.style("opacity", 0);
        });
}

// ==========================================
// 4. 左侧河流图 (DOMContentLoaded)
// ==========================================
document.addEventListener("DOMContentLoaded", function() {
    const config = {
        containerId: "#line-chart",
        legendId: "#stream-legend",
        titleId: "#chart-title-text",
        switchBtnId: "#switch-btn",
        streamApiUrl: "http://localhost:3020/api/cjy/stream-data", 
        colors: ["#5bb5bd", "#FEB536", "#9F2E2E", "#14507D", "#5a8446", "#CF9197", "#8B5F48", "#7A6E79"]
    };

    let currentType = 'line'; 
    let streamDataCache = null;
    let streamTooltip = d3.select(".stream-tooltip");

    if (streamTooltip.empty()) {
        streamTooltip = d3.select("body").append("div")
            .attr("class", "stream-tooltip") // CSS中已设置此类的样式
            .style("position", "absolute")
            .style("background", "rgba(0,0,0,0.9)")
            .style("color", "#fff")
            .style("border-radius", "8px")
            .style("pointer-events", "none")
            .style("opacity", 0)
            .style("z-index", 9999)
            .style("box-shadow", "0 4px 12px rgba(0,0,0,0.5)");
    }

    const btn = document.querySelector(config.switchBtnId);
    if(btn) btn.addEventListener("click", toggleChart);

    function toggleChart() {
        const container = d3.select(config.containerId);
        const title = document.querySelector(config.titleId);

        if (currentType === 'line') {
            currentType = 'stream';
            title.innerText = "Top15 学院论文发表演变 (2004起)";
            container.html(""); 
            d3.select(config.legendId).style("display", "flex");

            if (streamDataCache) {
                drawStreamGraph(streamDataCache);
            } else {
                fetchStreamData();
            }
        } else {
            currentType = 'line';
            title.innerText = "各学院平均参考文献引用数";
            container.html(""); 
            d3.select(config.legendId).html("").style("display", "none");
            if (typeof window.loadLineChart === 'function') window.loadLineChart();
        }
    }

    async function fetchStreamData() {
        try {
            const res = await fetch(config.streamApiUrl);
            const json = await res.json();
            if (json.code === 200) {
                streamDataCache = json.data;
                drawStreamGraph(json.data);
            }
        } catch (e) {
            console.error(e);
        }
    }

    function drawStreamGraph(data) {
        const containerEl = document.querySelector(config.containerId);
        data.forEach(d => { d.year = Number(d.year); d.count = Number(d.count); });
        let cleanData = data.filter(d => d.year >= 2004);
        
        const collegeTotals = d3.rollups(cleanData, v => d3.sum(v, d => d.count), d => d.college);
        collegeTotals.sort((a, b) => b[1] - a[1]);
        const top15Names = collegeTotals.slice(0, 15).map(d => d[0]);
        cleanData = cleanData.filter(d => top15Names.includes(d.college));

        const width = containerEl.clientWidth || 600;
        const height = containerEl.clientHeight || 400;
        const margin = {top: 20, right: 20, bottom: 30, left: 130}; 
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        d3.select(config.containerId).selectAll("*").remove();
        const svg = d3.select(config.containerId).append("svg")
            .attr("width", width).attr("height", height)
            .append("g").attr("transform", `translate(${margin.left},${margin.top})`);

        const colleges = top15Names; 
        const years = Array.from(new Set(cleanData.map(d => d.year))).sort((a,b)=>a-b);
        const grouped = d3.group(cleanData, d => d.year);
        const stackData = years.map(y => {
            const row = { year: y };
            colleges.forEach(c => row[c] = 0);
            (grouped.get(y) || []).forEach(r => { row[r.college] = r.count; });
            return row;
        });

        const x = d3.scaleLinear().domain(d3.extent(years)).range([0, innerWidth]);
        const color = d3.scaleOrdinal().domain(colleges).range(config.colors);
        const stack = d3.stack().keys(colleges).offset(d3.stackOffsetSilhouette).order(d3.stackOrderNone);
        const series = stack(stackData);
        const y = d3.scaleLinear().domain([d3.min(series, l=>d3.min(l, d=>d[0])), d3.max(series, l=>d3.max(l, d=>d[1]))]).range([innerHeight, 0]);
        const area = d3.area().x(d => x(d.data.year)).y0(d => y(d[0])).y1(d => y(d[1])).curve(d3.curveMonotoneX);

        svg.selectAll("path").data(series).enter().append("path").attr("d", area)
            .style("fill", d => color(d.key)).style("opacity", 0.9).style("stroke", "none")
            .on("mouseover", function(event, d) {
                d3.selectAll(config.containerId + " path").style("opacity", 0.2);
                d3.select(this).style("opacity", 1).style("stroke", "rgba(255,255,255,0.3)");
                streamTooltip.style("opacity", 1);
            })
            .on("mousemove", function(event, d) {
                 const yearVal = Math.round(x.invert(d3.pointer(event)[0]));
                 const yearData = d.find(item => item.data.year === yearVal);
                 streamTooltip.html(`<div style="font-size:16px; font-weight:bold;">${d.key}</div><div style="font-size:14px; margin-top:5px;">${yearVal}年: <span style="color:#ffeb3b">${yearData?yearData.data[d.key]:0}</span> 篇</div>`)
                 .style("left", (event.pageX+15)+"px").style("top", (event.pageY-15)+"px");
            })
            .on("mouseout", function() {
                d3.selectAll(config.containerId + " path").style("opacity", 0.9).style("stroke", "none");
                streamTooltip.style("opacity", 0);
            });

        svg.append("g").attr("transform", `translate(0,${innerHeight})`).call(d3.axisBottom(x).tickFormat(d3.format("d")).ticks(8))
            .selectAll("text").attr("fill", "#fff").style("font-size", "12px");
        
        const legend = d3.select(config.legendId);
        legend.html("").style("display", "flex").style("flex-direction", "column").style("overflow-y", "auto");
        colleges.forEach(col => {
            legend.append("div").style("display","flex").style("color","#ccc").style("font-size","13px").style("margin-bottom","5px")
                .html(`<div style="width:12px;height:12px;background:${color(col)};margin-right:8px;border-radius:2px;"></div>${col}`);
        });
    }
});

// --- 模块3 地图逻辑 ---
(function initMapZoom() {
    setTimeout(() => {
        const container = document.getElementById('map-container');
        const img = document.getElementById('zoom-map');
        if (!container || !img) return;
        let state = { scale: 2, panning: false, pointX: 0, pointY: 0, startX: 0, startY: 0, cssX: 0, cssY: 0 };
        function setTransform() { img.style.transform = `translate(${state.cssX}px, ${state.cssY}px) scale(${state.scale})`; }
        setTransform();
        container.addEventListener('mousedown', function(e) { e.preventDefault(); state.panning = true; state.startX = e.clientX - state.cssX; state.startY = e.clientY - state.cssY; container.style.cursor = 'grabbing'; });
        window.addEventListener('mouseup', function() { state.panning = false; container.style.cursor = 'grab'; });
        container.addEventListener('mousemove', function(e) { if (!state.panning) return; e.preventDefault(); state.cssX = e.clientX - state.startX; state.cssY = e.clientY - state.startY; setTransform(); });
        container.addEventListener('wheel', function(e) { e.preventDefault(); const rect = container.getBoundingClientRect(); const xs = (e.clientX - rect.left - state.cssX) / state.scale; const ys = (e.clientY - rect.top - state.cssY) / state.scale; const delta = -e.deltaY; (delta > 0) ? (state.scale *= 1.1) : (state.scale /= 1.1); if(state.scale < 0.5) state.scale = 0.5; if(state.scale > 10) state.scale = 10; state.cssX = e.clientX - rect.left - xs * state.scale; state.cssY = e.clientY - rect.top - ys * state.scale; setTransform(); });
    }, 500);
})();