from flask_login import session, redirect, url_for
from jinja2 import Template
import hashlib
from rdflib import Namespace, Graph, Literal, URIRef
from slugify import slugify
import sys
#from Namespace import Namespace

class Users:
	settings = {"user_module": {"login_url": "login", "logout_url": "logout", "create_user": "createuser", "delete_user": "deleteuser", "edit_user": "edituser"}}
	users = {}
	def __init__(self, settings, app=None):
		"""Initializes class. Check if login and logout have been redefined."""
		for k in settings:
			self.settings[k] = settings[k]


	def test(self, r):
		loginUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["login_url"])
		logoutUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["logout_url"])
		createUserUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["create_user"])
		if r["localUri"] == createUserUrl:
			return {"accepted": True, "url": createUserUrl}
		if "username" in session and (r["localUri"] != loginUrl and r["localUri"] != logoutUrl):
			return {"accepted": False, "url": r["localUri"]}
		if r["localUri"] == logoutUrl:
			return {"accepted": True, "url": logoutUrl}
		return {"accepted": True, "url": loginUrl}


	def _login(self, req, loginUrl):
		loginHTML = None
		with open("login.html") as f:
			loginHTML = Template("\n".join(f.readlines()))
		if req["request"].method == "GET" or req["request"].method == "HEAD":
			if "username" in session:
				return {"content": loginHTML.render(logged=True, loginError=False), "uri": loginUrl}
			else:
				return {"content": loginHTML.render(logged=False, loginError=False), "uri": loginUrl}
		if req["request"].method == "POST":
			_username = req["request"].form["username"]
			_password = req["request"].form["password"]
			if "username" in session and _username == session["username"]:
				return {"content": loginHTML.render(logged = True), "uri": loginUrl}
			if self.load_user(_username, _password):
				session["username"] = _username
				return {"content": loginHTML.render(logged = True), "uri": loginUrl}
			return {"content": loginHTML.render(logged = False, loginError=True), "uri": loginUrl}
		return {"content": "Invalid method", "status": 406}


	def _logout(self, req, logoutUrl):
		logoutHTML = None
		print "LOGOUT"
		with open("logout.html") as f:
			logoutHTML = Template("\n".join(f.readlines()))
		if "username" in session:
			if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": logoutHTML.render(logged = True), "uri": logoutUrl}
			if req["request"].method == "POST":
				session.clear()
				return {"content": logoutHTML.render(logged = False), "uri": "/"}
		else:
			return {"content": "Redirecting", "uri": "/", "status": 303}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def _createUser(self, req, createUserUrl):
		VOCAB = Namespace("http://flod.info/")
		with open("adduser.html") as f:
			addHTML = Template("\n".join(f.readlines()))
		if req["request"].method == "GET" or req["request"].method == "HEAD":
				return {"content": addHTML.render(logged = True), "uri": createUserUrl}
		if req["request"].method == "POST":
			if "username" not in session:
				return {"content": addHTML.render(logged = True, creationError=True), "uri": createUserUrl}
			g = Graph()
			try:
				_username = req["request"].form["username"]
				_usernameLiteral = Literal(_username)
				_password = req["request"].form["password"]
				g.parse("users.ttl", format="turtle")
				for s,p,o in g.triples( (None, VOCAB.username, _usernameLiteral) ):
					print s, p, o
					return {"content": addHTML.render(logged = True, creationSuccess=False), "uri": createUserUrl}
				g.add((URIRef("/"+slugify(_username)), VOCAB.username, _usernameLiteral))
				g.add((URIRef("/"+slugify(_username)), VOCAB.password, Literal(_password)))
				with open("users.ttl", "wb") as f:
					f.write(g.serialize(format='turtle'))
			except:
				print sys.exc_info()
				return {"content": "Can't write on users.ttl", "status": 500}
			return {"content": addHTML.render(logged = True, creationSuccess=True), "uri": createUserUrl}
		return {"content": "Redirecting", "uri": "/", "status": 303}

	def execute(self, req):
		"""Serves a URI, given that the test method returned True"""
		loginUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["login_url"])
		logoutUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["logout_url"])
		createUserUrl = "%s%s" % (self.settings["ns"]["local"], self.settings["user_module"]["create_user"])
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
		return {"content": "login", "uri": loginUrl, "status": 303}

	def load_user(self, username, password):
		self.users = {}
		g = Graph()
		try:
			g.parse("users.ttl", format="turtle")
			qres = g.query("""prefix vocab: <http://flod.info/>
SELECT * WHERE {
 ?u vocab:username "%s";
    vocab:password "%s" .
       }""" % (username, password))
			for row in qres:
				return True
		except:
			print "Error loading users RDF graph"
		return False


