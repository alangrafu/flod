from SPARQLWrapper import SPARQLWrapper, JSON, XML
from accept import Accept
from jinja2 import Template
from os import listdir
from os.path import isfile, join
from flask import Response


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
		if req['mimetype'] == 'text/html':
			queryPath = "components/types/rdfs__Resource/queries/"
			templatePath = "components/types/rdfs__Resource/"
			try:
				onlyfiles = [ f for f in listdir(queryPath) if isfile(join(queryPath,f)) ]
			except OSError, e:
				print "Can't find path for queries. Aborting"
				return Response(response="Internal error\n\n", status=500)

			queries = {}
			for filename in onlyfiles:
				try:
					f = open("%s%s"%(queryPath, filename))
					sparqlQuery = Template("\n".join(f.readlines()))
					self.sparql.setQuery(sparqlQuery.render(uri=uri))
					f.close()
				except Exception, e:
					print e
					print "CANNOT OPEN FILE %s"%filename
					exit(2)
				self.sparql.setReturnFormat(JSON)
				results = self.sparql.query().convert()
				queries[filename.replace(".query", "")] = results["results"]["bindings"]
				try:
					f = open("%s%s"%(templatePath, "html.template"))
					html = Template("\n".join(f.readlines()))
					f.close()
				except Exception, e:
					return "Can't find html.template in %s"%templatePath
					exit(3)
				try:
					out = html.render(queries=queries, uri=uri)
				except Exception:
					return "Rendering problems"
				return out
		else:
			#Try to find .construct query first
			try:
				f = open("components/rdfs__Resource/queries/main.construct")
				sparqlQuery = Template("\n".join(f.readlines()))
				self.sparql.setQuery(sparqlQuery.render(uri=uri))
				f.close()
			#If not found, use a generic CONSTRUCT query
			except Exception, e:
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
