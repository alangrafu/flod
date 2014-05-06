"""Util classes."""

from Utils import SparqlEndpoint
from jinja2 import Template
from os import listdir, chdir, getcwd, walk
from os.path import isfile, join, exists
from flask import Response
from Namespace import Namespace
import sys
from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from flask_login import session

env = Environment()
env.loader = FileSystemLoader('.')


class Services:
	settings = {}
	basedir = "components/services/"
	sparql = None
	flod = None

	def __init__(self, settings, app=None):
		"""Initializes class"""
		self.settings = settings
		self.sparql = SparqlEndpoint(self.settings)
		self.ns = Namespace()
		self.flod = self.settings["flod"] if "flod" in self.settings else None

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
							print sparqlQuery.render(uri=uri, session=session, flod=self.flod)
							results = self.sparql.query(sparqlQuery.render(uri=uri, session=session, flod=self.flod))
						except Exception, ex:
							print sys.exc_info()
							print ex
							return {"content": "A problem with SPARQL endpoint occurred", "status": 500}
						try:
							queries[filename.replace(".query", "")] = results["results"]["bindings"]
						except:
							continue
		chdir(currentDir)
		try:
			html = env.get_template("%s%s" % (templatePath, "html.template"))
		except Exception:
			return {"content": "Can't find html.template in %s" % templatePath, "status": 500}
			exit(3)
		try:
			out = html.render(queries=queries, uri=uri, session=session, flod=self.flod)
		except Exception:
			print sys.exc_info()
			return {"content": "Rendering problems", "status": 500}
		return {"content": out, "mimetype": "text/html"}
