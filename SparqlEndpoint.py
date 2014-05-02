"""Class in charge of managing the SPARQL Endpoints"""
from SPARQLWrapper import SPARQLWrapper, JSON


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
            return sparql.query().convert()
        except:
            print "SparqlEndpoint problem"
            return None