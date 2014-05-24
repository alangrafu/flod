from flask_login import session
from accept import Accept
from jinja2 import Template
from os import listdir, walk, chdir, getcwd
from os.path import isfile, join, exists
from flask import Response
from Utils import Namespace, SparqlEndpoint, MimetypeSelector
import sys
from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from rdflib import Graph, plugin
from rdflib.serializer import Serializer
import json

env = Environment()
env.loader = FileSystemLoader('.')


class Types:
	settings = {}
	sparql = None
	a = None
	flod = None
	mime = None

	def __init__(self, settings, app=None):
		"""Initializes class"""
		self.settings = settings
		self.sparql = SparqlEndpoint(self.settings)
		self.ns = Namespace()
		self.flod = self.settings["flod"] if "flod" in self.settings else None
		self.mime = MimetypeSelector()

	def __getResourceType(self, uri):
		"""Returns the types of a URI"""
		types = []
		results = self.sparql.query("""
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
		typeQuery = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT *
WHERE {
{<%s> ?p ?o}
UNION
{?s <%s> ?o}
UNION
{?s ?p <%s>}
""" % (uri, uri, uri)
		if self.mime.getMime(extension) is not None:
			extensionlessUri = ".".join(x)
			typeQuery += """UNION{<%s> ?p2 ?o2}
UNION
{?s2 <%s> ?o2}
UNION
{?s2 ?p2 <%s>} """ % (extensionlessUri, extensionlessUri, extensionlessUri)
		typeQuery += """}
LIMIT 1"""
		results = self.sparql.query(typeQuery)
		if results is None:
			pass
		elif len(results["results"]["bindings"]) > 0:
			myUri = uri
			if self.settings["mirrored"] is True:
				myUri = uri.replace(self.settings["ns"]["origin"], self.settings["ns"]["local"])
			extension = self.a.getExtension(r["mimetype"])
			types = self.__getResourceType(uri)
			curiedTypes = []
			for t in types:
				curiedTypes.append(self.ns.uri2curie(t))
			response = r
			response["accepted"] = True
			if "p2" in results["results"]["bindings"][0] or "s2" in results["results"]["bindings"]:
				print "Found", myUri
				response["url"] = myUri
			else:
				print "Found", myUri, extension
				response["url"] = "%s.%s" % (myUri, extension)
			print results
			response["types"] = curiedTypes
			return response
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		uri = req["originUri"]
		print uri,", ---------------------"
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
			try:
				html = env.get_template("%s%s.template" % (templatePath, templateName))
			except Exception:
				print sys.exc_info()
				if templateName != "json":
					return {"content": "Can't find %s.template in %s" % (templateName, templatePath), "status": 500}

			for filename in onlyfiles:
				for root, dirs, files in walk(queryPath):
					for filename in files:
						try:
							currentEndpoint = "local"
							_aux = root.rstrip("/").split("/").pop()
							if _aux != "queries":
								currentEndpoint = _aux
							if not filename.endswith(".query"):
								continue
							sparqlQuery = env.get_template("%s/%s" % (root, filename))
							results = self.sparql.query(sparqlQuery.render(queries=queries, uri=uri, session=session, flod=self.flod, args=myPath), currentEndpoint)
							if results is not None and "results" in results:
								queries[filename.replace(".query", "")] = results["results"]["bindings"]
							else: 
								#Fail gracefully
								queries[filename.replace(".query", "")] = []
						except Exception, ex:
							print sys.exc_info()
							print ex
							return {"content": "A problem with SPARQL endpoint occurred", "status": 500}
			chdir(currentDir)
			try:
				if templateName == "json":
					out = json.dumps(queries)
				else:
					out = html.render(queries=queries, uri=uri, session=session, flod=self.flod)
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
				sparqlQueryT = env.get_template(queryPath)
				sparqlQuery = sparqlQueryT.render(uri=uri, session=session, flod=self.flod)
			# If not found, use a generic CONSTRUCT query
			except Exception, e:
				sparqlQuery = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
DESCRIBE {<%s> }
LIMIT 100""" % (uri)
			results = self.sparql.query(sparqlQuery)			
		return {"content": results, "mimetype": self.mime.getMime(templateName)}
