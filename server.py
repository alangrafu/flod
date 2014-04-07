from flask import Flask, redirect, request, Response
app = Flask(__name__)
import json
import sys


def printerr(msg):
	sys.stderr.write(msg+"\n")

#Load settings
try:
	settings_file = open("settings.json")
	settings = json.load(settings_file)
except Exception, e:
	printerr("ERROR: Can't load settings.json")
	exit(1)

#Load modules
modules = []

for mod in settings["modules"]:
    try:
        m = reload(__import__(mod))
    except ImportError:
        printerr("Can't import module '%s'. Aborting." % mod)
        exit(2)
    try:
        c = getattr(m,mod)
        modules.append(c(settings, app))
    except AttributeError:
        app.logger.warning("No operations!")

cachedDocuments = {}

@app.route("/")
def root_url():
	return redirect(settings["root"], code=302)

@app.route("/<path:path>", methods=['POST', 'GET', 'HEAD', 'PUT', 'DELETE'])
def catch_all(path):
	mime = request.accept_mimetypes.best
	localUri = "%s%s" % (settings["ns"]["local"], path)
	#Check if URI is mirrored, otherwise originUri == localUri
	originUri = localUri
	if settings["mirrored"] == True:
		originUri = "%s%s" % (settings["ns"]["origin"], path)
	#Store .html, .ttl, .json URLs that are not present in triple store.
	if localUri in cachedDocuments.keys():
		originUri = cachedDocuments[localUri]["originUri"]
	c = ""
	r = {"originUri": originUri, "localUri": localUri, "mimetype": mime, "request": request}
	for module in modules:
		response = module.test(r)
		response["request"] = request
		if response["accepted"] == True:
			if localUri != response["url"]:
				cachedDocuments[response["url"]] = response
				cachedDocuments[response["url"]]["localUri"]  = localUri
				cachedDocuments[response["url"]]["originUri"] = originUri
				cachedDocuments[response["url"]]["mime"]   = mime
				return redirect(response["url"], code=303)
			c = module.execute(response)
			if not "mimetype" in c:
				c["mimetype"] = "text/html"
			if "status" in c:
				if c["status"] >= 300 and c["status"] < 400:
					return redirect(c["uri"], code=c["status"])
			return Response(c["content"], mimetype=c["mimetype"])
			break
	return "Resource not found", 404


if __name__ == "__main__":
	app.secret_key = "A0Zr98j/3yXAAAAAR~XHH!jmN]LWX/,?RT"
	app.run(host=settings["host"], port=settings["port"], debug=True)
