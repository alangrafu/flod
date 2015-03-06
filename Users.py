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
	settings = {"user_module": {"login_url": "login", "logout_url": "logout", "create_user": "createuser", "delete_user": "deleteuser", "edit_user": "edituser", "create_group": "creategroup", "delete_group": "deletegroup", "edit_group": "editgroup"}}
	users = {}
	groups = {}
	defaultPermission = True  # True  forbids to continue
	sparql = None
	VOCAB = Namespace("http://flod.info/")
	loginUrl = None
	logoutUrl = None
	createUserUrl = None
	editUserUrl = None
	deleteUserUrl = None
	createGroupUrl = None
	editGroupUrl = None
	flod = None
	_prefix = ""
	basedir = "components/users/"


	def __init__(self, settings, app=None):
		"""Initializes class. Check if login and logout have been redefined."""
		for k in settings:
			self.settings[k] = settings[k]
		self._prefix = self.settings["rootPrefix"] if "rootPrefix" in self.settings else ""
		self.loginUrl = "/"+self.settings["user_module"]["login_url"]
		self.logoutUrl = "/"+ self.settings["user_module"]["logout_url"]
		self.createUserUrl = "/admin/"+ self.settings["user_module"]["create_user"]
		self.editUserUrl = "/admin/" + self.settings["user_module"]["edit_user"]
		self.deleteUserUrl = "/admin/"+self.settings["user_module"]["delete_user"]
		self.createGroupUrl = "/admin/"+ self.settings["user_module"]["create_group"]
		self.editGroupUrl = "/admin/" + self.settings["user_module"]["edit_group"]
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
}
ORDER BY ?groupName""")

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
			if localUri == self.createUserUrl or localUri == self.loginUrl or localUri == self.logoutUrl or localUri == self.editUserUrl or localUri == self.deleteUserUrl or localUri == self.createGroupUrl or localUri == self.editGroupUrl:
				return {"accepted": True, "url": r["localUri"], "permission": True}
			return {"accepted": False, "url": localUri, "permission": True}
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
				return {"content": loginHTML.render(session=session, uri=self._prefix+loginUrl, flod=self.flod), "uri": loginUrl}
			else:
				return {"content": loginHTML.render(session=session, loginError=False, uri=self._prefix+loginUrl, flod=self.flod), "uri": loginUrl}
		if req["request"].method == "POST":
			_username = req["request"].form["username"]
			_password = req["request"].form["password"]
			if "username" in session and _username == session["username"]:
				return {"content": loginHTML.render(session=session, uri=self._prefix+loginUrl, flod=self.flod), "uri": req["url"]}
			loadedResult = self._load_user(_username, _password)
			if loadedResult["result"]:
				session["uri"] = loadedResult["uri"]
				session["salt"] = loadedResult["salt"]
				session["username"] = _username
				session["groups"] = loadedResult["groups"]
				session["params"] = loadedResult["params"]
				return {"content": loginHTML.render(session=session, flod=self.flod), "uri": req["url"]}
			return {"content": loginHTML.render(session=session, loginError=True, flod=self.flod), "uri": req["url"]}
		return {"content": "Invalid method", "status": 406}

	def _logout(self, req, logoutUrl):
		logoutHTML = None
		logoutHTML = env.get_template(self.basedir+"logout.template")
		if "username" in session:
			if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": logoutHTML.render(session=session, flod=self.flod), "uri": self._prefix+logoutUrl}
			if req["request"].method == "POST":
				session.clear()
				return {"content": logoutHTML.render(session=session, flod=self.flod), "uri": self._prefix+logoutUrl}
		else:
			return {"content": "You are not logged in", "uri": logoutUrl, "status": 406}
		return {"content": "You are not logged in", "uri": logoutUrl, "status": 406}

	def _createUser(self, req, createUserUrl):
		MYNS = Namespace(self.settings["ns"]["origin"]) if self.settings["mirrored"] else Namespace(self.settings["ns"]["local"])
		addHTML = env.get_template(self.basedir+"adduser.template")
		groups = self._getGroups()
		if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": addHTML.render(session=session, flod=self.flod, groups=groups), "uri": createUserUrl}
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
					return {"content": addHTML.render(session=session, creationSuccess=False, flod=self.flod, groups=groups), "uri": self._prefix+createUserUrl}
				g.add((MYNS[slugify(_username)], RDF["type"], self.VOCAB["User"]))
				g.add((MYNS[slugify(_username)], self.VOCAB.username, _usernameLiteral))
				g.add((MYNS[slugify(_username)], self.VOCAB.salt, Literal(_salt)))
				g.add((MYNS[slugify(_username)], self.VOCAB.password, Literal(_password)))
				mygroups = req["request"].form.getlist('groups')
				for group in mygroups:
					g.add((MYNS[slugify(_username)], self.VOCAB.group, URIRef(group)))
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
			return {"content": addHTML.render(session=session, groups=groups, creationSuccess=True, flod=self.flod), "uri": self._prefix+createUserUrl}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _deleteUser(self, req, createUserUrl):
		addHTML = env.get_template(self.basedir+"deleteuser.template")
		g = Graph()
		try:
			g.parse("users.ttl", format="turtle")
			usersrq = g.query("""prefix vocab: <http://flod.info/>
