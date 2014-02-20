
class Accept:
	def getExtension(self, mimetype):
		extensions = {}
		extensions['html'] = ('text/html')
		extensions['rdf']  = ('application/rdf+xml')
		extensions['ttl']  = ('text/n3', 'application/x-turtle', 'application/turtle', 'text/turtle', 'application/rdf+turtle')
		extensions['json'] = ('application/json', 'application/x-javascript', 'text/javascript', 'text/x-javascript', 'text/x-json')
		extensions['nt']   = ('text/plain')

		for extension, arr in extensions.items():
			if mimetype in arr:
				return extension
		return "html"

	def getConversionType(self, mimetype):
		conversion = {}
		conversion['html'] = 'xml'
		conversion['rdf'] = 'xml'
		conversion['ttl'] = 'turtle'
		conversion['json'] = 'xml'
		conversion['nt'] = 'nt'
		extension = self.getExtension(mimetype)
		if extension in conversion:
			return conversion[extension]
		#if none exist, assume XML
		return "xml"