from SPARQLWrapper import SPARQLWrapper, JSON, XML
from accept import Accept
from jinja2 import Template
from os import listdir
from os.path import isfile, join, exists
from flask import Response
from Namespace import Namespace

class Services:
	settings = {}
	basedir = "components/services/"
	sparql = None
	a = None
	def __init__(self, settings):
		"""Initializes class"""
		self.settings = settings
		self.sparql = SPARQLWrapper(self.settings['endpoints']['local'])
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
		file = r['localUri'].replace(self.settings['ns']['local'], "", 1)
		if exists(self.basedir+file):
			return {"accepted": True, "url": r['localUri']}
		return {"accepted": False}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		file = req['url'].replace(self.settings['ns']['local'], "", 1)
		service = self.basedir+file
		uri = req['url']
		queryPath = "%s/queries/"%service
		templatePath = "%s/" % service
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
			return {"content": out, "mimetype": "text/html"}
