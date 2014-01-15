from SPARQLWrapper import SPARQLWrapper, JSON


class Types:
	config = {}
	def __init__(self, config):
		self.config = config

	def operations(self):
		print "hola Types"

	def test(self, uri):
		return True

	def execute(self, uri):
		r = """<!DOCTYPE html>
		<html lang="">
			<head>
				<title>Title Page</title>
				<meta charset=utf-8>
				<meta name=description content="">
				<meta name=viewport content="width=device-width, initial-scale=1">
				<meta name="viewport" content="width=device-width, initial-scale=1.0">
				<!-- Bootstrap CSS -->
				<link href="//netdna.bootstrapcdn.com/bootstrap/3.0.3/css/bootstrap.min.css" rel="stylesheet" media="screen">
			</head>
			<body>
				<h1 class="text-center">%s</h1>
				<div class="content">
				 <div class="row">
				 	<div class="col-xs-12 col-sm-12 col-md-12 col-lg-12">
				 		<table class="table table-striped table-hover">
				 			<thead>
				 				<tr>
				 					<th>Predicate</th><th>Object</th>
				 				</tr>
				 			</thead>
				 			<tbody>
"""%uri
		sparql = SPARQLWrapper(self.config['endpoints']['local'])
		sparql.setQuery("""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?p ?o
    WHERE { <%s> ?p ?o }
LIMIT 100""" % uri)
		sparql.setReturnFormat(JSON)
		results = sparql.query().convert()

		for result in results["results"]["bindings"]:
			r += """				 				<tr>
				 					<td>%s</td><td>%s</td>
				 				</tr>
""" %(result["p"]["value"], result["o"]["value"])
		r += """		
				 			</tbody>
				 		</table>
				 	</div>
				 </div>
				<!-- jQuery -->
				<script src="//code.jquery.com/jquery.js"></script>
				<!-- Bootstrap JavaScript -->
				<script src="//netdna.bootstrapcdn.com/bootstrap/3.0.3/js/bootstrap.min.js"></script>
			</body>
		</html>"""
		return r
