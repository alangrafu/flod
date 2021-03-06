from flask_login import session
from accept import Accept
from jinja2 import Template
from os import listdir, walk, chdir, getcwd
from os.path import isfile, join, exists
from flask import Response
from Utils import Namespace, SparqlEndpoint, EnvironmentFactory
import sys
from jinja2 import FileSystemLoader
from rdflib import ConjunctiveGraph, URIRef
import requests


class JsonBasedWriter:
	settings = {}
	sparql = None
	flod = None
	basedir = "components/jsonupdates/"
	g = None
	env = None

	def __init__(self, settings, app=None):
		"""Initializes class"""

		self.settings = settings
		if "sparqlUpdateEndpoint" not in self.settings or "local" not in self.settings["sparqlUpdateEndpoint"]:
			print "Sparql Update endpoint not defined. Aborting."
			exit(10)
		self.sparql = SparqlEndpoint(self.settings)
		self.flod = self.settings["flod"] if "flod" in self.settings else None
		self.graph = ConjunctiveGraph('SPARQLUpdateStore')
		self.graph.open((self.settings["endpoints"]["local"], self.settings["sparqlUpdateEndpoint"]["local"]["url"]))
		e = EnvironmentFactory(self.settings, app)
		self.env = e.getEnvironment()

	def _update(self, q):
		graphuri = URIRef('urn:any')
		try:
			auth = None
			if "user" in self.settings["sparqlUpdateEndpoint"]["local"] and "pass" in self.settings["sparqlUpdateEndpoint"]["local"]:
			        auth = HTTPDigestAuth(self.settings["sparqlUpdateEndpoint"]["local"]['user'], self.settings["sparqlUpdateEndpoint"]["local"]['pass'])
			headers = {'content-type': 'application/sparql-update'}
			r = requests.post(self.settings["sparqlUpdateEndpoint"]["local"]["url"], data=q, auth=auth, headers=headers)
			if r.status_code > 299:
			        return False
		except:
			print sys.exc_info()
			return False
		return True


	def test(self, r):
		if r["request"].method != 'POST':
			return {"accepted": False}
		file = r["localUri"].replace(self.settings["ns"]["local"], "", 1)
		if exists(self.basedir + file):
			return {"accepted": True, "url": r["localUri"]}
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		file = req["url"].replace(self.settings["ns"]["local"], "", 1)
		myForm = req["request"].form
		myJson = req["request"].get_json()
		if myForm is None and myJson is None:
			return {"content": "{\"success\": false}", "status": 500, "mimetype": "application/json"}
		if myJson is not None:
			data = myJson
		else:
			data = myForm

		currentDir = getcwd()
		jsonService = self.basedir + file
		uri = req["url"]
		queryPath = "%s/queries/" % jsonService
		updatePath = "%s/" % jsonService
		try:
			onlyfiles = [f for f in listdir(queryPath) if isfile(join(queryPath, f)) and str(f).endswith(".query")]
		except OSError:
			print "Warning: Can't find path %s for queries." % updatePath
			onlyfiles = []
		queries = {}
		for filename in onlyfiles:
				for root, dirs, files in walk(queryPath):
					for filename in files:
						try:
							currentEndpoint = "local"
							if root.replace(queryPath, "", 1) != "":
								currentEndpoint = root.split("/").pop()
							sparqlQuery = self.env.get_template("%s/%s" % (root, filename))
							results = self.sparql.query(sparqlQuery.render(uri=uri, session=session, flod=self.flod, data=data))
							queries[filename.replace(".query", "")] = results["results"]["bindings"]
						except Exception, ex:
							print sys.exc_info()
							print sparqlQuery
							print ex
							return {"content": "A problem with SPARQL endpoint occurred", "status": 500}
		chdir(currentDir)
		try:
			updatefiles = [f for f in listdir(updatePath) if isfile(join(updatePath, f)) and str(f).endswith(".update")]
			for updatefile in updatefiles:
				query = self.env.get_template(join(updatePath, updatefile))
				out = query.render(queries=queries, uri=uri, session=session, flod=self.flod, data=data)
				print out
				if not self._update(out.encode("utf-8")):
					raise Exception
		except Exception:
			print sys.exc_info()
			return {"content": "{\"success\": false}", "status": 500, "mimetype": "application/json"}
		return {"content": "{\"success\": true}", "mimetype": "application/json"}

