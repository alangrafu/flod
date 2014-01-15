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
        print "bargh! import error!"
        continue
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
		if module.test(uri) == True:
			content = module.execute(uri)
			break
	return content

if __name__ == "__main__":
    app.run(host=settings['host'], port=settings['port'])