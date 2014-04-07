from SPARQLWrapper import SPARQLWrapper, JSON
from jinja2 import Template
from os import listdir, chdir, getcwd, walk
from os.path import isfile, join, exists
from flask import Response
from Namespace import Namespace
import sys

class Services:
	settings = {}
	basedir = "components/services/"
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
		file = r["localUri"].replace(self.settings["ns"]["local"], "", 1)
		if exists(self.basedir+file):
			return {"accepted": True, "url": r["localUri"]}
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		file = req["url"].replace(self.settings["ns"]["local"], "", 1)
		currentDir = getcwd()
		service = self.basedir+file
		uri = req["url"]
		queryPath = "%s/queries/"%service
		templatePath = "%s/" % service
		try:
			onlyfiles = [ f for f in listdir(queryPath) if isfile(join(queryPath,f)) ]
		except OSError:
			print "Can't find path %s for queries. Aborting" % templatePath
			return Response(response="Internal error\n\n", status=500)
		queries = {}
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
							f = open("%s/%s"%(root, filename))
							sparqlQuery = Template("\n".join(f.readlines()))
							self.sparql.setQuery(sparqlQuery.render(uri=uri))
							f.close()
						except Exception, ex:
							print sys.exc_info()
							
						self.sparql.setReturnFormat(JSON)
						results = self.sparql.query().convert()
						queries[filename.replace(".query", "")] = results["results"]["bindings"]
		chdir(currentDir)
		try:
			f = open("%s%s"%(templatePath, "html.template"))
			html = Template("\n".join(f.readlines()))
			f.close()
		except Exception:
			return "Can't find html.template in %s"%templatePath
			exit(3)
		try:
			out = html.render(queries=queries, uri=uri)
		except Exception:
			return "Rendering problems"
		return {"content": out, "mimetype": "text/html"}
