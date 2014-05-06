from flask_login import session
from accept import Accept
from jinja2 import Template
from os import listdir, walk, chdir, getcwd
from os.path import isfile, join, exists
from flask import Response
from Utils import Namespace, SparqlEndpoint
import sys
from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from rdflib import ConjunctiveGraph, URIRef
env = Environment()
env.loader = FileSystemLoader('.')


class JsonBasedWriter:
	settings = {}
	sparql = None
	flod = None
	basedir = "components/jsonupdates/"
	g = None

	def __init__(self, settings, app=None):
		"""Initializes class"""

		self.settings = settings
		if "sparqlUpdateEndpoint" not in self.settings or "local" not in self.settings["sparqlUpdateEndpoint"]:
			print "Sparql Update endpoint not defined. Aborting."
			exit(10)
		self.sparql = SparqlEndpoint(self.settings)
		self.flod = self.settings["flod"] if "flod" in self.settings else None
		self.graph = ConjunctiveGraph('SPARQLUpdateStore')
		self.graph.open((self.settings["endpoints"]["local"], self.settings["sparqlUpdateEndpoint"]["local"]))

	def _update(self, q):
		graphuri = URIRef('urn:any')
		try:
			g = self.graph.get_context(graphuri)
			g.update(q)
		except:
			return False
		return True


	def test(self, r):
		print r["request"]
		if r["request"].method != 'POST':
			return {"accepted": False}
		file = r["localUri"].replace(self.settings["ns"]["local"], "", 1)
		if exists(self.basedir + file):
			return {"accepted": True, "url": r["localUri"]}
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		file = req["url"].replace(self.settings["ns"]["local"], "", 1)
		currentDir = getcwd()
		service = self.basedir + file
		uri = req["url"]
		queryPath = "%s/queries/" % service
		templatePath = "%s/" % service
		try:
			onlyfiles = [f for f in listdir(queryPath) if isfile(join(queryPath, f))]
		except OSError:
			print "Warning: Can't find path %s for queries." % templatePath
			onlyfiles = []
		queries = {}
		for filename in onlyfiles:
				for root, dirs, files in walk(queryPath):
					for filename in files:
						try:
							currentEndpoint = "local"
							if root.replace(queryPath, "", 1) != "":
								currentEndpoint = root.split("/").pop()
							sparqlQuery = env.get_template("%s/%s" % (root, filename))
							results = self.sparql.query(sparqlQuery.render(uri=uri, session=session, flod=self.flod))
						except Exception, ex:
							print sys.exc_info()
							print ex
							return {"content": "A problem with SPARQL endpoint occurred", "status": 500}

						queries[filename.replace(".query", "")] = results["results"]["bindings"]
		chdir(currentDir)
		try:
			query = env.get_template("%s%s" % (templatePath, "update.query"))
		except Exception:
			return {"content": "Can't find update.query in %s" % templatePath, "status": 500}
			exit(3)
		try:
			out = query.render(queries=queries, uri=uri, session=session, flod=self.flod)
			self._update(out)
		except Exception:
			print sys.exc_info()
			return {"content": "Rendering problems", "status": 500}
		return {"content": out, "mimetype": "text/html"}

