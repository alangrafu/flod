from SparqlEndpoint import SparqlEndpoint
from flask_login import session, redirect, url_for
from jinja2 import Template
import hashlib
import uuid
from rdflib import Namespace, Graph, Literal, URIRef, RDF
from slugify import slugify
import sys
#from Namespace import Namespace
from jinja2 import FileSystemLoader
from jinja2.environment import Environment

env = Environment()
env.loader = FileSystemLoader('.')


class Users:
	settings = {"user_module": {"login_url": "login", "logout_url": "logout", "create_user": "createuser", "delete_user": "deleteuser", "edit_user": "edituser"}}
	users = {}
	sparql = None
	def __init__(self, settings, app=None):
		"""Initializes class. Check if login and logout have been redefined."""
		for k in settings:
			self.settings[k] = settings[k]
		self.sparql = SparqlEndpoint(settings)


	def test(self, r):
		loginUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["login_url"])
		logoutUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["logout_url"])
		createUserUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["create_user"])
		editUserUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["edit_user"])
		if r["localUri"] == createUserUrl:
			return {"accepted": True, "url": createUserUrl}
		if r["localUri"] == loginUrl:
			return {"accepted": True, "url": r["localUri"]}
		if r["localUri"] == logoutUrl:
			return {"accepted": True, "url": logoutUrl}
		if r["localUri"] == editUserUrl:
			return {"accepted": True, "url": editUserUrl}
		if "username" in session:
			return {"accepted": False, "url": loginUrl}
		return {"accepted": True, "url": loginUrl}


	def _login(self, req, loginUrl):
		loginHTML = None
		loginHTML = env.get_template("login.html")
		if req["request"].method == "GET" or req["request"].method == "HEAD":
			if "username" in session:
				return {"content": loginHTML.render(session=session), "uri": loginUrl}
			else:
				return {"content": loginHTML.render(session=session, loginError=False), "uri": loginUrl}
		if req["request"].method == "POST":
			_username = req["request"].form["username"]
			_password = req["request"].form["password"]
			if "username" in session and _username == session["username"]:
				return {"content": loginHTML.render(session=session), "uri": loginUrl}
			loadedResult = self._load_user(_username, _password)
			if loadedResult["result"]:
				session["uri"] = loadedResult["uri"]
				session["salt"] = loadedResult["salt"]
				session["username"] = _username
				return {"content": loginHTML.render(session=session), "uri": loginUrl}
			return {"content": loginHTML.render(session=session, loginError=True), "uri": loginUrl}
		return {"content": "Invalid method", "status": 406}


	def _logout(self, req, logoutUrl):
		logoutHTML = None
		logoutHTML = env.get_template("logout.html")
		if "username" in session:
			if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": logoutHTML.render(session=session), "uri": logoutUrl}
			if req["request"].method == "POST":
				session.clear()
				return {"content": logoutHTML.render(session=session), "uri": "/"}
		else:
			return {"content": "Redirecting", "uri": "/", "status": 303}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _createUser(self, req, createUserUrl):
		VOCAB = Namespace("http://flod.info/")
		MYNS = Namespace(self.settings["ns"]["origin"]) if self.settings["mirrored"] else Namespace(self.settings["ns"]["local"])
		addHTML = env.get_template("adduser.html")
		if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": addHTML.render(session=session), "uri": createUserUrl}
		if req["request"].method == "POST":
#			if "username" not in session:
#				return {"content": addHTML.render(session=session, creationError=True), "uri": createUserUrl}
			g = Graph()
			try:
				_username = unicode(uuid.uuid1().hex)
				_usernameLiteral = Literal(req["request"].form["username"])
				_salt = uuid.uuid4().hex
				_password = hashlib.sha224(_salt+req["request"].form["password"]).hexdigest()
				g.parse("users.ttl", format="turtle")
				for s,p,o in g.triples( (None, VOCAB.username, _usernameLiteral) ):
					print s, p, o
					return {"content": addHTML.render(session=session, creationSuccess=False), "uri": createUserUrl}
				g.add((MYNS[slugify(_username)], RDF["type"], VOCAB["User"]))
				g.add((MYNS[slugify(_username)], VOCAB.username, _usernameLiteral))
				g.add((MYNS[slugify(_username)], VOCAB.salt, Literal(_salt)))
				g.add((MYNS[slugify(_username)], VOCAB.password, Literal(_password)))
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
			return {"content": addHTML.render(session=session, creationSuccess=True), "uri": createUserUrl}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _editUser(self, req, editUserUrl):
		VOCAB = Namespace("http://flod.info/")
		editHTML = env.get_template("edituser.html")
		if req["request"].method == "GET" or req["request"].method == "HEAD":
			g = Graph()
			try:
				g.parse("users.ttl", format="turtle")
				data = {}
				for s,p,o in g.triples( (URIRef(session["uri"]), VOCAB.username, None) ):
					data["username"] = str(o)
					print data
					return {"content": editHTML.render(session=session, data=data, creationSuccess=None), "uri": editUserUrl}
				return {"content": addHTML.render(session=session), "uri": "/"}
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
		if req["request"].method == "POST":
			if "username" not in session:
				return {"content": addHTML.render(session=session, creationError=True), "uri": createUserUrl}
			g = Graph()
			try:
				_username = req["request"].form["username"]
				_usernameLiteral = Literal(_username)
				_password = req["request"].form["password"]
				_uri = URIRef(session["uri"])
				g.parse("users.ttl", format="turtle")
				print "removing"
				for s,p,o in g.triples( (_uri, None, None) ):
					if (_password != "" and p == VOCAB.password) and bool(p != VOCAB.salt) and bool(p != RDF.type):
						print "Removing ",s, p, o
						g.remove((s, p, o))
				print "adding ", _uri
				g.add((_uri, VOCAB.username, _usernameLiteral))
				if _password != "" or p != VOCAB.password:
					_password = hashlib.sha224(session["salt"]+req["request"].form["password"]).hexdigest()
					g.add((_uri, VOCAB.password, Literal(_password)))
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
					session["username"] = _username
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
			return {"content": editHTML.render(session=session, editionSuccess=True, data=session)}
		return {"content": "Redirecting", "uri": "/", "status": 303}


	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		loginUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["login_url"])
		logoutUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["logout_url"])
		createUserUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["create_user"])
		editUserUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["edit_user"])
		#Login
		print req["url"]
		if req["url"] == loginUrl:
			return self._login(req, loginUrl)
		#Logout
		if req["url"] == logoutUrl:
			return self._logout(req, logoutUrl)
		#Create user
		if req["url"] == createUserUrl:
			return self._createUser(req, createUserUrl)
		#Edit user
		if req["url"] == editUserUrl and "username" in session:
			return self._editUser(req, editUserUrl)

		return {"content": "login", "uri": loginUrl, "status": 303}

	def _load_user(self, username, password):
		self.users = {}
		g = Graph()
		try:
			g.parse("users.ttl", format="turtle")
			qres = g.query("""prefix vocab: <http://flod.info/>
SELECT ?u ?s ?p WHERE {
 ?u vocab:username "%s";
    vocab:salt ?s;
    vocab:password ?p .
       }""" % (username))
			for row in qres:
				_password = hashlib.sha224(row["s"]+password).hexdigest()				
				if str(_password) == str(row["p"]):
					return {"result": True, "uri": str(row["u"]), "salt": str(row["s"])}
		except:
			print "Error loading users RDF graph"
			print sys.exc_info()
		return {"result": False}


