from os.path import exists

class Static:
	basedir = "components/static/"
	settings = None
	def __init__(self, settings, app=None):
		self.settings = settings
		pass

	def __getMimetype(self, uri):
		extensions = {"html": "text/html", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "bmp": "image/bmp", "css": "text/css", "json": "application/json", "js": "application/javascript"}
		extension = uri.split(".").pop()
		if extension in extensions:
			return extensions[extension]
		return "text/plain"

	def operations(self):
		print "hola Static"

	def test(self, r):
		file = r["localUri"].replace(self.settings["ns"]["local"], "", 1)
		if exists(self.basedir+file):
			return {"accepted": True, "url": r["localUri"]}
		return {"accepted": False}

	def execute(self, r):
		"""Serves a URI, given that the test method returned True"""
		content = ""
		filename = self.basedir+r["url"].replace(self.settings["ns"]["local"], "", 1)
		with open(filename, mode="rb") as file: # b is important -> binary
			content += file.read()
		return {"content": content, "mimetype": self.__getMimetype(r["url"])}
