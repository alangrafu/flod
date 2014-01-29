from flask import Flask, redirect
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

for mod in settings['modules']:
    try:
        m = reload(__import__(mod))
    except ImportError:
        printerr("Can't import module '%s'. Aborting." % mod)
        exit(2)
    try:
        c = getattr(m,mod)
        modules.append(c(settings))
    except AttributeError:
        printerr("No operations!")


cachedDocuments = {}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
	localUri = "%s%s" % (settings['ns']['local'], path)
	#Check if URI is mirrored, otherwise originUri == localUri
	originUri = localUri
	if settings['mirrored'] == True:
		originUri = "%s%s" % (settings['ns']['origin'], path)

	if localUri in cachedDocuments.keys():
		originUri = cachedDocuments[localUri]['origin']
	content = ""
	for module in modules:
		response = module.test(originUri)
		if response['accepted'] == True:
			if localUri != response['url']:
				cachedDocuments[response['url']] = {"local": localUri, "origin": originUri}
				return redirect(response['url'], code=303)
			content = module.execute(originUri)
			return content
			break
	return 'Resource not found', 404
	

if __name__ == "__main__":
    app.run(host=settings['host'], port=settings['port'], debug=True)