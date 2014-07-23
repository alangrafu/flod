from flask_login import session
from accept import Accept
from os import listdir, walk, chdir, getcwd
from os.path import isfile, join, exists
from flask import Response
from Utils import Namespace, SparqlEndpoint, MimetypeSelector, EnvironmentFactory
import sys
from rdflib import Graph, plugin
from rdflib.serializer import Serializer
import json



class Types:
	settings = {}
	sparql = None
	a = None
	flod = None
	mime = None
	env = None

	def __init__(self, settings, app=None):
		"""Initializes class"""
		self.settings = settings
		self.sparql = SparqlEndpoint(self.settings)
		self.ns = Namespace()
		self.flod = self.settings["flod"] if "flod" in self.settings else None
		self.mime = MimetypeSelector()
		e = EnvironmentFactory(self.settings, app)
		self.env = e.getEnvironment()

	def __getResourceType(self, uri):
		"""Returns the types of a URI"""
		types = []
		(results, thisFirst) = self.sparql.query("""
SELECT DISTINCT ?t
WHERE {
<%s> a ?t
}""" % (uri))
		for t in results["results"]["bindings"]:
			types.append(t["t"]["value"])
		return types

	def operations(self):
		print "hola Types"

	def test(self, r):
		"""Test if this module should take care of that URI"""
		self.a = Accept()
		uri = r["originUri"]
		x = uri.split(".")
		extension = x.pop()
		extensionlessUri = None
		typeQuery = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT *
WHERE {
{<%s> ?p ?o}
UNION
{?s <%s> ?o}
UNION
{?s ?p <%s>}
UNION
{GRAPH ?g {<%s> ?p ?o}}
UNION
{GRAPH ?g {?s <%s> ?o}}
UNION
{GRAPH ?g {?s ?p <%s>}}

""" % (uri, uri, uri, uri, uri, uri)
		if self.mime.getMime(extension) is not None:
			extensionlessUri = ".".join(x)
			typeQuery += """UNION{<%s> ?p2 ?o2}
UNION
{?s2 <%s> ?o2}
UNION
{?s2 ?p2 <%s>} 
UNION
{GRAPH ?g{<%s> ?p2 ?o2}}
UNION
{GRAPH ?g{?s2 <%s> ?o2}}
UNION
{GRAPH ?g{?s2 ?p2 <%s>}} """ % (extensionlessUri, extensionlessUri, extensionlessUri, extensionlessUri, extensionlessUri, extensionlessUri)
		typeQuery += """}
LIMIT 1"""
		(results, thisFirst) = self.sparql.query(typeQuery)
		if results is None:
			pass
		elif len(results["results"]["bindings"]) > 0:
			if "p2" in results["results"]["bindings"][0] or "s2" in results["results"]["bindings"]:
				myUri = uri
				uri = extensionlessUri
			else:
				extension = self.a.getExtension(r["mimetype"])
				myUri = ".".join([uri, extension])
			types = self.__getResourceType(uri)
			if self.settings["mirrored"] is True:
				myUri = myUri.replace(self.settings["ns"]["origin"], self.settings["ns"]["local"])
			curiedTypes = []
			for t in types:
				curiedTypes.append(self.ns.uri2curie(t))
			response = r
			response["accepted"] = True
			response["url"] = myUri
			response["types"] = curiedTypes
			return response
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		uri = req["originUri"]
		currentDir = getcwd()
		x = uri.split(".")
		templateName =  x.pop()
		uri = ".".join(x)
		if templateName == "html" or templateName == "json":
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
				onlyfiles = [f for f in listdir(queryPath) if isfile(join(queryPath, f))]
			except OSError, e:
				print "Can't find path %s for queries. Aborting" % templatePath
				return Response(response="Internal error\n\n", status=500)

			queries = {}
			first = {}
			try:
				html = self.env.get_template("%s%s.template" % (templatePath, templateName))
			except Exception:
				print sys.exc_info()
				if templateName != "json":
					return {"content": "Can't find %s.template in %s" % (templateName, templatePath), "status": 500}
			for root, dirs, files in walk(queryPath):
				for filename in files:
					try:
						currentEndpoint = "local"
						_aux = root.rstrip("/").split("/").pop()
						if _aux != "queries":
							currentEndpoint = _aux
						if not filename.endswith(".query"):
							continue
						sparqlQuery = self.env.get_template("%s/%s" % (root, filename))
						(results, thisFirst) = self.sparql.query(sparqlQuery.render(first=first, queries=queries, uri=uri, session=session, flod=self.flod), currentEndpoint)
						if results is not None and "results" in results:
							_name = filename.replace(".query", "")
							queries[_name] = results["results"]["bindings"]
							first[_name] = thisFirst
						else: 
							#Fail gracefully
							queries[filename.replace(".query", "")] = []
							first[_name] = {}
					except Exception, ex:
						print sys.exc_info()
						print ex
						return {"content": "A problem with SPARQL endpoint occurred", "status": 500}
			chdir(currentDir)
			try:
				if templateName == "json":
					out = json.dumps(queries)
				else:
					out = html.render(queries=queries, first=first, uri=uri, session=session, flod=self.flod)
			except Exception:
				print sys.exc_info()
				return {"content": "Rendering problems", "status": 500}
			return {"content": out}
		else:
			# Try to find .construct query first
			try:
				queryPath = "components/types/rdfs__Resource/queries/main.construct"
				if(len(req["types"]) > 0):
					for t in req["types"]:
						tDir = t.replace(":", "__")
						aux = "components/types/%s/queries/main.construct" % tDir
						if exists(aux):
							queryPath = aux
							break
				sparqlQueryT = self.env.get_template(queryPath)
				sparqlQuery = sparqlQueryT.render(uri=uri, session=session, flod=self.flod)
			# If not found, use a generic CONSTRUCT query
			except Exception, e:
				sparqlQuery = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
DESCRIBE <%s> 
LIMIT 100""" % (uri)
			results = self.sparql.query(sparqlQuery)			
		return {"content": results, "mimetype": self.mime.getMime(templateName)}
