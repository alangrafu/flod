"""Util classes."""

from Utils import SparqlEndpoint, Namespace, MimetypeSelector, EnvironmentFactory
from jinja2 import Template
from os import listdir, chdir, getcwd, walk
from os.path import isfile, join, exists
from flask import Response
import sys
from flask_login import session
import json


class Services:
	settings = {}
	basedir = "components/services/"
	sparql = None
	flod = None
	env = None

	def __init__(self, settings, app=None):
		"""Initializes class"""
		self.settings = settings
		self.sparql = SparqlEndpoint(self.settings)
		self.ns = Namespace()
		self.mime = MimetypeSelector()
		self.flod = self.settings["flod"] if "flod" in self.settings else None
		e = EnvironmentFactory(self.settings, app)
		self.env = e.getEnvironment()

	def __getResourceType(self, uri):
		"""Returns the types of a URI"""
		types = []
		(results, first) = self.sparql.query("""
SELECT DISTINCT ?t
WHERE {
<%s> a ?t
}""" % (uri))
		for t in results["results"]["bindings"]:
			types.append(t["t"]["value"])
		return types

	def operations(self):
		print "hola Services"

	def test(self, r):
		myPath = r["localUri"].replace(self.settings["ns"]["local"], "", 1).split("/")
		file = myPath.pop(0)
		if exists(self.basedir + file):
			return {"accepted": True, "url": r["localUri"]}
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		myPath = req["url"].replace(self.settings["ns"]["local"], "", 1).split("/")
		file = myPath.pop(0)
		currentDir = getcwd()
		service = self.basedir + file
		uri = req["url"]
		queryPath = "%s/queries/" % service
		templatePath = "%s/" % service
		templateName =  self.mime.getExtension(req["request"].accept_mimetypes.best)
		try:
			onlyfiles = [f for f in listdir(queryPath) if isfile(join(queryPath, f))]
		except OSError:
			print "Warning: Can't find path %s for queries." % templatePath
			onlyfiles = []
		queries = {}
		first={}
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
					(results, thisFirst) = self.sparql.query(sparqlQuery.render(queries=queries, first=first, uri=uri, session=session, flod=self.flod, args=myPath), currentEndpoint)
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
			if templateName == "json" and not isfile( "%s%s.template" % (templatePath, templateName)):
				out = json.dumps(queries)
			else:
				content = self.env.get_template("%s%s.template" % (templatePath, templateName))
				out = content.render(queries=queries, first=first, uri=uri, session=session, flod=self.flod, args=myPath)
		except Exception:
			print sys.exc_info()
			return {"content": "Rendering problems", "status": 500}
		except Exception:
			return {"content": "Can't find %s.template in %s" % (templateName, templatePath), "status": 500}
			exit(3)
		return {"content": out, "mimetype": "text/html"}
