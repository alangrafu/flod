"""Class in charge of managing the SPARQL Endpoints"""
from SPARQLWrapper import SPARQLWrapper, JSON
import sys


class Singleton(object):
    """Base singleton class"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance


class SparqlEndpoint(Singleton):
    """Class in charge of managing the SPARQL Endpoints"""
    endpoints = {}
    settings = {}

    def __init__(self, settings):
        self.settings = settings
        for k, e in self.settings["endpoints"].iteritems():
            self.endpoints[k] = SPARQLWrapper(e)

    def query(self, q, thisEndpoint="local"):
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
            except:
                print sys.exc_info()
                print "Error iterating results"
            return results
        except:
            print "SparqlEndpoint problem"
            return None