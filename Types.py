from SPARQLWrapper import SPARQLWrapper, JSON, XML
from accept import Accept
from jinja2 import Template
from os import listdir
from os.path import isfile, join, exists
from flask import Response
from Namespace import Namespace

class Types:
	config = {}
	sparql = None
	a = None
	def __init__(self, config):
		"""Initializes class"""
		self.config = config
		self.sparql = SPARQLWrapper(self.config['endpoints']['local'])
		self.ns = Namespace()

	def __getResourceType(self, uri):
		"""Returns the types of a URI"""
		types = []
		self.sparql.setQuery("""
    SELECT DISTINCT ?t
    WHERE {
    	<%s> a ?t
    }""" % (uri))
		self.sparql.setReturnFormat(JSON)
		results = self.sparql.query().convert()
		for t in results["results"]["bindings"]:
			types.append(t['t']['value'])
		return types

	def operations(self):
		print "hola Types"

	def test(self, r):
		"""Test if this module should take care of that URI"""
		self.a = Accept()
		print r
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
			types = self.__getResourceType(uri)
			curiedTypes = []
			for t in types:
				curiedTypes.append(self.ns.uri2curie(t))
			response = r
			response['accepted'] = True
			response['url'] = "%s.%s"%(myUri, extension)
			response["types"] = curiedTypes
			return response
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		uri = req['originUri']
		if req['mimetype'] == 'text/html':
			queryPath = "components/types/rdfs__Resource/queries/"
			templatePath = "components/types/rdfs__Resource/" 
			if len(req['types']) > 0:
				for t in req['types']:
					tDir = t.replace(":", "__")
					_queryPath = "components/types/%s/queries/" % tDir
					_templatePath = "components/types/%s/" % tDir
					if exists(_queryPath) and exists(_templatePath):
						queryPath = "components/types/%s/queries/" % tDir
						templatePath = "components/types/%s/" % tDir
						break
			try:
				onlyfiles = [ f for f in listdir(queryPath) if isfile(join(queryPath,f)) ]
			except OSError, e:
				print "Can't find path %s for queries. Aborting" % templatePath
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
				queryPath = "components/types/rdfs__Resource/queries/main.construct"
				if(len(req['types']) > 0):
					for t in req['types']:
						tDir = t.replace(":", "__")
						aux = "components/types/%s/queries/main.construct" % tDir
						if exists(aux):
							queryPath = aux
							break
				f = open(queryPath)
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
