import logging
import byo.package

logger = logging.getLogger(__name__)

class Builder(object):
	def __init__(self, prefix, target, options):
		self.prefix = prefix
		self.target = target
		self.options = options
		self.metadata = byo.package.read_metadata(target)

	def fetch(self):
		logger.info('fetching...')
	def compile(self):
		logger.info('compiling...')
	def install(self):
		logger.info('installing...')
	def package(self):
		logger.info('packaging...')
	def cleanup(self):
		logger.info('cleaning up...')


def _build(prefix, target, options):
	logger.info('building %s for %s...' %(target, prefix))
	builder = Builder(prefix, target, options)
	try:
		builder.fetch()
		builder.compile()
		builder.install()
		builder.package()
	except:
		logger.exception('build failed')
		raise
	finally:
		builder.cleanup()

def build(prefix, target, options = {}):
	logger.info('building %s for %s...' %(target, prefix))
	for package in byo.package.get_package_queue(target):
		_build(prefix, package, options)
