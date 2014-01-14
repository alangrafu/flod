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
for m in settings['modules']:
	try:
		modules.append( __import__(m))
	except Exception, e:
		printerr("ERROR: Can't find module \"%s\". Aborting." % m)
		exit(2)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return 'You want path: %s' % path

if __name__ == "__main__":
    app.run()