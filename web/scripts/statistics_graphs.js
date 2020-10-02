function loadEventsPerCalendarAndParserGraph(data) { // TODO: Fix redrawing of the pie chart (currently adds new one)
    const margin = 40;
    const width = document.getElementById('statistics__graph__events_per_calendar_or_parser').clientWidth;
    const height = width / 2;

    const radius = Math.min(width, height) / 2 - margin;

    const svg = d3.select("#statistics__graph__events_per_calendar_or_parser")
                  .append("svg")
                  .attr("width", width)
                  .attr("height", height)
                  .append("g")
                  .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    const color = d3.scaleOrdinal()
                    .domain(Object.keys(GLB_EVENTS_PER_CALENDAR))
                    .range(d3.schemeDark2);

    const pie = d3.pie()
                  .value(function (d) {
                      return d.value;
                  })
                  .sort(function (a, b) {
                      return d3.ascending(a.key, b.key);
                  });

    const data_ready = pie(d3.entries(data));

    const u = svg.selectAll("path")
                 .data(data_ready);

    u.enter()
     .append('path')
     .merge(u)
     .transition()
     .duration(1000)
     .attr('d', d3.arc()
                  .innerRadius(0)
                  .outerRadius(radius)
     )
     .attr('fill', function (d) {
         return (color(d.data.key));
     })
     .attr("stroke", "white")
     .style("stroke-width", "2px")
     .style("opacity", 1);

    u.exit()
     .remove();
}

function loadEventsPerWeekGraph() {
    const margin = {top: 10, right: 10, bottom: 40, left: 40};
    const width = document.getElementById('statistics__graph__events_per_week').clientWidth - margin.left - margin.right;
    const height = (width / 2) - margin.top - margin.bottom;

    const svg = d3.select("#statistics__graph__events_per_week")
                  .append("svg")
                  .attr("width", width + margin.left + margin.right)
                  .attr("height", height + margin.top + margin.bottom)
                  .append("g")
                  .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    const x = d3.scaleBand()
                .range([width, 0])
                .domain(GLB_EVENTS_PER_WEEK.map(function (d) {
                    return d.week;
                }))
                .padding(0.2);
    svg.append("g")
       .attr("transform", "translate(0," + height + ")")
       .call(d3.axisBottom(x))
       .selectAll("text")
       .attr("transform", "translate(-10,0)rotate(-45)")
       .style("text-anchor", "end");

    const y = d3.scaleLinear()
                .domain([0, d3.max(GLB_EVENTS_PER_WEEK, function (d) {
                    return d.count;
                })])
                .range([height, 0]);
    svg.append("g")
       .call(d3.axisLeft(y));

    svg.selectAll("mybar")
       .data(GLB_EVENTS_PER_WEEK)
       .enter()
       .append("rect")
       .attr("x", function (d) {
           return x(d.week);
       })
       .attr("y", function (d) {
           return y(d.count);
       })
       .attr("width", x.bandwidth())
       .attr("height", function (d) {
           return height - y(d.count);
       })
       .attr("fill", "#69b3a2");
}