"""Class in charge of managing the SPARQL Endpoints."""
from SPARQLWrapper import SPARQLWrapper, JSON
import sys
import json


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
        sparql = self.endpoints[thisEndpoint]
        sparql.setQuery(q)
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.query().convert()
            try:
                if self.settings["mirrored"] is True:
                    for row in results["results"]["bindings"]:
                        for elem in row:
                            if row[elem]["type"] == "uri":
                                row[elem]["value"] = row[elem]["value"].replace(self.settings['ns']['origin'], self.settings['ns']['local'], 1)
                                row[elem]["curie"] = ns.uri2curie(row[elem]["value"])
            except:
                print sys.exc_info()
                print "Error iterating results"
            return results
        except:
            print sys.exc_info()
            print "SparqlEndpoint problem"
            return None


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
            with open("settings.json", "rb") as s_file:
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