from flask import Flask
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


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
	uri = "%s%s" % (settings['ns']['local'], path)
	if settings['mirrored'] == True:
		uri = "%s%s" % (settings['ns']['origin'], path)
	content = ""
	for module in modules:
		response = module.test(uri)
		if response['accepted'] == True:
			content = module.execute(uri)
			return content
			break
	return 'Resource not found', 404
	

if __name__ == "__main__":
    app.run(host=settings['host'], port=settings['port'])