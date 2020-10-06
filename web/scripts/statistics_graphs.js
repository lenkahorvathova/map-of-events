function loadEventsPerCalendarAndParserGraph(data) {
    d3.selectAll("#statistics__graph__events_per_calendar_or_parser > *").remove();

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
    svg.append("g")
       .attr("class", "slices");
    svg.append("g")
       .attr("class", "labels");
    svg.append("g")
       .attr("class", "lines");

    const labelTextFontSize = 15;
    const labelTextGroup = svg.append("g")
                              .attr("class", "labelText")
                              .attr("transform", "translate(" + 0 + ", " + ((height / 2) - labelTextFontSize) + ")");

    const all_keys = [...Object.keys(GLB_EVENTS_PER_CALENDAR), ...Object.keys(GLB_EVENTS_PER_PARSER)];
    const color = d3.scaleOrdinal().domain(all_keys).range(d3.schemeDark2);

    const arc = d3.arc().innerRadius(radius * 0.4).outerRadius(radius * 0.8);
    const outerArc = d3.arc().innerRadius(radius * 0.9).outerRadius(radius * 0.9);

    const pie = d3.pie()
                  .value(function (d) {
                      return d.value;
                  })
                  .sort(function (a, b) {
                      return d3.ascending(a.key, b.key);
                  });
    const data_ready = pie(d3.entries(data));

    // function midAngle(d) {
    //     return d.startAngle + (d.endAngle - d.startAngle) / 2;
    // }

    svg.select(".slices").selectAll("path.slice")
       .data(data_ready)
       .enter()
       .append('path')
       .attr('d', arc)
       .attr('fill', function (d) {
           return (color(d.data.key));
       })
       .attr("class", "slice")
       .style("opacity", 1)
       .on("mouseover", function (d, i) {
           // // show polyline with text
           // svg.select(".lines")
           //    .append("polyline")
           //    .style("fill", "none")
           //    .attr("stroke", "black")
           //    .attr("stroke-width", 1)
           //    .attr("points", function () {
           //        const posA = arc.centroid(d);
           //        const posB = outerArc.centroid(d);
           //        const posC = outerArc.centroid(d);
           //        const midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
           //        posC[0] = radius * 0.95 * (midangle < Math.PI ? 1 : -1);
           //        return [posA, posB, posC];
           //    })
           //    .attr("class", "mouseoutHide");
           //
           // svg.select(".labels")
           //    .append("text")
           //    .attr("dy", ".35em")
           //    .text(function () {
           //        return d.data.key + " (" + d.data.value.toLocaleString() + ")";
           //    })
           //    .attr("transform", function () {
           //        const pos = outerArc.centroid(d);
           //        const midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
           //        pos[0] = radius * 0.99 * (midangle < Math.PI ? 1 : -1);
           //        return 'translate(' + pos + ')';
           //    })
           //    .style("text-anchor", function () {
           //        const midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
           //        return (midangle < Math.PI ? 'start' : 'end');
           //    })
           //    .attr("class", "mouseoutHide");

           // show text under chart
           labelTextGroup.append("text")
                         .style("text-anchor", "middle")
                         .style("font-size", labelTextFontSize)
                         .attr("class", "mouseoutHide")
                         .style("fill", function (d, i) {
                             return "black";
                         })
                         .text(function () {
                             return d.data.key + " (" + d.data.value.toLocaleString() + ")";
                         });
       })
       .on("mouseout", function (d) {
           svg.selectAll(".mouseoutHide").remove();
       });

    const totalCount = Object.values(data).reduce((a, b) => a + b, 0);
    const minToShow = totalCount * 0.03;

    svg.select(".labels").selectAll("text")
       .data(data_ready)
       .enter()
       .filter(function (d) {
           return d.data.value > minToShow;
       })
       .append("text")
       .attr("dy", ".35em")
       .text(function (d) {
           return d.data.key + " (" + d.data.value.toLocaleString() + ")";
       })
       .attr("transform", function (d) {
           const pos = outerArc.centroid(d);
           const midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
           pos[0] = radius * 0.99 * (midangle < Math.PI ? 1 : -1);
           return 'translate(' + pos + ')';
       })
       .style("text-anchor", function (d) {
           const midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
           return (midangle < Math.PI ? 'start' : 'end');
       });

    svg.select(".lines").selectAll("polyline")
       .data(data_ready)
       .enter()
       .filter(function (d) {
           return d.data.value > minToShow;
       })
       .append("polyline")
       .style("fill", "none")
       .attr("stroke", "black")
       .attr("stroke-width", 1)
       .attr("points", function (d) {
           const posA = arc.centroid(d);
           const posB = outerArc.centroid(d);
           const posC = outerArc.centroid(d);
           const midangle = d.startAngle + (d.endAngle - d.startAngle) / 2;
           posC[0] = radius * 0.95 * (midangle < Math.PI ? 1 : -1);
           return [posA, posB, posC];
       });
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