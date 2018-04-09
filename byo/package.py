import yaml
import byo
import logging
import os.path
import yaml

logger = logging.getLogger(__name__)
cache = {}

class Metadata(object):
	def __init__(self, data):
		self.data = data

	@property
	def depends(self):
		return self.data.get('Depends on', [])

def read_metadata(name):
	if name in cache:
		return cache[name]

	root = os.path.join(byo.root, 'packages')
	with open(os.path.join(root, name + ".package")) as f:
		data = yaml.load(f)
	logger.debug('read metadata %s', name)
	data = Metadata(data)
	cache[name] = data
	return data

def get_package_queue(name):
	queue = [name]
	result = []
	visited = set()
	while queue:
		current = queue
		queue = []
		for name in current:
			logger.debug('processing %s...' %name)
			if name not in visited:
				visited.add(name)
				result.append(name)
				data = read_metadata(name)
				queue += data.depends
	return reversed(result)
