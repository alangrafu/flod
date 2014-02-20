from SPARQLWrapper import SPARQLWrapper, JSON, XML
from accept import Accept
from jinja2 import Template

class Types:
	config = {}
	sparql = None
	a = None
	def __init__(self, config):
		self.config = config
		self.sparql = SPARQLWrapper(self.config['endpoints']['local'])

	def operations(self):
		print "hola Types"

	def test(self, r):
		self.a = Accept()
		uri = r['originUri']
		self.sparql.setQuery("""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?p ?o
    WHERE {
    {<%s> ?p ?o}
    UNION
    {?s <%s> ?o}
    UNION
    {?s ?p <%s>}
    }
LIMIT 1""" % (uri, uri, uri))
		self.sparql.setReturnFormat(JSON)
		results = self.sparql.query().convert()
		if len(results["results"]["bindings"]) > 0:
			myUri = uri
			if self.config['mirrored']== True:
				myUri = uri.replace(self.config['ns']['origin'], self.config['ns']['local'])
			extension = self.a.getExtension(r['mimetype'])
			return {"accepted": True, "url": "%s.%s"%(myUri, extension)}
		return {"accepted": False}

	def execute(self, req):
		uri = req['originUri']
		print req['mimetype']
		if req['mimetype'] == 'text/html':
			try:
				f = open("components/rdfs__Resource/queries/main.query")
				sparqlQuery = Template("\n".join(f.readlines()))
				self.sparql.setQuery(sparqlQuery.render(uri=uri))
				f.close()
			except Exception, e:
				print e
			self.sparql.setReturnFormat(JSON)
			results = self.sparql.query().convert()

			r = """%s"""%uri
			for result in results["results"]["bindings"]:
				r += """%s\t%s\n\n""" %(result["p"]["value"], result["o"]["value"])
		else:
			self.sparql.setQuery("""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    CONSTRUCT {<%s>  ?p ?o}
    WHERE { <%s> ?p ?o }
LIMIT 100""" % (uri, uri))
		#self.sparql.setQuery(query)
			self.sparql.setReturnFormat(XML)
		#self.sparql.setReturnFormat(JSON)
			results = self.sparql.query().convert()
			r = results.serialize(format=self.a.getConversionType(req['mimetype']))
		return r
