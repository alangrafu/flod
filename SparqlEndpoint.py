from SPARQLWrapper import SPARQLWrapper, JSON


class Singleton(object):
  _instance = None
  def __new__(class_, *args, **kwargs):
    if not isinstance(class_._instance, class_):
        class_._instance = object.__new__(class_, *args, **kwargs)
    return class_._instance

class SparqlEndpoint(Singleton):
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
		return sparql.query().convert()
