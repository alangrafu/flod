"""Main file"""
from flask import Flask, redirect, request, Response
app = Flask(__name__)
import json
import sys
from jinja2 import FileSystemLoader
from jinja2.environment import Environment

env = Environment()
env.loader = FileSystemLoader('.')


def printerr(msg):
	sys.stderr.write(msg + "\n")

# Load settings
try:
	settings_file = open("settings.json")
	settings = json.load(settings_file)
except Exception, e:
	printerr("ERROR: Can't load settings.json")
	exit(1)

# Load modules
modules = []

for mod in settings["modules"]:
	try:
		m = reload(__import__(mod))
	except:
		printerr("Can't import module '%s'. Aborting." % mod)
		exit(2)
	try:
		c = getattr(m, mod)
		modules.append(c(settings, app))
	except AttributeError:
		app.logger.warning("No operations!")
cachedDocuments = {}
print modules


@app.route("/")
def root_url():
	return redirect(settings["root"], code=302)


@app.route("/<path:path>", methods=['POST', 'GET', 'HEAD', 'PUT', 'DELETE'])
def catch_all(path):
	mime = request.accept_mimetypes.best
	localUri = "%s%s" % (settings["ns"]["local"], path)
	# Check if URI is mirrored, otherwise originUri == localUri
	originUri = localUri
	if settings["mirrored"] is True:
		originUri = "%s%s" % (settings["ns"]["origin"], path)
	# Store .html, .ttl, .json URLs that are not present in triple store.
	if localUri in cachedDocuments.keys():
		originUri = cachedDocuments[localUri]["originUri"]
	c = ""
	r = {"originUri": originUri, "localUri": localUri, "mimetype": mime, "request": request}
	for module in modules:
		response = module.test(r)
		response["request"] = request
		if response["accepted"] is True:
			if localUri != response["url"]:
				cachedDocuments[response["url"]] = response
				cachedDocuments[response["url"]]["localUri"] = localUri
				cachedDocuments[response["url"]]["originUri"] = originUri
				cachedDocuments[response["url"]]["mime"] = mime
				return redirect(response["url"], code=303)
			c = module.execute(response)
			if "mimetype" not in c:
				c["mimetype"] = "text/html"
			status = c["status"] if "status" in c else 200
			if status >= 300 and status < 400:
				return redirect(c["uri"], code=status)
			return Response(c["content"], mimetype=c["mimetype"]), status
			break
	return "Resource not found", 404


if __name__ == "__main__":
	app.secret_key = settings["secret"]
	app.run(host=settings["host"], port=settings["port"], debug=settings["debug"] if "debug" in settings else False)
