from flask_login import session, redirect, url_for
from jinja2 import Template
from Utils import SparqlEndpoint
import hashlib
import re
import uuid
from rdflib import Namespace, Graph, Literal, URIRef, RDF
from slugify import slugify
import sys
# from Namespace import Namespace
from jinja2 import FileSystemLoader
from jinja2.environment import Environment

env = Environment()
env.loader = FileSystemLoader('.')


class Users:
	settings = {"user_module": {"login_url": "login", "logout_url": "logout", "create_user": "createuser", "delete_user": "deleteuser", "edit_user": "edituser"}}
	users = {}
	groups = {}
	defaultPermission = True  # True  forbids to continue
	sparql = None
	VOCAB = Namespace("http://flod.info/")
	loginUrl = None
	logoutUrl = None
	createUserUrl = None
	editUserUrl = None
	flod = None
	basedir = "components/users/"


	def __init__(self, settings, app=None):
		"""Initializes class. Check if login and logout have been redefined."""
		for k in settings:
			self.settings[k] = settings[k]

		self.loginUrl = "/%s" % (self.settings["user_module"]["login_url"])
		self.logoutUrl = "/%s" % (self.settings["user_module"]["logout_url"])
		self.createUserUrl = "/admin/%s" % (self.settings["user_module"]["create_user"])
		self.editUserUrl = "/admin/%s" % (self.settings["user_module"]["edit_user"])
		self.sparql = SparqlEndpoint(settings)
		self.flod = self.settings["flod"] if "flod" in self.settings else None

		g = Graph()
		g.parse("users.ttl", format="turtle")
		qres = g.query("""BASE <http://example.org/book/>

			prefix vocab: <http://flod.info/>
SELECT ?g ?groupName ?pattern WHERE {
?g a vocab:Group;
vocab:name ?groupName;
vocab:allowedPattern ?pattern .
}""")

		for row in qres:
			_groupName = str(row["groupName"]).lower()
			_pattern = str(row["pattern"])
			if _groupName not in self.groups.keys():
				self.groups[_groupName] = []
			self.groups[_groupName].append(_pattern)

	def test(self, r):
		repl = self.settings['ns']['local']
		localUri = str(r["localUri"].replace(repl, "/", 1))
		myGroups = ["anonymous"]
		if "username" in session:
			myGroups = session["groups"]
		if self._groupPermission(myGroups, localUri):
			if localUri == self.createUserUrl or localUri == self.loginUrl or localUri == self.logoutUrl or localUri == self.editUserUrl:
				return {"accepted": True, "url": r["localUri"], "permission": True}
			return {"accepted": False, "url": r["localUri"], "permission": True}
		return {"accepted": True, "url": r["localUri"], "status": 406, "permission": False}

	def _groupPermission(self, groups, url):
		for g in groups:
			if g not in self.groups:
				continue
			for u in self.groups[g]:
				if re.search(u, url) is not None:
					return True
		return False

	def _login(self, req, loginUrl):
		loginHTML = None
		loginHTML = env.get_template(self.basedir+"login.template")
		if req["request"].method == "GET" or req["request"].method == "HEAD":
			if "username" in session:
				return {"content": loginHTML.render(session=session, uri=loginUrl, flod=self.flod), "uri": loginUrl}
			else:
				return {"content": loginHTML.render(session=session, loginError=False, uri=loginUrl, flod=self.flod), "uri": loginUrl}
		if req["request"].method == "POST":
			_username = req["request"].form["username"]
			_password = req["request"].form["password"]
			if "username" in session and _username == session["username"]:
				return {"content": loginHTML.render(session=session, uri=loginUrl, flod=self.flod), "uri": req["url"]}
			loadedResult = self._load_user(_username, _password)
			if loadedResult["result"]:
				session["uri"] = loadedResult["uri"]
				session["salt"] = loadedResult["salt"]
				session["username"] = _username
				session["groups"] = loadedResult["groups"]
				return {"content": loginHTML.render(session=session, flod=self.flod), "uri": req["url"]}
			return {"content": loginHTML.render(session=session, loginError=True, flod=self.flod), "uri": req["url"]}
		return {"content": "Invalid method", "status": 406}

	def _logout(self, req, logoutUrl):
		logoutHTML = None
		logoutHTML = env.get_template(self.basedir+"logout.template")
		if "username" in session:
			if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": logoutHTML.render(session=session, flod=self.flod), "uri": logoutUrl}
			if req["request"].method == "POST":
				session.clear()
				return {"content": logoutHTML.render(session=session, flod=self.flod), "uri": logoutUrl}
		else:
			return {"content": "You are not logged in", "uri": logoutUrl, "status": 406}
		return {"content": "You are not logged in", "uri": logoutUrl, "status": 406}

	def _createUser(self, req, createUserUrl):
		MYNS = Namespace(self.settings["ns"]["origin"]) if self.settings["mirrored"] else Namespace(self.settings["ns"]["local"])
		addHTML = env.get_template(self.basedir+"adduser.template")
		if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": addHTML.render(session=session, flod=self.flod), "uri": createUserUrl}
		if req["request"].method == "POST":
			# if "username" not in session:
			# return {"content": addHTML.render(session=session, creationError=True), "uri": createUserUrl}
			g = Graph()
			try:
				_username = unicode(uuid.uuid1().hex)
				_usernameLiteral = Literal(req["request"].form["username"])
				_salt = uuid.uuid4().hex
				_password = hashlib.sha224(_salt + req["request"].form["password"]).hexdigest()
				g.parse("users.ttl", format="turtle")
				for s, p, o in g.triples((None, self.VOCAB.username, _usernameLiteral)):
					print s, p, o
					return {"content": addHTML.render(session=session, creationSuccess=False, flod=self.flod), "uri": createUserUrl}
				g.add((MYNS[slugify(_username)], RDF["type"], self.VOCAB["User"]))
				g.add((MYNS[slugify(_username)], self.VOCAB.username, _usernameLiteral))
				g.add((MYNS[slugify(_username)], self.VOCAB.salt, Literal(_salt)))
				g.add((MYNS[slugify(_username)], self.VOCAB.password, Literal(_password)))
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
			return {"content": addHTML.render(session=session, creationSuccess=True, flod=self.flod), "uri": createUserUrl}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _editUser(self, req, editUserUrl):
		self.VOCAB = Namespace("http://flod.info/")
		editHTML = env.get_template(self.basedir+"edituser.template")
		if req["request"].method == "GET" or req["request"].method == "HEAD":
			g = Graph()
			try:
				g.parse("users.ttl", format="turtle")
				data = {}
				for s, p, o in g.triples((URIRef(session["uri"]), self.VOCAB.username, None)):
					data["username"] = str(o)
					print data
					return {"content": editHTML.render(session=session, data=data, creationSuccess=None, flod=self.flod), "uri": editUserUrl}
				return {"content": addHTML.render(session=session, flod=self.flod), "uri": "/"}
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
		if req["request"].method == "POST":
			if "username" not in session:
				return {"content": addHTML.render(session=session, creationError=True, flod=self.flod), "uri": createUserUrl}
			g = Graph()
			try:
				_username = req["request"].form["username"]
				_usernameLiteral = Literal(_username)
				_password = req["request"].form["password"]
				_uri = URIRef(session["uri"])
				g.parse("users.ttl", format="turtle")
				print "removing"
				for s, p, o in g.triples((_uri, None, None)):
					if (_password != "" and p == self.VOCAB.password) and bool(p != self.VOCAB.salt) and bool(p != RDF.type):
						print "Removing ", s, p, o
						g.remove((s, p, o))
				print "adding ", _uri
				g.add((_uri, self.VOCAB.username, _usernameLiteral))
				if _password != "" or p != self.VOCAB.password:
					_password = hashlib.sha224(session["salt"] + req["request"].form["password"]).hexdigest()
					g.add((_uri, self.VOCAB.password, Literal(_password)))
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
					session["username"] = _username
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
			return {"content": editHTML.render(session=session, editionSuccess=True, data=session, flod=self.flod)}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		repl = self.settings['ns']['local']
		localUri = req["url"].replace(repl, "/", 1)
		flod = self.settings["flod"] if "flod" in self.settings else None

		if "permission" not in req or req["permission"] is True:
			# Login
			if localUri == self.loginUrl:
				return self._login(req, self.loginUrl)
			# Logout
			if localUri == self.logoutUrl:
				return self._logout(req, self.logoutUrl)
			# Create user
			if localUri == self.createUserUrl:
				return self._createUser(req, self.createUserUrl)
			# Edit user
			if localUri == self.editUserUrl and "username" in session:
				return self._editUser(req, self.editUserUrl)
		forbidHTML = env.get_template(self.basedir+"forbidden.template")
		return {"content": forbidHTML.render(session=session, creationSuccess=False, flod=self.flod), "url": req["url"], "status": 403}

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
				_password = hashlib.sha224(row["s"] + password).hexdigest()
				if str(_password) == str(row["p"]):
					# get groups
					_groups = []
					q = g.query("""prefix vocab: <http://flod.info/>
SELECT ?groupName WHERE {
?u vocab:group ?g ;
   vocab:username "%s".
?g vocab:name ?groupName.
}"""% (username))
					for rrow in q:
						_groups.append(str(rrow["groupName"]).lower())
					return {"result": True, "uri": str(row["u"]), "salt": str(row["s"]), "groups": _groups}
		except:
			print "Error loading users RDF graph"
			print sys.exc_info()
		return {"result": False}