SELECT ?u ?name WHERE {
?u a flod:User;
   flod:username ?name .
} ORDER BY ?name""" )
			users = []
			for row in usersrq:
				users.append({"u": str(row["u"]), "name": str(row["name"])})
		except:
			print sys.exc_info()
			return {"content": "Can't read users.ttl", "status": 500}
		if req["request"].method == "GET" or req["request"].method == "HEAD":
			return {"content": addHTML.render(session=session, flod=self.flod, users=users), "uri": createUserUrl}
		if req["request"].method == "POST":
			g = Graph()
			try:
				g.parse("users.ttl", format="turtle")
				_user = URIRef(req["request"].form["user"])
				for s, p, o in g.triples((_user, None, None)):
					g.remove((s, p, o))					
				usersrq = g.query("""prefix vocab: <http://flod.info/>
SELECT ?u ?name WHERE {
?u a flod:User;
   flod:username ?name .
}ORDER BY ?name""" )
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
				users = []
				for row in usersrq:
					users.append({"u": str(row["u"]), "name": str(row["name"])})
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
				return {"content": addHTML.render(session=session, flod=self.flod, users=users), "uri": createUserUrl}
			return {"content": addHTML.render(session=session, users=users, creationSuccess=True, flod=self.flod), "uri": self._prefix+createUserUrl}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _editGroup(self, req, createGroupUrl):
		addHTML = env.get_template(self.basedir+"editgroup.template")
		#groups = self._getGroups()
		if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": addHTML.render(session=session, flod=self.flod, groups=self.groups), "uri": createGroupUrl}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _createGroup(self, req, createGroupUrl):
		MYNS = Namespace(self.settings["ns"]["origin"]) if self.settings["mirrored"] else Namespace(self.settings["ns"]["local"])
		addHTML = env.get_template(self.basedir+"addgroup.template")
		groups = self._getGroups()
		if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": addHTML.render(session=session, flod=self.flod, groups=groups), "uri": createGroupUrl}
		if req["request"].method == "POST":
			g = Graph()
			try:
				_group = URIRef("/"+slugify(req["request"].form["group"]))
				_myUris = req["request"].form["uris"].split("\r\n")
				g.parse("users.ttl", format="turtle")
				for s, p, o in g.triples((_group, RDF["type"], self.VOCAB["Group"])):
					return {"content": addHTML.render(session=session, creationSuccess=False, flod=self.flod, groups=groups), "uri": self._prefix+createUserUrl}
				g.add((_group, RDF["type"], self.VOCAB["Group"]))
				g.add((_group, self.VOCAB["name"], Literal(req["request"].form["group"])))
				for _u in _myUris:
					g.add((_group, self.VOCAB["allowedPattern"], Literal(_u)))
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
			return {"content": addHTML.render(session=session, groups=groups, creationSuccess=True, flod=self.flod), "uri": self._prefix+createGroupUrl}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _getGroups(self):
		g = Graph()
		qres = []
		try:
			g.parse("users.ttl", format="turtle")
			qres = g.query("""prefix vocab: <http://flod.info/>
SELECT ?g ?name WHERE {
?g a flod:Group;
   flod:name ?name .
}""" )
		except Exception, e:
			pass
		return qres

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
					return {"content": editHTML.render(session=session, data=data, creationSuccess=None, flod=self.flod), "uri": self._prefix+editUserUrl}
				return {"content": addHTML.render(session=session, flod=self.flod), "uri": self._prefix+"/"}
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
		if req["request"].method == "POST":
			if "username" not in session:
				return {"content": addHTML.render(session=session, creationError=True, flod=self.flod), "uri": self._prefix+createUserUrl}
			g = Graph()
			try:
				_username = req["request"].form["username"]
				_usernameLiteral = Literal(_username)
				_password = req["request"].form["password"]
				_uri = URIRef(session["uri"])
				g.parse("users.ttl", format="turtle")
				for s, p, o in g.triples((_uri, None, None)):
					if (_password != "" and p == self.VOCAB.password) and bool(p != self.VOCAB.salt) and bool(p != RDF.type):
						g.remove((s, p, o))
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
		return {"content": "Redirecting", "uri": self._prefix+"/", "status": 303}

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
			# Delete user
			if localUri == self.deleteUserUrl and "username" in session:
				return self._deleteUser(req, self.deleteUserUrl)
			# Create group
			if localUri == self.createGroupUrl:
				return self._createGroup(req, self.createGroupUrl)
			# Edit group
			if localUri == self.editGroupUrl and "username" in session:
				return self._editGroup(req, self.editGroupUrl)

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
					#get extra parameters
					_params = {}
					q = g.query("""prefix vocab: <http://flod.info/>
SELECT ?paramName ?paramValue WHERE {
?u vocab:parameter [ vocab:parameterName ?paramName; vocab:parameterValue ?paramValue ];
   vocab:username "%s".
}"""% (username))
					for rrow in q:
						key = str(rrow["paramName"])
						if key not in _params:
							_params[key] = []
						_params[key].append(str(rrow["paramValue"]))

					return {"result": True, "uri": str(row["u"]), "salt": str(row["s"]), "groups": _groups, "params": _params}
		except:
			print "Error loading users RDF graph"
			print sys.exc_info()
		return {"result": False}
