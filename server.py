from flask import Flask, redirect, request
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
	app.logger.error("ERROR: Can't load settings.json")
	exit(1)


#Load modules
modules = []

for mod in settings['modules']:
    try:
        m = reload(__import__(mod))
    except ImportError:
        app.logger.error("Can't import module '%s'. Aborting." % mod)
        exit(2)
    try:
        c = getattr(m,mod)
        modules.append(c(settings))
    except AttributeError:
        app.logger.warning("No operations!")


cachedDocuments = {}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
	mime = request.accept_mimetypes.best
	localUri = "%s%s" % (settings['ns']['local'], path)
	#Check if URI is mirrored, otherwise originUri == localUri
	originUri = localUri
	if settings['mirrored'] == True:
		originUri = "%s%s" % (settings['ns']['origin'], path)
	#Store .html, .ttl, .json URLs that are not present in triple store.
	if localUri in cachedDocuments.keys():
		originUri = cachedDocuments[localUri]['originUri']
	content = ""
	r = {"originUri": originUri, "localUri": localUri, "mimetype": mime}
	for module in modules:
		response = module.test(r)
		if response['accepted'] == True:
			if localUri != response['url']:
				cachedDocuments[response['url']] = response
				cachedDocuments[response['url']]["localUri"]  = localUri
				cachedDocuments[response['url']]["originUri"] = originUri
				cachedDocuments[response['url']]["mime"]   = mime
				return redirect(response['url'], code=303)
			content = module.execute(response)
			return content
			break
	return 'Resource not found', 404
	

if __name__ == "__main__":
    app.run(host=settings['host'], port=settings['port'], debug=True)