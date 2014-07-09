function GoogleMap(div, data, options){
    bounds  = new google.maps.LatLngBounds();
    var map = new google.maps.Map(document.getElementById(div), options);
    for(var i=0; i< data.length; i++){
        bounds.extend(data[i]);
        new google.maps.Marker({
            map:map,
            draggable:true,
            animation: google.maps.Animation.DROP,
            position: data[i]
        });
    }
    if(options.zoom == undefined){
        map.fitBounds(bounds);
    }
    map.panToBounds(bounds);
}