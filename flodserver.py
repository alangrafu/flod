"""Main file"""
from flask import Flask, redirect, request, Response, make_response, current_app
app = Flask(__name__)
import json
import sys
from functools import update_wrapper
from datetime import timedelta
from jinja2 import FileSystemLoader
from Utils import EnvironmentFactory

# env = Environment()
# env.loader = FileSystemLoader('.')



def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

def printerr(msg):
	sys.stderr.write(msg + "\n")

settingsFile = "components/settings.json"
if len(sys.argv) > 1:
	settingsFile = sys.argv[1]
	print "Using %s as settings file" %settingsFile
# Load settings
try:
	settings_file = open(settingsFile)
	settings = json.load(settings_file)
except Exception, e:
	printerr("ERROR: Can't load %s" % settingsFile)
	exit(1)


# Create environment
e = EnvironmentFactory(settings, app)
env = e.getEnvironment()

# Load modules
app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = settings["secret"];
modules = []

# Load other paths where extra modules may exists
# Add modules in settings.json like
#  	"additionalModules": [ "components/customModules", "foo/bar" ],
# Later, you can add any module available in those dirs in "modules" setting
#

if "additionalModules" in settings:
	for directory in settings["additionalModules"]:
		sys.path.append(directory)

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
if "rootPrefix" in settings:
	settings["rootPrefix"] = settings["rootPrefix"].rstrip("/")+"/"
	settings["flod"]["rootPrefix"] = settings["rootPrefix"].rstrip("/")+"/"
else:
	settings["rootPrefix"] = ""
	settings["flod"]["rootPrefix"] = ""


@app.route("/")
@crossdomain(origin='*')
def root_url():
	return redirect(settings["root"], code=302)


@app.route("/<path:path>", methods=['POST', 'GET', 'HEAD', 'PUT', 'DELETE'])
@crossdomain(origin='*')
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
	if "rootPrefix" in settings:
		localUri = localUri.replace(settings["rootPrefix"], "", 1)
		originUri = originUri.replace(settings["rootPrefix"], "", 1)
		if localUri == settings["ns"]["local"]:
			return redirect(settings["root"], code=302)
	c = ""
	r = {"originUri": originUri, "localUri": localUri, "mimetype": mime, "request": request}
	for module in modules:
		response = module.test(r)
		response["request"] = request
		if response["accepted"] is True:
			if localUri != response["url"]:
				# cachedDocuments[response["url"]] = response
				# cachedDocuments[response["url"]]["localUri"] = localUri
				# cachedDocuments[response["url"]]["originUri"] = originUri
				# cachedDocuments[response["url"]]["mime"] = mime
				return redirect(response["url"], code=303)
			c = module.execute(response)
			if "mimetype" not in c:
				c["mimetype"] = "text/html"
			status = c["status"] if "status" in c else 200
			if status >= 300 and status < 400:
				return redirect(c["uri"], code=status)
			return Response(c["content"], mimetype=c["mimetype"]), status
			break
	notfoundHTML = env.get_template("notfound.template")
	return notfoundHTML.render(uri=localUri, flod=settings["flod"]), 404


if __name__ == "__main__":
	app.secret_key = settings["secret"]
	app.run(host=settings["host"], threaded= True, port=settings["port"], debug=settings["debug"] if "debug" in settings else False)
