from SPARQLWrapper import SPARQLWrapper, JSON, XML
from accept import Accept
from jinja2 import Template
from os import listdir, walk, chdir, getcwd
from os.path import isfile, join, exists
from flask import Response
from Namespace import Namespace
import sys
from jinja2 import FileSystemLoader
from jinja2.environment import Environment

env = Environment()
env.loader = FileSystemLoader('.')

class Types:
	settings = {}
	sparql = None
	a = None
	def __init__(self, settings, app=None):
		"""Initializes class"""
		self.settings = settings
		self.sparql = SPARQLWrapper(self.settings["endpoints"]["local"])
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
			types.append(t["t"]["value"])
		return types

	def operations(self):
		print "hola Types"

	def test(self, r):
		"""Test if this module should take care of that URI"""
		self.a = Accept()
		uri = r["originUri"]
		self.sparql = SPARQLWrapper(self.settings["endpoints"]["local"])
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
			if self.settings["mirrored"]== True:
				myUri = uri.replace(self.settings["ns"]["origin"], self.settings["ns"]["local"])
			extension = self.a.getExtension(r["mimetype"])
			types = self.__getResourceType(uri)
			curiedTypes = []
			for t in types:
				curiedTypes.append(self.ns.uri2curie(t))
			response = r
			response["accepted"] = True
			response["url"] = "%s.%s"%(myUri, extension)
			response["types"] = curiedTypes
			return response
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		uri = req["originUri"]
		currentDir = getcwd()
		if req["mimetype"] == "text/html":
			queryPath = "components/types/rdfs__Resource/queries/"
			templatePath = "components/types/rdfs__Resource/"
			if len(req["types"]) > 0:
				for t in req["types"]:
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
			try:				
				html = env.get_template("%s%s"%(templatePath, "html.template"))
			except Exception:
				return {"content": "Can't find html.template in %s"%templatePath, "status": 500}

			for filename in onlyfiles:
				for root, dirs, files in walk(queryPath):
					for filename in files:
						try:
							currentEndpoint = "local"
							if root.replace(queryPath, "", 1) != "":
								currentEndpoint = root.split("/").pop()
							try:
								self.sparql = SPARQLWrapper(self.settings["endpoints"][currentEndpoint])
							except:
								print "WARNING: No sparql endpoint %s found, using 'local' instead"%currentEndpoint
								self.sparql = SPARQLWrapper(self.settings["endpoints"]["local"])
							sparqlQuery = env.get_template("%s/%s"%(root, filename))
							self.sparql.setQuery(sparqlQuery.render(uri=uri))
						except Exception, ex:
							print "\n\nCANNOT OPEN FILE %s/%s"%(root, filename)
							
						self.sparql.setReturnFormat(JSON)
						results = self.sparql.query().convert()
						queries[filename.replace(".query", "")] = results["results"]["bindings"]
			chdir(currentDir)
			try:
				out = html.render(queries=queries, uri=uri)
			except Exception:
				return {"content":"Rendering problems", "status":500}
			return {"content":out}
		else:
			#Try to find .construct query first
			try:
				queryPath = "components/types/rdfs__Resource/queries/main.construct"
				if(len(req["types"]) > 0):
					for t in req["types"]:
						tDir = t.replace(":", "__")
						aux = "components/types/%s/queries/main.construct" % tDir
						if exists(aux):
							queryPath = aux
							break
				sparqlQuery = env.get_template(queryPath)
				self.sparql.setQuery(sparqlQuery.render(uri=uri))
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
			r = results.serialize(format=self.a.getConversionType(req["mimetype"]))
		return {"content": r, "mimetype": "text/turtle"}
