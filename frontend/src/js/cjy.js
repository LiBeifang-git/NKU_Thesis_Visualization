
  
  async function loadStats() {
    const res = await fetch('http://localhost:3020/api/cjy/midup');
    const data = await res.json();

    // 总论文数
    document.querySelector(".overview h1 span").textContent = data.total_papers;

    // 关键指标
    const metrics = document.querySelectorAll(".metric-circle");
    metrics[0].textContent = data.total_teachers;
    metrics[1].textContent = data.total_students;
    metrics[2].textContent = data.total_colleges;
}


async function loadRank() {
  try {
    const res = await fetch('http://localhost:3020/api/cjy/rightup');
    const result = await res.json();

    if (result.code !== 200) {
      console.error("API Error:", result.message);
      return;
    }

    const list = result.data;
    const ul = document.querySelector('.rank-list');

    if (!ul) {
      console.error("找不到 .rank-list 元素");
      return;
    }

    ul.innerHTML = ""; // 清空旧内容

    list.forEach(item => {
      ul.innerHTML += `
        <li class="rank-item">
          <div class="rank-num-wrap">
            <span class="rank-num ${item.rank <= 8 ? 'rank-' + item.rank : ''}">
              ${item.rank}
            </span>
          </div>

          <div class="rank-main">
            <div class="rank-title" title="${item.title}">
              ${item.title}
            </div>

            <div class="rank-row">
              <div class="rank-bar">
                <div class="rank-bar-fill" style="width:${item.percent}%"></div>
              </div>
              <div class="rank-value">${item.views}</div>
            </div>
          </div>
        </li>
      `;
    });
  } catch (err) {
    console.error("加载排行榜失败:", err);
  }
}

async function loadGraduatePieCharts() {
  const res = await fetch("http://localhost:3020/api/cjy/rightdown");
  const json = await res.json();
  drawGraduatePieCharts(json.data);   // 注意要用 json.data
}

function drawGraduatePieCharts(data) {
  const container = d3.select("#grad-chart");
  container.selectAll("*").remove();
  const rect = container.node().getBoundingClientRect();
  const width = rect.width*1;
  const height = rect.height;
  

  const perWidth = width / 3;
  const radius = Math.min(perWidth, height) * 0.2;

  const color = d3.scaleOrdinal()
    .domain(["硕士", "博士"])
    .range(["#3E6B6D", "#2A445E"]);

  const svg = container.append("svg")
    .attr("width", width)
    .attr("height", height);

  let index = 0;

  Object.entries(data).forEach(([year, v]) => {
    const group = svg.append("g")
      .attr("transform", `translate(${perWidth * (index + 0.5)}, ${height / 2-10})`);
    const total = d3.sum(Object.values(v));   // 计算总人数
    const pie = d3.pie().value(d => d[1]);
    const arc = d3.arc().innerRadius(0).outerRadius(radius);

    group.selectAll("path")
      .data(pie(Object.entries(v)))
      .enter()
      .append("path")
      .attr("d", arc)
      .attr("fill", d => color(d.data[0]))
      .attr("opacity", 0.85)
      .style("transition", "0.3s ease")
      .on("mouseover", function () {
        d3.select(this).attr("opacity", 1).attr("transform", "scale(1.05)");
      })
      .on("mouseout", function () {
        d3.select(this).attr("opacity", 0.85).attr("transform", "scale(1)");
      });

     // 追加百分比标签
    group.selectAll(".pie-label")
     .data(pie(Object.entries(v)))
     .enter()
     .append("text")
     .attr("class", "pie-label")
     .attr("transform", d => `translate(${arc.centroid(d)})`)
     .attr("text-anchor", "middle")
     .attr("fill", "#fff")
     .attr("font-size", "12px")
     .text(d => {
       const percent = (d.data[1] / total * 100).toFixed(1);
       return `${percent}%`;
     });

    // 标题（年份）
    group.append("text")
      .attr("text-anchor", "middle")
      .attr("y", -radius - 10)
      .attr("fill", "#fff")
      .attr("font-size", "14px")
      .text(year);

    // legend
    const legend = group.selectAll(".legend")
      .data(Object.entries(v))
      .enter()
      .append("g")
      .attr("transform", (_, i) => `translate(-40, ${i * 20 + radius + 10})`);

    legend.append("rect")
      .attr("width", 14)
      .attr("height", 14)
      .attr("fill", d => color(d[0]));

    legend.append("text")
      .attr("x", 20)
      .attr("y", 14)
      .attr("fill", "#fff")
      .attr("font-size", "12px")
      .text(d => `${d[0]}：${d[1]}人`);

    index++;
  });
}



