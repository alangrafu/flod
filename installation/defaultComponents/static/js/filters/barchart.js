function drawBarChart(div, data, newoptions){
	options = {
		width: 500,
		height: 500,
		leftBound: 0.1,
		rightBound: 0.8,
		upperBound: 0.1,
		lowerBound: 0.7,
		logY: false
	};

	for(var i in newoptions){
		options[i] = newoptions[i];
	}
    var svg = dimple.newSvg("#"+div, options.width, options.height);
    var myChart = new dimple.chart(svg, data);
    myChart.setBounds(options.leftBound*options.width, options.upperBound*options.height, options.rightBound*options.width, options.lowerBound*options.height)
    if(options.logY){
    	myChart.addLogAxis("x", options.y);	
    }else{
    	myChart.addMeasureAxis("x", options.y);
    }
    myChart.addCategoryAxis("y", options.x);
    myChart.addSeries(null, dimple.plot.bar);
    myChart.draw();
}
