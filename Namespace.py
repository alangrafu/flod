import json

class Namespace:
	ns = {}
	def __init__(self):
		ns_file = open("namespaces.json")
		aux = json.load(ns_file)
		ns_file.close()
		self.ns = aux['ns']
	def uri2curie(self, uri):
		for n in self.ns:
			u = self.ns[n]
			if uri.find(u) == 0:
				rest = uri.replace(u, "", 1)
				return "%s:%s" % (n, rest)
		return uri