async function loadTopchart() {
  const res = await fetch("http://localhost:3020/api/cjy/leftdown");
  const json = await res.json();
  renderTopTable(json.data);   // 注意要用 json.data
  
}

function renderTopTable(data) {
  const container = document.getElementById("table-wrapper");
  container.innerHTML = ""; // 清空旧内容

  // 创建表格
  const table = document.createElement("table");
  table.className = "top-table";

  // 表头
  table.innerHTML = `
    <thead >
      <tr>
        <th>指标</th>
        <th>Top</th>
        <th>说明</th>
      </tr>
    </thead>
  `;

  const tbody = document.createElement("tbody");

  // 逐项写入
  tbody.innerHTML = `
    <tr>
      <td>毕业学生人数最多的学位年度</td>
      <td>${data.top_year.year}年</td>
      <td>共 ${data.top_year.count} 人</td>
    </tr>

    <tr>
      <td>博士比例最高的学院</td>
      <td>${data.top_phd_college.college}</td>
      <td>博士 ${data.top_phd_college.phd_count} / 总数 ${data.top_phd_college.total_count} （比例 ${(data.top_phd_college.phd_ratio*100).toFixed(1)}%）</td>
    </tr>

    <tr>
      <td>带学生最多的导师</td>
      <td>${data.top_teacher.teacher}</td>
      <td>${data.top_teacher.college}，共带 ${data.top_teacher.student_count} 名学生</td>
    </tr>

    <tr>
      <td>论文数量最多的学院</td>
      <td>${data.top_college.college}</td>
      <td>共 ${data.top_college.paper_count} 篇论文</td>
    </tr>

    <tr>
      <td>参考文献峰值</td>
      <td>${data.top_reference.max_refs} 篇</td>
      <td>${data.top_reference.students.length} 名学生达到该数值</td>
    </tr>

     <tr>
      <td>博士毕业生最多的学院</td>
      <td>${data.top_doctor_college.college}</td>
      <td>共有${data.top_doctor_college.doctor_total}名博士毕业生</td>
    </tr>

   

  `;

  table.appendChild(tbody);
  container.appendChild(table);
}



