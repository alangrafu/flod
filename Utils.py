"""Class in charge of managing the SPARQL Endpoints."""
from SPARQLWrapper import SPARQLWrapper, JSON, XML
import sys
import json
import logging
from jinja2 import Environment, PackageLoader, FileSystemLoader
import uuid

logging.basicConfig()
class Singleton(object):

    """Base singleton class."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Instantiation."""
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance


class SparqlEndpoint(Singleton):

    """Class in charge of managing the SPARQL Endpoints."""

    endpoints = {}
    settings = {}

    def __init__(self, settings):
        """Initialize."""
        self.settings = settings
        for k, e in self.settings["endpoints"].iteritems():
            self.endpoints[k] = SPARQLWrapper(e)

    def query(self, q, thisEndpoint="local"):
        """Query an endpoint."""
        ns = Namespace()
        if thisEndpoint not in self.endpoints:
            #Fail gracefully
            print "Endpoint '%s' not found, will use 'local' instead" % thisEndpoint
            thisEndpoint = "local"
        sparql = self.endpoints[thisEndpoint]
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        isFirst = True
        first = {}
        try:
            results = sparql.query().convert()
            if self.settings["mirrored"] is True:
                for row in results["results"]["bindings"]:                    
                    for elem in results["head"]["vars"]:
                        if elem not in row:
                            row[elem] = {}
                        if "type" not in row[elem]:
                            row[elem]["type"] = None
                            row[elem]["value"] = None
                            row[elem]["curie"] = None
                        if row[elem]["type"] == "uri":
                            row[elem]["value"] = row[elem]["value"].replace(self.settings['ns']['origin'], self.settings['ns']['local'], 1)
                            row[elem]["curie"] = ns.uri2curie(row[elem]["value"])
                    if isFirst:
                        first = row
                        isFirst = False
        except:
            return (None, None)

        return (results, first)



class Namespace(Singleton):

    """Namespace management."""

    ns = {}

    def __init__(self):
        """Initialize."""
        try:
            with open("namespaces.json", "rb") as ns_file:
                aux = json.load(ns_file)
            self.ns = aux['ns']
        except:
            print sys.exc_info()
            print "Can't load namespace.json. Aborting"
            exit(1)
        try:
            with open("components/settings.json", "rb") as s_file:
                aux = json.load(s_file)
                for k, v in aux['ns'].iteritems():
                    self.ns[k] = v
        except:
            print sys.exc_info()
            print "Can't load settings.json. Aborting"
            exit(1)

    def uri2curie(self, uri):
        """Convert a URI to a CURIe."""
        for n in self.ns:
            u = self.ns[n]
            if uri.find(u) == 0:
                rest = uri.replace(u, "", 1)
                return "%s:%s" % (n, rest.replace("/", "_").replace("#", "_"))
        return uri




class MimetypeSelector(Singleton):
    mime2extension = {}

    def __init__(self):
        self.mime2extension["text/html"] = "html"
        self.mime2extension["application/json"] = "json"
        self.mime2extension["application/xhtml+xml"] = "html"
        # For later
        # self.mime2extension["text/turtle"] = "ttl"
        # self.mime2extension["application/rdf+xml"] = "rdf"
        # self.mime2extension["application/javascript"] = "js"
        # self.mime2extension["application/xhtml+xml"] = "html"
        # self.mime2extension["application/xml"] = "html"

    def getExtension(self, mime):
        return self.mime2extension[mime] if mime in self.mime2extension else "html"

    def getMime(self, extension):
        for key in self.mime2extension.keys():
            if self.mime2extension[key] == extension:
                return key
        return None

class EnvironmentFactory(Singleton):
    environment = None
    def __init__(self, settings, app):
        self.environment = Environment()
        self.environment.loader = FileSystemLoader('.')
        self.environment.filters['GoogleMaps'] = self._GoogleMaps
        self.environment.filters['BarChart'] = self._BarChart
    def getEnvironment(self):
        return self.environment
    def _GoogleMaps(self, data, lat=None,lon=None,zoom=None, width=None, height=None):
        _vizId = str(uuid.uuid4().hex)
        _dataId = "data_%s"%_vizId
        _centerX = 0
        _centerY = 0
        _zoom = "undefined" if zoom is None else int(zoom)
        _width = 400 if width is None else int(width)
        _height = 300 if height is None else int(height)
        _jData = """ %s = [];
"""%_dataId
        if lon is None or lat is None:
            return ""
        for row in data:
            _jData += """ %s.push(new google.maps.LatLng(%s, %s));
""" % (_dataId, row[lat]["value"], row[lon]["value"])
            _centerX += float(row[lat]["value"])
            _centerY += float(row[lon]["value"])
        return """
<div id="map_%s" style="height:%dpx;width:%dpx;"></div>
<script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false"></script>
<script type="text/javascript" src="/js/filters/googlemaps.js"></script>
<script type="text/javascript">
(function(){
%s
var mapOptions = {
    center: new google.maps.LatLng(%f, %f),
    zoom: %s,
    mapTypeId: google.maps.MapTypeId.ROADMAP
};
GoogleMap("map_%s", %s, mapOptions);
})();
</script>
""" % (_vizId, _height, _width, _jData, (_centerX/len(data)), (_centerY/len(data)), _zoom, _vizId, _dataId)

    def _BarChart(self, data, x=None, y=None, width=None, height=None, lowerBound=None, leftBound=None, rightBound=None, upperBound=None, yLog=None):
        _vizId = str(uuid.uuid4().hex)
        _dataId = "data_%s"%_vizId
        _width = 400 if width is None else int(width)
        _height = 300 if height is None else int(height)
        _jData = """ %s = [];
"""%_dataId
        if x is None or y is None:
            return ""
        for row in data:
            _jData += """ %s.push({%s: "%s", %s: %s});
""" % (_dataId, x, row[x]["value"],  y, row[y]["value"])
        myOptions = {}
        myOptions["width"] = _width
        myOptions["height"] = _height
        myOptions["x"] = x
        myOptions["y"] = y
        if lowerBound is not None:
            myOptions["lowerBound"] = lowerBound
        if upperBound is not None:
            myOptions["upperBound"] = upperBound
        if leftBound is not None:
            myOptions["leftBound"] = leftBound
        if rightBound is not None:
            myOptions["rightBound"] = rightBound
        options = """options_%s = %s""" % (_vizId, json.dumps(myOptions))
        return """<script src="/js/d3.v3.min.js"></script>
<script src="/js/dimple.v2.0.0.min.js"></script>
<script src="/js/filters/barchart.js"></script>
<div id="barchart_%s" style="height:%dpx;width:%dpx;"></div>
<script type="text/javascript">
(function(){
    %s
    %s
    drawColumnChart("barchart_%s", %s, options_%s);
})();
</script>""" % (_vizId, _height, _width, options, _jData, _vizId, _dataId, _vizId)
