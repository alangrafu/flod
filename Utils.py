"""Class in charge of managing the SPARQL Endpoints."""
from SPARQLWrapper import SPARQLWrapper, JSON, XML
import sys
import json
import logging

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
        except:
            return None

        return results



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