window.loadLineChart = async function() {
  // 请求后端接口获取数据
  const res = await fetch("http://localhost:3020/api/cjy/middown");
  const data = await res.json();

  // 数据类型转换
  data.forEach(d => {
    d.year = +d.year;
    d.avg_refs = +d.avg_refs;
  });

  const container = d3.select("#line-chart");
  container.selectAll("*").remove(); // 清空容器

  // 获取容器尺寸
  const rect = container.node().getBoundingClientRect();
  const width = rect.width;   // 默认宽度
  const height = rect.height; // 默认高度

  const margin = {top: 15, right: 150, bottom: 50, left: 50};
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const svg = container.append("svg")
    .attr("width", "100%")
    .attr("height", "100%")
    .attr("viewBox", `0 0 ${width} ${height}`);

  const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // 获取学院和年份
  const colleges = Array.from(new Set(data.map(d => d.college)));
  const years = Array.from(new Set(data.map(d => d.year))).sort((a,b)=>a-b);

  const morandiContrastColors = [
    "#5bb5bd", // 1
    "#FEB536", // 2
    "#9F2E2E", // 3
    "#14507D", // 4
    "#5a8446", // 5
    "#CF9197", // 6
    "#8B5F48", // 7
    "#7A6E79", // 8
    "#4B3F2F", // 深棕
    "#3E5C6E", // 深蓝灰
    "#506050"  // 墨绿色灰
  ];
  
  const color = d3.scaleOrdinal()
    .domain(colleges)
    .range(morandiContrastColors);
  
  

  // 坐标轴比例尺
  const x = d3.scaleLinear().domain(d3.extent(years)).range([0, innerWidth]);
  const y = d3.scaleLinear().domain([0, d3.max(data, d => d.avg_refs)]).nice().range([innerHeight, 0]);

  const xAxis = d3.axisBottom(x).tickFormat(d3.format("d")).ticks(years.length);
  const yAxis = d3.axisLeft(y);

// 生成每两年的刻度
const tickYears = years.filter((d, i) => i % 2 === 0);

// 绘制 x 轴，每两年一个刻度
g.append("g")
  .attr("transform", `translate(0,${innerHeight})`)
  .call(d3.axisBottom(x).tickValues(tickYears).tickFormat(d3.format("d")))
  .append("text")
  .attr("x", innerWidth / 2)
  .attr("y", 35)
  .attr("fill", "#000")
  .attr("class", "axis-label")
  .style("font-size", "12px")
  .text("学位年度");


  // 绘制 y 轴
  g.append("g")
    .call(yAxis)
    .append("text")
    .attr("transform", "rotate(-90)")
    .attr("x", -innerHeight / 2+40)
    .attr("y", -35)
    .attr("fill", "#000")
    .attr("class", "axis-label")
    .style("font-size", "12px")
    .text("平均参考文献数");

  // 按学院分组
  const dataNest = colleges.map(college => ({
    college,
    values: data.filter(d => d.college === college).sort((a,b)=>a.year-b.year)
  }));

  const line = d3.line()
    .x(d => x(d.year))
    .y(d => y(d.avg_refs))
    .curve(d3.curveMonotoneX); 

  // 绘制折线
  g.selectAll(".line")
    .data(dataNest)
    .enter()
    .append("path")
    .attr("class", "line")
    .attr("d", d => line(d.values))
    .style("stroke", d => color(d.college))
    .style("fill", "none")
    .style("stroke-width", 2);

  // tooltip
  const tooltip = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("height","11%")
    .style("width","8%")
    .style("position", "absolute")
    .style("padding", "6px")
    .style("background", "rgba(0,0,0,0.7)")
    .style("color", "#fff")
    .style("border-radius", "4px")
    .style("pointer-events", "none")
    .style("opacity", 0);

  // 添加点
  dataNest.forEach(d => {
    g.selectAll(`.dot-${d.college}`)
      .data(d.values)
      .enter()
      .append("circle")
      .attr("class", `dot-${d.college}`)
      .attr("cx", d => x(d.year))
      .attr("cy", d => y(d.avg_refs))
      .attr("r", 3)
      .style("fill", color(d.college))
      .on("mouseover", function(event, d) {
        // 动画放大
        d3.select(this)
        .transition()
        .duration(200)
        .attr("r",5 );
        tooltip.style("opacity", 1)
          .html(`
            <strong>${d.college} (${d.year})</strong><br/>
            平均参考文献数: ${d.avg_refs.toFixed(1)}<br/>
            最大参考文献数: ${d.max_refs}<br/>
            最小参考文献数: ${d.min_refs}<br/>
            论文数量: ${d.thesis_count}
          `)
          .style("left", (event.pageX + 10) + "px")
          .style("font-size",0.7+"rem")
          .style("top", (event.pageY - 28) + "px");
      })
      .on("mousemove", function(event) {
        tooltip.style("left", (event.pageX + 10) + "px")
               .style("top", (event.pageY - 28) + "px");
      })
      .on("mouseout", function() {
      // 恢复原来大小
      d3.select(this)
      .transition()
      .duration(200)
      .attr("r", 4);
      
        tooltip.style("opacity", 0);

      });
  }
  );

  // 添加图例
  const legend = svg.append("g")
    .attr("transform", `translate(${width - margin.right + 20}, ${margin.top})`);

  dataNest.forEach((d, i) => {
    legend.append("rect")
      .attr("x", 0)
      .attr("y", i * 20)
      .attr("width", 12)
      .attr("height", 12)
      .style("fill", color(d.college));

    legend.append("text")
      .attr("x", 18)
      .attr("y", i * 20 + 10)
      .text(d.college)
      .style("font-size", "12px");
  });
  window.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadRank();
  loadGraduatePieCharts();
  loadTopchart();
  window.loadLineChart(); 
  loadOSMMap();
});
}

function loadOSMMap() {
  console.log("[map] start loadOSMMap");

  const container = d3.select("#map-chart");
  const rect = container.node().getBoundingClientRect();
  const width = rect.width;
  const height = rect.height;

  console.log("[map] container size:", width, "x", height);

  const svg = container.append("svg")
      .attr("width", width)
      .attr("height", height);

  const g = svg.append("g");
  const projection = d3.geoMercator()
  const path = d3.geoPath().projection(projection)

  

  


}


window.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadRank();
  loadGraduatePieCharts();
  loadTopchart();
  loadLineChart(); 
  loadOSMMap();
});






